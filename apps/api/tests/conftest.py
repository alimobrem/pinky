"""Shared test fixtures — encryption key and auth bypass."""

import os

import pytest
from fastapi.testclient import TestClient

from pinky_api.app import app
from pinky_api.auth.middleware import get_current_principal


TEST_PRINCIPAL = {
    "id": "test-principal-id",
    "provider": "test",
    "email": "test@pinky.dev",
    "groups": ["pinky-admins"],
    "is_admin": True,
}


async def _mock_principal() -> dict:
    return TEST_PRINCIPAL


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = os.urandom(32).hex()
    monkeypatch.setenv("PINKY_ENCRYPTION_KEY", key)


@pytest.fixture
def authed_client() -> TestClient:
    app.dependency_overrides[get_current_principal] = _mock_principal
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client() -> TestClient:
    return TestClient(app)
