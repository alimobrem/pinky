# CLAUDE.md

## Project

Pinky — greenfield multi-cluster Kubernetes operations platform with embedded SRE agent "The Brain". Task-first (not alert-first), async-first, workflow-driven. Markdown-driven extensibility for scanners, tools, skills, pipelines, and policies.

## Stack

- **Web:** Next.js 15 + React 19 + TypeScript (apps/web)
  - **Styling:** Tailwind CSS v4 + shadcn/ui — no inline styles, no CSS modules
  - **Data fetching:** TanStack Query (React Query) — no raw fetch/useState boilerplate
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
apps/web/          → Next.js UI (Tasks, Watch, History, Alerts, Settings, Login)
apps/api/          → FastAPI API server (all /api/v1/* routes)
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
- **Definitions:** Markdown files with YAML frontmatter. Loaded from `definitions/` directory. DB overrides via API. Worker loads via `DefinitionRegistry`.
- **Policy:** Declarative rules in `policy/engine.py`. Priority-ordered, first-match-wins. No LLM in the policy pipeline.
- **Workflows:** 4 Temporal workflows (Investigation, Remediation, Approval, Verification). Activities in `execution/activities.py`. Workflow ID derived from issue fingerprint to prevent duplicates.
- **SSE:** Heartbeat every 15s. Reconnect with `Last-Event-ID`. Auth-expired/binding-expired sentinel events.
- **Models:** SQLAlchemy 2 declarative in `models/`. Alembic for migrations. 23 tables including extensibility (definitions, service_bindings, domain_events, webhooks, policy_rules, api_tokens).

### Security
- Strict CSP (no unsafe-inline, no unsafe-eval)
- CSRF via double-submit cookie (`X-CSRF-Token` header)
- All containers non-root (UID 1001), read-only rootfs
- Cluster credentials encrypted at rest (AES-256-GCM with AAD)
- Evidence redacted before LLM prompts (bearer tokens, connection strings, sensitive env vars)
- Observer identity isolated from user execution identity
- >5 clusters requires external OIDC (per-cluster OAuth doesn't scale)

## Testing

```bash
# API tests (68 tests)
cd apps/api && .venv/bin/pytest tests/ -v

# Worker tests (56 tests)
cd apps/worker && .venv/bin/pytest tests/ -v

# Web typecheck
pnpm --filter @pinky/web typecheck
```

Tests use `conftest.py` fixtures: `authed_client` (auth bypassed with test principal), `unauthed_client` (no auth), `non_admin_client`. Encryption key set via `monkeypatch`. Tests run against real Postgres and Redis.

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
- After login, API redirects to `APP_URL/tasks`
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
- **Zero inline styles** — use Tailwind utility classes only, never `style={{}}`
- **Zero CSS modules** — use Tailwind, not `.module.css` files
- **Use shadcn/ui components** — Button, Dialog, AlertDialog, Input, Select, Badge, Card, etc. Don't build custom primitives
- **Import types from `@pinky/contracts`** — never redeclare `interface WorkItem {}` locally
- **Use TanStack Query** for data fetching — never raw `useState` + `useEffect` + `fetch` patterns
- **Use react-hook-form + Zod** for forms — never manual `useState` per field
- **Use date-fns** for formatting — never raw `toLocaleString()`
