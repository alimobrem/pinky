"""Alerts routes — raw signal surface, separate from task queue."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import principal_uuid, require_authenticated, require_cluster_read_access
from pinky_api.db.deps import get_db
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.observations import ObservationRepository

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def _serialize(obs: Any) -> dict:
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
    principal: dict = Depends(require_authenticated),
) -> dict:
    binding_repo = BindingRepository(db)
    allowed_clusters = await binding_repo.list_accessible_cluster_ids(principal_uuid(principal))
    if cluster_id:
        await require_cluster_read_access(UUID(cluster_id), principal, db, require_binding=True)
    repo = ObservationRepository(db)
    result = await repo.list(
        cluster_id=cluster_id,
        cluster_ids=None if cluster_id else allowed_clusters,
        severity=severity,
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [_serialize(o) for o in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(result["items"])),
    }
