from __future__ import annotations

from typing import Any

from django.utils import timezone

from monitoring.models import HealthCheckResult, Incident, MonitoredEndpoint


def build_public_status() -> dict[str, Any]:
    """Public status payload for unauthenticated status page consumers."""
    endpoints = list(
        MonitoredEndpoint.objects.filter(is_public=True, is_active=True)
        .prefetch_related("tags")
        .order_by("name")
    )
    rows: list[dict[str, Any]] = []
    failing = 0

    for endpoint in endpoints:
        last = endpoint.checks.order_by("-checked_at").first()
        status = last.status if last else "unknown"
        if status in {
            HealthCheckResult.Status.DOWN,
            HealthCheckResult.Status.ERROR,
        }:
            failing += 1
        rows.append(
            {
                "name": endpoint.name,
                "status": status,
                "latency_ms": last.latency_ms if last else None,
                "last_checked_at": last.checked_at.isoformat() if last else None,
                "tags": list(endpoint.tags.values_list("name", flat=True)),
            }
        )

    if not endpoints:
        overall = "unknown"
    elif failing == 0:
        overall = "operational"
    elif failing == len(endpoints):
        overall = "major_outage"
    else:
        overall = "degraded"

    open_incidents = (
        Incident.objects.filter(
            status=Incident.Status.OPEN,
            endpoint__is_public=True,
        )
        .select_related("endpoint")
        .order_by("-opened_at")[:20]
    )

    return {
        "service": "apollo",
        "overall": overall,
        "generated_at": timezone.now().isoformat(),
        "endpoints": rows,
        "active_incidents": [
            {
                "endpoint_name": incident.endpoint.name,
                "summary": incident.summary,
                "opened_at": incident.opened_at.isoformat(),
            }
            for incident in open_incidents
        ],
    }
