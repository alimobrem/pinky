"""Tests for analytics event emission on investigation/remediation outcomes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest


class FakePool:
    def __init__(self):
        self.execute_calls: list[tuple] = []
        self.should_raise = False

    async def execute(self, query, *args):
        self.execute_calls.append((query, *args))
        if self.should_raise:
            raise RuntimeError("DB connection lost")


@pytest.mark.asyncio
async def test_emit_analytics_event_inserts_row():
    """Verify _emit_analytics_event inserts into analytics_events with correct payload."""
    from pinky_worker.execution.activities import _emit_analytics_event

    fake_pool = FakePool()
    execution_id = str(uuid4())
    cluster_id = str(uuid4())
    payload = {
        "artifact_id": "test-artifact",
        "issue_id": "test-issue",
        "confidence": 0.85,
        "evidence_hash": "abc123",
        "cached": False,
    }

    await _emit_analytics_event(
        fake_pool,
        "investigation_completed",
        payload,
        cluster_id=cluster_id,
        execution_id=execution_id,
    )

    assert len(fake_pool.execute_calls) == 1
    call = fake_pool.execute_calls[0]
    query = call[0]
    args = call[1:]

    assert "INSERT INTO analytics_events" in query
    # args: (uuid, event_type, execution_id, cluster_id, payload_json, occurred_at)
    assert isinstance(args[0], UUID)  # id
    assert args[1] == "investigation_completed"
    assert args[2] == UUID(execution_id)
    assert args[3] == UUID(cluster_id)
    assert json.loads(args[4]) == payload
    assert isinstance(args[5], datetime)


@pytest.mark.asyncio
async def test_emit_analytics_event_handles_failure():
    """Verify _emit_analytics_event doesn't raise on DB error (logs warning instead)."""
    from pinky_worker.execution.activities import _emit_analytics_event

    fake_pool = FakePool()
    fake_pool.should_raise = True

    # Should not raise
    await _emit_analytics_event(
        fake_pool,
        "investigation_completed",
        {"test": "data"},
        execution_id=str(uuid4()),
    )

    # Verify it attempted the insert
    assert len(fake_pool.execute_calls) == 1
