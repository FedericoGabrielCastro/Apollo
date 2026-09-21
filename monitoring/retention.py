from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from monitoring.models import HealthCheckResult


def prune_old_checks(*, days: int | None = None) -> int:
    """
    Delete HealthCheckResult rows older than `days`.

    Returns the number of deleted rows. Uses CHECK_RETENTION_DAYS when days is None.
    A value <= 0 disables pruning.
    """
    if days is None:
        days = int(getattr(settings, "CHECK_RETENTION_DAYS", 30) or 0)
    if days <= 0:
        return 0

    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = HealthCheckResult.objects.filter(checked_at__lt=cutoff).delete()
    return int(deleted)
