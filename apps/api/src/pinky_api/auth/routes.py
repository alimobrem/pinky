"""Auth routes — login, callback, logout, session status.

Supports OpenShift OAuth and external OIDC. The callback exchanges
the authorization code with the provider, fetches user info, resolves
or creates the principal (auto-linking on verified email match),
creates a session in Redis, and sets the HTTP-only cookie.
"""

import logging
import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import pinky_api.auth._state as auth_state
from pinky_api.auth.middleware import SESSION_COOKIE_NAME
from pinky_api.auth.providers import AuthProvider, ProviderUserInfo
from pinky_api.config import get_settings
from pinky_api.db.deps import get_db
from pinky_api.models.principal import Principal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
cookie_scheme = APIKeyCookie(name=SESSION_COOKIE_NAME, auto_error=False)


def _get_provider(provider_type: str) -> AuthProvider:
    settings = get_settings()
    if provider_type == "openshift":
        issuer = settings.auth.openshift_issuer_url
        client_id = settings.auth.openshift_client_id
        client_secret = settings.auth.openshift_client_secret
    elif provider_type == "oidc":
        issuer = settings.auth.oidc_issuer_url
        client_id = settings.auth.oidc_client_id
        client_secret = settings.auth.oidc_client_secret
    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_type}")

    if not issuer or not client_id:
        raise HTTPException(status_code=501, detail=f"Provider {provider_type} not configured")

    return AuthProvider(provider_type, client_id, client_secret, issuer)


async def _resolve_principal(user_info: ProviderUserInfo, db: AsyncSession) -> dict:
    """Find or create principal. Auto-links when verified email matches."""
    # Try exact provider+subject match
    result = await db.execute(
        select(Principal).where(Principal.provider == user_info.provider, Principal.subject == user_info.subject)
    )
    principal = result.scalar_one_or_none()

    if principal is None and user_info.email and user_info.email_verified:
        result = await db.execute(select(Principal).where(Principal.email == user_info.email))
        principal = result.scalar_one_or_none()

    if principal is None:
        principal = Principal(
            provider=user_info.provider,
            subject=user_info.subject,
            display_name=user_info.display_name,
            email=user_info.email,
            groups=user_info.groups,
        )
        db.add(principal)
        await db.flush()
        logger.info("principal created", principal_id=str(principal.id), provider=user_info.provider)
    else:
        principal.display_name = user_info.display_name or principal.display_name
        principal.groups = user_info.groups or principal.groups
        if user_info.email and user_info.email_verified:
            principal.email = user_info.email
        await db.flush()

    return {
        "id": str(principal.id),
        "provider": principal.provider,
        "email": principal.email,
        "display_name": principal.display_name,
        "groups": list(principal.groups) if principal.groups else [],
        "is_admin": "pinky-admins" in (principal.groups or []),
    }


@router.get("/login")
async def login(provider: str = "openshift") -> dict:
    if provider not in ("openshift", "oidc"):
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    state = secrets.token_urlsafe(32)
    store = auth_state.session_store
    if store is None:
        raise HTTPException(status_code=503, detail="Session store not initialized")

    await store._redis.set(f"pinky:oauth_state:{state}", provider, ex=300)

    try:
        auth_provider = _get_provider(provider)
        settings = get_settings()
        redirect_uri = f"{settings.auth.callback_base_url}/api/v1/auth/callback"
        authorize_url = auth_provider.get_authorize_url(redirect_uri, state)
        return {"provider": provider, "state": state, "authorize_url": authorize_url}
    except HTTPException as e:
        if e.status_code == 501:
            return {"provider": provider, "state": state, "authorize_url": None, "note": f"Provider {provider} not configured"}
        raise


@router.get("/callback")
async def callback(code: str, state: str, response: Response, db: AsyncSession = Depends(get_db)) -> dict:
    store = auth_state.session_store
    if store is None:
        raise HTTPException(status_code=503, detail="Session store not initialized")

    stored_provider = await store._redis.get(f"pinky:oauth_state:{state}")
    if stored_provider is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    await store._redis.delete(f"pinky:oauth_state:{state}")

    auth_provider = _get_provider(stored_provider)
    settings = get_settings()
    redirect_uri = f"{settings.auth.callback_base_url}/api/v1/auth/callback"

    token_data = await auth_provider.exchange_code(code, redirect_uri)
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Provider did not return access_token")

    user_info = await auth_provider.get_user_info(access_token)
    principal_data = await _resolve_principal(user_info, db)
    await db.commit()

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

    logger.info("login successful", principal_id=principal_data["id"], provider=stored_provider)
    return {"csrf_token": csrf_token, "principal": principal_data}


@router.post("/logout")
async def logout(response: Response, session_token: str | None = Depends(cookie_scheme)) -> dict:
    if session_token and auth_state.session_store:
        await auth_state.session_store.revoke(session_token)
        logger.info("logout")

    response.delete_cookie(SESSION_COOKIE_NAME, httponly=True, secure=True, samesite="strict", path="/")
    return {"message": "Logged out"}


@router.get("/session")
async def session_status(session_token: str | None = Depends(cookie_scheme)) -> dict:
    if not session_token or not auth_state.session_store:
        return {"authenticated": False}

    principal = await auth_state.session_store.validate(session_token)
    if principal is None:
        return {"authenticated": False}

    age = await auth_state.session_store.get_session_age_minutes(session_token)
    return {"authenticated": True, "principal": principal, "session_age_minutes": age}
