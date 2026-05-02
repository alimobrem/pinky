"""Auth middleware — session validation, CSRF, principal injection."""

import os

from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyCookie, APIKeyHeader

from pinky_api.security.crypto import hash_token

SESSION_COOKIE_NAME = "pinky_session"
CSRF_HEADER_NAME = "x-csrf-token"

cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)
bearer_scheme = APIKeyHeader(name="Authorization", auto_error=False)

UNPROTECTED_PATHS = {
    "/api/v1/healthz",
    "/api/v1/auth/login",
    "/api/v1/auth/callback",
}

STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _get_session_store() -> "SessionStore | None":
    from pinky_api.auth.session_store import SessionStore
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
        return {"id": "dev-user", "provider": "dev", "email": "dev@pinky.dev", "groups": ["pinky-admins"], "is_admin": True}

    # API token auth (CLI/CI)
    if auth_header and auth_header.startswith("Bearer "):
        api_token = auth_header[7:]
        token_hash = hash_token(api_token)
        # TODO: look up api_tokens table by token_hash, validate not revoked/expired
        raise HTTPException(status_code=401, detail="API token auth not yet implemented")

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
