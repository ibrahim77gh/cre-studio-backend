from django.urls import path
from property_app.views import (
    CampaignSubmissionViewSet,
    PropertyViewSet,
    PropertyGroupViewSet,
    ClientNotificationViewSet,
    CreativeAssetViewSet,
    CampaignCommentViewSet,
    CampaignCommentAttachmentViewSet,
    PlatformViewSet,
    PromptConfigurationViewSet,
    contact_us,
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r"campaigns", CampaignSubmissionViewSet, basename="campaign")
router.register(r"properties", PropertyViewSet, basename="property")
router.register(r"property-groups", PropertyGroupViewSet, basename="property-group")
router.register(r"notifications", ClientNotificationViewSet, basename="notification")
router.register(r"assets", CreativeAssetViewSet, basename="asset")
router.register(r"comments", CampaignCommentViewSet, basename="comment")
router.register(
    r"comment-attachments",
    CampaignCommentAttachmentViewSet,
    basename="comment-attachment",
)
router.register(r"platforms", PlatformViewSet, basename="platform")
router.register(
    r"prompt-configurations",
    PromptConfigurationViewSet,
    basename="prompt-configuration",
)

urlpatterns = [
    # Simple public contact endpoint
    path("contact/", contact_us, name="contact-us"),
] + router.urls