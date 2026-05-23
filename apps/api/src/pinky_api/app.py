import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import sqlalchemy
import structlog
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from pinky_api.auth.middleware import get_current_principal
from pinky_api.auth.routes import router as auth_router
from pinky_api.config import get_settings
from pinky_api.db.deps import get_db
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
from pinky_api.routes.resources import router as resources_router
from pinky_api.routes.streams import router as streams_router
from pinky_api.routes.webhooks import router as webhooks_router
from pinky_api.routes.work_items import router as work_items_router
from pinky_api.security.headers import SecurityHeadersMiddleware

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    import os

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

    # OpenTelemetry initialization (opt-in via OTEL_EXPORTER_OTLP_ENDPOINT)
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otel_endpoint:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": "pinky-api"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
        logger.info("OpenTelemetry initialized", endpoint=otel_endpoint)

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
async def logging_context_middleware(request: Request, call_next) -> Response:
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
app.include_router(resources_router)


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


@app.get("/api/v1/health/workflows")
async def workflow_health(db: AsyncSession = Depends(get_db)) -> dict:
    from sqlalchemy import text
    queries = {
        "stuck_pending": (
            "SELECT count(*) FROM executions "
            "WHERE status = 'pending' AND execution_type = 'investigation' "
            "AND created_at < now() - interval '5 minutes'"
        ),
        "stuck_running": (
            "SELECT count(*) FROM executions "
            "WHERE status = 'running' AND created_at < now() - interval '30 minutes'"
        ),
        "stale_ready_tasks": (
            "SELECT count(*) FROM work_items "
            "WHERE status = 'ready' AND created_at < now() - interval '7 days'"
        ),
        "orphaned_tasks": (
            "SELECT count(*) FROM work_items "
            "WHERE status NOT IN ('done') "
            "AND issue_id IN (SELECT id FROM issues WHERE status IN ('resolved', 'suppressed'))"
        ),
        "mismatched_task_issue": (
            "SELECT count(*) FROM work_items "
            "WHERE status = 'done' "
            "AND issue_id IN (SELECT id FROM issues WHERE status = 'open')"
        ),
    }
    results = {}
    for name, query in queries.items():
        row = await db.execute(text(query))
        results[name] = row.scalar() or 0
    return results


@app.post("/api/v1/admin/reset-stale")
async def reset_stale(
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(get_current_principal),
) -> dict:
    if not principal.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")

    from sqlalchemy import CursorResult, text
    results = {}

    for key, sql in [
        ("stale_ready_expired",
         "UPDATE work_items SET status = 'done', updated_at = now() "
         "WHERE status = 'ready' AND created_at < now() - interval '7 days'"),
        ("stuck_in_progress_reset",
         "UPDATE work_items SET status = 'ready', owner_id = NULL, updated_at = now() "
         "WHERE status = 'in_progress' AND updated_at < now() - interval '24 hours'"),
        ("stuck_pending_failed",
         "UPDATE executions SET status = 'failed', completed_at = now() "
         "WHERE status = 'pending' AND created_at < now() - interval '10 minutes'"),
        ("stuck_running_failed",
         "UPDATE executions SET status = 'failed', completed_at = now() "
         "WHERE status = 'running' AND created_at < now() - interval '1 hour'"),
    ]:
        r: CursorResult = await db.execute(text(sql))  # type: ignore[assignment]
        results[key] = r.rowcount

    await db.commit()
    return results
