"""
Commande Django pour créer les groupes et permissions
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from market.models import Commercant, Etal, Paiement, Ticket, TaxeJournaliere, Collecteur, LotTickets


class Command(BaseCommand):
    help = 'Crée les groupes d\'utilisateurs et leurs permissions'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Création des groupes et permissions...'))
        
        # Permissions pour chaque modèle
        content_types = {
            'commercant': ContentType.objects.get_for_model(Commercant),
            'etal': ContentType.objects.get_for_model(Etal),
            'paiement': ContentType.objects.get_for_model(Paiement),
            'ticket': ContentType.objects.get_for_model(Ticket),
            'taxe_journaliere': ContentType.objects.get_for_model(TaxeJournaliere),
            'collecteur': ContentType.objects.get_for_model(Collecteur),
            'lottickets': ContentType.objects.get_for_model(LotTickets),
        }
        
        # Groupe Administrateur - Toutes les permissions
        admin_group, created = Group.objects.get_or_create(name='Administrateur')
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Groupe Administrateur créé'))
        
        # Donner toutes les permissions
        for ct in content_types.values():
            permissions = Permission.objects.filter(content_type=ct)
            admin_group.permissions.add(*permissions)

        # Groupe ResponsableMairie - mêmes permissions que l'Administrateur (sans accès au /admin)
        responsable_group, created = Group.objects.get_or_create(name='ResponsableMairie')
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Groupe ResponsableMairie créé'))

        for ct in content_types.values():
            permissions = Permission.objects.filter(content_type=ct)
            responsable_group.permissions.add(*permissions)
        
        # Groupe Gestionnaire - CRUD complet sauf suppression
        gestionnaire_group, created = Group.objects.get_or_create(name='Gestionnaire')
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Groupe Gestionnaire créé'))
        
        # Permissions pour Gestionnaire
        for model_name, ct in content_types.items():
            # Add, change, view (pas delete)
            permissions = Permission.objects.filter(
                content_type=ct,
                codename__in=['add_' + model_name, 'change_' + model_name, 'view_' + model_name]
            )
            gestionnaire_group.permissions.add(*permissions)
        
        # Groupe Caissier - Créer/modifier paiements, voir tickets
        caissier_group, created = Group.objects.get_or_create(name='Caissier')
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Groupe Caissier créé'))
        
        # Permissions pour Caissier
        # Paiements : add, change, view
        paiement_perms = Permission.objects.filter(
            content_type=content_types['paiement'],
            codename__in=['add_paiement', 'change_paiement', 'view_paiement']
        )
        caissier_group.permissions.add(*paiement_perms)
        
        # Tickets : view
        ticket_perms = Permission.objects.filter(
            content_type=content_types['ticket'],
            codename='view_ticket'
        )
        caissier_group.permissions.add(*ticket_perms)
        
        # Commerçants : view (pour rechercher)
        commercant_perms = Permission.objects.filter(
            content_type=content_types['commercant'],
            codename='view_commercant'
        )
        caissier_group.permissions.add(*commercant_perms)
        
        # Étals : view (pour voir les étals occupés)
        etal_perms = Permission.objects.filter(
            content_type=content_types['etal'],
            codename='view_etal'
        )
        caissier_group.permissions.add(*etal_perms)
        
        # Groupe Lecteur - Lecture seule
        lecteur_group, created = Group.objects.get_or_create(name='Lecteur')
        if created:
            self.stdout.write(self.style.SUCCESS('  [OK] Groupe Lecteur créé'))
        
        # Permissions pour Lecteur (view seulement)
        for ct in content_types.values():
            permissions = Permission.objects.filter(
                content_type=ct,
                codename__startswith='view_'
            )
            lecteur_group.permissions.add(*permissions)
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Groupes et permissions créés avec succès!'))
        self.stdout.write(self.style.WARNING('\nNote: Assurez-vous d\'assigner les utilisateurs aux groupes appropriés via l\'admin Django.'))

