from property_app.views import CampaignSubmissionViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'campaigns', CampaignSubmissionViewSet, basename='campaign')

urlpatterns = router.urls