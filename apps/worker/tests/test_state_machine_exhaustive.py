"""Exhaustive state machine tests for execution and work item transitions.

Validates graph properties (reachability, termination, completeness) and
parametrizes over ALL (from, to) pairs to ensure every transition either
succeeds or returns False — no silent failures, no dead-end states.
"""

from __future__ import annotations

from collections import deque
from itertools import product
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from pinky_worker.execution.state_machine import (
    TERMINAL_STATUSES as SM_TERMINAL_STATUSES,
    VALID_EXECUTION_TRANSITIONS,
    InvalidTransitionError,
    validate_transition,
)
from pinky_worker.transitions import (
    EXEC_TERMINAL,
    EXEC_TRANSITIONS,
    WI_TRANSITIONS,
    transition_execution,
    transition_work_item,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# All execution statuses — union of keys and all targets
ALL_EXEC_STATUSES: frozenset[str] = frozenset(
    set(EXEC_TRANSITIONS.keys())
    | EXEC_TERMINAL
    | {t for targets in EXEC_TRANSITIONS.values() for t in targets}
)

# All work item statuses — union of keys and all targets
ALL_WI_STATUSES: frozenset[str] = frozenset(
    set(WI_TRANSITIONS.keys())
    | {t for targets in WI_TRANSITIONS.values() for t in targets}
)

# Work items have no truly terminal states ("done" can go back to "ready"),
# but we can identify states with no outgoing edges for graph analysis.
WI_SINK_STATUSES: frozenset[str] = frozenset(
    s for s in ALL_WI_STATUSES if not WI_TRANSITIONS.get(s, set())
)


def _reachable(start: str, transitions: dict[str, set[str]]) -> set[str]:
    """BFS from *start* over the transition graph. Returns reachable set."""
    visited: set[str] = set()
    queue = deque([start])
    while queue:
        state = queue.popleft()
        if state in visited:
            continue
        visited.add(state)
        for target in transitions.get(state, set()):
            if target not in visited:
                queue.append(target)
    return visited


def _has_path_to_any(start: str, targets: frozenset[str], transitions: dict[str, set[str]]) -> bool:
    """Return True if there is a path from *start* to any state in *targets*."""
    return bool(_reachable(start, transitions) & targets)


def _make_pool(row: dict | None = None) -> AsyncMock:
    """Build an AsyncMock pool that returns *row* from fetchrow."""
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


# ---------------------------------------------------------------------------
# Execution state machine — graph properties
# ---------------------------------------------------------------------------

class TestExecGraphCompleteness:
    """Structural invariants of the execution transition graph."""

    def test_every_non_terminal_has_outgoing_edges(self) -> None:
        for status in ALL_EXEC_STATUSES - EXEC_TERMINAL:
            edges = EXEC_TRANSITIONS.get(status, set())
            assert edges, f"non-terminal {status!r} has no outgoing transitions"

    def test_terminal_states_not_in_transition_keys(self) -> None:
        for status in EXEC_TERMINAL:
            assert status not in EXEC_TRANSITIONS, (
                f"terminal {status!r} should not appear as a key in EXEC_TRANSITIONS"
            )

    def test_terminal_set_is_explicit(self) -> None:
        assert EXEC_TERMINAL == {"completed", "failed", "cancelled", "timed_out"}

    def test_all_targets_are_known_statuses(self) -> None:
        for src, targets in EXEC_TRANSITIONS.items():
            for tgt in targets:
                assert tgt in ALL_EXEC_STATUSES, f"{src} -> {tgt}: unknown target status"


class TestExecReachability:
    """Every status is reachable from 'pending' (the initial state)."""

    def test_all_statuses_reachable_from_pending(self) -> None:
        reachable = _reachable("pending", EXEC_TRANSITIONS)
        for status in ALL_EXEC_STATUSES:
            assert status in reachable, f"{status!r} is unreachable from 'pending'"


class TestExecTermination:
    """Every non-terminal status has a path to at least one terminal status."""

    @pytest.mark.parametrize("status", sorted(ALL_EXEC_STATUSES - EXEC_TERMINAL))
    def test_path_to_terminal(self, status: str) -> None:
        assert _has_path_to_any(status, EXEC_TERMINAL, EXEC_TRANSITIONS), (
            f"{status!r} has no path to any terminal state"
        )


class TestExecTransitionExhaustive:
    """Parametrize over ALL (from, to) pairs for transition_execution."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        sorted(product(ALL_EXEC_STATUSES, ALL_EXEC_STATUSES)),
        ids=lambda p: f"{p}" if isinstance(p, str) else None,
    )
    @pytest.mark.asyncio
    async def test_every_pair(self, from_status: str, to_status: str) -> None:
        pool = _make_pool({
            "status": from_status,
            "execution_type": "investigation",
            "work_item_id": None,
            "cluster_id": uuid4(),
        })

        result = await transition_execution(pool, uuid4(), to_status)

        # Must be bool — never None or other
        assert isinstance(result, bool)

        if from_status == to_status:
            # Idempotent: same status always returns True
            assert result is True
        elif from_status in EXEC_TERMINAL:
            # Terminal states block all transitions
            assert result is False
        elif to_status in EXEC_TRANSITIONS.get(from_status, set()):
            assert result is True
        else:
            assert result is False


# ---------------------------------------------------------------------------
# Work item state machine — graph properties
# ---------------------------------------------------------------------------

class TestWIGraphCompleteness:
    """Structural invariants of the work item transition graph."""

    def test_every_status_has_outgoing_edges(self) -> None:
        for status in ALL_WI_STATUSES:
            edges = WI_TRANSITIONS.get(status, set())
            assert edges, f"work_item status {status!r} has no outgoing transitions"

    def test_all_targets_are_known_statuses(self) -> None:
        for src, targets in WI_TRANSITIONS.items():
            for tgt in targets:
                assert tgt in ALL_WI_STATUSES, f"{src} -> {tgt}: unknown target status"

    def test_no_orphan_statuses(self) -> None:
        """Every status appears as either a key or a target (not dangling)."""
        keys = set(WI_TRANSITIONS.keys())
        targets = {t for ts in WI_TRANSITIONS.values() for t in ts}
        assert keys == targets, f"key/target mismatch: keys_only={keys - targets}, targets_only={targets - keys}"


class TestWIReachability:
    """Every status is reachable from 'ready' (the initial state)."""

    def test_all_statuses_reachable_from_ready(self) -> None:
        reachable = _reachable("ready", WI_TRANSITIONS)
        for status in ALL_WI_STATUSES:
            assert status in reachable, f"{status!r} is unreachable from 'ready'"


class TestWICycles:
    """Work item graph is cyclic (done -> ready), verify the cycle exists."""

    def test_done_to_ready_cycle(self) -> None:
        assert "ready" in WI_TRANSITIONS.get("done", set())

    def test_ready_reachable_from_done(self) -> None:
        reachable = _reachable("done", WI_TRANSITIONS)
        assert "ready" in reachable


class TestWITransitionExhaustive:
    """Parametrize over ALL (from, to) pairs for transition_work_item."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        sorted(product(ALL_WI_STATUSES, ALL_WI_STATUSES)),
        ids=lambda p: f"{p}" if isinstance(p, str) else None,
    )
    @pytest.mark.asyncio
    async def test_every_pair(self, from_status: str, to_status: str) -> None:
        pool = _make_pool({
            "status": from_status,
            "cluster_id": uuid4(),
        })

        result = await transition_work_item(pool, uuid4(), to_status)

        assert isinstance(result, bool)

        if from_status == to_status:
            assert result is True
        elif to_status in WI_TRANSITIONS.get(from_status, set()):
            assert result is True
        else:
            assert result is False


# ---------------------------------------------------------------------------
# Transition dict consistency — two dicts must agree
# ---------------------------------------------------------------------------

class TestDictConsistency:
    """EXEC_TRANSITIONS (transitions.py) and VALID_EXECUTION_TRANSITIONS
    (execution/state_machine.py) must encode the same state machine."""

    def test_non_terminal_edges_match(self) -> None:
        for status, targets in EXEC_TRANSITIONS.items():
            sm_targets = VALID_EXECUTION_TRANSITIONS.get(status, set())
            assert targets == sm_targets, (
                f"edge mismatch for {status!r}: transitions.py={targets}, "
                f"state_machine.py={sm_targets}"
            )

    def test_terminal_states_match(self) -> None:
        assert EXEC_TERMINAL == SM_TERMINAL_STATUSES

    def test_terminal_states_have_empty_edges_in_state_machine(self) -> None:
        for status in EXEC_TERMINAL:
            assert VALID_EXECUTION_TRANSITIONS.get(status) == set(), (
                f"terminal {status!r} should have empty edge set in state_machine.py"
            )

    def test_full_status_sets_match(self) -> None:
        """Both dicts define the same universe of statuses."""
        from_transitions = set(EXEC_TRANSITIONS.keys()) | EXEC_TERMINAL
        from_state_machine = set(VALID_EXECUTION_TRANSITIONS.keys())
        assert from_transitions == from_state_machine, (
            f"status set mismatch: "
            f"only_transitions={from_transitions - from_state_machine}, "
            f"only_state_machine={from_state_machine - from_transitions}"
        )


class TestValidateTransitionExhaustive:
    """Parametrize validate_transition (raises-based API) over all pairs."""

    @pytest.mark.parametrize(
        "from_status,to_status",
        sorted(product(
            set(VALID_EXECUTION_TRANSITIONS.keys()),
            set(VALID_EXECUTION_TRANSITIONS.keys()),
        )),
        ids=lambda p: f"{p}" if isinstance(p, str) else None,
    )
    def test_every_pair(self, from_status: str, to_status: str) -> None:
        allowed = VALID_EXECUTION_TRANSITIONS.get(from_status, set())
        if to_status in allowed:
            validate_transition(from_status, to_status)  # should not raise
        else:
            with pytest.raises(InvalidTransitionError) as exc_info:
                validate_transition(from_status, to_status)
            assert exc_info.value.current == from_status
            assert exc_info.value.target == to_status
