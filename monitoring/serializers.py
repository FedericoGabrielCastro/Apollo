from rest_framework import serializers

from monitoring.models import HealthCheckResult, MonitoredEndpoint

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
            "created_at",
            "updated_at",
            "last_check",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "last_check"]

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

    def get_last_check(self, obj: MonitoredEndpoint) -> dict | None:
        check = obj.checks.order_by("-checked_at").first()
        if check is None:
            return None
        return HealthCheckResultSerializer(check).data
