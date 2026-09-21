import factory

from monitoring.models import MonitoredEndpoint


class MonitoredEndpointFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MonitoredEndpoint

    name = factory.Sequence(lambda n: f"Endpoint {n}")
    url = factory.Sequence(lambda n: f"https://example.com/api/{n}/health")
    method = "GET"
    expected_status = 200
    is_active = True
