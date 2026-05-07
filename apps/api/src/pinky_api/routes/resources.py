"""Resource routes — view and edit K8s resources using user's cluster binding."""

from __future__ import annotations

import logging
from uuid import UUID

import yaml
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import (
    get_cluster_binding_for_principal,
    require_authenticated,
    require_cluster_read_access,
    require_cluster_write_access,
)
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.k8s import apply_resource, get_resource
from pinky_api.repositories.clusters import ClusterRepository
from pinky_api.security.crypto import decrypt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/clusters", tags=["resources"])


def _parse_uuid(value: str, field: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=f"{field} not found") from exc


async def _resolve_token(cluster_id: UUID, principal: dict, db: AsyncSession) -> tuple[str, str]:
    from datetime import UTC, datetime

    cluster_repo = ClusterRepository(db)
    cluster = await cluster_repo.get(cluster_id)
    if cluster is None:
        raise HTTPException(status_code=404, detail="Cluster not found")

    binding = await get_cluster_binding_for_principal(cluster_id, principal, db)
    if binding is None or binding.encrypted_token is None:
        raise HTTPException(status_code=401, detail="Cluster binding required — log in to the cluster first")

    if binding.expires_at and binding.expires_at < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Cluster binding expired — please re-authenticate")

    try:
        token = decrypt(binding.encrypted_token, aad=f"cluster_identity_bindings:{binding.id}").decode()
    except Exception:
        logger.exception("token decryption failed for binding %s", binding.id)
        raise HTTPException(status_code=401, detail="Cluster binding invalid — please re-authenticate") from None
    return cluster.api_endpoint, token


@router.get("/{cluster_id}/resources/{namespace}/{kind}/{name}")
async def get_cluster_resource(
    cluster_id: str,
    namespace: str,
    kind: str,
    name: str,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    cid = _parse_uuid(cluster_id, "Cluster")
    await require_cluster_read_access(cid, principal, db, require_binding=True)

    api_endpoint, token = await _resolve_token(cid, principal, db)
    result = await get_resource(api_endpoint, token, namespace, kind, name)

    if result.get("error") == "not_found":
        raise HTTPException(status_code=404, detail=f"{kind}/{name} not found in {namespace}")
    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="Insufficient cluster permissions")

    resource_yaml = yaml.dump(result, default_flow_style=False, sort_keys=False)
    return {"resource": result, "yaml": resource_yaml}


class ApplyRequest(BaseModel):
    yaml_content: str


@router.put("/{cluster_id}/resources/{namespace}/{kind}/{name}")
async def apply_cluster_resource(
    cluster_id: str,
    namespace: str,
    kind: str,
    name: str,
    req: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(require_authenticated),
) -> dict:
    cid = _parse_uuid(cluster_id, "Cluster")
    await require_cluster_write_access(cid, principal, db)

    try:
        manifest = yaml.safe_load(req.yaml_content)
    except yaml.YAMLError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {exc}") from exc

    if not isinstance(manifest, dict):
        raise HTTPException(status_code=400, detail="YAML must be a mapping")

    api_endpoint, token = await _resolve_token(cid, principal, db)
    result = await apply_resource(api_endpoint, token, namespace, kind, name, manifest)

    if result.get("error") == "forbidden":
        raise HTTPException(status_code=403, detail="Insufficient cluster permissions")
    if result.get("error") == "invalid":
        raise HTTPException(status_code=422, detail=result.get("message", "Invalid resource"))

    await emit(db, "resource.applied", "cluster", cid, {
        "namespace": namespace, "kind": kind, "name": name,
    }, cluster_id=cid)
    await db.commit()

    updated_yaml = yaml.dump(result, default_flow_style=False, sort_keys=False)
    return {"resource": result, "yaml": updated_yaml}
