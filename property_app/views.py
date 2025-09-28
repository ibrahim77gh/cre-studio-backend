from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    ClientNotificationSerializer,
    CreativeAssetSerializer,
    CampaignCommentSerializer
)
from .models import (
    Campaign, Property, PropertyGroup, UserPropertyMembership,
    PropertyUserRole, ClientNotification, CreativeAsset, CampaignComment
)
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response
from .utils import send_comment_notifications


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

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

    def get_queryset(self):
        queryset = Campaign.objects.all()
        property_id = self.request.query_params.get("property_id")
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        return queryset


class PropertyGroupViewSet(viewsets.ModelViewSet):
    queryset = PropertyGroup.objects.all()
    serializer_class = PropertyGroupSerializer

    def get_queryset(self):
        property_group_id = self.kwargs.get('pk', None)
        if property_group_id:
            return PropertyGroup.objects.filter(id=property_group_id)
        return PropertyGroup.objects.all()


class ClientNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ClientNotificationSerializer
    permission_classes = [IsAuthenticated]

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
    ViewSet for managing campaign comments with threading support.
    """
    serializer_class = CampaignCommentSerializer
    permission_classes = [IsAuthenticated]

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
