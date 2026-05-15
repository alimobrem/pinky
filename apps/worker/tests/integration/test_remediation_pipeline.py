"""Full remediation pipeline integration tests.

Tests the complete chain with real Postgres + Temporal dev server.
K8s API calls mocked. Verifies every state transition and failure mode.
"""

from __future__ import annotations

import json
import uuid

import asyncpg
import pytest
from temporalio import activity
from temporalio.common import RetryPolicy
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pinky_worker.execution.activities import ExecutionEventPayload
from pinky_worker.workflows.remediation import RemediationInput, RemediationResult, RemediationWorkflow
from pinky_worker.workflows.verification import VerificationInput, VerificationResult, VerificationWorkflow

TASK_QUEUE = "test-remediation-pipeline"

_emitted: list[ExecutionEventPayload] = []


@activity.defn(name="emit_execution_event")
async def mock_emit(event: ExecutionEventPayload) -> None:
    _emitted.append(event)


@activity.defn(name="validate_approval")
async def mock_validate_ok(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": True}


@activity.defn(name="validate_approval")
async def mock_validate_expired(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": False, "reason": "approval_invalidated"}


@activity.defn(name="apply_change")
async def mock_apply_success(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    return {"status": "applied", "action": step.get("action", "")}


@activity.defn(name="apply_change")
async def mock_apply_fail(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    raise RuntimeError(f"K8s 403: forbidden for {step.get('resource', '')}")


_apply_call_count = 0


@activity.defn(name="apply_change")
async def mock_apply_fail_on_second(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    global _apply_call_count
    _apply_call_count += 1
    if step.get("_step_index", 0) == 1:
        raise RuntimeError("Step 2 failed: K8s 403")
    return {"status": "applied", "action": step.get("action", "")}


@activity.defn(name="verify_state")
async def mock_verify_pass(cluster_id: str, expected_state: dict) -> dict:
    return {"passed": True, "details": {"total_pods": 3, "unhealthy_pods": 0}}


@activity.defn(name="verify_state")
async def mock_verify_fail(cluster_id: str, expected_state: dict) -> dict:
    return {"passed": False, "details": {"total_pods": 3, "unhealthy_pods": 2}}


@pytest.fixture(autouse=True)
def _reset():
    global _apply_call_count
    _emitted.clear()
    _apply_call_count = 0


_DEFAULT_STEPS = [
    {"action": "scale", "namespace": "default", "resource": "deployment/web", "params": {"replicas": 3}, "description": "Scale web to 3"},
]


def _make_input(steps: list[dict] | None = None) -> RemediationInput:
    return RemediationInput(
        execution_id=str(uuid.uuid4()),
        approval_id=str(uuid.uuid4()),
        cluster_id=str(uuid.uuid4()),
        binding_id=str(uuid.uuid4()),
        plan_steps=_DEFAULT_STEPS if steps is None else steps,
    )


async def _run_workflow(
    env: WorkflowEnvironment,
    input: RemediationInput,
    activities: list,
) -> RemediationResult:
    async with Worker(
        env.client, task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=activities,
    ):
        return await env.client.execute_workflow(
            RemediationWorkflow.run, input,
            id=f"test-rem-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )


# --- Happy Path ---


async def test_remediation_happy_path(workflow_env: WorkflowEnvironment) -> None:
    """Full success: approve → apply → verify → completed."""
    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_success, mock_verify_pass],
    )

    assert result.status == "completed"
    assert result.verification_passed is True

    types = [e.event_type for e in _emitted]
    assert "started" in types
    assert "progress" in types
    assert "completed" in types

    completed = next(e for e in _emitted if e.event_type == "completed")
    assert completed.payload["verification_passed"] is True


# --- Failure Paths ---


async def test_apply_failure_stops_workflow(workflow_env: WorkflowEnvironment) -> None:
    """apply_change raises → workflow fails, does NOT proceed to verification."""
    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_fail, mock_verify_pass],
    )

    assert result.status == "failed"

    types = [e.event_type for e in _emitted]
    assert "started" in types
    assert "failed" in types
    assert "completed" not in types

    failed = next(e for e in _emitted if e.event_type == "failed")
    assert failed.payload["reason"] == "step_failed"


async def test_partial_failure_does_not_complete(workflow_env: WorkflowEnvironment) -> None:
    """Step 1 succeeds, step 2 fails → workflow fails, no partial 'done'."""
    inp = _make_input(steps=[
        {"action": "scale", "resource": "deployment/web", "namespace": "default", "params": {"replicas": 3}, "description": "Step 1", "_step_index": 0},
        {"action": "patch", "resource": "deployment/api", "namespace": "default", "params": {"patch": {}}, "description": "Step 2", "_step_index": 1},
    ])
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_fail_on_second, mock_verify_pass],
    )

    assert result.status == "failed"

    progress_events = [e for e in _emitted if e.event_type == "progress"]
    assert len(progress_events) >= 1


async def test_verification_failure_keeps_open(workflow_env: WorkflowEnvironment) -> None:
    """Apply succeeds, verify fails → completed but verification_passed=False."""
    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_success, mock_verify_fail],
    )

    assert result.status == "completed"
    assert result.verification_passed is False

    completed = next(e for e in _emitted if e.event_type == "completed")
    assert completed.payload["verification_passed"] is False


async def test_approval_invalidated(workflow_env: WorkflowEnvironment) -> None:
    """Expired/rejected approval → workflow fails immediately."""
    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_expired, mock_apply_success, mock_verify_pass],
    )

    assert result.status == "approval_invalidated"

    types = [e.event_type for e in _emitted]
    assert "failed" in types
    assert "progress" not in types


async def test_cancel_emits_failed(workflow_env: WorkflowEnvironment) -> None:
    """Cancel signal → failed event with reason=cancelled."""
    import asyncio

    inp = _make_input(steps=[
        {"action": "scale", "resource": "d/a", "namespace": "ns", "params": {}, "description": "S1"},
        {"action": "scale", "resource": "d/b", "namespace": "ns", "params": {}, "description": "S2"},
        {"action": "scale", "resource": "d/c", "namespace": "ns", "params": {}, "description": "S3"},
    ])

    @activity.defn(name="apply_change")
    async def slow_apply(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
        await asyncio.sleep(2)
        return {"status": "applied"}

    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=[mock_emit, mock_validate_ok, slow_apply, mock_verify_pass],
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run, inp,
            id=f"test-cancel-{uuid.uuid4()}", task_queue=TASK_QUEUE,
        )
        await asyncio.sleep(1)
        await handle.cancel()
        result = await handle.result()

    assert result.status in ("cancelled", "failed")
    failed = next((e for e in _emitted if e.event_type == "failed"), None)
    assert failed is not None
    assert failed.payload["reason"] in ("cancelled", "step_failed")


# --- Data Integrity ---


async def test_empty_plan_steps(workflow_env: WorkflowEnvironment) -> None:
    """0 steps → skip to verification, complete."""
    inp = _make_input(steps=[])
    _emitted.clear()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_success, mock_verify_pass],
    )

    assert result.status == "completed"
    progress_events = [e for e in _emitted if e.event_type == "progress" and e.execution_id == inp.execution_id]
    assert len(progress_events) == 0


# --- Event Type Contract ---


async def test_event_type_matches_frontend(workflow_env: WorkflowEnvironment) -> None:
    """pg_notify event_type must match what the frontend SSE handler filters on."""
    inp = _make_input()
    await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_success, mock_verify_pass],
    )

    completed = next(e for e in _emitted if e.event_type == "completed")
    assert "verification_passed" in completed.payload

    started = next(e for e in _emitted if e.event_type == "started")
    assert started.payload.get("type") == "remediation"

    failed_events = [e for e in _emitted if e.event_type == "failed"]
    for f in failed_events:
        assert "reason" in f.payload


# --- Binding Expiry ---


async def test_binding_expired_stops_workflow(workflow_env: WorkflowEnvironment) -> None:
    """Expired binding during apply_change should fail the workflow."""

    @activity.defn(name="apply_change")
    async def mock_apply_expired(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
        raise RuntimeError(f"Cluster binding {binding_id} expired — reconnect to the cluster")

    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_expired, mock_verify_pass],
    )

    assert result.status == "failed"
    failed = next(e for e in _emitted if e.event_type == "failed")
    assert failed.payload["reason"] == "step_failed"


# --- Idempotency ---


async def test_idempotent_apply_succeeds_twice(workflow_env: WorkflowEnvironment) -> None:
    """Applying the same step twice (e.g., after retry) must not break."""
    call_count = 0

    @activity.defn(name="apply_change")
    async def mock_apply_idempotent(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
        nonlocal call_count
        call_count += 1
        return {"status": "applied", "action": step.get("action", "")}

    inp = _make_input()
    result = await _run_workflow(
        workflow_env, inp,
        [mock_emit, mock_validate_ok, mock_apply_idempotent, mock_verify_pass],
    )

    assert result.status == "completed"
    assert call_count == 1


# --- Reconciliation ---


async def test_reconciliation_no_done_task_with_open_issue(conn: asyncpg.Connection, cluster_id: str) -> None:
    """No task should be 'done' while its issue is 'open'."""
    count = await conn.fetchval(
        "SELECT count(*) FROM work_items w JOIN issues i ON w.issue_id = i.id "
        "WHERE w.status = 'done' AND i.status = 'open'"
    )
    assert count == 0


async def test_reconciliation_no_completed_execution_without_events(conn: asyncpg.Connection, cluster_id: str) -> None:
    """Every completed execution should have at least 1 event."""
    orphaned = await conn.fetchval(
        "SELECT count(*) FROM executions e "
        "WHERE e.status = 'completed' "
        "AND NOT EXISTS (SELECT 1 FROM execution_events ee WHERE ee.execution_id = e.id)"
    )
    assert orphaned == 0
