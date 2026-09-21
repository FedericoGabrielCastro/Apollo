from __future__ import annotations

import socket
import ssl
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone as dt_timezone
from urllib.parse import urlparse

import httpx
from django.db.models import Max, QuerySet
from django.utils import timezone

from monitoring.alerts import dispatch_alerts_for_result
from monitoring.models import HealthCheckResult, MonitoredEndpoint


@dataclass(frozen=True)
class CheckOutcome:
    status: str
    status_code: int | None
    latency_ms: float | None
    error_message: str


def _ssl_expiry_days_remaining(hostname: str, port: int = 443) -> int | None:
    """Return days until TLS cert expiry for hostname, or None on failure."""
    context = ssl.create_default_context()
    with socket.create_connection((hostname, port), timeout=10) as sock:
        with context.wrap_socket(sock, server_hostname=hostname) as ssock:
            cert = ssock.getpeercert()
    if not cert:
        return None
    not_after = cert.get("notAfter")
    if not not_after:
        return None
    expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(
        tzinfo=dt_timezone.utc
    )
    remaining = expires - datetime.now(dt_timezone.utc)
    return max(0, remaining.days)


def check_ssl_certificate(endpoint: MonitoredEndpoint) -> str | None:
    """
    If SSL checking is enabled for an HTTPS URL, return an error message when
    the certificate is missing, unreadable, or within the warn window.
    """
    if not endpoint.check_ssl_expiry:
        return None

    parsed = urlparse(endpoint.url)
    if parsed.scheme.lower() != "https":
        return None

    hostname = parsed.hostname
    if not hostname:
        return "SSL check enabled but URL has no hostname"

    port = parsed.port or 443
    try:
        days_left = _ssl_expiry_days_remaining(hostname, port)
    except OSError as exc:
        return f"SSL check failed: {exc}"
    except ssl.SSLError as exc:
        return f"SSL check failed: {exc}"

    if days_left is None:
        return "SSL check failed: could not read certificate expiry"

    if days_left <= endpoint.ssl_warn_days:
        return (
            f"TLS certificate expires in {days_left} day(s) "
            f"(warn threshold {endpoint.ssl_warn_days})"
        )
    return None


def evaluate_response_assertions(
    endpoint: MonitoredEndpoint,
    *,
    status_code: int,
    latency_ms: float,
    body: str,
) -> str | None:
    """Return the first failing assertion message, or None when all pass."""
    if status_code != endpoint.expected_status:
        return (
            f"Expected status {endpoint.expected_status}, got {status_code}"
        )

    needle = (endpoint.expect_body_contains or "").strip()
    if needle and needle not in body:
        return f"Response body missing expected text: {needle!r}"

    if endpoint.max_latency_ms is not None and latency_ms > endpoint.max_latency_ms:
        return (
            f"Latency {latency_ms:.2f}ms exceeds max "
            f"{endpoint.max_latency_ms}ms"
        )

    return None


def probe_endpoint(endpoint: MonitoredEndpoint) -> CheckOutcome:
    """Perform an HTTP request (plus optional SSL check) and classify the result."""
    ssl_error = check_ssl_certificate(endpoint)
    if ssl_error:
        return CheckOutcome(
            status=HealthCheckResult.Status.DOWN,
            status_code=None,
            latency_ms=None,
            error_message=ssl_error,
        )

    started = time.perf_counter()

    try:
        with httpx.Client(timeout=endpoint.timeout_seconds, follow_redirects=True) as client:
            response = client.request(endpoint.method.upper(), endpoint.url)
        latency_ms = (time.perf_counter() - started) * 1000
        assertion_error = evaluate_response_assertions(
            endpoint,
            status_code=response.status_code,
            latency_ms=latency_ms,
            body=response.text,
        )
        if assertion_error:
            return CheckOutcome(
                status=HealthCheckResult.Status.DOWN,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                error_message=assertion_error,
            )

        return CheckOutcome(
            status=HealthCheckResult.Status.UP,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            error_message="",
        )
    except httpx.HTTPError as exc:
        latency_ms = (time.perf_counter() - started) * 1000
        return CheckOutcome(
            status=HealthCheckResult.Status.ERROR,
            status_code=None,
            latency_ms=round(latency_ms, 2),
            error_message=str(exc),
        )


def run_health_check(endpoint: MonitoredEndpoint) -> HealthCheckResult:
    """Probe an endpoint, persist the result, and dispatch transition alerts."""
    outcome = probe_endpoint(endpoint)
    result = HealthCheckResult.objects.create(
        endpoint=endpoint,
        status=outcome.status,
        status_code=outcome.status_code,
        latency_ms=outcome.latency_ms,
        error_message=outcome.error_message,
    )
    dispatch_alerts_for_result(endpoint, result)
    return result


def is_endpoint_due(
    endpoint: MonitoredEndpoint,
    *,
    last_checked_at=None,
    now=None,
) -> bool:
    """Return True when the endpoint has never been checked or its interval elapsed."""
    if now is None:
        now = timezone.now()

    if last_checked_at is None:
        latest = (
            endpoint.checks.order_by("-checked_at")
            .values_list("checked_at", flat=True)
            .first()
        )
        last_checked_at = latest

    if last_checked_at is None:
        return True

    return last_checked_at + timedelta(minutes=endpoint.check_interval_minutes) <= now


def due_endpoints(*, include_inactive: bool = False) -> list[MonitoredEndpoint]:
    """Active endpoints (by default) whose check interval has elapsed."""
    now = timezone.now()
    queryset: QuerySet[MonitoredEndpoint] = MonitoredEndpoint.objects.annotate(
        last_checked_at=Max("checks__checked_at"),
    )
    if not include_inactive:
        queryset = queryset.filter(is_active=True)

    return [
        endpoint
        for endpoint in queryset
        if is_endpoint_due(
            endpoint,
            last_checked_at=endpoint.last_checked_at,
            now=now,
        )
    ]


def run_due_checks(*, include_inactive: bool = False) -> list[HealthCheckResult]:
    """Probe every due endpoint and return the created results."""
    return [
        run_health_check(endpoint)
        for endpoint in due_endpoints(include_inactive=include_inactive)
    ]
