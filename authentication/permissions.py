from rest_framework import permissions

class IsCREUser(permissions.BasePermission):
    """
    Custom permission to only allow CRE (Super Admin) users to access a view.
    """
    def has_permission(self, request, view):
        # Assumes a Django Group named 'CRE User' exists.
        return request.user.groups.filter(name='CRE User').exists()

class IsPropertyGroupUser(permissions.BasePermission):
    """
    Custom permission to only allow Property Group Admin users to access a view.
    """
    def has_permission(self, request, view):
        # Assumes a Django Group named 'PropertyGroup User' exists.
        return request.user.groups.filter(name='PropertyGroup User').exists()

class IsPropertyUser(permissions.BasePermission):
    """
    Custom permission to only allow Single Property Admin users to access a view.
    """
    def has_permission(self, request, view):
        # Assumes a Django Group named 'Property User' exists.
        return request.user.groups.filter(name='Property User').exists()

class IsClientUser(permissions.BasePermission):
    """
    Custom permission to only allow Client users to access a view.
    """
    def has_permission(self, request, view):
        # Assumes a Django Group named 'Client User' exists.
        return request.user.groups.filter(name='Client User').exists()