"""Worker-side domain event emitter — writes to domain_events and fires pg_notify.

Mirrors the API's events.emit() but uses raw asyncpg connections instead of
SQLAlchemy sessions, since the worker operates directly on the connection pool.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

CHANNEL_MAP = {
    "work_item": "pinky_work_items",
    "issue": "pinky_issues",
    "execution": "pinky_watch",
    "approval": "pinky_watch",
    "cluster": "pinky_watch",
}


async def emit_domain_event(
    conn,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: dict | None = None,
    cluster_id: str | None = None,
    principal_id: str | None = None,
) -> str:
    """Insert a domain event and fire pg_notify."""
    event_id = uuid.uuid4()
    now = datetime.now(UTC)
    await conn.execute(
        """INSERT INTO domain_events
           (id, event_type, aggregate_type, aggregate_id, payload,
            cluster_id, principal_id, occurred_at)
           VALUES ($1, $2, $3, $4::uuid, $5, $6::uuid, $7::uuid, $8)""",
        event_id,
        event_type,
        aggregate_type,
        aggregate_id,
        json.dumps(payload or {}),
        cluster_id,
        principal_id,
        now,
    )

    channel = CHANNEL_MAP.get(aggregate_type, "pinky_watch")
    notify_payload = json.dumps({
        "event_id": str(event_id),
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": aggregate_id,
    })
    try:
        await conn.execute(f"SELECT pg_notify('{channel}', $1)", notify_payload)
    except Exception:
        logger.warning("pg_notify failed", event_type=event_type, aggregate_type=aggregate_type)

    return str(event_id)
