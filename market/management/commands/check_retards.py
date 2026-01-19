"""
Commande Django pour vérifier les retards de paiement et créer des notifications
À exécuter quotidiennement via cron
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from market.models import TaxeJournaliere, Notification
from market.services import NotificationService


class Command(BaseCommand):
    help = 'Vérifie les retards de paiement et crée des notifications pour les gestionnaires'

    def add_arguments(self, parser):
        parser.add_argument(
            '--notify-all',
            action='store_true',
            help='Notifier tous les utilisateurs (pas seulement les gestionnaires)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Vérification des retards de paiement...'))
        
        aujourdhui = timezone.now().date()
        
        # Récupérer toutes les taxes journalières en retard
        retards = TaxeJournaliere.objects.filter(
            paye=False,
            statut='du',
            date__lt=aujourdhui
        ).select_related('commercant', 'etal')
        
        count_retards = retards.count()
        self.stdout.write(f'  {count_retards} paiement(s) en retard trouvé(s)')
        
        if count_retards == 0:
            self.stdout.write(self.style.SUCCESS('Aucun retard à signaler.'))
            return
        
        # Récupérer les utilisateurs à notifier
        if options['notify_all']:
            users_to_notify = User.objects.filter(is_active=True)
        else:
            # Notifier seulement les gestionnaires et administrateurs
            from django.contrib.auth.models import Group
            gestionnaire_group = Group.objects.filter(name__in=['Gestionnaire', 'Administrateur']).first()
            if gestionnaire_group:
                users_to_notify = gestionnaire_group.user_set.filter(is_active=True)
            else:
                # Si les groupes n'existent pas, notifier tous les utilisateurs actifs
                users_to_notify = User.objects.filter(is_active=True)
        
        notifications_created = 0
        
        # Créer une notification pour chaque utilisateur concerné
        for user in users_to_notify:
            # Créer une notification globale pour les retards
            retards_count = retards.count()
            Notification.objects.create(
                user=user,
                type='retard',
                titre=f'{retards_count} paiement(s) en retard',
                message=f'Il y a {retards_count} taxe(s) journalière(s) en retard nécessitant votre attention.',
                lien='/commercants/'
            )
            notifications_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'  {notifications_created} notification(s) créée(s) pour {users_to_notify.count()} utilisateur(s)'
            )
        )
        
        # Afficher les détails des retards
        self.stdout.write('\nDétails des retards:')
        for retard in retards[:10]:  # Limiter à 10 pour l'affichage
            jours_retard = (aujourdhui - retard.date).days
            self.stdout.write(
                f'  - {retard.commercant.nom_complet} ({retard.etal.numero}): '
                f'{retard.montant_attendu:.0f} FCFA en retard depuis {jours_retard} jour(s)'
            )
        
        if count_retards > 10:
            self.stdout.write(f'  ... et {count_retards - 10} autre(s) retard(s)')
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Vérification terminée!'))

