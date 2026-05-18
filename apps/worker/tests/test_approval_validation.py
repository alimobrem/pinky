"""Tests for approval validation — digest enforcement and expiry."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest


class FakePool:
    def __init__(self, fetchrow_result: dict | None = None) -> None:
        self._result = fetchrow_result

    async def fetchrow(self, query: str, *args):  # noqa: ANN002
        return self._result


@pytest.fixture(autouse=True)
def _mock_activity_context():
    with patch("temporalio.activity.heartbeat"):
        yield


@pytest.mark.asyncio
async def test_validate_approval_rejects_empty_digest() -> None:
    """Empty changeset_digest must be rejected, not bypassed."""
    pool = FakePool(fetchrow_result={
        "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "")
    assert result["valid"] is False
    assert "required" in result["reason"]


@pytest.mark.asyncio
async def test_validate_approval_rejects_wrong_digest() -> None:
    pool = FakePool(fetchrow_result={
        "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "wrong_digest")
    assert result["valid"] is False
    assert "changed" in result["reason"]


@pytest.mark.asyncio
async def test_validate_approval_accepts_correct_digest() -> None:
    pool = FakePool(fetchrow_result={
        "status": "pending",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "abc123")
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_validate_approval_rejects_expired() -> None:
    pool = FakePool(fetchrow_result={
        "status": "pending",
        "expires_at": datetime.now(UTC) - timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "abc123")
    assert result["valid"] is False
    assert "expired" in result["reason"]


@pytest.mark.asyncio
async def test_validate_approval_rejects_not_found() -> None:
    pool = FakePool(fetchrow_result=None)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "abc123")
    assert result["valid"] is False
    assert "not found" in result["reason"]


@pytest.mark.asyncio
async def test_validate_approval_accepts_already_approved() -> None:
    """API may update approval to 'approved' before workflow reads it (race)."""
    pool = FakePool(fetchrow_result={
        "status": "approved",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "abc123")
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_validate_approval_rejects_already_rejected() -> None:
    pool = FakePool(fetchrow_result={
        "status": "rejected",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
        "changeset_digest": "abc123",
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import validate_approval
        result = await validate_approval(str(uuid.uuid4()), "abc123")
    assert result["valid"] is False
    assert "rejected" in result["reason"]


@pytest.mark.asyncio
async def test_revalidate_binding_accepts_valid() -> None:
    pool = FakePool(fetchrow_result={
        "status": "valid",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import revalidate_binding
        result = await revalidate_binding(str(uuid.uuid4()))
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_revalidate_binding_accepts_expiring() -> None:
    pool = FakePool(fetchrow_result={
        "status": "expiring",
        "expires_at": datetime.now(UTC) + timedelta(minutes=10),
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import revalidate_binding
        result = await revalidate_binding(str(uuid.uuid4()))
    assert result["valid"] is True


@pytest.mark.asyncio
async def test_revalidate_binding_rejects_expired() -> None:
    pool = FakePool(fetchrow_result={
        "status": "valid",
        "expires_at": datetime.now(UTC) - timedelta(hours=1),
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import revalidate_binding
        result = await revalidate_binding(str(uuid.uuid4()))
    assert result["valid"] is False
    assert "expired" in result["reason"]


@pytest.mark.asyncio
async def test_revalidate_binding_rejects_revoked() -> None:
    pool = FakePool(fetchrow_result={
        "status": "revoked",
        "expires_at": datetime.now(UTC) + timedelta(hours=1),
    })
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import revalidate_binding
        result = await revalidate_binding(str(uuid.uuid4()))
    assert result["valid"] is False
    assert "revoked" in result["reason"]


@pytest.mark.asyncio
async def test_revalidate_binding_rejects_not_found() -> None:
    pool = FakePool(fetchrow_result=None)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import revalidate_binding
        result = await revalidate_binding(str(uuid.uuid4()))
    assert result["valid"] is False
    assert "not found" in result["reason"]
