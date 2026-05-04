"""Auth dependencies for route-level authorization."""

from uuid import UUID

from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.authz import (
    AuthzClass,
    Role,
    check_cluster_authz,
    check_execution_authz,
    check_product_authz,
)
from pinky_api.auth.middleware import get_current_principal
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.service_bindings import ServiceBindingRepository


async def require_authenticated(
    principal: dict = Depends(get_current_principal),
) -> dict:
    if not principal or not principal.get("id"):
        raise HTTPException(status_code=401, detail="Authentication required")
    return principal


async def require_admin(
    principal: dict = Depends(require_authenticated),
) -> dict:
    check_product_authz(principal, Role.ADMIN)
    return principal


def principal_uuid(principal: dict) -> UUID:
    try:
        return UUID(principal["id"])
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid principal ID") from exc


def _binding_view(binding) -> dict | None:
    if binding is None:
        return None
    return {
        "status": getattr(binding, "status", None),
    }


def _observer_binding_view(binding) -> dict | None:
    if binding is None:
        return None
    return {
        "health_state": getattr(binding, "health_state", None),
    }


async def get_cluster_binding_for_principal(
    cluster_id: UUID,
    principal: dict,
    db: AsyncSession,
):
    repo = BindingRepository(db)
    return await repo.get_for_cluster(principal_uuid(principal), cluster_id)


async def get_observer_binding_for_cluster(
    cluster_id: UUID,
    db: AsyncSession,
):
    repo = ServiceBindingRepository(db)
    bindings = await repo.list(cluster_id=str(cluster_id))
    for binding in bindings:
        if binding.service_type == "observer":
            return binding
    return None


async def require_cluster_read_access(
    cluster_id: UUID,
    principal: dict,
    db: AsyncSession,
    *,
    sensitive: bool = False,
    require_binding: bool = False,
) -> None:
    observer_binding = await get_observer_binding_for_cluster(cluster_id, db)
    cluster_binding = await get_cluster_binding_for_principal(cluster_id, principal, db)
    if require_binding and cluster_binding is None:
        raise HTTPException(status_code=401, detail="Cluster binding required")
    authz_class = (
        AuthzClass.USER_SENSITIVE_READ
        if sensitive or require_binding
        else AuthzClass.OBSERVER_READ
    )
    check_cluster_authz(
        authz_class,
        cluster_binding=_binding_view(cluster_binding),
        observer_binding=_observer_binding_view(observer_binding),
    )


async def require_cluster_write_access(
    cluster_id: UUID,
    principal: dict,
    db: AsyncSession,
    *,
    risk_class: str = "standard",
    approval_status: str | None = None,
    session_age_minutes: int = 0,
) -> None:
    cluster_binding = await get_cluster_binding_for_principal(cluster_id, principal, db)
    check_cluster_authz(
        AuthzClass.USER_WRITE,
        cluster_binding=_binding_view(cluster_binding),
        observer_binding=None,
    )
    check_execution_authz(
        AuthzClass.USER_WRITE,
        risk_class=risk_class,
        approval_status=approval_status,
        session_age_minutes=session_age_minutes,
    )
