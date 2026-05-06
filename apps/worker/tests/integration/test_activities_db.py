"""Activity DB integration tests against real Postgres."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import asyncpg

from pinky_worker.execution.activities import (
    ExecutionEventPayload,
    InvestigationArtifact,
    check_artifact_cache,
    emit_execution_event,
    project_to_postgres,
    store_artifact,
    validate_approval,
)

from .conftest import FakePool

PATCH_TARGET = "pinky_worker.db.get_pool"


async def test_store_artifact_writes_event(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
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
        execution_id=execution_id,
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await store_artifact(artifact)

    assert result == execution_id
    row = await conn.fetchrow(
        "SELECT payload FROM execution_events WHERE event_type = 'investigation_completed' AND execution_id = $1",
        uuid.UUID(execution_id),
    )
    assert row is not None
    payload = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    assert payload["summary"] == "OOM detected"
    assert payload["evidence_hash"] == "hash-123"


async def test_cache_miss_returns_none(fake_pool: FakePool) -> None:
    with patch(PATCH_TARGET, return_value=fake_pool):
        assert await check_artifact_cache("nonexistent-hash", "key-1") is None


async def test_cache_hit_returns_artifact(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    payload = {
        "artifact_id": str(uuid.uuid4()),
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
        uuid.uuid4(), uuid.UUID(execution_id), json.dumps(payload), datetime.now(UTC),
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await check_artifact_cache("hash-cached", "key-1")

    assert result is not None
    assert result.summary == "Cached OOM analysis"
    assert result.confidence == 0.9


async def test_cache_expired_returns_none(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    await conn.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, 'investigation_completed', 999, $3, $4)""",
        uuid.uuid4(), uuid.UUID(execution_id),
        json.dumps({"evidence_hash": "hash-old"}),
        datetime.now(UTC) - timedelta(hours=2),
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        assert await check_artifact_cache("hash-old", "key-1") is None


async def test_emit_event_writes_to_db(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    event = ExecutionEventPayload(
        execution_id=execution_id,
        event_type="started",
        sequence=0,
        payload={"type": "investigation"},
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        await emit_execution_event(event)

    row = await conn.fetchrow(
        "SELECT event_type, sequence FROM execution_events WHERE execution_id = $1",
        uuid.UUID(execution_id),
    )
    assert row is not None
    assert row["event_type"] == "started"


async def test_validate_approval_valid(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest-abc', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) + timedelta(hours=4),
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await validate_approval(str(approval_id), "digest-abc")

    assert result["valid"] is True


async def test_validate_approval_not_found(fake_pool: FakePool) -> None:
    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await validate_approval(str(uuid.uuid4()), "")

    assert result["valid"] is False
    assert "not found" in result["reason"]


async def test_validate_approval_expired(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) - timedelta(hours=1),
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await validate_approval(str(approval_id), "")

    assert result["valid"] is False
    assert "expired" in result["reason"]


async def test_validate_approval_digest_mismatch(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    approval_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO approvals (id, execution_id, changeset_digest, target_resources, status, expires_at, created_at)
           VALUES ($1, $2::uuid, 'digest-original', '[]', 'pending', $3, now())""",
        approval_id, execution_id, datetime.now(UTC) + timedelta(hours=4),
    )

    with patch(PATCH_TARGET, return_value=fake_pool):
        result = await validate_approval(str(approval_id), "digest-different")

    assert result["valid"] is False
    assert "changeset changed" in result["reason"]


async def test_project_started_updates_execution(
    conn: asyncpg.Connection, execution_id: str, fake_pool: FakePool,
) -> None:
    with patch(PATCH_TARGET, return_value=fake_pool):
        await project_to_postgres(execution_id, "started", {"type": "investigation"})

    row = await conn.fetchrow("SELECT status, started_at FROM executions WHERE id = $1", uuid.UUID(execution_id))
    assert row["status"] == "running"
    assert row["started_at"] is not None

    history = await conn.fetchrow(
        "SELECT event_type FROM history_events WHERE aggregate_id = $1 AND event_type = 'started'",
        uuid.UUID(execution_id),
    )
    assert history is not None
