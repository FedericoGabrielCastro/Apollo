from __future__ import annotations

from typing import Any

import httpx
from django.utils import timezone

from monitoring.models import AlertEvent, HealthCheckResult, MonitoredEndpoint

FAILURE_STATUSES = {
    HealthCheckResult.Status.DOWN,
    HealthCheckResult.Status.ERROR,
}


def previous_check_status(
    endpoint: MonitoredEndpoint,
    current: HealthCheckResult,
) -> str | None:
    """Return the status of the check immediately before `current`, if any."""
    previous = (
        endpoint.checks.exclude(pk=current.pk)
        .order_by("-checked_at")
        .values_list("status", flat=True)
        .first()
    )
    return previous


def resolve_alert_event_type(
    previous_status: str | None,
    current_status: str,
) -> str | None:
    """
    Alert only on transitions:
    - healthy/unknown -> failure
    - failure -> healthy (recovery)
    Consecutive failures do not re-alert.
    """
    current_is_failure = current_status in FAILURE_STATUSES
    previous_is_failure = previous_status in FAILURE_STATUSES if previous_status else False

    if current_is_failure and not previous_is_failure:
        return AlertEvent.EventType.FAILURE
    if not current_is_failure and previous_is_failure:
        return AlertEvent.EventType.RECOVERY
    return None


def build_alert_payload(
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
    event_type: str,
) -> dict[str, Any]:
    return {
        "event": f"endpoint.{event_type}",
        "service": "apollo",
        "timestamp": timezone.now().isoformat(),
        "endpoint": {
            "id": endpoint.id,
            "name": endpoint.name,
            "url": endpoint.url,
            "method": endpoint.method,
        },
        "check": {
            "id": result.id,
            "status": result.status,
            "status_code": result.status_code,
            "latency_ms": result.latency_ms,
            "error_message": result.error_message,
            "checked_at": result.checked_at.isoformat(),
        },
    }


def deliver_webhook(url: str, payload: dict[str, Any]) -> tuple[bool, int | None, str]:
    """POST JSON payload to the webhook URL."""
    try:
        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            response = client.post(url, json=payload)
        if 200 <= response.status_code < 300:
            return True, response.status_code, ""
        return False, response.status_code, f"Webhook returned HTTP {response.status_code}"
    except httpx.HTTPError as exc:
        return False, None, str(exc)


def dispatch_alerts_for_result(
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
) -> list[AlertEvent]:
    """Evaluate status transition and dispatch configured alert channels."""
    if not endpoint.alert_on_failure:
        return []

    previous_status = previous_check_status(endpoint, result)
    event_type = resolve_alert_event_type(previous_status, result.status)
    if event_type is None:
        return []

    alerts: list[AlertEvent] = []
    payload = build_alert_payload(endpoint, result, event_type)

    if endpoint.webhook_url:
        success, response_status, error_message = deliver_webhook(
            endpoint.webhook_url,
            payload,
        )
        alerts.append(
            AlertEvent.objects.create(
                endpoint=endpoint,
                check_result=result,
                event_type=event_type,
                channel=AlertEvent.Channel.WEBHOOK,
                target=endpoint.webhook_url,
                payload=payload,
                success=success,
                response_status=response_status,
                error_message=error_message,
            )
        )

    return alerts
