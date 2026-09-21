from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

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
