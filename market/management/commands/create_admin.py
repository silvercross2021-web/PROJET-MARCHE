from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Crée l\'utilisateur admin s\'il n\'existe pas, ou réinitialise son mot de passe'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-password',
            action='store_true',
            help='Réinitialise le mot de passe même si l\'utilisateur existe déjà',
        )

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin123'
        email = 'admin@treichville.ci'
        
        # Vérifier si l'utilisateur existe
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_superuser': True,
                'is_staff': True,
                'is_active': True
            }
        )
        
        if created:
            # Utilisateur créé
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'[OK] Utilisateur "{username}" cree avec succes!\n'
                    f'  Username: {username}\n'
                    f'  Password: {password}'
                )
            )
        else:
            # Utilisateur existe déjà
            if options['reset_password']:
                # Réinitialiser le mot de passe
                user.set_password(password)
                user.email = email
                user.is_superuser = True
                user.is_staff = True
                user.is_active = True
                user.save()
                self.stdout.write(
                    self.style.WARNING(
                        f'[INFO] Utilisateur "{username}" existe deja. Mot de passe reinitialise.\n'
                        f'  Username: {username}\n'
                        f'  Password: {password}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'[INFO] Utilisateur "{username}" existe deja.\n'
                        f'  Pour reinitialiser le mot de passe, utilisez: --reset-password'
                    )
                )

