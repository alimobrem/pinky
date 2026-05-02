"""Execution routes — Brain workflows and approval management."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/executions", tags=["executions"])


class ApproveRequest(BaseModel):
    changeset_digest: str


class RejectRequest(BaseModel):
    reason: str


@router.get("")
async def list_executions(
    work_item_id: str | None = None,
    cluster_id: str | None = None,
    status: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query executions table from Postgres projections
    return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/{execution_id}")
async def get_execution(execution_id: str) -> dict:
    # TODO: fetch execution detail + execution events
    raise HTTPException(status_code=404, detail="Execution not found")


@router.post("")
async def start_execution(work_item_id: str, execution_type: str = "investigation") -> dict:
    # TODO: validate authz (user binding required for cluster)
    # TODO: start Temporal workflow with fingerprint-based workflow ID
    # TODO: emit domain event execution.started
    return {"message": "Execution start not yet implemented"}


@router.post("/{execution_id}/approve")
async def approve_execution(execution_id: str, req: ApproveRequest) -> dict:
    # TODO: validate changeset_digest matches current changeset
    # TODO: check session freshness for risk class
    # TODO: send approval signal to Temporal ApprovalWorkflow
    # TODO: emit domain event approval.granted
    return {"message": "Approve not yet implemented"}


@router.post("/{execution_id}/reject")
async def reject_execution(execution_id: str, req: RejectRequest) -> dict:
    # TODO: send reject signal to Temporal ApprovalWorkflow
    # TODO: emit domain event approval.rejected
    return {"message": "Reject not yet implemented"}
