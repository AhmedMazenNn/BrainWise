from rest_framework.permissions import BasePermission

from .models import RoleChoices


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.MANAGER

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsDispatcher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.DISPATCHER

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class IsDriver(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == RoleChoices.DRIVER

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)
