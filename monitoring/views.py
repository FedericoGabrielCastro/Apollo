from datetime import timedelta

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from monitoring.alerts import build_alert_payload, deliver_webhook
from monitoring.dashboard import build_dashboard
from monitoring.exports import csv_response
from monitoring.models import AlertEvent, HealthCheckResult, Incident, MonitoredEndpoint, StatusPageConfig, Tag
from monitoring.ownership import filter_endpoints_for_user
from monitoring.pagination_utils import paginate_queryset
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
        return Response(build_dashboard(hours=hours, user=request.user))


class MonitoredEndpointViewSet(viewsets.ModelViewSet):
    queryset = MonitoredEndpoint.objects.prefetch_related(
        "checks",
        "alerts",
        "tags",
        "incidents",
    ).select_related("owner").all()
    serializer_class = MonitoredEndpointSerializer

    def get_queryset(self):
        queryset = filter_endpoints_for_user(super().get_queryset(), self.request.user)
        tag = self.request.query_params.get("tag")
        if tag:
            queryset = queryset.filter(tags__name=tag.lower())
        return queryset.distinct()

    def perform_create(self, serializer) -> None:
        serializer.save(owner=self.request.user)

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
        page = paginate_queryset(request, endpoint.checks.all())
        return Response(
            {
                **page,
                "results": HealthCheckResultSerializer(page["results"], many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="alerts")
    def alerts(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        page = paginate_queryset(request, endpoint.alerts.all())
        return Response(
            {
                **page,
                "results": AlertEventSerializer(page["results"], many=True).data,
            }
        )

    @action(detail=True, methods=["get"], url_path="incidents")
    def incidents(self, request: Request, pk: str | None = None) -> Response:
        endpoint = self.get_object()
        page = paginate_queryset(request, endpoint.incidents.all())
        return Response(
            {
                **page,
                "results": IncidentSerializer(page["results"], many=True).data,
            }
        )

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

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = filter_endpoints_for_user(
            MonitoredEndpoint.objects.all(),
            self.request.user,
        ).values_list("id", flat=True)
        return queryset.filter(endpoint_id__in=visible)


class AlertEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AlertEvent.objects.select_related("endpoint", "check_result").all()
    serializer_class = AlertEventSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = filter_endpoints_for_user(
            MonitoredEndpoint.objects.all(),
            self.request.user,
        ).values_list("id", flat=True)
        return queryset.filter(endpoint_id__in=visible)


class IncidentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Incident.objects.select_related("endpoint", "acknowledged_by").all()
    serializer_class = IncidentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        visible = filter_endpoints_for_user(
            MonitoredEndpoint.objects.all(),
            self.request.user,
        ).values_list("id", flat=True)
        queryset = queryset.filter(endpoint_id__in=visible)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    @action(detail=True, methods=["post"])
    def acknowledge(self, request: Request, pk: str | None = None) -> Response:
        incident = self.get_object()
        if incident.status != Incident.Status.OPEN:
            return Response(
                {"detail": "Only open incidents can be acknowledged."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if incident.acknowledged_at is None:
            incident.acknowledged_at = timezone.now()
            incident.acknowledged_by = request.user
            incident.save(update_fields=["acknowledged_at", "acknowledged_by"])
        return Response(IncidentSerializer(incident).data)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "delete", "head", "options"]


class ExportView(APIView):
    """CSV downloads for checks, alerts, and incidents."""

    def get(self, request: Request, resource: str) -> Response:
        try:
            hours = int(request.query_params.get("hours", 24 * 7))
        except (TypeError, ValueError):
            hours = 24 * 7
        hours = max(1, min(hours, 24 * 90))
        since = timezone.now() - timedelta(hours=hours)
        endpoint_id = request.query_params.get("endpoint_id")
        visible_ids = list(
            filter_endpoints_for_user(
                MonitoredEndpoint.objects.all(),
                request.user,
            ).values_list("id", flat=True)
        )

        if resource == "checks":
            queryset = HealthCheckResult.objects.select_related("endpoint").filter(
                checked_at__gte=since,
                endpoint_id__in=visible_ids,
            )
            if endpoint_id:
                queryset = queryset.filter(endpoint_id=endpoint_id)
            rows = (
                (
                    item.id,
                    item.endpoint_id,
                    item.endpoint.name,
                    item.status,
                    item.status_code if item.status_code is not None else "",
                    item.latency_ms if item.latency_ms is not None else "",
                    item.error_message,
                    item.checked_at.isoformat(),
                )
                for item in queryset.order_by("-checked_at")[:5000]
            )
            return csv_response(
                "apollo-checks.csv",
                [
                    "id",
                    "endpoint_id",
                    "endpoint_name",
                    "status",
                    "status_code",
                    "latency_ms",
                    "error_message",
                    "checked_at",
                ],
                rows,
            )

        if resource == "alerts":
            queryset = AlertEvent.objects.select_related("endpoint").filter(
                created_at__gte=since,
                endpoint_id__in=visible_ids,
            )
            if endpoint_id:
                queryset = queryset.filter(endpoint_id=endpoint_id)
            rows = (
                (
                    item.id,
                    item.endpoint_id,
                    item.endpoint.name,
                    item.event_type,
                    item.channel,
                    item.target,
                    item.success,
                    item.response_status if item.response_status is not None else "",
                    item.error_message,
                    item.created_at.isoformat(),
                )
                for item in queryset.order_by("-created_at")[:5000]
            )
            return csv_response(
                "apollo-alerts.csv",
                [
                    "id",
                    "endpoint_id",
                    "endpoint_name",
                    "event_type",
                    "channel",
                    "target",
                    "success",
                    "response_status",
                    "error_message",
                    "created_at",
                ],
                rows,
            )

        if resource == "incidents":
            queryset = Incident.objects.select_related("endpoint").filter(
                endpoint_id__in=visible_ids,
            )
            if endpoint_id:
                queryset = queryset.filter(endpoint_id=endpoint_id)
            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            rows = (
                (
                    item.id,
                    item.endpoint_id,
                    item.endpoint.name,
                    item.status,
                    item.summary,
                    item.opened_at.isoformat(),
                    item.resolved_at.isoformat() if item.resolved_at else "",
                    item.acknowledged_at.isoformat() if item.acknowledged_at else "",
                )
                for item in queryset.order_by("-opened_at")[:5000]
            )
            return csv_response(
                "apollo-incidents.csv",
                [
                    "id",
                    "endpoint_id",
                    "endpoint_name",
                    "status",
                    "summary",
                    "opened_at",
                    "resolved_at",
                    "acknowledged_at",
                ],
                rows,
            )

        return Response({"detail": "Unknown export resource."}, status=status.HTTP_404_NOT_FOUND)
