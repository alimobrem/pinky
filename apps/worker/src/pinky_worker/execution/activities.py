"""Temporal activities — the building blocks of Brain workflows.

Each activity is a focused, retryable unit of work. Activities handle
evidence gathering, LLM reasoning, artifact storage, change application,
and event emission. They never carry raw credentials — the execution
context injects authenticated clients.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from temporalio import activity

logger = logging.getLogger(__name__)


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
    """Gather evidence from cluster using observer identity."""
    activity.heartbeat("gathering evidence")

    from pinky_worker.observation.k8s_client import create_client, list_pods, list_events
    from pinky_worker.llm.redaction import redact_evidence_sections

    try:
        k8s = await create_client()
        pods = await list_pods(k8s)
        events = await list_events(k8s, limit=50)
        await k8s.close()

        sections = {
            "pods": json.dumps(pods[:20], indent=2, default=str),
            "events": json.dumps(events[:20], indent=2, default=str),
            "cluster_id": cluster_id,
            "issue_id": issue_id,
        }
    except Exception:
        logger.exception("failed to gather evidence from cluster")
        sections = {
            "error": "Failed to connect to cluster — using cached data if available",
            "cluster_id": cluster_id,
            "issue_id": issue_id,
        }

    redacted = redact_evidence_sections(sections)

    return EvidenceBundle(
        issue_id=issue_id,
        cluster_id=cluster_id,
        fingerprint="",
        evidence_hash=compute_evidence_hash(redacted),
        sections=redacted,
        gathered_at=datetime.now(timezone.utc).isoformat(),
    )


@activity.defn
async def check_artifact_cache(evidence_hash: str, correlation_key: str) -> InvestigationArtifact | None:
    """Check if a valid cached investigation artifact exists."""
    from pinky_worker.db import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT payload FROM execution_events
           WHERE event_type = 'investigation_completed'
           AND payload->>'evidence_hash' = $1
           AND occurred_at > $2
           ORDER BY occurred_at DESC LIMIT 1""",
        evidence_hash,
        datetime.now(timezone.utc) - timedelta(hours=1),
    )

    if row is None:
        return None

    data = json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]
    logger.info("cache hit: %s", evidence_hash)
    return InvestigationArtifact(
        artifact_id=data.get("artifact_id", str(uuid4())),
        issue_id=data.get("issue_id", ""),
        summary=data.get("summary", ""),
        root_cause=data.get("root_cause", ""),
        recommended_action=data.get("recommended_action", ""),
        confidence=data.get("confidence", 0.0),
        tool_calls=data.get("tool_calls", []),
        evidence_hash=evidence_hash,
        created_at=data.get("created_at", ""),
    )


@activity.defn
async def run_investigation(evidence: EvidenceBundle, skill_body: str) -> InvestigationArtifact:
    """Run LLM-powered investigation using the matching skill definition."""
    activity.heartbeat("running investigation")

    from pinky_worker.llm.vertex_provider import VertexProvider
    from pinky_worker.llm.provider import LLMRequest, LLMRouter, ModelTier
    from pinky_worker.llm.redaction import redact_evidence_sections

    redacted = redact_evidence_sections(evidence.sections)
    evidence_text = "\n\n".join(f"## {k}\n{v}" for k, v in redacted.items())

    messages = [
        {
            "role": "system",
            "content": (
                "You are The Brain, an SRE agent embedded in Pinky. "
                "Investigate the issue using the skill instructions and evidence below. "
                "Respond with a structured analysis: summary, root_cause, recommended_action, confidence (0-1)."
            ),
        },
        {
            "role": "user",
            "content": f"# Skill Instructions\n\n{skill_body}\n\n# Evidence\n\n{evidence_text}",
        },
    ]

    router = LLMRouter()
    router.register(VertexProvider())

    response = await router.complete(LLMRequest(
        messages=messages,
        model_tier=ModelTier.REASONING,
        max_tokens=2048,
    ))

    activity.heartbeat("parsing response")

    return InvestigationArtifact(
        artifact_id=str(uuid4()),
        issue_id=evidence.issue_id,
        summary=response.content[:500],
        root_cause=response.content,
        recommended_action="See investigation summary",
        confidence=0.7,
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@activity.defn
async def store_artifact(artifact: InvestigationArtifact) -> str:
    """Store investigation artifact as an execution event for caching."""
    from pinky_worker.db import get_pool

    pool = await get_pool()
    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT DO NOTHING""",
        uuid4(), UUID(artifact.artifact_id), "investigation_completed", 999,
        json.dumps({
            "artifact_id": artifact.artifact_id,
            "issue_id": artifact.issue_id,
            "summary": artifact.summary,
            "root_cause": artifact.root_cause,
            "recommended_action": artifact.recommended_action,
            "confidence": artifact.confidence,
            "evidence_hash": artifact.evidence_hash,
            "tool_calls": artifact.tool_calls,
            "created_at": artifact.created_at,
        }),
        datetime.now(timezone.utc),
    )
    logger.info("artifact stored: %s", artifact.artifact_id)
    return artifact.artifact_id


@activity.defn
async def emit_execution_event(event: ExecutionEventPayload) -> None:
    """Emit an execution event to Postgres and trigger SSE broadcast."""
    from pinky_worker.db import get_pool

    pool = await get_pool()
    occurred = datetime.now(timezone.utc)

    exec_id_str = event.execution_id or ""
    try:
        exec_uuid = UUID(exec_id_str)
    except ValueError:
        if exec_id_str.startswith("investigation-"):
            exec_uuid = UUID(exec_id_str.removeprefix("investigation-"))
        else:
            exec_uuid = uuid4()

    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT DO NOTHING""",
        uuid4(), exec_uuid,
        event.event_type, event.sequence,
        json.dumps(event.payload), occurred,
    )

    try:
        await pool.execute(
            "SELECT pg_notify($1, $2)",
            "pinky_watch",
            json.dumps({"event_type": event.event_type, "execution_id": event.execution_id}),
        )
    except Exception:
        logger.debug("NOTIFY skipped in execution event emission")

    logger.info("execution event emitted: %s %s", event.event_type, event.execution_id)


@activity.defn
async def validate_approval(approval_id: str, changeset_digest: str) -> dict:
    """Validate that an approval is still valid."""
    from pinky_worker.db import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT status, expires_at, changeset_digest FROM approvals WHERE id = $1""",
        UUID(approval_id),
    )

    if row is None:
        return {"valid": False, "reason": "approval not found"}

    if row["status"] != "pending":
        return {"valid": False, "reason": f"approval status is {row['status']}"}

    if row["expires_at"] and row["expires_at"] < datetime.now(timezone.utc):
        return {"valid": False, "reason": "approval expired"}

    if changeset_digest and row["changeset_digest"] != changeset_digest:
        return {"valid": False, "reason": "changeset changed since approval was granted"}

    return {"valid": True}


@activity.defn
async def apply_change(cluster_id: str, binding_id: str, step: dict) -> dict:
    """Apply a remediation step using the user's cluster identity."""
    action = step.get("action", "")
    namespace = step.get("namespace", "default")
    resource = step.get("resource", "")
    params = step.get("params", {})
    description = step.get("description", f"{action} {resource}")

    activity.heartbeat(f"applying: {description}")

    from pinky_worker.observation.k8s_client import (
        create_client, scale_deployment, delete_pod, patch_resource, rollback_deployment,
    )

    try:
        k8s = await create_client()

        if action == "scale":
            name = resource.split("/")[-1] if "/" in resource else resource
            replicas = params.get("replicas", 1)
            result = await scale_deployment(k8s, namespace, name, replicas)
        elif action == "delete_pod":
            name = resource.split("/")[-1] if "/" in resource else resource
            result = await delete_pod(k8s, namespace, name)
        elif action == "patch":
            parts = resource.split("/")
            kind = parts[0] if len(parts) > 1 else "deployment"
            name = parts[-1]
            result = await patch_resource(k8s, namespace, kind, name, params.get("patch", {}))
        elif action == "rollback":
            name = resource.split("/")[-1] if "/" in resource else resource
            result = await rollback_deployment(k8s, namespace, name)
        else:
            result = {"status": "unsupported", "action": action}
            logger.warning("unsupported apply_change action: %s", action)

        await k8s.close()
        result["applied_at"] = datetime.now(timezone.utc).isoformat()
        return result

    except Exception as e:
        logger.exception("apply_change failed for cluster %s", cluster_id)
        return {"status": "failed", "action": action, "resource": resource, "error": str(e)}


@activity.defn
async def verify_state(cluster_id: str, expected_state: dict) -> dict:
    """Verify cluster state matches expected state after remediation."""
    from pinky_worker.observation.k8s_client import create_client, list_pods

    try:
        k8s = await create_client()
        pods = await list_pods(k8s)
        await k8s.close()

        unhealthy = [p for p in pods if any(
            (c.get("state") or {}).get("type") == "waiting"
            for c in p.get("containers", [])
        )]

        passed = len(unhealthy) == 0 or len(unhealthy) <= expected_state.get("max_unhealthy", 0)

        return {
            "passed": passed,
            "details": {
                "total_pods": len(pods),
                "unhealthy_pods": len(unhealthy),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            },
        }
    except Exception as e:
        logger.exception("verify_state failed")
        return {"passed": False, "details": {"error": str(e)}}


@activity.defn
async def project_to_postgres(execution_id: str, event_type: str, payload: dict) -> None:
    """Write idempotent projection to Postgres."""
    from pinky_worker.db import get_pool

    pool = await get_pool()

    if event_type == "started":
        await pool.execute(
            """UPDATE executions SET status = 'running', started_at = $2 WHERE id = $1""",
            UUID(execution_id), datetime.now(timezone.utc),
        )
    elif event_type == "completed":
        await pool.execute(
            """UPDATE executions SET status = 'completed', completed_at = $2 WHERE id = $1""",
            UUID(execution_id), datetime.now(timezone.utc),
        )
    elif event_type == "failed":
        await pool.execute(
            """UPDATE executions SET status = 'failed', completed_at = $2 WHERE id = $1""",
            UUID(execution_id), datetime.now(timezone.utc),
        )

    await pool.execute(
        """INSERT INTO history_events (id, aggregate_type, aggregate_id, event_type, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6)""",
        uuid4(), "execution", UUID(execution_id), event_type,
        json.dumps(payload), datetime.now(timezone.utc),
    )

    logger.info("projected to postgres: %s %s", execution_id, event_type)
