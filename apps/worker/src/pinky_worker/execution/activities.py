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
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
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
    issue_title: str = ""
    resource_namespace: str = ""
    resource_name: str = ""
    resource_kind: str = ""


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
    execution_id: str = ""
    system_prompt: str = ""
    skill_used: str = ""
    prompt_version: str = ""
    remediation_steps: list[dict] = field(default_factory=list)
    manual_commands: list[str] = field(default_factory=list)


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


async def _emit_event(
    pool: Any, execution_id: str, event_type: str, seq: int, payload: dict,
) -> None:
    if not execution_id:
        return
    try:
        await pool.execute(
            """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
               VALUES ($1, $2, $3, $4, $5, $6)
               ON CONFLICT DO NOTHING""",
            uuid4(), UUID(execution_id), event_type, seq,
            json.dumps(payload), datetime.now(UTC),
        )
        notify = json.dumps({"event_type": event_type, "execution_id": execution_id})
        await pool.execute("SELECT pg_notify($1, $2)", "pinky_watch", notify)
        await pool.execute("SELECT pg_notify($1, $2)", f"pinky_execution_{execution_id}", notify)
    except Exception:
        logger.debug("%s event emission skipped", event_type)


async def _emit_tool_event(pool: Any, execution_id: str, tool_name: str, seq: int) -> None:
    await _emit_event(pool, execution_id, "tool_used", seq, {"tool_name": tool_name})


def _build_oc_command(action: str, kind: str, name: str, namespace: str, params: dict) -> str:
    if action == "scale":
        return f"oc scale {kind} {name} -n {namespace} --replicas={params.get('replicas', 1)}"
    if action == "patch":
        patch = json.dumps(params.get("patch", {}))
        return f"oc patch {kind} {name} -n {namespace} -p '{patch}'"
    if action == "delete_pod":
        return f"oc delete pod {name} -n {namespace}"
    if action == "rollback":
        return f"oc rollout undo {kind}/{name} -n {namespace}"
    return f"oc {action} {kind}/{name} -n {namespace}"


async def _emit_command_event(
    pool: Any, execution_id: str, seq: int, command: str, output: str, exit_code: int,
    action: str, resource: str,
) -> None:
    await _emit_event(pool, execution_id, "command", seq, {
        "command": command, "output": output, "exit_code": exit_code,
        "action": action, "resource": resource,
    })


@activity.defn
async def gather_evidence(
    issue_id: str, cluster_id: str, skill_tools: list[str] | None = None,
    execution_id: str = "",
) -> EvidenceBundle:
    """Gather evidence from cluster using observer identity.

    When *skill_tools* is provided, additional tool-specific evidence is
    collected (pod logs, metrics, describe, rollout status, helm releases).
    """
    activity.heartbeat("gathering evidence")

    from pinky_worker.db import get_pool
    from pinky_worker.llm.redaction import redact_evidence_sections
    from pinky_worker.observation.k8s_client import (
        create_client,
        describe_resource,
        get_helm_releases,
        get_pod_logs,
        get_rollout_status,
        get_top_nodes,
        get_top_pods,
        list_events,
        list_pods,
    )

    pool = await get_pool()
    wi = await pool.fetchrow(
        "SELECT title, labels FROM work_items WHERE issue_id = $1::uuid LIMIT 1",
        issue_id,
    )

    issue_title = ""
    resource_namespace = ""
    resource_name = ""
    resource_kind = "pod"
    if wi:
        issue_title = wi["title"] or ""
        if wi["labels"]:
            labels = json.loads(wi["labels"]) if isinstance(wi["labels"], str) else wi["labels"]
            resource_namespace = labels.get("namespace", "")
            resource_name = labels.get("name", "")
            resource_kind = labels.get("kind", "pod")
        if not resource_name and issue_title:
            import re
            m = re.match(r"(\w+)\s+(\S+)/(\S+)\s+", issue_title)
            if m:
                resource_kind = m.group(1).lower()
                resource_namespace = resource_namespace or m.group(2)
                resource_name = m.group(3)

    try:
        k8s = await create_client()
        pods = await list_pods(k8s, namespace=resource_namespace)
        events = await list_events(k8s, namespace=resource_namespace, limit=50)

        sections: dict[str, str] = {
            "cluster_id": cluster_id,
            "issue_id": issue_id,
            "issue_title": issue_title,
        }
        if resource_name:
            target_pods = [p for p in pods if p.get("name") == resource_name]
            other_pods = [p for p in pods if p.get("name") != resource_name]
            sections["target_resource"] = json.dumps(target_pods, indent=2, default=str)
            sections["namespace_pods"] = json.dumps(other_pods[:10], indent=2, default=str)
        else:
            sections["pods"] = json.dumps(pods[:20], indent=2, default=str)
        sections["events"] = json.dumps(events[:20], indent=2, default=str)

        # ----- skill-aware evidence -----
        tool_seq = 100
        if skill_tools:

            if "kubectl-logs" in skill_tools and resource_namespace and resource_name:
                current_logs = await get_pod_logs(k8s, resource_namespace, resource_name)
                previous_logs = await get_pod_logs(
                    k8s, resource_namespace, resource_name, previous=True,
                )
                if current_logs:
                    sections["pod_logs"] = current_logs
                if previous_logs:
                    sections["pod_logs_previous"] = previous_logs
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "kubectl-logs", tool_seq)

            if "kubectl-top" in skill_tools:
                top_pods = await get_top_pods(k8s, resource_namespace)
                top_nodes = await get_top_nodes(k8s)
                if top_pods:
                    sections["resource_usage_pods"] = json.dumps(top_pods, default=str)
                if top_nodes:
                    sections["resource_usage_nodes"] = json.dumps(top_nodes, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "kubectl-top", tool_seq)

            if "kubectl-describe" in skill_tools and resource_namespace and resource_name:
                detail = await describe_resource(k8s, resource_kind, resource_namespace, resource_name)
                if detail:
                    sections["resource_detail"] = json.dumps(detail, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "kubectl-describe", tool_seq)

            if "kubectl-events" in skill_tools and resource_name:
                resource_events = [
                    e for e in events
                    if e.get("involved_object", {}).get("name") == resource_name
                ]
                if resource_events:
                    sections["resource_events"] = json.dumps(resource_events, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "kubectl-events", tool_seq)

            if "kubectl-rollout" in skill_tools and resource_namespace and resource_name:
                rollout = await get_rollout_status(k8s, resource_namespace, resource_name)
                if rollout:
                    sections["rollout_status"] = json.dumps(rollout, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "kubectl-rollout", tool_seq)

            if "helm-history" in skill_tools and resource_namespace:
                helm = await get_helm_releases(k8s, resource_namespace)
                if helm:
                    sections["helm_releases"] = json.dumps(helm, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "helm-history", tool_seq)

            if "prometheus-query" in skill_tools and resource_namespace and resource_name:
                from pinky_worker.observation.prom_client import PromClient

                prom = PromClient(k8s)
                ns_pod = f'namespace="{resource_namespace}",pod=~"{resource_name}.*"'
                prom_queries: dict[str, str] = {
                    "cpu_usage_5m": f"rate(container_cpu_usage_seconds_total{{{ns_pod}}}[5m])",
                    "memory_working_set": f"container_memory_working_set_bytes{{{ns_pod}}}",
                    "restart_rate": f"rate(kube_pod_container_status_restarts_total{{{ns_pod}}}[1h])",
                    "cpu_p50_24h": (
                        f'quantile_over_time(0.50, rate(container_cpu_usage_seconds_total{{{ns_pod}}}[5m])[24h:])'
                    ),
                    "cpu_p95_24h": (
                        f'quantile_over_time(0.95, rate(container_cpu_usage_seconds_total{{{ns_pod}}}[5m])[24h:])'
                    ),
                    "memory_p50_24h": f'quantile_over_time(0.50, container_memory_working_set_bytes{{{ns_pod}}}[24h:])',
                    "memory_p95_24h": f'quantile_over_time(0.95, container_memory_working_set_bytes{{{ns_pod}}}[24h:])',
                    "oom_kills": f'kube_pod_container_status_last_terminated_reason{{reason="OOMKilled",{ns_pod}}}',
                }
                prom_results: dict[str, float | None] = {}
                for metric_name, prom_query in prom_queries.items():
                    try:
                        result = await prom.query_value(prom_query)
                        prom_results[metric_name] = result
                    except Exception:
                        logger.warning("prometheus query failed", extra={"metric": metric_name})
                if prom_results:
                    sections["prometheus_metrics"] = json.dumps(prom_results, default=str)
                tool_seq += 1
                await _emit_tool_event(pool, execution_id, "prometheus-query", tool_seq)

        await k8s.close()
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
        gathered_at=datetime.now(UTC).isoformat(),
        issue_title=issue_title,
        resource_namespace=resource_namespace,
        resource_name=resource_name,
        resource_kind=resource_kind,
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
        datetime.now(UTC) - timedelta(minutes=5),
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
        remediation_steps=data.get("remediation_steps", []),
        manual_commands=data.get("manual_commands", []),
    )


def _parse_structured_response(content: str) -> dict:
    """Extract JSON block from LLM response. Falls back to empty dict."""
    import re
    match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("failed to parse JSON from LLM response")
    return {}


_GENERIC_SKILL_BODY = (
    "Investigate the issue by examining the evidence provided. "
    "Look for: container restarts, OOMKilled events, image pull errors, "
    "missing resource limits/requests, failed health checks, pending PVCs, "
    "certificate expiration, and replica mismatches. "
    "Identify the root cause and suggest specific remediation steps."
)

_MAX_EVIDENCE_CHARS = int(os.environ.get("PINKY_MAX_EVIDENCE_CHARS", "8000"))
_LLM_MAX_TOKENS = int(os.environ.get("PINKY_LLM_MAX_TOKENS", "4096"))
_PROMPT_VERSION = "v2"


@activity.defn
async def run_investigation(evidence: EvidenceBundle, skill_body: str, execution_id: str = "") -> InvestigationArtifact:
    """Run LLM-powered investigation using the matching skill definition."""
    activity.heartbeat("running investigation")

    from pinky_worker.llm.provider import LLMRequest, LLMRouter, ModelTier
    from pinky_worker.llm.redaction import redact_evidence_sections
    from pinky_worker.llm.vertex_provider import VertexProvider

    redacted = redact_evidence_sections(evidence.sections)
    evidence_text = "\n\n".join(f"## {k}\n{v}" for k, v in redacted.items())
    if len(evidence_text) > _MAX_EVIDENCE_CHARS:
        evidence_text = evidence_text[:_MAX_EVIDENCE_CHARS] + "\n\n[evidence truncated]"

    issue_context = ""
    if evidence.issue_title:
        issue_context = (
            f"You are investigating a SPECIFIC issue:\n\n"
            f"  Issue: {evidence.issue_title}\n"
            f"  Resource: {evidence.resource_kind}/{evidence.resource_namespace}/{evidence.resource_name}\n\n"
            f"Focus ONLY on this resource. Do not analyze unrelated resources or issues "
            f"found in the evidence. The evidence may contain other resources for context, "
            f"but your analysis must be about the specific issue above.\n\n"
        )

    effective_skill = skill_body or _GENERIC_SKILL_BODY

    messages = [
        {
            "role": "system",
            "content": (
                "You are The Brain, an SRE agent embedded in Pinky. "
                f"{issue_context}"
                "Investigate the issue using the skill instructions and evidence below.\n\n"
                "Provide your analysis in clear sections, then end with a JSON block "
                "containing structured remediation steps.\n\n"
                "Your response must end with exactly one ```json code block:\n"
                "```json\n"
                '{\n'
                '  "summary": "One paragraph summary of the situation",\n'
                '  "root_cause": "Root cause explanation",\n'
                '  "recommended_action": "Primary recommended action in plain English",\n'
                '  "confidence": 0.85,\n'
                '  "remediation_steps": [\n'
                '    {\n'
                '      "action": "patch|scale|delete_pod|rollback",\n'
                '      "description": "What this step does",\n'
                '      "resource_kind": "Deployment|StatefulSet|Pod",\n'
                '      "resource_namespace": "namespace",\n'
                '      "resource_name": "name",\n'
                '      "params": {},\n'
                '      "risk": "low|medium|high"\n'
                '    }\n'
                '  ],\n'
                '  "manual_commands": ["oc get pods -n default", "oc describe deploy/web -n default"],\n'
                '  "verification": {"check_delay_seconds": 60, "success_criteria": "description"}\n'
                '}\n'
                "```\n\n"
                "If no automated remediation is possible, set remediation_steps to [] "
                "and provide manual_commands the operator should run."
            ),
        },
        {
            "role": "user",
            "content": f"# Skill Instructions\n\n{effective_skill}\n\n# Evidence\n\n{evidence_text}",
        },
    ]

    router = LLMRouter()
    router.register(VertexProvider())

    response = await router.complete(LLMRequest(
        messages=messages,
        model_tier=ModelTier.REASONING,
        max_tokens=_LLM_MAX_TOKENS,
    ))

    activity.heartbeat("parsing response")

    content = response.content
    structured = _parse_structured_response(content)

    system_prompt = messages[0]["content"] if messages else ""

    return InvestigationArtifact(
        artifact_id=str(uuid4()),
        issue_id=evidence.issue_id,
        summary=structured.get("summary", content[:500]),
        root_cause=structured.get("root_cause", content),
        recommended_action=structured.get("recommended_action", "See investigation summary"),
        confidence=structured.get("confidence", 0.7),
        tool_calls=[],
        evidence_hash=evidence.evidence_hash,
        created_at=datetime.now(UTC).isoformat(),
        execution_id=execution_id,
        remediation_steps=structured.get("remediation_steps", []),
        manual_commands=structured.get("manual_commands", []),
        system_prompt=system_prompt,
        skill_used=effective_skill[:200],
        prompt_version=_PROMPT_VERSION,
    )


_VALID_ACTIONS = {"scale", "patch", "delete_pod", "rollback"}


def _normalize_step(step: dict) -> dict | None:
    kind = step.get("resource_kind", "").lower() or "deployment"
    name = step.get("resource_name", "")
    ns = step.get("resource_namespace", step.get("namespace", "default"))

    resource = step.get("resource", "")
    if resource and "/" in resource:
        parts = resource.split("/")
        kind = parts[0].lower()
        name = parts[-1]
    elif resource and not name:
        name = resource

    if not name:
        logger.warning("remediation step rejected: no resource name in %s", step)
        return None

    action = step.get("action", "patch")
    if action not in _VALID_ACTIONS:
        logger.warning("unknown action %s, defaulting to patch", action)
        action = "patch"

    return {
        "action": action,
        "resource": f"{kind}/{name}",
        "namespace": ns,
        "resource_kind": kind,
        "resource_name": name,
        "resource_namespace": ns,
        "params": step.get("params", {}),
        "description": step.get("description", f"{action} {kind}/{name}"),
        "risk": step.get("risk", "medium"),
    }


def _normalize_steps(steps: list[dict]) -> list[dict]:
    normalized = []
    for s in steps:
        n = _normalize_step(s)
        if n:
            normalized.append(n)
    return normalized


@activity.defn
async def store_artifact(artifact: InvestigationArtifact) -> str:
    """Store investigation artifact as an execution event for caching."""
    from pinky_worker.db import get_pool

    pool = await get_pool()

    if artifact.execution_id:
        exec_uuid = UUID(artifact.execution_id)
    else:
        exec_row = await pool.fetchrow(
            "SELECT e.id FROM executions e "
            "JOIN work_items w ON e.work_item_id = w.id "
            "WHERE w.issue_id = $1::uuid AND e.execution_type = 'investigation' "
            "ORDER BY e.created_at DESC LIMIT 1",
            artifact.issue_id,
        )
        exec_uuid = exec_row["id"] if exec_row else uuid4()

    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT DO NOTHING""",
        uuid4(), exec_uuid, "investigation_completed", 999,
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
            "remediation_steps": artifact.remediation_steps,
            "manual_commands": artifact.manual_commands,
            "system_prompt": artifact.system_prompt,
            "skill_used": artifact.skill_used,
            "prompt_version": artifact.prompt_version,
        }),
        datetime.now(UTC),
    )
    logger.info("artifact stored: %s", artifact.artifact_id)

    # Create approval and populate artifact_refs when remediation steps exist
    if artifact.remediation_steps:
        artifact.remediation_steps = _normalize_steps(artifact.remediation_steps)
        if not artifact.remediation_steps:
            logger.warning("all remediation steps rejected during normalization")
            return artifact.artifact_id
        try:
            exec_row = await pool.fetchrow(
                "SELECT work_item_id, cluster_id FROM executions WHERE id = $1",
                exec_uuid,
            )
            if not exec_row or not exec_row["work_item_id"]:
                logger.error(
                    "execution %s has no work_item, cannot create approval",
                    str(exec_uuid),
                )
                return artifact.artifact_id
            if exec_row and exec_row["work_item_id"]:
                work_item_id = exec_row["work_item_id"]
                cluster_id = exec_row["cluster_id"]

                plan_steps = artifact.remediation_steps
                changeset_digest = hashlib.sha256(
                    json.dumps(plan_steps, sort_keys=True).encode(),
                ).hexdigest()[:16]
                target_resources = [
                    {
                        "kind": s.get("resource_kind", ""),
                        "namespace": s.get("resource_namespace", ""),
                        "name": s.get("resource_name", ""),
                    }
                    for s in plan_steps
                ]

                approval_id = uuid4()
                approval_ttl_hours = int(os.environ.get("PINKY_APPROVAL_TTL_HOURS", "24"))
                await pool.execute(
                    """INSERT INTO approvals
                       (id, execution_id, changeset_digest, target_resources, status, expires_at)
                       VALUES ($1, $2, $3, $4, 'pending', now() + make_interval(hours => $5))""",
                    approval_id, exec_uuid, changeset_digest,
                    json.dumps(target_resources), approval_ttl_hours,
                )

                # Look up the active binding for this cluster so remediation
                # can proceed without the user having to supply it separately.
                binding_row = await pool.fetchrow(
                    """SELECT id FROM cluster_identity_bindings
                       WHERE cluster_id = $1 AND status IN ('valid', 'expiring')
                       ORDER BY expires_at DESC NULLS LAST LIMIT 1""",
                    cluster_id,
                )
                refs: dict[str, Any] = {
                    "approval_id": str(approval_id),
                    "plan_steps": plan_steps,
                }
                if binding_row:
                    refs["binding_id"] = str(binding_row["id"])

                await pool.execute(
                    """UPDATE work_items
                       SET artifact_refs = COALESCE(artifact_refs, '{}'::jsonb) || $2::jsonb,
                           updated_at = now()
                       WHERE id = $1""",
                    work_item_id, json.dumps(refs),
                )

                logger.info(
                    "approval created: %s for work_item %s",
                    str(approval_id), str(work_item_id),
                )
        except Exception:
            logger.exception("failed to create approval after investigation")

    return artifact.artifact_id


@activity.defn
async def emit_execution_event(event: ExecutionEventPayload) -> None:
    """Emit an execution event to Postgres and trigger SSE broadcast."""
    from pinky_worker.db import get_pool

    pool = await get_pool()
    occurred = datetime.now(UTC)

    exec_id_str = event.execution_id or ""
    try:
        exec_uuid = UUID(exec_id_str)
    except ValueError:
        stripped = exec_id_str.removeprefix("investigation-").removeprefix("remediation-")
        exec_uuid = UUID(stripped)

    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6)
           ON CONFLICT DO NOTHING""",
        uuid4(), exec_uuid,
        event.event_type, event.sequence,
        json.dumps(event.payload), occurred,
    )

    status_map = {
        "started": ("running", "UPDATE executions SET status = 'running', started_at = $2 WHERE id = $1"),
        "completed": ("completed", "UPDATE executions SET status = 'completed', completed_at = $2 WHERE id = $1"),
        "failed": ("failed", "UPDATE executions SET status = 'failed', completed_at = $2 WHERE id = $1"),
    }
    if event.event_type in status_map:
        _, sql = status_map[event.event_type]
        await pool.execute(sql, exec_uuid, occurred)

    try:
        payload = json.dumps({"event_type": event.event_type, "execution_id": str(exec_uuid)})
        await pool.execute("SELECT pg_notify($1, $2)", "pinky_watch", payload)
        await pool.execute("SELECT pg_notify($1, $2)", f"pinky_execution_{exec_uuid}", payload)
    except Exception:
        logger.debug("NOTIFY skipped in execution event emission")

    logger.info("execution event emitted: %s %s exec=%s", event.event_type, event.execution_id, str(exec_uuid))


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

    if row["expires_at"] and row["expires_at"] < datetime.now(UTC):
        return {"valid": False, "reason": "approval expired"}

    if changeset_digest and row["changeset_digest"] != changeset_digest:
        return {"valid": False, "reason": "changeset changed since approval was granted"}

    return {"valid": True}


@activity.defn
async def apply_change(execution_id: str, cluster_id: str, binding_id: str, step: dict) -> dict:
    """Apply a remediation step using the user's cluster identity."""
    action = step.get("action", "")
    namespace = step.get("namespace", step.get("resource_namespace", "default"))
    resource = step.get("resource", "")
    params = step.get("params", {})
    step_index = step.get("_step_index", 0)
    cmd_seq = 500 + step_index * 10

    if resource and "/" in resource:
        parts = resource.split("/")
        kind = parts[0]
        name = parts[-1]
    else:
        kind = step.get("resource_kind", resource or "deployment").lower()
        name = step.get("resource_name", resource)

    description = step.get("description", f"{action} {kind}/{name}")
    activity.heartbeat(f"applying: {description}")

    from pinky_worker.db import get_pool
    from pinky_worker.observation.k8s_client import (
        create_client,
        delete_pod,
        patch_resource,
        rollback_deployment,
        scale_deployment,
    )

    oc_cmd = _build_oc_command(action, kind, name, namespace, params)

    try:
        api_endpoint = None
        user_token = None
        if binding_id:
            binding_pool = await get_pool()
            binding_row = await binding_pool.fetchrow(
                "SELECT encrypted_token, cluster_id, expires_at FROM cluster_identity_bindings WHERE id = $1",
                UUID(binding_id),
            )
            if binding_row and binding_row.get("expires_at"):
                from datetime import UTC as _UTC
                from datetime import datetime as _dt
                if binding_row["expires_at"].replace(tzinfo=_UTC) < _dt.now(_UTC):
                    raise RuntimeError(
                        f"Cluster binding {binding_id} expired — reconnect to the cluster"
                    )
            if binding_row and binding_row["encrypted_token"]:
                from pinky_worker.security import decrypt
                user_token = decrypt(
                    binding_row["encrypted_token"],
                    aad=f"cluster_identity_bindings:{binding_id}",
                ).decode()
                cluster_row = await binding_pool.fetchrow(
                    "SELECT api_endpoint FROM cluster_registry WHERE id = $1",
                    binding_row["cluster_id"],
                )
                if cluster_row:
                    api_endpoint = cluster_row["api_endpoint"]

        k8s = await create_client(api_endpoint=api_endpoint, token=user_token)

        if action == "scale":
            replicas = params.get("replicas", 1)
            result = await scale_deployment(k8s, namespace, name, replicas)
        elif action == "delete_pod":
            result = await delete_pod(k8s, namespace, name)
        elif action == "patch":
            result = await patch_resource(k8s, namespace, kind, name, params.get("patch", {}))
        elif action == "rollback":
            result = await rollback_deployment(k8s, namespace, name)
        else:
            result = {"status": "unsupported", "action": action}
            logger.warning("unsupported apply_change action: %s", action)

        await k8s.close()
        result["applied_at"] = datetime.now(UTC).isoformat()

        output = f"{kind}/{name} {result.get('status', 'applied')}"
        pool = await get_pool()
        await _emit_command_event(pool, execution_id, cmd_seq, oc_cmd, output, 0, action, resource)

        return result

    except Exception as e:
        logger.exception("apply_change failed for cluster %s", cluster_id)
        try:
            pool = await get_pool()
            await _emit_command_event(pool, execution_id, cmd_seq, oc_cmd, str(e), 1, action, resource)
        except Exception:
            logger.debug("failed to emit error command event")
        raise


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
                "verified_at": datetime.now(UTC).isoformat(),
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
            UUID(execution_id), datetime.now(UTC),
        )
    elif event_type == "completed":
        await pool.execute(
            """UPDATE executions SET status = 'completed', completed_at = $2 WHERE id = $1""",
            UUID(execution_id), datetime.now(UTC),
        )
        confidence = payload.get("confidence")
        if confidence is not None:
            await pool.execute(
                """UPDATE work_items SET confidence = $2, updated_at = now()
                   WHERE id = (SELECT work_item_id FROM executions WHERE id = $1)""",
                UUID(execution_id), float(confidence),
            )

        if payload.get("verification_passed"):
            exec_info = await pool.fetchrow(
                "SELECT execution_type, work_item_id FROM executions WHERE id = $1",
                UUID(execution_id),
            )
        else:
            exec_info = None
        if (exec_info
                and exec_info["execution_type"] == "remediation"
                and exec_info["work_item_id"]):
            wi_id = exec_info["work_item_id"]
            async with pool.acquire() as conn, conn.transaction():
                await conn.execute(
                    "UPDATE work_items SET status = 'done', updated_at = now() WHERE id = $1", wi_id,
                )
                await conn.execute(
                    """UPDATE issues SET status = 'resolved', resolved_by = 'remediation', updated_at = now()
                       WHERE id = (SELECT issue_id FROM work_items WHERE id = $1)""",
                    wi_id,
                )
                await conn.execute(
                    "SELECT pg_notify($1, $2)", "pinky_work_items",
                    json.dumps({"event_type": "work_item.completed", "aggregate_id": str(wi_id)}),
                )
    elif event_type == "failed":
        await pool.execute(
            """UPDATE executions SET status = 'failed', completed_at = $2 WHERE id = $1""",
            UUID(execution_id), datetime.now(UTC),
        )

    exec_row = await pool.fetchrow(
        "SELECT cluster_id FROM executions WHERE id = $1", UUID(execution_id),
    )
    cluster_id = exec_row["cluster_id"] if exec_row else None
    await pool.execute(
        """INSERT INTO domain_events (id, aggregate_type, aggregate_id, event_type, cluster_id, payload, occurred_at)
           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
        uuid4(), "execution", UUID(execution_id), event_type,
        cluster_id, json.dumps(payload), datetime.now(UTC),
    )

    logger.info("projected to postgres: %s %s", execution_id, event_type)
