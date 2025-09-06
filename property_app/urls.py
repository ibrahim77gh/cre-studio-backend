from property_app.views import CampaignSubmissionViewSet, PropertyViewSet, PropertyGroupViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'campaigns', CampaignSubmissionViewSet, basename='campaign')
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'property-groups', PropertyGroupViewSet, basename='property-group')

urlpatterns = router.urls