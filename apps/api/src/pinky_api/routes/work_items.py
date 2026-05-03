"""Work item routes — the core task-first API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_authenticated
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.repositories.work_items import WorkItemRepository
from pinky_api.schemas.work_item import WorkItemListResponse, WorkItemResponse

router = APIRouter(prefix="/api/v1/work-items", tags=["work-items"])


def _serialize(item: object) -> dict:
    return {
        "id": str(item.id),
        "issue_id": str(item.issue_id) if item.issue_id else None,
        "cluster_id": str(item.cluster_id),
        "title": item.title,
        "why_now": item.why_now,
        "recommended_next_step": item.recommended_next_step,
        "status": item.status,
        "owner_id": str(item.owner_id) if item.owner_id else None,
        "confidence": item.confidence,
        "priority": item.priority,
        "labels": item.labels or {},
        "annotations": item.annotations or {},
        "runbook_url": item.runbook_url,
        "artifact_refs": item.artifact_refs or {},
        "created_at": item.created_at.isoformat() if item.created_at else "",
        "updated_at": item.updated_at.isoformat() if item.updated_at else "",
    }


@router.get("")
async def list_work_items(
    cluster_id: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    priority: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = WorkItemRepository(db)
    result = await repo.list(
        cluster_id=cluster_id, status=status, owner_id=owner,
        priority=priority, limit=limit, cursor=cursor,
    )
    return {
        "items": [_serialize(i) for i in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.get("/{work_item_id}")
async def get_work_item(work_item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = WorkItemRepository(db)
    item = await repo.get(UUID(work_item_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    return _serialize(item)


@router.post("/{work_item_id}/accept")
async def accept_work_item(work_item_id: str, db: AsyncSession = Depends(get_db), _principal: dict = Depends(require_authenticated)) -> dict:
    repo = WorkItemRepository(db)
    try:
        item = await repo.transition(UUID(work_item_id), "accepted")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.accepted", "work_item", UUID(work_item_id), {"status": "accepted"})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/start")
async def start_work_item(work_item_id: str, db: AsyncSession = Depends(get_db), _principal: dict = Depends(require_authenticated)) -> dict:
    repo = WorkItemRepository(db)
    try:
        item = await repo.transition(UUID(work_item_id), "in_progress")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.started", "work_item", UUID(work_item_id), {"status": "in_progress"})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/complete")
async def complete_work_item(work_item_id: str, db: AsyncSession = Depends(get_db), _principal: dict = Depends(require_authenticated)) -> dict:
    repo = WorkItemRepository(db)
    try:
        item = await repo.transition(UUID(work_item_id), "done")
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await emit(db, "work_item.completed", "work_item", UUID(work_item_id), {"status": "done"})
    await db.commit()
    return _serialize(item)


@router.post("/{work_item_id}/reassign")
async def reassign_work_item(
    work_item_id: str,
    assignee_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = WorkItemRepository(db)
    item = await repo.reassign(UUID(work_item_id), UUID(assignee_id))
    if item is None:
        raise HTTPException(status_code=404, detail="Work item not found")
    await db.commit()
    return _serialize(item)


@router.get("/{work_item_id}/events")
async def get_work_item_events(work_item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    from pinky_api.repositories.executions import ExecutionRepository
    repo = ExecutionRepository(db)
    events = await repo.get_events_for_work_item(UUID(work_item_id))
    return {
        "items": [
            {
                "id": str(e.id),
                "execution_id": str(e.execution_id),
                "event_type": e.event_type,
                "sequence": e.sequence,
                "payload": e.payload or {},
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else "",
            }
            for e in events
        ],
    }


@router.get("/{work_item_id}/investigation")
async def get_work_item_investigation(work_item_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    from pinky_api.repositories.executions import ExecutionRepository
    repo = ExecutionRepository(db)
    investigation = await repo.get_investigation_for_work_item(UUID(work_item_id))
    if investigation is None:
        return {"has_investigation": False}
    return {"has_investigation": True, **investigation}
