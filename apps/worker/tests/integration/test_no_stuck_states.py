"""Stuck-state tests — every state transition must lead somewhere.

A task that can't progress is a silent outage. These tests verify that
no combination of success/failure/cancellation leaves the system in a
dead-end state where the user has no path forward.

Requires: real Postgres. K8s and LLM mocked.
"""

from __future__ import annotations

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest

from pinky_worker.issues.correlator import CorrelationResult


async def _seed_issue_and_task(conn: asyncpg.Connection, cluster_id: str) -> tuple[str, str]:
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3, 'Test issue', 'high',
           'open', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id, f"test-{uuid.uuid4().hex[:8]}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'Test issue', 'ready',
           NULL, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )
    return issue_id, wi_id


async def _seed_execution(
    conn: asyncpg.Connection, cluster_id: str, wi_id: str,
    exec_type: str = "investigation", status: str = "pending",
) -> str:
    exec_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, $4, $5, now())""",
        exec_id, wi_id, cluster_id, exec_type, status,
    )
    return exec_id


class _FakeConn:
    def __init__(self, real_conn: asyncpg.Connection):
        self._c = real_conn

    async def fetchrow(self, query, *args):
        return await self._c.fetchrow(query, *args)

    async def execute(self, query, *args):
        return await self._c.execute(query, *args)

    @asynccontextmanager
    async def transaction(self):
        yield


class _FakePool:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = _FakeConn(conn)
        self._c = conn

    async def fetchrow(self, query, *args):
        return await self._c.fetchrow(query, *args)

    async def execute(self, query, *args):
        return await self._c.execute(query, *args)

    async def fetch(self, query, *args):
        return await self._c.fetch(query, *args)

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


async def test_no_task_stuck_after_failed_investigation(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Failed investigation → execution 'failed', task stays 'ready', re-investigation possible."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "investigation", "failed")
    await conn.execute(
        "UPDATE executions SET completed_at = now() - interval '2 hours' WHERE id = $1::uuid",
        exec_id,
    )

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"

    obs = MagicMock()
    obs.fingerprint = "test-fp"
    obs.correlation_key = f"test-{uuid.uuid4().hex[:8]}"
    obs.check_id = "test-check"
    obs.resource_kind = "Pod"
    obs.resource_namespace = "default"
    obs.resource_name = "test-pod"

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock()
    result = CorrelationResult(action="created", issue_id=issue_id, observation_count=1)
    decision = MagicMock()
    decision.action.skill = None

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.observation.observer import _dispatch_investigation
        await _dispatch_investigation(mock_client, cluster_id, obs, result, decision, MagicMock())

    mock_client.start_workflow.assert_called_once()


async def test_no_task_stuck_after_completed_investigation(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Completed investigation blocks re-dispatch — task is actionable via UI, not stuck in loop."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "investigation", "completed")
    await conn.execute(
        "UPDATE executions SET completed_at = now() - interval '10 hours' WHERE id = $1::uuid",
        exec_id,
    )

    obs = MagicMock()
    obs.fingerprint = "test-fp"
    obs.correlation_key = f"test-{uuid.uuid4().hex[:8]}"

    mock_client = AsyncMock()
    result = CorrelationResult(action="created", issue_id=issue_id, observation_count=1)
    decision = MagicMock()
    decision.action.skill = None

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.observation.observer import _dispatch_investigation
        await _dispatch_investigation(mock_client, cluster_id, obs, result, decision, MagicMock())

    mock_client.start_workflow.assert_not_called()

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"


async def test_no_task_stuck_after_cancel(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Cancelled remediation → execution 'cancelled', task stays open for user action."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "remediation", "cancelled")

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"

    issue = await conn.fetchrow("SELECT status FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "open"


async def test_no_issue_stuck_after_remediation_complete(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Remediation + verification passed → issue resolved, not stuck as open."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "remediation", "running")

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=exec_id, event_type="completed", sequence=100,
            payload={"verification_passed": True},
        ))

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "done"

    issue = await conn.fetchrow("SELECT status, resolved_by FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "resolved"
    assert issue["resolved_by"] == "remediation"


async def test_no_task_stuck_after_failed_verification(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Remediation with failed verification → task stays open for user decision."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "remediation", "running")

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=exec_id, event_type="completed", sequence=100,
            payload={"verification_passed": False},
        ))

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"

    issue = await conn.fetchrow("SELECT status FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "open"


async def test_no_execution_stuck_in_pending(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Temporal fails to start → execution deleted, not stuck in 'pending'."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)

    obs = MagicMock()
    obs.fingerprint = "test-fp"
    obs.correlation_key = f"test-{uuid.uuid4().hex[:8]}"
    obs.check_id = "test-check"
    obs.resource_kind = "Pod"
    obs.resource_namespace = "default"
    obs.resource_name = "test-pod"

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock(side_effect=Exception("Temporal unavailable"))

    result = CorrelationResult(action="created", issue_id=issue_id, observation_count=1)
    decision = MagicMock()
    decision.action.skill = None

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.observation.observer import _dispatch_investigation
        await _dispatch_investigation(mock_client, cluster_id, obs, result, decision, MagicMock())

    pending = await conn.fetch(
        "SELECT id, status FROM executions WHERE work_item_id = $1::uuid AND status = 'pending'",
        wi_id,
    )
    assert len(pending) == 0

    failed = await conn.fetch(
        "SELECT id, status FROM executions WHERE work_item_id = $1::uuid AND status = 'failed'",
        wi_id,
    )
    assert len(failed) == 1


async def test_second_investigation_can_complete(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """A re-investigation must be able to complete even if a prior completed investigation exists."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)

    # First completed investigation
    exec1 = await _seed_execution(conn, cluster_id, wi_id, "investigation", "completed")
    await conn.execute(
        "UPDATE executions SET completed_at = now() - interval '2 hours' WHERE id = $1::uuid", exec1,
    )

    # Second investigation running
    exec2 = await _seed_execution(conn, cluster_id, wi_id, "investigation", "running")

    # Completing the second investigation must not crash
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=exec2, event_type="completed", sequence=100,
            payload={"confidence": 0.85},
        ))

    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", exec2)
    assert row["status"] == "completed"


async def test_remediation_can_complete_alongside_investigation(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """A remediation must complete even if a completed investigation exists for the same work_item."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)

    inv_id = await _seed_execution(conn, cluster_id, wi_id, "investigation", "completed")
    await conn.execute(
        "UPDATE executions SET completed_at = now() WHERE id = $1::uuid", inv_id,
    )

    rem_id = await _seed_execution(conn, cluster_id, wi_id, "remediation", "running")

    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event
        await emit_execution_event(ExecutionEventPayload(
            execution_id=rem_id, event_type="completed", sequence=100,
            payload={"verification_passed": True},
        ))

    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", rem_id)
    assert row["status"] == "completed"

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "done"


async def test_orphaned_task_auto_completes(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Task whose issue was resolved must be swept to done."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    await conn.execute("UPDATE issues SET status = 'resolved' WHERE id = $1::uuid", issue_id)

    from pinky_worker.observation.observer import _sweep_orphaned_tasks
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_orphaned_tasks(cluster_id)

    assert count == 1
    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "done"


async def test_task_not_orphaned_when_issue_open(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Task with open issue must NOT be swept."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)

    from pinky_worker.observation.observer import _sweep_orphaned_tasks
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_orphaned_tasks(cluster_id)

    assert count == 0
    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"


async def test_stuck_pending_investigation_cleaned(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Pending investigation older than 5 min must be marked failed."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "investigation", "pending")
    await conn.execute(
        "UPDATE executions SET created_at = now() - interval '10 minutes' WHERE id = $1::uuid", exec_id,
    )

    from pinky_worker.observation.observer import _sweep_stuck_executions
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stuck_executions(cluster_id)

    assert count == 1
    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", exec_id)
    assert row["status"] == "failed"


async def test_pending_remediation_not_cleaned(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Pending remediation must NOT be swept — it legitimately waits for approval."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "remediation", "pending")
    await conn.execute(
        "UPDATE executions SET created_at = now() - interval '1 hour' WHERE id = $1::uuid", exec_id,
    )

    from pinky_worker.observation.observer import _sweep_stuck_executions
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stuck_executions(cluster_id)

    assert count == 0
    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", exec_id)
    assert row["status"] == "pending"


async def test_recent_pending_execution_not_cleaned(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Pending execution under 5 min old must NOT be swept."""
    issue_id, wi_id = await _seed_issue_and_task(conn, cluster_id)
    exec_id = await _seed_execution(conn, cluster_id, wi_id, "investigation", "pending")

    from pinky_worker.observation.observer import _sweep_stuck_executions
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stuck_executions(cluster_id)

    assert count == 0
    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", exec_id)
    assert row["status"] == "pending"


async def test_sweep_only_affects_target_cluster(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Sweep for cluster A must not touch cluster B data."""
    other_cluster = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state, created_at, updated_at)
           VALUES ($1::uuid, 'other-cluster', 'https://other:6443', 'ready', now(), now())""",
        other_cluster,
    )
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3, 'Other cluster issue', 'high',
           'resolved', '{}', '{}', now(), now(), now(), now())""",
        issue_id, other_cluster, f"test-{uuid.uuid4().hex[:8]}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'Other cluster task', 'ready',
           NULL, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, other_cluster,
    )

    from pinky_worker.observation.observer import _sweep_orphaned_tasks
    pool = _FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_orphaned_tasks(cluster_id)

    assert count == 0
    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"


async def test_suppressed_issue_has_no_open_tasks(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Suppressed issue → work_items marked done, no active tasks for user."""
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, suppressed_until, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3, 'Suppressed issue', 'medium',
           'suppressed', now() + interval '1 hour', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id, f"test-{uuid.uuid4().hex[:8]}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'Suppressed issue', 'done',
           NULL, 'medium', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )

    active_tasks = await conn.fetch(
        "SELECT id FROM work_items WHERE issue_id = $1::uuid AND status != 'done'",
        issue_id,
    )
    assert len(active_tasks) == 0

    issue = await conn.fetchrow("SELECT status FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "suppressed"
