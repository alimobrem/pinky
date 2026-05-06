"""Direct async investigation pipeline — no Temporal, no activities, no UUID resolution.

Replaces the InvestigationWorkflow + 6 activities with a single async function
that gathers evidence, calls the LLM, and stores results. All DB operations use
the same pool connection with direct SQL — no serialization, no timeouts, no
activity-level retry. Failures are caught and the execution is marked as failed.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pinky_worker.observation.k8s_client import create_client, list_pods, list_events

logger = logging.getLogger(__name__)


async def run_investigation(
    pool,
    execution_id: UUID,
    issue_id: str,
    cluster_id: str,
    skill_body: str = "",
    skill_tools: list[str] | None = None,
) -> None:
    """Run a complete investigation: evidence → LLM → store. No Temporal."""
    try:
        await pool.execute(
            "UPDATE executions SET status = 'running', started_at = now() WHERE id = $1",
            execution_id,
        )
        await _notify(pool, "started", execution_id)

        evidence = await _gather_evidence(cluster_id, issue_id)
        result = await _call_llm(evidence, skill_body)
        await _store_and_complete(pool, execution_id, issue_id, result)

    except Exception:
        logger.exception("investigation failed: %s", execution_id)
        try:
            await pool.execute(
                "UPDATE executions SET status = 'failed', completed_at = now() WHERE id = $1",
                execution_id,
            )
            await _notify(pool, "failed", execution_id)
        except Exception:
            logger.exception("failed to mark execution as failed: %s", execution_id)


async def _gather_evidence(cluster_id: str, issue_id: str) -> dict:
    """Gather K8s evidence. Returns sections dict."""
    sections: dict[str, str] = {
        "cluster_id": cluster_id,
        "issue_id": issue_id,
    }
    try:
        k8s = await create_client()
        pods = await list_pods(k8s)
        events = await list_events(k8s, limit=50)
        sections["pods"] = json.dumps(pods[:20], indent=2, default=str)
        sections["events"] = json.dumps(events[:20], indent=2, default=str)
        await k8s.close()
    except Exception:
        logger.warning("failed to gather K8s evidence, continuing with empty evidence")
        sections["error"] = "Failed to connect to cluster"

    return sections


async def _call_llm(evidence: dict, skill_body: str) -> dict:
    """Call the LLM for investigation analysis. Returns structured result."""
    import re
    import anthropic

    evidence_text = "\n\n".join(f"## {k}\n{v}" for k, v in evidence.items())

    system_prompt = (
        "You are The Brain, an SRE agent embedded in Pinky. "
        "Investigate the issue using the evidence below.\n\n"
        "Provide your analysis, then end with a ```json block:\n"
        '{"summary": "...", "root_cause": "...", "recommended_action": "...", '
        '"confidence": 0.85, "remediation_steps": [...], "manual_commands": [...]}\n'
    )

    client = anthropic.AsyncAnthropicVertex(region="global")
    response = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": f"# Skill Instructions\n\n{skill_body}\n\n# Evidence\n\n{evidence_text}"},
        ],
    )

    content = response.content[0].text

    structured = {}
    match = re.search(r"```json\s*\n(.*?)\n```", content, re.DOTALL)
    if match:
        try:
            structured = json.loads(match.group(1))
        except json.JSONDecodeError:
            logger.warning("failed to parse JSON from LLM response")

    return {
        "summary": structured.get("summary", content[:500]),
        "root_cause": structured.get("root_cause", content),
        "recommended_action": structured.get("recommended_action", "See investigation summary"),
        "confidence": structured.get("confidence", 0.7),
        "remediation_steps": structured.get("remediation_steps", []),
        "manual_commands": structured.get("manual_commands", []),
    }


async def _store_and_complete(
    pool, execution_id: UUID, issue_id: str, result: dict,
) -> None:
    """Write investigation results and mark execution as completed."""
    event_id = uuid4()
    now = datetime.now(UTC)

    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, 'investigation_completed', 999, $3, $4)
           ON CONFLICT DO NOTHING""",
        event_id, execution_id,
        json.dumps({
            "artifact_id": str(event_id),
            "issue_id": issue_id,
            "summary": result["summary"],
            "root_cause": result["root_cause"],
            "recommended_action": result["recommended_action"],
            "confidence": result["confidence"],
            "remediation_steps": result["remediation_steps"],
            "manual_commands": result["manual_commands"],
            "created_at": now.isoformat(),
        }),
        now,
    )

    await pool.execute(
        """INSERT INTO execution_events (id, execution_id, event_type, sequence, payload, occurred_at)
           VALUES ($1, $2, 'completed', 1, $3, $4)
           ON CONFLICT DO NOTHING""",
        uuid4(), execution_id,
        json.dumps({"confidence": result["confidence"], "artifact_id": str(event_id)}),
        now,
    )

    await pool.execute(
        "UPDATE executions SET status = 'completed', completed_at = $2 WHERE id = $1",
        execution_id, now,
    )

    await _notify(pool, "completed", execution_id)
    logger.info("investigation completed: %s", execution_id)


async def _notify(pool, event_type: str, execution_id: UUID) -> None:
    """Fire pg_notify for SSE."""
    try:
        payload = json.dumps({"event_type": event_type, "execution_id": str(execution_id)})
        await pool.execute("SELECT pg_notify('pinky_watch', $1)", payload)
    except Exception:
        logger.debug("pg_notify skipped")
