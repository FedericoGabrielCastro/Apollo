from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.models import HealthCheckResult, MonitoredEndpoint
from monitoring.serializers import HealthCheckResultSerializer, MonitoredEndpointSerializer
from monitoring.services import run_health_check


class HealthView(APIView):
    """Liveness endpoint for Apollo itself."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "apollo",
                "timestamp": timezone.now().isoformat(),
            }
        )


class MonitoredEndpointViewSet(viewsets.ModelViewSet):
    queryset = MonitoredEndpoint.objects.prefetch_related("checks").all()
    serializer_class = MonitoredEndpointSerializer

    @action(detail=True, methods=["post"])
    def check(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        result = run_health_check(endpoint)
        return Response(
            HealthCheckResultSerializer(result).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="checks")
    def checks(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        results = endpoint.checks.all()[:50]
        return Response(HealthCheckResultSerializer(results, many=True).data)


class HealthCheckResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthCheckResult.objects.select_related("endpoint").all()
    serializer_class = HealthCheckResultSerializer
