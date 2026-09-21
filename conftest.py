import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

# Fixed test credential — not a real account secret.
TEST_PASSWORD = "pytest-only-pass"


@pytest.fixture
def user(db) -> User:
    account = User.objects.create_user(username="tester", password=TEST_PASSWORD)
    Token.objects.create(user=account)
    return account


@pytest.fixture
def api_client(user) -> APIClient:
    client = APIClient()
    token = Token.objects.get(user=user)
    client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
    return client


@pytest.fixture
def anon_client() -> APIClient:
    return APIClient()
