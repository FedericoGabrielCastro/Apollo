from __future__ import annotations

from typing import Any

import httpx
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from monitoring.models import AlertEvent, HealthCheckResult, Incident, MonitoredEndpoint

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


def deliver_email(to_email: str, event_type: str, payload: dict[str, Any]) -> tuple[bool, str]:
    """Send a plain-text alert email."""
    endpoint = payload.get("endpoint", {})
    check = payload.get("check", {})
    subject = f"[Apollo] {endpoint.get('name', 'endpoint')} {event_type}"
    body = (
        f"Event: {payload.get('event')}\n"
        f"Endpoint: {endpoint.get('name')} ({endpoint.get('url')})\n"
        f"Status: {check.get('status')}\n"
        f"HTTP: {check.get('status_code')}\n"
        f"Latency: {check.get('latency_ms')}ms\n"
        f"Error: {check.get('error_message') or '-'}\n"
        f"Checked at: {check.get('checked_at')}\n"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "apollo@localhost"),
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True, ""
    except Exception as exc:  # noqa: BLE001 - record delivery failure
        return False, str(exc)


def sync_incident_for_transition(
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
    event_type: str,
) -> Incident | None:
    """Open or resolve an incident based on the alert transition."""
    if event_type == AlertEvent.EventType.FAILURE:
        open_incident = endpoint.incidents.filter(status=Incident.Status.OPEN).first()
        if open_incident:
            return open_incident
        summary = result.error_message or f"Endpoint became {result.status}"
        return Incident.objects.create(
            endpoint=endpoint,
            status=Incident.Status.OPEN,
            summary=summary[:255],
            opened_by_check=result,
        )

    if event_type == AlertEvent.EventType.RECOVERY:
        open_incident = endpoint.incidents.filter(status=Incident.Status.OPEN).first()
        if not open_incident:
            return None
        open_incident.status = Incident.Status.RESOLVED
        open_incident.resolved_by_check = result
        open_incident.resolved_at = timezone.now()
        open_incident.save(
            update_fields=["status", "resolved_by_check", "resolved_at"]
        )
        return open_incident

    return None


def dispatch_alerts_for_result(
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
) -> list[AlertEvent]:
    """Evaluate status transition, sync incidents, and dispatch alert channels."""
    if not endpoint.alert_on_failure:
        # Still track incidents even if alerting is disabled? Product choice:
        # track incidents whenever status transitions, regardless of alert_on_failure.
        previous_status = previous_check_status(endpoint, result)
        event_type = resolve_alert_event_type(previous_status, result.status)
        if event_type:
            sync_incident_for_transition(endpoint, result, event_type)
        return []

    previous_status = previous_check_status(endpoint, result)
    event_type = resolve_alert_event_type(previous_status, result.status)
    if event_type is None:
        return []

    sync_incident_for_transition(endpoint, result, event_type)

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

    if endpoint.alert_email:
        success, error_message = deliver_email(
            endpoint.alert_email,
            event_type,
            payload,
        )
        alerts.append(
            AlertEvent.objects.create(
                endpoint=endpoint,
                check_result=result,
                event_type=event_type,
                channel=AlertEvent.Channel.EMAIL,
                target=endpoint.alert_email,
                payload=payload,
                success=success,
                response_status=None,
                error_message=error_message,
            )
        )

    return alerts
