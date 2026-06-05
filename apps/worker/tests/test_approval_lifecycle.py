"""Tests for approval lifecycle — invalidation timing."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest


class FakePool:
    def __init__(self, fetchrow_result=None):
        self.executed: list[tuple] = []
        self._fetchrow_result = fetchrow_result or {}

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        return self._fetchrow_result

    def acquire(self):
        return _FakeAcquire(self)


class _FakeAcquire:
    def __init__(self, pool):
        self._pool = pool

    async def __aenter__(self):
        return self._pool

    async def __aexit__(self, *args):
        pass


@pytest.mark.asyncio
async def test_investigation_completion_does_not_invalidate_approvals():
    """Investigation reaching terminal status should NOT invalidate pending approvals."""
    exec_id = uuid4()
    pool = FakePool(fetchrow_result={
        "status": "running",
        "execution_type": "investigation",
        "work_item_id": None,
        "cluster_id": uuid4(),
    })

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "pinky_worker.db.get_pool", AsyncMock(return_value=pool),
    ):
        from pinky_worker.transitions import transition_execution
        await transition_execution(pool, exec_id, "completed")

    invalidation_calls = [
        c for c in pool.executed
        if "UPDATE approvals" in c[0] and "invalidated" in c[0]
    ]
    assert len(invalidation_calls) == 0, "Investigation completion should not invalidate approvals"


@pytest.mark.asyncio
async def test_remediation_completion_invalidates_approvals():
    """Remediation reaching terminal status SHOULD invalidate pending approvals."""
    exec_id = uuid4()
    pool = FakePool(fetchrow_result={
        "status": "running",
        "execution_type": "remediation",
        "work_item_id": None,
        "cluster_id": uuid4(),
    })

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "pinky_worker.db.get_pool", AsyncMock(return_value=pool),
    ):
        from pinky_worker.transitions import transition_execution
        await transition_execution(pool, exec_id, "completed")

    invalidation_calls = [
        c for c in pool.executed
        if "UPDATE approvals" in c[0] and "invalidated" in c[0]
    ]
    assert len(invalidation_calls) == 1, "Remediation completion should invalidate pending approvals"


@pytest.mark.asyncio
async def test_remediation_failure_invalidates_approvals():
    """Remediation failure SHOULD also invalidate pending approvals."""
    exec_id = uuid4()
    pool = FakePool(fetchrow_result={
        "status": "running",
        "execution_type": "remediation",
        "work_item_id": None,
        "cluster_id": uuid4(),
    })

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "pinky_worker.db.get_pool", AsyncMock(return_value=pool),
    ):
        from pinky_worker.transitions import transition_execution
        await transition_execution(pool, exec_id, "failed")

    invalidation_calls = [
        c for c in pool.executed
        if "UPDATE approvals" in c[0] and "invalidated" in c[0]
    ]
    assert len(invalidation_calls) == 1, "Remediation failure should invalidate pending approvals"


@pytest.mark.asyncio
async def test_non_terminal_status_does_not_invalidate():
    """Non-terminal statuses (running, waiting) should not touch approvals."""
    exec_id = uuid4()
    pool = FakePool(fetchrow_result={
        "status": "pending",
        "execution_type": "remediation",
        "work_item_id": None,
        "cluster_id": uuid4(),
    })

    with __import__("unittest.mock", fromlist=["patch"]).patch(
        "pinky_worker.db.get_pool", AsyncMock(return_value=pool),
    ):
        from pinky_worker.transitions import transition_execution
        await transition_execution(pool, exec_id, "running")

    invalidation_calls = [
        c for c in pool.executed
        if "UPDATE approvals" in c[0] and "invalidated" in c[0]
    ]
    assert len(invalidation_calls) == 0
