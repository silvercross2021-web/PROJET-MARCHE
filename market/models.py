from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from django.db.models import Q
import re
import json


class Secteur(models.Model):
    """Secteur du marché"""
    nom = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    tarif_par_defaut = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('5000.00'), 
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Tarif par défaut par m² en FCFA"
    )
    jour_echeance = models.IntegerField(
        default=31, 
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Jour du mois pour l'échéance (1-31, 31 = dernier jour du mois)"
    )
    
    class Meta:
        verbose_name = "Secteur"
        verbose_name_plural = "Secteurs"
        ordering = ['nom']
    
    def __str__(self):
        return self.nom


class Commercant(models.Model):
    """Commerçant du marché"""
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    contact = models.CharField(max_length=20)
    type_commerce = models.CharField(max_length=100)
    date_inscription = models.DateField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Commerçant"
        verbose_name_plural = "Commerçants"
        ordering = ['nom', 'prenom']
    
    def __str__(self):
        return f"{self.nom} {self.prenom}"
    
    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"


class Etal(models.Model):
    """Étal du marché"""
    STATUT_CHOICES = [
        ('libre', 'Libre'),
        ('occupe', 'Occupé'),
    ]
    
    numero = models.CharField(max_length=20, unique=True)
    secteur = models.ForeignKey(Secteur, on_delete=models.CASCADE, related_name='etals')
    superficie = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    tarif_par_metre_carre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                               help_text="Tarif spécifique par m² pour cet étal (optionnel)")
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='libre')
    commercant = models.ForeignKey(Commercant, on_delete=models.SET_NULL, null=True, blank=True, related_name='etals')
    date_attribution = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Étal"
        verbose_name_plural = "Étals"
        ordering = ['secteur', 'numero']
    
    def __str__(self):
        return f"{self.numero} - {self.secteur.nom}"


class HistoriqueAttribution(models.Model):
    """Historique des attributions d'étals"""
    etal = models.ForeignKey(Etal, on_delete=models.CASCADE, related_name='historique_attributions')
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name='historique_etals')
    date_debut = models.DateField()
    date_fin = models.DateField(null=True, blank=True)
    attribue_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='attributions_realisees')
    
    class Meta:
        verbose_name = "Historique d'attribution"
        verbose_name_plural = "Historique d'attribution"
        ordering = ['-date_debut']
    
    def __str__(self):
        return f"{self.etal.numero} -> {self.commercant.nom_complet} ({self.date_debut} - {self.date_fin or 'en cours'})"


class Collecteur(models.Model):
    """Collecteur de taxes (référencé pour la traçabilité des carnets)"""

    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    contact = models.CharField(max_length=20, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Collecteur"
        verbose_name_plural = "Collecteurs"
        ordering = ['nom', 'prenom']

    def __str__(self):
        return f"{self.nom} {self.prenom}"

    @property
    def nom_complet(self):
        return f"{self.nom} {self.prenom}"


class LotTickets(models.Model):
    """Carnet/Lot de tickets remis à un collecteur"""

    STATUT_CHOICES = [
        ('ouvert', 'Ouvert'),
        ('clos', 'Clos'),
    ]

    collecteur = models.ForeignKey(Collecteur, on_delete=models.PROTECT, related_name='lots')
    date_remise = models.DateField(default=timezone.now)
    remis_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='lots_remis')
    statut = models.CharField(max_length=10, choices=STATUT_CHOICES, default='ouvert')
    ticket_debut = models.CharField(max_length=20, null=True, blank=True)
    ticket_fin = models.CharField(max_length=20, null=True, blank=True)
    date_cloture = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Lot de tickets"
        verbose_name_plural = "Lots de tickets"
        ordering = ['-date_remise', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['collecteur'],
                condition=Q(statut='ouvert'),
                name='unique_lot_ouvert_par_collecteur',
            )
        ]

    def __str__(self):
        return f"Lot {self.id} - {self.collecteur.nom_complet}"

    @property
    def nb_remis(self):
        return self.tickets.count()

    @property
    def nb_utilises(self):
        return self.tickets.filter(statut='utilise').count()

    @property
    def nb_perdus_annules(self):
        return self.tickets.filter(statut__in=['annule', 'perdu']).count()

    @property
    def nb_restants(self):
        return self.tickets.filter(statut='disponible').count()

    @staticmethod
    def _parse_ticket_numero(numero):
        match = re.fullmatch(r"T-(\d{6})", (numero or '').strip())
        if not match:
            raise ValidationError("Format ticket invalide. Format attendu: T-000001")
        return int(match.group(1))

    def clean(self):
        if (self.ticket_debut and not self.ticket_fin) or (self.ticket_fin and not self.ticket_debut):
            raise ValidationError("La plage de tickets doit contenir un début et une fin.")

        if self.ticket_debut and self.ticket_fin:
            debut = self._parse_ticket_numero(self.ticket_debut)
            fin = self._parse_ticket_numero(self.ticket_fin)
            if fin < debut:
                raise ValidationError("La fin de plage doit être >= au début de plage.")

            numeros = [f"T-{i:06d}" for i in range(debut, fin + 1)]
            qs = Ticket.objects.filter(numero__in=numeros)
            if qs.count() != len(numeros):
                raise ValidationError("Plage incomplète: certains tickets n'existent pas.")

            conflit = qs.exclude(lot__isnull=True).exclude(lot_id=self.id if self.id else None).exists()
            if conflit:
                raise ValidationError("Plage déjà attribuée à un autre lot.")

        super().clean()

    def assigner_plage(self):
        if self.statut != 'ouvert':
            raise ValueError("Lot de tickets clos.")
        if not self.ticket_debut or not self.ticket_fin:
            raise ValueError("La plage de tickets est obligatoire.")

        debut = self._parse_ticket_numero(self.ticket_debut)
        fin = self._parse_ticket_numero(self.ticket_fin)
        if fin < debut:
            raise ValueError("La fin de plage doit être >= au début de plage.")

        numeros = [f"T-{i:06d}" for i in range(debut, fin + 1)]
        qs = Ticket.objects.filter(numero__in=numeros)
        if qs.count() != len(numeros):
            raise ValueError("Plage incomplète: certains tickets n'existent pas.")

        conflit = qs.exclude(lot__isnull=True).exclude(lot_id=self.id).exists()
        if conflit:
            raise ValueError("Plage déjà attribuée à un autre lot.")

        updated = qs.update(lot=self)
        if updated != len(numeros):
            raise ValueError("Assignation partielle détectée.")
        return updated


class Ticket(models.Model):
    """Ticket de paiement"""
    STATUT_CHOICES = [
        ('disponible', 'Disponible'),
        ('utilise', 'Utilisé'),
        ('annule', 'Annulé'),
        ('perdu', 'Perdu'),
    ]
    numero = models.CharField(max_length=20, unique=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_utilisation = models.DateTimeField(null=True, blank=True)
    utilise = models.BooleanField(default=False)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='disponible')
    lot = models.ForeignKey('LotTickets', on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets')
    motif = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Ticket"
        verbose_name_plural = "Tickets"
        ordering = ['-date_creation']
    
    def __str__(self):
        return self.numero

    def save(self, *args, **kwargs):
        # Synchroniser statut et booléen legacy
        if self.utilise:
            self.statut = 'utilise'
        elif self.statut == 'utilise':
            self.utilise = True
        elif self.statut == 'annule':
            self.utilise = False
        else:
            self.utilise = False
        super().save(*args, **kwargs)


class Paiement(models.Model):
    """Paiement effectué par un commerçant"""
    MODE_PAIEMENT_CHOICES = [
        ('especes', 'Espèces'),
        ('mobile_money', 'Mobile Money'),
    ]
    
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name='paiements')
    etal = models.ForeignKey(Etal, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements')
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    date_paiement = models.DateTimeField(default=timezone.now)
    mode_paiement = models.CharField(max_length=20, choices=MODE_PAIEMENT_CHOICES, default='especes')
    ticket = models.ForeignKey(Ticket, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements')
    collecteur = models.ForeignKey(Collecteur, on_delete=models.SET_NULL, null=True, blank=True, related_name='paiements')
    enregistre_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='paiements_enregistres')
    
    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-date_paiement']
        constraints = [
            models.UniqueConstraint(fields=['ticket'], name='unique_paiement_par_ticket')
        ]
    
    def __str__(self):
        return f"{self.commercant.nom_complet} - {self.montant} FCFA"


class TaxeJournaliere(models.Model):
    """Taxe journalière attendue/payantée pour un étal à une date donnée."""

    STATUT_CHOICES = [
        ('du', 'Dû'),
        ('paye', 'Payé'),
        ('annule', 'Annulé'),
    ]

    date = models.DateField()
    commercant = models.ForeignKey(Commercant, on_delete=models.CASCADE, related_name='taxes_journalieres')
    etal = models.ForeignKey(Etal, on_delete=models.CASCADE, related_name='taxes_journalieres')
    montant_attendu = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    paye = models.BooleanField(default=False)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='du')
    paiement = models.OneToOneField('Paiement', on_delete=models.SET_NULL, null=True, blank=True, related_name='taxe_journaliere')
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Taxe journalière"
        verbose_name_plural = "Taxes journalières"
        unique_together = ['date', 'etal']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['-date']),
            models.Index(fields=['etal', '-date']),
            models.Index(fields=['commercant', '-date']),
            models.Index(fields=['paye', '-date']),
        ]

    def __str__(self):
        return f"{self.date} - {self.etal.numero} - {self.montant_attendu:.0f}"

    @property
    def en_retard(self):
        from django.utils import timezone
        return (not self.paye) and (self.statut == 'du') and (self.date < timezone.now().date())


class AuditLog(models.Model):
    """Journal d'audit pour tracer toutes les actions"""
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('view', 'Consultation'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('export', 'Export'),
        ('import', 'Import'),
    ]
    
    STATUS_CHOICES = [
        ('success', 'Succès'),
        ('error', 'Erreur'),
        ('warning', 'Avertissement'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100, help_text="Nom du modèle concerné")
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_repr = models.CharField(max_length=200, blank=True)
    changes = models.JSONField(default=dict, blank=True, help_text="Changements effectués (ancien/nouveau)")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='success')
    message = models.TextField(blank=True, help_text="Message d'erreur ou description")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['model_name', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.model_name} - {self.timestamp}"


class Notification(models.Model):
    """Notifications pour les utilisateurs"""
    TYPE_CHOICES = [
        ('retard', 'Retard de paiement'),
        ('attribution', 'Attribution d\'étal'),
        ('liberation', 'Libération d\'étal'),
        ('paiement', 'Nouveau paiement'),
        ('alerte', 'Alerte'),
        ('info', 'Information'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    lue = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    lien = models.URLField(blank=True, help_text="URL optionnelle vers l'objet concerné")
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['user', '-date_creation']),
            models.Index(fields=['user', 'lue', '-date_creation']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.user.username}"
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        from django.utils import timezone
        self.lue = True
        self.date_lecture = timezone.now()
        self.save(update_fields=['lue', 'date_lecture'])


class RapportJournalierCollecteur(models.Model):
    """Rapport journalier pour chaque collecteur"""
    collecteur = models.ForeignKey(Collecteur, on_delete=models.CASCADE, related_name='rapports_journaliers')
    date_rapport = models.DateField()
    total_tickets_remis = models.IntegerField(default=0)
    total_tickets_utilises = models.IntegerField(default=0)
    total_tickets_perdus_annules = models.IntegerField(default=0)
    total_tickets_restants = models.IntegerField(default=0)
    total_montant_collecte = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    nombre_paiements = models.IntegerField(default=0)
    nombre_commercants_distincts = models.IntegerField(default=0)
    date_generation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Rapport journalier collecteur"
        verbose_name_plural = "Rapports journaliers collecteurs"
        unique_together = ['collecteur', 'date_rapport']
        ordering = ['-date_rapport', 'collecteur']
        indexes = [
            models.Index(fields=['collecteur', '-date_rapport']),
            models.Index(fields=['-date_rapport']),
        ]
    
    def __str__(self):
        return f"Rapport {self.collecteur.nom_complet} - {self.date_rapport}"
    
    @property
    def taux_utilisation_tickets(self):
        if self.total_tickets_remis == 0:
            return 0
        return round((self.total_tickets_utilises / self.total_tickets_remis) * 100, 1)
    
    @property
    def montant_moyen_paiement(self):
        if self.nombre_paiements == 0:
            return Decimal('0.00')
        return self.total_montant_collecte / self.nombre_paiements


class RapportMensuelCollecteur(models.Model):
    """Rapport mensuel pour chaque collecteur"""
    collecteur = models.ForeignKey(Collecteur, on_delete=models.CASCADE, related_name='rapports_mensuels')
    annee = models.IntegerField()
    mois = models.IntegerField()
    total_tickets_remis = models.IntegerField(default=0)
    total_tickets_utilises = models.IntegerField(default=0)
    total_tickets_perdus_annules = models.IntegerField(default=0)
    total_tickets_restants = models.IntegerField(default=0)
    total_montant_collecte = models.DecimalField(max_digits=15, decimal_places=2, default=Decimal('0.00'))
    nombre_paiements = models.IntegerField(default=0)
    nombre_commercants_distincts = models.IntegerField(default=0)
    nombre_jours_actifs = models.IntegerField(default=0)
    moyenne_journaliere = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    meilleur_jour = models.DateField(null=True, blank=True)
    meilleur_jour_montant = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    date_generation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Rapport mensuel collecteur"
        verbose_name_plural = "Rapports mensuels collecteurs"
        unique_together = ['collecteur', 'annee', 'mois']
        ordering = ['-annee', '-mois', 'collecteur']
        indexes = [
            models.Index(fields=['collecteur', '-annee', '-mois']),
            models.Index(fields=['-annee', '-mois']),
        ]
    
    def __str__(self):
        return f"Rapport {self.collecteur.nom_complet} - {self.mois}/{self.annee}"
    
    @property
    def taux_utilisation_tickets(self):
        if self.total_tickets_remis == 0:
            return 0
        return round((self.total_tickets_utilises / self.total_tickets_remis) * 100, 1)
    
    @property
    def montant_moyen_paiement(self):
        if self.nombre_paiements == 0:
            return Decimal('0.00')
        return self.total_montant_collecte / self.nombre_paiements
    
    @property
    def performance_moyenne_journaliere(self):
        if self.nombre_jours_actifs == 0:
            return Decimal('0.00')
        return self.total_montant_collecte / self.nombre_jours_actifs


