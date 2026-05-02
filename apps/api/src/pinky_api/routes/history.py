"""History routes — append-only audit and narrative surface."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/history", tags=["history"])


@router.get("")
async def list_history(
    cluster_id: str | None = None,
    aggregate_type: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
) -> dict:
    # TODO: query history_events table with filters
    return {"items": [], "next_cursor": None, "has_more": False}
