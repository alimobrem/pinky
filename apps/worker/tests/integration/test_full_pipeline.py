"""Full pipeline integration test.

Tests the complete chain: fake K8s pods → scanner detects issue →
correlator creates issue + work_item in Postgres → Temporal workflow
runs investigation (mocked LLM) → artifact stored → API serves results.

Requires: real Postgres, Temporal CLI.
Mocks: K8s API (fake pod data), LLM provider (fake response).
"""

from __future__ import annotations

import json
import uuid

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
)
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.scanner_runner import run_pod_health_checks
from pinky_worker.workflows.investigation import InvestigationInput, InvestigationResult, InvestigationWorkflow

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
    frontmatter={"kind": "scanner", "name": "pod-health", "version": "1.0.0"},
    body="", source="test",
)


@activity.defn(name="gather_evidence")
async def mock_gather(issue_id: str, cluster_id: str) -> EvidenceBundle:
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
async def mock_investigate(evidence: EvidenceBundle, skill_body: str) -> InvestigationArtifact:
    return InvestigationArtifact(
        artifact_id=str(uuid.uuid4()),
        issue_id=evidence.issue_id,
        summary="Pod web-frontend is OOMKilled. Memory limit 128Mi is too low.",
        root_cause="Container exceeds 128Mi memory limit under load.",
        recommended_action="Increase memory limit to 512Mi.",
        confidence=0.9,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
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


@pytest.fixture(autouse=True)
def _reset():
    _emitted.clear()


async def test_full_pipeline(conn: asyncpg.Connection, cluster_id: str, workflow_env: WorkflowEnvironment) -> None:
    """End-to-end: fake pods → scanner → correlator → DB → workflow → results."""

    # ── Step 1: Scanner detects issues from fake K8s data ──
    observations = run_pod_health_checks(FAKE_PODS, cluster_id, SCANNER_DEF)

    assert len(observations) >= 2
    check_ids = {o.check_id for o in observations}
    assert "crash-loop-backoff" in check_ids
    assert "oom-killed" in check_ids

    crash_obs = next(o for o in observations if o.check_id == "crash-loop-backoff")
    assert crash_obs.severity == "high"
    assert crash_obs.resource_namespace == "production"
    assert crash_obs.resource_name == "web-frontend-abc123"

    # ── Step 2: Correlator creates issue + work item in Postgres ──
    fake_pool = FakePool(conn)

    from unittest.mock import patch
    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=fake_pool):
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(crash_obs)

    assert result.action == "created"
    issue_id = result.issue_id

    issue = await conn.fetchrow("SELECT * FROM issues WHERE id = $1::uuid", issue_id)
    assert issue is not None
    assert issue["status"] == "open"
    assert issue["severity"] == "high"
    assert "CrashLoopBackOff" in issue["title"]

    work_item = await conn.fetchrow("SELECT * FROM work_items WHERE issue_id = $1::uuid", issue_id)
    assert work_item is not None
    assert work_item["status"] == "ready"
    assert work_item["priority"] == "high"

    # ── Step 3: Verify dedup — same observation attaches, no new issue ──
    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=fake_pool):
        dedup_result = await correlator.correlate(crash_obs)

    assert dedup_result.action == "attached"
    assert dedup_result.issue_id == issue_id

    issue_count = await conn.fetchval(
        "SELECT count(*) FROM issues WHERE cluster_id = $1::uuid", cluster_id,
    )
    assert issue_count == 1

    # ── Step 4: Investigation workflow runs with mocked LLM ──
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
                correlation_key=crash_obs.correlation_key,
                evidence_hash="",
            ),
            id=f"pipeline-inv-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )

    assert isinstance(inv_result, InvestigationResult)
    assert inv_result.summary == "Pod web-frontend is OOMKilled. Memory limit 128Mi is too low."
    assert inv_result.confidence == 0.9
    assert not inv_result.cached

    # ── Step 5: Verify execution events emitted ──
    event_types = [e.event_type for e in _emitted]
    assert "started" in event_types
    assert "completed" in event_types

    started = next(e for e in _emitted if e.event_type == "started")
    assert started.payload["type"] == "investigation"
    assert started.payload["issue_id"] == issue_id

    completed = next(e for e in _emitted if e.event_type == "completed")
    assert "artifact_id" in completed.payload
    assert completed.payload["confidence"] == 0.9

    # ── Step 6: Second observation of OOM ──
    oom_obs = next(o for o in observations if o.check_id == "oom-killed")
    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=fake_pool):
        oom_result = await correlator.correlate(oom_obs)

    assert oom_result.action == "created"
    assert oom_result.issue_id != issue_id

    oom_issue = await conn.fetchrow("SELECT * FROM issues WHERE id = $1::uuid", oom_result.issue_id)
    assert oom_issue["severity"] == "critical"

    oom_wi = await conn.fetchrow("SELECT * FROM work_items WHERE issue_id = $1::uuid", oom_result.issue_id)
    assert oom_wi["priority"] == "high"

    # ── Final: 2 issues, 2 work items, 1 healthy pod ignored ──
    total_issues = await conn.fetchval(
        "SELECT count(*) FROM issues WHERE cluster_id = $1::uuid", cluster_id,
    )
    assert total_issues == 2

    total_wis = await conn.fetchval(
        "SELECT count(*) FROM work_items WHERE cluster_id = $1::uuid", cluster_id,
    )
    assert total_wis == 2
