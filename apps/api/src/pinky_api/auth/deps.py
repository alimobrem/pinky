"""Auth dependencies for route-level authorization."""

from fastapi import Depends, HTTPException, Request

from pinky_api.auth.authz import Role, check_product_authz
from pinky_api.auth.middleware import get_current_principal


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
