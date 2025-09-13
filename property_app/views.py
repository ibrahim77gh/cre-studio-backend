from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    CampaignSubmissionSerializer
)
from .models import Campaign, Property, PropertyGroup, UserPropertyMembership, PropertyUserRole
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from authentication.permissions import IsCREUser, IsPropertyGroupUser, IsPropertyUser, IsClientUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        - Superuser: return all properties
        - Group admin: return all properties for groups where the user has group_admin role
        - Property admin: return properties where the user has property_admin role
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
        subdomain = self.request.query_params.get("subdomain")
        if subdomain:
            queryset = queryset.filter(property__subdomain=subdomain)
        return queryset


class PropertyGroupViewSet(viewsets.ModelViewSet):
    queryset = PropertyGroup.objects.all()
    serializer_class = PropertyGroupSerializer

    def get_queryset(self):
        property_group_id = self.kwargs.get('pk', None)
        if property_group_id:
            return PropertyGroup.objects.filter(id=property_group_id)
