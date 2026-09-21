from django.db import models


class MonitoredEndpoint(models.Model):
    """An external or internal HTTP endpoint to track."""

    name = models.CharField(max_length=120)
    url = models.URLField()
    method = models.CharField(max_length=10, default="GET")
    expected_status = models.PositiveSmallIntegerField(default=200)
    is_active = models.BooleanField(default=True)
    timeout_seconds = models.PositiveSmallIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.url})"


class HealthCheckResult(models.Model):
    """Outcome of a single probe against a monitored endpoint."""

    class Status(models.TextChoices):
        UP = "up", "Up"
        DOWN = "down", "Down"
        ERROR = "error", "Error"

    endpoint = models.ForeignKey(
        MonitoredEndpoint,
        on_delete=models.CASCADE,
        related_name="checks",
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    latency_ms = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_at"]

    def __str__(self) -> str:
        return f"{self.endpoint.name}: {self.status} @ {self.checked_at}"
