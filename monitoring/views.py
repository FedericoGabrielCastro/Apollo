from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.alerts import build_alert_payload, deliver_webhook
from monitoring.dashboard import build_dashboard
from monitoring.models import AlertEvent, HealthCheckResult, Incident, MonitoredEndpoint, StatusPageConfig, Tag
from monitoring.serializers import (
    AlertEventSerializer,
    HealthCheckResultSerializer,
    IncidentSerializer,
    MonitoredEndpointSerializer,
    StatusPageConfigSerializer,
    TagSerializer,
)
from monitoring.services import run_due_checks, run_health_check
from monitoring.statuspage import build_public_status


class HealthView(APIView):
    """Liveness endpoint for Apollo itself."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(
            {
                "status": "ok",
                "service": "apollo",
                "timestamp": timezone.now().isoformat(),
            }
        )


class PublicStatusView(APIView):
    """Unauthenticated public status page payload."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        return Response(build_public_status())


class StatusPageConfigView(APIView):
    """Read/update branding for the public status page."""

    def get(self, request: Request) -> Response:
        config = StatusPageConfig.get_solo()
        return Response(StatusPageConfigSerializer(config).data)

    def patch(self, request: Request) -> Response:
        config = StatusPageConfig.get_solo()
        serializer = StatusPageConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def put(self, request: Request) -> Response:
        return self.patch(request)


class DashboardView(APIView):
    """Aggregated uptime and operational metrics."""

    def get(self, request: Request) -> Response:
        try:
            hours = int(request.query_params.get("hours", 24))
        except (TypeError, ValueError):
            hours = 24
        return Response(build_dashboard(hours=hours))


class MonitoredEndpointViewSet(viewsets.ModelViewSet):
    queryset = MonitoredEndpoint.objects.prefetch_related(
        "checks",
        "alerts",
        "tags",
        "incidents",
    ).all()
    serializer_class = MonitoredEndpointSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__name=tag.lower())
        return queryset.distinct()

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
            }
        )

    @action(detail=True, methods=["get"], url_path="checks")
    def checks(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        results = endpoint.checks.all()[:50]
        return Response(HealthCheckResultSerializer(results, many=True).data)

    @action(detail=True, methods=["get"], url_path="alerts")
    def alerts(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        results = endpoint.alerts.all()[:50]
        return Response(AlertEventSerializer(results, many=True).data)

    @action(detail=True, methods=["get"], url_path="incidents")
    def incidents(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        results = endpoint.incidents.all()[:50]
        return Response(IncidentSerializer(results, many=True).data)

    @action(detail=True, methods=["post"], url_path="test-webhook")
    def test_webhook(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        if not endpoint.webhook_url:
            return Response(
                {"detail": "Endpoint has no webhook_url configured."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest = endpoint.checks.order_by("-checked_at").first()
        if latest is None:
            payload = {
                "event": "endpoint.test",
                "service": "apollo",
                "timestamp": timezone.now().isoformat(),
                "endpoint": {
                    "id": endpoint.id,
                    "name": endpoint.name,
                    "url": endpoint.url,
                    "method": endpoint.method,
                },
                "check": None,
            }
        else:
            payload = build_alert_payload(
                endpoint,
                latest,
                AlertEvent.EventType.FAILURE,
            )
            payload["event"] = "endpoint.test"

        success, response_status, error_message = deliver_webhook(
            endpoint.webhook_url,
            payload,
        )

        alert = None
        if latest is not None:
            alert = AlertEvent.objects.create(
                endpoint=endpoint,
                check_result=latest,
                event_type=AlertEvent.EventType.FAILURE,
                channel=AlertEvent.Channel.WEBHOOK,
                target=endpoint.webhook_url,
                payload=payload,
                success=success,
                response_status=response_status,
                error_message=error_message,
            )

        body = {
            "success": success,
            "response_status": response_status,
            "error_message": error_message,
            "payload": payload,
        }
        if alert is not None:
            body["alert"] = AlertEventSerializer(alert).data

        return Response(
            body,
            status=status.HTTP_200_OK if success else status.HTTP_502_BAD_GATEWAY,
        )


class HealthCheckResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HealthCheckResult.objects.select_related("endpoint").all()
    serializer_class = HealthCheckResultSerializer


class AlertEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertEvent.objects.select_related("endpoint", "check_result").all()
    serializer_class = AlertEventSerializer


class IncidentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Incident.objects.select_related("endpoint").all()
    serializer_class = IncidentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]
