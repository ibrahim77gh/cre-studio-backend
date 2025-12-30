from django.conf import settings
from django.db import models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, filters, permissions
from rest_framework.decorators import action
from djoser.social.views import ProviderAuthView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView
)
from .serializers import (
    UserSerializer, 
    UserManagementCreateSerializer,
    UserManagementUpdateSerializer,
    UserManagementListSerializer,
    UserProfileUpdateSerializer,
    UserStatsSerializer
)
from .tokens import CampaignPlannerTokenObtainPairSerializer
from .models import CustomUser, App
from .permissions import CanManageUsers
from property_app.models import PropertyUserRole, UserPropertyMembership


def set_tokens(response):
    access_token = response.data.get('access')
    refresh_token = response.data.get('refresh')
    response.set_cookie(
        'access',
        access_token,
        max_age=settings.AUTH_ACCESS_COOKIE_MAX_AGE,
        path=settings.AUTH_COOKIE_PATH,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.AUTH_COOKIE_SAMESITE
    )
    response.set_cookie(
        'refresh',
        refresh_token,
        max_age=settings.AUTH_REFRESH_COOKIE_MAX_AGE,
        path=settings.AUTH_COOKIE_PATH,
        secure=settings.AUTH_COOKIE_SECURE,
        httponly=settings.AUTH_COOKIE_HTTP_ONLY,
        samesite=settings.AUTH_COOKIE_SAMESITE
    )

class CustomProviderAuthView(ProviderAuthView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 201:
            set_tokens(response)

        return response


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom token obtain view that uses enhanced JWT tokens with
    user identity and role information for SSO with Retail Studio.
    """
    serializer_class = CampaignPlannerTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            set_tokens(response)

        return response


class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh')

        if refresh_token:
            request.data['refresh'] = refresh_token

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            set_tokens(response)

        return response


class CustomTokenVerifyView(TokenVerifyView):
    def post(self, request, *args, **kwargs):
        access_token = request.COOKIES.get('access')

        if access_token:
            request.data['token'] = access_token

        return super().post(request, *args, **kwargs)


class LogoutView(APIView):
    def post(self, request, *args, **kwargs):
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie('access')
        response.delete_cookie('refresh')

        return response


class UserManagementViewSet(viewsets.ModelViewSet):
    """
    ViewSet for comprehensive user management with hierarchical permissions.
    
    Supports:
    - Creating users with appropriate roles
    - Updating user information and roles  
    - Deleting users (with restrictions)
    - Listing users based on permissions
    - Filtering users by role, property, etc.
    """
    permission_classes = [CanManageUsers]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['email', 'first_name', 'last_name', 'date_joined']
    ordering = ['-date_joined']
    
    def get_queryset(self):
        """
        Return users that the current user can manage.
        """
        user = self.request.user
        
        # Superusers can see all users
        if user.is_superuser:
            return CustomUser.objects.all()
        
        # Get the user's memberships to determine what they can manage
        user_memberships = user.property_memberships.all()
        manageable_user_ids = set()
        
        for membership in user_memberships:
            if membership.role == PropertyUserRole.GROUP_ADMIN:
                # Group admins can manage users in their property group
                if membership.property_group:
                    # Get all properties in this group
                    group_properties = membership.property_group.properties.all()
                    
                    # Get users with memberships in these properties
                    group_property_users = CustomUser.objects.filter(
                        property_memberships__property__in=group_properties,
                        property_memberships__role__in=[PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]
                    )
                    
                    # Get users with group memberships
                    group_users = CustomUser.objects.filter(
                        property_memberships__property_group=membership.property_group,
                        property_memberships__role__in=[PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.TENANT]
                    )
                    
                    manageable_user_ids.update(group_property_users.values_list('id', flat=True))
                    manageable_user_ids.update(group_users.values_list('id', flat=True))
                    
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN:
                # Property admins can manage tenants in their property
                if membership.property:
                    property_tenants = CustomUser.objects.filter(
                        property_memberships__property=membership.property,
                        property_memberships__role=PropertyUserRole.TENANT
                    )
                    manageable_user_ids.update(property_tenants.values_list('id', flat=True))
        
        # Return queryset of manageable users
        if manageable_user_ids:
            return CustomUser.objects.filter(id__in=manageable_user_ids)
        else:
            return CustomUser.objects.none()
    
    def get_serializer_class(self):
        """
        Return appropriate serializer based on action.
        """
        if self.action == 'create':
            return UserManagementCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserManagementUpdateSerializer
        elif self.action == 'list':
            return UserManagementListSerializer
        else:
            return UserManagementListSerializer
    
    def perform_destroy(self, instance):
        """
        Custom delete logic - mark as inactive instead of hard delete
        for data integrity, or allow hard delete for superusers.
        """
        if self.request.user.is_superuser:
            # Superusers can hard delete
            super().perform_destroy(instance)
        else:
            # Others just deactivate
            instance.is_active = False
            instance.save()
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """
        Activate a deactivated user.
        Note: Users should be activated through invitation acceptance, not manually.
        This endpoint is kept for backward compatibility but should be used sparingly.
        Superusers can manually activate accounts even if invitation wasn't accepted.
        """
        user = self.get_object()
        
        if not user.is_active:
            # Check if user has accepted their invitation
            if not user.invitation_accepted:
                # Allow superusers to manually activate accounts
                if not request.user.is_superuser:
                    return Response(
                        {'error': 'User must accept their invitation before being activated. Please resend the invitation email.'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                else:
                    # Superuser is manually activating - also mark invitation as accepted
                    user.invitation_accepted = True
            
            user.is_active = True
            user.save()
            return Response({'status': 'User activated'})
        else:
            return Response(
                {'error': 'User is already active'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """
        Deactivate a user.
        """
        user = self.get_object()
        
        # Prevent users from deactivating themselves
        if user == request.user:
            return Response(
                {'error': 'Cannot deactivate yourself'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if user.is_active:
            user.is_active = False
            user.save()
            return Response({'status': 'User deactivated'})
        else:
            return Response(
                {'error': 'User is already inactive'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['get'])
    def my_manageable_scopes(self, request):
        """
        Return the properties and groups that the current user can manage.
        Useful for frontend dropdowns.
        """
        user = request.user
        
        if user.is_superuser:
            from property_app.models import Property, PropertyGroup
            return Response({
                'can_manage_all': True,
                'properties': [
                    {'id': p.id, 'name': p.name, 'property_group': {
                        'id': p.property_group.id, 'name': p.property_group.name
                    }} for p in Property.objects.all()
                ],
                'property_groups': [
                    {'id': pg.id, 'name': pg.name} for pg in PropertyGroup.objects.all()
                ]
            })
        
        manageable_properties = []
        manageable_groups = []
        
        for membership in user.property_memberships.all():
            if membership.role == PropertyUserRole.GROUP_ADMIN and membership.property_group:
                # Can manage all properties in the group
                group_properties = membership.property_group.properties.all()
                manageable_properties.extend([
                    {
                        'id': p.id, 
                        'name': p.name,
                        'property_group': {
                            'id': membership.property_group.id,
                            'name': membership.property_group.name
                        }
                    } for p in group_properties
                ])
                manageable_groups.append({
                    'id': membership.property_group.id,
                    'name': membership.property_group.name
                })
                
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN and membership.property:
                # Can only manage their specific property
                manageable_properties.append({
                    'id': membership.property.id,
                    'name': membership.property.name,
                    'property_group': {
                        'id': membership.property.property_group.id,
                        'name': membership.property.property_group.name
                    } if membership.property.property_group else None
                })
        
        return Response({
            'can_manage_all': False,
            'properties': manageable_properties,
            'property_groups': manageable_groups
        })
    
    @action(detail=False, methods=['get'])
    def role_options(self, request):
        """
        Return available role options for the current user.
        """
        user = request.user
        
        if user.is_superuser:
            return Response({
                'roles': [
                    {'value': 'super_user', 'label': 'Super User'},
                    {'value': PropertyUserRole.GROUP_ADMIN, 'label': 'Property Group Admin'},
                    {'value': PropertyUserRole.PROPERTY_ADMIN, 'label': 'Property Admin'},
                    {'value': PropertyUserRole.TENANT, 'label': 'Tenant'},
                ]
            })
        
        available_roles = []
        
        for membership in user.property_memberships.all():
            if membership.role == PropertyUserRole.GROUP_ADMIN:
                available_roles.extend([
                    {'value': PropertyUserRole.PROPERTY_ADMIN, 'label': 'Property Admin'},
                    {'value': PropertyUserRole.TENANT, 'label': 'Tenant'},
                ])
            elif membership.role == PropertyUserRole.PROPERTY_ADMIN:
                available_roles.append(
                    {'value': PropertyUserRole.TENANT, 'label': 'Tenant'}
                )
        
        # Remove duplicates
        seen = set()
        unique_roles = []
        for role in available_roles:
            if role['value'] not in seen:
                seen.add(role['value'])
                unique_roles.append(role)
        
        return Response({'roles': unique_roles})


# Keep the old AdminUserViewSet for backward compatibility if needed
class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer

    def perform_create(self, serializer):
        """Ensure password is set correctly on user creation."""
        user = serializer.save()
        user.set_password(serializer.validated_data['password'])
        user.save()

    def perform_update(self, serializer):
        """Ensure password is hashed when updated."""
        user = serializer.save()
        if 'password' in self.request.data:
            user.set_password(self.request.data['password'])
            user.save()


class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for users to manage their own profile information.
    Allows users to update their own profile but not role-related fields.
    """
    serializer_class = UserProfileUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Users can only access their own profile"""
        return CustomUser.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        """Always return the current user's profile"""
        return self.request.user
    
    def list(self, request, *args, **kwargs):
        """Redirect list to retrieve current user's profile"""
        return self.retrieve(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Profile creation is handled by registration, not here"""
        return Response(
            {'error': 'Profile creation is handled through user registration'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
    
    def destroy(self, request, *args, **kwargs):
        """Users cannot delete their own profiles through this endpoint"""
        return Response(
            {'error': 'Profile deletion not allowed through this endpoint'}, 
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )


class UserStatsView(APIView):
    """
    API endpoint to get user statistics.
    Returns counts for total_users, active_users, admin_users, and tenants.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Get user statistics for all users in the system.
        """
        # Get all users
        base_queryset = CustomUser.objects.all()
        
        # Calculate statistics
        total_users = base_queryset.count()
        active_users = base_queryset.filter(is_active=True).count()
        
        # Admin users: superusers + property admins + group admins
        admin_users = base_queryset.filter(
            models.Q(is_superuser=True) |
            models.Q(property_memberships__role__in=[PropertyUserRole.PROPERTY_ADMIN, PropertyUserRole.GROUP_ADMIN])
        ).distinct().count()
        
        # Tenants: users with tenant role
        tenants = base_queryset.filter(
            property_memberships__role=PropertyUserRole.TENANT
        ).distinct().count()
        
        # Prepare response data
        stats_data = {
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'tenants': tenants
        }
        
        # Serialize and return
        serializer = UserStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AcceptInvitationView(APIView):
    """
    API endpoint to accept user invitations.
    Users can accept invitations using their invitation token.
    """
    permission_classes = [permissions.AllowAny]  # No authentication required for invitation acceptance
    
    def get(self, request, token):
        """
        Accept an invitation using the invitation token.
        This activates the user account.
        """
        try:
            # Find user with the invitation token
            user = CustomUser.objects.get(invitation_token=token)
            
            # Check if invitation is still valid (not expired)
            if user.invitation_sent_at:
                from datetime import timedelta
                from django.utils import timezone
                invitation_expiry = user.invitation_sent_at + timedelta(days=7)
                if timezone.now() > invitation_expiry:
                    return Response(
                        {'error': 'Invitation has expired. Please request a new invitation.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Check if invitation is already accepted
            if user.invitation_accepted:
                return Response(
                    {'error': 'Invitation has already been accepted.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Accept the invitation
            user.invitation_accepted = True
            user.invitation_accepted_at = timezone.now()
            user.is_active = True  # Activate the user
            user.save()
            
            return Response({
                'message': 'Invitation accepted successfully! Your account has been activated.',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_active': user.is_active
                }
            })
            
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'Invalid invitation token.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResendInvitationView(APIView):
    """
    API endpoint to resend invitation emails.
    Only accessible by users who can manage the target user.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, user_id):
        """
        Resend invitation email to a user.
        """
        try:
            # Get the target user
            target_user = CustomUser.objects.get(id=user_id)
            
            # Check if current user can manage this user
            current_user = request.user
            manageable_users = current_user.get_managed_users()
            
            if target_user not in manageable_users:
                return Response(
                    {'error': 'You do not have permission to resend invitations for this user.'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if user already accepted invitation
            if target_user.invitation_accepted:
                return Response(
                    {'error': 'This user has already accepted their invitation.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get role information for the email
            role_info = self._get_role_info(target_user)
            
            # Send the invitation email
            from .email import InvitationEmail
            invitation_email = InvitationEmail(target_user, role_info)
            invitation_email.send()
            
            return Response({
                'message': f'Invitation email has been resent to {target_user.email}.'
            })
            
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_role_info(self, user):
        """Get role information for the user"""
        if user.is_superuser:
            return {'role_label': 'Super User'}
        
        memberships = user.property_memberships.all()
        if not memberships.exists():
            return {'role_label': 'User'}
        
        membership = memberships.first()
        role_labels = {
            PropertyUserRole.GROUP_ADMIN: 'Property Group Admin',
            PropertyUserRole.PROPERTY_ADMIN: 'Property Admin',
            PropertyUserRole.TENANT: 'Tenant',
        }
        
        role_info = {
            'role_label': role_labels.get(membership.role, membership.role),
            'property_name': None,
            'property_group_name': None,
        }
        
        if membership.property:
            role_info['property_name'] = membership.property.name
            if membership.property.property_group:
                role_info['property_group_name'] = membership.property.property_group.name
        elif membership.property_group:
            role_info['property_group_name'] = membership.property_group.name
        
        return role_info


class AppListView(APIView):
    """
    API endpoint to list all apps that the current user has access to.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Return list of apps the user has access to.
        Superusers see all active apps (handled by get_accessible_apps()).
        """
        user = request.user
        apps = user.get_accessible_apps()
        
        app_list = [
            {
                'id': app.id,
                'name': app.name,
                'slug': app.slug,
                'description': app.description,
                'is_active': app.is_active
            }
            for app in apps
        ]
        
        return Response({
            'apps': app_list,
            'count': len(app_list)
        })


class TokenIntrospectionView(APIView):
    """
    Token introspection endpoint for Retail Studio (and other services)
    to validate tokens and get current user information.
    
    This endpoint can be used by external services to:
    1. Verify that a token is valid and not expired
    2. Get fresh user data (in case token claims are stale)
    3. Get detailed user permissions and memberships
    4. Get app context information
    
    Requires a valid JWT token in the Authorization header or cookie.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """
        Return current user information for token validation.
        
        Returns:
            JSON response with:
            - active: bool - whether the token/user is active
            - user_id: int - the user's ID
            - email: str - the user's email
            - first_name: str - the user's first name
            - last_name: str - the user's last name
            - is_superuser: bool - superuser flag
            - is_staff: bool - staff flag
            - is_active: bool - active flag
            - role: str - the user's primary role
            - memberships: list - detailed membership information
            - app: dict - current app information (from token)
            - accessible_apps: list - all apps user has access to
        """
        user = request.user
        
        # Get app from token if available
        app_info = None
        if hasattr(request, 'auth') and request.auth:
            app_id = request.auth.get('app_id')
            if app_id:
                from .models import App
                try:
                    app = App.objects.get(id=app_id)
                    app_info = {
                        'id': app.id,
                        'name': app.name,
                        'slug': app.slug
                    }
                except App.DoesNotExist:
                    pass
        
        # Get all accessible apps
        accessible_apps = [
            {
                'id': app.id,
                'name': app.name,
                'slug': app.slug
            }
            for app in user.get_accessible_apps()
        ]
        
        return Response({
            'active': True,
            'user_id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_superuser': user.is_superuser,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'role': self._get_user_role(user),
            'memberships': self._get_user_memberships(user),
            'app': app_info,
            'accessible_apps': accessible_apps,
            'iss': 'campaign-planner',
        })
    
    def _get_user_role(self, user):
        """Get the user's primary role"""
        if user.is_superuser:
            return 'super_user'
        
        memberships = user.property_memberships.all()
        if not memberships.exists():
            return None
        
        # Return the highest privilege role
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
    
    def _get_user_memberships(self, user):
        """Get all user memberships for granular permission checks"""
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