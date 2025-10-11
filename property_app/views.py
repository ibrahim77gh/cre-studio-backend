from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    ClientNotificationSerializer,
    CreativeAssetSerializer,
    CampaignCommentSerializer,
    CampaignCommentAttachmentSerializer,
    CampaignStatsSerializer,
    ConfigurationSerializer,
    ConfigurationListSerializer,
    ConfigurationPreviewSerializer
)
from .models import (
    Campaign, Property, PropertyGroup, UserPropertyMembership,
    PropertyUserRole, ClientNotification, CreativeAsset, CampaignComment,
    CampaignCommentAttachment, Configuration
)
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .utils import send_comment_notifications


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        """
        - Superuser: return all properties
        - Group admin: return all properties for groups where the user has group_admin role
        - Property admin: return properties where the user has property_admin role
        - Tenant: return properties where the user has tenant role
        - Otherwise: return no properties
        """
        user = self.request.user

        if user.is_superuser:
            qs = Property.objects.all()
        else:
            # Check for group admin roles
            group_ids_qs = UserPropertyMembership.objects.filter(
                user=user,
                role=PropertyUserRole.GROUP_ADMIN,
                property_group__isnull=False
            ).values_list("property_group_id", flat=True)

            if group_ids_qs.exists():
                qs = Property.objects.filter(property_group_id__in=group_ids_qs)
            else:
                # Check for property admin roles
                prop_ids_qs = UserPropertyMembership.objects.filter(
                    user=user,
                    role=PropertyUserRole.PROPERTY_ADMIN,
                    property__isnull=False
                ).values_list("property_id", flat=True)
                
                if prop_ids_qs.exists():
                    qs = Property.objects.filter(id__in=prop_ids_qs)
                else:
                    # Check for tenant roles
                    tenant_prop_ids_qs = UserPropertyMembership.objects.filter(
                        user=user,
                        role=PropertyUserRole.TENANT,
                        property__isnull=False
                    ).values_list("property_id", flat=True)
                    
                    if tenant_prop_ids_qs.exists():
                        qs = Property.objects.filter(id__in=tenant_prop_ids_qs)
                    else:
                        qs = Property.objects.none()

        return qs

class CampaignSubmissionViewSet(viewsets.ModelViewSet):
    """
    A ViewSet to handle the creation of a Campaign from the PMCB form.
    Only allows authenticated Client Users to submit data.
    """
    serializer_class = CampaignSubmissionSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        Return campaigns filtered by property_id for list views.
        For detail views (when pk is provided), return all campaigns to allow lookup by ID.
        """
        # For detail views (retrieve, update, delete), allow access to any campaign
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            return Campaign.objects.all()
        
        # For list views, require property_id filter
        property_id = self.request.query_params.get("property_id")
        if not property_id:
            return Campaign.objects.none()
        
        queryset = Campaign.objects.filter(property_id=property_id)
        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Get campaign statistics for a specific property.
        Usage: GET /api/campaigns/stats/?property_id=123
        """
        property_id = request.query_params.get('property_id')
        if not property_id:
            return Response(
                {'error': 'property_id parameter is required'}, 
                status=400
            )
        
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response(
                {'error': 'Property not found'}, 
                status=404
            )
        
        # Get all campaigns for this property
        campaigns = Campaign.objects.filter(property_id=property_id)
        
        # Calculate statistics
        total_campaigns = campaigns.count()
        
        # Approval status counts
        pending_count = campaigns.filter(approval_status=Campaign.ApprovalStatus.PENDING).count()
        admin_approved_count = campaigns.filter(approval_status=Campaign.ApprovalStatus.ADMIN_APPROVED).count()
        client_approved_count = campaigns.filter(approval_status=Campaign.ApprovalStatus.CLIENT_APPROVED).count()
        fully_approved_count = campaigns.filter(approval_status=Campaign.ApprovalStatus.FULLY_APPROVED).count()
        
        # Prepare response data
        stats_data = {
            'property_id': property_obj.id,
            'property_name': property_obj.name,
            'total_campaigns': total_campaigns,
            'pending_count': pending_count,
            'admin_approved_count': admin_approved_count,
            'client_approved_count': client_approved_count,
            'fully_approved_count': fully_approved_count,
        }
        
        serializer = CampaignStatsSerializer(stats_data)
        return Response(serializer.data)


class PropertyGroupViewSet(viewsets.ModelViewSet):
    queryset = PropertyGroup.objects.all()
    serializer_class = PropertyGroupSerializer
    pagination_class = None

    def get_queryset(self):
        property_group_id = self.kwargs.get('pk', None)
        if property_group_id:
            return PropertyGroup.objects.filter(id=property_group_id)
        return PropertyGroup.objects.all()


class ClientNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ClientNotificationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        notifications = ClientNotification.objects.filter(user=self.request.user)
        return notifications

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Notification marked as read'})


class CreativeAssetViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing individual creative assets.
    Provides full CRUD operations for assets.
    Frontend handles access permissions by only showing accessible campaigns.
    """
    queryset = CreativeAsset.objects.all()
    serializer_class = CreativeAssetSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """
        Return assets with optional filtering by campaign_id.
        """
        queryset = CreativeAsset.objects.all().select_related('campaign__property')
        
        # Filter by campaign_id if provided in query params
        campaign_id = self.request.query_params.get('campaign_id')
        if campaign_id:
            queryset = queryset.filter(campaign_id=campaign_id)

        return queryset.order_by('-uploaded_at')

    @action(detail=False, methods=['get'])
    def by_campaign(self, request):
        """
        Custom action to get all assets for a specific campaign.
        Usage: GET /api/assets/by_campaign/?campaign_id=123
        """
        campaign_id = request.query_params.get('campaign_id')
        if not campaign_id:
            return Response(
                {'error': 'campaign_id parameter is required'}, 
                status=400
            )
        
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'}, 
                status=404
            )
        
        assets = CreativeAsset.objects.filter(campaign=campaign).order_by('-uploaded_at')
        serializer = self.get_serializer(assets, many=True)
        
        return Response({
            'campaign_id': campaign_id,
            'campaign_name': str(campaign),
            'assets': serializer.data
        })


class CampaignCommentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing campaign comments with threading support and file uploads.
    """
    serializer_class = CampaignCommentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """
        Return comments for campaigns the user has access to.
        Any user with any role (tenant, property admin, or group admin) can see all comments.
        """
        user = self.request.user
        
        if user.is_superuser:
            return CampaignComment.objects.all().select_related('user', 'campaign', 'parent_comment')
        
        # Get campaigns the user has access to with any role
        accessible_campaign_ids = set()
        
        # Campaigns where user has any role (tenant, property admin, or group admin)
        user_campaigns = Campaign.objects.filter(
            property__memberships__user=user,
            property__memberships__role__in=[
                PropertyUserRole.TENANT, 
                PropertyUserRole.PROPERTY_ADMIN, 
                PropertyUserRole.GROUP_ADMIN
            ]
        ).values_list('id', flat=True)
        accessible_campaign_ids.update(user_campaigns)
        
        # Also include campaigns where user is group admin for the property group
        group_admin_campaigns = Campaign.objects.filter(
            property__property_group__memberships__user=user,
            property__property_group__memberships__role=PropertyUserRole.GROUP_ADMIN
        ).values_list('id', flat=True)
        accessible_campaign_ids.update(group_admin_campaigns)
        
        return CampaignComment.objects.filter(
            campaign_id__in=accessible_campaign_ids
        ).select_related('user', 'campaign', 'parent_comment').order_by('created_at')

    def perform_create(self, serializer):
        """Create a new comment and send notifications"""
        comment = serializer.save()
        
        # Send notifications to relevant users
        send_comment_notifications(comment)

    @action(detail=True, methods=['post'])
    def mark_resolved(self, request, pk=None):
        """Mark a comment as resolved (only by comment author or admins)"""
        comment = self.get_object()
        user = request.user
        
        # Check if user can resolve this comment
        can_resolve = (
            comment.user == user or
            user.is_superuser or
            user.is_property_admin(comment.campaign.property) or
            user.is_group_admin(comment.campaign.property.property_group)
        )
        
        if not can_resolve:
            raise PermissionDenied("You don't have permission to resolve this comment.")
        
        comment.is_resolved = True
        comment.save()
        
        return Response({'status': 'Comment marked as resolved'})

    @action(detail=False, methods=['get'])
    def by_campaign(self, request):
        """Get all comments for a specific campaign"""
        campaign_id = request.query_params.get('campaign_id')
        if not campaign_id:
            return Response(
                {'error': 'campaign_id parameter is required'}, 
                status=400
            )
        
        try:
            campaign = Campaign.objects.get(id=campaign_id)
        except Campaign.DoesNotExist:
            return Response(
                {'error': 'Campaign not found'}, 
                status=404
            )
        
        # Check if user has access to this campaign
        user = request.user
        has_access = (
            user.is_superuser or
            user.property_memberships.filter(
                property=campaign.property,
                role__in=[
                    PropertyUserRole.TENANT, 
                    PropertyUserRole.PROPERTY_ADMIN, 
                    PropertyUserRole.GROUP_ADMIN
                ]
            ).exists() or
            user.property_memberships.filter(
                property_group=campaign.property.property_group,
                role=PropertyUserRole.GROUP_ADMIN
            ).exists()
        )
        
        if not has_access:
            raise PermissionDenied("You don't have access to this campaign's comments.")
        
        # Get root comments (not replies) with their replies
        root_comments = self.get_queryset().filter(
            campaign=campaign,
            parent_comment__isnull=True
        ).order_by('created_at')
        
        serializer = self.get_serializer(root_comments, many=True)
        
        return Response({
            'campaign_id': campaign_id,
            'campaign_name': str(campaign),
            'comments': serializer.data
        })


class CampaignCommentAttachmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing comment attachments.
    """
    serializer_class = CampaignCommentAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def get_queryset(self):
        """
        Return attachments for comments the user has access to.
        """
        user = self.request.user
        
        if user.is_superuser:
            return CampaignCommentAttachment.objects.all().select_related('comment__campaign', 'comment__user')
        
        # Get campaigns the user has access to
        accessible_campaign_ids = set()
        
        # Campaigns where user has any role
        user_campaigns = Campaign.objects.filter(
            property__memberships__user=user,
            property__memberships__role__in=[
                PropertyUserRole.TENANT, 
                PropertyUserRole.PROPERTY_ADMIN, 
                PropertyUserRole.GROUP_ADMIN
            ]
        ).values_list('id', flat=True)
        accessible_campaign_ids.update(user_campaigns)
        
        # Also include campaigns where user is group admin
        group_admin_campaigns = Campaign.objects.filter(
            property__property_group__memberships__user=user,
            property__property_group__memberships__role=PropertyUserRole.GROUP_ADMIN
        ).values_list('id', flat=True)
        accessible_campaign_ids.update(group_admin_campaigns)
        
        return CampaignCommentAttachment.objects.filter(
            comment__campaign_id__in=accessible_campaign_ids
        ).select_related('comment__campaign', 'comment__user').order_by('-uploaded_at')

    @action(detail=False, methods=['get'])
    def by_comment(self, request):
        """Get all attachments for a specific comment"""
        comment_id = request.query_params.get('comment_id')
        if not comment_id:
            return Response(
                {'error': 'comment_id parameter is required'}, 
                status=400
            )
        
        try:
            comment = CampaignComment.objects.get(id=comment_id)
        except CampaignComment.DoesNotExist:
            return Response(
                {'error': 'Comment not found'}, 
                status=404
            )
        
        # Check if user has access to this comment's campaign
        user = request.user
        has_access = (
            user.is_superuser or
            user.property_memberships.filter(
                property=comment.campaign.property,
                role__in=[
                    PropertyUserRole.TENANT, 
                    PropertyUserRole.PROPERTY_ADMIN, 
                    PropertyUserRole.GROUP_ADMIN
                ]
            ).exists() or
            user.property_memberships.filter(
                property_group=comment.campaign.property.property_group,
                role=PropertyUserRole.GROUP_ADMIN
            ).exists()
        )
        
        if not has_access:
            raise PermissionDenied("You don't have access to this comment's attachments.")
        
        attachments = self.get_queryset().filter(comment=comment)
        serializer = self.get_serializer(attachments, many=True)
        
        return Response({
            'comment_id': comment_id,
            'attachments': serializer.data
        })


class ConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing system configurations (AI prompts)
    Only super users can manage configurations
    """
    queryset = Configuration.objects.all()
    serializer_class = ConfigurationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination
    
    def get_queryset(self):
        """Filter configurations based on user permissions and query parameters"""
        queryset = Configuration.objects.all()
        
        # Filter by config type if provided
        config_type = self.request.query_params.get('config_type')
        if config_type:
            queryset = queryset.filter(config_type=config_type)
        
        # Filter by property if provided
        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        
        # Filter by scope (global vs property-specific)
        scope = self.request.query_params.get('scope')
        if scope == 'global':
            queryset = queryset.filter(property__isnull=True)
        elif scope == 'property':
            queryset = queryset.filter(property__isnull=False)
        
        return queryset.order_by('config_type', 'property__name', 'name')
    
    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return ConfigurationListSerializer
        elif self.action == 'preview':
            return ConfigurationPreviewSerializer
        return ConfigurationSerializer
    
    def perform_create(self, serializer):
        """Set the created_by field to the current user"""
        serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Update the configuration"""
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        """
        Preview a configuration with sample variables
        """
        config = self.get_object()
        variables = request.data.get('variables', {})
        
        try:
            resolved_system_prompt = config.get_resolved_prompt(**variables)
            resolved_user_prompt = config.get_resolved_user_prompt(**variables)
            
            return Response({
                'system_prompt': resolved_system_prompt,
                'user_prompt': resolved_user_prompt,
                'variables': config.available_variables
            })
        except Exception as e:
            return Response({
                'error': f'Error resolving variables: {str(e)}'
            }, status=400)
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """
        Get available configuration types
        """
        return Response({
            'config_types': [
                {'value': choice[0], 'label': choice[1]}
                for choice in Configuration.ConfigType.choices
            ]
        })
    
    @action(detail=False, methods=['get'])
    def variables(self, request):
        """
        Get available variables for a specific configuration type
        """
        config_type = request.query_params.get('config_type')
        if not config_type:
            return Response({'error': 'config_type parameter is required'}, status=400)
        
        # Define default variables for each configuration type
        default_variables = {
            Configuration.ConfigType.META_AD_COPYWRITER: [
                {'name': 'messaging', 'description': 'The main messaging for the campaign'},
                {'name': 'primary_goal', 'description': 'The primary goal of the campaign'},
                {'name': 'target_audience', 'description': 'The target audience for the campaign'},
                {'name': 'campaign_name', 'description': 'The name of the campaign'},
                {'name': 'property_name', 'description': 'The name of the property'},
                {'name': 'brand_tone', 'description': 'The brand tone and voice'},
            ],
            Configuration.ConfigType.GOOGLE_ADS_COPYWRITER: [
                {'name': 'messaging', 'description': 'The main messaging for the campaign'},
                {'name': 'primary_goal', 'description': 'The primary goal of the campaign'},
                {'name': 'target_audience', 'description': 'The target audience for the campaign'},
                {'name': 'campaign_name', 'description': 'The name of the campaign'},
                {'name': 'property_name', 'description': 'The name of the property'},
                {'name': 'brand_tone', 'description': 'The brand tone and voice'},
            ],
            Configuration.ConfigType.CUSTOM: [
                {'name': 'custom_variable_1', 'description': 'Custom variable 1'},
                {'name': 'custom_variable_2', 'description': 'Custom variable 2'},
            ]
        }
        
        variables = default_variables.get(config_type, [])
        return Response({'variables': variables})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """
        Get active configurations for a specific type and optionally property
        """
        config_type = request.query_params.get('config_type')
        property_id = request.query_params.get('property_id')
        
        if not config_type:
            return Response({'error': 'config_type parameter is required'}, status=400)
        
        # Try to get property-specific configuration first
        config = None
        if property_id:
            try:
                property_obj = Property.objects.get(id=property_id)
                config = Configuration.get_configuration(config_type, property_obj)
            except Property.DoesNotExist:
                return Response({'error': 'Property not found'}, status=404)
        
        # Fallback to global configuration if no property-specific one found
        if not config:
            config = Configuration.get_configuration(config_type)
        
        if not config:
            return Response({'error': 'No active configuration found'}, status=404)
        
        serializer = self.get_serializer(config)
        return Response(serializer.data)
    
    def get_permissions(self):
        """
        Only super users can manage configurations
        """
        if self.action in ['list', 'retrieve', 'types', 'variables', 'active', 'preview']:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def has_permission(self, request, view):
        """
        Check if user has permission to perform the action
        """
        if request.user.is_superuser:
            return True
        
        # Non-super users can only view active configurations
        if view.action in ['list', 'retrieve', 'types', 'variables', 'active', 'preview']:
            return True
        
        return False
