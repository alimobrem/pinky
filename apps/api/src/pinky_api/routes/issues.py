"""Issue routes — correlated operational problems."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/issues", tags=["issues"])


@router.get("")
async def list_issues(
    cluster_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query issues table with filters
    return {"items": [], "next_cursor": None, "has_more": False}


@router.get("/{issue_id}")
async def get_issue(issue_id: str) -> dict:
    # TODO: fetch with linked observations and work items
    raise HTTPException(status_code=404, detail="Issue not found")
