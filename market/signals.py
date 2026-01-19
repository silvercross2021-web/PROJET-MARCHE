"""
Signals Django pour l'audit automatique
"""
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from .models import Commercant, Etal, Paiement, Ticket, AuditLog
from .services import AuditService
import logging

logger = logging.getLogger('market.audit')


@receiver(post_save, sender=Commercant)
def log_commercant_save(sender, instance, created, **kwargs):
    """Log la création/modification d'un commerçant"""
    action = 'create' if created else 'update'
    changes = {}
    
    if not created:
        # Récupérer l'ancien état depuis la base
        try:
            old_instance = Commercant.objects.get(pk=instance.pk)
            if old_instance.nom != instance.nom:
                changes['nom'] = {'old': old_instance.nom, 'new': instance.nom}
            if old_instance.prenom != instance.prenom:
                changes['prenom'] = {'old': old_instance.prenom, 'new': instance.prenom}
            if old_instance.actif != instance.actif:
                changes['actif'] = {'old': old_instance.actif, 'new': instance.actif}
        except Commercant.DoesNotExist:
            pass
    
    AuditLog.objects.create(
        action=action,
        model_name='Commercant',
        object_id=instance.id,
        object_repr=str(instance),
        changes=changes,
        status='success'
    )


@receiver(post_delete, sender=Commercant)
def log_commercant_delete(sender, instance, **kwargs):
    """Log la suppression d'un commerçant"""
    AuditLog.objects.create(
        action='delete',
        model_name='Commercant',
        object_id=instance.id,
        object_repr=str(instance),
        status='success'
    )


@receiver(post_save, sender=Etal)
def log_etal_save(sender, instance, created, **kwargs):
    """Log la création/modification d'un étal"""
    action = 'create' if created else 'update'
    changes = {}
    
    if not created:
        try:
            old_instance = Etal.objects.get(pk=instance.pk)
            if old_instance.statut != instance.statut:
                changes['statut'] = {'old': old_instance.statut, 'new': instance.statut}
            if old_instance.commercant != instance.commercant:
                changes['commercant'] = {
                    'old': str(old_instance.commercant) if old_instance.commercant else None,
                    'new': str(instance.commercant) if instance.commercant else None
                }
        except Etal.DoesNotExist:
            pass
    
    AuditLog.objects.create(
        action=action,
        model_name='Etal',
        object_id=instance.id,
        object_repr=str(instance),
        changes=changes,
        status='success'
    )


@receiver(post_save, sender=Paiement)
def log_paiement_save(sender, instance, created, **kwargs):
    """Log la création d'un paiement"""
    if created:
        AuditLog.objects.create(
            action='create',
            model_name='Paiement',
            object_id=instance.id,
            object_repr=str(instance),
            changes={
                'montant': float(instance.montant),
                'mode_paiement': instance.mode_paiement,
                'commercant': str(instance.commercant),
            },
            status='success'
        )


@receiver(post_save, sender=Ticket)
def log_ticket_save(sender, instance, created, **kwargs):
    """Log la création/modification d'un ticket"""
    action = 'create' if created else 'update'
    changes = {}
    
    if not created:
        try:
            old_instance = Ticket.objects.get(pk=instance.pk)
            if old_instance.statut != instance.statut:
                changes['statut'] = {'old': old_instance.statut, 'new': instance.statut}
        except Ticket.DoesNotExist:
            pass
    
    AuditLog.objects.create(
        action=action,
        model_name='Ticket',
        object_id=instance.id,
        object_repr=str(instance),
        changes=changes,
        status='success'
    )


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log la connexion d'un utilisateur"""
    ip_address = AuditService.get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AuditLog.objects.create(
        user=user,
        action='login',
        model_name='User',
        object_id=user.id,
        object_repr=user.username,
        ip_address=ip_address,
        user_agent=user_agent,
        status='success'
    )


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log la déconnexion d'un utilisateur"""
    if user:
        ip_address = AuditService.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        AuditLog.objects.create(
            user=user,
            action='logout',
            model_name='User',
            object_id=user.id,
            object_repr=user.username,
            ip_address=ip_address,
            user_agent=user_agent,
            status='success'
        )

