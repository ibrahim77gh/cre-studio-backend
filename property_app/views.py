from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    ClientNotificationSerializer,
    CreativeAssetSerializer,
    CampaignCommentSerializer,
    CampaignCommentAttachmentSerializer,
    CampaignStatsSerializer,
    CampaignBudgetSerializer,
    PlatformSerializer,
    PlatformBudgetSerializer,
    PromptConfigurationSerializer,
    PromptConfigurationListSerializer
)
from .models import (
    Campaign, Property, PropertyGroup, UserPropertyMembership,
    PropertyUserRole, ClientNotification, CreativeAsset, CampaignComment,
    CampaignCommentAttachment, CampaignBudget, Platform, PlatformBudget, PromptConfiguration
)
from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from .utils import send_comment_notifications
from .tasks import process_campaign_ai_content


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
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsAuthenticated]
    pagination_class = PageNumberPagination

    def get_queryset(self):
        """
        Return campaigns filtered by property_id for list views.
        For detail views (when pk is provided), return all campaigns to allow lookup by ID.
        Supports filtering by approval_status and ordering by created_at (descending).
        """
        # For detail views (retrieve, update, delete) and custom detail actions, allow access to any campaign
        if self.action in ['retrieve', 'update', 'partial_update', 'destroy', 'budget_detail', 'add_platform_budget', 'update_platform_budget', 'process_ai_content']:
            return Campaign.objects.all()
        
        # For list views, require property_id filter
        property_id = self.request.query_params.get("property_id")
        if not property_id:
            return Campaign.objects.none()
        
        queryset = Campaign.objects.filter(property_id=property_id)
        
        # Filter by approval_status if provided
        approval_status = self.request.query_params.get("approval_status")
        if approval_status:
            queryset = queryset.filter(approval_status=approval_status)
        
        # Order by created_at descending (newest first)
        queryset = queryset.order_by('-created_at')
        
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

    @action(detail=True, methods=['post'])
    def process_ai_content(self, request, pk=None):
        """
        Trigger AI content processing for a specific campaign.
        Usage: POST /api/campaigns/{id}/process_ai_content/
        """
        campaign = self.get_object()
        
        # Check if campaign has pmcb_form_data to process
        if not campaign.pmcb_form_data:
            return Response(
                {'error': 'Campaign does not have PMCB form data to process'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if AI processing is already in progress
        if campaign.ai_processing_status == Campaign.AIProcessingStatus.PROCESSING:
            return Response(
                {'error': 'AI processing is already in progress for this campaign'}, 
                status=status.HTTP_409_CONFLICT
            )
        
        # Allow reprocessing even if already completed (user may have updated PMCB form data)
        # Reset processing status to pending when starting new processing
        if campaign.ai_processing_status == Campaign.AIProcessingStatus.COMPLETED:
            # Reset the status to allow reprocessing
            campaign.ai_processing_status = Campaign.AIProcessingStatus.PENDING
            campaign.ai_processing_error = None
            campaign.save(update_fields=['ai_processing_status', 'ai_processing_error'])
        
        try:
            # Trigger the Celery task for AI processing
            task = process_campaign_ai_content.delay(campaign.id)
            
            return Response(
                {
                    'message': 'AI content processing started successfully',
                    'campaign_id': campaign.id,
                    'task_id': task.id,
                    'status': 'processing_started'
                }, 
                status=status.HTTP_202_ACCEPTED
            )
            
        except Exception as e:
            return Response(
                {'error': f'Failed to start AI processing: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _has_campaign_access(self, user, campaign):
        """Check if user has access to the campaign"""
        if user.is_superuser:
            return True
        
        # Check if user is the campaign creator
        if campaign.user == user:
            return True
        
        # Check property membership
        try:
            membership = UserPropertyMembership.objects.get(
                user=user,
                property=campaign.property
            )
            return True
        except UserPropertyMembership.DoesNotExist:
            pass
        
        # Check group membership
        try:
            membership = UserPropertyMembership.objects.get(
                user=user,
                property_group=campaign.property.property_group
            )
            return True
        except UserPropertyMembership.DoesNotExist:
            pass
        
        return False

    @action(detail=True, methods=['get', 'patch'], url_path='budget', url_name='campaign-budget')
    def budget_detail(self, request, pk=None):
        """
        Get or update campaign budget
        GET /api/campaigns/{id}/budget/
        PATCH /api/campaigns/{id}/budget/
        """
        campaign = self.get_object()
        
        # Check permissions
        if not self._has_campaign_access(request.user, campaign):
            raise PermissionDenied("You don't have access to this campaign's budget.")
        
        budget, created = CampaignBudget.objects.get_or_create(campaign=campaign)
        
        if request.method == 'GET':
            serializer = CampaignBudgetSerializer(budget)
            return Response(serializer.data)
        
        elif request.method == 'PATCH':
            serializer = CampaignBudgetSerializer(budget, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='budget/platforms/')
    def add_platform_budget(self, request, pk=None):
        """
        Add a platform budget to campaign
        POST /api/campaigns/{id}/budget/platforms/
        """
        campaign = self.get_object()
        
        # Check permissions
        if not self._has_campaign_access(request.user, campaign):
            raise PermissionDenied("You don't have access to this campaign's budget.")
        
        budget, created = CampaignBudget.objects.get_or_create(campaign=campaign)
        platform_id = request.data.get('platform_id')
        gross_amount = request.data.get('gross_amount', 0)
        
        if not platform_id:
            return Response(
                {'error': 'platform_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            platform = Platform.objects.get(id=platform_id)
        except Platform.DoesNotExist:
            return Response(
                {'error': 'Platform not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        platform_budget, created = PlatformBudget.objects.get_or_create(
            campaign_budget=budget,
            platform=platform
        )
        platform_budget.gross_amount = gross_amount
        platform_budget.save()
        
        serializer = PlatformBudgetSerializer(platform_budget)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=['patch'], url_path='budget/platform/(?P<platform_id>[^/.]+)/')
    def update_platform_budget(self, request, pk=None, platform_id=None):
        """
        Update specific platform budget
        PATCH /api/campaigns/{id}/budget/platform/{platform_id}/
        """
        campaign = self.get_object()
        
        # Check permissions
        if not self._has_campaign_access(request.user, campaign):
            raise PermissionDenied("You don't have access to this campaign's budget.")
        
        budget, created = CampaignBudget.objects.get_or_create(campaign=campaign)
        
        try:
            platform = Platform.objects.get(id=platform_id)
            platform_budget = PlatformBudget.objects.get(
                campaign_budget=budget,
                platform=platform
            )
        except (Platform.DoesNotExist, PlatformBudget.DoesNotExist):
            return Response(
                {'error': 'Platform budget not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PlatformBudgetSerializer(platform_budget, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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


class PlatformViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing advertising platforms.
    Read-only for regular users, superusers can manage platforms via admin.
    """
    queryset = Platform.objects.filter(is_active=True)
    serializer_class = PlatformSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        """Return only active platforms"""
        return Platform.objects.filter(is_active=True).order_by('name')


class PromptConfigurationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AI prompt configurations.
    Only superusers can create, update, or delete prompts.
    """
    queryset = PromptConfiguration.objects.all()
    serializer_class = PromptConfigurationSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        """
        Return prompt configurations.
        Superusers can see all prompts.
        Regular users can only view prompts (but not edit/delete).
        """
        queryset = PromptConfiguration.objects.all().select_related('property', 'created_by', 'updated_by')
        
        # Filter by property_id if provided
        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)
        
        # Filter by prompt_type if provided
        prompt_type = self.request.query_params.get('prompt_type')
        if prompt_type:
            queryset = queryset.filter(prompt_type=prompt_type)
        
        # Filter by is_active if provided
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active_bool)
        
        return queryset.order_by('-created_at')
    
    def get_serializer_class(self):
        """Use list serializer for list action, detail serializer for others"""
        if self.action == 'list':
            return PromptConfigurationListSerializer
        return PromptConfigurationSerializer
    
    def perform_create(self, serializer):
        """Only superusers can create prompts"""
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only super users can create prompt configurations.")
        serializer.save()
    
    def perform_update(self, serializer):
        """Only superusers can update prompts"""
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only super users can update prompt configurations.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """Only superusers can delete prompts"""
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only super users can delete prompt configurations.")
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def available_variables(self, request):
        """
        Get available variables for prompt templates.
        This helps the frontend display available variables to users.
        """
        variables = {
            'meta_ad': {
                'messaging': 'Campaign messaging and key points',
                'primary_goal': 'Primary goal of the campaign (e.g., awareness, conversions)',
                'target_audience': 'Target audience description',
                'campaign_name': 'Name of the campaign or key event'
            },
            'google_display': {
                'messaging': 'Campaign messaging and key points',
                'primary_goal': 'Primary goal of the campaign (e.g., awareness, conversions)',
                'target_audience': 'Target audience description',
                'campaign_name': 'Name of the campaign or key event'
            }
        }
        
        prompt_type = request.query_params.get('prompt_type')
        if prompt_type and prompt_type in variables:
            return Response({
                'prompt_type': prompt_type,
                'variables': variables[prompt_type]
            })
        
        return Response(variables)
    
    @action(detail=False, methods=['get'])
    def for_property(self, request):
        """
        Get the appropriate prompt configuration for a specific property and prompt type.
        Returns property-specific prompt if available, otherwise returns default prompt.
        """
        property_id = request.query_params.get('property_id')
        prompt_type = request.query_params.get('prompt_type')
        
        if not property_id or not prompt_type:
            return Response(
                {'error': 'Both property_id and prompt_type parameters are required'},
                status=400
            )
        
        try:
            property_obj = Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return Response(
                {'error': 'Property not found'},
                status=404
            )
        
        # Get appropriate prompt using the model method
        prompt = PromptConfiguration.get_prompt_for_campaign(prompt_type, property_obj)
        
        if not prompt:
            return Response(
                {'error': f'No prompt configuration found for type {prompt_type}'},
                status=404
            )
        
        serializer = PromptConfigurationSerializer(prompt, context={'request': request})
        return Response(serializer.data)
