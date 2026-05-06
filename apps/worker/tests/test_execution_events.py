"""Tests for execution event emission and status projection."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from pinky_worker.execution.activities import ExecutionEventPayload


class FakePool:
    def __init__(self, fetchrow_result=None):
        self.executed: list[tuple] = []
        self._fetchrow_result = fetchrow_result

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        return self._fetchrow_result


@pytest.mark.asyncio
async def test_emit_resolves_uuid_from_investigation_prefix():
    exec_id = uuid.uuid4()
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=f"investigation-{exec_id}",
            event_type="started", sequence=0, payload={},
        ))

    insert_calls = [c for c in pool.executed if "INSERT INTO execution_events" in c[0]]
    assert len(insert_calls) == 1
    assert insert_calls[0][1][1] == exec_id

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0]]
    assert len(status_calls) == 1
    assert "running" in status_calls[0][0]


@pytest.mark.asyncio
async def test_emit_updates_status_on_completed():
    exec_id = uuid.uuid4()
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=str(exec_id),
            event_type="completed", sequence=1, payload={},
        ))

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0]]
    assert len(status_calls) == 1
    assert "completed" in status_calls[0][0]


@pytest.mark.asyncio
async def test_emit_updates_status_on_failed():
    exec_id = uuid.uuid4()
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=str(exec_id),
            event_type="failed", sequence=1, payload={"error": "timeout"},
        ))

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0]]
    assert len(status_calls) == 1
    assert "failed" in status_calls[0][0]


@pytest.mark.asyncio
async def test_emit_no_status_update_for_progress():
    exec_id = uuid.uuid4()
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=str(exec_id),
            event_type="progress", sequence=1, payload={},
        ))

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0]]
    assert len(status_calls) == 0


@pytest.mark.asyncio
async def test_emit_raises_on_unparseable_workflow_id():
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        with pytest.raises(ValueError):
            await emit_execution_event(ExecutionEventPayload(
                execution_id="investigation-980c491b-f2162ce7e9cb",
                event_type="started", sequence=0, payload={},
            ))
