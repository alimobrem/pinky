"""History routes — append-only audit and narrative surface."""

import csv
import io
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.models.execution import Execution
from pinky_api.models.issue import Issue
from pinky_api.models.principal import Principal
from pinky_api.models.work_item import WorkItem
from pinky_api.repositories.history import HistoryRepository

router = APIRouter(prefix="/api/v1/history", tags=["history"])


def _serialize(event: Any) -> dict:
    return {
        "id": str(event.id),
        "aggregate_type": event.aggregate_type,
        "aggregate_id": str(event.aggregate_id),
        "event_type": event.event_type,
        "cluster_id": str(event.cluster_id) if event.cluster_id else None,
        "principal_id": str(event.principal_id) if event.principal_id else None,
        "payload": event.payload or {},
        "occurred_at": event.occurred_at.isoformat() if event.occurred_at else "",
    }


def _describe(event_type: str, title: str | None, payload: dict) -> str:
    t = title or ""
    match event_type:
        case "issue.created":
            return f"New issue: {t}" if t else "New issue detected"
        case "issue.resolved":
            return f"Issue resolved: {t}" if t else "Issue resolved"
        case "issue.auto_resolved":
            return f"Auto-resolved: {t}" if t else "Issue auto-resolved"
        case "issue.suppressed":
            return f"Issue suppressed: {t}" if t else "Issue suppressed"
        case "issue.escalated":
            return f"Issue escalated: {t}" if t else "Issue escalated"
        case "work_item.created":
            return f"Task created: {t}" if t else "Task created"
        case "work_item.taken":
            return f"Task taken: {t}" if t else "Task taken"
        case "work_item.completed":
            return f"Task completed: {t}" if t else "Task completed"
        case "execution.started":
            return "Investigation started"
        case "execution.completed":
            return "Investigation completed"
        case "execution.failed":
            return "Investigation failed"
        case "resource.applied":
            kind = payload.get("kind", "")
            name = payload.get("name", "")
            return f"Resource applied: {kind}/{name}" if kind else "Resource applied"
        case "binding.created":
            return "Cluster binding created"
        case _:
            return event_type.replace(".", " ").replace("_", " ").title()


async def _enrich_events(items: list[dict], db: AsyncSession) -> None:
    """Batch-resolve titles and actor names for serialized events."""
    # Group aggregate IDs by type
    ids_by_type: dict[str, list[uuid.UUID]] = defaultdict(list)
    principal_ids: list[uuid.UUID] = []

    for item in items:
        agg_id = uuid.UUID(item["aggregate_id"])
        ids_by_type[item["aggregate_type"]].append(agg_id)
        if item["principal_id"]:
            principal_ids.append(uuid.UUID(item["principal_id"]))

    # Batch resolve titles
    title_map: dict[uuid.UUID, str] = {}
    issue_work_item_map: dict[uuid.UUID, uuid.UUID] = {}
    exec_work_item_map: dict[uuid.UUID, uuid.UUID] = {}

    if ids_by_type.get("work_item"):
        wi_ids = ids_by_type["work_item"]
        rows = (await db.execute(
            select(WorkItem.id, WorkItem.title).where(WorkItem.id.in_(wi_ids))
        )).all()
        for row in rows:
            title_map[row[0]] = row[1]

    if ids_by_type.get("issue"):
        issue_ids = ids_by_type["issue"]
        rows = (await db.execute(
            select(Issue.id, Issue.title).where(Issue.id.in_(issue_ids))
        )).all()
        for row in rows:
            title_map[row[0]] = row[1]
        # Also resolve issue → work_item link
        wi_rows = (await db.execute(
            select(WorkItem.issue_id, WorkItem.id).where(
                WorkItem.issue_id.in_(issue_ids)
            )
        )).all()
        for row in wi_rows:
            if row[0] is not None:
                issue_work_item_map[row[0]] = row[1]

    if ids_by_type.get("execution"):
        exec_ids = ids_by_type["execution"]
        rows = (await db.execute(
            select(Execution.id, Execution.work_item_id).where(
                Execution.id.in_(exec_ids)
            )
        )).all()
        for row in rows:
            if row[1] is not None:
                exec_work_item_map[row[0]] = row[1]

    # Batch resolve actor names
    actor_map: dict[uuid.UUID, str] = {}
    if principal_ids:
        rows = (await db.execute(
            select(Principal.id, Principal.display_name).where(
                Principal.id.in_(principal_ids)
            )
        )).all()
        for row in rows:
            if row[1] is not None:
                actor_map[row[0]] = row[1]

    # Enrich each item
    for item in items:
        agg_id = uuid.UUID(item["aggregate_id"])
        item["aggregate_title"] = title_map.get(agg_id)
        item["principal_display_name"] = (
            actor_map.get(uuid.UUID(item["principal_id"]))
            if item["principal_id"]
            else None
        )

        if item["aggregate_type"] == "issue" and agg_id in issue_work_item_map:
            item["payload"]["work_item_id"] = str(issue_work_item_map[agg_id])
        if item["aggregate_type"] == "execution" and agg_id in exec_work_item_map:
            item["payload"]["work_item_id"] = str(exec_work_item_map[agg_id])

        item["description"] = _describe(
            item["event_type"], item.get("aggregate_title"), item["payload"]
        )


@router.get("/export")
async def export_history(
    cluster_id: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> Response:
    repo = HistoryRepository(db)
    result = await repo.list(
        cluster_id=cluster_id, event_type=event_type, since=since, limit=10000,
    )
    items = [_serialize(e) for e in result["items"]]
    await _enrich_events(items, db)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Time", "Type", "Description", "Actor",
        "Cluster", "Entity Type", "Entity ID",
    ])
    for item in items:
        writer.writerow([
            item["occurred_at"],
            item["event_type"],
            item.get("description", ""),
            item.get("principal_display_name", item.get("principal_id", "")),
            item.get("cluster_id", ""),
            item["aggregate_type"],
            item["aggregate_id"],
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=pinky-history.csv"},
    )


@router.get("")
async def list_history(
    cluster_id: str | None = None,
    aggregate_type: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = HistoryRepository(db)
    result = await repo.list(
        cluster_id=cluster_id, aggregate_type=aggregate_type,
        event_type=event_type, since=since, limit=limit, cursor=cursor,
    )
    items = [_serialize(e) for e in result["items"]]
    await _enrich_events(items, db)
    return {
        "items": items,
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(result["items"])),
    }
