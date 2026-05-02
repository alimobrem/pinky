"""Fleet routes — cluster registry and binding management."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from pinky_api.auth.authz import AuthzClass, Role, check_product_authz

router = APIRouter(prefix="/api/v1", tags=["fleet"])

MAX_CLUSTERS_WITHOUT_OIDC = 5


class ClusterCreateRequest(BaseModel):
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None = None


class ClusterResponse(BaseModel):
    id: str
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None
    onboarding_state: str
    created_at: str


class BindingCreateRequest(BaseModel):
    cluster_id: str
    binding_method: str = "oauth"


class BindingResponse(BaseModel):
    id: str
    principal_id: str
    cluster_id: str
    binding_method: str
    status: str
    expires_at: str | None


# --- Cluster Registry (admin only) ---

@router.get("/clusters")
async def list_clusters() -> dict:
    # TODO: query cluster_registry table, paginate
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/clusters", status_code=201)
async def create_cluster(req: ClusterCreateRequest) -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: insert into cluster_registry
    # TODO: check cluster count — if > MAX_CLUSTERS_WITHOUT_OIDC, warn about OIDC requirement
    return {"message": "Cluster creation not yet implemented"}


@router.delete("/clusters/{cluster_id}", status_code=204)
async def remove_cluster(cluster_id: str) -> None:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: implement cluster removal cascade (ADR-19):
    #   - mark offboarded
    #   - 30-min drain for in-flight workflows
    #   - archive open tasks with cluster_removed resolution
    #   - revoke observer binding
    #   - emit cluster.removed domain event
    pass


# --- Cluster Bindings (user) ---

@router.get("/cluster-bindings")
async def list_bindings() -> dict:
    # TODO: query cluster_identity_bindings for current principal
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/cluster-bindings", status_code=201)
async def create_binding(req: BindingCreateRequest) -> dict:
    # TODO: check cluster count — if > MAX_CLUSTERS_WITHOUT_OIDC, require OIDC binding method
    # TODO: for oauth method, initiate per-cluster OAuth flow
    # TODO: for brokered method, check admin-managed binding
    # TODO: encrypt token, store in cluster_identity_bindings
    # TODO: emit binding.created domain event
    return {"message": "Binding creation not yet implemented"}


@router.post("/cluster-bindings/{binding_id}/refresh")
async def refresh_binding(binding_id: str) -> dict:
    # TODO: refresh the binding token, update expires_at
    return {"message": "Binding refresh not yet implemented"}


@router.delete("/cluster-bindings/{binding_id}", status_code=204)
async def revoke_binding(binding_id: str) -> None:
    # TODO: set status = revoked
    # TODO: return assigned tasks to team queue
    # TODO: emit binding.revoked domain event
    pass


# --- Service Bindings (admin) ---

@router.get("/service-bindings")
async def list_service_bindings() -> dict:
    # TODO: query service_bindings table
    return {"items": [], "next_cursor": None, "has_more": False}


@router.post("/service-bindings", status_code=201)
async def create_service_binding() -> dict:
    # TODO: check_product_authz(principal, Role.ADMIN)
    # TODO: encrypt credential, store in service_bindings
    return {"message": "Service binding creation not yet implemented"}


@router.delete("/service-bindings/{binding_id}", status_code=204)
async def remove_service_binding(binding_id: str) -> None:
    # TODO: check_product_authz(principal, Role.ADMIN)
    pass
