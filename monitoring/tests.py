from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from monitoring.factories import HealthCheckResultFactory, MonitoredEndpointFactory
from monitoring.models import HealthCheckResult, MonitoredEndpoint
from monitoring.services import CheckOutcome, run_health_check


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

    call_command("seed")
    assert MonitoredEndpoint.objects.filter(name="Apollo self").exists()

    call_command("seed", flush=True, count=1)
    assert MonitoredEndpoint.objects.count() == 4  # 3 curated + 1 factory


@pytest.mark.django_db
@patch("monitoring.services.probe_endpoint")
def test_run_health_check_persists_result(mock_probe: MagicMock) -> None:
    endpoint = MonitoredEndpointFactory()
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=8.2,
        error_message="",
    )

    result = run_health_check(endpoint)

    assert result.status == HealthCheckResult.Status.UP
    assert result.status_code == 200
    assert HealthCheckResult.objects.count() == 1


@pytest.mark.django_db
@patch("monitoring.views.run_health_check")
def test_check_endpoint_action(mock_run: MagicMock) -> None:
    endpoint = MonitoredEndpointFactory()
    mock_run.return_value = HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=10.0,
    )

    client = APIClient()
    response = client.post(f"/api/endpoints/{endpoint.id}/check/")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "up"
    mock_run.assert_called_once_with(endpoint)


@pytest.mark.django_db
def test_endpoint_includes_last_check() -> None:
    endpoint = MonitoredEndpointFactory()
    HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
    )

    client = APIClient()
    response = client.get(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["last_check"]["status"] == "down"
    assert response.data["last_check"]["status_code"] == 500


@pytest.mark.django_db
@patch("monitoring.services.probe_endpoint")
def test_check_endpoints_command(mock_probe: MagicMock) -> None:
    from django.core.management import call_command

    MonitoredEndpointFactory(is_active=True)
    MonitoredEndpointFactory(is_active=False)
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=5.0,
        error_message="",
    )

    call_command("check_endpoints")

    assert HealthCheckResult.objects.count() == 1


@pytest.mark.django_db
def test_create_endpoint() -> None:
    client = APIClient()
    response = client.post(
        "/api/endpoints/",
        {
            "name": "Payments",
            "url": "https://example.com/health",
            "method": "get",
            "expected_status": 200,
            "is_active": True,
            "timeout_seconds": 5,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["method"] == "GET"
    assert MonitoredEndpoint.objects.filter(name="Payments").exists()


@pytest.mark.django_db
def test_update_endpoint() -> None:
    endpoint = MonitoredEndpointFactory(name="Old")
    client = APIClient()

    response = client.put(
        f"/api/endpoints/{endpoint.id}/",
        {
            "name": "New",
            "url": endpoint.url,
            "method": "HEAD",
            "expected_status": 204,
            "is_active": False,
            "timeout_seconds": 10,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    endpoint.refresh_from_db()
    assert endpoint.name == "New"
    assert endpoint.method == "HEAD"
    assert endpoint.expected_status == 204
    assert endpoint.is_active is False


@pytest.mark.django_db
def test_delete_endpoint() -> None:
    endpoint = MonitoredEndpointFactory()
    client = APIClient()

    response = client.delete(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not MonitoredEndpoint.objects.filter(id=endpoint.id).exists()


@pytest.mark.django_db
def test_create_endpoint_rejects_invalid_method() -> None:
    client = APIClient()
    response = client.post(
        "/api/endpoints/",
        {
            "name": "Bad",
            "url": "https://example.com/health",
            "method": "TRACE",
            "expected_status": 200,
            "is_active": True,
            "timeout_seconds": 5,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
