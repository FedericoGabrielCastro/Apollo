from rest_framework import serializers

from monitoring.models import (
    AlertEvent,
    HealthCheckResult,
    Incident,
    MonitoredEndpoint,
    Tag,
)
from monitoring.services import is_endpoint_due

HTTP_METHODS = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE")


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
        ]
        read_only_fields = fields


class MonitoredEndpointSerializer(serializers.ModelSerializer):
    last_check = serializers.SerializerMethodField()
    last_alert = serializers.SerializerMethodField()
    open_incident = serializers.SerializerMethodField()
    is_due = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    method = serializers.CharField(default="GET", max_length=10)
    webhook_url = serializers.URLField(required=False, allow_blank=True)
    alert_email = serializers.EmailField(required=False, allow_blank=True)
    expect_body_contains = serializers.CharField(
        required=False, allow_blank=True, max_length=255
    )
    max_latency_ms = serializers.IntegerField(
        required=False, allow_null=True, min_value=1
    )
    mute_alerts_until = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = MonitoredEndpoint
        fields = [
            "id",
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
            "max_latency_ms",
            "check_ssl_expiry",
            "ssl_warn_days",
            "mute_alerts_until",
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
