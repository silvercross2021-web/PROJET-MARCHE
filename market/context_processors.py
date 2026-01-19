from .permissions import is_admin_or_responsable


def ui_permissions(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'can_manage_collecteurs_ui': False,
        }

    return {
        'can_manage_collecteurs_ui': is_admin_or_responsable(user),
    }
