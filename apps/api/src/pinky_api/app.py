import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sqlalchemy
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from pinky_api.auth.middleware import get_current_principal
from pinky_api.auth.routes import router as auth_router
from pinky_api.config import get_settings
from pinky_api.fleet.routes import router as fleet_router
from pinky_api.logging_config import configure_logging
from pinky_api.routes.alerts import router as alerts_router
from pinky_api.routes.analytics import router as analytics_router
from pinky_api.routes.api_tokens import router as api_tokens_router
from pinky_api.routes.definitions import router as definitions_router
from pinky_api.routes.executions import router as executions_router
from pinky_api.routes.history import router as history_router
from pinky_api.routes.issues import router as issues_router
from pinky_api.routes.policy_rules import router as policy_rules_router
from pinky_api.routes.streams import router as streams_router
from pinky_api.routes.webhooks import router as webhooks_router
from pinky_api.routes.work_items import router as work_items_router
from pinky_api.security.headers import SecurityHeadersMiddleware

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import redis.asyncio as aioredis

    import pinky_api.auth._state as auth_state
    from pinky_api.auth.session_store import SessionStore
    from pinky_api.db.engine import close_engine, init_engine

    settings = get_settings()
    init_engine(settings.database.url)

    redis_client = aioredis.from_url(settings.redis.url, decode_responses=True)
    auth_state.session_store = SessionStore(
        redis_client,
        idle_timeout_minutes=settings.auth.session_idle_timeout_minutes,
        absolute_timeout_hours=settings.auth.session_absolute_timeout_hours,
    )

    yield

    await redis_client.aclose()
    await close_engine()


app = FastAPI(
    title="Pinky API",
    version="0.1.0",
    lifespan=lifespan,
    dependencies=[Depends(get_current_principal)],
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-CSRF-Token"],
)


@app.middleware("http")
async def logging_context_middleware(request: Request, call_next):  # noqa: ANN201
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    return response


app.include_router(auth_router)
app.include_router(fleet_router)
app.include_router(work_items_router)
app.include_router(issues_router)
app.include_router(history_router)
app.include_router(alerts_router)
app.include_router(executions_router)
app.include_router(streams_router)
app.include_router(definitions_router)
app.include_router(webhooks_router)
app.include_router(policy_rules_router)
app.include_router(analytics_router)
app.include_router(api_tokens_router)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "")
    logger.exception("unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
                "request_id": request_id,
            }
        },
    )


@app.get("/api/v1/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/readyz")
async def readyz() -> JSONResponse:
    import pinky_api.auth._state as auth_state
    from pinky_api.db.engine import get_engine

    checks: dict[str, str] = {"db": "fail", "redis": "fail"}

    try:
        engine = get_engine()
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        checks["db"] = "ok"
    except Exception:
        logger.warning("readyz: DB check failed", exc_info=True)

    try:
        store = auth_state.session_store
        if store is not None:
            await store.ping()
            checks["redis"] = "ok"
    except Exception:
        logger.warning("readyz: Redis check failed", exc_info=True)

    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503
    body: dict[str, object] = {"status": "ready"} if all_ok else {"status": "not_ready", "checks": checks}
    return JSONResponse(content=body, status_code=status_code)
