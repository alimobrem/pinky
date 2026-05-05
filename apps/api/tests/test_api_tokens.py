"""Tests for API token CRUD and Bearer auth validation."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import httpx
import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pinky_api.app import app
from pinky_api.auth.middleware import get_current_principal
from pinky_api.db.deps import get_db
from pinky_api.db.engine import close_engine, init_engine
from pinky_api.models.extensibility import ApiToken
from pinky_api.models.principal import Principal

TEST_DB_URL = "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky"
_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_factory = async_sessionmaker(_engine, expire_on_commit=False)

PRINCIPAL_ID = UUID("00000000-0000-0000-0000-000000000010")


async def _mock_principal() -> dict:
    return {
        "id": str(PRINCIPAL_ID),
        "provider": "test",
        "email": "test@pinky.dev",
        "groups": ["pinky-admins"],
        "is_admin": True,
    }


async def _test_db():
    async with _factory() as s:
        yield s


@pytest.fixture
async def seed_principal():
    """Ensure principal exists in DB, init engine for Bearer tests, clean up after."""
    init_engine(TEST_DB_URL)

    created_principal = False
    async with _factory() as s:
        existing = await s.execute(select(Principal).where(Principal.id == PRINCIPAL_ID))
        if existing.scalar_one_or_none() is None:
            s.add(
                Principal(
                    id=PRINCIPAL_ID,
                    provider="test",
                    subject="test-admin-tokens",
                    email="test@pinky.dev",
                    display_name="Test Admin",
                    groups=["pinky-admins"],
                )
            )
            await s.commit()
            created_principal = True

    yield

    async with _factory() as s:
        await s.execute(delete(ApiToken).where(ApiToken.principal_id == PRINCIPAL_ID))
        if created_principal:
            await s.execute(delete(Principal).where(Principal.id == PRINCIPAL_ID))
        await s.commit()

    # Clean up engine to avoid polluting other tests
    await close_engine()


@pytest.fixture
async def authed(seed_principal: None):
    """Async client with auth bypass for CRUD tests."""
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# ── CRUD tests ──


@pytest.mark.asyncio
async def test_create_token(authed: httpx.AsyncClient) -> None:
    resp = await authed.post("/api/v1/api-tokens", json={
        "name": "ci-deploy",
        "scopes": ["read", "write"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "token" in data
    assert data["name"] == "ci-deploy"
    assert data["scopes"] == ["read", "write"]
    assert "id" in data
    assert "created_at" in data
    assert len(data["token"]) > 20


@pytest.mark.asyncio
async def test_list_tokens(authed: httpx.AsyncClient) -> None:
    await authed.post("/api/v1/api-tokens", json={"name": "token-a"})
    await authed.post("/api/v1/api-tokens", json={"name": "token-b"})

    resp = await authed.get("/api/v1/api-tokens")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    names = [t["name"] for t in data["items"]]
    assert "token-a" in names
    assert "token-b" in names

    for item in data["items"]:
        assert "token_hash" not in item
        assert "token" not in item


@pytest.mark.asyncio
async def test_revoke_token(authed: httpx.AsyncClient) -> None:
    resp = await authed.post("/api/v1/api-tokens", json={"name": "to-revoke"})
    token_id = resp.json()["id"]

    resp = await authed.delete(f"/api/v1/api-tokens/{token_id}")
    assert resp.status_code == 204

    resp = await authed.get("/api/v1/api-tokens")
    ids = [t["id"] for t in resp.json()["items"]]
    assert token_id not in ids


@pytest.mark.asyncio
async def test_revoke_nonexistent_token(authed: httpx.AsyncClient) -> None:
    resp = await authed.delete("/api/v1/api-tokens/00000000-0000-0000-0000-000000000099")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_token_with_expiry(authed: httpx.AsyncClient) -> None:
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    resp = await authed.post("/api/v1/api-tokens", json={
        "name": "expiring-token",
        "scopes": ["read"],
        "expires_at": future,
    })
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None


# ── Bearer auth tests ──


@pytest.mark.asyncio
async def test_bearer_auth_valid_token(seed_principal: None) -> None:
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as authed:
        resp = await authed.post("/api/v1/api-tokens", json={"name": "bearer-test"})
        raw_token = resp.json()["token"]

    # Now use a client without auth override
    app.dependency_overrides.pop(get_current_principal, None)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.get(
            "/api/v1/api-tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert resp.status_code == 200

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bearer_auth_revoked_token(seed_principal: None) -> None:
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as authed:
        resp = await authed.post("/api/v1/api-tokens", json={"name": "revoke-bearer"})
        data = resp.json()
        raw_token = data["token"]
        token_id = data["id"]
        await authed.delete(f"/api/v1/api-tokens/{token_id}")

    app.dependency_overrides.pop(get_current_principal, None)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.get(
            "/api/v1/api-tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert resp.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bearer_auth_expired_token(seed_principal: None) -> None:
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db
    transport = httpx.ASGITransport(app=app)

    past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as authed:
        resp = await authed.post("/api/v1/api-tokens", json={
            "name": "expired-bearer",
            "expires_at": past,
        })
        raw_token = resp.json()["token"]

    app.dependency_overrides.pop(get_current_principal, None)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.get(
            "/api/v1/api-tokens",
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert resp.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bearer_auth_invalid_token(seed_principal: None) -> None:
    app.dependency_overrides[get_db] = _test_db
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.get(
            "/api/v1/api-tokens",
            headers={"Authorization": "Bearer totally-bogus-token"},
        )
        assert resp.status_code == 401

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bearer_auth_skips_csrf(seed_principal: None) -> None:
    """Bearer token auth should not require CSRF for state-changing requests."""
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as authed:
        resp = await authed.post("/api/v1/api-tokens", json={"name": "csrf-test"})
        raw_token = resp.json()["token"]

    # POST without X-CSRF-Token — should succeed for Bearer auth
    app.dependency_overrides.pop(get_current_principal, None)
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as raw:
        resp = await raw.post(
            "/api/v1/api-tokens",
            json={"name": "created-via-bearer"},
            headers={"Authorization": f"Bearer {raw_token}"},
        )
        assert resp.status_code == 201

    app.dependency_overrides.clear()
