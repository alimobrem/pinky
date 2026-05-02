"""Alerts routes — raw signal surface, separate from task queue."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.repositories.observations import ObservationRepository

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _serialize(obs: object) -> dict:
    return {
        "id": str(obs.id),
        "cluster_id": str(obs.cluster_id),
        "scanner": obs.scanner,
        "fingerprint": obs.fingerprint,
        "check_id": obs.check_id,
        "severity": obs.severity,
        "resource_kind": obs.resource_kind,
        "resource_namespace": obs.resource_namespace,
        "resource_name": obs.resource_name,
        "payload": obs.payload or {},
        "observed_at": obs.observed_at.isoformat() if obs.observed_at else "",
    }


@router.get("")
async def list_alerts(
    cluster_id: str | None = None,
    severity: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = ObservationRepository(db)
    result = await repo.list(cluster_id=cluster_id, severity=severity, limit=limit, cursor=cursor)
    return {"items": [_serialize(o) for o in result["items"]], "next_cursor": result["next_cursor"], "has_more": result["has_more"]}
