"""
Middleware personnalisé pour la gestion d'erreurs
"""
import logging
import traceback
from django.http import HttpResponseServerError
from django.http import HttpResponseForbidden
from django.template import loader
from django.utils import timezone
from .services import AuditService

logger = logging.getLogger('market')


class ErrorLoggingMiddleware:
    """Middleware pour logger toutes les exceptions non gérées"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """Traite les exceptions non gérées"""
        # Logger l'erreur
        error_message = f"Exception non gérée: {str(exception)}"
        logger.error(
            error_message,
            exc_info=True,
            extra={
                'request': request,
                'user': getattr(request, 'user', None),
                'path': request.path,
                'method': request.method,
            }
        )

        # Enregistrer dans l'audit si l'utilisateur est authentifié
        if hasattr(request, 'user') and request.user.is_authenticated:
            try:
                ip_address = AuditService.get_client_ip(request)
                user_agent = request.META.get('HTTP_USER_AGENT', '')
                AuditService.log_error(
                    user=request.user,
                    action='error',
                    model_name='Exception',
                    error_message=f"{type(exception).__name__}: {str(exception)}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            except Exception:
                pass  # Ne pas bloquer si l'audit échoue

        # Retourner None pour laisser Django gérer l'erreur normalement
        return None


class AdminAccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/admin'):
            user = getattr(request, 'user', None)
            if not user or not user.is_authenticated:
                return HttpResponseForbidden('Accès interdit.')
            if not user.is_superuser and not user.groups.filter(name='Administrateur').exists():
                return HttpResponseForbidden('Accès interdit.')
        return self.get_response(request)


class SecurityHeadersMiddleware:
    """Middleware pour ajouter des en-têtes de sécurité"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Ajouter des en-têtes de sécurité
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response

