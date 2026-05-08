"""Fleet routes — cluster registry and binding management."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import principal_uuid, require_admin, require_authenticated
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.models.fleet import ClusterObserverBinding
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.clusters import ClusterRepository
from pinky_api.repositories.service_bindings import ServiceBindingRepository
from pinky_api.security.crypto import encrypt

router = APIRouter(prefix="/api/v1", tags=["fleet"])

MAX_CLUSTERS_WITHOUT_OIDC = 5


class ClusterCreateRequest(BaseModel):
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None = None


class BindingCreateRequest(BaseModel):
    cluster_id: str
    binding_method: str = "oauth_login"


class ServiceBindingCreateRequest(BaseModel):
    name: str
    service_type: str
    cluster_id: str | None = None
    base_url: str
    auth_method: str
    credential: str


def _serialize_cluster(c: Any) -> dict:
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


def _serialize_binding(b: Any) -> dict:
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


def _serialize_service_binding(b: Any) -> dict:
    return {
        "id": str(b.id),
        "name": b.name,
        "service_type": b.service_type,
        "cluster_id": str(b.cluster_id) if b.cluster_id else None,
        "base_url": b.base_url,
        "auth_method": b.auth_method,
        "health_state": b.health_state,
        "last_check_at": b.last_check_at.isoformat() if b.last_check_at else None,
        "created_at": b.created_at.isoformat() if b.created_at else "",
        "updated_at": b.updated_at.isoformat() if b.updated_at else "",
    }


@router.get("/clusters")
async def list_clusters(
    limit: int = 50,
    cursor: str | None = None,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = ClusterRepository(db)
    result = await repo.list(limit=limit, cursor=cursor)
    return {
        "items": [_serialize_cluster(c) for c in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(result["items"])),
    }


@router.get("/clusters/{cluster_id}")
async def get_cluster(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    cid = _safe_uuid(cluster_id)
    if cid is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    repo = ClusterRepository(db)
    cluster = await repo.get(cid)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")
    result = _serialize_cluster(cluster)
    obs_binding_result = await db.execute(
        select(ClusterObserverBinding).where(ClusterObserverBinding.cluster_id == cid)
    )
    obs_binding = obs_binding_result.scalar_one_or_none()
    if obs_binding:
        result["observer_health"] = obs_binding.health_state
        last_obs = obs_binding.last_observation_at
        result["last_observation_at"] = last_obs.isoformat() if last_obs else None
    else:
        from pinky_api.models.observation import Observation
        last_obs_result = await db.execute(
            select(Observation.observed_at)
            .where(Observation.cluster_id == cid)
            .order_by(Observation.observed_at.desc())
            .limit(1)
        )
        last_row = last_obs_result.scalar_one_or_none()
        if last_row:
            age = (datetime.now(UTC) - last_row).total_seconds()
            result["observer_health"] = "healthy" if age < 600 else "degraded"
            result["last_observation_at"] = last_row.isoformat()
        else:
            result["observer_health"] = "unknown"
            result["last_observation_at"] = None
    return result


@router.post("/clusters", status_code=201)
async def create_cluster(
    req: ClusterCreateRequest, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> dict:
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
async def remove_cluster(
    cluster_id: str, db: AsyncSession = Depends(get_db), _admin: dict = Depends(require_admin),
) -> None:
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
    pid = principal_uuid(principal)
    repo = BindingRepository(db)
    bindings = await repo.list_for_principal(pid)
    return {"items": [_serialize_binding(b) for b in bindings]}


@router.get("/cluster-bindings/status")
async def get_binding_status(
    cluster_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    pid = principal_uuid(principal)
    repo = BindingRepository(db)
    binding = await repo.get_for_cluster(pid, UUID(cluster_id))
    if binding is None:
        return {"status": "missing", "binding": None}
    if binding.status == "valid" and binding.expires_at and binding.expires_at < datetime.now(UTC):
        return {"status": "expired", "binding": _serialize_binding(binding)}
    if binding.status == "valid" and binding.expires_at and binding.expires_at < datetime.now(UTC) + timedelta(hours=1):
        return {"status": "expiring", "binding": _serialize_binding(binding)}
    return {"status": binding.status, "binding": _serialize_binding(binding)}


@router.post("/cluster-bindings", status_code=201)
async def create_binding(
    req: BindingCreateRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = BindingRepository(db)
    pid = principal_uuid(principal)
    cluster_uuid = UUID(req.cluster_id)
    existing = await repo.get_for_cluster(pid, cluster_uuid)
    not_expired = (
        existing
        and existing.status == "valid"
        and existing.expires_at
        and existing.expires_at > datetime.now(UTC)
    )
    if not_expired:
        return _serialize_binding(existing)

    if existing:
        binding = await repo.refresh(existing.id)
    else:
        binding = await repo.create(
            principal_id=pid,
            cluster_id=cluster_uuid,
            binding_method=req.binding_method,
            status="valid",
            expires_at=datetime.now(UTC) + timedelta(hours=8),
        )

    await emit(
        db, "binding.created", "cluster", cluster_uuid,
        {"principal_id": principal["id"]}, cluster_id=cluster_uuid, principal_id=pid,
    )
    await db.commit()
    return _serialize_binding(binding)


@router.post("/cluster-bindings/{binding_id}/refresh")
async def refresh_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    repo = BindingRepository(db)
    binding_uuid = UUID(binding_id)
    current = await repo.get(binding_uuid)
    if current is None:
        raise HTTPException(status_code=404, detail="Binding not found")
    pid = principal_uuid(principal)
    if current.principal_id != pid and not principal.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    binding = await repo.refresh(binding_uuid)
    if binding is None:
        raise HTTPException(status_code=404, detail="Binding not found")
    await db.commit()
    return _serialize_binding(binding)


@router.delete("/cluster-bindings/{binding_id}", status_code=204)
async def revoke_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> None:
    repo = BindingRepository(db)
    binding_uuid = UUID(binding_id)
    current = await repo.get(binding_uuid)
    if current is None:
        raise HTTPException(status_code=404, detail="Binding not found")
    pid = principal_uuid(principal)
    if current.principal_id != pid and not principal.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")
    revoked = await repo.revoke(binding_uuid)
    if not revoked:
        raise HTTPException(status_code=404, detail="Binding not found")
    await db.commit()


# ── Service Bindings (placeholder) ──


@router.get("/service-bindings")
async def list_service_bindings(
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> dict:
    repo = ServiceBindingRepository(db)
    bindings = await repo.list()
    return {"items": [_serialize_service_binding(b) for b in bindings], "next_cursor": None, "has_more": False}


@router.post("/service-bindings", status_code=201)
async def create_service_binding(
    req: ServiceBindingCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
) -> dict:
    repo = ServiceBindingRepository(db)
    binding = await repo.create(
        name=req.name,
        service_type=req.service_type,
        cluster_id=UUID(req.cluster_id) if req.cluster_id else None,
        base_url=req.base_url,
        auth_method=req.auth_method,
        encrypted_credential=b"",
        created_by=principal_uuid(admin),
    )
    binding.encrypted_credential = encrypt(
        req.credential.encode(),
        aad=f"service_binding:{binding.id}",
    )
    await db.commit()
    return _serialize_service_binding(binding)


@router.delete("/service-bindings/{binding_id}", status_code=204)
async def remove_service_binding(
    binding_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> None:
    repo = ServiceBindingRepository(db)
    deleted = await repo.delete(UUID(binding_id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Service binding not found")
    await db.commit()
