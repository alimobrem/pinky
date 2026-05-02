"""Three-layer authorization model.

Layer 1: Product authorization — does the principal have access to this feature?
Layer 2: Cluster authorization — valid binding + operation matches scope?
Layer 3: Execution authorization — risk class, approval state, session freshness?
"""

from enum import StrEnum
from typing import Any

from fastapi import HTTPException


class AuthzClass(StrEnum):
    PRODUCT_READ = "product_read"
    OBSERVER_READ = "observer_read"
    USER_SENSITIVE_READ = "user_sensitive_read"
    USER_WRITE = "user_write"
    ADMIN_CONTROL_PLANE = "admin_control_plane"


class Role(StrEnum):
    USER = "user"
    ADMIN = "admin"


VALID_BINDING_STATUSES = {"valid", "expiring"}


def check_product_authz(principal: dict, required_role: Role = Role.USER) -> None:
    if not principal:
        raise HTTPException(status_code=401, detail="Authentication required")
    if required_role == Role.ADMIN:
        groups = principal.get("groups", [])
        if "pinky-admins" not in groups and not principal.get("is_admin", False):
            raise HTTPException(status_code=403, detail="Admin access required")


def check_cluster_authz(
    authz_class: AuthzClass,
    cluster_binding: dict | None,
    observer_binding: dict | None = None,
) -> None:
    if authz_class == AuthzClass.OBSERVER_READ:
        if not observer_binding or observer_binding.get("health_state") == "unhealthy":
            raise HTTPException(status_code=503, detail="Observer binding unavailable for this cluster")
        return

    if authz_class in (AuthzClass.USER_SENSITIVE_READ, AuthzClass.USER_WRITE):
        if not cluster_binding:
            raise HTTPException(status_code=401, detail="Cluster binding required")
        if cluster_binding.get("status") not in VALID_BINDING_STATUSES:
            raise HTTPException(
                status_code=401,
                detail=f"Cluster binding {cluster_binding.get('status', 'missing')} — reauthentication required",
            )
        return


def check_execution_authz(
    authz_class: AuthzClass,
    risk_class: str = "standard",
    approval_status: str | None = None,
    session_age_minutes: int = 0,
) -> None:
    if authz_class != AuthzClass.USER_WRITE:
        return

    if risk_class == "very_high" and session_age_minutes > 15:
        raise HTTPException(
            status_code=401,
            detail="Very high risk action requires fresh reauthentication",
        )

    if risk_class in ("high", "very_high") and approval_status != "approved":
        raise HTTPException(
            status_code=403,
            detail="Approval required for this action",
        )
