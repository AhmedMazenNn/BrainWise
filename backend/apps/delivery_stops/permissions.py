from rest_framework import permissions

from apps.accounts.models import RoleChoices


class DeliveryStopPermission(permissions.BasePermission):
    """Manager/Dispatcher: full CRUD. Driver: read-only on own stops,
    plus mark_delivered/mark_failed on own stops."""

    # Actions that drivers are allowed to use (in addition to read).
    DRIVER_WRITE_ACTIONS = {'mark_delivered', 'mark_failed'}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role in (RoleChoices.MANAGER, RoleChoices.DISPATCHER):
            return True
        if request.user.role == RoleChoices.DRIVER:
            if request.method in permissions.SAFE_METHODS:
                return True
            if getattr(view, 'action', None) in self.DRIVER_WRITE_ACTIONS:
                return True
            return False
        return False

    def has_object_permission(self, request, view, obj):
        if request.user.role in (RoleChoices.MANAGER, RoleChoices.DISPATCHER):
            return True
        if request.user.role == RoleChoices.DRIVER:
            if getattr(view, 'action', None) in self.DRIVER_WRITE_ACTIONS:
                return obj.delivery_run.driver.user == request.user
            if request.method in permissions.SAFE_METHODS:
                return obj.delivery_run.driver.user == request.user
        return False
