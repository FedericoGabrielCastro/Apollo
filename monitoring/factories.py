import factory

from monitoring.models import AlertEvent, HealthCheckResult, MonitoredEndpoint


class MonitoredEndpointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MonitoredEndpoint

    name = factory.Sequence(lambda n: f"Endpoint {n}")
    url = factory.Sequence(lambda n: f"https://example.com/api/{n}/health")
    method = "GET"
    expected_status = 200
    is_active = True
    timeout_seconds = 5
    check_interval_minutes = 5
    webhook_url = ""
    alert_on_failure = True


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
