from django.contrib import admin
from django.utils import timezone
from .models import (
    Secteur, Commercant, Etal, Ticket, Paiement, Collecteur, LotTickets,
    AuditLog, Notification, TaxeJournaliere
)


@admin.register(Secteur)
class SecteurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'description', 'tarif_par_defaut', 'jour_echeance']
    search_fields = ['nom']
    fields = ['nom', 'description', 'tarif_par_defaut', 'jour_echeance']


@admin.register(Commercant)
class CommercantAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'contact', 'type_commerce', 'date_inscription', 'actif']
    list_filter = ['actif', 'type_commerce', 'date_inscription']
    search_fields = ['nom', 'prenom', 'contact']
    list_editable = ['actif']


@admin.register(Etal)
class EtalAdmin(admin.ModelAdmin):
    list_display = ['numero', 'secteur', 'superficie', 'tarif_par_metre_carre', 'statut', 'commercant', 'date_attribution']
    list_filter = ['statut', 'secteur']
    search_fields = ['numero', 'commercant__nom', 'commercant__prenom']
    list_editable = ['statut']
    fields = ['numero', 'secteur', 'superficie', 'tarif_par_metre_carre', 'statut', 'commercant', 'date_attribution']


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ['numero', 'statut', 'lot', 'date_creation', 'date_utilisation', 'utilise']
    list_filter = ['statut', 'lot', 'date_creation']
    search_fields = ['numero']

    actions = ['action_marquer_perdu', 'action_marquer_annule']

    def get_readonly_fields(self, request, obj=None):
        if obj and (obj.statut == 'utilise' or obj.paiements.exists()):
            return ['numero', 'statut', 'utilise', 'date_creation', 'date_utilisation', 'lot', 'motif']
        return []

    def action_marquer_perdu(self, request, queryset):
        updated = 0
        for t in queryset:
            if t.statut == 'utilise' or t.paiements.exists():
                continue
            t.utilise = False
            t.statut = 'perdu'
            if not t.motif:
                t.motif = 'Déclaré perdu'
            t.date_utilisation = None
            t.save()
            updated += 1
        self.message_user(request, f"{updated} ticket(s) marqué(s) perdu(s).")
    action_marquer_perdu.short_description = "Marquer les tickets comme perdus"

    def action_marquer_annule(self, request, queryset):
        updated = 0
        for t in queryset:
            if t.statut == 'utilise' or t.paiements.exists():
                continue
            t.utilise = False
            t.statut = 'annule'
            if not t.motif:
                t.motif = 'Déclaré annulé'
            t.date_utilisation = None
            t.save()
            updated += 1
        self.message_user(request, f"{updated} ticket(s) marqué(s) annulé(s).")
    action_marquer_annule.short_description = "Marquer les tickets comme annulés"


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ['commercant', 'etal', 'montant', 'date_paiement', 'mode_paiement', 'ticket', 'collecteur']
    list_filter = ['mode_paiement', 'date_paiement']
    search_fields = ['commercant__nom', 'commercant__prenom', 'ticket__numero']
    date_hierarchy = 'date_paiement'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Collecteur)
class CollecteurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'contact', 'actif', 'date_creation']
    list_filter = ['actif', 'date_creation']
    search_fields = ['nom', 'prenom', 'contact']
    list_editable = ['actif']


@admin.register(LotTickets)
class LotTicketsAdmin(admin.ModelAdmin):
    list_display = ['id', 'collecteur', 'date_remise', 'statut', 'ticket_debut', 'ticket_fin', 'nb_remis', 'nb_utilises', 'nb_restants', 'nb_perdus_annules']
    list_filter = ['statut', 'date_remise']
    search_fields = ['collecteur__nom', 'collecteur__prenom', 'ticket_debut', 'ticket_fin']

    actions = ['action_assigner_plage', 'action_clore_lot']

    def action_assigner_plage(self, request, queryset):
        total = 0
        for lot in queryset:
            total += lot.assigner_plage()
        self.message_user(request, f"{total} ticket(s) assigné(s) aux lots sélectionnés.")
    action_assigner_plage.short_description = "Assigner la plage de tickets"

    def action_clore_lot(self, request, queryset):
        updated = queryset.update(statut='clos', date_cloture=timezone.now().date())
        self.message_user(request, f"{updated} lot(s) clos.")
    action_clore_lot.short_description = "Clore le lot"


@admin.register(TaxeJournaliere)
class TaxeJournaliereAdmin(admin.ModelAdmin):
    list_display = ['date', 'commercant', 'etal', 'montant_attendu', 'paye', 'statut', 'paiement']
    list_filter = ['paye', 'statut', 'date']
    search_fields = ['commercant__nom', 'commercant__prenom', 'etal__numero']
    date_hierarchy = 'date'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'model_name', 'object_repr', 'status']
    list_filter = ['action', 'status', 'model_name', 'timestamp']
    search_fields = ['user__username', 'model_name', 'object_repr', 'message']
    readonly_fields = ['timestamp', 'user', 'action', 'model_name', 'object_id', 'object_repr', 
                       'changes', 'ip_address', 'user_agent', 'status', 'message']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'titre', 'lue', 'date_creation']
    list_filter = ['type', 'lue', 'date_creation']
    search_fields = ['user__username', 'titre', 'message']
    readonly_fields = ['date_creation']
    date_hierarchy = 'date_creation'


