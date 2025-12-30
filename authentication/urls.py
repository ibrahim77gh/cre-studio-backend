from django.urls import include, path, re_path
from .views import (
    CustomProviderAuthView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    LogoutView,
    AdminUserViewSet,
    UserManagementViewSet,
    UserProfileViewSet,
    UserStatsView,
    AcceptInvitationView,
    ResendInvitationView,
    TokenIntrospectionView,
    AppListView,
    SwitchAppView,
)
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'manage-users', AdminUserViewSet, basename='manage-user')
router.register(r'user-management', UserManagementViewSet, basename='user-management')
router.register(r'profile', UserProfileViewSet, basename='profile')

urlpatterns = [
    re_path(
        r'^o/(?P<provider>\S+)/$',
        CustomProviderAuthView.as_view(),
        name='provider-auth'
    ),
    path('jwt/create/', CustomTokenObtainPairView.as_view()),
    path('jwt/refresh/', CustomTokenRefreshView.as_view()),
    path('jwt/verify/', CustomTokenVerifyView.as_view()),
    path('jwt/introspect/', TokenIntrospectionView.as_view(), name='token-introspect'),
    path('logout/', LogoutView.as_view()),
    path('user-stats/', UserStatsView.as_view(), name='user-stats'),
    path('accept-invitation/<str:token>/', AcceptInvitationView.as_view(), name='accept-invitation'),
    path('resend-invitation/<int:user_id>/', ResendInvitationView.as_view(), name='resend-invitation'),
    path('apps/', AppListView.as_view(), name='app-list'),
    path('switch-app/', SwitchAppView.as_view(), name='switch-app'),
    path('', include(router.urls)),
]