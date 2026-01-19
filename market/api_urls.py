"""
URLs pour l'API REST
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .viewsets import (
    SecteurViewSet, CommercantViewSet, EtalViewSet,
    TicketViewSet, PaiementViewSet, TaxeJournaliereViewSet,
    HistoriqueAttributionViewSet, AuditLogViewSet, NotificationViewSet
)

# Créer le router
router = DefaultRouter()
router.register(r'secteurs', SecteurViewSet, basename='secteur')
router.register(r'commercants', CommercantViewSet, basename='commercant')
router.register(r'etals', EtalViewSet, basename='etal')
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'paiements', PaiementViewSet, basename='paiement')
router.register(r'taxes-journalieres', TaxeJournaliereViewSet, basename='taxe-journaliere')
router.register(r'historique-attributions', HistoriqueAttributionViewSet, basename='historique-attribution')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'notifications', NotificationViewSet, basename='notification')

# Vue de schéma Swagger
schema_view = get_schema_view(
    openapi.Info(
        title="e-Marché API",
        default_version='v1',
        description="API REST pour la gestion des marchés municipaux",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@emarche.treichville.ci"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
)

urlpatterns = [
    # Routes du router
    path('', include(router.urls)),
    
    # Authentification
    path('auth/token/', obtain_auth_token, name='api_token_auth'),
    
    # Documentation Swagger
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('swagger.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
]

