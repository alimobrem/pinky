"""Tests for centralized transition functions."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from pinky_worker.transitions import (
    EXEC_TERMINAL,
    EXEC_TRANSITIONS,
    WI_TRANSITIONS,
    transition_execution,
    transition_work_item,
)


def _make_pool(row: dict | None = None) -> AsyncMock:
    pool = AsyncMock()
    pool.fetchrow = AsyncMock(return_value=row)
    pool.execute = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()

    class AcquireCM:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *args):
            pass

    pool.acquire = AcquireCM
    return pool


class TestTransitionExecution:
    @pytest.mark.asyncio
    async def test_valid_transition(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "running") is True

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_false(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "completed") is False

    @pytest.mark.asyncio
    async def test_idempotent_same_status(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, uuid4(), "running") is True
        pool.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_terminal_status_blocks_further_transitions(self) -> None:
        for terminal in EXEC_TERMINAL:
            pool = _make_pool({"status": terminal, "execution_type": "investigation",
                               "work_item_id": None, "cluster_id": uuid4()})
            assert await transition_execution(pool, uuid4(), "running") is False

    @pytest.mark.asyncio
    async def test_not_found_returns_false(self) -> None:
        pool = _make_pool(None)
        assert await transition_execution(pool, uuid4(), "running") is False

    @pytest.mark.asyncio
    async def test_terminal_sets_completed_at(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        await transition_execution(pool, uuid4(), "failed")
        sql = pool.execute.call_args_list[0][0][0]
        assert "completed_at" in sql

    @pytest.mark.asyncio
    async def test_running_sets_started_at(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        await transition_execution(pool, uuid4(), "running")
        sql = pool.execute.call_args_list[0][0][0]
        assert "started_at" in sql

    @pytest.mark.asyncio
    async def test_failure_cascades_to_work_item_ready(self) -> None:
        wi_id = uuid4()
        pool = _make_pool({"status": "running", "execution_type": "remediation",
                           "work_item_id": wi_id, "cluster_id": uuid4()})

        wi_row = {"status": "in_progress", "cluster_id": uuid4()}
        call_count = 0
        original = pool.fetchrow

        async def multi_fetchrow(query, *args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"status": "running", "execution_type": "remediation",
                        "work_item_id": wi_id, "cluster_id": uuid4()}
            return wi_row

        pool.fetchrow = multi_fetchrow
        await transition_execution(pool, uuid4(), "failed")
        wi_update_calls = [c for c in pool.execute.call_args_list if "work_items" in str(c)]
        assert len(wi_update_calls) > 0

    @pytest.mark.asyncio
    async def test_terminal_invalidates_pending_approvals(self) -> None:
        pool = _make_pool({"status": "running", "execution_type": "remediation",
                           "work_item_id": None, "cluster_id": uuid4()})
        await transition_execution(pool, uuid4(), "failed")
        approval_calls = [c for c in pool.execute.call_args_list if "approvals" in str(c)]
        assert len(approval_calls) == 1
        assert "invalidated" in str(approval_calls[0])

    @pytest.mark.asyncio
    async def test_accepts_string_id(self) -> None:
        pool = _make_pool({"status": "pending", "execution_type": "investigation",
                           "work_item_id": None, "cluster_id": uuid4()})
        assert await transition_execution(pool, str(uuid4()), "running") is True


class TestTransitionWorkItem:
    @pytest.mark.asyncio
    async def test_valid_transition(self) -> None:
        pool = _make_pool({"status": "ready", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "in_progress") is True

    @pytest.mark.asyncio
    async def test_invalid_transition_returns_false(self) -> None:
        pool = _make_pool({"status": "ready", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "done") is False

    @pytest.mark.asyncio
    async def test_idempotent_same_status(self) -> None:
        pool = _make_pool({"status": "ready", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready") is True
        pool.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_found_returns_false(self) -> None:
        pool = _make_pool(None)
        assert await transition_work_item(pool, uuid4(), "in_progress") is False

    @pytest.mark.asyncio
    async def test_done_to_ready_allowed(self) -> None:
        pool = _make_pool({"status": "done", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready") is True

    @pytest.mark.asyncio
    async def test_done_to_in_progress_blocked(self) -> None:
        pool = _make_pool({"status": "done", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "in_progress") is False

    @pytest.mark.asyncio
    async def test_waiting_for_approval_to_ready(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "ready") is True

    @pytest.mark.asyncio
    async def test_waiting_for_approval_to_done(self) -> None:
        pool = _make_pool({"status": "waiting_for_approval", "cluster_id": uuid4()})
        assert await transition_work_item(pool, uuid4(), "done") is True


class TestStateCompleteness:
    """Every state in the transition maps must have at least one outbound edge."""

    def test_every_exec_state_has_exit(self) -> None:
        all_states = set(EXEC_TRANSITIONS.keys()) | EXEC_TERMINAL
        for state in all_states:
            if state in EXEC_TERMINAL:
                continue
            exits = EXEC_TRANSITIONS.get(state, set())
            assert len(exits) > 0, f"execution state {state!r} has no exits — dead end"

    def test_every_wi_state_has_exit(self) -> None:
        for state, exits in WI_TRANSITIONS.items():
            assert len(exits) > 0, f"work_item state {state!r} has no exits — dead end"

    def test_exec_terminal_states_have_no_outbound(self) -> None:
        for state in EXEC_TERMINAL:
            assert state not in EXEC_TRANSITIONS, f"terminal state {state!r} has outbound transitions"

    def test_all_exec_targets_are_defined(self) -> None:
        all_states = set(EXEC_TRANSITIONS.keys()) | EXEC_TERMINAL
        for state, targets in EXEC_TRANSITIONS.items():
            for target in targets:
                assert target in all_states, f"{state} → {target}: target not in state set"

    def test_all_wi_targets_are_defined(self) -> None:
        all_states = set(WI_TRANSITIONS.keys())
        for state, targets in WI_TRANSITIONS.items():
            for target in targets:
                assert target in all_states, f"{state} → {target}: target not in state set"
