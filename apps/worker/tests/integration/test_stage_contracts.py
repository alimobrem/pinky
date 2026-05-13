"""Stage contract tests — verify outputs of one stage match inputs of the next.

If someone changes how store_artifact writes plan_steps or how project_to_postgres
marks tasks done, these tests catch the break before production.

Requires: real Postgres.
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest

from .conftest import FakePool


async def _seed_full(conn: asyncpg.Connection, cluster_id: str) -> tuple[str, str, str]:
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, 'contract-test', 'Contract test', 'high',
           'open', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id,
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'Contract test', 'ready',
           NULL, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'investigation', 'running', now())""",
        exec_id, wi_id, cluster_id,
    )
    return issue_id, wi_id, exec_id


async def test_command_event_payload_matches_terminal_expectations(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """_emit_command_event output must have all fields ExecutionTerminal expects."""
    issue_id, wi_id, exec_id = await _seed_full(conn, cluster_id)

    pool = FakePool(conn)
    from pinky_worker.execution.activities import _emit_command_event
    await _emit_command_event(
        pool, exec_id, 500,
        "oc scale deployment web -n default --replicas=3",
        "deployment.apps/web scaled",
        0, "scale", "deployment/web",
    )

    event = await conn.fetchrow(
        "SELECT payload FROM execution_events WHERE execution_id = $1::uuid AND event_type = 'command'",
        exec_id,
    )
    assert event is not None
    payload = json.loads(event["payload"]) if isinstance(event["payload"], str) else event["payload"]
    assert "command" in payload
    assert "output" in payload
    assert "exit_code" in payload
    assert "action" in payload
    assert "resource" in payload
    assert isinstance(payload["exit_code"], int)


async def test_project_to_postgres_completed_remediation_state(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """project_to_postgres(completed, verification_passed=True) must set task done + issue resolved."""
    issue_id, wi_id, _ = await _seed_full(conn, cluster_id)
    exec_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'remediation', 'running', now())""",
        exec_id, wi_id, cluster_id,
    )

    pool = FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import project_to_postgres
        await project_to_postgres(exec_id, "completed", {"verification_passed": True})

    execution = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", exec_id)
    assert execution["status"] == "completed"

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "done"

    issue = await conn.fetchrow("SELECT status, resolved_by FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "resolved"
    assert issue["resolved_by"] == "remediation"


async def test_project_to_postgres_investigation_does_not_complete_task(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """project_to_postgres(completed) for investigation must NOT mark task done."""
    issue_id, wi_id, exec_id = await _seed_full(conn, cluster_id)

    pool = FakePool(conn)
    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import project_to_postgres
        await project_to_postgres(exec_id, "completed", {"confidence": 0.85})

    task = await conn.fetchrow("SELECT status FROM work_items WHERE id = $1::uuid", wi_id)
    assert task["status"] == "ready"

    issue = await conn.fetchrow("SELECT status FROM issues WHERE id = $1::uuid", issue_id)
    assert issue["status"] == "open"


async def test_execution_events_ordered_by_sequence(
    conn: asyncpg.Connection, cluster_id: str,
) -> None:
    """Events must be retrievable in correct order regardless of insertion timing."""
    issue_id, wi_id, exec_id = await _seed_full(conn, cluster_id)

    pool = FakePool(conn)
    from pinky_worker.execution.activities import _emit_event

    await _emit_event(pool, exec_id, "started", 0, {"type": "remediation"})
    await _emit_event(pool, exec_id, "progress", 2, {"step": 1})
    await _emit_event(pool, exec_id, "command", 500, {"command": "oc scale ..."})
    await _emit_event(pool, exec_id, "progress", 4, {"step": 2})
    await _emit_event(pool, exec_id, "command", 510, {"command": "oc patch ..."})
    await _emit_event(pool, exec_id, "completed", 100, {"verification_passed": True})

    events = await conn.fetch(
        "SELECT event_type, sequence FROM execution_events WHERE execution_id = $1::uuid ORDER BY sequence",
        exec_id,
    )
    sequences = [e["sequence"] for e in events]
    assert sequences == sorted(sequences)
    types = [e["event_type"] for e in events]
    assert types[0] == "started"
    assert types[-1] == "command"
    assert "progress" in types
