from rest_framework.permissions import BasePermission

from apps.accounts.models import RoleChoices


class IsManagerOrDispatcher(BasePermission):
    """Allow access only to Manager and Dispatcher roles."""

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.role in (RoleChoices.MANAGER, RoleChoices.DISPATCHER)
        )
