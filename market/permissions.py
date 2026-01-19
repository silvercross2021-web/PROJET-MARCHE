"""
Permissions personnalisées pour l'application market
"""
from rest_framework import permissions


class IsAdministrateur(permissions.BasePermission):
    """Permission pour les administrateurs"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.groups.filter(name='Administrateur').exists()


class IsGestionnaire(permissions.BasePermission):
    """Permission pour les gestionnaires"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.groups.filter(name='Administrateur').exists() or
            request.user.groups.filter(name='Gestionnaire').exists()
        )


class IsCaissier(permissions.BasePermission):
    """Permission pour les caissiers"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.groups.filter(name__in=['Administrateur', 'Gestionnaire', 'Caissier']).exists()
        )


class IsLecteur(permissions.BasePermission):
    """Permission pour les lecteurs (lecture seule)"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Les administrateurs, gestionnaires et caissiers ont aussi accès en lecture
        if request.user.groups.filter(name__in=['Administrateur', 'Gestionnaire', 'Caissier']).exists():
            return True
        
        # Les lecteurs ont accès en lecture seule
        if request.method in permissions.SAFE_METHODS:
            return request.user.groups.filter(name='Lecteur').exists()
        
        return False


def has_group(user, group_name):
    """Vérifie si un utilisateur appartient à un groupe"""
    return user.is_authenticated and user.groups.filter(name=group_name).exists()


def is_administrateur(user):
    """Vérifie si l'utilisateur est administrateur"""
    return has_group(user, 'Administrateur')


def is_responsable_mairie(user):
    return has_group(user, 'ResponsableMairie')


def is_admin_or_responsable(user):
    return is_administrateur(user) or is_responsable_mairie(user)


def is_gestionnaire(user):
    """Vérifie si l'utilisateur est gestionnaire ou administrateur"""
    return is_administrateur(user) or is_responsable_mairie(user) or has_group(user, 'Gestionnaire')


def is_caissier(user):
    """Vérifie si l'utilisateur est caissier, gestionnaire ou administrateur"""
    return is_administrateur(user) or is_responsable_mairie(user) or has_group(user, 'Gestionnaire') or has_group(user, 'Caissier')


def can_modify_paiement(user):
    """Vérifie si l'utilisateur peut modifier un paiement"""
    return is_caissier(user)


def can_manage_commercants(user):
    """Vérifie si l'utilisateur peut gérer les commerçants"""
    return is_gestionnaire(user)


def can_manage_etals(user):
    """Vérifie si l'utilisateur peut gérer les étals"""
    return is_gestionnaire(user)


def can_manage_tickets(user):
    return is_gestionnaire(user)


def can_manage_collecteurs(user):
    return is_admin_or_responsable(user)

