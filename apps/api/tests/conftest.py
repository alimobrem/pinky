"""Shared test fixtures — encryption key, auth bypass, real Postgres DB."""

import os
from collections.abc import AsyncIterator

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
    "id": "test-principal-id",
    "provider": "test",
    "email": "test@pinky.dev",
    "groups": ["pinky-admins"],
    "is_admin": True,
}


async def _mock_principal() -> dict:
    return TEST_PRINCIPAL


_test_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_test_session_factory = async_sessionmaker(_test_engine, expire_on_commit=False)


async def _get_test_db() -> AsyncIterator[AsyncSession]:
    async with _test_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()


@pytest.fixture(autouse=True)
def _set_encryption_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = os.urandom(32).hex()
    monkeypatch.setenv("PINKY_ENCRYPTION_KEY", key)


@pytest.fixture
def authed_client() -> TestClient:
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _get_test_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def unauthed_client() -> TestClient:
    return TestClient(app)
