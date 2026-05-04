"""Activity DB integration tests against real Postgres.

Tests activities that read/write to the database: artifact cache,
event emission, approval validation, execution projection.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import asyncpg
import pytest

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://pinky:pinky@localhost:5432/pinky",
)


@pytest.fixture
async def conn():
    c = await asyncpg.connect(TEST_DB_URL)
    tx = c.transaction()
    await tx.start()
    try:
        yield c
    finally:
        await tx.rollback()
        await c.close()


def _mock_pool(conn: asyncpg.Connection):
    """Wrap a connection to look like an asyncpg pool."""

    class _Pool:
        async def fetchrow(self, query, *args):
            return await conn.fetchrow(query, *args)

        async def fetchval(self, query, *args):
            return await conn.fetchval(query, *args)

        async def execute(self, query, *args):
            return await conn.execute(query, *args)

    return _Pool()


@pytest.fixture
async def cluster_id(conn: asyncpg.Connection) -> str:
    cid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state, created_at, updated_at)
           VALUES ($1::uuid, 'test-cluster', 'https://api.test:6443', 'ready', now(), now())""",
        cid,
    )
    return cid


@pytest.fixture
async def execution_id(conn: asyncpg.Connection, cluster_id: str) -> str:
    eid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO executions (id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, 'investigation', 'pending', now())""",
        eid, cluster_id,
    )
    return eid


# --- store_artifact + check_artifact_cache ---


async def test_store_artifact_writes_event(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import InvestigationArtifact, store_artifact

    artifact = InvestigationArtifact(
        artifact_id=execution_id,
        issue_id=str(uuid.uuid4()),
        summary="OOM detected",
        root_cause="Memory limit too low",
        recommended_action="Increase to 512Mi",
        confidence=0.85,
        tool_calls=[],
        evidence_hash="hash-123",
        created_at=datetime.now(UTC).isoformat(),
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await store_artifact(artifact)

    assert result == execution_id

    row = await conn.fetchrow(
        "SELECT * FROM execution_events WHERE event_type = 'investigation_completed' AND execution_id = $1",
        uuid.UUID(execution_id),
    )
    assert row is not None
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    assert payload["summary"] == "OOM detected"
    assert payload["evidence_hash"] == "hash-123"


async def test_cache_miss_returns_none(conn: asyncpg.Connection) -> None:
    from pinky_worker.execution.activities import check_artifact_cache

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await check_artifact_cache("nonexistent-hash", "key-1")

    assert result is None


async def test_cache_hit_returns_artifact(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import check_artifact_cache

    exec_id = uuid.UUID(execution_id)
    payload = {
        "artifact_id": str(uuid.uuid4()),
        "issue_id": str(uuid.uuid4()),
        "summary": "Cached OOM analysis",
        "root_cause": "Memory leak",
        "recommended_action": "Fix the leak",
        "confidence": 0.9,
        "tool_calls": [],
        "evidence_hash": "hash-cached",
    }
    await conn.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, 'investigation_completed', 999, $3, $4)""",
        uuid.uuid4(), exec_id, json.dumps(payload), datetime.now(UTC),
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await check_artifact_cache("hash-cached", "key-1")

    assert result is not None
    assert result.summary == "Cached OOM analysis"
    assert result.confidence == 0.9


async def test_cache_expired_returns_none(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import check_artifact_cache

    exec_id = uuid.UUID(execution_id)
    old_time = datetime.now(UTC) - timedelta(hours=2)
    payload = {"evidence_hash": "hash-old", "summary": "Old result"}
    await conn.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, 'investigation_completed', 999, $3, $4)""",
        uuid.uuid4(), exec_id, json.dumps(payload), old_time,
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await check_artifact_cache("hash-old", "key-1")

    assert result is None


# --- emit_execution_event ---


async def test_emit_event_writes_to_db(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event

    event = ExecutionEventPayload(
        execution_id=execution_id,
        event_type="started",
        sequence=0,
        payload={"type": "investigation"},
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        await emit_execution_event(event)

    row = await conn.fetchrow(
        "SELECT * FROM execution_events WHERE execution_id = $1",
        uuid.UUID(execution_id),
    )
    assert row is not None
    assert row["event_type"] == "started"
    assert row["sequence"] == 0


# --- validate_approval ---


async def test_validate_approval_valid(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import validate_approval

    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest-abc', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) + timedelta(hours=4),
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await validate_approval(str(approval_id), "digest-abc")

    assert result["valid"] is True


async def test_validate_approval_not_found(conn: asyncpg.Connection) -> None:
    from pinky_worker.execution.activities import validate_approval

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await validate_approval(str(uuid.uuid4()), "")

    assert result["valid"] is False
    assert "not found" in result["reason"]


async def test_validate_approval_expired(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import validate_approval

    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) - timedelta(hours=1),
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await validate_approval(str(approval_id), "")

    assert result["valid"] is False
    assert "expired" in result["reason"]


async def test_validate_approval_digest_mismatch(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import validate_approval

    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest-original', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) + timedelta(hours=4),
    )

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        result = await validate_approval(str(approval_id), "digest-different")

    assert result["valid"] is False
    assert "changeset changed" in result["reason"]


# --- project_to_postgres ---


async def test_project_started_updates_execution(conn: asyncpg.Connection, execution_id: str) -> None:
    from pinky_worker.execution.activities import project_to_postgres

    with patch("pinky_worker.db.get_pool", return_value=_mock_pool(conn)):
        await project_to_postgres(execution_id, "started", {"type": "investigation"})

    row = await conn.fetchrow("SELECT * FROM executions WHERE id = $1", uuid.UUID(execution_id))
    assert row["status"] == "running"
    assert row["started_at"] is not None

    history = await conn.fetchrow(
        "SELECT * FROM history_events WHERE aggregate_id = $1 AND event_type = 'started'",
        uuid.UUID(execution_id),
    )
    assert history is not None
