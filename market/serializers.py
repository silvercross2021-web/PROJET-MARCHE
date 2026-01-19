"""
Serializers pour l'API REST
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Secteur, Commercant, Etal, Ticket, Paiement, 
    HistoriqueAttribution, AuditLog, Notification, TaxeJournaliere
)


class SecteurSerializer(serializers.ModelSerializer):
    """Serializer pour Secteur"""
    
    class Meta:
        model = Secteur
        fields = ['id', 'nom', 'description', 'tarif_par_defaut', 'jour_echeance']


class CommercantSerializer(serializers.ModelSerializer):
    """Serializer pour Commercant"""
    nom_complet = serializers.ReadOnlyField()
    etals_occupes = serializers.SerializerMethodField()
    
    class Meta:
        model = Commercant
        fields = [
            'id', 'nom', 'prenom', 'nom_complet', 'contact', 
            'type_commerce', 'date_inscription', 'actif', 'etals_occupes'
        ]
    
    def get_etals_occupes(self, obj):
        """Retourne les numéros des étals occupés"""
        return [etal.numero for etal in obj.etals.filter(statut='occupe')]


class EtalSerializer(serializers.ModelSerializer):
    """Serializer pour Etal"""
    secteur_nom = serializers.CharField(source='secteur.nom', read_only=True)
    commercant_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Etal
        fields = [
            'id', 'numero', 'secteur', 'secteur_nom', 'superficie',
            'tarif_par_metre_carre', 'statut', 'commercant', 'commercant_nom',
            'date_attribution'
        ]
    
    def get_commercant_nom(self, obj):
        """Retourne le nom complet du commerçant"""
        return str(obj.commercant) if obj.commercant else None


class TicketSerializer(serializers.ModelSerializer):
    """Serializer pour Ticket"""
    
    class Meta:
        model = Ticket
        fields = [
            'id', 'numero', 'date_creation', 'date_utilisation',
            'utilise', 'statut'
        ]


class PaiementSerializer(serializers.ModelSerializer):
    """Serializer pour Paiement"""
    commercant_nom = serializers.CharField(source='commercant.nom_complet', read_only=True)
    etal_numero = serializers.CharField(source='etal.numero', read_only=True)
    ticket_numero = serializers.CharField(source='ticket.numero', read_only=True)
    collecteur_nom = serializers.CharField(source='collecteur.nom_complet', read_only=True)
    enregistre_par_username = serializers.CharField(source='enregistre_par.username', read_only=True)
    
    class Meta:
        model = Paiement
        fields = [
            'id', 'commercant', 'commercant_nom', 'etal', 'etal_numero',
            'montant', 'date_paiement', 'mode_paiement', 'ticket',
            'ticket_numero', 'collecteur', 'collecteur_nom', 'enregistre_par', 'enregistre_par_username'
        ]
        read_only_fields = ['date_paiement', 'enregistre_par']
        extra_kwargs = {
            'montant': {'required': False},
            'etal': {'required': True},
            'ticket': {'required': True},
            'collecteur': {'required': True},
        }


class TaxeJournaliereSerializer(serializers.ModelSerializer):
    commercant_nom = serializers.CharField(source='commercant.nom_complet', read_only=True)
    etal_numero = serializers.CharField(source='etal.numero', read_only=True)
    en_retard = serializers.ReadOnlyField()

    class Meta:
        model = TaxeJournaliere
        fields = [
            'id', 'date', 'commercant', 'commercant_nom', 'etal', 'etal_numero',
            'montant_attendu', 'paye', 'statut', 'paiement', 'en_retard'
        ]


class HistoriqueAttributionSerializer(serializers.ModelSerializer):
    """Serializer pour HistoriqueAttribution"""
    etal_numero = serializers.CharField(source='etal.numero', read_only=True)
    commercant_nom = serializers.CharField(source='commercant.nom_complet', read_only=True)
    
    class Meta:
        model = HistoriqueAttribution
        fields = [
            'id', 'etal', 'etal_numero', 'commercant', 'commercant_nom',
            'date_debut', 'date_fin', 'attribue_par'
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer pour AuditLog"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_username', 'action', 'model_name',
            'object_id', 'object_repr', 'changes', 'ip_address',
            'status', 'message', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer pour Notification"""
    
    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'titre', 'message', 'lue',
            'date_creation', 'date_lecture', 'lien'
        ]
        read_only_fields = ['date_creation']


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour User (basique)"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff']
        read_only_fields = ['is_staff']

