from django.contrib import admin

from monitoring.models import AlertEvent, HealthCheckResult, Incident, MonitoredEndpoint, StatusPageConfig, Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)


@admin.register(StatusPageConfig)
class StatusPageConfigAdmin(admin.ModelAdmin):
    list_display = ("title", "support_url", "updated_at")


@admin.register(MonitoredEndpoint)
class MonitoredEndpointAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "url",
        "method",
        "expected_status",
        "is_active",
        "is_public",
        "failure_threshold",
        "auth_type",
        "alert_on_failure",
        "check_ssl_expiry",
        "mute_alerts_until",
        "webhook_url",
        "alert_email",
    )
    list_filter = (
        "is_active",
        "is_public",
        "method",
        "auth_type",
        "alert_on_failure",
        "check_ssl_expiry",
        "tags",
    )
    search_fields = ("name", "url", "webhook_url", "alert_email", "discord_webhook_url", "slack_webhook_url")
    filter_horizontal = ("tags",)


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


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("endpoint", "status", "summary", "opened_at", "resolved_at")
    list_filter = ("status",)
    search_fields = ("endpoint__name", "summary")
    readonly_fields = (
        "endpoint",
        "status",
        "summary",
        "opened_by_check",
        "resolved_by_check",
        "opened_at",
        "resolved_at",
    )
