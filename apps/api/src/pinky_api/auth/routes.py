"""Auth routes — login, callback, logout, session status."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import APIKeyCookie

import pinky_api.auth._state as auth_state
from pinky_api.auth.middleware import SESSION_COOKIE_NAME

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


@router.get("/login")
async def login(provider: str = "openshift") -> dict:
    if provider not in ("openshift", "oidc"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    state = secrets.token_urlsafe(32)

    store = auth_state.session_store
    if store is not None:
        await store._redis.set(f"pinky:oauth_state:{state}", provider, ex=300)

    return {"provider": provider, "state": state}


@router.get("/callback")
async def callback(code: str, state: str, response: Response) -> dict:
    store = auth_state.session_store
    if store is None:
        raise HTTPException(status_code=503, detail="Session store not initialized")

    stored_provider = await store._redis.get(f"pinky:oauth_state:{state}")
    if stored_provider is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    await store._redis.delete(f"pinky:oauth_state:{state}")

    # TODO: exchange code with provider, get user info
    # For now, create a dev principal from the callback
    principal_data = {
        "id": f"principal-{secrets.token_hex(4)}",
        "provider": stored_provider,
        "email": "user@example.com",
        "groups": [],
        "is_admin": False,
    }

    raw_token, csrf_token = await store.create(
        principal_id=principal_data["id"],
        principal_data=principal_data,
    )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
        max_age=int(store.absolute_timeout.total_seconds()),
    )

    return {"csrf_token": csrf_token, "principal": principal_data}


@router.post("/logout")
async def logout(
    response: Response,
    session_token: str | None = Depends(cookie_scheme),
) -> dict:
    if session_token and auth_state.session_store:
        await auth_state.session_store.revoke(session_token)

    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, secure=True, samesite="strict", path="/")
    return {"message": "Logged out"}


@router.get("/session")
async def session_status(
    session_token: str | None = Depends(cookie_scheme),
) -> dict:
    if not session_token or not auth_state.session_store:
        return {"authenticated": False}

    principal = await auth_state.session_store.validate(session_token)
    if principal is None:
        return {"authenticated": False}

    age = await auth_state.session_store.get_session_age_minutes(session_token)
    return {
        "authenticated": True,
        "principal": principal,
        "session_age_minutes": age,
    }
