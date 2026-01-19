"""
Formulaires Django pour l'application market
"""
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from decimal import Decimal
from .models import Commercant, Etal, Paiement, Ticket, Secteur
from .exceptions import CommercantInactifException, EtalDejaOccupeException, TicketDejaUtiliseException


class CommercantForm(forms.ModelForm):
    """Formulaire pour créer/modifier un commerçant"""
    
    class Meta:
        model = Commercant
        fields = ['nom', 'prenom', 'contact', 'type_commerce', 'actif']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'prenom': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'type_commerce': forms.TextInput(attrs={'class': 'form-control'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nom': 'Nom',
            'prenom': 'Prénom',
            'contact': 'Contact',
            'type_commerce': 'Type de commerce',
            'actif': 'Actif',
        }
    
    def clean_contact(self):
        contact = self.cleaned_data.get('contact')
        if contact and len(contact) < 8:
            raise ValidationError('Le contact doit contenir au moins 8 caractères.')
        return contact


class EtalForm(forms.ModelForm):
    """Formulaire pour créer/modifier un étal"""
    
    class Meta:
        model = Etal
        fields = ['numero', 'secteur', 'superficie', 'tarif_par_metre_carre', 'statut']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control', 'required': True}),
            'secteur': forms.Select(attrs={'class': 'form-control', 'required': True}),
            'superficie': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01', 'required': True}),
            'tarif_par_metre_carre': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'numero': 'Numéro',
            'secteur': 'Secteur',
            'superficie': 'Superficie (m²)',
            'tarif_par_metre_carre': 'Tarif par m² (FCFA)',
            'statut': 'Statut',
        }
    
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero:
            # Vérifier l'unicité
            qs = Etal.objects.filter(numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ce numéro d\'étal existe déjà.')
        return numero


class PaiementForm(forms.Form):
    """Formulaire pour enregistrer un paiement"""
    
    commercant_id = forms.IntegerField(widget=forms.HiddenInput())
    mode_paiement = forms.ChoiceField(
        choices=Paiement.MODE_PAIEMENT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'required': True}),
        label='Mode de paiement'
    )
    ticket_numero = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'required': True, 'placeholder': 'Ex: T-000123'}),
        label='Numéro de ticket'
    )
    etal_id = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Étal'
    )
    date_paiement = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        label='Date de paiement (optionnel)'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        pass
    
    def clean_commercant_id(self):
        commercant_id = self.cleaned_data.get('commercant_id')
        try:
            commercant = Commercant.objects.get(id=commercant_id)
            if not commercant.actif:
                raise ValidationError('Le commerçant est inactif. Impossible d\'enregistrer un paiement.')
            return commercant_id
        except Commercant.DoesNotExist:
            raise ValidationError('Commerçant introuvable.')
    
    def clean_ticket_numero(self):
        ticket_numero = (self.cleaned_data.get('ticket_numero') or '').strip()
        if not ticket_numero:
            raise ValidationError('Le numéro de ticket est obligatoire.')

        try:
            ticket = Ticket.objects.get(numero=ticket_numero)
        except Ticket.DoesNotExist:
            raise ValidationError('Ticket introuvable.')

        if ticket.statut != 'disponible' or ticket.utilise:
            raise ValidationError('Le ticket est déjà utilisé ou non disponible.')
        if ticket.paiements.exists():
            raise ValidationError('Le ticket est déjà lié à un paiement existant.')

        return ticket_numero
    
    def clean_etal_id(self):
        etal_id = self.cleaned_data.get('etal_id')
        commercant_id = self.cleaned_data.get('commercant_id')
        
        if etal_id and commercant_id:
            try:
                commercant = Commercant.objects.get(id=commercant_id)
                etal = Etal.objects.get(id=etal_id)
                if etal.statut != 'occupe' or etal.commercant != commercant:
                    raise ValidationError('L\'étal sélectionné n\'est pas occupé par ce commerçant.')
                return etal_id
            except (Etal.DoesNotExist, Commercant.DoesNotExist):
                raise ValidationError('Étal ou commerçant introuvable.')
        return etal_id


class TicketForm(forms.ModelForm):
    """Formulaire pour créer/modifier un ticket"""
    
    class Meta:
        model = Ticket
        fields = ['numero', 'statut']
        widgets = {
            'numero': forms.TextInput(attrs={'class': 'form-control'}),
            'statut': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'numero': 'Numéro',
            'statut': 'Statut',
        }
    
    def clean_numero(self):
        numero = self.cleaned_data.get('numero')
        if numero:
            # Vérifier l'unicité
            qs = Ticket.objects.filter(numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ce numéro de ticket existe déjà.')
        return numero


class CommercantSearchForm(forms.Form):
    """Formulaire de recherche de commerçant"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher par nom, prénom, contact...'
        }),
        label='Recherche'
    )


class RapportFilterForm(forms.Form):
    """Formulaire de filtrage pour les rapports"""
    
    type_rapport = forms.ChoiceField(
        choices=[
            ('hebdomadaire', 'Hebdomadaire'),
            ('mensuel', 'Mensuel'),
            ('personnalise', 'Personnalisé'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Type de rapport'
    )
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date de début'
    )
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        label='Date de fin'
    )
    
    def clean(self):
        cleaned_data = super().clean()
        type_rapport = cleaned_data.get('type_rapport')
        date_debut = cleaned_data.get('date_debut')
        date_fin = cleaned_data.get('date_fin')
        
        if type_rapport == 'personnalise':
            if not date_debut or not date_fin:
                raise ValidationError('Les dates de début et de fin sont requises pour un rapport personnalisé.')
            if date_fin < date_debut:
                raise ValidationError('La date de fin doit être postérieure à la date de début.')
        
        return cleaned_data

