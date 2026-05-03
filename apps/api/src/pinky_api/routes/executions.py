"""Execution routes — Brain workflows and approval management."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.repositories.executions import ExecutionRepository

logger = logging.getLogger(__name__)

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
    import pinky_api.temporal_state as temporal_state

    repo = ExecutionRepository(db)

    wi_id = UUID(work_item_id)
    from pinky_api.repositories.work_items import WorkItemRepository
    wi_repo = WorkItemRepository(db)
    wi = await wi_repo.get(wi_id)
    if wi is None:
        raise HTTPException(status_code=404, detail="Work item not found")

    ex = await repo.create(work_item_id=wi_id, cluster_id=wi.cluster_id, execution_type=execution_type)
    await emit(db, "execution.started", "execution", ex.id, {"type": execution_type, "work_item_id": work_item_id})
    await db.commit()

    if temporal_state.client is not None:
        try:
            workflow_input = {
                "issue_id": str(wi.issue_id) if wi.issue_id else str(wi.id),
                "cluster_id": str(wi.cluster_id),
                "correlation_key": str(wi.id),
                "evidence_hash": "",
                "skill_body": "",
            }

            await temporal_state.client.start_workflow(
                "InvestigationWorkflow",
                workflow_input,
                id=f"investigation-{ex.id}",
                task_queue="investigation",
            )
            logger.info("temporal workflow started for execution %s", str(ex.id))
        except Exception:
            logger.exception("failed to start temporal workflow for execution %s", str(ex.id))

    return _serialize(ex)


@router.post("/{execution_id}/approve")
async def approve_execution(execution_id: str, req: ApproveRequest, db: AsyncSession = Depends(get_db)) -> dict:
    import pinky_api.temporal_state as temporal_state

    if temporal_state.client is None:
        raise HTTPException(status_code=503, detail="Temporal not available")

    try:
        handle = temporal_state.client.get_workflow_handle(f"investigation-{execution_id}")
        await handle.signal("approve", {"changeset_digest": req.changeset_digest})
        await emit(db, "approval.granted", "execution", UUID(execution_id), {"changeset_digest": req.changeset_digest})
        await db.commit()
        return {"status": "approved", "execution_id": execution_id}
    except Exception:
        logger.exception("failed to signal approval")
        raise HTTPException(status_code=500, detail="Failed to signal workflow")


@router.post("/{execution_id}/reject")
async def reject_execution(execution_id: str, req: RejectRequest, db: AsyncSession = Depends(get_db)) -> dict:
    import pinky_api.temporal_state as temporal_state

    if temporal_state.client is None:
        raise HTTPException(status_code=503, detail="Temporal not available")

    try:
        handle = temporal_state.client.get_workflow_handle(f"investigation-{execution_id}")
        await handle.signal("reject", {"reason": req.reason})
        await emit(db, "approval.rejected", "execution", UUID(execution_id), {"reason": req.reason})
        await db.commit()
        return {"status": "rejected", "execution_id": execution_id}
    except Exception:
        logger.exception("failed to signal rejection")
        raise HTTPException(status_code=500, detail="Failed to signal workflow")
