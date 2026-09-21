from rest_framework import serializers

from monitoring.models import HealthCheckResult, MonitoredEndpoint
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


class MonitoredEndpointSerializer(serializers.ModelSerializer):
    last_check = serializers.SerializerMethodField()
    is_due = serializers.SerializerMethodField()
    method = serializers.CharField(default="GET", max_length=10)

    class Meta:
        model = MonitoredEndpoint
        fields = [
            "id",
            "name",
            "url",
            "method",
            "expected_status",
            "is_active",
            "timeout_seconds",
            "check_interval_minutes",
            "created_at",
            "updated_at",
            "last_check",
            "is_due",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_check", "is_due"]

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

    def get_last_check(self, obj: MonitoredEndpoint) -> dict | None:
        check = obj.checks.order_by("-checked_at").first()
        if check is None:
            return None
        return HealthCheckResultSerializer(check).data

    def get_is_due(self, obj: MonitoredEndpoint) -> bool:
        last = obj.checks.order_by("-checked_at").values_list("checked_at", flat=True).first()
        return is_endpoint_due(obj, last_checked_at=last)
