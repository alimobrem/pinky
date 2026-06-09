"""Full pipeline integration test.

Tests the complete chain: fake K8s pods → scanner detects issue →
Temporal workflow runs investigation (mocked LLM) → artifact stored.

Also tests the complete investigation → remediation → verification →
auto-complete flow with real DB state transitions.

Requires: real Postgres, Temporal CLI.
Mocks: K8s API (fake pod data), LLM provider (fake response).
"""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import asyncpg
import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pinky_worker.definitions.loader import Definition
from pinky_worker.execution.activities import (
    EvidenceBundle,
    ExecutionEventPayload,
    InvestigationArtifact,
    check_artifact_cache,
    emit_execution_event,
    store_artifact,
)
from pinky_worker.observation.generic_scanner import run_generic_checks
from pinky_worker.workflows.investigation import (
    InvestigationInput,
    InvestigationResult,
    InvestigationWorkflow,
)
from pinky_worker.workflows.remediation import RemediationInput, RemediationWorkflow
from pinky_worker.workflows.verification import VerificationWorkflow

from .conftest import FakePool

TASK_QUEUE = "test-pipeline"

FAKE_PODS = [
    {
        "name": "web-frontend-abc123",
        "namespace": "production",
        "status": "CrashLoopBackOff",
        "containers": [
            {
                "name": "web",
                "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
                "restart_count": 12,
            }
        ],
    },
    {
        "name": "api-server-xyz789",
        "namespace": "production",
        "status": "Running",
        "containers": [
            {
                "name": "api",
                "state": {"type": "running"},
                "last_state": {},
                "restart_count": 0,
            }
        ],
    },
]

SCANNER_DEF = Definition(
    kind="scanner", name="pod-health", version="1.0.0",
    frontmatter={
        "kind": "scanner", "name": "pod-health", "version": "1.0.0",
        "resource_kinds": ["Pod"],
        "checks": [
            {
                "id": "crash-loop-backoff",
                "title": "CrashLoopBackOff: {name}",
                "severity": "high",
                "iterate": "containers",
                "condition": {"path": "state.reason", "op": "eq", "value": "CrashLoopBackOff"},
            },
            {
                "id": "oom-killed",
                "title": "OOMKilled: {name}",
                "severity": "critical",
                "iterate": "containers",
                "condition": {"path": "last_state.reason", "op": "eq", "value": "OOMKilled"},
            },
        ],
    },
    body="", source="test",
)


# ---------------------------------------------------------------------------
# Mock activities — only K8s + LLM are mocked; emit/store run against real DB
# ---------------------------------------------------------------------------


@activity.defn(name="gather_evidence")
async def mock_gather(
    issue_id: str, cluster_id: str,
    skill_tools: list[str] | None = None, execution_id: str = "",
) -> EvidenceBundle:
    return EvidenceBundle(
        issue_id=issue_id,
        cluster_id=cluster_id,
        fingerprint="pipeline-test",
        evidence_hash=f"pipeline-{uuid.uuid4().hex[:8]}",
        sections={
            "pods": json.dumps(FAKE_PODS, indent=2),
            "events": "[]",
            "cluster_id": cluster_id,
            "issue_id": issue_id,
        },
    )


@activity.defn(name="run_investigation")
async def mock_investigate(
    evidence: EvidenceBundle, skill_body: str, execution_id: str = "",
) -> InvestigationArtifact:
    patch_body = {
        "spec": {"template": {"spec": {"containers": [
            {"name": "web", "resources": {"limits": {"memory": "512Mi"}}},
        ]}}},
    }
    return InvestigationArtifact(
        artifact_id=str(uuid.uuid4()),
        issue_id=evidence.issue_id,
        summary="Pod web-frontend is OOMKilled. Memory limit 128Mi is too low.",
        root_cause="Container exceeds 128Mi memory limit under load.",
        recommended_action="Increase memory limit to 512Mi.",
        confidence=0.9,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
        execution_id=execution_id,
        remediation_steps=[
            {
                "action": "patch",
                "description": "Increase memory limit",
                "resource_kind": "Deployment",
                "resource_namespace": "production",
                "resource_name": "web-frontend",
                "params": {"patch": patch_body},
                "risk": "low",
            },
        ],
    )


@activity.defn(name="run_investigation")
async def mock_investigate_no_remediation(
    evidence: EvidenceBundle, skill_body: str, execution_id: str = "",
) -> InvestigationArtifact:
    """Investigation that returns no remediation steps (for rejection test)."""
    return InvestigationArtifact(
        artifact_id=str(uuid.uuid4()),
        issue_id=evidence.issue_id,
        summary="Pod web-frontend is OOMKilled. Memory limit 128Mi is too low.",
        root_cause="Container exceeds 128Mi memory limit under load.",
        recommended_action="Increase memory limit to 512Mi.",
        confidence=0.9,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
        execution_id=execution_id,
    )


_emitted: list[ExecutionEventPayload] = []


@activity.defn(name="emit_execution_event")
async def mock_emit(event: ExecutionEventPayload) -> None:
    _emitted.append(event)


@activity.defn(name="check_artifact_cache")
async def mock_cache_miss(evidence_hash: str, correlation_key: str) -> InvestigationArtifact | None:
    return None


@activity.defn(name="store_artifact")
async def mock_store(artifact: InvestigationArtifact) -> str:
    return artifact.artifact_id


@activity.defn(name="validate_approval")
async def mock_validate_ok(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": True}


@activity.defn(name="apply_change")
async def mock_apply_success(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    return {"status": "applied", "action": step.get("action", "")}


@activity.defn(name="verify_state")
async def mock_verify_pass(
    cluster_id: str, expected_state: dict, target_resources: list | None = None,
) -> dict:
    return {"passed": True, "details": {"total_pods": 3, "unhealthy_pods": 0}}


@activity.defn(name="verify_state")
async def mock_verify_fail(
    cluster_id: str, expected_state: dict, target_resources: list | None = None,
) -> dict:
    return {"passed": False, "details": {"total_pods": 3, "unhealthy_pods": 2}}


@activity.defn(name="revalidate_binding")
async def mock_revalidate_binding(binding_id: str) -> dict:
    return {"valid": True}


@pytest.fixture(autouse=True)
def _reset():
    _emitted.clear()


@pytest.fixture
def pool_patch(conn: asyncpg.Connection):
    """Patch get_pool to return FakePool wrapping the transactional connection."""
    fp = FakePool(conn)
    mock = AsyncMock(return_value=fp)
    with (
        patch("pinky_worker.db.get_pool", mock),
        patch("pinky_worker.issues.db_correlator.get_pool", mock),
    ):
        yield fp


# ---------------------------------------------------------------------------
# DB seeding helpers
# ---------------------------------------------------------------------------


async def _seed_issue_work_item_execution(
    conn: asyncpg.Connection,
    cluster_id: str,
    *,
    execution_type: str = "investigation",
) -> tuple[str, str, str]:
    """Create issue + work_item + execution, return (issue_id, wi_id, exec_id)."""
    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    exec_id = str(uuid.uuid4())

    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3, 'CrashLoopBackOff: web-frontend', 'high',
           'open', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id, f"pipeline-test-{issue_id[:8]}",
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'CrashLoopBackOff: web-frontend', 'ready',
           0.7, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, $4, 'pending', now())""",
        exec_id, wi_id, cluster_id, execution_type,
    )
    return issue_id, wi_id, exec_id


# ---------------------------------------------------------------------------
# Original scanner test (unchanged)
# ---------------------------------------------------------------------------


async def test_scanner_detects_issues() -> None:
    """Generic scanner correctly identifies CrashLoopBackOff and OOMKilled from fake pod data."""
    cluster_id = str(uuid.uuid4())
    observations = await run_generic_checks(FAKE_PODS, cluster_id, SCANNER_DEF)

    assert len(observations) >= 2
    check_ids = {o.check_id for o in observations}
    assert "crash-loop-backoff" in check_ids
    assert "oom-killed" in check_ids

    crash_obs = next(o for o in observations if o.check_id == "crash-loop-backoff")
    assert crash_obs.severity == "high"
    assert crash_obs.resource_namespace == "production"
    assert crash_obs.resource_name == "web-frontend-abc123"

    oom_obs = next(o for o in observations if o.check_id == "oom-killed")
    assert oom_obs.severity == "critical"


# ---------------------------------------------------------------------------
# Original pipeline test — investigation only (unchanged)
# ---------------------------------------------------------------------------


async def test_full_pipeline(conn: asyncpg.Connection, cluster_id: str, workflow_env: WorkflowEnvironment) -> None:
    """End-to-end: seed DB → workflow → verify events emitted."""

    issue_id = str(uuid.uuid4())
    wi_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
           status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, 'pipeline-test', 'CrashLoopBackOff: web-frontend', 'high',
           'open', '{}', '{}', now(), now(), now(), now())""",
        issue_id, cluster_id,
    )
    await conn.execute(
        """INSERT INTO work_items (id, issue_id, cluster_id, title, status,
           confidence, priority, labels, annotations, artifact_refs, created_at, updated_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'CrashLoopBackOff: web-frontend', 'ready',
           0.7, 'high', '{}', '{}', '{}', now(), now())""",
        wi_id, issue_id, cluster_id,
    )

    activities = [mock_emit, mock_gather, mock_cache_miss, mock_investigate, mock_store]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[InvestigationWorkflow], activities=activities,
    ):
        inv_result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id=issue_id,
                cluster_id=cluster_id,
                correlation_key="pipeline-test",
                evidence_hash="",
            ),
            id=f"pipeline-inv-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert isinstance(inv_result, InvestigationResult)
    assert inv_result.summary == "Pod web-frontend is OOMKilled. Memory limit 128Mi is too low."
    assert inv_result.confidence == 0.9
    assert not inv_result.cached

    event_types = [e.event_type for e in _emitted]
    assert "started" in event_types
    assert "completed" in event_types

    started = next(e for e in _emitted if e.event_type == "started")
    assert started.payload["type"] == "investigation"
    assert started.payload["issue_id"] == issue_id

    completed = next(e for e in _emitted if e.event_type == "completed")
    assert "artifact_id" in completed.payload
    assert completed.payload["confidence"] == 0.9


# ---------------------------------------------------------------------------
# NEW: Full investigation → remediation → verification → auto-complete
# ---------------------------------------------------------------------------


async def test_investigation_to_remediation_to_verification(
    conn: asyncpg.Connection,
    cluster_id: str,
    pool_patch: FakePool,
    workflow_env: WorkflowEnvironment,
) -> None:
    """Full flow: investigation → store_artifact creates approval →
    remediation (approve) → apply → verify (pass) → auto-complete.

    Uses real emit_execution_event and store_artifact against DB.
    """
    # 1. Seed DB
    issue_id, wi_id, inv_exec_id = await _seed_issue_work_item_execution(
        conn, cluster_id, execution_type="investigation",
    )

    # 2. Run InvestigationWorkflow with real emit + store (DB-backed)
    inv_activities = [
        emit_execution_event, mock_gather, check_artifact_cache,
        mock_investigate, store_artifact,
    ]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[InvestigationWorkflow], activities=inv_activities,
    ):
        inv_result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id=issue_id,
                cluster_id=cluster_id,
                correlation_key=f"pipeline-test-{issue_id[:8]}",
                evidence_hash="",
                execution_id=inv_exec_id,
            ),
            id=f"pipeline-full-inv-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert inv_result.summary == "Pod web-frontend is OOMKilled. Memory limit 128Mi is too low."
    assert inv_result.confidence == 0.9

    # 3. Verify investigation execution completed in DB
    inv_row = await conn.fetchrow(
        "SELECT status, completed_at FROM executions WHERE id = $1::uuid", inv_exec_id,
    )
    assert inv_row["status"] == "completed"
    assert inv_row["completed_at"] is not None

    # 4. Verify store_artifact created an approval (since mock_investigate returns remediation_steps)
    approval_row = await conn.fetchrow(
        "SELECT id, status, changeset_digest FROM approvals WHERE execution_id = $1::uuid",
        inv_exec_id,
    )
    assert approval_row is not None, "store_artifact should have created an approval"
    assert approval_row["status"] == "pending"
    approval_id = str(approval_row["id"])
    changeset_digest = approval_row["changeset_digest"]

    # 5. Verify work_item.artifact_refs populated
    wi_row = await conn.fetchrow(
        "SELECT artifact_refs FROM work_items WHERE id = $1::uuid", wi_id,
    )
    refs = json.loads(wi_row["artifact_refs"]) if isinstance(wi_row["artifact_refs"], str) else wi_row["artifact_refs"]
    assert refs.get("approval_id") == approval_id
    assert refs.get("changeset_digest") == changeset_digest
    plan_steps = refs.get("plan_steps", [])
    assert len(plan_steps) > 0

    # 6. Create remediation execution
    rem_exec_id = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, $3::uuid, 'remediation', 'pending', now())""",
        rem_exec_id, wi_id, cluster_id,
    )

    # 7. Run RemediationWorkflow — approve, apply, verify
    rem_activities = [
        emit_execution_event, mock_validate_ok, mock_apply_success,
        mock_verify_pass, mock_revalidate_binding,
    ]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=rem_activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id=rem_exec_id,
                approval_id=approval_id,
                cluster_id=cluster_id,
                binding_id=refs.get("binding_id", str(uuid.uuid4())),
                changeset_digest=changeset_digest,
                target_resources=refs.get("target_resources", []),
                plan_steps=plan_steps,
            ),
            id=f"pipeline-full-rem-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(
            RemediationWorkflow.approve,
            {"approver": "test-admin", "changeset_digest": changeset_digest},
        )
        rem_result = await handle.result()

    assert rem_result.status == "completed"
    assert rem_result.verification_passed is True

    # 8. Verify auto-complete: work_item → done, issue → resolved, execution → verified_fixed
    wi_final = await conn.fetchrow(
        "SELECT status FROM work_items WHERE id = $1::uuid", wi_id,
    )
    assert wi_final["status"] == "done", f"work_item should be 'done' but is '{wi_final['status']}'"

    issue_final = await conn.fetchrow(
        "SELECT status, resolved_by FROM issues WHERE id = $1::uuid", issue_id,
    )
    assert issue_final["status"] == "resolved", f"issue should be 'resolved' but is '{issue_final['status']}'"
    assert issue_final["resolved_by"] == "remediation"

    exec_final = await conn.fetchrow(
        "SELECT status, outcome FROM executions WHERE id = $1::uuid", rem_exec_id,
    )
    assert exec_final["status"] == "completed"
    assert exec_final["outcome"] == "verified_fixed"


# ---------------------------------------------------------------------------
# NEW: Pipeline with rejection
# ---------------------------------------------------------------------------


async def test_pipeline_with_rejection(
    conn: asyncpg.Connection,
    cluster_id: str,
    pool_patch: FakePool,
    workflow_env: WorkflowEnvironment,
) -> None:
    """Reject the approval → execution ends as 'rejected', work_item stays 'ready'."""
    issue_id, wi_id, rem_exec_id = await _seed_issue_work_item_execution(
        conn, cluster_id, execution_type="remediation",
    )

    rem_activities = [
        emit_execution_event, mock_validate_ok, mock_apply_success,
        mock_verify_pass, mock_revalidate_binding,
    ]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=rem_activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id=rem_exec_id,
                approval_id=str(uuid.uuid4()),
                cluster_id=cluster_id,
                binding_id=str(uuid.uuid4()),
                changeset_digest="test-digest",
                plan_steps=[{
                    "action": "scale", "resource": "deployment/web",
                    "namespace": "default", "params": {"replicas": 3},
                    "description": "Scale up",
                }],
            ),
            id=f"pipeline-reject-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(
            RemediationWorkflow.reject,
            {"reason": "Too risky for production"},
        )
        rem_result = await handle.result()

    assert rem_result.status == "rejected"

    # Verify: execution marked failed (rejection triggers failed transition via approval_rejected event)
    exec_row = await conn.fetchrow(
        "SELECT status FROM executions WHERE id = $1::uuid", rem_exec_id,
    )
    # The workflow emits approval_rejected → transitions to "failed"
    assert exec_row["status"] == "failed", f"execution should be 'failed' after rejection but is '{exec_row['status']}'"

    # Verify: work_item reset to 'ready' (transition_execution resets on failure)
    wi_row = await conn.fetchrow(
        "SELECT status FROM work_items WHERE id = $1::uuid", wi_id,
    )
    assert wi_row["status"] == "ready", f"work_item should be 'ready' after rejection but is '{wi_row['status']}'"

    # Verify: issue stays open
    issue_row = await conn.fetchrow(
        "SELECT status FROM issues WHERE id = $1::uuid", issue_id,
    )
    assert issue_row["status"] == "open"


# ---------------------------------------------------------------------------
# NEW: Pipeline with failed verification
# ---------------------------------------------------------------------------


async def test_pipeline_with_failed_verification(
    conn: asyncpg.Connection,
    cluster_id: str,
    pool_patch: FakePool,
    workflow_env: WorkflowEnvironment,
) -> None:
    """Approve + apply succeeds, but verification fails → no auto-complete."""
    issue_id, wi_id, rem_exec_id = await _seed_issue_work_item_execution(
        conn, cluster_id, execution_type="remediation",
    )

    # Use mock_verify_fail — returns passed=False on all attempts
    rem_activities = [
        emit_execution_event, mock_validate_ok, mock_apply_success,
        mock_verify_fail, mock_revalidate_binding,
    ]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=rem_activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id=rem_exec_id,
                approval_id=str(uuid.uuid4()),
                cluster_id=cluster_id,
                binding_id=str(uuid.uuid4()),
                changeset_digest="digest-fail-verify",
                target_resources=[{"kind": "Deployment", "name": "web"}],
                plan_steps=[{
                    "action": "patch", "resource": "deployment/web",
                    "namespace": "default", "params": {},
                    "description": "Patch web",
                }],
            ),
            id=f"pipeline-fail-verify-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        await handle.signal(
            RemediationWorkflow.approve,
            {"approver": "test-admin", "changeset_digest": "digest-fail-verify"},
        )
        rem_result = await handle.result()

    # Workflow completes but verification_passed is False
    assert rem_result.status == "completed"
    assert rem_result.verification_passed is False

    # The completed event has verification_passed=False, so auto-complete does NOT fire
    wi_row = await conn.fetchrow(
        "SELECT status FROM work_items WHERE id = $1::uuid", wi_id,
    )
    assert wi_row["status"] == "ready", f"work_item should remain 'ready' but is '{wi_row['status']}'"

    issue_row = await conn.fetchrow(
        "SELECT status FROM issues WHERE id = $1::uuid", issue_id,
    )
    assert issue_row["status"] == "open", f"issue should remain 'open' but is '{issue_row['status']}'"

    exec_row = await conn.fetchrow(
        "SELECT outcome FROM executions WHERE id = $1::uuid", rem_exec_id,
    )
    assert exec_row["outcome"] is None, "outcome should not be set when verification fails"


# ---------------------------------------------------------------------------
# NEW: Pipeline with approval timeout
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def time_skipping_env():
    """Separate time-skipping Temporal environment for timeout tests."""
    async with await WorkflowEnvironment.start_time_skipping() as env:
        yield env


async def test_pipeline_with_approval_timeout(
    conn: asyncpg.Connection,
    cluster_id: str,
    pool_patch: FakePool,
    time_skipping_env: WorkflowEnvironment,
) -> None:
    """Don't send approval signal → 4h timeout expires → timed_out.

    Uses time-skipping env so we don't actually wait 4 hours.
    """
    issue_id, wi_id, rem_exec_id = await _seed_issue_work_item_execution(
        conn, cluster_id, execution_type="remediation",
    )

    rem_activities = [
        emit_execution_event, mock_validate_ok, mock_apply_success,
        mock_verify_pass, mock_revalidate_binding,
    ]
    task_queue = f"test-pipeline-timeout-{uuid.uuid4().hex[:8]}"

    async with Worker(
        time_skipping_env.client, task_queue=task_queue,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=rem_activities,
    ):
        # Start workflow but do NOT send approve/reject signal
        rem_result = await time_skipping_env.client.execute_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id=rem_exec_id,
                approval_id=str(uuid.uuid4()),
                cluster_id=cluster_id,
                binding_id=str(uuid.uuid4()),
                changeset_digest="digest-timeout",
                plan_steps=[{
                    "action": "scale", "resource": "deployment/web",
                    "namespace": "default", "params": {"replicas": 3},
                    "description": "Scale up",
                }],
            ),
            id=f"pipeline-timeout-{uuid.uuid4()}",
            task_queue=task_queue,
        )

    assert rem_result.status == "timed_out"

    # Verify DB state
    exec_row = await conn.fetchrow(
        "SELECT status FROM executions WHERE id = $1::uuid", rem_exec_id,
    )
    assert exec_row["status"] == "timed_out", f"execution should be 'timed_out' but is '{exec_row['status']}'"

    # work_item should be reset to 'ready' (transition_execution resets on timed_out)
    wi_row = await conn.fetchrow(
        "SELECT status FROM work_items WHERE id = $1::uuid", wi_id,
    )
    assert wi_row["status"] == "ready", f"work_item should be 'ready' after timeout but is '{wi_row['status']}'"

    issue_row = await conn.fetchrow(
        "SELECT status FROM issues WHERE id = $1::uuid", issue_id,
    )
    assert issue_row["status"] == "open"
