"""Role checks for tracker views. Always enforced server-side, whatever the UI shows."""

from functools import wraps

from django.core.exceptions import PermissionDenied


def admin_required(view):
    """Refuse the request with 403 Forbidden unless the user has the Admin role."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            raise PermissionDenied("Only Admins can do this.")
        return view(request, *args, **kwargs)

    return wrapper
