from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, Q
from django.utils import timezone

from monitoring.models import AlertEvent, HealthCheckResult, MonitoredEndpoint
from monitoring.services import due_endpoints


def build_dashboard(*, hours: int = 24) -> dict[str, Any]:
    """Aggregate uptime and operational metrics for the dashboard."""
    hours = max(1, min(hours, 24 * 30))
    since = timezone.now() - timedelta(hours=hours)

    endpoints = list(MonitoredEndpoint.objects.all())
    active_endpoints = [endpoint for endpoint in endpoints if endpoint.is_active]
    due = due_endpoints()
    alerting = [
        endpoint
        for endpoint in endpoints
        if endpoint.alert_on_failure and endpoint.webhook_url
    ]

    checks = HealthCheckResult.objects.filter(checked_at__gte=since)
    check_stats = checks.aggregate(
        total=Count("id"),
        up=Count("id", filter=Q(status=HealthCheckResult.Status.UP)),
        down=Count("id", filter=Q(status=HealthCheckResult.Status.DOWN)),
        error=Count("id", filter=Q(status=HealthCheckResult.Status.ERROR)),
        avg_latency=Avg("latency_ms"),
    )
    total_checks = check_stats["total"] or 0
    up_checks = check_stats["up"] or 0
    uptime_percent = round((up_checks / total_checks) * 100, 2) if total_checks else None

    alerts = AlertEvent.objects.filter(created_at__gte=since)
    alert_stats = alerts.aggregate(
        total=Count("id"),
        failed=Count("id", filter=Q(success=False)),
        failures=Count("id", filter=Q(event_type=AlertEvent.EventType.FAILURE)),
        recoveries=Count("id", filter=Q(event_type=AlertEvent.EventType.RECOVERY)),
    )

    endpoint_rows: list[dict[str, Any]] = []
    due_ids = {endpoint.id for endpoint in due}

    for endpoint in endpoints:
        endpoint_checks = checks.filter(endpoint=endpoint)
        endpoint_totals = endpoint_checks.aggregate(
            total=Count("id"),
            up=Count("id", filter=Q(status=HealthCheckResult.Status.UP)),
            avg_latency=Avg("latency_ms"),
        )
        endpoint_total = endpoint_totals["total"] or 0
        endpoint_up = endpoint_totals["up"] or 0
        last_check = endpoint.checks.order_by("-checked_at").first()

        endpoint_rows.append(
            {
                "id": endpoint.id,
                "name": endpoint.name,
                "url": endpoint.url,
                "is_active": endpoint.is_active,
                "is_due": endpoint.id in due_ids,
                "checks_total": endpoint_total,
                "uptime_percent": (
                    round((endpoint_up / endpoint_total) * 100, 2)
                    if endpoint_total
                    else None
                ),
                "avg_latency_ms": (
                    round(endpoint_totals["avg_latency"], 2)
                    if endpoint_totals["avg_latency"] is not None
                    else None
                ),
                "last_status": last_check.status if last_check else None,
                "last_checked_at": (
                    last_check.checked_at.isoformat() if last_check else None
                ),
            }
        )

    endpoint_rows.sort(key=lambda row: row["name"].lower())

    recent_failures = list(
        checks.exclude(status=HealthCheckResult.Status.UP)
        .select_related("endpoint")
        .order_by("-checked_at")[:10]
    )
    recent_alerts = list(
        alerts.select_related("endpoint").order_by("-created_at")[:10]
    )

    return {
        "window_hours": hours,
        "generated_at": timezone.now().isoformat(),
        "summary": {
            "endpoints_total": len(endpoints),
            "endpoints_active": len(active_endpoints),
            "endpoints_due": len(due),
            "endpoints_with_webhook": len(alerting),
            "checks_total": total_checks,
            "checks_up": up_checks,
            "checks_down": check_stats["down"] or 0,
            "checks_error": check_stats["error"] or 0,
            "uptime_percent": uptime_percent,
            "avg_latency_ms": (
                round(check_stats["avg_latency"], 2)
                if check_stats["avg_latency"] is not None
                else None
            ),
            "alerts_total": alert_stats["total"] or 0,
            "alerts_failed_delivery": alert_stats["failed"] or 0,
            "alerts_failure_events": alert_stats["failures"] or 0,
            "alerts_recovery_events": alert_stats["recoveries"] or 0,
        },
        "endpoints": endpoint_rows,
        "recent_failures": [
            {
                "id": item.id,
                "endpoint_id": item.endpoint_id,
                "endpoint_name": item.endpoint.name,
                "status": item.status,
                "status_code": item.status_code,
                "latency_ms": item.latency_ms,
                "error_message": item.error_message,
                "checked_at": item.checked_at.isoformat(),
            }
            for item in recent_failures
        ],
        "recent_alerts": [
            {
                "id": item.id,
                "endpoint_id": item.endpoint_id,
                "endpoint_name": item.endpoint.name,
                "event_type": item.event_type,
                "success": item.success,
                "created_at": item.created_at.isoformat(),
            }
            for item in recent_alerts
        ],
    }
