from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal

from market.models import Secteur, Commercant, Etal, Ticket
from market.services import TicketService, TaxeJournaliereService


class Command(BaseCommand):
    help = 'Initialise les données de base pour l\'application'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initialisation des données...'))
        
        # Créer les secteurs
        secteurs_data = [
            {'nom': 'Secteur A', 'description': 'Fruits et légumes'},
            {'nom': 'Secteur B', 'description': 'Poisson frais'},
            {'nom': 'Secteur C', 'description': 'Viande'},
            {'nom': 'Secteur D', 'description': 'Textile et autres'},
        ]
        
        for secteur_data in secteurs_data:
            secteur, created = Secteur.objects.get_or_create(
                nom=secteur_data['nom'],
                defaults=secteur_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Secteur cree: {secteur.nom}'))
        
        # Créer les commerçants
        commercants_data = [
            {'nom': 'Kouassi', 'prenom': 'Adjoua', 'contact': '+225 07 12 34 56 78', 'type_commerce': 'Fruits et Légumes'},
            {'nom': 'Bamba', 'prenom': 'Seydou', 'contact': '+225 05 98 76 54 32', 'type_commerce': 'Poisson Frais'},
            {'nom': 'Traoré', 'prenom': 'Fatou', 'contact': '+225 01 23 45 67 89', 'type_commerce': 'Viande'},
            {'nom': 'Yao', 'prenom': 'Marie', 'contact': '+225 07 88 99 00 11', 'type_commerce': 'Épices'},
            {'nom': 'Koné', 'prenom': 'Ibrahim', 'contact': '+225 05 44 55 66 77', 'type_commerce': 'Textile'},
            {'nom': 'Koffi', 'prenom': 'Jean', 'contact': '+225 06 11 22 33 44', 'type_commerce': 'Fruits et Légumes'},
        ]
        
        for comm_data in commercants_data:
            commercant, created = Commercant.objects.get_or_create(
                nom=comm_data['nom'],
                prenom=comm_data['prenom'],
                defaults=comm_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Commercant cree: {commercant.nom_complet}'))
        
        # Créer les étals
        etals_data = [
            {'numero': 'A-001', 'secteur': 'Secteur A', 'superficie': 12, 'statut': 'occupe', 'commercant': 'Kouassi Adjoua'},
            {'numero': 'A-002', 'secteur': 'Secteur A', 'superficie': 10, 'statut': 'libre'},
            {'numero': 'A-003', 'secteur': 'Secteur A', 'superficie': 8, 'statut': 'occupe', 'commercant': 'Yao Marie'},
            {'numero': 'A-004', 'secteur': 'Secteur A', 'superficie': 12, 'statut': 'libre'},
            {'numero': 'A-045', 'secteur': 'Secteur A', 'superficie': 15, 'statut': 'occupe', 'commercant': 'Kouassi Adjoua'},
            {'numero': 'A-078', 'secteur': 'Secteur A', 'superficie': 10, 'statut': 'occupe', 'commercant': 'Yao Marie'},
            {'numero': 'B-001', 'secteur': 'Secteur B', 'superficie': 15, 'statut': 'occupe', 'commercant': 'Bamba Seydou'},
            {'numero': 'B-002', 'secteur': 'Secteur B', 'superficie': 15, 'statut': 'libre'},
            {'numero': 'B-023', 'secteur': 'Secteur B', 'superficie': 18, 'statut': 'occupe', 'commercant': 'Bamba Seydou'},
            {'numero': 'C-001', 'secteur': 'Secteur C', 'superficie': 20, 'statut': 'occupe', 'commercant': 'Traoré Fatou'},
            {'numero': 'C-002', 'secteur': 'Secteur C', 'superficie': 18, 'statut': 'libre'},
            {'numero': 'C-012', 'secteur': 'Secteur C', 'superficie': 22, 'statut': 'occupe', 'commercant': 'Traoré Fatou'},
            {'numero': 'D-001', 'secteur': 'Secteur D', 'superficie': 25, 'statut': 'occupe', 'commercant': 'Koné Ibrahim'},
            {'numero': 'D-002', 'secteur': 'Secteur D', 'superficie': 22, 'statut': 'libre'},
            {'numero': 'D-089', 'secteur': 'Secteur D', 'superficie': 28, 'statut': 'occupe', 'commercant': 'Koné Ibrahim'},
        ]
        
        for etal_data in etals_data:
            secteur = Secteur.objects.get(nom=etal_data['secteur'])
            commercant = None
            if 'commercant' in etal_data:
                nom, prenom = etal_data['commercant'].split(' ', 1)
                commercant = Commercant.objects.filter(nom=nom, prenom=prenom).first()
            
            etal, created = Etal.objects.get_or_create(
                numero=etal_data['numero'],
                defaults={
                    'secteur': secteur,
                    'superficie': Decimal(str(etal_data['superficie'])),
                    'statut': etal_data['statut'],
                    'commercant': commercant,
                    'date_attribution': date.today() if commercant else None,
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Etal cree: {etal.numero}'))
        
        # Créer des tickets
        for i in range(1, 101):
            numero = f"T-{i:06d}"
            ticket, created = Ticket.objects.get_or_create(numero=numero)
            if created and i <= 10:
                self.stdout.write(self.style.SUCCESS(f'  [OK] Ticket cree: {ticket.numero}'))

        # Créer les taxes journalières pour aujourd'hui (tous les étals occupés)
        TaxeJournaliereService.generer_taxes_pour_date(timezone.now().date())
        self.stdout.write(self.style.SUCCESS('  [OK] Taxes journalières générées pour aujourd\'hui'))
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Initialisation terminee avec succes!'))


