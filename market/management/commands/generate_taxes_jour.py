from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime

from market.services import TaxeJournaliereService


class Command(BaseCommand):
    help = "Génère les taxes journalières (TaxeJournaliere) pour une date donnée"

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            type=str,
            default=None,
            help="Date au format YYYY-MM-DD (par défaut: aujourd'hui)",
        )

    def handle(self, *args, **options):
        date_str = options.get("date")
        if date_str:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except Exception:
                raise ValueError("Format invalide pour --date. Utilise YYYY-MM-DD")
        else:
            target_date = timezone.now().date()

        TaxeJournaliereService.generer_taxes_pour_date(target_date)
        self.stdout.write(self.style.SUCCESS(f"[OK] Taxes journalières générées pour {target_date}"))
