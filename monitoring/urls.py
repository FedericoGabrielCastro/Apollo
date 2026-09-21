from django.urls import include, path
from rest_framework.routers import DefaultRouter

from monitoring.auth_views import LoginView, LogoutView, MeView
from monitoring.views import (
    AlertEventViewSet,
    DashboardView,
    ExportView,
    HealthCheckResultViewSet,
    HealthView,
    IncidentViewSet,
    MonitoredEndpointViewSet,
    PublicStatusView,
    StatusPageConfigView,
    TagViewSet,
)

router = DefaultRouter()
router.register("endpoints", MonitoredEndpointViewSet, basename="endpoint")
router.register("checks", HealthCheckResultViewSet, basename="check")
router.register("alerts", AlertEventViewSet, basename="alert")
router.register("incidents", IncidentViewSet, basename="incident")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("status/public/", PublicStatusView.as_view(), name="public-status"),
    path("status/config/", StatusPageConfigView.as_view(), name="status-config"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("exports/<str:resource>.csv", ExportView.as_view(), name="exports-csv"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", MeView.as_view(), name="auth-me"),
    path("", include(router.urls)),
]
