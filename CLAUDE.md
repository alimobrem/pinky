# CLAUDE.md

## Project

Pinky — greenfield multi-cluster Kubernetes operations platform with embedded SRE agent "The Brain". Task-first (not alert-first), async-first, workflow-driven. Markdown-driven extensibility for scanners, tools, skills, pipelines, and policies.

## Stack

- **Web:** Next.js 15 + React 19 + TypeScript (apps/web)
  - **Styling:** Tailwind CSS v4 (@theme tokens, @layer base) + shadcn/ui (28 components) — no inline styles, no CSS modules
  - **Data fetching:** TanStack Query with co-located `queries.ts` per page — no raw fetch/useState
  - **Animation:** Motion v12 — FadeIn, StaggerList, AnimatePresence
  - **Real-time:** SSE via `useSSE` hook on tasks, dashboard, watch pages
  - **Forms:** react-hook-form + Zod schemas
  - **Dates:** date-fns (relative timestamps for < 24h)
  - **Types:** Import from `@pinky/contracts` — never redeclare types locally
  - **Icons:** lucide-react
- **API:** FastAPI + Pydantic v2 + SQLAlchemy 2 async + asyncpg (apps/api)
- **Worker:** Temporal SDK + Python 3.12 (apps/worker)
- **CLI:** typer (apps/cli)
- **Contracts:** Shared TypeScript types (packages/contracts)
- **Design System:** React components (packages/design-system)
- **Database:** PostgreSQL 16 (24 tables, Alembic migrations)
- **Session Store:** Redis 7
- **Workflow Runtime:** Temporal
- **Real-time:** SSE (not WebSocket)
- **Encryption:** AES-256-GCM envelope encryption with key versioning and AAD

## Commands

```bash
# Dev environment
make dev-infra          # Start Postgres, Redis, Temporal (podman compose)
make dev-api            # FastAPI with hot reload on :8000
make dev-worker         # Temporal worker
make dev-web            # Next.js on :3000
make dev                # All of the above
make dev-web-clean      # Clear .next cache + restart (fixes stale chunk errors)

# Quality
make lint               # ruff (Python) + eslint (TypeScript)
make typecheck          # pyright + tsc
make test               # pytest + vitest
make verify             # lint + typecheck + test

# Database
make db-upgrade         # Run Alembic migrations
make db-migrate MSG="description"  # Generate new migration

# Temporal
make temporal-init      # Create pinky namespace
```

## Architecture

### Monorepo Layout
```
apps/web/          → Next.js UI (Dashboard, Tasks, Watch, History, Clusters, Settings, Login)
apps/api/          → FastAPI API server (63 endpoints across /api/v1/*)
apps/worker/       → Temporal workflows + observers + projectors
apps/cli/          → CLI wrapping REST API
packages/contracts/ → Shared TypeScript domain types
packages/design-system/ → React component library
definitions/       → Markdown-driven extensibility (scanners, tools, skills, pipelines, policies, redaction rules)
infra/docker/      → docker-compose + Dockerfiles
infra/helm/        → Helm chart
```

### Key Patterns
- **Auth:** Global `get_current_principal` dependency on all routes. Unprotected paths in `UNPROTECTED_PATHS` set. Session cookies (HTTP-only, Secure, SameSite=Strict) + API tokens for CLI.
- **Authz:** 3-layer model in `auth/authz.py` — product authz, cluster authz, execution authz. Observer reads vs user-sensitive reads vs user writes.
- **Crypto:** `security/crypto.py` — AES-256-GCM with key version prefix + AAD binding. HMAC-SHA256 for token hashing. Never `# type: ignore`.
- **Definitions:** Markdown files with YAML frontmatter. Loaded from `definitions/` directory. DB overrides via API. Worker loads via `DefinitionRegistry`. 53 definitions ship out of box: 13 scanners, 8 tools, 11 skills, 16 policies, 3 pipelines, 2 redaction rules.
- **Policy:** Declarative rules in `policy/engine.py`. Priority-ordered, first-match-wins. No LLM in the policy pipeline. Supports 8 condition fields and 5 action types. Observer dispatches Temporal workflows on `investigate` decisions.
- **Observation:** Generic scanner executor in `generic_scanner.py` — interprets structured YAML checks in scanner frontmatter. 18 operators (eq, gt, condition_status, age_gt, cert_expires_within, quantity_gte, promql_gt, etc.), compound conditions (all/any), nested iteration. No hardcoded runner functions — operators add scanners with just markdown. Recurrence counting via observation count per correlation key. Prometheus integration via `prom_client.py` for PromQL-based checks. Operator-managed detection (OLM labels, ownerRefs, annotations). Root-cause correlation (NotReady nodes suppress pod observations). Age threshold (5min default, env-configurable). Completed job filtering.
- **Workflows:** 4 Temporal workflows (Investigation, Remediation, Approval, Verification). Activities in `execution/activities.py`. Workflow ID derived from issue fingerprint to prevent duplicates. `gather_evidence` is skill-aware — reads the skill's `tools` list and calls tool-specific K8s API functions (logs, top, describe, rollout, helm-history).
- **SSE:** Singleton `EventBusProvider` at shell level — one EventSource per session, components subscribe via `useEventBus(id, handler)`. Heartbeat every 15s. Reconnect with `Last-Event-ID`. Auth-expired/binding-expired sentinel events.
- **Pagination:** Cursor-based via `usePaginatedData` hook — accumulates pages, resets on SSE events. DataTable has Load More footer with total count.
- **Cluster Names:** API returns `cluster_display_name` on all responses via shared `resolve_cluster_names` helper. Frontend never maintains cluster ID→name maps.
- **API Tokens:** CRUD at `/v1/api-tokens`. HMAC-SHA256 hashed, plaintext returned once on creation. Bearer auth in middleware alongside session cookies.
- **Logging:** structlog for structured JSON logging in production, console in dev. Request ID bound to context per request via `logging_config.py`.
- **Health:** `/healthz` (always 200) + `/readyz` (checks DB + Redis connectivity). Helm readiness probe uses `/readyz`.
- **Graceful Shutdown:** Worker handles SIGTERM/SIGINT. Observer checks shutdown event before each scan cycle.
- **Models:** SQLAlchemy 2 declarative in `models/`. Alembic for migrations. 20 tables (4 dead tables dropped: history_events, eval_runs, session_audit_log, projection_cursors). Extensibility tables: definitions, service_bindings, domain_events, webhooks, policy_rules, api_tokens.

### Secret Management
- Secrets stored in `secrets/` directory (gitignored), never committed
- `scripts/deploy.sh` creates K8s secrets from local files before Helm install
- OAuth client secret: `secrets/oauth-client-secret`
- Vertex AI credentials: `secrets/vertex-credentials.json`
- Encryption key: auto-generated by Helm, preserved across upgrades via `lookup`
- `scripts/preflight.sh` scans for accidental secret commits pre-push

### Security
- Strict CSP (no unsafe-inline, no unsafe-eval)
- CSRF via double-submit cookie (`X-CSRF-Token` header)
- All containers non-root (UID 1001), read-only rootfs
- Cluster credentials encrypted at rest (AES-256-GCM with AAD)
- Evidence redacted before LLM prompts (11 patterns: bearer tokens, connection strings, env vars, K8s JWTs, kubeconfig fields, AWS/GCP metadata, Helm release secrets)
- Observer identity isolated from user execution identity
- >5 clusters requires external OIDC (per-cluster OAuth doesn't scale)

## Testing

```bash
# API tests (274 unit/integration + 10 benchmarks)
cd apps/api && .venv/bin/pytest tests/ --ignore=tests/benchmark -v
cd apps/api && .venv/bin/pytest tests/benchmark/ -v --benchmark-only  # perf only

# Worker tests (543 unit + 26 integration + 36 evals)
cd apps/worker && .venv/bin/pytest tests/ -v                          # unit + integration
cd apps/worker && .venv/bin/pytest evals/ -v                          # LLM eval graders

# CLI tests (18 tests)
cd apps/cli && .venv/bin/pytest tests/ -v

# Contracts tests (11 tests)
pnpm --filter @pinky/contracts test

# Web E2E (Playwright)
cd apps/web && npx playwright test

# Web typecheck
pnpm --filter @pinky/web typecheck

# Everything
make verify  # lint + typecheck + test
```

**API fixtures:** `authed_client` (auth bypassed with test principal), `unauthed_client`, `non_admin_client`. Encryption key via `monkeypatch`. Real Postgres.

**Worker integration fixtures:** `workflow_env` (session-scoped Temporal dev server), `conn` (transaction-wrapped Postgres connection with rollback), `FakePool` (unified mock for both `pool.execute()` and `pool.acquire()` patterns), `cluster_id`/`execution_id` (auto-seeded FK dependencies).

**LLM eval framework:** Evidence fixtures in `evals/fixtures/` (OOM, CrashLoop, ImagePull), expectations in `evals/expectations/`. Deterministic graders: structure, safety, relevance, redaction. No LLM calls needed for deterministic evals.

**CI:** 4 jobs in ci.yml (api-tests, worker-tests, worker-integration, web-checks). Weekly eval.yml and perf.yml workflows.

## OAuth (OpenShift)

Dev cluster: `your-cluster.example.com`

```bash
# Required env vars for OAuth login
PINKY_AUTH__OPENSHIFT_ISSUER_URL=https://oauth-openshift.apps.your-cluster.example.com
PINKY_AUTH__OPENSHIFT_CLIENT_ID=pinky
PINKY_AUTH__OPENSHIFT_CLIENT_SECRET=<from secrets/oauth-client-secret>
PINKY_AUTH__OPENSHIFT_API_URL=https://api.your-cluster.example.com:6443
PINKY_AUTH__CALLBACK_BASE_URL=http://localhost:8000
PINKY_AUTH__COOKIE_DOMAIN=localhost
PINKY_AUTH__APP_URL=http://localhost:3000
```

Key architecture:
- **Issuer URL** = OAuth route (for authorize + token exchange)
- **API URL** = K8s API server (for user info `/apis/user.openshift.io/v1/users/~`)
- Callback hits API on `:8000` directly (not proxied through Next.js)
- Cookie set with `domain=localhost` so it's sent to both `:8000` and `:3000`
- After login, API redirects to `APP_URL/dashboard`
- SSL verify disabled when `PINKY_DEBUG=true` (dev clusters with self-signed certs)

## Specs

All in `docs/superpowers/specs/`:
- `2026-05-01-pinky-prd.md` — Product requirements
- `2026-05-01-pinky-sds.md` — System design (DB schema, API contracts, SSE protocol, Temporal patterns)
- `2026-05-01-pinky-ui-design.md` — UI design (wireframes, interaction specs, state machine)
- `2026-05-01-pinky-architecture-decisions.md` — 25 ADRs
- Implementation plan: `docs/superpowers/plans/2026-05-01-pinky-platform.md`

## Hard Rules

### Backend
- Never `# type: ignore` — fix the actual type issue
- Never `except Exception: pass` — always `logger.exception("context")`
- Never store raw credentials in browser, logs, or LLM prompts
- Always use AAD when encrypting credentials (`encrypt(data, aad="table:id")`)
- Observer identity never used for writes or sensitive reads
- Policy engine is deterministic — no LLM calls
- Definitions are the extensibility mechanism — not hardcoded Python

### Frontend
- **All CSS in `@layer base`** — never write unlayered CSS, it overrides Tailwind utilities
- **Use `text-caption` (11px) and `text-body-sm` (13px)** — never `text-[11px]` or `text-[13px]`
- **Use `tabular-nums`** — never custom `tabular` utility
- **SSE subscriptions** — use `useEventBus(id, handler)` hook (singleton EventBusProvider), NOT per-view `useSSE`. Only use `useSSE` directly for execution-specific streams (`/streams/executions/{id}`).
- **Pagination** — use `usePaginatedData` hook for cursor-based page accumulation. Never hardcode limits without Load More.
- **Cluster names** — API returns `cluster_display_name`. Never build frontend cluster ID→name maps.
- **Co-located queries** — each page has `queries.ts` exporting `queryOptions` factories
- **Zero inline styles** — use Tailwind utility classes only, never `style={{}}` (exception: runtime-computed column resize widths with eslint-disable)
- **Zero CSS modules** — use Tailwind, not `.module.css` files
- **Use shadcn/ui components** — Button, Dialog, AlertDialog, Input, Select, Badge, Card, etc. Don't build custom primitives
- **Import types from `@pinky/contracts`** — never redeclare `interface WorkItem {}` locally
- **Use TanStack Query** for data fetching — never raw `useState` + `useEffect` + `fetch` patterns
- **Use react-hook-form + Zod** for forms — never manual `useState` per field
- **Use date-fns** for formatting — never raw `toLocaleString()`
