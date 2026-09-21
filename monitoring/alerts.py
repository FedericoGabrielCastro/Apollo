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


def trailing_failure_streak(
    endpoint: MonitoredEndpoint,
    current: HealthCheckResult,
) -> int:
    """Count consecutive failure statuses ending at `current` (inclusive)."""
    statuses = list(
        endpoint.checks.order_by("-checked_at").values_list("status", flat=True)[:50]
    )
    # Ensure current is first (just created).
    if not statuses or statuses[0] != current.status:
        statuses = [current.status, *statuses]

    streak = 0
    for status_value in statuses:
        if status_value in FAILURE_STATUSES:
            streak += 1
        else:
            break
    return streak


def resolve_alert_event_type(
    endpoint: MonitoredEndpoint,
    current: HealthCheckResult,
    previous_status: str | None,
) -> str | None:
    """
    Alert when consecutive failures reach failure_threshold, and on recovery
    after a threshold-crossing outage (or an already-open incident).
    """
    threshold = max(1, endpoint.failure_threshold or 1)
    current_is_failure = current.status in FAILURE_STATUSES
    previous_is_failure = previous_status in FAILURE_STATUSES if previous_status else False

    if current_is_failure:
        streak = trailing_failure_streak(endpoint, current)
        if streak == threshold:
            return AlertEvent.EventType.FAILURE
        return None

    if previous_is_failure:
        open_incident = endpoint.incidents.filter(status=Incident.Status.OPEN).exists()
        prior_statuses = list(
            endpoint.checks.exclude(pk=current.pk)
            .order_by("-checked_at")
            .values_list("status", flat=True)[:50]
        )
        prior_streak = 0
        for status_value in prior_statuses:
            if status_value in FAILURE_STATUSES:
                prior_streak += 1
            else:
                break
        if open_incident or prior_streak >= threshold:
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


def _alert_text(event_type: str, payload: dict[str, Any]) -> str:
    endpoint = payload.get("endpoint", {})
    check = payload.get("check", {})
    return (
        f"[Apollo] {endpoint.get('name', 'endpoint')} {event_type}\n"
        f"Status: {check.get('status')} · HTTP {check.get('status_code')}\n"
        f"Error: {check.get('error_message') or '-'}"
    )


def deliver_discord(url: str, event_type: str, payload: dict[str, Any]) -> tuple[bool, int | None, str]:
    """POST a Discord-compatible webhook body."""
    body = {"content": _alert_text(event_type, payload)[:1900]}
    return deliver_webhook(url, body)


def deliver_slack(url: str, event_type: str, payload: dict[str, Any]) -> tuple[bool, int | None, str]:
    """POST a Slack incoming-webhook body."""
    body = {"text": _alert_text(event_type, payload)}
    return deliver_webhook(url, body)


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


def alerts_are_muted(endpoint: MonitoredEndpoint, *, now=None) -> bool:
    """True when mute_alerts_until is set and still in the future."""
    if endpoint.mute_alerts_until is None:
        return False
    if now is None:
        now = timezone.now()
    return endpoint.mute_alerts_until > now


def _record_channel(
    *,
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
    event_type: str,
    channel: str,
    target: str,
    payload: dict[str, Any],
    success: bool,
    response_status: int | None,
    error_message: str,
) -> AlertEvent:
    return AlertEvent.objects.create(
        endpoint=endpoint,
        check_result=result,
        event_type=event_type,
        channel=channel,
        target=target,
        payload=payload,
        success=success,
        response_status=response_status,
        error_message=error_message,
    )


def dispatch_alerts_for_result(
    endpoint: MonitoredEndpoint,
    result: HealthCheckResult,
) -> list[AlertEvent]:
    """Evaluate status transition, sync incidents, and dispatch alert channels."""
    previous_status = previous_check_status(endpoint, result)
    event_type = resolve_alert_event_type(endpoint, result, previous_status)

    if event_type:
        sync_incident_for_transition(endpoint, result, event_type)

    if event_type is None:
        return []

    if not endpoint.alert_on_failure or alerts_are_muted(endpoint):
        return []

    alerts: list[AlertEvent] = []
    payload = build_alert_payload(endpoint, result, event_type)

    if endpoint.webhook_url:
        success, response_status, error_message = deliver_webhook(
            endpoint.webhook_url,
            payload,
        )
        alerts.append(
            _record_channel(
                endpoint=endpoint,
                result=result,
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
            _record_channel(
                endpoint=endpoint,
                result=result,
                event_type=event_type,
                channel=AlertEvent.Channel.EMAIL,
                target=endpoint.alert_email,
                payload=payload,
                success=success,
                response_status=None,
                error_message=error_message,
            )
        )

    if endpoint.discord_webhook_url:
        success, response_status, error_message = deliver_discord(
            endpoint.discord_webhook_url,
            event_type,
            payload,
        )
        alerts.append(
            _record_channel(
                endpoint=endpoint,
                result=result,
                event_type=event_type,
                channel=AlertEvent.Channel.DISCORD,
                target=endpoint.discord_webhook_url,
                payload=payload,
                success=success,
                response_status=response_status,
                error_message=error_message,
            )
        )

    if endpoint.slack_webhook_url:
        success, response_status, error_message = deliver_slack(
            endpoint.slack_webhook_url,
            event_type,
            payload,
        )
        alerts.append(
            _record_channel(
                endpoint=endpoint,
                result=result,
                event_type=event_type,
                channel=AlertEvent.Channel.SLACK,
                target=endpoint.slack_webhook_url,
                payload=payload,
                success=success,
                response_status=response_status,
                error_message=error_message,
            )
        )

    return alerts
