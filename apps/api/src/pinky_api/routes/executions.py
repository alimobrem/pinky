"""Execution routes — Brain workflows and approval management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.repositories.executions import ExecutionRepository

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class ApproveRequest(BaseModel):
    changeset_digest: str


class RejectRequest(BaseModel):
    reason: str


def _serialize(ex: object) -> dict:
    return {
        "id": str(ex.id),
        "work_item_id": str(ex.work_item_id) if ex.work_item_id else None,
        "cluster_id": str(ex.cluster_id),
        "execution_type": ex.execution_type,
        "status": ex.status,
        "started_at": ex.started_at.isoformat() if ex.started_at else None,
        "completed_at": ex.completed_at.isoformat() if ex.completed_at else None,
        "created_at": ex.created_at.isoformat() if ex.created_at else "",
    }


@router.get("")
async def list_executions(
    work_item_id: str | None = None,
    cluster_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = ExecutionRepository(db)
    result = await repo.list(work_item_id=work_item_id, cluster_id=cluster_id, status=status, limit=limit, cursor=cursor)
    return {"items": [_serialize(e) for e in result["items"]], "next_cursor": result["next_cursor"], "has_more": result["has_more"]}


@router.get("/{execution_id}")
async def get_execution(execution_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = ExecutionRepository(db)
    ex = await repo.get(UUID(execution_id))
    if ex is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return _serialize(ex)


@router.post("")
async def start_execution(work_item_id: str, execution_type: str = "investigation", db: AsyncSession = Depends(get_db)) -> dict:
    repo = ExecutionRepository(db)
    ex = await repo.create(work_item_id=UUID(work_item_id), cluster_id=UUID(work_item_id), execution_type=execution_type)
    await db.commit()
    return _serialize(ex)


@router.post("/{execution_id}/approve")
async def approve_execution(execution_id: str, req: ApproveRequest) -> dict:
    return {"message": "Approve — requires Temporal workflow signal"}


@router.post("/{execution_id}/reject")
async def reject_execution(execution_id: str, req: RejectRequest) -> dict:
    return {"message": "Reject — requires Temporal workflow signal"}
