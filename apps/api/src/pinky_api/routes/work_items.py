"""Work item routes — the core task-first API."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/work-items", tags=["work-items"])


class WorkItemResponse(BaseModel):
    id: str
    issue_id: str | None = None
    cluster_id: str
    title: str
    why_now: str | None = None
    recommended_next_step: str | None = None
    status: str
    owner_id: str | None = None
    confidence: float | None = None
    priority: str = "medium"
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    runbook_url: str | None = None
    created_at: str = ""
    updated_at: str = ""


VALID_TRANSITIONS: dict[str, set[str]] = {
    "ready": {"accepted"},
    "accepted": {"in_progress", "done"},
    "in_progress": {"blocked", "waiting_for_approval", "done"},
    "blocked": {"in_progress", "done"},
    "waiting_for_approval": {"in_progress"},
}


@router.get("")
async def list_work_items(
    cluster_id: str | None = None,
    status: str | None = None,
    owner: str | None = None,
    priority: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query work_items table with filters, cursor pagination
    return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/{work_item_id}")
async def get_work_item(work_item_id: str) -> dict:
    # TODO: fetch from DB with evidence, plan, execution refs
    raise HTTPException(status_code=404, detail="Work item not found")


@router.post("/{work_item_id}/accept")
async def accept_work_item(work_item_id: str) -> dict:
    # TODO: validate transition ready->accepted, set owner to current principal
    # TODO: emit domain event work_item.accepted
    # TODO: log to analytics_events
    return {"message": "Accept not yet implemented"}


@router.post("/{work_item_id}/start")
async def start_work_item(work_item_id: str) -> dict:
    # TODO: validate transition accepted->in_progress
    # TODO: emit domain event work_item.started
    return {"message": "Start not yet implemented"}


@router.post("/{work_item_id}/complete")
async def complete_work_item(work_item_id: str) -> dict:
    # TODO: validate transition to done
    # TODO: move to history
    # TODO: emit domain event work_item.completed
    return {"message": "Complete not yet implemented"}


@router.post("/{work_item_id}/reassign")
async def reassign_work_item(work_item_id: str, assignee_id: str) -> dict:
    # TODO: change owner_id
    # TODO: emit domain event work_item.reassigned
    return {"message": "Reassign not yet implemented"}
