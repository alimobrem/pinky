# Pinky API

FastAPI backend serving 78 REST endpoints for the Pinky platform. Handles authentication, CRUD operations, cluster resource access, execution orchestration, SSE streaming, and the Brain chat interface.

## Running

```bash
make dev-api   # FastAPI with hot reload on :8000
```

Or manually:

```bash
cd apps/api
python -m uvicorn pinky_api.app:app --reload --port 8000
```

## Directory Structure

```
src/pinky_api/
  app.py                 Application entry, middleware, health checks
  config.py              Pydantic settings (PINKY_* env vars)
  auth/
    middleware.py         Session/token auth, principal injection
    deps.py              require_cluster_read_access, require_cluster_write_access
    providers.py          OpenShift OAuth provider
    authz.py             3-layer authorization (product, cluster, execution)
  routes/
    work_items.py         Task CRUD, status transitions, bulk, chat (15 endpoints)
    issues.py             Issue lifecycle — suppress, resolve, escalate (5 endpoints)
    executions.py         Workflow dispatch, approve, reject, cancel, preview (8 endpoints)
    streams.py            SSE endpoints for real-time updates (5 endpoints)
    resources.py          Direct K8s resource access via cluster bindings (5 endpoints)
    alerts.py             Watch page data (observations + executions) (1 endpoint)
    history.py            Audit trail with enrichment and export (2 endpoints)
    analytics.py          ROI metrics, scanner stats, watch summary (4 endpoints)
    definitions.py        Definition CRUD (4 endpoints)
    policy_rules.py       Policy rule management + evaluate (5 endpoints)
    webhooks.py           Webhook subscription management (4 endpoints)
    api_tokens.py         API token CRUD (3 endpoints)
  fleet/
    routes.py             Cluster registration, binding management
  models/                 SQLAlchemy 2 declarative models (24 tables)
  repositories/           Data access layer (cursor pagination, filtering)
  schemas/                Pydantic request/response schemas
  security/
    crypto.py             AES-256-GCM encryption/decryption
    headers.py            Security headers middleware (CSP, HSTS, etc.)
  k8s.py                  Lightweight K8s client (httpx, TLS-verified)
  events.py               Domain event emitter (pg_notify + domain_events table)
```

## Authentication

- **Session cookies:** HTTP-only, Secure, SameSite=Lax. Backed by Redis with idle/absolute timeouts.
- **API tokens:** HMAC-SHA256 hashed. Bearer auth via `Authorization` header.
- **OAuth:** OpenShift OIDC login flow. Token exchange + user info from K8s API.
- **All routes protected** via global `get_current_principal` dependency. Unprotected paths explicitly listed.

## Testing

```bash
cd apps/api
.venv/bin/pytest tests/ -v                          # 430 tests
.venv/bin/pytest tests/benchmark/ --benchmark-only  # 10 latency benchmarks
```

Test fixtures: `authed_client` (auth bypassed), `unauthed_client`, `non_admin_client`. Real Postgres database.
