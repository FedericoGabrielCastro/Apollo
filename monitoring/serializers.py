from rest_framework import serializers

from monitoring.models import (
    AlertEvent,
    HealthCheckResult,
    Incident,
    MonitoredEndpoint,
    StatusPageConfig,
    Tag,
)
from monitoring.services import is_endpoint_due

HTTP_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE")
AUTH_TYPES = ("none", "bearer", "basic")


class HealthCheckResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheckResult
        fields = [
            "id",
            "endpoint",
            "status",
            "status_code",
            "latency_ms",
            "error_message",
            "checked_at",
        ]
        read_only_fields = fields


class AlertEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertEvent
        fields = [
            "id",
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
        ]
        read_only_fields = fields


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]


class IncidentSerializer(serializers.ModelSerializer):
    endpoint_name = serializers.CharField(source="endpoint.name", read_only=True)
    acknowledged_by_username = serializers.CharField(
        source="acknowledged_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Incident
        fields = [
            "id",
            "endpoint",
            "endpoint_name",
            "status",
            "summary",
            "opened_by_check",
            "resolved_by_check",
            "opened_at",
            "resolved_at",
            "acknowledged_at",
            "acknowledged_by",
            "acknowledged_by_username",
        ]
        read_only_fields = fields


class MonitoredEndpointSerializer(serializers.ModelSerializer):
    last_check = serializers.SerializerMethodField()
    last_alert = serializers.SerializerMethodField()
    open_incident = serializers.SerializerMethodField()
    is_due = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    owner_username = serializers.CharField(source="owner.username", read_only=True, allow_null=True)
    method = serializers.CharField(default="GET", max_length=10)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    alert_email = serializers.EmailField(required=False, allow_blank=True)
    expect_body_contains = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    expect_header_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    expect_header_value = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expect_json_path = serializers.CharField(required=False, allow_blank=True, max_length=255)
    expect_json_value = serializers.CharField(required=False, allow_blank=True, max_length=255)
    request_body = serializers.CharField(required=False, allow_blank=True)
    max_latency_ms = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    mute_alerts_until = serializers.DateTimeField(required=False, allow_null=True)
    quiet_hours_start = serializers.TimeField(required=False, allow_null=True)
    quiet_hours_end = serializers.TimeField(required=False, allow_null=True)
    discord_webhook_url = serializers.URLField(required=False, allow_blank=True)
    slack_webhook_url = serializers.URLField(required=False, allow_blank=True)
    request_headers = serializers.JSONField(required=False)
    auth_username = serializers.CharField(required=False, allow_blank=True, max_length=120)
    auth_secret = serializers.CharField(required=False, allow_blank=True, max_length=255)

    class Meta:
        model = MonitoredEndpoint
        fields = [
            "id",
            "owner",
            "owner_username",
            "name",
            "url",
            "method",
            "expected_status",
            "is_active",
            "is_public",
            "timeout_seconds",
            "check_interval_minutes",
            "webhook_url",
            "alert_email",
            "alert_on_failure",
            "expect_body_contains",
            "expect_header_name",
            "expect_header_value",
            "expect_json_path",
            "expect_json_value",
            "request_body",
            "max_latency_ms",
            "check_ssl_expiry",
            "ssl_warn_days",
            "mute_alerts_until",
            "quiet_hours_start",
            "quiet_hours_end",
            "request_headers",
            "auth_type",
            "auth_username",
            "auth_secret",
            "failure_threshold",
            "discord_webhook_url",
            "slack_webhook_url",
            "tags",
            "created_at",
            "updated_at",
            "last_check",
            "last_alert",
            "open_incident",
            "is_due",
        ]
        read_only_fields = [
            "id",
            "owner",
            "owner_username",
            "created_at",
            "updated_at",
            "last_check",
            "last_alert",
            "open_incident",
            "is_due",
            "tags",
        ]

    def validate_method(self, value: str) -> str:
        method = value.upper()
        if method not in HTTP_METHODS:
            raise serializers.ValidationError(
                f"Invalid method. Allowed: {', '.join(HTTP_METHODS)}."
            )
        return method

    def validate_expected_status(self, value: int) -> int:
        if value < 100 or value > 599:
            raise serializers.ValidationError(
                "Must be a valid HTTP status code (100–599)."
            )
        return value

    def validate_timeout_seconds(self, value: int) -> int:
        if value < 1 or value > 120:
            raise serializers.ValidationError(
                "Timeout must be between 1 and 120 seconds."
            )
        return value

    def validate_check_interval_minutes(self, value: int) -> int:
        if value < 1 or value > 24 * 60:
            raise serializers.ValidationError(
                "Interval must be between 1 and 1440 minutes."
            )
        return value

    def validate_ssl_warn_days(self, value: int) -> int:
        if value < 1 or value > 365:
            raise serializers.ValidationError(
                "SSL warn days must be between 1 and 365."
            )
        return value

    def validate_max_latency_ms(self, value: int | None) -> int | None:
        if value is None:
            return value
        if value < 1 or value > 600_000:
            raise serializers.ValidationError(
                "Max latency must be between 1 and 600000 ms."
            )
        return value

    def validate_auth_type(self, value: str) -> str:
        auth_type = (value or "none").lower()
        if auth_type not in AUTH_TYPES:
            raise serializers.ValidationError(
                f"Invalid auth_type. Allowed: {', '.join(AUTH_TYPES)}."
            )
        return auth_type

    def validate_failure_threshold(self, value: int) -> int:
        if value < 1 or value > 20:
            raise serializers.ValidationError(
                "Failure threshold must be between 1 and 20."
            )
        return value

    def validate_request_headers(self, value):
        if value in (None, ""):
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("request_headers must be an object.")
        cleaned: dict[str, str] = {}
        for key, item in value.items():
            name = str(key).strip()
            if not name:
                continue
            cleaned[name] = str(item)
        return cleaned

    def _parse_tag_names(self) -> list[str] | None:
        if "tags" not in self.initial_data:
            return None
        raw = self.initial_data.get("tags") or []
        if isinstance(raw, str):
            raw = [raw]
        cleaned = []
        for item in raw:
            name = str(item).strip().lower()
            if name:
                cleaned.append(name)
        return cleaned

    def _sync_tags(self, endpoint: MonitoredEndpoint, names: list[str]) -> None:
        tags = []
        for name in names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)
        endpoint.tags.set(tags)

    def create(self, validated_data: dict) -> MonitoredEndpoint:
        endpoint = MonitoredEndpoint.objects.create(**validated_data)
        tag_names = self._parse_tag_names() or []
        self._sync_tags(endpoint, tag_names)
        return endpoint

    def update(self, instance: MonitoredEndpoint, validated_data: dict) -> MonitoredEndpoint:
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        tag_names = self._parse_tag_names()
        if tag_names is not None:
            self._sync_tags(instance, tag_names)
        return instance

    def get_tags(self, obj: MonitoredEndpoint) -> list[str]:
        return list(obj.tags.values_list("name", flat=True))

    def get_last_check(self, obj: MonitoredEndpoint) -> dict | None:
        check = obj.checks.order_by("-checked_at").first()
        if check is None:
            return None
        return HealthCheckResultSerializer(check).data

    def get_last_alert(self, obj: MonitoredEndpoint) -> dict | None:
        alert = obj.alerts.order_by("-created_at").first()
        if alert is None:
            return None
        return AlertEventSerializer(alert).data

    def get_open_incident(self, obj: MonitoredEndpoint) -> dict | None:
        incident = obj.incidents.filter(status=Incident.Status.OPEN).first()
        if incident is None:
            return None
        return IncidentSerializer(incident).data

    def get_is_due(self, obj: MonitoredEndpoint) -> bool:
        last = (
            obj.checks.order_by("-checked_at")
            .values_list("checked_at", flat=True)
            .first()
        )
        return is_endpoint_due(obj, last_checked_at=last)


class StatusPageConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatusPageConfig
        fields = ["title", "subtitle", "support_url", "updated_at"]
        read_only_fields = ["updated_at"]
