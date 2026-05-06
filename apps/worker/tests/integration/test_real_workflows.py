"""Real workflow integration tests — uses real DB, real activities, real Temporal.

Only K8s client and LLM provider are mocked. Everything else (emit_execution_event,
store_artifact, DB writes, UUID resolution, status projection) runs for real.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import asyncpg
import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pinky_worker.execution.activities import (
    EvidenceBundle,
    ExecutionEventPayload,
    InvestigationArtifact,
    emit_execution_event,
    check_artifact_cache,
    store_artifact,
)
from pinky_worker.issues.correlator import CorrelationResult, RawObservation
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.workflows.investigation import InvestigationInput, InvestigationWorkflow

from .conftest import FakePool

TASK_QUEUE = "test-real-workflows"


# --- Fixtures ---


@pytest.fixture
def pool_patch(conn: asyncpg.Connection):
    fp = FakePool(conn)
    mock = AsyncMock(return_value=fp)
    with (
        patch("pinky_worker.db.get_pool", mock),
        patch("pinky_worker.issues.db_correlator.get_pool", mock),
    ):
        yield fp


async def _seed_issue_and_work_item(conn: asyncpg.Connection, cluster_id: str) -> tuple[str, str]:
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, 'test-corr-key', 'Test issue', 'high',
           'open', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id,
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'Test task', 'ready',
           0.7, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )
    return issue_id, wi_id


# --- Mock activities for K8s + LLM (only these are mocked) ---


@activity.defn(name="gather_evidence")
async def mock_gather(issue_id: str, cluster_id: str, skill_tools: list[str] | None = None) -> EvidenceBundle:
    return EvidenceBundle(
        issue_id=issue_id,
        cluster_id=cluster_id,
        fingerprint="fp-test",
        evidence_hash="hash-test",
        sections={"status": "CrashLoopBackOff"},
    )


@activity.defn(name="run_investigation")
async def mock_llm(evidence: EvidenceBundle, skill_body: str, execution_id: str = "") -> InvestigationArtifact:
    return InvestigationArtifact(
        artifact_id=str(uuid.uuid4()),
        issue_id=evidence.issue_id,
        summary="Pod is crash-looping",
        root_cause="OOMKilled",
        recommended_action="Increase memory",
        confidence=0.85,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
    )


# --- Tests ---


async def test_emit_event_updates_execution_status(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
) -> None:
    """emit_execution_event with real DB updates execution status."""
    await emit_execution_event(ExecutionEventPayload(
        execution_id=execution_id,
        event_type="started", sequence=0, payload={},
    ))

    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", execution_id)
    assert row["status"] == "running"

    await emit_execution_event(ExecutionEventPayload(
        execution_id=execution_id,
        event_type="completed", sequence=1, payload={},
    ))

    row = await conn.fetchrow("SELECT status, completed_at FROM executions WHERE id = $1::uuid", execution_id)
    assert row["status"] == "completed"
    assert row["completed_at"] is not None


async def test_emit_event_writes_to_execution_events_table(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
) -> None:
    """emit_execution_event inserts rows into execution_events."""
    await emit_execution_event(ExecutionEventPayload(
        execution_id=execution_id,
        event_type="started", sequence=0, payload={"type": "investigation"},
    ))

    events = await conn.fetch(
        "SELECT event_type, sequence FROM execution_events WHERE execution_id = $1::uuid ORDER BY sequence",
        execution_id,
    )
    assert len(events) == 1
    assert events[0]["event_type"] == "started"


async def test_emit_resolves_investigation_prefix(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
) -> None:
    """emit_execution_event resolves investigation-{uuid} to the real execution UUID."""
    workflow_id = f"investigation-{execution_id}"

    await emit_execution_event(ExecutionEventPayload(
        execution_id=workflow_id,
        event_type="started", sequence=0, payload={},
    ))

    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", execution_id)
    assert row["status"] == "running"


async def test_observer_dispatch_creates_execution(
    conn: asyncpg.Connection, cluster_id: str, pool_patch,
) -> None:
    """_dispatch_investigation creates an execution record before starting workflow."""
    from pinky_worker.observation.observer import _dispatch_investigation

    issue_id, wi_id = await _seed_issue_and_work_item(conn, cluster_id)

    mock_client = AsyncMock()
    mock_client.start_workflow = AsyncMock()
    obs = MagicMock(fingerprint="abc123", correlation_key="test-key",
                    check_id="crash", resource_kind="Pod",
                    resource_namespace="default", resource_name="pod-1")
    result = CorrelationResult(action="created", issue_id=issue_id, observation_count=1)
    decision = MagicMock()
    decision.action.skill = None

    await _dispatch_investigation(mock_client, cluster_id, obs, result, decision, MagicMock())

    execs = await conn.fetch(
        "SELECT id, work_item_id, status FROM executions WHERE cluster_id = $1::uuid AND execution_type = 'investigation'",
        cluster_id,
    )
    assert len(execs) >= 1
    latest = execs[-1]
    assert latest["status"] == "pending"
    assert str(latest["work_item_id"]) == wi_id

    mock_client.start_workflow.assert_called_once()
    wf_id = mock_client.start_workflow.call_args.kwargs["id"]
    assert wf_id.startswith(f"investigation-{cluster_id[:8]}")


async def test_observer_dispatch_skips_if_pending_exists(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
) -> None:
    """_dispatch_investigation does NOT start a new workflow if one is already pending."""
    from pinky_worker.observation.observer import _dispatch_investigation

    issue_id, wi_id = await _seed_issue_and_work_item(conn, cluster_id)

    await conn.execute(
        "UPDATE executions SET work_item_id = $1::uuid WHERE id = $2::uuid",
        wi_id, execution_id,
    )

    mock_client = AsyncMock()
    obs = MagicMock(fingerprint="abc123", correlation_key="test-key",
                    check_id="crash", resource_kind="Pod",
                    resource_namespace="default", resource_name="pod-1")
    result = CorrelationResult(action="created", issue_id=issue_id, observation_count=1)
    decision = MagicMock()
    decision.action.skill = None

    await _dispatch_investigation(mock_client, cluster_id, obs, result, decision, MagicMock())

    mock_client.start_workflow.assert_not_called()


@pytest.mark.skip(reason="ON CONFLICT requires non-transactional connection — tested in test_db_correlator.py")
async def test_observation_insert_generates_uuid(
    conn: asyncpg.Connection, cluster_id: str, pool_patch,
) -> None:
    """DbIssueCorrelator generates a UUID for each observation."""
    correlator = DbIssueCorrelator()

    obs = RawObservation(
        cluster_id=cluster_id,
        scanner="test-scanner",
        scanner_version="1.0.0",
        fingerprint=f"fp-{uuid.uuid4().hex[:16]}",
        check_id="test-check",
        severity="medium",
        resource_kind="Pod",
        resource_namespace="default",
        resource_name="test-pod",
        title="Test observation",
        observed_at=datetime.now(UTC),
        correlation_key=f"corr-{uuid.uuid4().hex[:8]}",
    )

    await correlator.correlate(obs)

    row = await conn.fetchrow(
        "SELECT id FROM observations WHERE fingerprint = $1", obs.fingerprint,
    )
    assert row is not None
    assert row["id"] is not None


@pytest.mark.skip(reason="ON CONFLICT requires non-transactional connection — tested in test_db_correlator.py")
async def test_duplicate_observation_no_duplicate_issue(
    conn: asyncpg.Connection, cluster_id: str, pool_patch,
) -> None:
    """Same observation correlated twice creates only one issue."""
    correlator = DbIssueCorrelator()
    corr_key = f"corr-{uuid.uuid4().hex[:8]}"

    obs = RawObservation(
        cluster_id=cluster_id,
        scanner="test-scanner",
        scanner_version="1.0.0",
        fingerprint=f"fp-{uuid.uuid4().hex[:16]}",
        check_id="test-check",
        severity="high",
        resource_kind="Pod",
        resource_namespace="default",
        resource_name="test-pod",
        title="Duplicate test",
        observed_at=datetime.now(UTC),
        correlation_key=corr_key,
    )

    r1 = await correlator.correlate(obs)
    assert r1.action == "created"

    r2 = await correlator.correlate(obs)
    assert r2.action == "attached"
    assert r2.issue_id == r1.issue_id

    issues = await conn.fetch(
        "SELECT id FROM issues WHERE correlation_key = $1", corr_key,
    )
    assert len(issues) == 1


@pytest.mark.skip(reason="ON CONFLICT requires non-transactional connection — tested in test_full_pipeline.py")
async def test_full_pipeline_observation_to_completed_execution(
    conn: asyncpg.Connection, cluster_id: str, pool_patch,
    workflow_env: WorkflowEnvironment,
) -> None:
    """Full pipeline: correlate → dispatch → workflow → events → status update."""
    correlator = DbIssueCorrelator()
    corr_key = f"corr-{uuid.uuid4().hex[:8]}"

    obs = RawObservation(
        cluster_id=cluster_id,
        scanner="test-scanner",
        scanner_version="1.0.0",
        fingerprint=f"fp-{uuid.uuid4().hex[:16]}",
        check_id="crash-loop",
        severity="critical",
        resource_kind="Pod",
        resource_namespace="default",
        resource_name="crash-pod",
        title="Pod crash-looping",
        observed_at=datetime.now(UTC),
        correlation_key=corr_key,
    )

    result = await correlator.correlate(obs)
    assert result.action == "created"

    wi_row = await conn.fetchrow(
        "SELECT id FROM work_items WHERE issue_id = $1::uuid", result.issue_id,
    )
    assert wi_row is not None

    exec_id = uuid.uuid4()
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1, $2, $3::uuid, 'investigation', 'pending', now())""",
        exec_id, wi_row["id"], cluster_id,
    )

    activities = [emit_execution_event, mock_gather, check_artifact_cache, mock_llm, store_artifact]

    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[InvestigationWorkflow], activities=activities,
    ):
        wf_result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id=result.issue_id,
                cluster_id=cluster_id,
                correlation_key=corr_key,
                evidence_hash="",
                execution_id=str(exec_id),
            ),
            id=f"test-pipeline-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert wf_result.summary == "Pod is crash-looping"
    assert wf_result.confidence == 0.85

    exec_row = await conn.fetchrow("SELECT status, completed_at FROM executions WHERE id = $1", exec_id)
    assert exec_row["status"] == "completed"
    assert exec_row["completed_at"] is not None

    events = await conn.fetch(
        "SELECT event_type FROM execution_events WHERE execution_id = $1 ORDER BY sequence", exec_id,
    )
    event_types = [e["event_type"] for e in events]
    assert "started" in event_types
    assert "completed" in event_types


async def test_investigation_pending_to_completed(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
    workflow_env: WorkflowEnvironment,
) -> None:
    """Prove the full lifecycle: pending → running → completed via Temporal.

    No correlator dependency — seeds DB directly.
    """
    issue_id, wi_id = await _seed_issue_and_work_item(conn, cluster_id)
    await conn.execute(
        "UPDATE executions SET work_item_id = $1::uuid WHERE id = $2::uuid",
        wi_id, execution_id,
    )

    activities = [emit_execution_event, mock_gather, check_artifact_cache, mock_llm, store_artifact]

    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[InvestigationWorkflow], activities=activities,
    ):
        wf_result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id=issue_id,
                cluster_id=cluster_id,
                correlation_key="test-key",
                evidence_hash="",
                execution_id=execution_id,
            ),
            id=f"test-e2e-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert wf_result.summary == "Pod is crash-looping"
    assert wf_result.confidence == 0.85
    assert not wf_result.cached

    row = await conn.fetchrow(
        "SELECT status, started_at, completed_at FROM executions WHERE id = $1::uuid",
        execution_id,
    )
    assert row["status"] == "completed"
    assert row["started_at"] is not None
    assert row["completed_at"] is not None

    events = await conn.fetch(
        "SELECT event_type FROM execution_events WHERE execution_id = $1::uuid ORDER BY sequence",
        execution_id,
    )
    event_types = [e["event_type"] for e in events]
    assert "started" in event_types
    assert "completed" in event_types
    assert "investigation_completed" in event_types


async def test_investigation_workflow_failure_marks_failed(
    conn: asyncpg.Connection, cluster_id: str, execution_id: str, pool_patch,
    workflow_env: WorkflowEnvironment,
) -> None:
    """When an activity fails, the workflow emits a failed event and the execution is marked failed."""

    @activity.defn(name="gather_evidence")
    async def failing_gather(issue_id: str, cluster_id: str, skill_tools: list[str] | None = None) -> EvidenceBundle:
        raise RuntimeError("K8s cluster unreachable")

    activities = [emit_execution_event, failing_gather, check_artifact_cache, mock_llm, store_artifact]

    from temporalio.client import WorkflowFailureError

    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[InvestigationWorkflow], activities=activities,
    ):
        with pytest.raises(WorkflowFailureError):
            await workflow_env.client.execute_workflow(
                InvestigationWorkflow.run,
                InvestigationInput(
                    issue_id="fake-issue",
                    cluster_id=cluster_id,
                    correlation_key="test-key",
                    evidence_hash="",
                    execution_id=execution_id,
                ),
                id=f"test-fail-{uuid.uuid4()}",
                task_queue=TASK_QUEUE,
            )

    row = await conn.fetchrow("SELECT status FROM executions WHERE id = $1::uuid", execution_id)
    assert row["status"] == "failed"

    events = await conn.fetch(
        "SELECT event_type FROM execution_events WHERE execution_id = $1::uuid ORDER BY sequence",
        execution_id,
    )
    event_types = [e["event_type"] for e in events]
    assert "started" in event_types
    assert "failed" in event_types
