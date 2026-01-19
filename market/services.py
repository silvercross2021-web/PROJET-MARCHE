"""
Services métier pour l'application market
"""
from django.db.models import Sum, Count, Q, F
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404
from datetime import datetime, timedelta, date
from decimal import Decimal
from .models import Commercant, Etal, Paiement, Ticket, HistoriqueAttribution, TaxeJournaliere, Collecteur, RapportJournalierCollecteur, RapportMensuelCollecteur


class DashboardService:
    """Service pour les statistiques du dashboard"""
    
    @staticmethod
    def get_total_collecte_aujourdhui():
        """Calcule le total collecté aujourd'hui (cache 5 minutes)"""
        from django.core.cache import cache
        
        aujourdhui = timezone.now().date()
        cache_key = f'dashboard_total_aujourdhui_{aujourdhui}'
        
        total = cache.get(cache_key)
        if total is None:
            total = Paiement.objects.filter(
                date_paiement__date=aujourdhui
            ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            cache.set(cache_key, total, 300)  # 5 minutes
        
        return total
    
    @staticmethod
    def get_comparaison_hier():
        """Compare la collecte d'aujourd'hui avec hier"""
        aujourdhui = timezone.now().date()
        hier = aujourdhui - timedelta(days=1)
        
        total_aujourdhui = Paiement.objects.filter(
            date_paiement__date=aujourdhui
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        total_hier = Paiement.objects.filter(
            date_paiement__date=hier
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        if total_hier == 0:
            pourcentage = 100.0 if total_aujourdhui > 0 else 0.0
        else:
            pourcentage = ((total_aujourdhui - total_hier) / total_hier) * 100
        
        return {
            'aujourdhui': total_aujourdhui,
            'hier': total_hier,
            'difference': total_aujourdhui - total_hier,
            'pourcentage': round(pourcentage, 1)
        }
    
    @staticmethod
    def get_commercants_en_retard():
        """Compte les commerçants en retard de paiement"""
        aujourdhui = timezone.now().date()
        return TaxeJournaliere.objects.filter(
            paye=False,
            statut='du',
            date__lt=aujourdhui,
        ).values('commercant').distinct().count()
    
    @staticmethod
    def get_top_commercants_retard(limit=5):
        """Retourne les top commerçants en retard"""
        from .models import Commercant
        
        aujourdhui = timezone.now().date()
        retards = TaxeJournaliere.objects.filter(
            paye=False,
            statut='du',
            date__lt=aujourdhui,
        ).values('commercant').annotate(
            total_retard=Sum('montant_attendu'),
            nombre_retards=Count('id'),
        ).order_by('-total_retard')[:limit]
        
        result = []
        for retard in retards:
            commercant = Commercant.objects.get(id=retard['commercant'])
            result.append({
                'commercant': commercant,
                'total_retard': retard['total_retard'],
                'nombre_retards': retard['nombre_retards']
            })
        
        return result
    
    @staticmethod
    def get_taux_occupation():
        """Calcule le taux d'occupation des étals (cache 5 minutes)"""
        from django.core.cache import cache
        
        cache_key = 'dashboard_taux_occupation'
        result = cache.get(cache_key)
        
        if result is None:
            total_etals = Etal.objects.count()
            etals_occupes = Etal.objects.filter(statut='occupe').count()
            if total_etals == 0:
                result = {
                    'taux': 0,
                    'total': 0,
                    'occupes': 0,
                    'libres': 0
                }
            else:
                result = {
                    'taux': round((etals_occupes / total_etals) * 100, 1),
                    'total': total_etals,
                    'occupes': etals_occupes,
                    'libres': total_etals - etals_occupes
                }
            cache.set(cache_key, result, 300)  # 5 minutes
        
        return result
    
    @staticmethod
    def get_collecte_mensuelle():
        """Calcule la collecte du mois en cours"""
        maintenant = timezone.now()
        total = Paiement.objects.filter(
            date_paiement__year=maintenant.year,
            date_paiement__month=maintenant.month
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        return total
    
    @staticmethod
    def get_comparaison_mois_precedent():
        """Compare la collecte du mois en cours avec le mois précédent"""
        maintenant = timezone.now()
        
        # Mois en cours
        total_mois_actuel = Paiement.objects.filter(
            date_paiement__year=maintenant.year,
            date_paiement__month=maintenant.month
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        # Mois précédent
        if maintenant.month == 1:
            mois_precedent = 12
            annee_precedente = maintenant.year - 1
        else:
            mois_precedent = maintenant.month - 1
            annee_precedente = maintenant.year
        
        total_mois_precedent = Paiement.objects.filter(
            date_paiement__year=annee_precedente,
            date_paiement__month=mois_precedent
        ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        if total_mois_precedent == 0:
            pourcentage = 100.0 if total_mois_actuel > 0 else 0.0
        else:
            pourcentage = ((total_mois_actuel - total_mois_precedent) / total_mois_precedent) * 100
        
        return {
            'mois_actuel': total_mois_actuel,
            'mois_precedent': total_mois_precedent,
            'difference': total_mois_actuel - total_mois_precedent,
            'pourcentage': round(pourcentage, 1)
        }
    
    @staticmethod
    def get_collection_journaliere():
        """Retourne la collection des 7 derniers jours (cache 10 minutes)"""
        from django.core.cache import cache
        
        aujourdhui = timezone.now().date()
        cache_key = f'dashboard_collection_journaliere_{aujourdhui}'
        
        result = cache.get(cache_key)
        if result is None:
            jours = []
            max_value = Decimal('0.00')
            
            for i in range(6, -1, -1):
                date = aujourdhui - timedelta(days=i)
                total = Paiement.objects.filter(
                    date_paiement__date=date
                ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
                
                if total > max_value:
                    max_value = total
                
                jours.append({
                    'date': date,
                    'total': total,
                    'jour_semaine': date.strftime('%A')[:3]
                })
            
            # Calculer la moyenne
            moyenne = sum(j['total'] for j in jours) / len(jours) if jours else Decimal('0.00')
            
            # Trouver le meilleur jour
            meilleur_jour = max(jours, key=lambda x: x['total'])
            
            result = {
                'jours': jours,
                'max_value': max_value,
                'moyenne': moyenne,
                'meilleur_jour': meilleur_jour
            }
            cache.set(cache_key, result, 600)  # 10 minutes
        
        return result
    
    @staticmethod
    def get_evolution_mensuelle():
        """Retourne l'évolution mensuelle des 6 derniers mois (cache 1 heure)"""
        from django.core.cache import cache
        
        maintenant = timezone.now()
        cache_key = f'dashboard_evolution_mensuelle_{maintenant.year}_{maintenant.month}'
        
        result = cache.get(cache_key)
        if result is None:
            mois = []
            max_value = Decimal('0.00')
            noms_mois = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                         'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            
            for i in range(5, -1, -1):
                # Calculer la date du mois
                mois_cible = maintenant.month - i
                annee_cible = maintenant.year
                
                while mois_cible <= 0:
                    mois_cible += 12
                    annee_cible -= 1
                
                total = Paiement.objects.filter(
                    date_paiement__year=annee_cible,
                    date_paiement__month=mois_cible
                ).aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
                
                if total > max_value:
                    max_value = total
                
                mois.append({
                    'mois': mois_cible,
                    'annee': annee_cible,
                    'nom_mois': noms_mois[mois_cible - 1],
                    'nom_court': noms_mois[mois_cible - 1][:3],
                    'total': total
                })
            
            # Calculer la moyenne
            moyenne = sum(m['total'] for m in mois) / len(mois) if mois else Decimal('0.00')
            
            # Calculer les points pour SVG (normalisés entre 0 et 100)
            for m in mois:
                if max_value > 0:
                    m['pourcentage'] = (m['total'] / max_value) * 100
                else:
                    m['pourcentage'] = 0
            
            result = {
                'mois': mois,
                'max_value': max_value,
                'moyenne': moyenne
            }
            cache.set(cache_key, result, 3600)  # 1 heure
        
        return result
    
    @staticmethod
    def get_alertes():
        """Retourne les alertes actives"""
        alertes = []
        maintenant = timezone.now().date()
        
        # Alerte 1: Commerçants en retard > 5
        commercants_retard = DashboardService.get_commercants_en_retard()
        if commercants_retard > 5:
            alertes.append({
                'type': 'danger',
                'titre': 'Commerçants en retard',
                'message': f'{commercants_retard} commerçants ont des paiements en retard',
                'action': 'Voir la liste'
            })
        
        # Alerte 2: Taux d'occupation < 50%
        taux_data = DashboardService.get_taux_occupation()
        if taux_data['taux'] < 50:
            alertes.append({
                'type': 'warning',
                'titre': 'Taux d\'occupation faible',
                'message': f'Seulement {taux_data["taux"]}% des étals sont occupés',
                'action': 'Voir les étals'
            })
        
        # Alerte 3: Tickets restants < 10%
        total_tickets = Ticket.objects.count()
        tickets_restants = Ticket.objects.filter(statut='disponible', utilise=False).count()
        if total_tickets > 0 and (tickets_restants / total_tickets) < 0.1:
            alertes.append({
                'type': 'warning',
                'titre': 'Stock de tickets faible',
                'message': f'Il ne reste que {tickets_restants} tickets ({round((tickets_restants/total_tickets)*100, 1)}%)',
                'action': 'Générer des tickets'
            })
        
        return alertes
    
    @staticmethod
    def get_activites_recentes(limit=10):
        """Retourne les activités récentes"""
        activites = []
        
        # Paiements récents
        paiements = Paiement.objects.select_related('commercant', 'etal').order_by('-date_paiement')[:limit]
        
        for paiement in paiements:
            temps_ecoule = timezone.now() - paiement.date_paiement
            if temps_ecoule.days > 0:
                temps_str = f"Il y a {temps_ecoule.days} jour(s)"
            elif temps_ecoule.seconds > 3600:
                heures = temps_ecoule.seconds // 3600
                temps_str = f"Il y a {heures} heure(s)"
            else:
                minutes = temps_ecoule.seconds // 60
                temps_str = f"Il y a {minutes} minute(s)" if minutes > 0 else "À l'instant"
            
            activites.append({
                'type': 'paiement',
                'icone': '💰',
                'titre': f'Paiement de {paiement.montant:.0f} FCFA',
                'description': f'{paiement.commercant.nom_complet}',
                'temps': temps_str,
                'date': paiement.date_paiement
            })
        
        return sorted(activites, key=lambda x: x['date'], reverse=True)[:limit]
    
    @staticmethod
    def get_repartition_paiements():
        """Retourne la répartition des paiements par mode"""
        aujourdhui = timezone.now().date()
        paiements = Paiement.objects.filter(date_paiement__date=aujourdhui)
        
        especes = paiements.filter(mode_paiement='especes').aggregate(
            total=Sum('montant'),
            nombre=Count('id')
        )
        
        mobile_money = paiements.filter(mode_paiement='mobile_money').aggregate(
            total=Sum('montant'),
            nombre=Count('id')
        )
        
        total = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        especes_total = especes['total'] or Decimal('0.00')
        mobile_money_total = mobile_money['total'] or Decimal('0.00')
        
        return {
            'especes': {
                'montant': especes_total,
                'nombre': especes['nombre'] or 0,
                'pourcentage': (especes_total / total * 100) if total > 0 else 0
            },
            'mobile_money': {
                'montant': mobile_money_total,
                'nombre': mobile_money['nombre'] or 0,
                'pourcentage': (mobile_money_total / total * 100) if total > 0 else 0
            },
            'total': total
        }


class PaiementService:
    """Service pour la gestion des paiements"""

    @staticmethod
    def calculer_taxe_journaliere(etal):
        """Calcule la taxe journalière selon la règle métier.

        - Si superficie < 50 m² => 500 FCFA
        - Si superficie >= 50 m² => 1000 FCFA
        """
        try:
            superficie = Decimal(str(etal.superficie))
        except Exception:
            superficie = Decimal('0')

        if superficie < Decimal('50'):
            return Decimal('500')
        return Decimal('1000')

    @staticmethod
    def get_resume_journalier(date=None):
        """Retourne le résumé des paiements du jour (pour la page de saisie)."""
        if date is None:
            date = timezone.now().date()

        paiements = Paiement.objects.filter(date_paiement__date=date)

        total = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        nombre = paiements.count()
        especes = paiements.filter(mode_paiement='especes').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        mobile_money = paiements.filter(mode_paiement='mobile_money').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')

        return {
            'total': total,
            'nombre': nombre,
            'especes': especes,
            'mobile_money': mobile_money,
        }

    @staticmethod
    def _annuler_ticket(ticket):
        """Annule un ticket (non réutilisable)."""
        if not ticket:
            return
        ticket.utilise = False
        ticket.statut = 'annule'
        ticket.date_utilisation = None
        ticket.save(update_fields=['utilise', 'statut', 'date_utilisation'])

    @staticmethod
    @transaction.atomic
    def enregistrer_paiement(commercant, montant, mode_paiement, etal=None, ticket=None, collecteur=None, user=None, date_paiement=None):
        """Enregistre un nouveau paiement de manière atomique (taxe journalière, pas de partiel)."""
        if not commercant.actif:
            raise ValueError("Le commerçant est inactif.")

        if etal is None:
            raise ValueError("Un étal est obligatoire pour enregistrer une taxe journalière.")

        if collecteur is None:
            raise ValueError("Le collecteur est obligatoire.")
        if isinstance(collecteur, int):
            collecteur = Collecteur.objects.filter(id=collecteur, actif=True).first()
        if not collecteur or not getattr(collecteur, 'actif', False):
            raise ValueError("Collecteur invalide ou inactif.")

        # 1. VALIDER LE TICKET AVANT DE CRÉER LE PAIEMENT
        if ticket:
            ticket.refresh_from_db()
            if ticket.statut != 'disponible' or ticket.utilise:
                raise ValueError("Ticket déjà utilisé ou non disponible.")
            if ticket.paiements.exists():
                raise ValueError("Ticket déjà lié à un paiement existant.")
            if not ticket.lot_id:
                raise ValueError("Ticket non attribué à un lot.")
            ticket.lot.refresh_from_db()
            if ticket.lot.statut != 'ouvert':
                raise ValueError("Lot de tickets clos.")
            if ticket.lot.collecteur_id != collecteur.id:
                raise ValueError("Ticket non attribué à ce collecteur.")
        else:
            raise ValueError("Un ticket est obligatoire.")

        # 2. VALIDER L'ÉTAL
        if etal.statut != 'occupe' or etal.commercant != commercant:
            raise ValueError("L'étal sélectionné n'est pas occupé par ce commerçant.")

        # 3. VALIDER LA TAXE JOURNALIÈRE (PAS DE PARTIEL)
        date_collecte = (date_paiement or timezone.now()).date()
        taxe = TaxeJournaliereService.get_or_create_taxe(date_collecte, etal)

        if taxe.statut == 'annule':
            raise ValueError("La taxe journalière est annulée pour cet étal à cette date.")
        if taxe.paye or taxe.paiement_id is not None:
            raise ValueError("La taxe journalière est déjà payée pour cet étal à cette date.")

        if Decimal(montant) != Decimal(taxe.montant_attendu):
            raise ValueError(f"Paiement partiel interdit. Montant attendu: {taxe.montant_attendu:.0f} FCFA")

        # 4. CRÉER LE PAIEMENT
        paiement = Paiement.objects.create(
            commercant=commercant,
            etal=etal,
            montant=montant,
            mode_paiement=mode_paiement,
            ticket=ticket,
            collecteur=collecteur,
            enregistre_par=user,
            date_paiement=date_paiement or timezone.now()
        )

        # 5. METTRE À JOUR LE TICKET
        ticket.utilise = True
        ticket.statut = 'utilise'
        ticket.date_utilisation = paiement.date_paiement
        ticket.save(update_fields=['utilise', 'statut', 'date_utilisation'])

        # 6. MARQUER LA TAXE DU JOUR COMME PAYÉE
        taxe.paye = True
        taxe.statut = 'paye'
        taxe.paiement = paiement
        taxe.save(update_fields=['paye', 'statut', 'paiement', 'date_mise_a_jour'])

        return paiement

    @staticmethod
    @transaction.atomic
    def modifier_paiement(paiement, nouveau_montant, nouveau_mode_paiement=None, nouveau_ticket=None):
        """Modifie un paiement existant (montant fixe, pas de partiel)."""

        if not paiement.etal_id:
            raise ValueError("Impossible de modifier: paiement sans étal.")

        montant_attendu = PaiementService.calculer_taxe_journaliere(paiement.etal)
        if Decimal(nouveau_montant) != Decimal(montant_attendu):
            raise ValueError(f"Paiement partiel interdit. Montant attendu: {montant_attendu:.0f} FCFA")

        ancien_ticket = paiement.ticket

        if nouveau_ticket:
            nouveau_ticket.refresh_from_db()
            if nouveau_ticket.statut != 'disponible' or nouveau_ticket.utilise:
                raise ValueError("Ticket déjà utilisé ou non disponible.")
            if nouveau_ticket.paiements.exists():
                raise ValueError("Ticket déjà lié à un paiement existant.")

            # Annuler l'ancien ticket (non réutilisable)
            if ancien_ticket:
                PaiementService._annuler_ticket(ancien_ticket)

            paiement.ticket = nouveau_ticket
            nouveau_ticket.utilise = True
            nouveau_ticket.statut = 'utilise'
            nouveau_ticket.date_utilisation = paiement.date_paiement
            nouveau_ticket.save(update_fields=['utilise', 'statut', 'date_utilisation'])

        paiement.montant = nouveau_montant
        if nouveau_mode_paiement and nouveau_mode_paiement != 'annuler_ticket':
            paiement.mode_paiement = nouveau_mode_paiement
        paiement.save()

        return paiement

    @staticmethod
    @transaction.atomic
    def annuler_paiement(paiement):
        """Annule un paiement (taxe repasse en dû, ticket annulé non réutilisable)."""

        ticket = paiement.ticket
        taxe = None
        try:
            taxe = paiement.taxe_journaliere
        except Exception:
            taxe = None

        if taxe:
            taxe.paye = False
            taxe.statut = 'du'
            taxe.paiement = None
            taxe.save(update_fields=['paye', 'statut', 'paiement', 'date_mise_a_jour'])

        if ticket:
            PaiementService._annuler_ticket(ticket)

        paiement_id = paiement.id
        paiement.delete()
        return paiement_id


class TaxeJournaliereService:
    """Service pour la génération et la mise à jour des taxes journalières."""

    @staticmethod
    def get_or_create_taxe(date, etal):
        montant_attendu = PaiementService.calculer_taxe_journaliere(etal)
        commercant = etal.commercant
        if commercant is None:
            raise ValueError("L'étal n'est pas attribué à un commerçant.")

        taxe, _ = TaxeJournaliere.objects.get_or_create(
            date=date,
            etal=etal,
            defaults={
                'commercant': commercant,
                'montant_attendu': montant_attendu,
                'paye': False,
                'statut': 'du',
            }
        )

        # Sécuriser les champs en cas de changement d'attribution / règle
        needs_save = False
        if taxe.commercant_id != commercant.id:
            taxe.commercant = commercant
            needs_save = True
        if taxe.montant_attendu != montant_attendu:
            taxe.montant_attendu = montant_attendu
            needs_save = True
        if needs_save:
            taxe.save(update_fields=['commercant', 'montant_attendu', 'date_mise_a_jour'])

        return taxe

    @staticmethod
    def generer_taxes_pour_date(date):
        """Crée les taxes journalières (statut dû) pour tous les étals occupés."""
        etals_occupes = Etal.objects.select_related('commercant').filter(statut='occupe', commercant__isnull=False)
        for etal in etals_occupes:
            TaxeJournaliereService.get_or_create_taxe(date=date, etal=etal)


class TicketService:
    """Service pour la gestion des tickets"""
    
    @staticmethod
    def generer_numero_ticket():
        """Génère un numéro de ticket unique"""
        dernier_ticket = Ticket.objects.order_by('-id').first()
        if dernier_ticket:
            try:
                numero = int(dernier_ticket.numero.split('-')[1])
            except:
                numero = 0
        else:
            numero = 0
        
        nouveau_numero = numero + 1
        return f"T-{nouveau_numero:06d}"
    
    @staticmethod
    def creer_ticket():
        """Crée un nouveau ticket"""
        numero = TicketService.generer_numero_ticket()
        return Ticket.objects.create(numero=numero)
    
    @staticmethod
    def generer_tickets_en_masse(quantite):
        """Génère plusieurs tickets en une fois"""
        tickets = []
        for _ in range(quantite):
            numero = TicketService.generer_numero_ticket()
            ticket = Ticket.objects.create(numero=numero)
            tickets.append(ticket)
        return tickets


class CommercantService:
    """Service pour la gestion des commerçants"""
    
    @staticmethod
    def get_statistiques_commercant(commercant):
        """Retourne les statistiques d'un commerçant"""
        paiements = Paiement.objects.filter(commercant=commercant)
        taxes_journalieres = TaxeJournaliere.objects.filter(commercant=commercant)
        
        total_paye = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        total_attendu = taxes_journalieres.aggregate(total=Sum('montant_attendu'))['total'] or Decimal('0.00')

        aujourdhui = timezone.now().date()
        paiements_en_retard = taxes_journalieres.filter(
            paye=False,
            statut='du',
            date__lt=aujourdhui,
        ).count()
        
        return {
            'total_paye': total_paye,
            'total_attendu': total_attendu,
            'paiements_en_retard': paiements_en_retard,
            'nombre_paiements': paiements.count(),
            'etals_occupes': commercant.etals.filter(statut='occupe').count(),
        }
    
    @staticmethod
    def get_historique_paiements(commercant, limite=50):
        """Retourne l'historique des paiements d'un commerçant"""
        return Paiement.objects.filter(commercant=commercant).order_by('-date_paiement')[:limite]


class EtalService:
    """Service pour la gestion des étals"""
    
    @staticmethod
    def attribuer_etal(etal, commercant, date_attribution=None, user=None):
        """Attribue un étal à un commerçant"""
        if not commercant.actif:
            raise ValueError("Le commerçant est inactif.")
        if etal.statut == 'occupe':
            raise ValueError("L'étal est déjà occupé")
        
        if date_attribution is None:
            date_attribution = timezone.now().date()
        
        # Clore l'historique en cours s'il existe
        HistoriqueAttribution.objects.filter(etal=etal, date_fin__isnull=True).update(date_fin=date_attribution)
        
        etal.commercant = commercant
        etal.statut = 'occupe'
        etal.date_attribution = date_attribution
        etal.save()

        HistoriqueAttribution.objects.create(
            etal=etal,
            commercant=commercant,
            date_debut=date_attribution,
            attribue_par=user,
        )
        
        return etal
    
    @staticmethod
    def liberer_etal(etal, user=None):
        """Libère un étal"""
        # Clore l'historique en cours
        HistoriqueAttribution.objects.filter(etal=etal, date_fin__isnull=True).update(
            date_fin=timezone.now().date(),
            attribue_par=user,
        )
        etal.commercant = None
        etal.statut = 'libre'
        etal.date_attribution = None
        etal.save()
        
        return etal
    
    @staticmethod
    def get_historique_attribution(etal):
        """Retourne l'historique d'attribution d'un étal"""
        # Pour l'instant, on retourne juste les informations actuelles
        # On pourrait créer un modèle HistoriqueAttribution pour un suivi complet
        return {
            'commercant_actuel': etal.commercant,
            'date_attribution': etal.date_attribution,
            'statut': etal.statut,
        }


class RapportService:
    """Service pour la génération de rapports complets"""
    
    @staticmethod
    def generer_rapport_personnalise(date_debut, date_fin):
        """Génère un rapport personnalisé complet pour une période donnée"""
        from django.db.models import Avg, Max, Min, Q
        from datetime import timedelta
        
        # Optimisation des requêtes
        paiements = Paiement.objects.select_related(
            'commercant', 'etal', 'etal__secteur', 'ticket'
        ).filter(
            date_paiement__date__gte=date_debut,
            date_paiement__date__lte=date_fin
        )
        
        # Statistiques générales
        total = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        nombre = paiements.count()
        especes = paiements.filter(mode_paiement='especes').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        mobile_money = paiements.filter(mode_paiement='mobile_money').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        
        # Statistiques avancées
        montant_moyen = paiements.aggregate(avg=Avg('montant'))['avg'] or Decimal('0.00')
        montant_max = paiements.aggregate(max=Max('montant'))['max'] or Decimal('0.00')
        montant_min = paiements.aggregate(min=Min('montant'))['min'] or Decimal('0.00')
        
        # Répartition par mode de paiement
        pourcentage_especes = (especes / total * 100) if total > 0 else Decimal('0.00')
        pourcentage_mobile = (mobile_money / total * 100) if total > 0 else Decimal('0.00')
        
        # Paiements par jour
        paiements_par_jour = paiements.extra(
            select={'jour': "DATE(date_paiement)"}
        ).values('jour').annotate(
            total=Sum('montant'),
            nombre=Count('id')
        ).order_by('jour')
        
        # Par commerçant (top 20)
        paiements_par_commercant = paiements.values(
            'commercant__nom', 'commercant__prenom', 'commercant__id'
        ).annotate(
            total=Sum('montant'),
            nombre=Count('id'),
            moyenne=Avg('montant')
        ).order_by('-total')[:20]
        
        # Par secteur
        paiements_par_secteur = paiements.filter(etal__isnull=False).values(
            'etal__secteur__nom', 'etal__secteur__id'
        ).annotate(
            total=Sum('montant'),
            nombre=Count('id'),
            moyenne=Avg('montant')
        ).order_by('-total')
        
        # Par étal (top 10)
        paiements_par_etal = paiements.filter(etal__isnull=False).values(
            'etal__numero', 'etal__secteur__nom', 'etal__id'
        ).annotate(
            total=Sum('montant'),
            nombre=Count('id')
        ).order_by('-total')[:10]
        
        # Retards journaliers dans la période
        retards = TaxeJournaliere.objects.select_related(
            'commercant', 'etal', 'etal__secteur'
        ).filter(
            date__gte=date_debut,
            date__lte=date_fin,
            paye=False,
            statut='du',
        )

        total_retards = retards.aggregate(total=Sum('montant_attendu'))['total'] or Decimal('0.00')
        nombre_retards = retards.count()

        retards_par_secteur = retards.values(
            'etal__secteur__nom'
        ).annotate(
            total=Sum('montant_attendu'),
            nombre=Count('id')
        ).order_by('-total')
        
        # Évolution quotidienne
        jours_ecoules = (date_fin - date_debut).days + 1
        moyenne_quotidienne = total / jours_ecoules if jours_ecoules > 0 else Decimal('0.00')
        
        # Paiements avec tickets
        paiements_avec_tickets = paiements.filter(ticket__isnull=False).count()
        paiements_sans_tickets = nombre - paiements_avec_tickets
        
        # Statistiques par type de commerce
        paiements_par_type_commerce = paiements.filter(commercant__isnull=False).values(
            'commercant__type_commerce'
        ).annotate(
            total=Sum('montant'),
            nombre=Count('id')
        ).order_by('-total')
        
        return {
            'date_debut': date_debut,
            'date_fin': date_fin,
            'jours_ecoules': jours_ecoules,
            # Totaux
            'total': total,
            'nombre': nombre,
            'especes': especes,
            'mobile_money': mobile_money,
            # Statistiques avancées
            'montant_moyen': montant_moyen,
            'montant_max': montant_max,
            'montant_min': montant_min,
            'moyenne_quotidienne': moyenne_quotidienne,
            'pourcentage_especes': pourcentage_especes,
            'pourcentage_mobile': pourcentage_mobile,
            # Répartitions
            'paiements_par_jour': paiements_par_jour,
            'paiements_par_commercant': paiements_par_commercant,
            'paiements_par_secteur': paiements_par_secteur,
            'paiements_par_etal': paiements_par_etal,
            'paiements_par_type_commerce': paiements_par_type_commerce,
            # Retards
            'total_retards': total_retards,
            'nombre_retards': nombre_retards,
            'retards': list(retards[:50]),  # Limiter à 50 pour l'affichage
            'retards_par_secteur': retards_par_secteur,
            # Tickets
            'paiements_avec_tickets': paiements_avec_tickets,
            'paiements_sans_tickets': paiements_sans_tickets,
        }
    
    @staticmethod
    def generer_rapport_hebdomadaire():
        """Génère un rapport hebdomadaire pour les 3 dernières semaines calendaires"""
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        maintenant = timezone.now()
        semaines = []
        
        # Calculer les 3 dernières semaines calendaires complètes
        for i in range(2, -1, -1):
            # Semaine actuelle commence le lundi
            jours_depuis_lundi = maintenant.weekday()
            lundi_semaine_actuelle = maintenant - timedelta(days=jours_depuis_lundi)
            
            # Aller en arrière de i semaines
            lundi_semaine = lundi_semaine_actuelle - timedelta(weeks=i+1)
            dimanche_semaine = lundi_semaine + timedelta(days=6)
            
            # Ajuster pour la semaine actuelle
            if i == -1:
                dimanche_semaine = maintenant.date()
            
            date_debut = lundi_semaine.date()
            date_fin = dimanche_semaine.date()
            
            paiements = Paiement.objects.select_related(
                'commercant', 'etal', 'etal__secteur'
            ).filter(
                date_paiement__date__gte=date_debut,
                date_paiement__date__lte=date_fin
            )
            
            total = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            nombre = paiements.count()
            especes = paiements.filter(mode_paiement='especes').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            mobile_money = paiements.filter(mode_paiement='mobile_money').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            
            retards = TaxeJournaliere.objects.filter(
                date__gte=date_debut,
                date__lte=date_fin,
                paye=False,
                statut='du',
            ).count()
            
            numero_semaine = lundi_semaine.isocalendar()[1]
            annee = lundi_semaine.year
            
            semaines.append({
                'date_debut': date_debut,
                'date_fin': date_fin,
                'periode': f'Semaine {numero_semaine} ({date_debut.strftime("%d/%m")} - {date_fin.strftime("%d/%m/%Y")})',
                'total': total,
                'nombre': nombre,
                'especes': especes,
                'mobile_money': mobile_money,
                'retards': retards,
                'moyenne_quotidienne': total / 7 if total > 0 else Decimal('0.00'),
            })
        
        return semaines
    
    @staticmethod
    def generer_rapport_mensuel():
        """Génère un rapport mensuel pour les 3 derniers mois calendaires"""
        from datetime import datetime
        from calendar import monthrange
        from django.utils import timezone
        
        maintenant = timezone.now()
        mois = []
        
        # Calculer les 3 derniers mois calendaires complets
        for i in range(2, -1, -1):
            # Calculer le mois (i+1 mois en arrière)
            mois_cible = maintenant.month - (i + 1)
            annee_cible = maintenant.year
            
            # Ajuster si on dépasse janvier
            while mois_cible <= 0:
                mois_cible += 12
                annee_cible -= 1
            
            # Premier jour du mois
            premier_jour = datetime(annee_cible, mois_cible, 1).date()
            
            # Dernier jour du mois
            if i == -1:
                # Mois actuel - jusqu'à aujourd'hui
                dernier_jour = maintenant.date()
            else:
                _, dernier_jour_mois = monthrange(annee_cible, mois_cible)
                dernier_jour = datetime(annee_cible, mois_cible, dernier_jour_mois).date()
            
            paiements = Paiement.objects.select_related(
                'commercant', 'etal', 'etal__secteur'
            ).filter(
                date_paiement__date__gte=premier_jour,
                date_paiement__date__lte=dernier_jour
            )
            
            total = paiements.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            nombre = paiements.count()
            especes = paiements.filter(mode_paiement='especes').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            mobile_money = paiements.filter(mode_paiement='mobile_money').aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
            
            retards = TaxeJournaliere.objects.filter(
                date__gte=premier_jour,
                date__lte=dernier_jour,
                paye=False,
                statut='du',
            ).count()
            
            noms_mois = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 
                        'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']
            
            jours_dans_mois = (dernier_jour - premier_jour).days + 1
            
            mois.append({
                'date_debut': premier_jour,
                'date_fin': dernier_jour,
                'periode': f'{noms_mois[premier_jour.month-1]} {premier_jour.year}',
                'total': total,
                'nombre': nombre,
                'especes': especes,
                'mobile_money': mobile_money,
                'retards': retards,
                'moyenne_quotidienne': total / jours_dans_mois if jours_dans_mois > 0 else Decimal('0.00'),
            })
        
        return mois


class AuditService:
    """Service pour l'audit et le logging des actions"""

    @staticmethod
    def _make_json_safe(value):
        from django.db.models import Model

        if value is None:
            return None
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, Model):
            return str(value)
        if isinstance(value, dict):
            return {str(k): AuditService._make_json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [AuditService._make_json_safe(v) for v in value]

        return value
    
    @staticmethod
    def log_action(user, action, model_name, object_id=None, object_repr='', 
                   changes=None, ip_address=None, user_agent='', status='success', message=''):
        """Enregistre une action dans le journal d'audit"""
        from .models import AuditLog
        
        try:
            safe_changes = AuditService._make_json_safe(changes or {})
            AuditLog.objects.create(
                user=user,
                action=action,
                model_name=model_name,
                object_id=object_id,
                object_repr=object_repr[:200],
                changes=safe_changes,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else '',
                status=status,
                message=message[:1000] if message else ''
            )
        except Exception as e:
            import logging
            logger = logging.getLogger('market.audit')
            logger.error(f"Erreur lors de l'enregistrement de l'audit: {str(e)}")
    
    @staticmethod
    def log_error(user, action, model_name, error_message, ip_address=None, user_agent=''):
        """Enregistre une erreur dans le journal d'audit"""
        AuditService.log_action(
            user=user,
            action=action,
            model_name=model_name,
            ip_address=ip_address,
            user_agent=user_agent,
            status='error',
            message=str(error_message)
        )
    
    @staticmethod
    def get_audit_trail(model_name=None, user=None, action=None, limit=100):
        """Récupère le journal d'audit avec filtres optionnels"""
        from .models import AuditLog
        
        queryset = AuditLog.objects.all()
        
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        if user:
            queryset = queryset.filter(user=user)
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset[:limit]
    
    @staticmethod
    def get_client_ip(request):
        """Récupère l'adresse IP du client depuis la requête"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class NotificationService:
    """Service pour la gestion des notifications"""
    
    @staticmethod
    def notifier_retard(user, taxe_journaliere):
        """Crée une notification pour un retard de taxe journalière"""
        from .models import Notification
        
        Notification.objects.create(
            user=user,
            type='retard',
            titre=f'Retard de paiement - {taxe_journaliere.commercant.nom_complet}',
            message=(
                f'La taxe journalière de {taxe_journaliere.montant_attendu:.0f} FCFA '
                f'pour {taxe_journaliere.commercant.nom_complet} (étal {taxe_journaliere.etal.numero}) '
                f'est en retard depuis le {taxe_journaliere.date.strftime("%d/%m/%Y")}.'
            ),
            lien=f'/commercants/{taxe_journaliere.commercant.id}/'
        )
    
    @staticmethod
    def notifier_attribution(user, etal, commercant):
        """Crée une notification pour une attribution d'étal"""
        from .models import Notification
        
        Notification.objects.create(
            user=user,
            type='attribution',
            titre=f'Attribution d\'étal - {etal.numero}',
            message=f'L\'étal {etal.numero} a été attribué à {commercant.nom_complet}.',
            lien=f'/etals/{etal.id}/'
        )
    
    @staticmethod
    def notifier_liberation(user, etal):
        """Crée une notification pour une libération d'étal"""
        from .models import Notification
        
        Notification.objects.create(
            user=user,
            type='liberation',
            titre=f'Libération d\'étal - {etal.numero}',
            message=f'L\'étal {etal.numero} a été libéré.',
            lien=f'/etals/{etal.id}/'
        )
    
    @staticmethod
    def notifier_paiement(user, paiement):
        """Crée une notification pour un nouveau paiement"""
        from .models import Notification
        
        Notification.objects.create(
            user=user,
            type='paiement',
            titre=f'Nouveau paiement - {paiement.commercant.nom_complet}',
            message=f'Un paiement de {paiement.montant:.0f} FCFA a été enregistré pour {paiement.commercant.nom_complet}.',
            lien=f'/paiements/'
        )
    
    @staticmethod
    def get_notifications_non_lues(user, limit=20):
        """Récupère les notifications non lues d'un utilisateur"""
        from .models import Notification
        
        return Notification.objects.filter(user=user, lue=False).order_by('-date_creation')[:limit]
    
    @staticmethod
    def get_count_notifications_non_lues(user):
        """Compte les notifications non lues d'un utilisateur"""
        from .models import Notification
        
        return Notification.objects.filter(user=user, lue=False).count()


class RapportCollecteurService:
    """Service pour la gestion des rapports des collecteurs"""
    
    @staticmethod
    def generer_rapport_journalier(collecteur_id, date_rapport=None):
        """Génère le rapport journalier pour un collecteur"""
        if date_rapport is None:
            date_rapport = timezone.now().date()
        
        collecteur = get_object_or_404(Collecteur, id=collecteur_id)
        
        # Paiements du jour pour ce collecteur
        paiements_jour = Paiement.objects.filter(
            collecteur=collecteur,
            date_paiement__date=date_rapport
        )
        
        # Tickets du jour pour ce collecteur
        tickets_jour = Ticket.objects.filter(
            lot__collecteur=collecteur,
            date_creation__date=date_rapport
        )
        
        # Statistiques des tickets
        tickets_utilises = tickets_jour.filter(statut='utilise').count()
        tickets_perdus_annules = tickets_jour.filter(statut__in=['annule', 'perdu']).count()
        tickets_restants = tickets_jour.filter(statut='disponible').count()
        
        # Calcul des montants
        total_montant = paiements_jour.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        nombre_paiements = paiements_jour.count()
        nombre_commercants = paiements_jour.values('commercant').distinct().count()
        
        # Création ou mise à jour du rapport
        rapport, created = RapportJournalierCollecteur.objects.update_or_create(
            collecteur=collecteur,
            date_rapport=date_rapport,
            defaults={
                'total_tickets_remis': tickets_jour.count(),
                'total_tickets_utilises': tickets_utilises,
                'total_tickets_perdus_annules': tickets_perdus_annules,
                'total_tickets_restants': tickets_restants,
                'total_montant_collecte': total_montant,
                'nombre_paiements': nombre_paiements,
                'nombre_commercants_distincts': nombre_commercants,
            }
        )
        
        return rapport
    
    @staticmethod
    def generer_rapports_journaliers_tous_collecteurs(date_rapport=None):
        """Génère les rapports journaliers pour tous les collecteurs actifs"""
        if date_rapport is None:
            date_rapport = timezone.now().date()
        
        rapports = []
        collecteurs = Collecteur.objects.filter(actif=True)
        
        for collecteur in collecteurs:
            rapport = RapportCollecteurService.generer_rapport_journalier(
                collecteur.id, date_rapport
            )
            rapports.append(rapport)
        
        return rapports
    
    @staticmethod
    def generer_rapport_mensuel(collecteur_id, annee=None, mois=None):
        """Génère le rapport mensuel pour un collecteur"""
        if annee is None:
            annee = timezone.now().year
        if mois is None:
            mois = timezone.now().month
        
        collecteur = get_object_or_404(Collecteur, id=collecteur_id)
        
        # Paiements du mois pour ce collecteur
        paiements_mois = Paiement.objects.filter(
            collecteur=collecteur,
            date_paiement__year=annee,
            date_paiement__month=mois
        )
        
        # Tickets du mois pour ce collecteur
        tickets_mois = Ticket.objects.filter(
            lot__collecteur=collecteur,
            date_creation__year=annee,
            date_creation__month=mois
        )
        
        # Statistiques des tickets
        tickets_utilises = tickets_mois.filter(statut='utilise').count()
        tickets_perdus_annules = tickets_mois.filter(statut__in=['annule', 'perdu']).count()
        tickets_restants = tickets_mois.filter(statut='disponible').count()
        
        # Calcul des montants
        total_montant = paiements_mois.aggregate(total=Sum('montant'))['total'] or Decimal('0.00')
        nombre_paiements = paiements_mois.count()
        nombre_commercants = paiements_mois.values('commercant').distinct().count()
        
        # Nombre de jours actifs (jours avec au moins un paiement)
        jours_actifs = paiements_mois.dates('date_paiement', 'day').count()
        
        # Moyenne journalière
        moyenne_journaliere = total_montant / jours_actifs if jours_actifs > 0 else Decimal('0.00')
        
        # Meilleur jour
        meilleur_jour_data = paiements_mois.values('date_paiement__date').annotate(
            total_jour=Sum('montant')
        ).order_by('-total_jour').first()
        
        meilleur_jour = None
        meilleur_jour_montant = Decimal('0.00')
        if meilleur_jour_data:
            meilleur_jour = meilleur_jour_data['date_paiement__date']
            meilleur_jour_montant = meilleur_jour_data['total_jour']
        
        # Création ou mise à jour du rapport
        rapport, created = RapportMensuelCollecteur.objects.update_or_create(
            collecteur=collecteur,
            annee=annee,
            mois=mois,
            defaults={
                'total_tickets_remis': tickets_mois.count(),
                'total_tickets_utilises': tickets_utilises,
                'total_tickets_perdus_annules': tickets_perdus_annules,
                'total_tickets_restants': tickets_restants,
                'total_montant_collecte': total_montant,
                'nombre_paiements': nombre_paiements,
                'nombre_commercants_distincts': nombre_commercants,
                'nombre_jours_actifs': jours_actifs,
                'moyenne_journaliere': moyenne_journaliere,
                'meilleur_jour': meilleur_jour,
                'meilleur_jour_montant': meilleur_jour_montant,
            }
        )
        
        return rapport
    
    @staticmethod
    def generer_rapports_mensuels_tous_collecteurs(annee=None, mois=None):
        """Génère les rapports mensuels pour tous les collecteurs actifs"""
        if annee is None:
            annee = timezone.now().year
        if mois is None:
            mois = timezone.now().month
        
        rapports = []
        collecteurs = Collecteur.objects.filter(actif=True)
        
        for collecteur in collecteurs:
            rapport = RapportCollecteurService.generer_rapport_mensuel(
                collecteur.id, annee, mois
            )
            rapports.append(rapport)
        
        return rapports
    
    @staticmethod
    def get_historique_journalier_collecteur(collecteur_id, debut=None, fin=None):
        """Récupère l'historique journalier d'un collecteur"""
        collecteur = get_object_or_404(Collecteur, id=collecteur_id)
        
        queryset = RapportJournalierCollecteur.objects.filter(
            collecteur=collecteur
        ).order_by('-date_rapport')
        
        if debut:
            queryset = queryset.filter(date_rapport__gte=debut)
        if fin:
            queryset = queryset.filter(date_rapport__lte=fin)
        
        return queryset
    
    @staticmethod
    def get_historique_mensuel_collecteur(collecteur_id, annee=None):
        """Récupère l'historique mensuel d'un collecteur"""
        collecteur = get_object_or_404(Collecteur, id=collecteur_id)
        
        queryset = RapportMensuelCollecteur.objects.filter(
            collecteur=collecteur
        ).order_by('-annee', '-mois')
        
        if annee:
            queryset = queryset.filter(annee=annee)
        
        return queryset
    
    @staticmethod
    def get_statistiques_globales_collecteurs(date_debut=None, date_fin=None):
        """Statistiques globales pour tous les collecteurs sur une période"""
        queryset = RapportJournalierCollecteur.objects.all()
        
        if date_debut:
            queryset = queryset.filter(date_rapport__gte=date_debut)
        if date_fin:
            queryset = queryset.filter(date_rapport__lte=date_fin)
        
        stats = queryset.aggregate(
            total_collecte=Sum('total_montant_collecte'),
            total_paiements=Sum('nombre_paiements'),
            total_tickets_utilises=Sum('total_tickets_utilises'),
            total_tickets_perdus_annules=Sum('total_tickets_perdus_annules'),
        )
        
        # Top collecteurs
        top_collecteurs = queryset.values('collecteur__nom', 'collecteur__prenom').annotate(
            total_collecte=Sum('total_montant_collecte'),
            total_paiements=Sum('nombre_paiements')
        ).order_by('-total_collecte')[:10]
        
        return {
            'stats_globales': stats,
            'top_collecteurs': top_collecteurs,
        }


