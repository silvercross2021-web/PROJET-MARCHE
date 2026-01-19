from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group


class Command(BaseCommand):
    help = "Crée/met à jour un utilisateur dans le groupe ResponsableMairie"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, required=True)
        parser.add_argument("--password", type=str, required=True)

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]

        group, _ = Group.objects.get_or_create(name="ResponsableMairie")

        user, created = User.objects.get_or_create(username=username)
        user.set_password(password)
        user.is_active = True
        user.save()

        user.groups.add(group)

        if created:
            self.stdout.write(self.style.SUCCESS(f"[OK] Utilisateur créé: {username} (ResponsableMairie)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK] Utilisateur mis à jour: {username} (ResponsableMairie)"))
