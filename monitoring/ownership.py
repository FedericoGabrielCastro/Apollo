from __future__ import annotations

from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from monitoring.models import MonitoredEndpoint


def owned_endpoints_q(user: User) -> Q:
    """Filter endpoints visible to a user (staff sees all)."""
    if user.is_staff:
        return Q()
    return Q(owner=user) | Q(owner__isnull=True)


def filter_endpoints_for_user(queryset: QuerySet[MonitoredEndpoint], user: User) -> QuerySet[MonitoredEndpoint]:
    if user.is_staff:
        return queryset
    return queryset.filter(owned_endpoints_q(user))
