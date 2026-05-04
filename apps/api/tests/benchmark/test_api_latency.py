"""API endpoint latency benchmarks.

Establishes baseline response times for key endpoints.
Run with: pytest tests/benchmark/ -v --benchmark-only
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pinky_api.app import app
from pinky_api.auth.middleware import get_current_principal
from pinky_api.db.deps import get_db

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky",
)

TEST_PRINCIPAL = {
    "id": "00000000-0000-0000-0000-000000000010",
    "provider": "test",
    "email": "bench@pinky.dev",
    "groups": ["pinky-admins"],
    "is_admin": True,
}

_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _mock_principal() -> dict:
    return TEST_PRINCIPAL


async def _get_db():
    async with _session_factory() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _get_db
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()


def test_healthz_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/healthz")
    assert result.status_code == 200


def test_work_items_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/work-items")
    assert result.status_code == 200


def test_issues_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/issues")
    assert result.status_code == 200


def test_clusters_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/clusters")
    assert result.status_code == 200


def test_history_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/history")
    assert result.status_code == 200


def test_alerts_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/alerts")
    assert result.status_code == 200


def test_definitions_list_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/definitions")
    assert result.status_code == 200


def test_analytics_roi_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/analytics/roi")
    assert result.status_code == 200


def test_work_items_filtered_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/work-items", params={"status": "ready"})
    assert result.status_code == 200


def test_issues_filtered_latency(client: TestClient, benchmark) -> None:
    result = benchmark(client.get, "/api/v1/issues", params={"status": "open"})
    assert result.status_code == 200
