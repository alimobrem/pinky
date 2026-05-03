"""Fleet routes — cluster registry and binding management."""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import require_admin, require_authenticated
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.clusters import ClusterRepository

router = APIRouter(prefix="/api/v1", tags=["fleet"])

MAX_CLUSTERS_WITHOUT_OIDC = 5


class ClusterCreateRequest(BaseModel):
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None = None


class BindingCreateRequest(BaseModel):
    cluster_id: str
    binding_method: str = "token"


def _serialize_cluster(c: object) -> dict:
    return {
        "id": str(c.id),
        "display_name": c.display_name,
        "api_endpoint": c.api_endpoint,
        "fleet_identifier": c.fleet_identifier,
        "onboarding_state": c.onboarding_state,
        "offboarding_state": c.offboarding_state,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
    }


def _serialize_binding(b: object) -> dict:
    return {
        "id": str(b.id),
        "principal_id": str(b.principal_id),
        "cluster_id": str(b.cluster_id),
        "cluster_username": b.cluster_username,
        "cluster_groups": b.cluster_groups or [],
        "binding_method": b.binding_method,
        "status": b.status,
        "expires_at": b.expires_at.isoformat() if b.expires_at else None,
        "created_at": b.created_at.isoformat() if b.created_at else "",
        "updated_at": b.updated_at.isoformat() if b.updated_at else "",
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


# ── Cluster Identity Bindings ──


def _safe_uuid(value: str) -> UUID | None:
    try:
        return UUID(value)
    except (ValueError, AttributeError):
        return None


@router.get("/cluster-bindings")
async def list_bindings(
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    pid = _safe_uuid(principal["id"])
    if pid is None:
        return {"items": []}
    repo = BindingRepository(db)
    bindings = await repo.list_for_principal(pid)
    return {"items": [_serialize_binding(b) for b in bindings]}


@router.get("/cluster-bindings/status")
async def get_binding_status(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    pid = _safe_uuid(principal["id"])
    if pid is None:
        return {"status": "missing", "binding": None}
    repo = BindingRepository(db)
    binding = await repo.get_for_cluster(pid, UUID(cluster_id))
    if binding is None:
        return {"status": "missing", "binding": None}
    if binding.status == "valid" and binding.expires_at and binding.expires_at < datetime.utcnow():
        return {"status": "expired", "binding": _serialize_binding(binding)}
    if binding.status == "valid" and binding.expires_at and binding.expires_at < datetime.utcnow() + timedelta(hours=1):
        return {"status": "expiring", "binding": _serialize_binding(binding)}
    return {"status": binding.status, "binding": _serialize_binding(binding)}


@router.post("/cluster-bindings", status_code=201)
async def create_binding(
    req: BindingCreateRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = BindingRepository(db)
    pid = _safe_uuid(principal["id"])
    if pid is None:
        raise HTTPException(status_code=400, detail="Invalid principal ID")
    existing = await repo.get_for_cluster(pid, UUID(req.cluster_id))
    if existing and existing.status == "valid":
        return _serialize_binding(existing)

    if existing:
        binding = await repo.refresh(existing.id)
    else:
        binding = await repo.create(
            principal_id=pid,
            cluster_id=UUID(req.cluster_id),
            binding_method=req.binding_method,
            status="valid",
            expires_at=datetime.utcnow() + timedelta(hours=8),
        )

    await emit(db, "binding.created", "cluster", UUID(req.cluster_id), {"principal_id": principal["id"]})
    await db.commit()
    return _serialize_binding(binding)


@router.post("/cluster-bindings/{binding_id}/refresh")
async def refresh_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = BindingRepository(db)
    binding = await repo.refresh(UUID(binding_id))
    if binding is None:
        raise HTTPException(status_code=404, detail="Binding not found")
    await db.commit()
    return _serialize_binding(binding)


@router.delete("/cluster-bindings/{binding_id}", status_code=204)
async def revoke_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> None:
    repo = BindingRepository(db)
    revoked = await repo.revoke(UUID(binding_id))
    if not revoked:
        raise HTTPException(status_code=404, detail="Binding not found")
    await db.commit()


# ── Service Bindings (placeholder) ──


@router.get("/service-bindings")
async def list_service_bindings(db: AsyncSession = Depends(get_db)) -> dict:
    raise HTTPException(status_code=501, detail="Service bindings not implemented")


@router.post("/service-bindings", status_code=201)
async def create_service_binding(db: AsyncSession = Depends(get_db)) -> dict:
    raise HTTPException(status_code=501, detail="Service binding creation not implemented")


@router.delete("/service-bindings/{binding_id}", status_code=204)
async def remove_service_binding(binding_id: str) -> None:
    raise HTTPException(status_code=501, detail="Service binding removal not implemented")
