"""Dead-end test matrix — every state has a tested exit path.

Verifies no task or execution can get permanently stuck without
a user-recoverable action.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pinky_worker.transitions import (
    EXEC_TERMINAL,
    transition_execution,
    transition_work_item,
)


def _make_pool(row: dict | None) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=row)
    pool.execute = AsyncMock()

    class AcquireCM:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, *args):
            pass

    pool.acquire = AcquireCM
    return pool


class TestExecutionNoDeadEnds:
    @pytest.mark.asyncio
    async def test_pending_can_reach_running(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "running")

    @pytest.mark.asyncio
    async def test_pending_can_reach_failed(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "failed")

    @pytest.mark.asyncio
    async def test_pending_can_reach_cancelled(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "cancelled")

    @pytest.mark.asyncio
    async def test_running_can_reach_completed(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "completed")

    @pytest.mark.asyncio
    async def test_running_can_reach_failed(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "failed")

    @pytest.mark.asyncio
    async def test_running_can_reach_waiting_for_approval(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "waiting_for_approval")

    @pytest.mark.asyncio
    async def test_waiting_approval_can_reach_running(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "running")

    @pytest.mark.asyncio
    async def test_waiting_approval_can_reach_failed(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "failed")

    @pytest.mark.asyncio
    async def test_waiting_approval_can_reach_timed_out(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "timed_out")

    @pytest.mark.asyncio
    async def test_terminal_states_are_final(self) -> None:
        for terminal in EXEC_TERMINAL:
            pool = _make_pool({"status": terminal, "execution_type": "investigation",
                               "work_item_id": None, "cluster_id": uuid4()})
            assert not await transition_execution(pool, uuid4(), "running")


class TestWorkItemNoDeadEnds:
    @pytest.mark.asyncio
    async def test_ready_can_start(self) -> None:
        pool = _make_pool({"status": "ready", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "in_progress")

    @pytest.mark.asyncio
    async def test_in_progress_can_complete(self) -> None:
        pool = _make_pool({"status": "in_progress", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "done")

    @pytest.mark.asyncio
    async def test_in_progress_can_reset(self) -> None:
        pool = _make_pool({"status": "in_progress", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready")

    @pytest.mark.asyncio
    async def test_in_progress_can_block(self) -> None:
        pool = _make_pool({"status": "in_progress", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "blocked")

    @pytest.mark.asyncio
    async def test_blocked_can_unblock(self) -> None:
        pool = _make_pool({"status": "blocked", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "in_progress")

    @pytest.mark.asyncio
    async def test_blocked_can_reset(self) -> None:
        pool = _make_pool({"status": "blocked", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready")

    @pytest.mark.asyncio
    async def test_waiting_approval_can_reset(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready")

    @pytest.mark.asyncio
    async def test_waiting_approval_can_complete(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "done")

    @pytest.mark.asyncio
    async def test_done_can_reopen(self) -> None:
        pool = _make_pool({"status": "done", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready")


class TestCrossEntityCascades:
    @pytest.mark.asyncio
    async def test_exec_failure_resets_work_item(self) -> None:
        wi_id = uuid4()
        call_count = 0

        async def fetchrow(query, *args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "running", "execution_type": "remediation",
                        "work_item_id": wi_id, "cluster_id": uuid4()}
            return {"status": "in_progress", "cluster_id": uuid4()}

        pool = _make_pool(None)
        pool.fetchrow = fetchrow
        await transition_execution(pool, uuid4(), "failed")
        wi_updates = [c for c in pool.execute.call_args_list if "work_items" in str(c)]
        assert len(wi_updates) > 0

    @pytest.mark.asyncio
    async def test_exec_timeout_resets_work_item(self) -> None:
        wi_id = uuid4()
        call_count = 0

        async def fetchrow(query, *args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "waiting_for_approval", "execution_type": "remediation",
                        "work_item_id": wi_id, "cluster_id": uuid4()}
            return {"status": "waiting_for_approval", "cluster_id": uuid4()}

        pool = _make_pool(None)
        pool.fetchrow = fetchrow
        await transition_execution(pool, uuid4(), "timed_out")
        wi_updates = [c for c in pool.execute.call_args_list if "work_items" in str(c)]
        assert len(wi_updates) > 0

    @pytest.mark.asyncio
    async def test_exec_cancel_resets_work_item(self) -> None:
        wi_id = uuid4()
        call_count = 0

        async def fetchrow(query, *args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "pending", "execution_type": "investigation",
                        "work_item_id": wi_id, "cluster_id": uuid4()}
            return {"status": "in_progress", "cluster_id": uuid4()}

        pool = _make_pool(None)
        pool.fetchrow = fetchrow
        await transition_execution(pool, uuid4(), "cancelled")
        wi_updates = [c for c in pool.execute.call_args_list if "work_items" in str(c)]
        assert len(wi_updates) > 0

    @pytest.mark.asyncio
    async def test_terminal_exec_invalidates_approval(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        await transition_execution(pool, uuid4(), "failed")
        approval_calls = [c for c in pool.execute.call_args_list if "approvals" in str(c)]
        assert len(approval_calls) == 1

    @pytest.mark.asyncio
    async def test_completed_does_not_reset_work_item(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "investigation",
                           "work_item_id": uuid4(), "cluster_id": uuid4()})
        await transition_execution(pool, uuid4(), "completed")
        wi_updates = [c for c in pool.execute.call_args_list if "work_items" in str(c)]
        assert len(wi_updates) == 0
