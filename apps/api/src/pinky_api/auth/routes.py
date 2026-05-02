"""Auth routes — login, callback, logout, session status."""

import secrets

from fastapi import APIRouter, HTTPException, Request, Response

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/login")
async def login(provider: str = "openshift") -> dict:
    if provider not in ("openshift", "oidc"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    state = secrets.token_urlsafe(32)
    # TODO: store state in Redis with short TTL for CSRF validation on callback
    # TODO: look up provider config, build authorize URL, return redirect

    return {"message": "Login not yet implemented", "provider": provider, "state": state}


@router.get("/callback")
async def callback(code: str, state: str, response: Response) -> dict:
    # TODO: validate state against Redis
    # TODO: exchange code for tokens via provider
    # TODO: get user info from provider
    # TODO: resolve/create principal (auto-link on verified email match)
    # TODO: create session, set HTTP-only cookie, rotate if existing session
    # TODO: log to session_audit_log

    return {"message": "Callback not yet implemented"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    # TODO: revoke session in Redis
    # TODO: clear session cookie
    # TODO: log to session_audit_log

    response.delete_cookie("pinky_session", httponly=True, secure=True, samesite="strict")
    return {"message": "Logged out"}


@router.get("/session")
async def session_status() -> dict:
    # TODO: return current session info (principal, expiry, cluster bindings)
    return {"message": "Session status not yet implemented"}
