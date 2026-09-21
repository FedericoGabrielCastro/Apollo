from django.urls import include, path
from rest_framework.routers import DefaultRouter

from monitoring.views import HealthCheckResultViewSet, HealthView, MonitoredEndpointViewSet

router = DefaultRouter()
router.register("endpoints", MonitoredEndpointViewSet, basename="endpoint")
router.register("checks", HealthCheckResultViewSet, basename="check")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include(router.urls)),
]
