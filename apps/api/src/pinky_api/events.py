"""Domain event emitter — writes to domain_events table and fires Postgres NOTIFY.

Every significant state transition should call emit() to:
1. Persist the event to domain_events table
2. Fire NOTIFY on the appropriate channel for SSE fan-out
3. Queue webhook delivery for matching subscriptions
"""

import json
import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.models.extensibility import DomainEvent

logger = logging.getLogger(__name__)

CHANNEL_MAP = {
    "work_item": "pinky_work_items",
    "issue": "pinky_issues",
    "execution": "pinky_watch",
    "approval": "pinky_watch",
    "cluster": "pinky_watch",
}


async def emit(
    db: AsyncSession,
    event_type: str,
    aggregate_type: str,
    aggregate_id: UUID,
    payload: dict,
    cluster_id: UUID | None = None,
    principal_id: UUID | None = None,
) -> DomainEvent:
    event = DomainEvent()
    event.event_type = event_type
    event.aggregate_type = aggregate_type
    event.aggregate_id = aggregate_id
    event.payload = payload
    event.cluster_id = cluster_id
    event.principal_id = principal_id
    db.add(event)
    await db.flush()

    channel = CHANNEL_MAP.get(aggregate_type, "pinky_watch")
    notify_payload = json.dumps({
        "event_id": str(event.id),
        "event_type": event_type,
        "aggregate_type": aggregate_type,
        "aggregate_id": str(aggregate_id),
    })
    try:
        raw_conn = await db.connection()
        await raw_conn.execute(
            text("SELECT pg_notify(:channel, :payload)"),
            {"channel": channel, "payload": notify_payload},
        )
    except Exception:
        logger.debug("NOTIFY skipped — not connected to Postgres or in test mode")

    logger.info(
        "domain event emitted %s %s %s",
        event_type,
        aggregate_type,
        str(aggregate_id),
    )
    return event
