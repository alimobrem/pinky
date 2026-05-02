"""Alerts routes — raw signal surface, separate from task queue."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


@router.get("")
async def list_alerts(
    cluster_id: str | None = None,
    severity: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query observations not yet correlated into issues, or raw alert sources
    return {"items": [], "next_cursor": None, "has_more": False}
