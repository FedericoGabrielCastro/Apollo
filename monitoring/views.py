from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.models import HealthCheckResult, MonitoredEndpoint
from monitoring.serializers import HealthCheckResultSerializer, MonitoredEndpointSerializer
from monitoring.services import run_due_checks, run_health_check


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

    @action(detail=False, methods=["post"], url_path="check-due")
    def check_due(self, request: Request) -> Response:
        results = run_due_checks()
        return Response(
            {
                "checked": len(results),
                "results": HealthCheckResultSerializer(results, many=True).data,
            },
            status=status.HTTP_200_OK if results else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"], url_path="checks")
    def checks(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        results = endpoint.checks.all()[:50]
        return Response(HealthCheckResultSerializer(results, many=True).data)


class HealthCheckResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthCheckResult.objects.select_related("endpoint").all()
    serializer_class = HealthCheckResultSerializer
