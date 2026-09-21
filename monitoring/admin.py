from django.contrib import admin

from monitoring.models import AlertEvent, HealthCheckResult, MonitoredEndpoint


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
        "alert_on_failure",
        "webhook_url",
    )
    list_filter = ("is_active", "method", "alert_on_failure")
    search_fields = ("name", "url", "webhook_url")


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


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = (
        "endpoint",
        "event_type",
        "channel",
        "success",
        "response_status",
        "created_at",
    )
    list_filter = ("event_type", "channel", "success")
    search_fields = ("endpoint__name", "target", "error_message")
    readonly_fields = (
        "endpoint",
        "check_result",
        "event_type",
        "channel",
        "target",
        "payload",
        "success",
        "response_status",
        "error_message",
        "created_at",
    )
