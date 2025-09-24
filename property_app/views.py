from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    CampaignSubmissionSerializer,
    ClientNotificationSerializer,
    CreativeAssetSerializer
)
from .models import Campaign, Property, PropertyGroup, UserPropertyMembership, PropertyUserRole, ClientNotification, CreativeAsset
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action
from rest_framework.response import Response


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


class ClientNotificationViewSet(viewsets.ModelViewSet):
    serializer_class = ClientNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientNotification.objects.filter(user=self.request.user)

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
