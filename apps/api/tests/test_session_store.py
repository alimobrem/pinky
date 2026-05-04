"""Integration tests for session store against real Redis."""

import os

import pytest
import redis.asyncio as aioredis

from pinky_api.auth.session_store import SessionStore

REDIS_URL = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379/1")

TEST_PRINCIPAL = {"id": "p1", "email": "test@pinky.dev", "groups": ["users"]}


@pytest.fixture
async def store():
    client = aioredis.from_url(REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception:
        pytest.skip("Redis not available")
    s = SessionStore(client, idle_timeout_minutes=1, absolute_timeout_hours=1)
    yield s
    await client.flushdb()
    await client.aclose()


@pytest.mark.asyncio
async def test_create_and_validate(store: SessionStore) -> None:
    raw_token, csrf = await store.create("p1", TEST_PRINCIPAL)
    assert len(raw_token) > 32
    assert len(csrf) > 20

    principal = await store.validate(raw_token)
    assert principal is not None
    assert principal["id"] == "p1"
    assert principal["email"] == "test@pinky.dev"


@pytest.mark.asyncio
async def test_invalid_token_returns_none(store: SessionStore) -> None:
    result = await store.validate("completely-bogus-token")
    assert result is None


@pytest.mark.asyncio
async def test_revoke_invalidates_session(store: SessionStore) -> None:
    raw_token, _ = await store.create("p1", TEST_PRINCIPAL)
    assert await store.validate(raw_token) is not None

    revoked = await store.revoke(raw_token)
    assert revoked is True

    assert await store.validate(raw_token) is None


@pytest.mark.asyncio
async def test_csrf_token_matches(store: SessionStore) -> None:
    raw_token, expected_csrf = await store.create("p1", TEST_PRINCIPAL)
    actual_csrf = await store.get_csrf_token(raw_token)
    assert actual_csrf == expected_csrf


@pytest.mark.asyncio
async def test_csrf_token_none_for_invalid_session(store: SessionStore) -> None:
    csrf = await store.get_csrf_token("bogus-token")
    assert csrf is None


@pytest.mark.asyncio
async def test_session_age(store: SessionStore) -> None:
    raw_token, _ = await store.create("p1", TEST_PRINCIPAL)
    age = await store.get_session_age_minutes(raw_token)
    assert age == 0  # just created


@pytest.mark.asyncio
async def test_double_revoke_returns_false(store: SessionStore) -> None:
    raw_token, _ = await store.create("p1", TEST_PRINCIPAL)
    await store.revoke(raw_token)
    assert await store.revoke(raw_token) is False
