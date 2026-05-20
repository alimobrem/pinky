"""Tests for execution event emission and status projection."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from pinky_worker.execution.activities import ExecutionEventPayload


class FakePool:
    def __init__(self, fetchrow_result=None):
        self.executed: list[tuple] = []
        self._fetchrow_result = fetchrow_result or {
            "status": "pending",
            "execution_type": "investigation",
            "work_item_id": None,
            "cluster_id": uuid.uuid4(),
        }
        self._call_count = 0

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        self._call_count += 1
        if "SELECT status" in query and "executions" in query:
            row = dict(self._fetchrow_result)
            if self._call_count > 2:
                for prev in self.executed:
                    if "UPDATE executions" in prev[0] and "running" in prev[0]:
                        row["status"] = "running"
                    elif "UPDATE executions" in prev[0] and "completed" in prev[0]:
                        row["status"] = "completed"
                    elif "UPDATE executions" in prev[0] and "failed" in prev[0]:
                        row["status"] = "failed"
            return row
        return self._fetchrow_result

    @asynccontextmanager
    async def acquire(self):
        yield AsyncMock()


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
    assert len(status_calls) >= 1


@pytest.mark.asyncio
async def test_emit_updates_status_on_completed():
    exec_id = uuid.uuid4()
    pool = FakePool({"status": "running", "execution_type": "investigation",
                     "work_item_id": None, "cluster_id": uuid.uuid4()})

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=str(exec_id),
            event_type="completed", sequence=1, payload={},
        ))

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0] and "completed_at" in c[0]]
    assert len(status_calls) >= 1


@pytest.mark.asyncio
async def test_emit_updates_status_on_failed():
    exec_id = uuid.uuid4()
    pool = FakePool({"status": "running", "execution_type": "investigation",
                     "work_item_id": None, "cluster_id": uuid.uuid4()})

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=str(exec_id),
            event_type="failed", sequence=1, payload={"error": "timeout"},
        ))

    status_calls = [c for c in pool.executed if "UPDATE executions" in c[0] and "completed_at" in c[0]]
    assert len(status_calls) >= 1


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
