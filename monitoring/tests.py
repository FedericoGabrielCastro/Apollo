import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from monitoring.factories import MonitoredEndpointFactory
from monitoring.models import MonitoredEndpoint


@pytest.mark.django_db
def test_health_endpoint() -> None:
    client = APIClient()
    response = client.get(reverse("health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert response.data["service"] == "apollo"


@pytest.mark.django_db
def test_list_endpoints() -> None:
    MonitoredEndpointFactory.create_batch(3)
    client = APIClient()

    response = client.get("/api/endpoints/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 3


@pytest.mark.django_db
def test_seed_command() -> None:
    from django.core.management import call_command

    call_command("seed", count=2)
    assert MonitoredEndpoint.objects.count() == 2

    call_command("seed", flush=True, count=1)
    assert MonitoredEndpoint.objects.count() == 1
