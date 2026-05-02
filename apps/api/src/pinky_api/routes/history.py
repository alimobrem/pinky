"""History routes — append-only audit and narrative surface."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.repositories.history import HistoryRepository

router = APIRouter(prefix="/api/v1/history", tags=["history"])


def _serialize(event: object) -> dict:
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
        event_type=event_type, limit=limit, cursor=cursor,
    )
    return {
        "items": [_serialize(e) for e in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }
