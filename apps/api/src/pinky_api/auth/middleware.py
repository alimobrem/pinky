"""Auth middleware — session validation, CSRF, principal injection."""

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


async def get_current_principal(
    request: Request,
    session_token: str | None = Depends(cookie_scheme),
    auth_header: str | None = Depends(bearer_scheme),
) -> dict:
    if request.url.path in UNPROTECTED_PATHS:
        return {}

    # API token auth (CLI/CI)
    if auth_header and auth_header.startswith("Bearer "):
        api_token = auth_header[7:]
        token_hash = hash_token(api_token)
        # TODO: look up api_tokens table by token_hash, validate not revoked/expired
        raise HTTPException(status_code=401, detail="API token auth not yet implemented")

    # Session cookie auth
    if not session_token:
        raise HTTPException(status_code=401, detail="Authentication required")

    token_hash = hash_token(session_token)
    # TODO: look up session in Redis by token_hash, validate not expired/revoked
    # TODO: refresh idle timeout on valid session
    # TODO: return principal dict with id, provider, email, groups

    raise HTTPException(status_code=401, detail="Session validation not yet implemented")


def validate_csrf(request: Request) -> None:
    if request.method not in STATE_CHANGING_METHODS:
        return
    if request.url.path in UNPROTECTED_PATHS:
        return

    csrf_header = request.headers.get(CSRF_HEADER_NAME)
    if not csrf_header:
        raise HTTPException(status_code=403, detail="CSRF token missing")

    # TODO: compare csrf_header against session's csrf_token
