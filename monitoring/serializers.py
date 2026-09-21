from rest_framework import serializers

from monitoring.models import HealthCheckResult, MonitoredEndpoint


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

    def get_last_check(self, obj: MonitoredEndpoint) -> dict | None:
        check = obj.checks.order_by("-checked_at").first()
        if check is None:
            return None
        return HealthCheckResultSerializer(check).data
