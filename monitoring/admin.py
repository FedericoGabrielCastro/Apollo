from django.contrib import admin

from monitoring.models import HealthCheckResult, MonitoredEndpoint


@admin.register(MonitoredEndpoint)
class MonitoredEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "url",
        "method",
        "expected_status",
        "is_active",
        "timeout_seconds",
        "check_interval_minutes",
    )
    list_filter = ("is_active", "method")
    search_fields = ("name", "url")


@admin.register(HealthCheckResult)
class HealthCheckResultAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "status", "status_code", "latency_ms", "checked_at")
    list_filter = ("status",)
    search_fields = ("endpoint__name", "error_message")
    readonly_fields = (
        "endpoint",
        "status",
        "status_code",
        "latency_ms",
        "error_message",
        "checked_at",
    )
