"""Centralized state transitions — every execution and work_item status
change in the worker MUST go through these functions.

No raw SQL status UPDATEs anywhere else. This module is the single source
of truth for what transitions are valid, and guarantees that every change
emits a domain event and pg_notify.
"""

from __future__ import annotations

from uuid import UUID

import structlog

from pinky_worker.events import emit_domain_event

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# State machines — single source of truth
# ---------------------------------------------------------------------------

EXEC_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "failed", "cancelled"},
    "running": {"waiting_for_approval", "completed", "failed", "cancelled"},
    "waiting_for_approval": {"running", "failed", "timed_out", "cancelled"},
}

EXEC_TERMINAL: frozenset[str] = frozenset({"completed", "failed", "cancelled", "timed_out"})

WI_TRANSITIONS: dict[str, set[str]] = {
    "ready": {"in_progress", "done"},
    "in_progress": {"blocked", "waiting_for_approval", "done", "ready"},
    "blocked": {"in_progress", "done", "ready"},
    "waiting_for_approval": {"in_progress", "done", "ready"},
    "done": {"ready"},
}


# ---------------------------------------------------------------------------
# Execution transitions
# ---------------------------------------------------------------------------

async def transition_execution(
    pool,
    exec_id,
    target_status: str,
    *,
    payload: dict | None = None,
) -> bool:
    """Validate and apply an execution status transition.

    Returns True on success (including idempotent no-ops).
    Returns False if the transition is invalid or the row doesn't exist.
    """
    uid = UUID(str(exec_id)) if not isinstance(exec_id, UUID) else exec_id

    row = await pool.fetchrow(
        "SELECT status, execution_type, work_item_id, cluster_id FROM executions WHERE id = $1",
        uid,
    )
    if not row:
        logger.warning("transition_execution: execution not found", exec_id=str(uid))
        return False

    current = row["status"]

    if current == target_status:
        return True

    if current in EXEC_TERMINAL:
        return False

    allowed = EXEC_TRANSITIONS.get(current, set())
    if target_status not in allowed:
        logger.warning(
            "blocked execution transition",
            exec_id=str(uid), current=current, target=target_status,
        )
        return False

    if target_status in EXEC_TERMINAL:
        await pool.execute(
            "UPDATE executions SET status = $1, completed_at = now() WHERE id = $2",
            target_status, uid,
        )
    elif target_status == "running":
        await pool.execute(
            "UPDATE executions SET status = 'running', started_at = COALESCE(started_at, now()) WHERE id = $1",
            uid,
        )
    else:
        await pool.execute(
            "UPDATE executions SET status = $1 WHERE id = $2",
            target_status, uid,
        )

    cluster_id_str = str(row["cluster_id"]) if row["cluster_id"] else None

    async with pool.acquire() as conn:
        await emit_domain_event(
            conn,
            f"execution.{target_status}",
            "execution",
            str(uid),
            payload=payload or {},
            cluster_id=cluster_id_str,
        )

    if target_status in EXEC_TERMINAL and row.get("execution_type") == "remediation":
        await pool.execute(
            "UPDATE approvals SET status = 'invalidated' "
            "WHERE execution_id = $1 AND status = 'pending'",
            uid,
        )

    if target_status in ("failed", "timed_out", "cancelled") and row["work_item_id"]:
        await transition_work_item(
            pool,
            row["work_item_id"],
            "ready",
            payload={"reason": f"execution_{target_status}"},
        )

    return True


# ---------------------------------------------------------------------------
# Work item transitions
# ---------------------------------------------------------------------------

async def transition_work_item(
    pool,
    wi_id,
    target_status: str,
    *,
    payload: dict | None = None,
) -> bool:
    """Validate and apply a work_item status transition.

    Returns True on success (including idempotent no-ops).
    Returns False if the transition is invalid or the row doesn't exist.
    """
    uid = UUID(str(wi_id)) if not isinstance(wi_id, UUID) else wi_id

    row = await pool.fetchrow(
        "SELECT status, cluster_id FROM work_items WHERE id = $1",
        uid,
    )
    if not row:
        logger.warning("transition_work_item: work_item not found", wi_id=str(uid))
        return False

    current = row["status"]

    if current == target_status:
        return True

    allowed = WI_TRANSITIONS.get(current, set())
    if target_status not in allowed:
        logger.warning(
            "blocked work_item transition",
            wi_id=str(uid), current=current, target=target_status,
        )
        return False

    await pool.execute(
        "UPDATE work_items SET status = $1, updated_at = now() WHERE id = $2",
        target_status, uid,
    )

    cluster_id_str = str(row["cluster_id"]) if row["cluster_id"] else None

    async with pool.acquire() as conn:
        await emit_domain_event(
            conn,
            f"work_item.{target_status}",
            "work_item",
            str(uid),
            payload=payload or {},
            cluster_id=cluster_id_str,
        )

    return True
