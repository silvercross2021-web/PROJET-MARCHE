"""
ViewSets pour l'API REST
"""
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import (
    Secteur, Commercant, Etal, Ticket, Paiement,
    HistoriqueAttribution, AuditLog, Notification, TaxeJournaliere
)
from .serializers import (
    SecteurSerializer, CommercantSerializer, EtalSerializer,
    TicketSerializer, PaiementSerializer,
    HistoriqueAttributionSerializer, AuditLogSerializer, NotificationSerializer, TaxeJournaliereSerializer
)
from .permissions import IsGestionnaire, IsCaissier, IsLecteur
from .services import PaiementService


class SecteurViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour Secteur (lecture seule)"""
    queryset = Secteur.objects.all()
    serializer_class = SecteurSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'description']
    ordering_fields = ['nom']


class CommercantViewSet(viewsets.ModelViewSet):
    """ViewSet pour Commercant"""
    queryset = Commercant.objects.all()
    serializer_class = CommercantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['nom', 'prenom', 'contact', 'type_commerce']
    ordering_fields = ['nom', 'prenom', 'date_inscription']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par actif si demandé
        actif = self.request.query_params.get('actif', None)
        if actif is not None:
            queryset = queryset.filter(actif=actif.lower() == 'true')
        return queryset


class TaxeJournaliereViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TaxeJournaliere.objects.select_related('commercant', 'etal', 'paiement').all()
    serializer_class = TaxeJournaliereSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['commercant__nom', 'commercant__prenom', 'etal__numero']
    ordering_fields = ['date', 'montant_attendu']

    def get_queryset(self):
        queryset = super().get_queryset()
        paye = self.request.query_params.get('paye', None)
        if paye is not None:
            queryset = queryset.filter(paye=paye.lower() == 'true')
        retards = self.request.query_params.get('retards', None)
        if retards and retards.lower() == 'true':
            from django.utils import timezone
            queryset = queryset.filter(paye=False, statut='du', date__lt=timezone.now().date())
        return queryset


class EtalViewSet(viewsets.ModelViewSet):
    """ViewSet pour Etal"""
    queryset = Etal.objects.select_related('secteur', 'commercant').all()
    serializer_class = EtalSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero', 'secteur__nom', 'commercant__nom', 'commercant__prenom']
    ordering_fields = ['numero', 'secteur__nom', 'date_attribution']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par statut si demandé
        statut = self.request.query_params.get('statut', None)
        if statut:
            queryset = queryset.filter(statut=statut)
        # Filtrer par secteur si demandé
        secteur = self.request.query_params.get('secteur', None)
        if secteur:
            queryset = queryset.filter(secteur_id=secteur)
        return queryset


class TicketViewSet(viewsets.ModelViewSet):
    """ViewSet pour Ticket"""
    queryset = Ticket.objects.all()
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero']
    ordering_fields = ['date_creation', 'numero']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par statut si demandé
        statut = self.request.query_params.get('statut', None)
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset


class PaiementViewSet(viewsets.ModelViewSet):
    """ViewSet pour Paiement"""
    queryset = Paiement.objects.select_related(
        'commercant', 'etal', 'ticket', 'enregistre_par'
    ).all()
    serializer_class = PaiementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['commercant__nom', 'commercant__prenom', 'ticket__numero']
    ordering_fields = ['date_paiement', 'montant']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Filtrer par mode de paiement si demandé
        mode = self.request.query_params.get('mode_paiement', None)
        if mode:
            queryset = queryset.filter(mode_paiement=mode)
        # Filtrer par commerçant si demandé
        commercant = self.request.query_params.get('commercant', None)
        if commercant:
            queryset = queryset.filter(commercant_id=commercant)
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Créer un paiement en passant par la logique métier (taxe journalière fixe, pas de partiel)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        commercant = serializer.validated_data.get('commercant')
        etal = serializer.validated_data.get('etal')
        ticket = serializer.validated_data.get('ticket')
        mode_paiement = serializer.validated_data.get('mode_paiement')
        collecteur = serializer.validated_data.get('collecteur')

        montant = PaiementService.calculer_taxe_journaliere(etal)
        paiement = PaiementService.enregistrer_paiement(
            commercant=commercant,
            montant=montant,
            mode_paiement=mode_paiement,
            etal=etal,
            ticket=ticket,
            collecteur=collecteur,
            user=request.user,
            date_paiement=None,
        )

        out = self.get_serializer(paiement)
        return Response(out.data, status=201)


class HistoriqueAttributionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour HistoriqueAttribution (lecture seule)"""
    queryset = HistoriqueAttribution.objects.select_related('etal', 'commercant').all()
    serializer_class = HistoriqueAttributionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_debut', 'date_fin']


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour AuditLog (lecture seule, admin seulement)"""
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsGestionnaire]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['model_name', 'action', 'user__username']
    ordering_fields = ['timestamp', 'action', 'model_name']


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet pour Notification"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['date_creation']
    
    def get_queryset(self):
        """Retourne uniquement les notifications de l'utilisateur connecté"""
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def marquer_lue(self, request, pk=None):
        """Marque une notification comme lue"""
        notification = self.get_object()
        notification.marquer_comme_lue()
        return Response({'status': 'notification marquée comme lue'})
    
    @action(detail=False, methods=['get'])
    def non_lues(self, request):
        """Retourne les notifications non lues"""
        notifications = self.get_queryset().filter(lue=False)
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def marquer_toutes_lues(self, request):
        """Marque toutes les notifications comme lues"""
        count = self.get_queryset().filter(lue=False).update(lue=True)
        return Response({'status': f'{count} notifications marquées comme lues'})

