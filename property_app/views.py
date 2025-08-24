from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from authentication.permissions import IsCREUser, IsPropertyGroupUser, IsPropertyUser, IsClientUser
from property_app.serializers import CampaignSubmissionSerializer
from .models import Campaign, Property
from rest_framework.permissions import IsAuthenticated

class CampaignSubmissionViewSet(viewsets.ModelViewSet):
    """
    A ViewSet to handle the creation of a Campaign from the PMCB form.
    Only allows authenticated Client Users to submit data.
    """
    queryset = Campaign.objects.all()
    serializer_class = CampaignSubmissionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['post']