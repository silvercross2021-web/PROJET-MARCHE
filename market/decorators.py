"""
Décorateurs personnalisés pour les permissions
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from .permissions import (
    is_administrateur, is_gestionnaire, is_caissier,
    can_modify_paiement, can_manage_commercants, can_manage_etals
)


def permission_required_custom(permission_func):
    """
    Décorateur pour vérifier une permission personnalisée
    
    Usage:
        @permission_required_custom(is_gestionnaire)
        def ma_vue(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
                return redirect('login')
            
            if not permission_func(request.user):
                messages.error(request, 'Vous n\'avez pas la permission d\'accéder à cette page.')
                raise PermissionDenied
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def administrateur_required(view_func):
    """Décorateur pour les vues réservées aux administrateurs"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_administrateur(request.user):
            messages.error(request, 'Accès réservé aux administrateurs.')
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def gestionnaire_required(view_func):
    """Décorateur pour les vues réservées aux gestionnaires"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_gestionnaire(request.user):
            messages.error(request, 'Accès réservé aux gestionnaires.')
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def caissier_required(view_func):
    """Décorateur pour les vues réservées aux caissiers"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_caissier(request.user):
            messages.error(request, 'Accès réservé aux caissiers.')
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper

