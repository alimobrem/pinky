"""Temporal activities — the building blocks of Brain workflows.

Each activity is a focused, retryable unit of work. Activities handle
evidence gathering, LLM reasoning, artifact storage, change application,
and event emission. They never carry raw credentials — the execution
context injects authenticated clients.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from temporalio import activity


@dataclass(frozen=True)
class EvidenceBundle:
    issue_id: str
    cluster_id: str
    fingerprint: str
    evidence_hash: str
    sections: dict[str, str] = field(default_factory=dict)
    resource_snapshots: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metrics: list[dict] = field(default_factory=list)
    truncated: bool = False
    gathered_at: str = ""


@dataclass(frozen=True)
class InvestigationArtifact:
    artifact_id: str
    issue_id: str
    summary: str
    root_cause: str
    recommended_action: str
    confidence: float
    tool_calls: list[str]
    evidence_hash: str
    created_at: str = ""


@dataclass(frozen=True)
class ExecutionEventPayload:
    execution_id: str
    event_type: str
    sequence: int
    payload: dict = field(default_factory=dict)
    occurred_at: str = ""


def compute_evidence_hash(sections: dict[str, str]) -> str:
    raw = json.dumps(sections, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


@activity.defn
async def gather_evidence(issue_id: str, cluster_id: str) -> EvidenceBundle:
    """Gather evidence from cluster using observer identity.

    Collects: pod status, events, resource specs, metrics.
    Applies redaction rules before returning.
    """
    # TODO: use tool definitions to gather evidence
    # TODO: apply redaction rules from definitions/redaction-rules/
    # TODO: enforce per-section size limits and truncation markers
    activity.heartbeat("gathering evidence")

    sections = {
        "status": "placeholder — connect to cluster observer",
        "events": "placeholder — fetch recent events",
    }

    return EvidenceBundle(
        issue_id=issue_id,
        cluster_id=cluster_id,
        fingerprint="",
        evidence_hash=compute_evidence_hash(sections),
        sections=sections,
        gathered_at=datetime.now(timezone.utc).isoformat(),
    )


@activity.defn
async def check_artifact_cache(evidence_hash: str, correlation_key: str) -> InvestigationArtifact | None:
    """Check if a valid cached investigation artifact exists for this evidence."""
    # TODO: query investigation artifacts by (correlation_key, evidence_hash)
    # TODO: return if exists and < 1 hour old
    return None


@activity.defn
async def run_investigation(evidence: EvidenceBundle, skill_body: str) -> InvestigationArtifact:
    """Run LLM-powered investigation using the matching skill definition.

    The skill_body is the markdown body from the skill definition —
    The Brain reads it as investigation instructions.
    """
    activity.heartbeat("running investigation")

    # TODO: construct prompt from skill body + evidence sections
    # TODO: call LLMRouter.complete() with ModelTier.REASONING
    # TODO: parse structured output into InvestigationArtifact
    # TODO: record token usage to analytics_events

    return InvestigationArtifact(
        artifact_id=str(uuid4()),
        issue_id=evidence.issue_id,
        summary="placeholder — LLM investigation not yet connected",
        root_cause="unknown",
        recommended_action="investigate manually",
        confidence=0.0,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@activity.defn
async def store_artifact(artifact: InvestigationArtifact) -> str:
    """Store investigation artifact in Postgres for reuse."""
    # TODO: insert into investigation_artifacts table
    # TODO: emit domain event investigation.completed
    return artifact.artifact_id


@activity.defn
async def emit_execution_event(event: ExecutionEventPayload) -> None:
    """Emit an execution event to Postgres and trigger SSE broadcast."""
    # TODO: insert into execution_events table
    # TODO: NOTIFY for SSE fan-out
    # TODO: log to analytics_events
    pass


@activity.defn
async def validate_approval(approval_id: str, changeset_digest: str) -> dict:
    """Validate that an approval is still valid (not expired, not invalidated by drift)."""
    # TODO: query approvals table
    # TODO: check expiry, check changeset_digest matches
    return {"valid": False, "reason": "approval validation not yet implemented"}


@activity.defn
async def apply_change(cluster_id: str, binding_id: str, step: dict) -> dict:
    """Apply a remediation step using the user's cluster identity.

    Never uses observer identity for writes. The binding_id resolves
    to the user's encrypted token, which is decrypted and used for
    this single operation.
    """
    activity.heartbeat(f"applying: {step.get('description', 'unknown step')}")

    # TODO: resolve user binding -> decrypt token -> create authenticated k8s client
    # TODO: execute the step (e.g., kubectl apply, scale, rollback)
    # TODO: emit execution event with step result
    return {"status": "not_implemented", "step": step}


@activity.defn
async def verify_state(cluster_id: str, expected_state: dict) -> dict:
    """Verify cluster state matches expected state after remediation."""
    # TODO: re-scan relevant resources using observer identity
    # TODO: compare against expected_state
    # TODO: return passed/failed with details
    return {"passed": False, "details": {"reason": "verification not yet implemented"}}


@activity.defn
async def project_to_postgres(execution_id: str, event_type: str, payload: dict) -> None:
    """Write idempotent projection to Postgres.

    Uses INSERT ... ON CONFLICT (execution_id, sequence) DO NOTHING
    to guarantee replay safety.
    """
    # TODO: upsert into work_items, executions, history_events
    # TODO: update projection_cursors
    pass
