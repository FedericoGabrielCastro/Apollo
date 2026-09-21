import factory

from monitoring.models import (
    AlertEvent,
    HealthCheckResult,
    Incident,
    MonitoredEndpoint,
    Tag,
)


class TagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tag

    name = factory.Sequence(lambda n: f"tag-{n}")


class MonitoredEndpointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MonitoredEndpoint

    name = factory.Sequence(lambda n: f"Endpoint {n}")
    url = factory.Sequence(lambda n: f"https://example.com/api/{n}/health")
    method = "GET"
    expected_status = 200
    is_active = True
    is_public = True
    timeout_seconds = 5
    check_interval_minutes = 5
    webhook_url = ""
    alert_email = ""
    alert_on_failure = True
    expect_body_contains = ""
    max_latency_ms = None
    check_ssl_expiry = False
    ssl_warn_days = 14
    mute_alerts_until = None
    request_headers = factory.LazyFunction(dict)
    auth_type = "none"
    auth_username = ""
    auth_secret = ""
    failure_threshold = 1
    discord_webhook_url = ""
    slack_webhook_url = ""


class HealthCheckResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HealthCheckResult

    endpoint = factory.SubFactory(MonitoredEndpointFactory)
    status = HealthCheckResult.Status.UP
    status_code = 200
    latency_ms = 12.5
    error_message = ""


class AlertEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlertEvent

    endpoint = factory.SubFactory(MonitoredEndpointFactory)
    check_result = factory.LazyAttribute(
        lambda obj: HealthCheckResultFactory(endpoint=obj.endpoint)
    )
    event_type = AlertEvent.EventType.FAILURE
    channel = AlertEvent.Channel.WEBHOOK
    target = "https://hooks.example.com/apollo"
    payload = factory.LazyFunction(dict)
    success = True
    response_status = 200
    error_message = ""


class IncidentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Incident

    endpoint = factory.SubFactory(MonitoredEndpointFactory)
    status = Incident.Status.OPEN
    summary = "Endpoint became down"
    opened_by_check = factory.LazyAttribute(
        lambda obj: HealthCheckResultFactory(
            endpoint=obj.endpoint,
            status=HealthCheckResult.Status.DOWN,
            status_code=500,
        )
    )
