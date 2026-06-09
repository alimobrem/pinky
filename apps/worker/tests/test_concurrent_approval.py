"""Chaos tests: concurrent approval signals on RemediationWorkflow.

Verifies that multiple simultaneous approve/reject signals don't crash
the workflow, don't cause duplicate apply_change calls, and always
produce a deterministic terminal state.

Requires: temporal CLI on PATH (brew install temporal).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pinky_worker.execution.activities import ExecutionEventPayload
from pinky_worker.workflows.remediation import (
    RemediationInput,
    RemediationResult,
    RemediationWorkflow,
)
from pinky_worker.workflows.verification import (
    VerificationInput,
    VerificationResult,
    VerificationWorkflow,
)

TASK_QUEUE = "test-concurrent-approval"

# ---------------------------------------------------------------------------
# Temporal dev-server fixture (same pattern as integration/conftest.py)
# ---------------------------------------------------------------------------

TEMPORAL_PATH = shutil.which("temporal") or os.environ.get("TEMPORAL_PATH", "")


@pytest.fixture(scope="module")
def _check_temporal() -> None:
    if not TEMPORAL_PATH:
        pytest.skip("temporal CLI not found — install via `brew install temporal`")


@pytest.fixture(scope="module")
async def workflow_env(_check_temporal: None):
    async with await WorkflowEnvironment.start_local(
        dev_server_existing_path=TEMPORAL_PATH,
        dev_server_log_level="error",
    ) as env:
        yield env


# ---------------------------------------------------------------------------
# Mock activities — track call counts for assertions
# ---------------------------------------------------------------------------

_emitted_events: list[ExecutionEventPayload] = []
_apply_call_count: int = 0


@activity.defn(name="emit_execution_event")
async def mock_emit(event: ExecutionEventPayload) -> None:
    _emitted_events.append(event)


@activity.defn(name="validate_approval")
async def mock_validate_ok(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": True}


@activity.defn(name="apply_change")
async def mock_apply(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    global _apply_call_count
    _apply_call_count += 1
    return {"status": "applied", "action": step.get("action", "")}


@activity.defn(name="verify_state")
async def mock_verify_pass(
    cluster_id: str, expected_state: dict, target_resources: list | None = None,
) -> dict:
    return {"passed": True, "details": {"total_pods": 3, "unhealthy_pods": 0}}


@activity.defn(name="revalidate_binding")
async def mock_revalidate_ok(binding_id: str) -> dict:
    return {"valid": True}


@pytest.fixture(autouse=True)
def _reset():
    global _apply_call_count
    _emitted_events.clear()
    _apply_call_count = 0


def _make_input() -> RemediationInput:
    return RemediationInput(
        execution_id=str(uuid.uuid4()),
        approval_id=str(uuid.uuid4()),
        cluster_id=str(uuid.uuid4()),
        binding_id=str(uuid.uuid4()),
        changeset_digest="digest-chaos",
        target_resources=[{"kind": "Deployment", "name": "web"}],
        plan_steps=[
            {
                "action": "scale",
                "namespace": "default",
                "resource": "deployment/web",
                "params": {"replicas": 3},
                "description": "Scale web to 3",
            },
        ],
    )


ALL_ACTIVITIES = [mock_emit, mock_validate_ok, mock_apply, mock_verify_pass, mock_revalidate_ok]


# ---------------------------------------------------------------------------
# Test 1: 10 concurrent approve signals — only one apply_change execution
# ---------------------------------------------------------------------------


async def test_concurrent_approve_signals(workflow_env: WorkflowEnvironment) -> None:
    """Fire 10 approve signals concurrently. Workflow must complete normally
    and apply_change must be called exactly once (not 10 times)."""

    inp = _make_input()

    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=ALL_ACTIVITIES,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            inp,
            id=f"chaos-concurrent-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        # No asyncio.sleep here — Temporal buffers signals even if the workflow
        # hasn't reached wait_condition yet, and asyncio.sleep disrupts the
        # dev server's time-skipping (causing workflow.sleep to block in real time).

        # Fire 10 approve signals concurrently
        signals = [
            handle.signal(
                RemediationWorkflow.approve,
                {"approver": f"user-{i}", "changeset_digest": inp.changeset_digest},
            )
            for i in range(10)
        ]
        await asyncio.gather(*signals)

        result = await handle.result()

    assert isinstance(result, RemediationResult)
    assert result.status == "completed", f"Expected 'completed' but got '{result.status}'"
    assert result.verification_passed is True

    # The critical assertion: apply_change was called exactly once per plan step,
    # not once per signal.
    assert _apply_call_count == 1, (
        f"apply_change called {_apply_call_count} times — expected exactly 1. "
        "Multiple approve signals must not trigger duplicate executions."
    )

    # Workflow emitted exactly one 'completed' event
    completed_events = [e for e in _emitted_events if e.event_type == "completed"]
    assert len(completed_events) == 1


# ---------------------------------------------------------------------------
# Test 2: approve and reject fired simultaneously — deterministic outcome
# ---------------------------------------------------------------------------


async def test_approve_and_reject_race(workflow_env: WorkflowEnvironment) -> None:
    """Send approve and reject at the same instant. Workflow must finish in
    exactly one of 'completed' or 'rejected' — no crash, no stuck state."""

    inp = _make_input()

    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=ALL_ACTIVITIES,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            inp,
            id=f"chaos-race-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        # Fire approve and reject simultaneously
        await asyncio.gather(
            handle.signal(
                RemediationWorkflow.approve,
                {"approver": "admin", "changeset_digest": inp.changeset_digest},
            ),
            handle.signal(
                RemediationWorkflow.reject,
                {"reason": "Changed my mind"},
            ),
        )

        result = await handle.result()

    assert isinstance(result, RemediationResult)
    # Exactly one terminal state — whichever signal was processed first wins
    assert result.status in ("completed", "rejected"), (
        f"Unexpected status '{result.status}' — "
        "approve/reject race must resolve to 'completed' or 'rejected'"
    )

    if result.status == "completed":
        # Approve won the race: apply_change ran, verification ran
        assert result.verification_passed is True
        assert _apply_call_count == 1
    else:
        # Reject won the race: no apply_change should have been called
        assert _apply_call_count == 0


# ---------------------------------------------------------------------------
# Test 3: approve barrage with multi-step plan — steps still run exactly once
# ---------------------------------------------------------------------------


async def test_concurrent_approve_multi_step(workflow_env: WorkflowEnvironment) -> None:
    """Same as test 1 but with 3 plan steps. Each step must execute exactly once."""

    inp = RemediationInput(
        execution_id=str(uuid.uuid4()),
        approval_id=str(uuid.uuid4()),
        cluster_id=str(uuid.uuid4()),
        binding_id=str(uuid.uuid4()),
        changeset_digest="digest-multi",
        target_resources=[{"kind": "Deployment", "name": "web"}],
        plan_steps=[
            {"action": "scale", "resource": "deployment/web", "namespace": "default", "params": {"replicas": 3}, "description": "Step 1"},
            {"action": "patch", "resource": "deployment/web", "namespace": "default", "params": {}, "description": "Step 2"},
            {"action": "restart", "resource": "deployment/web", "namespace": "default", "params": {}, "description": "Step 3"},
        ],
    )

    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=ALL_ACTIVITIES,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            inp,
            id=f"chaos-multi-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        signals = [
            handle.signal(
                RemediationWorkflow.approve,
                {"approver": f"user-{i}", "changeset_digest": inp.changeset_digest},
            )
            for i in range(10)
        ]
        await asyncio.gather(*signals)

        result = await handle.result()

    assert result.status == "completed"
    assert result.verification_passed is True

    # 3 steps, each called exactly once
    assert _apply_call_count == 3, (
        f"apply_change called {_apply_call_count} times — expected 3 (one per step). "
        "Concurrent signals must not multiply step executions."
    )

    progress_events = [e for e in _emitted_events if e.event_type == "progress"]
    assert len(progress_events) == 3
