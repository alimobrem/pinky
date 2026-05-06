"""Full pipeline integration test.

Tests the complete chain: fake K8s pods → scanner detects issue →
Temporal workflow runs investigation (mocked LLM) → artifact stored.

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
from pinky_worker.observation.generic_scanner import run_generic_checks
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


@activity.defn(name="gather_evidence")
async def mock_gather(issue_id: str, cluster_id: str, skill_tools: list[str] | None = None, execution_id: str = "") -> EvidenceBundle:
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
async def mock_investigate(evidence: EvidenceBundle, skill_body: str, execution_id: str = "") -> InvestigationArtifact:
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


@pytest.fixture(autouse=True)
def _reset():
    _emitted.clear()


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
