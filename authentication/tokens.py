"""
Custom JWT Token Serializers for Campaign Planner SSO.

This module provides enhanced JWT tokens that include user identity,
role information, and permissions for cross-service authentication
with Retail Studio.
"""

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from property_app.models import PropertyUserRole
from .models import App


class CampaignPlannerTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom token serializer that includes user identity and role information
    for cross-service authentication (SSO with Retail Studio).
    
    The token includes:
    - Core identity (email, name)
    - Permission flags (is_superuser, is_staff, is_active)
    - Role information (primary role)
    - Memberships (detailed property/group access)
    - App information (current app context)
    - Issuer claim for token origin verification
    """
    app_id = serializers.IntegerField(required=False, write_only=True, allow_null=True)
    app_slug = serializers.CharField(required=False, write_only=True, allow_null=True)
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Get app from app_id or app_slug
        app = None
        app_id = attrs.get('app_id')
        app_slug = attrs.get('app_slug')
        
        if app_id:
            try:
                app = App.objects.get(id=app_id, is_active=True)
            except App.DoesNotExist:
                raise serializers.ValidationError({
                    'app_id': 'Invalid app ID or app is not active.'
                })
        elif app_slug:
            try:
                app = App.objects.get(slug=app_slug, is_active=True)
            except App.DoesNotExist:
                raise serializers.ValidationError({
                    'app_slug': 'Invalid app slug or app is not active.'
                })
        else:
            raise serializers.ValidationError({
                'app_id': 'Either app_id or app_slug is required.'
            })
        
        # Check if user has access to this app
        user = self.user
        if not user.has_access_to_app(app):
            raise serializers.ValidationError({
                'app_id': 'You do not have access to this app.'
            })
        
        # Store app in context for token generation
        self.app = app
        
        return data
    
    @classmethod
    def get_token(cls, user, app=None):
        token = super().get_token(user)
        
        # Core identity claims
        token['email'] = user.email
        token['first_name'] = user.first_name or ''
        token['last_name'] = user.last_name or ''
        
        # Permission flags
        token['is_superuser'] = user.is_superuser
        token['is_staff'] = user.is_staff
        token['is_active'] = user.is_active
        
        # Role and membership information
        token['role'] = cls._get_user_role(user)
        token['memberships'] = cls._get_user_memberships(user)
        
        # App information
        if app:
            token['app_id'] = app.id
            token['app_name'] = app.name
            token['app_slug'] = app.slug
        
        # Service identifier (helps Retail Studio verify token origin)
        token['iss'] = 'campaign-planner'
        
        return token
    
    @classmethod
    def _get_user_role(cls, user):
        """
        Get the user's primary role.
        
        Returns:
            str: The user's primary role ('super_user', 'group_admin', 
                 'property_admin', 'tenant') or None if no role assigned.
        """
        if user.is_superuser:
            return 'super_user'
        
        memberships = user.property_memberships.all()
        if not memberships.exists():
            return None
        
        # Return the highest privilege role if user has multiple memberships
        # Priority: group_admin > property_admin > tenant
        role_priority = {
            PropertyUserRole.GROUP_ADMIN: 3,
            PropertyUserRole.PROPERTY_ADMIN: 2,
            PropertyUserRole.TENANT: 1,
        }
        
        highest_role = None
        highest_priority = 0
        
        for membership in memberships:
            priority = role_priority.get(membership.role, 0)
            if priority > highest_priority:
                highest_priority = priority
                highest_role = membership.role
        
        return highest_role
    
    @classmethod
    def _get_user_memberships(cls, user):
        """
        Get all user memberships for granular permission checks.
        
        Returns:
            list: List of membership dictionaries containing role and scope info.
        """
        if user.is_superuser:
            return [{'role': 'super_user', 'scope': 'global'}]
        
        memberships = []
        for m in user.property_memberships.all():
            membership_data = {'role': m.role}
            
            if m.property:
                membership_data['property_id'] = m.property.id
                membership_data['property_name'] = m.property.name
                if m.property.property_group:
                    membership_data['property_group_id'] = m.property.property_group.id
                    membership_data['property_group_name'] = m.property.property_group.name
            elif m.property_group:
                membership_data['property_group_id'] = m.property_group.id
                membership_data['property_group_name'] = m.property_group.name
            
            memberships.append(membership_data)
        
        return memberships
    
    def get_token(self, user):
        """Override to pass app context"""
        app = getattr(self, 'app', None)
        return self.__class__.get_token(user, app=app)

