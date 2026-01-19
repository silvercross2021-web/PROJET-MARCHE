from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count, Value
from django.db.models.functions import Concat
from django.db import transaction
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import Commercant, Etal, Paiement, Ticket, Secteur, TaxeJournaliere, Collecteur, LotTickets, RapportJournalierCollecteur, RapportMensuelCollecteur
from .services import (
    DashboardService, PaiementService, TicketService,
    CommercantService, EtalService, RapportService, TaxeJournaliereService, RapportCollecteurService
)
from django.http import JsonResponse, HttpResponse
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from .permissions import (
    can_manage_commercants, can_manage_etals, can_manage_tickets, can_manage_collecteurs, can_modify_paiement
)


def _forbidden():
    return HttpResponseForbidden('Accès interdit.')


def login_view(request):
    """Vue de connexion"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('identifiant')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Identifiant ou mot de passe incorrect.')
    
    return render(request, 'market/login.html')


@login_required
def logout_view(request):
    """Vue de déconnexion"""
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    """Vue du tableau de bord"""
    TaxeJournaliereService.generer_taxes_pour_date(timezone.now().date())
    service = DashboardService()
    
    # Données de base
    total_aujourdhui = service.get_total_collecte_aujourdhui()
    comparaison_hier = service.get_comparaison_hier()
    commercants_retard = service.get_commercants_en_retard()
    top_retards = service.get_top_commercants_retard(5)
    taux_data = service.get_taux_occupation()
    collecte_mensuelle = service.get_collecte_mensuelle()
    comparaison_mois = service.get_comparaison_mois_precedent()
    collection_journaliere = service.get_collection_journaliere()
    evolution_mensuelle = service.get_evolution_mensuelle()
    repartition = service.get_repartition_paiements()
    alertes = service.get_alertes()
    activites = service.get_activites_recentes(10)
    
    # Tickets
    tickets_utilises = Ticket.objects.filter(statut='utilise').count()
    tickets_restants = Ticket.objects.filter(statut='disponible').count()
    total_carnets = Ticket.objects.count()
    
    # Détails du jour pour modal
    aujourdhui = timezone.now().date()
    paiements_aujourdhui = Paiement.objects.filter(
        date_paiement__date=aujourdhui
    ).select_related('commercant', 'etal', 'ticket').order_by('-date_paiement')[:20]
    
    context = {
        # KPI Cards
        'total_aujourdhui': total_aujourdhui,
        'comparaison_hier': comparaison_hier,
        'commercants_retard': commercants_retard,
        'top_retards': top_retards,
        'taux_occupation': taux_data['taux'],
        'taux_data': taux_data,
        'collecte_mensuelle': collecte_mensuelle,
        'comparaison_mois': comparaison_mois,
        
        # Graphiques
        'collection_journaliere': collection_journaliere,
        'evolution_mensuelle': evolution_mensuelle,
        
        # Tickets
        'tickets_utilises': tickets_utilises,
        'tickets_restants': tickets_restants,
        'total_carnets': total_carnets,
        
        # Données supplémentaires
        'repartition': repartition,
        'alertes': alertes,
        'activites': activites,
        'paiements_aujourdhui': paiements_aujourdhui,
        
        # Métadonnées
        'derniere_mise_a_jour': timezone.now(),
    }
    
    return render(request, 'market/dashboard.html', context)


@login_required
def commercants_list(request):
    """Vue de la liste des commerçants"""
    search_query = (request.GET.get('search', '') or '').strip()
    
    commercants = Commercant.objects.filter(actif=True)
    
    if search_query:
        terms = search_query.split()
        full_name_filter = Q()
        if len(terms) >= 2:
            full_name_filter = Q(nom__icontains=terms[0], prenom__icontains=" ".join(terms[1:]))

        commercants = commercants.annotate(
            full_name=Concat('nom', Value(' '), 'prenom')
        ).filter(
            full_name_filter |
            Q(full_name__icontains=search_query) |
            Q(nom__icontains=search_query) |
            Q(prenom__icontains=search_query) |
            Q(contact__icontains=search_query) |
            Q(type_commerce__icontains=search_query) |
            Q(etals__numero__icontains=search_query)
        ).distinct()
    
    # Ajouter l'état de paiement pour chaque commerçant (taxe journalière)
    commercants_avec_etat = []
    aujourd_hui = timezone.now().date()
    for commercant in commercants:
        taxes = TaxeJournaliere.objects.filter(commercant=commercant)
        etals_occupees = list(
            commercant.etals.filter(statut='occupe')
            .order_by('numero')
            .values_list('numero', flat=True)
        )

        if taxes.filter(paye=False, statut='du', date__lt=aujourd_hui).exists():
            etat_paiement = 'retard'
        elif taxes.filter(paye=False, statut='du', date=aujourd_hui).exists():
            etat_paiement = 'en_attente'
        else:
            etat_paiement = 'a_jour'
        
        commercants_avec_etat.append({
            'commercant': commercant,
            'etat_paiement': etat_paiement,
            'etals_occupees': ", ".join(etals_occupees) if etals_occupees else "-",
        })
    
    context = {
        'commercants': commercants_avec_etat,
        'search_query': search_query,
    }
    
    return render(request, 'market/commercants.html', context)


@login_required
def etals_list(request):
    """Vue de la liste des étals"""
    search_query = request.GET.get('search', '')
    filtre_statut = request.GET.get('statut', 'tous')
    filtre_secteur = request.GET.get('secteur', '')
    page_number = request.GET.get('page', 1)
    
    etals = Etal.objects.select_related('secteur', 'commercant')
    
    if search_query:
        etals = etals.filter(
            Q(numero__icontains=search_query) |
            Q(secteur__nom__icontains=search_query) |
            Q(commercant__nom__icontains=search_query) |
            Q(commercant__prenom__icontains=search_query)
        )
    
    if filtre_statut != 'tous':
        etals = etals.filter(statut=filtre_statut)

    if filtre_secteur:
        etals = etals.filter(secteur_id=filtre_secteur)
    
    paginator = Paginator(etals.order_by('secteur__nom', 'numero'), 15)
    etals_page = paginator.get_page(page_number)
    
    total_etals = Etal.objects.count()
    etals_occupes = Etal.objects.filter(statut='occupe').count()
    etals_libres = Etal.objects.filter(statut='libre').count()
    secteurs = Secteur.objects.all().order_by('nom')
    
    context = {
        'etals': etals_page,
        'search_query': search_query,
        'filtre_statut': filtre_statut,
        'filtre_secteur': filtre_secteur,
        'total_etals': total_etals,
        'etals_occupes': etals_occupes,
        'etals_libres': etals_libres,
        'secteurs': secteurs,
        'paginator': paginator,
        'page_obj': etals_page,
    }
    
    return render(request, 'market/etals.html', context)


@login_required
def etal_detail(request, etal_id):
    """Vue détaillée d'un étal"""
    etal = get_object_or_404(Etal.objects.select_related('secteur', 'commercant'), id=etal_id)
    historique = etal.historique_attributions.select_related('commercant').all()
    paiements = Paiement.objects.filter(etal=etal).select_related('commercant').order_by('-date_paiement')[:50]
    taxes_journalieres = TaxeJournaliere.objects.filter(etal=etal).select_related('commercant').order_by('-date')[:60]
    
    context = {
        'etal': etal,
        'historique': historique,
        'paiements': paiements,
        'taxes_journalieres': taxes_journalieres,
    }
    return render(request, 'market/etal_detail.html', context)


@login_required
def paiements_view(request):
    """Vue de saisie des paiements"""
    if not can_modify_paiement(request.user):
        return _forbidden()
    TaxeJournaliereService.generer_taxes_pour_date(timezone.now().date())
    service = PaiementService()
    form_defaults = {}
    
    if request.method == 'POST':
        commercant_id = request.POST.get('commercant_id')
        mode_paiement = request.POST.get('mode_paiement')
        ticket_numero = (request.POST.get('ticket_numero') or '').strip()
        etal_id = request.POST.get('etal_id')
        collecteur_id = request.POST.get('collecteur_id')
        date_paiement_str = request.POST.get('date_paiement')
        form_defaults = {
            'mode_paiement': mode_paiement,
            'ticket_numero': ticket_numero,
            'etal_id': etal_id,
            'collecteur_id': collecteur_id,
            'date_paiement': date_paiement_str,
        }
        
        try:
            if not commercant_id:
                raise ValueError("Aucun commerçant sélectionné.")
            
            commercant = get_object_or_404(Commercant, id=commercant_id)
            if not commercant.actif:
                raise ValueError("Le commerçant est inactif. Impossible d'enregistrer un paiement.")
            
            etal = None
            if etal_id:
                try:
                    etal = Etal.objects.get(id=etal_id, commercant=commercant, statut='occupe')
                except Etal.DoesNotExist:
                    raise ValueError(f"L'étal sélectionné n'est pas occupé par ce commerçant.")
            else:
                etal = commercant.etals.filter(statut='occupe').first()
                if not etal:
                    raise ValueError("Aucun étal occupé trouvé pour ce commerçant.")
            
            ticket = None
            if not ticket_numero:
                raise ValueError("Le numéro de ticket est obligatoire.")
            ticket = Ticket.objects.filter(
                numero=ticket_numero,
                statut='disponible',
                utilise=False
            ).exclude(paiements__isnull=False).first()
            if not ticket:
                raise ValueError("Ticket introuvable, déjà utilisé ou non disponible.")

            if not collecteur_id:
                raise ValueError("Le collecteur est obligatoire.")
            collecteur = Collecteur.objects.filter(id=collecteur_id, actif=True).first()
            if not collecteur:
                raise ValueError("Collecteur invalide ou inactif.")

            if not ticket.lot_id:
                raise ValueError("Ticket non attribué à un lot.")
            ticket.lot.refresh_from_db()
            if ticket.lot.statut != 'ouvert':
                raise ValueError("Lot de tickets clos.")
            if ticket.lot.collecteur_id != collecteur.id:
                raise ValueError("Ticket non attribué à ce collecteur.")

            date_paiement = None
            if date_paiement_str:
                try:
                    date_paiement = datetime.fromisoformat(date_paiement_str)
                    if timezone.is_naive(date_paiement):
                        date_paiement = timezone.make_aware(date_paiement, timezone.get_current_timezone())
                except Exception:
                    date_paiement = None

            montant = service.calculer_taxe_journaliere(etal)
            
            paiement = service.enregistrer_paiement(
                commercant=commercant,
                montant=montant,
                mode_paiement=mode_paiement,
                etal=etal,
                ticket=ticket,
                collecteur=collecteur,
                user=request.user,
                date_paiement=date_paiement
            )
            
            messages.success(request, f'✅ Paiement de {montant:,.0f} FCFA enregistré avec succès.')
            # Rediriger vers la page paiements en conservant le commerçant sélectionné
            return redirect(f"{request.path}?search_merchant={commercant.nom_complet}")
            
        except ValueError as e:
            messages.error(request, f'❌ {str(e)}')
        except Exception as e:
            messages.error(request, f'❌ Erreur lors de l\'enregistrement: {str(e)}')
    
    # Recherche de commerçant
    search_merchant = request.GET.get('search_merchant', '')
    commercant_selectionne = None
    etals_selection = []
    taxes_par_etal_json = '{}'
    
    if search_merchant:
        # Recherche améliorée avec Concat pour nom complet
        commercants = Commercant.objects.annotate(
            nom_complet_search=Concat('nom', Value(' '), 'prenom')
        ).filter(
            Q(nom__icontains=search_merchant) |
            Q(prenom__icontains=search_merchant) |
            Q(nom_complet_search__icontains=search_merchant) |
            Q(etals__numero__icontains=search_merchant)
        ).distinct().first()
        
        if commercants:
            if not commercants.actif:
                messages.warning(request, f'Le commerçant "{commercants.nom_complet}" est inactif. Vous ne pouvez pas enregistrer de paiement pour ce commerçant.')
            else:
                commercant_selectionne = commercants
                etals_selection = commercants.etals.filter(statut='occupe').order_by('numero')
        else:
            # Message d'info si aucun résultat trouvé (sera affiché dans le template)
            pass
    
    # Si POST échoue, conserver le commerçant sélectionné et les données du formulaire
    if request.method == 'POST' and not commercant_selectionne and request.POST.get('commercant_id'):
        try:
            commercant_selectionne = Commercant.objects.get(id=request.POST.get('commercant_id'))
            etals_selection = commercant_selectionne.etals.filter(statut='occupe').order_by('numero')
            # Conserver aussi la recherche pour l'affichage
            if not search_merchant:
                search_merchant = commercant_selectionne.nom_complet
        except Exception:
            commercant_selectionne = None
            etals_selection = []

    if commercant_selectionne and etals_selection:
        taxes_par_etal = {str(e.id): float(service.calculer_taxe_journaliere(e)) for e in etals_selection}
        taxes_par_etal_json = json.dumps(taxes_par_etal)

    # Filtres paiements récents
    filtre_mode = request.GET.get('mode', '')
    filtre_date_debut = request.GET.get('date_debut', '')
    filtre_date_fin = request.GET.get('date_fin', '')
    filtre_ticket = request.GET.get('ticket', '')
    filtre_commercant_p = request.GET.get('commercant_p', '')
    page_number = request.GET.get('page', 1)

    paiements_qs = Paiement.objects.select_related('commercant', 'ticket').order_by('-date_paiement')
    if filtre_mode:
        paiements_qs = paiements_qs.filter(mode_paiement=filtre_mode)
    if filtre_date_debut:
        paiements_qs = paiements_qs.filter(date_paiement__date__gte=filtre_date_debut)
    if filtre_date_fin:
        paiements_qs = paiements_qs.filter(date_paiement__date__lte=filtre_date_fin)
    if filtre_ticket:
        paiements_qs = paiements_qs.filter(ticket__numero__icontains=filtre_ticket)
    if filtre_commercant_p:
        paiements_qs = paiements_qs.filter(commercant__id=filtre_commercant_p)

    paginator = Paginator(paiements_qs, 20)
    paiements_recents = paginator.get_page(page_number)

    # Tickets disponibles : statut='disponible', utilise=False, et aucun paiement lié
    tickets_disponibles = Ticket.objects.filter(
        statut='disponible',
        utilise=False
    ).exclude(
        paiements__isnull=False
    ).distinct().order_by('date_creation')[:100]
    collecteurs_filter = Collecteur.objects.filter(actif=True).order_by('nom', 'prenom')
    commercants_filter = Commercant.objects.filter(actif=True).order_by('nom', 'prenom')
    
    # Résumé du jour
    resume_journalier = service.get_resume_journalier()
    
    context = {
        'commercant_selectionne': commercant_selectionne,
        'etals_selection': etals_selection,
        'tickets_disponibles': tickets_disponibles,
        'collecteurs_filter': collecteurs_filter,
        'taxes_par_etal_json': taxes_par_etal_json,
        'paiements_recents': paiements_recents,
        'resume_journalier': resume_journalier,
        'search_merchant': search_merchant,
        'form_defaults': form_defaults,
        'filtre_mode': filtre_mode,
        'filtre_date_debut': filtre_date_debut,
        'filtre_date_fin': filtre_date_fin,
        'filtre_ticket': filtre_ticket,
        'filtre_commercant_p': filtre_commercant_p,
        'paginator': paginator,
        'page_obj': paiements_recents,
        'commercants_filter': commercants_filter,
    }
    
    return render(request, 'market/paiements.html', context)


@login_required
@require_http_methods(["GET"])
def tickets_disponibles_par_collecteur(request, collecteur_id):
    if not can_modify_paiement(request.user):
        return JsonResponse({'detail': 'Accès interdit.'}, status=403)

    collecteur = Collecteur.objects.filter(id=collecteur_id, actif=True).first()
    if not collecteur:
        return JsonResponse({'tickets': []})

    tickets_qs = Ticket.objects.filter(
        lot__collecteur_id=collecteur.id,
        lot__statut='ouvert',
        statut='disponible',
        utilise=False,
    ).exclude(
        paiements__isnull=False
    ).distinct().order_by('numero')[:500]

    tickets = list(tickets_qs.values_list('numero', flat=True))
    return JsonResponse({'tickets': tickets})


@login_required
def tickets_list(request):
    """Vue de la liste des tickets"""
    search_query = request.GET.get('search', '')
    filtre_statut = request.GET.get('statut', 'tous')
    date_debut = request.GET.get('date_debut', '')
    date_fin = request.GET.get('date_fin', '')
    filtre_commercant = request.GET.get('commercant', '')
    filtre_etal = request.GET.get('etal', '')
    page_number = request.GET.get('page', 1)
    
    tickets = Ticket.objects.all()
    
    if search_query:
        tickets = tickets.filter(numero__icontains=search_query)

    if filtre_statut != 'tous':
        tickets = tickets.filter(statut=filtre_statut)

    if date_debut:
        tickets = tickets.filter(date_creation__date__gte=date_debut)
    if date_fin:
        tickets = tickets.filter(date_creation__date__lte=date_fin)

    if filtre_commercant:
        tickets = tickets.filter(paiements__commercant__id=filtre_commercant)

    if filtre_etal:
        tickets = tickets.filter(paiements__etal__id=filtre_etal)

    paginator = Paginator(tickets.order_by('-date_creation'), 20)
    tickets_page = paginator.get_page(page_number)
    
    commercants_filter = Commercant.objects.filter(actif=True).order_by('nom', 'prenom')
    etals_filter = Etal.objects.order_by('secteur__nom', 'numero')

    context = {
        'tickets': tickets_page,
        'search_query': search_query,
        'filtre_statut': filtre_statut,
        'date_debut': date_debut,
        'date_fin': date_fin,
        'filtre_commercant': filtre_commercant,
        'filtre_etal': filtre_etal,
        'commercants_filter': commercants_filter,
        'etals_filter': etals_filter,
        'paginator': paginator,
        'page_obj': tickets_page,
    }
    
    return render(request, 'market/tickets.html', context)


@login_required
def ticket_detail(request, ticket_id):
    """Vue détaillée d'un ticket"""
    ticket = get_object_or_404(Ticket.objects.prefetch_related('paiements'), id=ticket_id)
    paiements = ticket.paiements.select_related('commercant', 'etal').order_by('-date_paiement')
    context = {
        'ticket': ticket,
        'paiements': paiements,
    }
    return render(request, 'market/ticket_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def ticket_create(request):
    """Créer un ticket (ou plusieurs)"""
    if not can_manage_tickets(request.user):
        return _forbidden()
    service = TicketService()
    if request.method == 'POST':
        quantite = request.POST.get('quantite', '1')
        numero = request.POST.get('numero', '').strip()
        try:
            quantite_int = int(quantite)
            if quantite_int < 1 or quantite_int > 1000:
                raise ValueError("Quantité entre 1 et 1000 requise.")
            created = []
            if numero:
                ticket = Ticket.objects.create(numero=numero)
                created.append(ticket)
            else:
                created = service.generer_tickets_en_masse(quantite_int)
            messages.success(request, f'{len(created)} ticket(s) créé(s) avec succès.')
            return redirect('tickets')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création : {str(e)}')
    return render(request, 'market/ticket_form.html', {'action': 'Créer'})


@login_required
@require_http_methods(["GET", "POST"])
def ticket_update(request, ticket_id):
    """Modifier un ticket"""
    if not can_manage_tickets(request.user):
        return _forbidden()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.method == 'POST':
        numero = request.POST.get('numero', '').strip()
        statut = request.POST.get('statut', 'disponible')
        motif = request.POST.get('motif', '')
        try:
            if ticket.paiements.exists() or ticket.statut == 'utilise':
                raise ValueError("Impossible de modifier un ticket déjà utilisé.")
            if numero:
                ticket.numero = numero
            if statut not in ['disponible', 'annule', 'perdu']:
                raise ValueError("Statut invalide.")

            ticket.statut = statut
            ticket.utilise = False
            ticket.date_utilisation = None
            ticket.motif = motif
            ticket.save()
            messages.success(request, 'Ticket modifié avec succès.')
            return redirect('tickets')
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification : {str(e)}')
    return render(request, 'market/ticket_form.html', {'action': 'Modifier', 'ticket': ticket})


@login_required
@require_http_methods(["POST"])
def ticket_delete(request, ticket_id):
    """Supprimer un ticket (interdit si utilisé)"""
    if not can_manage_tickets(request.user):
        return _forbidden()
    ticket = get_object_or_404(Ticket, id=ticket_id)
    try:
        if ticket.statut == 'utilise':
            raise ValueError("Impossible de supprimer un ticket déjà utilisé.")
        ticket.delete()
        messages.success(request, 'Ticket supprimé.')
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression : {str(e)}')
    return redirect('tickets')


@login_required
def commercant_detail(request, commercant_id):
    """Vue détaillée d'un commerçant"""
    commercant = get_object_or_404(Commercant, id=commercant_id)
    service = CommercantService()
    
    statistiques = service.get_statistiques_commercant(commercant)
    historique = service.get_historique_paiements(commercant)
    taxes_journalieres = TaxeJournaliere.objects.filter(commercant=commercant).select_related('etal').order_by('-date')[:60]
    etals = commercant.etals.filter(statut='occupe')
    
    context = {
        'commercant': commercant,
        'statistiques': statistiques,
        'historique': historique,
        'taxes_journalieres': taxes_journalieres,
        'etals': etals,
    }
    
    return render(request, 'market/commercant_detail.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def commercant_create(request):
    """Créer un nouveau commerçant"""
    if not can_manage_commercants(request.user):
        return _forbidden()
    etals_disponibles = Etal.objects.filter(statut='libre').order_by('secteur__nom', 'numero')
    etal_service = EtalService()
    
    if request.method == 'POST':
        try:
            commercant = Commercant.objects.create(
                nom=request.POST.get('nom'),
                prenom=request.POST.get('prenom'),
                contact=request.POST.get('contact'),
                type_commerce=request.POST.get('type_commerce'),
                actif=True
            )
            
            etal_id = request.POST.get('etal_id')
            if etal_id:
                etal = get_object_or_404(Etal, id=etal_id, statut='libre')
                etal_service.attribuer_etal(etal, commercant, user=request.user)
            
            messages.success(request, f'Commerçant {commercant.nom_complet} créé avec succès.')
            return redirect('commercant_detail', commercant_id=commercant.id)
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    return render(request, 'market/commercant_form.html', {
        'action': 'Créer',
        'etals_disponibles': etals_disponibles,
        'etal_selectionne': None,
    })


@login_required
@require_http_methods(["GET", "POST"])
def commercant_update(request, commercant_id):
    """Modifier un commerçant"""
    if not can_manage_commercants(request.user):
        return _forbidden()
    commercant = get_object_or_404(Commercant, id=commercant_id)
    etal_service = EtalService()
    
    if request.method == 'POST':
        try:
            commercant.nom = request.POST.get('nom')
            commercant.prenom = request.POST.get('prenom')
            commercant.contact = request.POST.get('contact')
            commercant.type_commerce = request.POST.get('type_commerce')
            commercant.actif = request.POST.get('actif') == 'on'
            commercant.save()
            
            etal_id = request.POST.get('etal_id')
            anciens_etals = list(commercant.etals.all())
            nouvel_etal = None
            
            if etal_id:
                nouvel_etal = get_object_or_404(Etal, id=etal_id)
                if not commercant.actif:
                    raise ValueError("Le commerçant est inactif, impossible d'attribuer un étal.")
                if nouvel_etal.statut == 'occupe' and nouvel_etal.commercant != commercant:
                    raise ValueError("L'étal sélectionné est déjà occupé.")
                
                # Utiliser le service pour centraliser et tracer
                etal_service.attribuer_etal(nouvel_etal, commercant, user=request.user)
            
            # Libérer les autres étals du commerçant s'ils ne sont plus sélectionnés
            for etal in anciens_etals:
                if nouvel_etal and etal.id == nouvel_etal.id:
                    continue
                etal.commercant = None
                etal.statut = 'libre'
                etal.date_attribution = None
                etal.save()
            
            messages.success(request, f'Commerçant {commercant.nom_complet} modifié avec succès.')
            return redirect('commercants')
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    etals_disponibles = Etal.objects.filter(
        Q(statut='libre') | Q(commercant=commercant)
    ).order_by('secteur__nom', 'numero')
    etal_selectionne = commercant.etals.filter(statut='occupe').first()
    
    return render(request, 'market/commercant_form.html', {
        'commercant': commercant,
        'action': 'Modifier',
        'etals_disponibles': etals_disponibles,
        'etal_selectionne': etal_selectionne,
    })


@login_required
@require_http_methods(["POST"])
def commercant_delete(request, commercant_id):
    """Supprimer un commerçant"""
    if not can_manage_commercants(request.user):
        return _forbidden()
    commercant = get_object_or_404(Commercant, id=commercant_id)
    
    try:
        nom = commercant.nom_complet
        commercant.actif = False
        commercant.save()
        messages.success(request, f'Commerçant {nom} désactivé avec succès.')
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
    
    return redirect('commercants')


@login_required
@require_http_methods(["GET", "POST"])
def etal_attribuer(request, etal_id):
    """Attribuer un étal à un commerçant"""
    if not can_manage_etals(request.user):
        return _forbidden()
    etal = get_object_or_404(Etal, id=etal_id)
    service = EtalService()
    
    if request.method == 'POST':
        commercant_id = request.POST.get('commercant_id')
        try:
            commercant = get_object_or_404(Commercant, id=commercant_id)
            if not commercant.actif:
                raise ValueError("Le commerçant est inactif.")
            service.attribuer_etal(etal, commercant, user=request.user)
            messages.success(request, f'Étal {etal.numero} attribué à {commercant.nom_complet}.')
            return redirect('etals')
        except ValueError as e:
            messages.error(request, str(e))
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    commercants = Commercant.objects.filter(actif=True).order_by('nom', 'prenom')
    context = {
        'etal': etal,
        'commercants': commercants,
    }
    return render(request, 'market/etal_attribuer.html', context)


@login_required
@require_http_methods(["POST"])
def etal_liberer(request, etal_id):
    """Libérer un étal"""
    if not can_manage_etals(request.user):
        return _forbidden()
    etal = get_object_or_404(Etal, id=etal_id)
    service = EtalService()
    
    try:
        # Vérifier s'il reste des taxes journalières dues pour cet étal
        if TaxeJournaliere.objects.filter(etal=etal, paye=False, statut='du').exists():
            raise ValueError("Impossible de libérer : taxes journalières dues pour cet étal.")
        service.liberer_etal(etal, user=request.user)
        messages.success(request, f'Étal {etal.numero} libéré avec succès.')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('etals')


@login_required
@require_http_methods(["GET", "POST"])
def etal_create(request):
    """Créer un nouvel étal"""
    if not can_manage_etals(request.user):
        return _forbidden()
    if request.method == 'POST':
        numero = request.POST.get('numero')
        secteur_id = request.POST.get('secteur_id')
        superficie = request.POST.get('superficie')
        statut = request.POST.get('statut', 'libre')
        try:
            secteur = get_object_or_404(Secteur, id=secteur_id)
            etal = Etal.objects.create(
                numero=numero,
                secteur=secteur,
                superficie=superficie,
                statut=statut
            )
            messages.success(request, f'Étal {etal.numero} créé avec succès.')
            return redirect('etals')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')
    
    secteurs = Secteur.objects.all().order_by('nom')
    return render(request, 'market/etal_form.html', {
        'action': 'Créer',
        'secteurs': secteurs,
        'etal': None,
    })


@login_required
@require_http_methods(["GET", "POST"])
def etal_update(request, etal_id):
    """Modifier un étal"""
    if not can_manage_etals(request.user):
        return _forbidden()
    etal = get_object_or_404(Etal, id=etal_id)
    
    if request.method == 'POST':
        numero = request.POST.get('numero')
        secteur_id = request.POST.get('secteur_id')
        superficie = request.POST.get('superficie')
        statut = request.POST.get('statut', 'libre')
        try:
            secteur = get_object_or_404(Secteur, id=secteur_id)
            etal.numero = numero
            etal.secteur = secteur
            etal.superficie = superficie
            etal.statut = statut
            if statut == 'libre':
                etal.commercant = None
                etal.date_attribution = None
            etal.save()
            messages.success(request, f'Étal {etal.numero} modifié avec succès.')
            return redirect('etals')
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')
    
    secteurs = Secteur.objects.all().order_by('nom')
    return render(request, 'market/etal_form.html', {
        'action': 'Modifier',
        'secteurs': secteurs,
        'etal': etal,
    })


@login_required
@require_http_methods(["POST"])
def etal_delete(request, etal_id):
    """Supprimer (libérer puis supprimer) un étal"""
    if not can_manage_etals(request.user):
        return _forbidden()
    etal = get_object_or_404(Etal, id=etal_id)
    try:
        etal.commercant = None
        etal.statut = 'libre'
        etal.date_attribution = None
        etal.save()
        etal.delete()
        messages.success(request, f'Étal {etal.numero} supprimé.')
    except Exception as e:
        messages.error(request, f'Erreur lors de la suppression: {str(e)}')
    return redirect('etals')


@login_required
def paiement_modifier(request, paiement_id):
    """Modifier un paiement"""
    if not can_modify_paiement(request.user):
        return _forbidden()
    paiement = get_object_or_404(Paiement, id=paiement_id)
    service = PaiementService()
    
    if request.method == 'POST':
        try:
            nouveau_montant = Decimal(request.POST.get('montant'))
            nouveau_mode = request.POST.get('mode_paiement')
            service.modifier_paiement(paiement, nouveau_montant, nouveau_mode)
            messages.success(request, 'Paiement modifié avec succès.')
            return redirect('paiements')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    context = {
        'paiement': paiement,
    }
    return render(request, 'market/paiement_modifier.html', context)


@login_required
@require_http_methods(["POST"])
def paiement_annuler(request, paiement_id):
    """Annuler un paiement"""
    if not can_modify_paiement(request.user):
        return _forbidden()
    paiement = get_object_or_404(Paiement, id=paiement_id)
    service = PaiementService()
    
    try:
        service.annuler_paiement(paiement)
        messages.success(request, 'Paiement annulé avec succès.')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    
    return redirect('paiements')


@login_required
def paiement_reçu(request, paiement_id):
    """Générer un reçu pour un paiement"""
    paiement = get_object_or_404(Paiement, id=paiement_id)
    
    context = {
        'paiement': paiement,
    }
    return render(request, 'market/paiement_reçu.html', context)


@login_required
@require_http_methods(["GET", "POST"])
def tickets_generer(request):
    """Générer des tickets en masse"""
    if not can_manage_tickets(request.user):
        return _forbidden()
    if request.method == 'POST':
        try:
            quantite = int(request.POST.get('quantite', 1))
            if quantite < 1 or quantite > 1000:
                messages.error(request, 'La quantité doit être entre 1 et 1000.')
                return redirect('tickets')
            
            service = TicketService()
            tickets = service.generer_tickets_en_masse(quantite)
            messages.success(request, f'{quantite} ticket(s) généré(s) avec succès.')
            return redirect('tickets')
        except Exception as e:
            messages.error(request, f'Erreur: {str(e)}')
    
    return render(request, 'market/tickets_generer.html')


@login_required
def collecteurs_list(request):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    search_query = (request.GET.get('search', '') or '').strip()
    page_number = request.GET.get('page', 1)

    qs = Collecteur.objects.all().order_by('nom', 'prenom')
    if search_query:
        qs = qs.filter(Q(nom__icontains=search_query) | Q(prenom__icontains=search_query) | Q(contact__icontains=search_query))

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page_number)

    return render(request, 'market/collecteurs.html', {
        'collecteurs': page_obj,
        'search_query': search_query,
        'paginator': paginator,
        'page_obj': page_obj,
    })


@login_required
@require_http_methods(["GET", "POST"])
def collecteur_create(request):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    if request.method == 'POST':
        try:
            Collecteur.objects.create(
                nom=request.POST.get('nom') or '',
                prenom=request.POST.get('prenom') or '',
                contact=request.POST.get('contact') or '',
                actif=True,
            )
            messages.success(request, 'Collecteur créé avec succès.')
            return redirect('collecteurs')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')

    return render(request, 'market/collecteur_form.html', {'action': 'Créer', 'collecteur': None})


@login_required
@require_http_methods(["GET", "POST"])
def collecteur_update(request, collecteur_id):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    collecteur = get_object_or_404(Collecteur, id=collecteur_id)
    if request.method == 'POST':
        try:
            collecteur.nom = request.POST.get('nom') or ''
            collecteur.prenom = request.POST.get('prenom') or ''
            collecteur.contact = request.POST.get('contact') or ''
            collecteur.actif = request.POST.get('actif') == 'on'
            collecteur.save()
            messages.success(request, 'Collecteur modifié avec succès.')
            return redirect('collecteurs')
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')

    return render(request, 'market/collecteur_form.html', {'action': 'Modifier', 'collecteur': collecteur})


@login_required
@require_http_methods(["POST"])
def collecteur_toggle(request, collecteur_id):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    collecteur = get_object_or_404(Collecteur, id=collecteur_id)
    collecteur.actif = not collecteur.actif
    collecteur.save(update_fields=['actif'])
    return redirect('collecteurs')


@login_required
def lots_tickets_list(request):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    page_number = request.GET.get('page', 1)
    collecteur_id = request.GET.get('collecteur', '')

    qs = LotTickets.objects.select_related('collecteur').all().order_by('-date_remise', '-id')
    if collecteur_id:
        qs = qs.filter(collecteur_id=collecteur_id)

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(page_number)
    collecteurs_filter = Collecteur.objects.filter(actif=True).order_by('nom', 'prenom')

    return render(request, 'market/lots_tickets.html', {
        'lots': page_obj,
        'collecteurs_filter': collecteurs_filter,
        'filtre_collecteur': collecteur_id,
        'paginator': paginator,
        'page_obj': page_obj,
    })


@login_required
@require_http_methods(["GET", "POST"])
def lot_ticket_create(request):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    collecteurs = Collecteur.objects.filter(actif=True).order_by('nom', 'prenom')
    if request.method == 'POST':
        try:
            collecteur_id = request.POST.get('collecteur_id')
            collecteur = get_object_or_404(Collecteur, id=collecteur_id, actif=True)
            date_remise_str = request.POST.get('date_remise')
            date_remise = timezone.now().date()
            if date_remise_str:
                date_remise = datetime.strptime(date_remise_str, '%Y-%m-%d').date()

            lot = LotTickets(
                collecteur=collecteur,
                date_remise=date_remise,
                remis_par=request.user,
                statut=request.POST.get('statut') or 'ouvert',
                ticket_debut=(request.POST.get('ticket_debut') or '').strip() or None,
                ticket_fin=(request.POST.get('ticket_fin') or '').strip() or None,
            )
            if not lot.ticket_debut or not lot.ticket_fin:
                raise ValueError("La plage de tickets est obligatoire pour un carnet.")
            with transaction.atomic():
                lot.full_clean()
                lot.save()
                count = lot.assigner_plage()
            messages.success(request, f'Lot {lot.id} créé avec succès.')
            messages.success(request, f'{count} ticket(s) assigné(s) au lot {lot.id}.')
            return redirect('lots_tickets')
        except Exception as e:
            messages.error(request, f'Erreur lors de la création: {str(e)}')

    return render(request, 'market/lot_ticket_form.html', {'action': 'Créer', 'lot': None, 'collecteurs': collecteurs})


@login_required
@require_http_methods(["GET", "POST"])
def lot_ticket_update(request, lot_id):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    lot = get_object_or_404(LotTickets.objects.select_related('collecteur'), id=lot_id)
    collecteurs = Collecteur.objects.filter(actif=True).order_by('nom', 'prenom')
    if request.method == 'POST':
        try:
            ancien_collecteur_id = lot.collecteur_id
            ancien_ticket_debut = lot.ticket_debut
            ancien_ticket_fin = lot.ticket_fin
            ancien_statut = lot.statut

            collecteur_id = request.POST.get('collecteur_id')
            nouveau_collecteur = get_object_or_404(Collecteur, id=collecteur_id, actif=True)
            date_remise_str = request.POST.get('date_remise')
            if date_remise_str:
                lot.date_remise = datetime.strptime(date_remise_str, '%Y-%m-%d').date()
            lot.statut = request.POST.get('statut') or lot.statut
            lot.ticket_debut = (request.POST.get('ticket_debut') or '').strip() or None
            lot.ticket_fin = (request.POST.get('ticket_fin') or '').strip() or None
            if not lot.ticket_debut or not lot.ticket_fin:
                raise ValueError("La plage de tickets est obligatoire pour un carnet.")

            # Règle 1 carnet = 1 lot : une fois des tickets assignés, on ne modifie plus la plage/collecteur
            if lot.nb_remis > 0:
                if ancien_collecteur_id != nouveau_collecteur.id:
                    raise ValueError("Carnet déjà assigné: impossible de changer le collecteur.")
                if ancien_ticket_debut != lot.ticket_debut or ancien_ticket_fin != lot.ticket_fin:
                    raise ValueError("Carnet déjà assigné: impossible de modifier la plage.")

            lot.collecteur = nouveau_collecteur

            # Réouverture contrôlée
            if ancien_statut == 'clos' and lot.statut == 'ouvert':
                if lot.nb_utilises > 0:
                    raise ValueError("Impossible de réouvrir un lot déjà utilisé.")
            if lot.statut == 'clos' and not lot.date_cloture:
                lot.date_cloture = timezone.now().date()
            if lot.statut == 'ouvert':
                lot.date_cloture = None
            with transaction.atomic():
                lot.full_clean()
                lot.save()
                if lot.statut == 'ouvert':
                    count = lot.assigner_plage()
                    messages.success(request, f'{count} ticket(s) assigné(s) au lot {lot.id}.')
            messages.success(request, 'Lot modifié avec succès.')
            return redirect('lots_tickets')
        except Exception as e:
            messages.error(request, f'Erreur lors de la modification: {str(e)}')

    return render(request, 'market/lot_ticket_form.html', {'action': 'Modifier', 'lot': lot, 'collecteurs': collecteurs})


@login_required
@require_http_methods(["POST"])
def lot_ticket_assigner_plage(request, lot_id):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    lot = get_object_or_404(LotTickets, id=lot_id)
    try:
        count = lot.assigner_plage()
        messages.success(request, f'{count} ticket(s) assigné(s) au lot {lot.id}.')
    except Exception as e:
        messages.error(request, f'Erreur: {str(e)}')
    return redirect('lots_tickets')


@login_required
@require_http_methods(["POST"])
def lot_ticket_clore(request, lot_id):
    if not can_manage_collecteurs(request.user):
        return _forbidden()
    lot = get_object_or_404(LotTickets, id=lot_id)
    lot.statut = 'clos'
    lot.date_cloture = timezone.now().date()
    lot.save(update_fields=['statut', 'date_cloture'])
    return redirect('lots_tickets')


@login_required
def rapports_view(request):
    """Vue des rapports complets"""
    type_rapport = request.GET.get('type', 'hebdomadaire')
    maintenant = timezone.now()
    service = RapportService()
    
    if type_rapport == 'hebdomadaire':
        # Rapport hebdomadaire - utilise le service amélioré
        semaines = service.generer_rapport_hebdomadaire()
        
        # Totaux
        total_general = sum(s['total'] for s in semaines)
        total_nombre = sum(s['nombre'] for s in semaines)
        total_especes = sum(s['especes'] for s in semaines)
        total_mobile_money = sum(s['mobile_money'] for s in semaines)
        total_retards = sum(s['retards'] for s in semaines)
        moyenne_generale = total_general / (len(semaines) * 7) if semaines else Decimal('0.00')
        
        context = {
            'type_rapport': 'hebdomadaire',
            'semaines': semaines,
            'total_general': total_general,
            'total_nombre': total_nombre,
            'total_especes': total_especes,
            'total_mobile_money': total_mobile_money,
            'total_retards': total_retards,
            'moyenne_generale': moyenne_generale,
            'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
        }
    
    elif type_rapport == 'mensuel':
        # Rapport mensuel - utilise le service amélioré
        mois = service.generer_rapport_mensuel()
        
        # Totaux
        total_general = sum(m['total'] for m in mois)
        total_nombre = sum(m['nombre'] for m in mois)
        total_especes = sum(m['especes'] for m in mois)
        total_mobile_money = sum(m['mobile_money'] for m in mois)
        total_retards = sum(m['retards'] for m in mois)
        
        # Calculer la moyenne mensuelle
        jours_totaux = sum((m['date_fin'] - m['date_debut']).days + 1 for m in mois)
        moyenne_generale = total_general / jours_totaux if jours_totaux > 0 else Decimal('0.00')
        
        context = {
            'type_rapport': 'mensuel',
            'mois': mois,
            'total_general': total_general,
            'total_nombre': total_nombre,
            'total_especes': total_especes,
            'total_mobile_money': total_mobile_money,
            'total_retards': total_retards,
            'moyenne_generale': moyenne_generale,
            'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
        }
    elif type_rapport == 'personnalise':
        # Rapport personnalisé
        date_debut_str = request.GET.get('date_debut', '')
        date_fin_str = request.GET.get('date_fin', '')
        
        if date_debut_str and date_fin_str:
            try:
                date_debut = datetime.strptime(date_debut_str, '%Y-%m-%d').date()
                date_fin = datetime.strptime(date_fin_str, '%Y-%m-%d').date()
                
                # Validation des dates
                if date_fin < date_debut:
                    messages.error(request, 'La date de fin doit être postérieure à la date de début.')
                    context = {
                        'type_rapport': 'personnalise',
                        'date_debut': date_debut_str,
                        'date_fin': date_fin_str,
                        'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
                    }
                else:
                    # Limiter à 1 an maximum
                    if (date_fin - date_debut).days > 365:
                        messages.warning(request, 'La période est limitée à 1 an. Affichage des 365 derniers jours.')
                        date_debut = date_fin - timedelta(days=365)
                    
                    rapport = service.generer_rapport_personnalise(date_debut, date_fin)
                    
                    context = {
                        'type_rapport': 'personnalise',
                        'rapport': rapport,
                        'date_debut': date_debut_str,
                        'date_fin': date_fin_str,
                        'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
                    }
            except ValueError as e:
                messages.error(request, f'Format de date invalide: {str(e)}')
                context = {
                    'type_rapport': 'personnalise',
                    'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
                }
        else:
            context = {
                'type_rapport': 'personnalise',
                'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
            }
    else:
        context = {
            'type_rapport': 'personnalise',
            'date_generation': maintenant.strftime('%d/%m/%Y à %H:%M'),
        }
    
    # Statistiques générales (tous temps)
    total_collecte_all = Paiement.objects.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    total_paiements_all = Paiement.objects.count()
    total_especes_all = Paiement.objects.filter(mode_paiement='especes').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    total_mobile_all = Paiement.objects.filter(mode_paiement='mobile_money').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
    total_retards_all = TaxeJournaliere.objects.filter(paye=False, statut='du', date__lt=timezone.now().date()).count()
    
    context.update({
        'total_collecte': total_collecte_all,
        'total_paiements': total_paiements_all,
        'total_especes': total_especes_all,
        'total_mobile': total_mobile_all,
        'total_retards': total_retards_all,
    })
    
    return render(request, 'market/rapports.html', context)


@login_required
def rapports_export_pdf(request):
    """Export PDF d'un rapport"""
    # Pour l'instant, on retourne une vue HTML qui peut être imprimée
    # On pourrait utiliser reportlab ou weasyprint pour un vrai PDF
    type_rapport = request.GET.get('type', 'hebdomadaire')
    return rapports_view(request)  # Réutilise la vue principale


@login_required
def rapports_export_excel(request):
    """Export Excel d'un rapport"""
    # Pour l'instant, on retourne une réponse JSON
    # On pourrait utiliser openpyxl ou xlsxwriter pour un vrai Excel
    type_rapport = request.GET.get('type', 'hebdomadaire')
    return JsonResponse({'message': 'Export Excel à implémenter'})


@login_required
def historique_collecteur(request, collecteur_id):
    """Vue de l'historique complet d'un collecteur"""
    collecteur = get_object_or_404(Collecteur, id=collecteur_id)
    
    # Récupérer les paramètres de filtrage
    debut = request.GET.get('debut')
    fin = request.GET.get('fin')
    annee = request.GET.get('annee')
    
    # Convertir les dates si fournies
    date_debut = None
    date_fin = None
    if debut:
        try:
            date_debut = datetime.strptime(debut, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Format de date de début invalide')
    
    if fin:
        try:
            date_fin = datetime.strptime(fin, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Format de date de fin invalide')
    
    # Récupérer l'historique journalier
    historique_journalier = RapportCollecteurService.get_historique_journalier_collecteur(
        collecteur_id, date_debut, date_fin
    )
    
    # Récupérer l'historique mensuel
    annee_filtre = None
    if annee:
        try:
            annee_filtre = int(annee)
        except ValueError:
            messages.error(request, 'Format d\'année invalide')
    
    historique_mensuel = RapportCollecteurService.get_historique_mensuel_collecteur(
        collecteur_id, annee_filtre
    )
    
    # Statistiques globales pour ce collecteur
    stats_globales = RapportCollecteurService.get_statistiques_globales_collecteurs(
        date_debut, date_fin
    )
    
    # Filtrer les stats pour ce collecteur spécifique
    stats_collecteur = None
    for stat in stats_globales.get('top_collecteurs', []):
        if f"{stat['collecteur__nom']} {stat['collecteur__prenom']}" == collecteur.nom_complet:
            stats_collecteur = stat
            break
    
    context = {
        'collecteur': collecteur,
        'historique_journalier': historique_journalier,
        'historique_mensuel': historique_mensuel,
        'stats_collecteur': stats_collecteur,
        'date_debut': debut,
        'date_fin': fin,
        'annee': annee,
    }
    
    return render(request, 'market/historique_collecteur.html', context)


@login_required
def rapports_collecteurs(request):
    """Vue des rapports de tous les collecteurs"""
    # Récupérer les paramètres de filtrage
    debut = request.GET.get('debut')
    fin = request.GET.get('fin')
    type_rapport = request.GET.get('type', 'journalier')
    
    # Convertir les dates si fournies
    date_debut = None
    date_fin = None
    if debut:
        try:
            date_debut = datetime.strptime(debut, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Format de date de début invalide')
    
    if fin:
        try:
            date_fin = datetime.strptime(fin, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Format de date de fin invalide')
    
    # Récupérer les statistiques globales
    stats_globales = RapportCollecteurService.get_statistiques_globales_collecteurs(
        date_debut, date_fin
    )
    
    # Récupérer tous les collecteurs actifs
    collecteurs = Collecteur.objects.filter(actif=True)
    
    # Préparer les données pour chaque collecteur
    collecteurs_data = []
    for collecteur in collecteurs:
        # Dernier rapport journalier
        dernier_rapport_j = RapportJournalierCollecteur.objects.filter(
            collecteur=collecteur
        ).order_by('-date_rapport').first()
        
        # Dernier rapport mensuel
        dernier_rapport_m = RapportMensuelCollecteur.objects.filter(
            collecteur=collecteur
        ).order_by('-annee', '-mois').first()
        
        collecteurs_data.append({
            'collecteur': collecteur,
            'dernier_rapport_journalier': dernier_rapport_j,
            'dernier_rapport_mensuel': dernier_rapport_m,
        })
    
    context = {
        'collecteurs_data': collecteurs_data,
        'stats_globales': stats_globales,
        'date_debut': debut,
        'date_fin': fin,
        'type_rapport': type_rapport,
    }
    
    return render(request, 'market/rapports_collecteurs.html', context)


@login_required
@require_http_methods(['POST'])
def generer_rapport_collecteur(request, collecteur_id):
    """Génère un rapport pour un collecteur spécifique"""
    collecteur = get_object_or_404(Collecteur, id=collecteur_id)
    type_rapport = request.POST.get('type_rapport', 'journalier')
    
    try:
        if type_rapport == 'journalier':
            date_rapport = request.POST.get('date_rapport')
            if date_rapport:
                date_rapport = datetime.strptime(date_rapport, '%Y-%m-%d').date()
            else:
                date_rapport = timezone.now().date()
            
            rapport = RapportCollecteurService.generer_rapport_journalier(
                collecteur_id, date_rapport
            )
            messages.success(request, f'rapport journalier généré pour {date_rapport}')
            
        elif type_rapport == 'mensuel':
            annee = request.POST.get('annee')
            mois = request.POST.get('mois')
            
            if annee and mois:
                annee = int(annee)
                mois = int(mois)
            else:
                annee = timezone.now().year
                mois = timezone.now().month
            
            rapport = RapportCollecteurService.generer_rapport_mensuel(
                collecteur_id, annee, mois
            )
            messages.success(request, f'rapport mensuel généré pour {mois}/{annee}')
        
        else:
            messages.error(request, 'Type de rapport invalide')
            
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération du rapport: {str(e)}')
    
    # Rediriger vers la page d'historique du collecteur
    return redirect('historique_collecteur', collecteur_id=collecteur_id)


@login_required
@require_http_methods(['POST'])
def generer_rapports_tous_collecteurs(request):
    """Génère les rapports pour tous les collecteurs"""
    type_rapport = request.POST.get('type_rapport', 'journalier')
    
    try:
        if type_rapport == 'journalier':
            date_rapport = request.POST.get('date_rapport')
            if date_rapport:
                date_rapport = datetime.strptime(date_rapport, '%Y-%m-%d').date()
            else:
                date_rapport = timezone.now().date()
            
            rapports = RapportCollecteurService.generer_rapports_journaliers_tous_collecteurs(
                date_rapport
            )
            messages.success(request, f'{len(rapports)} rapports journaliers générés pour {date_rapport}')
            
        elif type_rapport == 'mensuel':
            annee = request.POST.get('annee')
            mois = request.POST.get('mois')
            
            if annee and mois:
                annee = int(annee)
                mois = int(mois)
            else:
                annee = timezone.now().year
                mois = timezone.now().month
            
            rapports = RapportCollecteurService.generer_rapports_mensuels_tous_collecteurs(
                annee, mois
            )
            messages.success(request, f'{len(rapports)} rapports mensuels générés pour {mois}/{annee}')
        
        else:
            messages.error(request, 'Type de rapport invalide')
            
    except Exception as e:
        messages.error(request, f'Erreur lors de la génération des rapports: {str(e)}')
    
    return redirect('rapports_collecteurs')


