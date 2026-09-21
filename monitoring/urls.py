from django.urls import include, path
from rest_framework.routers import DefaultRouter

from monitoring.auth_views import LoginView, LogoutView, MeView
from monitoring.views import (
    AlertEventViewSet,
    DashboardView,
    HealthCheckResultViewSet,
    HealthView,
    MonitoredEndpointViewSet,
)

router = DefaultRouter()
router.register("endpoints", MonitoredEndpointViewSet, basename="endpoint")
router.register("checks", HealthCheckResultViewSet, basename="check")
router.register("alerts", AlertEventViewSet, basename="alert")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("", include(router.urls)),
]
