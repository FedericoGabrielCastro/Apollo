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
            "check_interval_minutes": 15,
            "webhook_url": "https://hooks.example.com/x",
            "alert_on_failure": False,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    endpoint.refresh_from_db()
    assert endpoint.name == "New"
    assert endpoint.method == "HEAD"
    assert endpoint.expected_status == 204
    assert endpoint.is_active is False
    assert endpoint.check_interval_minutes == 15
    assert endpoint.webhook_url == "https://hooks.example.com/x"
    assert endpoint.alert_on_failure is False


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


@pytest.mark.django_db
def test_endpoint_is_due_when_never_checked() -> None:
    endpoint = MonitoredEndpointFactory(check_interval_minutes=5)
    client = APIClient()

    response = client.get(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_due"] is True
    assert response.data["check_interval_minutes"] == 5


@pytest.mark.django_db
def test_endpoint_not_due_right_after_check() -> None:
    endpoint = MonitoredEndpointFactory(check_interval_minutes=60)
    HealthCheckResultFactory(endpoint=endpoint)
    client = APIClient()

    response = client.get(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_due"] is False


@pytest.mark.django_db
@patch("monitoring.views.run_due_checks")
def test_check_due_action(mock_run_due: MagicMock) -> None:
    endpoint = MonitoredEndpointFactory()
    mock_run_due.return_value = [
        HealthCheckResultFactory(
            endpoint=endpoint,
            status=HealthCheckResult.Status.UP,
            status_code=200,
            latency_ms=4.0,
        )
    ]
    client = APIClient()

    response = client.post("/api/endpoints/check-due/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["checked"] == 1
    assert response.data["results"][0]["status"] == "up"
    mock_run_due.assert_called_once_with()


@pytest.mark.django_db
@patch("monitoring.services.probe_endpoint")
def test_check_endpoints_due_skips_fresh(mock_probe: MagicMock) -> None:
    from django.core.management import call_command

    fresh = MonitoredEndpointFactory(check_interval_minutes=60)
    HealthCheckResultFactory(endpoint=fresh)
    due = MonitoredEndpointFactory(check_interval_minutes=1, name="Due one")
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=5.0,
        error_message="",
    )

    call_command("check_endpoints", due=True)

    assert HealthCheckResult.objects.filter(endpoint=due).count() == 1
    assert HealthCheckResult.objects.filter(endpoint=fresh).count() == 1


@pytest.mark.django_db
def test_list_endpoint_checks() -> None:
    endpoint = MonitoredEndpointFactory()
    older = HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
    )
    newer = HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.UP,
        status_code=200,
    )
    other = MonitoredEndpointFactory()
    HealthCheckResultFactory(endpoint=other)

    client = APIClient()
    response = client.get(f"/api/endpoints/{endpoint.id}/checks/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
    assert response.data[0]["id"] == newer.id
    assert response.data[1]["id"] == older.id


@pytest.mark.django_db
def test_resolve_alert_transitions() -> None:
    from monitoring.alerts import resolve_alert_event_type
    from monitoring.models import AlertEvent

    assert resolve_alert_event_type(None, "down") == AlertEvent.EventType.FAILURE
    assert resolve_alert_event_type("up", "error") == AlertEvent.EventType.FAILURE
    assert resolve_alert_event_type("down", "down") is None
    assert resolve_alert_event_type("error", "up") == AlertEvent.EventType.RECOVERY
    assert resolve_alert_event_type("up", "up") is None


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_failure_transition_sends_webhook(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
        alert_on_failure=True,
    )
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP)
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=20.0,
        error_message="Expected status 200, got 500",
    )
    mock_deliver.return_value = (True, 200, "")

    run_health_check(endpoint)

    assert AlertEvent.objects.count() == 1
    alert = AlertEvent.objects.get()
    assert alert.event_type == AlertEvent.EventType.FAILURE
    assert alert.success is True
    mock_deliver.assert_called_once()


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_consecutive_failures_do_not_realert(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
    )
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.DOWN)
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=20.0,
        error_message="still down",
    )

    run_health_check(endpoint)

    assert AlertEvent.objects.count() == 0
    mock_deliver.assert_not_called()


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_recovery_sends_webhook(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
    )
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.ERROR)
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=8.0,
        error_message="",
    )
    mock_deliver.return_value = (True, 204, "")

    run_health_check(endpoint)

    alert = AlertEvent.objects.get()
    assert alert.event_type == AlertEvent.EventType.RECOVERY


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_alerts_disabled_skips_webhook(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
        alert_on_failure=False,
    )
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=20.0,
        error_message="down",
    )

    run_health_check(endpoint)

    assert AlertEvent.objects.count() == 0
    mock_deliver.assert_not_called()


@pytest.mark.django_db
def test_list_endpoint_alerts() -> None:
    from monitoring.factories import AlertEventFactory

    endpoint = MonitoredEndpointFactory()
    newer = AlertEventFactory(endpoint=endpoint)
    older = AlertEventFactory(endpoint=endpoint)
    other = MonitoredEndpointFactory()
    AlertEventFactory(endpoint=other)

    client = APIClient()
    response = client.get(f"/api/endpoints/{endpoint.id}/alerts/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 2
    ids = {item["id"] for item in response.data}
    assert newer.id in ids
    assert older.id in ids


@pytest.mark.django_db
def test_test_webhook_requires_url() -> None:
    endpoint = MonitoredEndpointFactory(webhook_url="")
    client = APIClient()

    response = client.post(f"/api/endpoints/{endpoint.id}/test-webhook/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@patch("monitoring.views.deliver_webhook")
def test_test_webhook_action(mock_deliver: MagicMock) -> None:
    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
    )
    HealthCheckResultFactory(endpoint=endpoint)
    mock_deliver.return_value = (True, 200, "")
    client = APIClient()

    response = client.post(f"/api/endpoints/{endpoint.id}/test-webhook/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    mock_deliver.assert_called_once()
