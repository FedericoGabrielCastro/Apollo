import factory

from monitoring.models import HealthCheckResult, MonitoredEndpoint


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


class HealthCheckResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = HealthCheckResult

    endpoint = factory.SubFactory(MonitoredEndpointFactory)
    status = HealthCheckResult.Status.UP
    status_code = 200
    latency_ms = 12.5
    error_message = ""
