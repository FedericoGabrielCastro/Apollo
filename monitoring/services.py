from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import timedelta

import httpx
from django.db.models import Max, QuerySet
from django.utils import timezone

from monitoring.models import HealthCheckResult, MonitoredEndpoint


@dataclass(frozen=True)
class CheckOutcome:
    status: str
    status_code: int | None
    latency_ms: float | None
    error_message: str


def probe_endpoint(endpoint: MonitoredEndpoint) -> CheckOutcome:
    """Perform an HTTP request and classify the result."""
    started = time.perf_counter()

    try:
        with httpx.Client(timeout=endpoint.timeout_seconds, follow_redirects=True) as client:
            response = client.request(endpoint.method.upper(), endpoint.url)
        latency_ms = (time.perf_counter() - started) * 1000

        if response.status_code == endpoint.expected_status:
            return CheckOutcome(
                status=HealthCheckResult.Status.UP,
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
                error_message="",
            )

        return CheckOutcome(
            status=HealthCheckResult.Status.DOWN,
            status_code=response.status_code,
            latency_ms=round(latency_ms, 2),
            error_message=(
                f"Expected status {endpoint.expected_status}, "
                f"got {response.status_code}"
            ),
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
    """Probe an endpoint and persist the result."""
    outcome = probe_endpoint(endpoint)
    return HealthCheckResult.objects.create(
        endpoint=endpoint,
        status=outcome.status,
        status_code=outcome.status_code,
        latency_ms=outcome.latency_ms,
        error_message=outcome.error_message,
    )


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
        latest = endpoint.checks.order_by("-checked_at").values_list("checked_at", flat=True).first()
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
    return [run_health_check(endpoint) for endpoint in due_endpoints(include_inactive=include_inactive)]
