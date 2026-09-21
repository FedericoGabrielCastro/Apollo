from django.db import models


class MonitoredEndpoint(models.Model):
    """An external or internal HTTP endpoint to track."""

    name = models.CharField(max_length=120)
    url = models.URLField()
    method = models.CharField(max_length=10, default="GET")
    expected_status = models.PositiveSmallIntegerField(default=200)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.url})"
