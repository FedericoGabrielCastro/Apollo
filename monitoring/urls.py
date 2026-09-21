from django.urls import include, path
from rest_framework.routers import DefaultRouter

from monitoring.views import HealthView, MonitoredEndpointViewSet

router = DefaultRouter()
router.register("endpoints", MonitoredEndpointViewSet, basename="endpoint")

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("", include(router.urls)),
]
