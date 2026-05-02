"""Fleet routes — cluster registry and binding management."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin, require_authenticated
from pinky_api.db.deps import get_db
from pinky_api.repositories.clusters import ClusterRepository

router = APIRouter(prefix="/api/v1", tags=["fleet"])

MAX_CLUSTERS_WITHOUT_OIDC = 5


class ClusterCreateRequest(BaseModel):
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None = None


def _serialize_cluster(c: object) -> dict:
    return {
        "id": str(c.id),
        "display_name": c.display_name,
        "api_endpoint": c.api_endpoint,
        "fleet_identifier": c.fleet_identifier,
        "onboarding_state": c.onboarding_state,
        "offboarding_state": c.offboarding_state,
        "created_at": c.created_at.isoformat() if c.created_at else "",
    }


@router.get("/clusters")
async def list_clusters(
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = ClusterRepository(db)
    result = await repo.list(limit=limit, cursor=cursor)
    return {
        "items": [_serialize_cluster(c) for c in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.post("/clusters", status_code=201)
async def create_cluster(req: ClusterCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin)) -> dict:
    repo = ClusterRepository(db)
    count = await repo.count()
    cluster = await repo.create(
        display_name=req.display_name,
        api_endpoint=req.api_endpoint,
        fleet_identifier=req.fleet_identifier,
    )
    await db.commit()

    response = _serialize_cluster(cluster)
    if count >= MAX_CLUSTERS_WITHOUT_OIDC:
        response["warning"] = "More than 5 clusters registered — external OIDC is required for cluster bindings"
    return response


@router.delete("/clusters/{cluster_id}", status_code=204)
async def remove_cluster(cluster_id: str, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin)) -> None:
    repo = ClusterRepository(db)
    deleted = await repo.delete(UUID(cluster_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Cluster not found")
    await db.commit()


@router.get("/cluster-bindings")
async def list_bindings(db: AsyncSession = Depends(get_db)) -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/cluster-bindings", status_code=201)
async def create_binding(db: AsyncSession = Depends(get_db)) -> dict:
    return {"message": "Binding creation not yet implemented"}


@router.post("/cluster-bindings/{binding_id}/refresh")
async def refresh_binding(binding_id: str) -> dict:
    return {"message": "Binding refresh not yet implemented"}


@router.delete("/cluster-bindings/{binding_id}", status_code=204)
async def revoke_binding(binding_id: str) -> None:
    pass


@router.get("/service-bindings")
async def list_service_bindings(db: AsyncSession = Depends(get_db)) -> dict:
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/service-bindings", status_code=201)
async def create_service_binding(db: AsyncSession = Depends(get_db)) -> dict:
    return {"message": "Service binding creation not yet implemented"}


@router.delete("/service-bindings/{binding_id}", status_code=204)
async def remove_service_binding(binding_id: str) -> None:
    pass
