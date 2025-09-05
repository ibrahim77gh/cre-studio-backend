from property_app.serializers import (
    CampaignSubmissionSerializer,
    PropertyGroupSerializer,
    PropertySerializer,
    CampaignSubmissionSerializer
)
from .models import Campaign, Property, PropertyGroup
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied
from authentication.permissions import IsCREUser, IsPropertyGroupUser, IsPropertyUser, IsClientUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import action


class PropertyViewSet(viewsets.ModelViewSet):
    queryset = Property.objects.all()
    serializer_class = PropertySerializer

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
    
    @action(
        detail=True,
        methods=["post", "put", "patch"],
        url_path="budget",
        permission_classes=[IsAuthenticated, IsClientUser],
    )
    def budget(self, request, pk=None):
        """
        Create or update the CampaignBudget for the given campaign (pk).
        Send any subset of budget fields in the request body (partial updates allowed).
        """
        campaign = self.get_object()  # ensures campaign exists and permission checks run
        budget_obj, created = CampaignBudget.objects.get_or_create(campaign=campaign)
        serializer = self.CampaignBudgetSerializer(budget_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class PropertyGroupViewSet(viewsets.ModelViewSet):
    queryset = PropertyGroup.objects.all()
    serializer_class = PropertyGroupSerializer

    def get_queryset(self):
        property_group_id = self.kwargs.get('pk', None)
        if property_group_id:
            return PropertyGroup.objects.filter(id=property_group_id)
