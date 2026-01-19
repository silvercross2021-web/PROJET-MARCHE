from django.urls import path
from . import views

urlpatterns = [
    # Authentification
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Commerçants
    path('commercants/', views.commercants_list, name='commercants'),
    path('commercants/<int:commercant_id>/', views.commercant_detail, name='commercant_detail'),
    path('commercants/create/', views.commercant_create, name='commercant_create'),
    path('commercants/<int:commercant_id>/update/', views.commercant_update, name='commercant_update'),
    path('commercants/<int:commercant_id>/delete/', views.commercant_delete, name='commercant_delete'),
    
    # Étals
    path('etals/', views.etals_list, name='etals'),
    path('etals/<int:etal_id>/', views.etal_detail, name='etal_detail'),
    path('etals/create/', views.etal_create, name='etal_create'),
    path('etals/<int:etal_id>/update/', views.etal_update, name='etal_update'),
    path('etals/<int:etal_id>/delete/', views.etal_delete, name='etal_delete'),
    path('etals/<int:etal_id>/attribuer/', views.etal_attribuer, name='etal_attribuer'),
    path('etals/<int:etal_id>/liberer/', views.etal_liberer, name='etal_liberer'),
    
    # Paiements
    path('paiements/', views.paiements_view, name='paiements'),
    path('paiements/<int:paiement_id>/modifier/', views.paiement_modifier, name='paiement_modifier'),
    path('paiements/<int:paiement_id>/annuler/', views.paiement_annuler, name='paiement_annuler'),
    path('paiements/<int:paiement_id>/reçu/', views.paiement_reçu, name='paiement_reçu'),

    path('api/collecteurs/<int:collecteur_id>/tickets-disponibles/', views.tickets_disponibles_par_collecteur, name='tickets_disponibles_par_collecteur'),
    
    # Tickets
    path('tickets/', views.tickets_list, name='tickets'),
    path('tickets/create/', views.ticket_create, name='ticket_create'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/update/', views.ticket_update, name='ticket_update'),
    path('tickets/<int:ticket_id>/delete/', views.ticket_delete, name='ticket_delete'),
    path('tickets/generer/', views.tickets_generer, name='tickets_generer'),

    # Collecteurs / Lots
    path('collecteurs/', views.collecteurs_list, name='collecteurs'),
    path('collecteurs/create/', views.collecteur_create, name='collecteur_create'),
    path('collecteurs/<int:collecteur_id>/update/', views.collecteur_update, name='collecteur_update'),
    path('collecteurs/<int:collecteur_id>/toggle/', views.collecteur_toggle, name='collecteur_toggle'),

    path('lots-tickets/', views.lots_tickets_list, name='lots_tickets'),
    path('lots-tickets/create/', views.lot_ticket_create, name='lot_ticket_create'),
    path('lots-tickets/<int:lot_id>/update/', views.lot_ticket_update, name='lot_ticket_update'),
    path('lots-tickets/<int:lot_id>/assigner-plage/', views.lot_ticket_assigner_plage, name='lot_ticket_assigner_plage'),
    path('lots-tickets/<int:lot_id>/clore/', views.lot_ticket_clore, name='lot_ticket_clore'),
    
    # Rapports
    path('rapports/', views.rapports_view, name='rapports'),
    path('rapports/export-pdf/', views.rapports_export_pdf, name='rapports_export_pdf'),
    path('rapports/export-excel/', views.rapports_export_excel, name='rapports_export_excel'),
    
    # Historique collecteurs
    path('collecteurs/<int:collecteur_id>/historique/', views.historique_collecteur, name='historique_collecteur'),
    path('collecteurs/<int:collecteur_id>/generer-rapport/', views.generer_rapport_collecteur, name='generer_rapport_collecteur'),
    path('rapports/collecteurs/', views.rapports_collecteurs, name='rapports_collecteurs'),
    path('rapports/collecteurs/generer-tous/', views.generer_rapports_tous_collecteurs, name='generer_rapports_tous_collecteurs'),
]


