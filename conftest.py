import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient


@pytest.fixture
def user(db) -> User:
    account = User.objects.create_user(username="tester", password="secret123")
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
