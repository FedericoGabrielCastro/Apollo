from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, Q
from django.utils import timezone

from monitoring.models import HealthCheckResult


def build_check_series(
    *,
    hours: int = 24,
    endpoint_id: int | None = None,
    endpoint_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    """
    Build hourly uptime/latency buckets for charts.

    Buckets cover [now - hours, now), one entry per hour (oldest first).
    """
    hours = max(1, min(hours, 24 * 30))
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(hours=hours - 1)

    queryset = HealthCheckResult.objects.filter(checked_at__gte=start)
    if endpoint_id is not None:
        queryset = queryset.filter(endpoint_id=endpoint_id)
    elif endpoint_ids is not None:
        queryset = queryset.filter(endpoint_id__in=endpoint_ids)

    # Prefetch into memory for sqlite-friendly bucketing.
    rows = list(queryset.values("checked_at", "status", "latency_ms"))
    buckets: dict[Any, dict[str, Any]] = {}
    cursor = start
    while cursor <= now:
        buckets[cursor] = {
            "bucket_start": cursor.isoformat(),
            "checks_total": 0,
            "checks_up": 0,
            "avg_latency_ms": None,
            "uptime_percent": None,
            "_latency_sum": 0.0,
            "_latency_count": 0,
        }
        cursor += timedelta(hours=1)

    for row in rows:
        checked_at = row["checked_at"].replace(minute=0, second=0, microsecond=0)
        bucket = buckets.get(checked_at)
        if bucket is None:
            continue
        bucket["checks_total"] += 1
        if row["status"] == HealthCheckResult.Status.UP:
            bucket["checks_up"] += 1
        if row["latency_ms"] is not None:
            bucket["_latency_sum"] += float(row["latency_ms"])
            bucket["_latency_count"] += 1

    series: list[dict[str, Any]] = []
    for key in sorted(buckets.keys()):
        bucket = buckets[key]
        total = bucket["checks_total"]
        up = bucket["checks_up"]
        latency_count = bucket.pop("_latency_count")
        latency_sum = bucket.pop("_latency_sum")
        bucket["uptime_percent"] = round((up / total) * 100, 2) if total else None
        bucket["avg_latency_ms"] = (
            round(latency_sum / latency_count, 2) if latency_count else None
        )
        series.append(bucket)
    return series


def build_endpoint_uptime_summary(*, hours: int = 24) -> dict[str, Any]:
    """Compact aggregate used by export/tests."""
    hours = max(1, min(hours, 24 * 30))
    since = timezone.now() - timedelta(hours=hours)
    stats = HealthCheckResult.objects.filter(checked_at__gte=since).aggregate(
        total=Count("id"),
        up=Count("id", filter=Q(status=HealthCheckResult.Status.UP)),
        avg_latency=Avg("latency_ms"),
    )
    total = stats["total"] or 0
    up = stats["up"] or 0
    return {
        "hours": hours,
        "checks_total": total,
        "uptime_percent": round((up / total) * 100, 2) if total else None,
        "avg_latency_ms": (
            round(stats["avg_latency"], 2) if stats["avg_latency"] is not None else None
        ),
    }
