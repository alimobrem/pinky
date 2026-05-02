from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pinky_api.auth.routes import router as auth_router
from pinky_api.config import get_settings
from pinky_api.fleet.routes import router as fleet_router
from pinky_api.routes.alerts import router as alerts_router
from pinky_api.routes.analytics import router as analytics_router
from pinky_api.routes.definitions import router as definitions_router
from pinky_api.routes.executions import router as executions_router
from pinky_api.routes.history import router as history_router
from pinky_api.routes.issues import router as issues_router
from pinky_api.routes.policy_rules import router as policy_rules_router
from pinky_api.routes.streams import router as streams_router
from pinky_api.routes.webhooks import router as webhooks_router
from pinky_api.routes.work_items import router as work_items_router
from pinky_api.security.headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    # TODO: initialize database pool, redis, definition loader
    yield
    # TODO: cleanup


app = FastAPI(
    title="Pinky API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/api/v1/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
