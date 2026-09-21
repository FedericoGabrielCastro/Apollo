from django.db import models


class Tag(models.Model):
    """Label used to group monitored endpoints."""

    name = models.SlugField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class MonitoredEndpoint(models.Model):
    """An external or internal HTTP endpoint to track."""

    name = models.CharField(max_length=120)
    url = models.URLField()
    method = models.CharField(max_length=10, default="GET")
    expected_status = models.PositiveSmallIntegerField(default=200)
    is_active = models.BooleanField(default=True)
    is_public = models.BooleanField(
        default=True,
        help_text="Include this endpoint on the public status page.",
    )
    timeout_seconds = models.PositiveSmallIntegerField(default=5)
    check_interval_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Minimum minutes between automatic due checks.",
    )
    webhook_url = models.URLField(
        blank=True,
        help_text="Optional webhook notified on failure and recovery transitions.",
    )
    alert_email = models.EmailField(
        blank=True,
        help_text="Optional email notified on failure and recovery transitions.",
    )
    alert_on_failure = models.BooleanField(
        default=True,
        help_text="Send alerts when status transitions to down/error or recovers.",
    )
    expect_body_contains = models.CharField(
        max_length=255,
        blank=True,
        help_text="If set, response body must contain this substring.",
    )
    max_latency_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="If set, responses slower than this are marked down.",
    )
    check_ssl_expiry = models.BooleanField(
        default=False,
        help_text="For HTTPS URLs, fail when the certificate expires within ssl_warn_days.",
    )
    ssl_warn_days = models.PositiveSmallIntegerField(
        default=14,
        help_text="Days before SSL expiry to treat the endpoint as down.",
    )
    mute_alerts_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="While set and in the future, skip webhook/email (incidents still sync).",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="endpoints")
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


class AlertEvent(models.Model):
    """Record of an alert dispatched (or attempted) for a status transition."""

    class EventType(models.TextChoices):
        FAILURE = "failure", "Failure"
        RECOVERY = "recovery", "Recovery"

    class Channel(models.TextChoices):
        WEBHOOK = "webhook", "Webhook"
        EMAIL = "email", "Email"

    endpoint = models.ForeignKey(
        MonitoredEndpoint,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    check_result = models.ForeignKey(
        HealthCheckResult,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    event_type = models.CharField(max_length=16, choices=EventType.choices)
    channel = models.CharField(
        max_length=16,
        choices=Channel.choices,
        default=Channel.WEBHOOK,
    )
    target = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    success = models.BooleanField(default=False)
    response_status = models.PositiveSmallIntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.endpoint.name}: {self.event_type} ({self.channel})"


class Incident(models.Model):
    """Open/resolved outage window for an endpoint."""

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        RESOLVED = "resolved", "Resolved"

    endpoint = models.ForeignKey(
        MonitoredEndpoint,
        on_delete=models.CASCADE,
        related_name="incidents",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.OPEN,
    )
    summary = models.CharField(max_length=255)
    opened_by_check = models.ForeignKey(
        HealthCheckResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="opened_incidents",
    )
    resolved_by_check = models.ForeignKey(
        HealthCheckResult,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_incidents",
    )
    opened_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self) -> str:
        return f"{self.endpoint.name}: {self.status} ({self.summary})"
