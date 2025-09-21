from rest_framework import permissions
from property_app.models import Property, PropertyUserRole


class CanManageUsers(permissions.BasePermission):
    """
    Permission class for hierarchical user management.
    
    Hierarchy:
    - SuperUser: Can manage all user types
    - Property Group Admin: Can manage Property Admins and Tenants within their group
    - Property Admin: Can manage Tenants within their property
    - Tenant: Cannot manage other users
    """
    
    def has_permission(self, request, view):
        """Check if user has any management permissions"""
        if not request.user.is_authenticated:
            return False
            
        # Superusers can always manage users
        if request.user.is_superuser:
            return True
            
        # Check if user has admin roles
        memberships = request.user.property_memberships.all()
        admin_roles = [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.GROUP_ADMIN]
        
        return memberships.filter(role__in=admin_roles).exists()
    
    def has_object_permission(self, request, view, obj):
        """Check if user can manage the specific user object"""
        if not request.user.is_authenticated:
            return False
            
        # Superusers can manage anyone
        if request.user.is_superuser:
            return True
            
        # Users cannot manage themselves through this API (prevents privilege escalation)
        if request.user == obj:
            return False
            
        # Get requesting user's memberships
        requester_memberships = request.user.property_memberships.all()
        
        # Get target user's memberships
        target_memberships = obj.property_memberships.all()
        
        # If target is a superuser, only superusers can manage them
        if obj.is_superuser:
            return request.user.is_superuser
            
        for requester_membership in requester_memberships:
            # Property Group Admins can manage users in their group
            if requester_membership.role == PropertyUserRole.GROUP_ADMIN:
                if requester_membership.property_group:
                    # Can manage property admins and tenants in same property group
                    for target_membership in target_memberships:
                        if (target_membership.property and 
                            target_membership.property.property_group == requester_membership.property_group):
                            if target_membership.role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]:
                                return True
                        elif (target_membership.property_group == requester_membership.property_group and
                              target_membership.role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]):
                            return True
                            
            # Property Admins can manage tenants in their property
            elif requester_membership.role == PropertyUserRole.PROPERTY_ADMIN:
                if requester_membership.property:
                    for target_membership in target_memberships:
                        if (target_membership.property == requester_membership.property and
                            target_membership.role == PropertyUserRole.TENANT):
                            return True
                            
        return False


class CanCreateUserWithRole(permissions.BasePermission):
    """
    Permission to check if a user can create users with specific roles.
    This is used in the create action to validate the role being assigned.
    """
    
    def has_permission(self, request, view):
        """Basic permission check - same as CanManageUsers"""
        return CanManageUsers().has_permission(request, view)
    
    def can_create_role(self, requester, target_role, property_id=None, property_group_id=None):
        """
        Check if requester can create a user with the target role
        """
        if not requester.is_authenticated:
            return False
            
        # Superusers can create any role
        if requester.is_superuser:
            return True
            
        requester_memberships = requester.property_memberships.all()
        
        for membership in requester_memberships:
            # Property Group Admins can create Property Admins and Tenants in their group
            if membership.role == PropertyUserRole.GROUP_ADMIN:
                if membership.property_group:
                    if target_role in [PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]:
                        # Check if target property/group is within their scope
                        if property_group_id == membership.property_group.id:
                            return True
                        if property_id:
                            try:
                                prop = Property.objects.get(id=property_id)
                                if prop.property_group == membership.property_group:
                                    return True
                            except Property.DoesNotExist:
                                pass
                                
            # Property Admins can only create Tenants in their property
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN:
                if membership.property:
                    if (target_role == PropertyUserRole.TENANT and 
                        property_id == membership.property.id):
                        return True
                        
        return False