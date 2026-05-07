"""Auth middleware — session validation, CSRF, principal injection."""

import logging
import os
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie, APIKeyHeader
from sqlalchemy import select, update

if TYPE_CHECKING:
    from pinky_api.auth.session_store import SessionStore

logger = logging.getLogger(__name__)

SESSION_COOKIE_NAME = "pinky_session"
CSRF_HEADER_NAME = "x-csrf-token"

cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)
bearer_scheme = APIKeyHeader(name="Authorization", auto_error=False)

UNPROTECTED_PATHS = {
    "/api/v1/healthz",
    "/api/v1/readyz",
    "/api/v1/auth/login",
    "/api/v1/auth/callback",
    "/api/v1/auth/test-login",
}

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _get_session_store() -> "SessionStore | None":
    import pinky_api.auth._state as state
    return state.session_store


async def get_current_principal(
    request: Request,
    session_token: str | None = Depends(cookie_scheme),
    auth_header: str | None = Depends(bearer_scheme),
) -> dict:
    if request.url.path in UNPROTECTED_PATHS:
        return {}

    # Dev mode bypass — never enable in production
    if os.environ.get("PINKY_DEV_AUTH_BYPASS") == "true":
        return {
            "id": "dev-user",
            "provider": "dev",
            "email": "dev@pinky.dev",
            "groups": ["pinky-admins"],
            "is_admin": True,
        }

    # API token auth (CLI/CI)
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        return await _validate_api_token(raw_token)

    # Session cookie auth
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    store = _get_session_store()
    if store is None:
        raise HTTPException(status_code=503, detail="Session store not initialized")

    principal = await store.validate(session_token)
    if principal is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # CSRF validation for state-changing requests
    if request.method in STATE_CHANGING_METHODS:
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        if not csrf_header:
            raise HTTPException(status_code=403, detail="CSRF token missing")

        expected_csrf = await store.get_csrf_token(session_token)
        if expected_csrf is None or csrf_header != expected_csrf:
            raise HTTPException(status_code=403, detail="CSRF token invalid")

    return principal


async def _validate_api_token(raw_token: str) -> dict:
    from pinky_api.db.engine import get_session_factory
    from pinky_api.models.extensibility import ApiToken
    from pinky_api.models.principal import Principal
    from pinky_api.security.crypto import hash_token

    try:
        factory = get_session_factory()
    except RuntimeError:
        raise HTTPException(status_code=503, detail="Database not initialized") from None

    token_hash_value = hash_token(raw_token)

    async with factory() as db:
        stmt = select(ApiToken).where(ApiToken.token_hash == token_hash_value)
        result = await db.execute(stmt)
        token_row = result.scalar_one_or_none()

        if token_row is None:
            raise HTTPException(status_code=401, detail="Invalid API token")

        if token_row.revoked_at is not None:
            raise HTTPException(status_code=401, detail="API token has been revoked")

        now = datetime.now(UTC)
        expires_at = token_row.expires_at
        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=UTC)
            if expires_at <= now:
                raise HTTPException(status_code=401, detail="API token has expired")

        # Update last_used_at
        await db.execute(
            update(ApiToken)
            .where(ApiToken.id == token_row.id)
            .values(last_used_at=now)
        )

        # Look up the principal to build context
        principal_stmt = select(Principal).where(Principal.id == token_row.principal_id)
        principal_result = await db.execute(principal_stmt)
        principal_row = principal_result.scalar_one_or_none()

        await db.commit()

    if principal_row is None:
        logger.error("API token references nonexistent principal %s", token_row.principal_id)
        raise HTTPException(status_code=401, detail="Invalid API token")

    groups = principal_row.groups if principal_row.groups else []
    return {
        "id": str(principal_row.id),
        "provider": principal_row.provider,
        "email": principal_row.email or "",
        "groups": groups,
        "is_admin": "pinky-admins" in groups,
        "auth_method": "api_token",
        "token_scopes": list(token_row.scopes) if token_row.scopes else [],
    }
