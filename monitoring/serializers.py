from rest_framework import serializers

from monitoring.models import MonitoredEndpoint


class MonitoredEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = MonitoredEndpoint
        fields = [
            "id",
            "name",
            "url",
            "method",
            "expected_status",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
