from property_app.views import CampaignSubmissionViewSet, PropertyViewSet, PropertyGroupViewSet, ClientNotificationViewSet, CreativeAssetViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'campaigns', CampaignSubmissionViewSet, basename='campaign')
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'property-groups', PropertyGroupViewSet, basename='property-group')
router.register(r'notifications', ClientNotificationViewSet, basename='notification')
router.register(r'assets', CreativeAssetViewSet, basename='asset')

urlpatterns = router.urls