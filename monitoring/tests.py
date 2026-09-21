from unittest.mock import MagicMock, patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from monitoring.factories import HealthCheckResultFactory, MonitoredEndpointFactory
from monitoring.models import HealthCheckResult, MonitoredEndpoint
from monitoring.services import CheckOutcome, run_health_check

# Fixed test credential — not a real account secret.
TEST_PASSWORD = "pytest-only-pass"


@pytest.mark.django_db
def test_health_endpoint() -> None:
    client = APIClient()
    response = client.get(reverse("health"))

    assert response.status_code == status.HTTP_200_OK
    assert response.data["status"] == "ok"
    assert response.data["service"] == "apollo"


@pytest.mark.django_db
def test_list_endpoints(api_client) -> None:
    MonitoredEndpointFactory.create_batch(3)

    response = api_client.get("/api/endpoints/")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 3


@pytest.mark.django_db
def test_seed_command() -> None:
    from django.contrib.auth.models import User
    from django.core.management import call_command
    from rest_framework.authtoken.models import Token

    call_command("seed")
    assert MonitoredEndpoint.objects.filter(name="Apollo self").exists()
    assert User.objects.filter(username="apollo").exists()
    assert Token.objects.filter(user__username="apollo").exists()

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
def test_check_endpoint_action(mock_run: MagicMock, api_client) -> None:
    endpoint = MonitoredEndpointFactory()
    mock_run.return_value = HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.UP,
        status_code=200,
        latency_ms=10.0,
    )

    response = api_client.post(f"/api/endpoints/{endpoint.id}/check/")

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["status"] == "up"
    mock_run.assert_called_once_with(endpoint)


@pytest.mark.django_db
def test_endpoint_includes_last_check(api_client) -> None:
    endpoint = MonitoredEndpointFactory()
    HealthCheckResultFactory(
        endpoint=endpoint,
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
    )

    response = api_client.get(f"/api/endpoints/{endpoint.id}/")

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
def test_create_endpoint(api_client) -> None:
    response = api_client.post(
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
def test_update_endpoint(api_client) -> None:
    endpoint = MonitoredEndpointFactory(name="Old")

    response = api_client.put(
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
            "alert_email": "ops@example.com",
            "alert_on_failure": False,
            "is_public": False,
            "tags": ["payments", "critical"],
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
    assert endpoint.alert_email == "ops@example.com"
    assert endpoint.alert_on_failure is False
    assert endpoint.is_public is False
    assert set(endpoint.tags.values_list("name", flat=True)) == {"payments", "critical"}


@pytest.mark.django_db
def test_delete_endpoint(api_client) -> None:
    endpoint = MonitoredEndpointFactory()

    response = api_client.delete(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not MonitoredEndpoint.objects.filter(id=endpoint.id).exists()


@pytest.mark.django_db
def test_create_endpoint_rejects_invalid_method(api_client) -> None:
    response = api_client.post(
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
def test_endpoint_is_due_when_never_checked(api_client) -> None:
    endpoint = MonitoredEndpointFactory(check_interval_minutes=5)

    response = api_client.get(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_due"] is True
    assert response.data["check_interval_minutes"] == 5


@pytest.mark.django_db
def test_endpoint_not_due_right_after_check(api_client) -> None:
    endpoint = MonitoredEndpointFactory(check_interval_minutes=60)
    HealthCheckResultFactory(endpoint=endpoint)

    response = api_client.get(f"/api/endpoints/{endpoint.id}/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["is_due"] is False


@pytest.mark.django_db
@patch("monitoring.views.run_due_checks")
def test_check_due_action(mock_run_due: MagicMock, api_client) -> None:
    endpoint = MonitoredEndpointFactory()
    mock_run_due.return_value = [
        HealthCheckResultFactory(
            endpoint=endpoint,
            status=HealthCheckResult.Status.UP,
            status_code=200,
            latency_ms=4.0,
        )
    ]

    response = api_client.post("/api/endpoints/check-due/")

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
def test_list_endpoint_checks(api_client) -> None:
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

    response = api_client.get(f"/api/endpoints/{endpoint.id}/checks/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    assert len(response.data["results"]) == 2
    assert response.data["results"][0]["id"] == newer.id
    assert response.data["results"][1]["id"] == older.id


@pytest.mark.django_db
def test_resolve_alert_transitions() -> None:
    from monitoring.alerts import resolve_alert_event_type
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(failure_threshold=1)
    first = HealthCheckResultFactory(
        endpoint=endpoint, status=HealthCheckResult.Status.DOWN, status_code=500
    )
    assert (
        resolve_alert_event_type(endpoint, first, None) == AlertEvent.EventType.FAILURE
    )

    second = HealthCheckResultFactory(
        endpoint=endpoint, status=HealthCheckResult.Status.DOWN, status_code=500
    )
    assert resolve_alert_event_type(endpoint, second, "down") is None

    recovery = HealthCheckResultFactory(
        endpoint=endpoint, status=HealthCheckResult.Status.UP, status_code=200
    )
    assert (
        resolve_alert_event_type(endpoint, recovery, "down")
        == AlertEvent.EventType.RECOVERY
    )


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
def test_list_endpoint_alerts(api_client) -> None:
    from monitoring.factories import AlertEventFactory

    endpoint = MonitoredEndpointFactory()
    newer = AlertEventFactory(endpoint=endpoint)
    older = AlertEventFactory(endpoint=endpoint)
    other = MonitoredEndpointFactory()
    AlertEventFactory(endpoint=other)

    response = api_client.get(f"/api/endpoints/{endpoint.id}/alerts/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 2
    ids = {item["id"] for item in response.data["results"]}
    assert newer.id in ids
    assert older.id in ids


@pytest.mark.django_db
def test_test_webhook_requires_url(api_client) -> None:
    endpoint = MonitoredEndpointFactory(webhook_url="")

    response = api_client.post(f"/api/endpoints/{endpoint.id}/test-webhook/")

    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@patch("monitoring.views.deliver_webhook")
def test_test_webhook_action(mock_deliver: MagicMock, api_client) -> None:
    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
    )
    HealthCheckResultFactory(endpoint=endpoint)
    mock_deliver.return_value = (True, 200, "")

    response = api_client.post(f"/api/endpoints/{endpoint.id}/test-webhook/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    mock_deliver.assert_called_once()


@pytest.mark.django_db
def test_endpoints_require_auth(anon_client) -> None:
    response = anon_client.get("/api/endpoints/")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_login_and_me(anon_client, user) -> None:
    response = anon_client.post(
        "/api/auth/login/",
        {"username": "tester", "password": TEST_PASSWORD},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert "token" in response.data

    anon_client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
    me = anon_client.get("/api/auth/me/")
    assert me.status_code == status.HTTP_200_OK
    assert me.data["username"] == "tester"


@pytest.mark.django_db
def test_login_rejects_bad_credentials(anon_client, user) -> None:
    response = anon_client.post(
        "/api/auth/login/",
        {"username": "tester", "password": "wrong"},
        format="json",
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_logout_deletes_token(api_client, user) -> None:
    from rest_framework.authtoken.models import Token

    assert Token.objects.filter(user=user).exists()
    response = api_client.post("/api/auth/logout/")
    assert response.status_code == status.HTTP_204_NO_CONTENT
    assert not Token.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_dashboard_metrics(api_client) -> None:
    endpoint = MonitoredEndpointFactory(name="Alpha")
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP, latency_ms=10)
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.DOWN, latency_ms=20)

    response = api_client.get("/api/dashboard/?hours=24")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["summary"]["checks_total"] == 2
    assert response.data["summary"]["checks_up"] == 1
    assert response.data["summary"]["uptime_percent"] == 50.0
    assert response.data["endpoints"][0]["name"] == "Alpha"
    assert response.data["endpoints"][0]["uptime_percent"] == 50.0


@pytest.mark.django_db
@patch("monitoring.management.commands.run_check_worker.call_command")
def test_run_check_worker_once(mock_call: MagicMock) -> None:
    from django.core.management import call_command

    call_command("run_check_worker", once=True, interval=5)
    assert mock_call.call_args_list == [
        (("check_endpoints",), {"due": True}),
        (("prune_checks",), {}),
    ]


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_failure_opens_incident(mock_probe: MagicMock, mock_deliver: MagicMock) -> None:
    from monitoring.models import Incident

    endpoint = MonitoredEndpointFactory(webhook_url="https://hooks.example.com/x")
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP)
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=11.0,
        error_message="boom",
    )
    mock_deliver.return_value = (True, 200, "")

    run_health_check(endpoint)

    incident = Incident.objects.get()
    assert incident.status == Incident.Status.OPEN
    assert "boom" in incident.summary


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_email")
@patch("monitoring.services.probe_endpoint")
def test_email_alert_on_failure(mock_probe: MagicMock, mock_email: MagicMock) -> None:
    from monitoring.models import AlertEvent

    endpoint = MonitoredEndpointFactory(alert_email="ops@example.com", webhook_url="")
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.ERROR,
        status_code=None,
        latency_ms=3.0,
        error_message="timeout",
    )
    mock_email.return_value = (True, "")

    run_health_check(endpoint)

    alert = AlertEvent.objects.get()
    assert alert.channel == AlertEvent.Channel.EMAIL
    assert alert.target == "ops@example.com"


@pytest.mark.django_db
def test_public_status_endpoint(anon_client) -> None:
    endpoint = MonitoredEndpointFactory(name="Public API", is_public=True, is_active=True)
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP)
    MonitoredEndpointFactory(name="Hidden", is_public=False)

    response = anon_client.get("/api/status/public/")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["overall"] == "operational"
    names = [row["name"] for row in response.data["endpoints"]]
    assert "Public API" in names
    assert "Hidden" not in names


@pytest.mark.django_db
def test_list_incidents(api_client) -> None:
    from monitoring.factories import IncidentFactory
    from monitoring.models import Incident

    IncidentFactory(status=Incident.Status.OPEN)
    IncidentFactory(status=Incident.Status.RESOLVED)

    response = api_client.get("/api/incidents/?status=open")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["status"] == "open"


@pytest.mark.django_db
def test_filter_endpoints_by_tag(api_client) -> None:
    from monitoring.factories import TagFactory

    tag = TagFactory(name="core")
    matched = MonitoredEndpointFactory(name="Core API")
    matched.tags.add(tag)
    MonitoredEndpointFactory(name="Other")

    response = api_client.get("/api/endpoints/?tag=core")

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["name"] == "Core API"


@pytest.mark.django_db
@patch("monitoring.services.check_ssl_certificate", return_value=None)
@patch("httpx.Client")
def test_body_assertion_marks_down(mock_client_cls: MagicMock, _ssl: MagicMock) -> None:
    from monitoring.models import HealthCheckResult
    from monitoring.services import probe_endpoint

    endpoint = MonitoredEndpointFactory(expect_body_contains="healthy")
    response = MagicMock()
    response.status_code = 200
    response.text = "status=degraded"
    mock_client_cls.return_value.__enter__.return_value.request.return_value = response

    outcome = probe_endpoint(endpoint)

    assert outcome.status == HealthCheckResult.Status.DOWN
    assert "missing expected text" in outcome.error_message


@pytest.mark.django_db
@patch("monitoring.services.check_ssl_certificate", return_value=None)
@patch("httpx.Client")
def test_max_latency_marks_down(mock_client_cls: MagicMock, _ssl: MagicMock) -> None:
    from monitoring.models import HealthCheckResult
    from monitoring.services import probe_endpoint

    endpoint = MonitoredEndpointFactory(max_latency_ms=1)
    response = MagicMock()
    response.status_code = 200
    response.text = "ok"

    def slow_request(*_args, **_kwargs):
        import time

        time.sleep(0.02)
        return response

    mock_client_cls.return_value.__enter__.return_value.request.side_effect = slow_request

    outcome = probe_endpoint(endpoint)

    assert outcome.status == HealthCheckResult.Status.DOWN
    assert "exceeds max" in outcome.error_message


@pytest.mark.django_db
@patch(
    "monitoring.services.check_ssl_certificate",
    return_value="TLS certificate expires in 2 day(s) (warn threshold 14)",
)
def test_ssl_warn_marks_down(mock_ssl: MagicMock) -> None:
    from monitoring.models import HealthCheckResult
    from monitoring.services import probe_endpoint

    endpoint = MonitoredEndpointFactory(
        url="https://example.com/health",
        check_ssl_expiry=True,
        ssl_warn_days=14,
    )

    outcome = probe_endpoint(endpoint)

    assert outcome.status == HealthCheckResult.Status.DOWN
    assert "TLS certificate" in outcome.error_message
    mock_ssl.assert_called_once()


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_mute_alerts_skips_webhook(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from django.utils import timezone
    from datetime import timedelta

    from monitoring.models import AlertEvent, HealthCheckResult, Incident
    from monitoring.services import run_health_check

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
        mute_alerts_until=timezone.now() + timedelta(hours=1),
    )
    mock_probe.return_value = __import__(
        "monitoring.services", fromlist=["CheckOutcome"]
    ).CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=10.0,
        error_message="boom",
    )

    run_health_check(endpoint)

    mock_deliver.assert_not_called()
    assert AlertEvent.objects.count() == 0
    assert Incident.objects.filter(status=Incident.Status.OPEN).count() == 1


@pytest.mark.django_db
def test_create_endpoint_with_assertions(api_client) -> None:
    response = api_client.post(
        "/api/endpoints/",
        {
            "name": "Asserted",
            "url": "https://example.com/health",
            "method": "GET",
            "expected_status": 200,
            "expect_body_contains": "ok",
            "max_latency_ms": 500,
            "check_ssl_expiry": True,
            "ssl_warn_days": 7,
            "mute_alerts_until": None,
        },
        format="json",
    )

    assert response.status_code == status.HTTP_201_CREATED
    assert response.data["expect_body_contains"] == "ok"
    assert response.data["max_latency_ms"] == 500
    assert response.data["check_ssl_expiry"] is True
    assert response.data["ssl_warn_days"] == 7


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_failure_threshold_delays_alert(
    mock_probe: MagicMock,
    mock_deliver: MagicMock,
) -> None:
    from monitoring.models import AlertEvent, Incident
    from monitoring.services import CheckOutcome, run_health_check

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
        failure_threshold=2,
    )
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=10.0,
        error_message="boom",
    )
    mock_deliver.return_value = (True, 200, "")

    run_health_check(endpoint)
    assert AlertEvent.objects.count() == 0
    assert Incident.objects.count() == 0

    run_health_check(endpoint)
    assert AlertEvent.objects.count() == 1
    assert Incident.objects.filter(status=Incident.Status.OPEN).count() == 1
    mock_deliver.assert_called_once()


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_discord")
@patch("monitoring.services.probe_endpoint")
def test_discord_alert_channel(
    mock_probe: MagicMock,
    mock_discord: MagicMock,
) -> None:
    from monitoring.models import AlertEvent
    from monitoring.services import CheckOutcome, run_health_check

    endpoint = MonitoredEndpointFactory(
        discord_webhook_url="https://example.com/hooks/discord",
    )
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=10.0,
        error_message="boom",
    )
    mock_discord.return_value = (True, 204, "")

    run_health_check(endpoint)

    assert AlertEvent.objects.filter(channel=AlertEvent.Channel.DISCORD).count() == 1
    mock_discord.assert_called_once()


@pytest.mark.django_db
@patch("monitoring.services.check_ssl_certificate", return_value=None)
@patch("httpx.Client")
def test_probe_sends_bearer_auth(mock_client_cls: MagicMock, _ssl: MagicMock) -> None:
    from monitoring.services import probe_endpoint

    endpoint = MonitoredEndpointFactory(
        auth_type="bearer",
        auth_secret="secret-token",
        request_headers={"X-Trace": "1"},
    )
    response = MagicMock()
    response.status_code = 200
    response.text = "ok"
    request_mock = mock_client_cls.return_value.__enter__.return_value.request
    request_mock.return_value = response

    probe_endpoint(endpoint)

    kwargs = request_mock.call_args.kwargs
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["headers"]["X-Trace"] == "1"


@pytest.mark.django_db
def test_status_page_config_update(api_client) -> None:
    response = api_client.patch(
        "/api/status/config/",
        {
            "title": "Acme Status",
            "subtitle": "Platform health",
            "support_url": "https://support.example.com",
        },
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.data["title"] == "Acme Status"

    public = api_client.get("/api/status/public/")
    # public needs anon - but api_client is authenticated which is fine for GET public
    # Actually PublicStatusView uses AllowAny - api_client can still call it
    # Wait - api_client is token authenticated. Public status allows any.
    # But we used api_client for patch - for public use anon. Let's just check via build or re-get.

    from rest_framework.test import APIClient

    anon = APIClient()
    public = anon.get("/api/status/public/")
    assert public.status_code == status.HTTP_200_OK
    assert public.data["title"] == "Acme Status"
    assert public.data["subtitle"] == "Platform health"
    assert public.data["support_url"] == "https://support.example.com"


@pytest.mark.django_db
def test_dashboard_includes_series(api_client) -> None:
    endpoint = MonitoredEndpointFactory()
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP)
    HealthCheckResultFactory(
        endpoint=endpoint, status=HealthCheckResult.Status.DOWN, status_code=500
    )

    response = api_client.get("/api/dashboard/?hours=24")

    assert response.status_code == status.HTTP_200_OK
    assert "series" in response.data
    assert isinstance(response.data["series"], list)
    assert len(response.data["series"]) == 24


@pytest.mark.django_db
def test_export_checks_csv(api_client) -> None:
    endpoint = MonitoredEndpointFactory(name="CSV Target")
    HealthCheckResultFactory(endpoint=endpoint, status=HealthCheckResult.Status.UP)

    response = api_client.get("/api/exports/checks.csv?hours=24")

    assert response.status_code == status.HTTP_200_OK
    assert "text/csv" in response["Content-Type"]
    body = response.content.decode()
    assert "endpoint_name" in body
    assert "CSV Target" in body


@pytest.mark.django_db
def test_prune_old_checks() -> None:
    from datetime import timedelta

    from django.utils import timezone

    from monitoring.retention import prune_old_checks

    endpoint = MonitoredEndpointFactory()
    old = HealthCheckResultFactory(endpoint=endpoint)
    HealthCheckResult.objects.filter(pk=old.pk).update(
        checked_at=timezone.now() - timedelta(days=40)
    )
    fresh = HealthCheckResultFactory(endpoint=endpoint)

    deleted = prune_old_checks(days=30)

    assert deleted == 1
    assert not HealthCheckResult.objects.filter(pk=old.pk).exists()
    assert HealthCheckResult.objects.filter(pk=fresh.pk).exists()


@pytest.mark.django_db
def test_checks_pagination(api_client) -> None:
    endpoint = MonitoredEndpointFactory()
    HealthCheckResultFactory.create_batch(5, endpoint=endpoint)

    response = api_client.get(f"/api/endpoints/{endpoint.id}/checks/?page=1&page_size=2")

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 5
    assert response.data["page_size"] == 2
    assert len(response.data["results"]) == 2
    assert response.data["total_pages"] == 3


@pytest.mark.django_db
def test_register_and_own_endpoints(anon_client, settings) -> None:
    settings.APOLLO_ALLOW_REGISTER = True
    response = anon_client.post(
        "/api/auth/register/",
        {"username": "newbie", "password": TEST_PASSWORD, "email": "n@example.com"},
        format="json",
    )
    assert response.status_code == status.HTTP_201_CREATED
    token = response.data["token"]

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
    created = client.post(
        "/api/endpoints/",
        {
            "name": "Mine",
            "url": "https://example.com/mine",
            "method": "GET",
            "expected_status": 200,
        },
        format="json",
    )
    assert created.status_code == status.HTTP_201_CREATED
    assert created.data["owner_username"] == "newbie"

    other = MonitoredEndpointFactory(name="Someone else", owner=None)
    # Unowned still visible; owned-by-other should hide for non-staff after we assign owner
    from django.contrib.auth.models import User

    stranger = User.objects.create_user(username="stranger", password=TEST_PASSWORD)
    other.owner = stranger
    other.save(update_fields=["owner"])

    listing = client.get("/api/endpoints/")
    names = {row["name"] for row in listing.data}
    assert "Mine" in names
    assert "Someone else" not in names


@pytest.mark.django_db
@patch("monitoring.services.check_ssl_certificate", return_value=None)
@patch("httpx.Client")
def test_json_path_and_header_assertions(mock_client_cls: MagicMock, _ssl: MagicMock) -> None:
    from monitoring.services import probe_endpoint

    endpoint = MonitoredEndpointFactory(
        expect_json_path="status",
        expect_json_value="ok",
        expect_header_name="X-Health",
        expect_header_value="green",
    )
    response = MagicMock()
    response.status_code = 200
    response.text = '{"status":"ok"}'
    response.headers = {"X-Health": "green"}
    mock_client_cls.return_value.__enter__.return_value.request.return_value = response

    outcome = probe_endpoint(endpoint)
    assert outcome.status == HealthCheckResult.Status.UP

    response.text = '{"status":"bad"}'
    outcome = probe_endpoint(endpoint)
    assert outcome.status == HealthCheckResult.Status.DOWN
    assert "JSON path" in outcome.error_message


@pytest.mark.django_db
@patch("monitoring.alerts.deliver_webhook")
@patch("monitoring.services.probe_endpoint")
def test_quiet_hours_mute_alerts(mock_probe: MagicMock, mock_deliver: MagicMock) -> None:
    from datetime import time

    from monitoring.models import AlertEvent, Incident
    from monitoring.services import CheckOutcome, run_health_check

    endpoint = MonitoredEndpointFactory(
        webhook_url="https://hooks.example.com/apollo",
        quiet_hours_start=time(0, 0),
        quiet_hours_end=time(23, 59, 59),
    )
    mock_probe.return_value = CheckOutcome(
        status=HealthCheckResult.Status.DOWN,
        status_code=500,
        latency_ms=1.0,
        error_message="down",
    )

    run_health_check(endpoint)

    mock_deliver.assert_not_called()
    assert AlertEvent.objects.count() == 0
    assert Incident.objects.filter(status=Incident.Status.OPEN).count() == 1


@pytest.mark.django_db
def test_acknowledge_incident(api_client) -> None:
    from monitoring.factories import IncidentFactory
    from monitoring.models import Incident

    incident = IncidentFactory(status=Incident.Status.OPEN)
    response = api_client.post(f"/api/incidents/{incident.id}/acknowledge/")

    assert response.status_code == status.HTTP_200_OK
    incident.refresh_from_db()
    assert incident.acknowledged_at is not None
    assert response.data["acknowledged_by_username"] == "tester"
