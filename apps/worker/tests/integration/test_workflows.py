"""Temporal workflow integration tests using local dev server.

Activities are mocked — these tests verify workflow orchestration logic:
signal handling, timeouts, child workflow spawning, event emission.
"""

from __future__ import annotations

import uuid

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from pinky_worker.execution.activities import (
    EvidenceBundle,
    ExecutionEventPayload,
    InvestigationArtifact,
)
from pinky_worker.workflows.investigation import InvestigationInput, InvestigationResult, InvestigationWorkflow
from pinky_worker.workflows.remediation import RemediationInput, RemediationResult, RemediationWorkflow
from pinky_worker.workflows.verification import VerificationInput, VerificationResult, VerificationWorkflow

TASK_QUEUE = "test-workflows"

_emitted_events: list[ExecutionEventPayload] = []


# --- Mock Activities ---


@activity.defn(name="emit_execution_event")
async def mock_emit(event: ExecutionEventPayload) -> None:
    _emitted_events.append(event)


@activity.defn(name="gather_evidence")
async def mock_gather(issue_id: str, cluster_id: str, skill_tools: list[str] | None = None, execution_id: str = "") -> EvidenceBundle:
    return EvidenceBundle(
        issue_id=issue_id,
        cluster_id=cluster_id,
        fingerprint="fp-test",
        evidence_hash="hash-abc",
        sections={"status": "CrashLoopBackOff", "events": "OOMKilled"},
    )


@activity.defn(name="check_artifact_cache")
async def mock_cache_miss(evidence_hash: str, correlation_key: str) -> InvestigationArtifact | None:
    return None


_cached_artifact = InvestigationArtifact(
    artifact_id="cached-001",
    issue_id="i-1",
    summary="Cached result",
    root_cause="Known OOM",
    recommended_action="Increase memory limit",
    confidence=0.9,
    tool_calls=[],
    evidence_hash="hash-abc",
)


@activity.defn(name="check_artifact_cache")
async def mock_cache_hit(evidence_hash: str, correlation_key: str) -> InvestigationArtifact | None:
    return _cached_artifact


@activity.defn(name="run_investigation")
async def mock_run_investigation(evidence: EvidenceBundle, skill_body: str, execution_id: str = "") -> InvestigationArtifact:
    return InvestigationArtifact(
        artifact_id=str(uuid.uuid4()),
        issue_id=evidence.issue_id,
        summary="Pod is OOMKilled due to memory limit",
        root_cause="Container memory limit too low for workload",
        recommended_action="Increase memory limit to 512Mi",
        confidence=0.85,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
    )


@activity.defn(name="store_artifact")
async def mock_store(artifact: InvestigationArtifact) -> str:
    return artifact.artifact_id


@activity.defn(name="validate_approval")
async def mock_validate_valid(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": True}


@activity.defn(name="validate_approval")
async def mock_validate_invalid(approval_id: str, changeset_digest: str) -> dict:
    return {"valid": False, "reason": "approval_invalidated"}


@activity.defn(name="apply_change")
async def mock_apply(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    return {"status": "applied", "action": step.get("action", "")}


@activity.defn(name="verify_state")
async def mock_verify_pass(
    cluster_id: str, expected_state: dict, target_resources: list | None = None,
) -> dict:
    return {"passed": True, "details": {"total_pods": 5, "unhealthy_pods": 0}}


@activity.defn(name="verify_state")
async def mock_verify_fail(
    cluster_id: str, expected_state: dict, target_resources: list | None = None,
) -> dict:
    return {"passed": False, "details": {"total_pods": 5, "unhealthy_pods": 2}}


@activity.defn(name="revalidate_binding")
async def mock_revalidate_binding(binding_id: str) -> dict:
    return {"valid": True}


@pytest.fixture(autouse=True)
def _reset_events() -> None:
    _emitted_events.clear()


# --- Investigation Workflow ---


async def test_investigation_happy_path(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_gather, mock_cache_miss, mock_run_investigation, mock_store]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[InvestigationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id="issue-1",
                cluster_id="cluster-1",
                correlation_key="pod-health::ns/pod",
                evidence_hash="",
            ),
            id=f"test-inv-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert isinstance(result, InvestigationResult)
    assert result.summary == "Pod is OOMKilled due to memory limit"
    assert result.confidence == 0.85
    assert not result.cached

    event_types = [e.event_type for e in _emitted_events]
    assert "started" in event_types
    assert "completed" in event_types


async def test_investigation_cache_hit(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_gather, mock_cache_hit, mock_run_investigation, mock_store]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[InvestigationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            InvestigationWorkflow.run,
            InvestigationInput(
                issue_id="issue-1",
                cluster_id="cluster-1",
                correlation_key="pod-health::ns/pod",
                evidence_hash="hash-abc",
            ),
            id=f"test-inv-cache-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert result.cached is True
    assert result.artifact_id == "cached-001"
    assert result.summary == "Cached result"

    event_types = [e.event_type for e in _emitted_events]
    assert "started" in event_types
    assert "completed" in event_types


# --- Remediation Workflow ---


async def test_remediation_happy_path(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_validate_valid, mock_apply, mock_verify_pass, mock_revalidate_binding]
    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id="exec-1",
                approval_id=str(uuid.uuid4()),
                cluster_id="cluster-1",
                binding_id="bind-1",
                changeset_digest="digest-1",
                target_resources=[{"kind": "Deployment", "name": "web"}],
                plan_steps=[
                    {
                        "action": "scale",
                        "resource": "deployment/web",
                        "namespace": "default",
                        "params": {"replicas": 3},
                    },
                ],
            ),
            id=f"test-rem-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        await handle.signal(RemediationWorkflow.approve, {"approver": "admin", "changeset_digest": "digest-1"})
        result = await handle.result()

    assert isinstance(result, RemediationResult)
    assert result.status == "completed"
    assert result.verification_passed is True


async def test_remediation_rejected(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_validate_valid, mock_apply, mock_verify_pass, mock_revalidate_binding]
    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id="exec-1",
                approval_id=str(uuid.uuid4()),
                cluster_id="cluster-1",
                binding_id="bind-1",
                changeset_digest="digest-1",
                plan_steps=[{"action": "scale", "resource": "web", "namespace": "default"}],
            ),
            id=f"test-rem-rej-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        await handle.signal(RemediationWorkflow.reject, {"reason": "Too risky"})
        result = await handle.result()

    assert result.status == "rejected"


async def test_remediation_invalid_approval(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_validate_invalid, mock_apply, mock_verify_pass, mock_revalidate_binding]
    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id="exec-1",
                approval_id=str(uuid.uuid4()),
                cluster_id="cluster-1",
                binding_id="bind-1",
                changeset_digest="digest-1",
                plan_steps=[{"action": "scale", "resource": "web", "namespace": "default"}],
            ),
            id=f"test-rem-invalid-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        await handle.signal(RemediationWorkflow.approve, {"approver": "admin", "changeset_digest": "digest-1"})
        result = await handle.result()

    assert result.status == "approval_invalidated"
    assert result.verification_passed is None


async def test_remediation_multi_step_emits_progress(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_validate_valid, mock_apply, mock_verify_pass, mock_revalidate_binding]
    async with Worker(
        workflow_env.client,
        task_queue=TASK_QUEUE,
        workflows=[RemediationWorkflow, VerificationWorkflow],
        activities=activities,
    ):
        handle = await workflow_env.client.start_workflow(
            RemediationWorkflow.run,
            RemediationInput(
                execution_id="exec-1",
                approval_id=str(uuid.uuid4()),
                cluster_id="cluster-1",
                binding_id="bind-1",
                changeset_digest="digest-1",
                plan_steps=[
                    {"action": "scale", "resource": "web", "namespace": "default"},
                    {"action": "delete_pod", "resource": "web-abc123", "namespace": "default"},
                    {"action": "patch", "resource": "deployment/web", "namespace": "default"},
                ],
            ),
            id=f"test-rem-multi-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

        await handle.signal(RemediationWorkflow.approve, {"approver": "admin", "changeset_digest": "digest-1"})
        result = await handle.result()

    assert result.status == "completed"
    progress_events = [e for e in _emitted_events if e.event_type == "progress"]
    assert len(progress_events) == 3
    assert progress_events[0].payload["step"] == 1
    assert progress_events[2].payload["step"] == 3


# --- Verification Workflow ---


async def test_verification_passes(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_verify_pass]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[VerificationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            VerificationWorkflow.run,
            VerificationInput(execution_id="exec-1", cluster_id="cluster-1", delay_seconds=1),
            id=f"test-ver-pass-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert isinstance(result, VerificationResult)
    assert result.passed is True
    assert result.details["unhealthy_pods"] == 0

    event_types = [e.event_type for e in _emitted_events]
    assert "verified" in event_types


async def test_verification_fails(workflow_env: WorkflowEnvironment) -> None:
    activities = [mock_emit, mock_verify_fail]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[VerificationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            VerificationWorkflow.run,
            VerificationInput(execution_id="exec-1", cluster_id="cluster-1", delay_seconds=1),
            id=f"test-ver-fail-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert result.passed is False
    assert result.details["unhealthy_pods"] == 2

    event_types = [e.event_type for e in _emitted_events]
    assert "failed" in event_types


async def test_verification_retries_on_failure(workflow_env: WorkflowEnvironment) -> None:
    """Verification retries up to max_attempts, passing on second try."""
    call_count = 0

    @activity.defn(name="verify_state")
    async def mock_verify_pass_on_second(
        cluster_id: str, expected_state: dict, target_resources: list | None = None,
    ) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"passed": False, "details": {"total_pods": 3, "unhealthy_pods": 2}}
        return {"passed": True, "details": {"total_pods": 3, "unhealthy_pods": 0}}

    activities = [mock_emit, mock_verify_pass_on_second]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[VerificationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            VerificationWorkflow.run,
            VerificationInput(
                execution_id="exec-1", cluster_id="cluster-1",
                delay_seconds=1, max_attempts=3,
            ),
            id=f"test-ver-retry-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert result.passed is True
    assert call_count == 2

    event_types = [e.event_type for e in _emitted_events]
    assert "verified" in event_types


async def test_verification_exhausts_retries(workflow_env: WorkflowEnvironment) -> None:
    """Verification fails after exhausting all attempts."""
    activities = [mock_emit, mock_verify_fail]
    async with Worker(
        workflow_env.client, task_queue=TASK_QUEUE, workflows=[VerificationWorkflow], activities=activities,
    ):
        result = await workflow_env.client.execute_workflow(
            VerificationWorkflow.run,
            VerificationInput(
                execution_id="exec-1", cluster_id="cluster-1",
                delay_seconds=1, max_attempts=2,
            ),
            id=f"test-ver-exhaust-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert result.passed is False

    event_types = [e.event_type for e in _emitted_events]
    assert "failed" in event_types
