# Pinky

Task-first multi-cluster Kubernetes operations platform with an embedded SRE agent, **The Brain**.

Pinky observes clusters, correlates problems into actionable tasks, investigates root causes with LLM analysis, and orchestrates remediations through approval-gated Temporal workflows. Operators work from a prioritized task inbox — not a wall of alerts.

## Core Pipeline

```
Cluster Observers         Policy Engine            The Brain              Operator
(async, per-cluster)      (deterministic)          (LLM-powered)          (task inbox)
       │                        │                       │                      │
       ▼                        │                       │                      │
  ┌─────────┐                   │                       │                      │
  │ Scanner │──fingerprint──►┌──▼───────────┐           │                      │
  │ Plugins │                │ Observations │           │                      │
  └─────────┘                └──────┬───────┘           │                      │
                                    │                   │                      │
                             ┌──────▼───────┐           │                      │
                             │  Correlate   │           │                      │
                             │  & Dedup     │           │                      │
                             └──────┬───────┘           │                      │
                                    │                   │                      │
                             ┌──────▼───────┐           │                      │
                             │ Policy Gate  │           │                      │
                             │ (first-match │           │                      │
                             │  wins)       │           │                      │
                             └──┬───┬───┬───┘           │                      │
                                │   │   │               │                      │
                    ┌───────────┘   │   └────────┐      │                      │
                    ▼               ▼            ▼      │                      │
               Suppress         Observe    ┌─────▼────┐ │                      │
               (Watch)          (Watch)    │Investigate│ │                      │
                                           └─────┬────┘ │                      │
                                                 │      │                      │
                                           ┌─────▼────────────┐               │
                                           │ Gather Evidence   │               │
                                           │ Redact Secrets    │               │
                                           │ LLM Analysis      │               │
                                           │ Generate Plan     │               │
                                           └─────┬────────────┘               │
                                                 │                             │
                                           ┌─────▼──────┐              ┌──────▼──────┐
                                           │ Create Task │─────────────►│ Task Inbox  │
                                           │ with Plan   │              │ (ready)     │
                                           └─────────────┘              └──────┬──────┘
                                                                               │
                                                                        accept/start
                                                                               │
                                                                        ┌──────▼──────┐
                                                                        │ Remediation │
                                                                        │ Workflow    │
                                                                        └──────┬──────┘
                                                                               │
                                                                        ┌──────▼──────┐
                                                                        │  Approval   │
                                                                        │  (4hr TTL)  │
                                                                        └──────┬──────┘
                                                                               │
                                                                        ┌──────▼──────┐
                                                                        │  Execute    │
                                                                        │  (user creds)│
                                                                        └──────┬──────┘
                                                                               │
                                                                        ┌──────▼──────┐
                                                                        │  Verify     │
                                                                        └──────┬──────┘
                                                                               │
                                                                        ┌──────▼──────┐
                                                                        │  History    │
                                                                        └─────────────┘
```

**Key principle:** deterministic policy runs before any LLM call. Signals that don't pass the policy gate never hit the reasoning layer.

## System Architecture

```
                              ┌─────────────────────────────────────────┐
                              │           pinky.example.com             │
                              │         (same-origin ingress)           │
                              └─────┬──────────────┬────────────────────┘
                                    │              │
                              /     │     /api/v1/ │  /api/v1/streams/
                                    │              │  (no buffering)
                              ┌─────▼─────┐  ┌────▼──────┐
                              │  Next.js   │  │  FastAPI   │
                              │  Web UI    │  │  API       │
                              │  :3000     │  │  :8000     │
                              └────────────┘  └──┬──┬──┬──┘
                                                 │  │  │
                         ┌───────────────────────┘  │  └───────────────────┐
                         │                          │                      │
                   ┌─────▼──────┐            ┌──────▼──────┐        ┌─────▼──────┐
                   │ PostgreSQL │◄──NOTIFY───│   Redis     │        │  Temporal   │
                   │  16        │            │   7         │        │  Server     │
                   │            │            │  (sessions) │        │            │
                   │ 23 tables  │            └─────────────┘        └─────┬──────┘
                   │ partitioned│                                         │
                   └────────────┘                                   ┌────▼───────┐
                                                                    │  Worker    │
                                                                    │            │
                                                                    │ Observers  │
                                                                    │ Workflows  │
                                                                    │ Projectors │
                                                                    │ Webhooks   │
                                                                    └────┬───────┘
                                                                         │
                                                                    ┌────▼───────┐
                                                                    │ K8s Clusters│
                                                                    │ (observed)  │
                                                                    └─────────────┘
```

### Component Responsibilities

| Component | Role |
|-----------|------|
| **Web** | Task inbox, watch feed, history, alerts, settings, dashboard. Real-time via SSE. |
| **API** | REST endpoints, auth (OpenShift OAuth / OIDC), RBAC, session management, SSE fan-out via Postgres NOTIFY. |
| **Worker** | Cluster observers, issue correlator, 4 Temporal workflows (investigation, remediation, approval, verification), event projector, webhook delivery. |
| **PostgreSQL** | System of record. 23 tables including partitioned event tables (pg_partman). Authoritative for issues, tasks, history, projections. |
| **Redis** | Session store (ephemeral — loss = re-login). TTL-based expiry, atomic rotation/revocation. |
| **Temporal** | Durable workflow runtime. Authoritative for in-flight execution state. Single `pinky` namespace with per-type task queues. |

## Temporal Workflows

Four durable workflows with explicit timeout and retry policies:

```
InvestigationWorkflow                 ApprovalWorkflow
────────────────────                  ─────────────────
gather_evidence (30s)                 emit approval_required
  │                                     │
check_artifact_cache (5s)             wait for signal
  │                                   ┌──┴──┐
LLM investigation (120s,             approve reject  (or 4hr timeout)
  heartbeat 30s)                       │
  │                                    ▼
store_artifact (5s)                  return decision
  │
project_to_postgres

RemediationWorkflow                   VerificationWorkflow
────────────────────                  ────────────────────
validate_approval                     wait configurable delay (30s-5min)
  │                                     │
execute steps via                     re-scan target resources
  user binding (60s/step)               │
  │                                   compare against expected state
emit progress events                    │
  │                                   emit verified / failed
trigger VerificationWorkflow
  (child workflow)
```

**Workflow ID:** `investigation-{cluster_id}-{fingerprint_hash}` — prevents duplicate investigations of the same issue.

**Task queues:** `investigation`, `remediation`, `observation`, `projection` — independently scalable worker pools.

## Observation Pipeline

```
Per-Cluster Observer Loop (60s polling, max 50 concurrent)
  │
  ├─ Run scanner plugins (from definitions/scanners/*.md)
  │    └─ Each scanner declares resource_kinds + check conditions
  │
  ├─ Generate fingerprint: sha256(cluster:kind:ns:name:scanner:check_id)
  │
  ├─ Dedup rules:
  │    1. Same fingerprint + cluster + scanner → upsert observation
  │    2. Same correlation key as open issue → attach to existing
  │    3. Same correlation key as recently resolved (<1hr) → reopen
  │    4. Identical fingerprint within scan interval → collapse
  │
  ├─ Policy gate (priority-ordered, first-match-wins, no LLM):
  │    suppress | observe | investigate | auto-resolve | create-task
  │
  └─ Backpressure: skip cycle when queue depth >500/cluster
```

## Data Flow: Temporal to UI

```
Temporal Workflow Events
        │
        ▼
Projector Worker (2s poll)
        │
        ▼
Idempotent Upsert (INSERT ... ON CONFLICT DO NOTHING)
        │
        ▼
PostgreSQL (execution_events, work_items)
        │
        ▼
NOTIFY (pg channel)
        │
        ▼
API (in-memory SSE connection registry)
        │
        ▼
Browser (EventSource with Last-Event-ID)
```

**Target latency:** <10s from workflow event to UI update. Projector lag alert threshold: >10s.

## SSE Protocol

| Endpoint | Purpose |
|----------|---------|
| `/v1/streams/work-items` | Work item status changes |
| `/v1/streams/watch` | Watch/analysis activity |
| `/v1/streams/issues` | Issue lifecycle changes |
| `/v1/streams/executions/{id}` | Live execution progress |

- **Heartbeat:** every 15s. Client treats no event for 45s as dead.
- **Reconnect:** `Last-Event-ID` → replay from buffer (1000 events/stream, LRU). Outside buffer: `snapshot_required` with `fetch_url`.
- **Backoff:** 1s → 2s → 4s → 8s → 30s cap. Reset after 60s connected.
- **Auth expiry:** stream terminates with `auth-expired` sentinel event.
- **Binding expiry:** `binding-expired` event for affected cluster scope.

## Auth & Identity Model

```
                    ┌──────────────┐
                    │   Principal  │
                    │ (auto-linked │
                    │  by email)   │
                    └──┬───────┬───┘
                       │       │
              ┌────────▼──┐ ┌──▼────────────┐
              │  Product   │ │  Cluster       │
              │  Session   │ │  Identity      │
              │  (Redis)   │ │  Bindings      │
              │            │ │  (per-cluster)  │
              └────────────┘ └──┬─────────┬───┘
                                │         │
                         ┌──────▼──┐  ┌───▼───────┐
                         │Observer  │  │  User     │
                         │Identity  │  │  Identity │
                         │(SA, r/o) │  │  (writes, │
                         │          │  │   sensitive│
                         └──────────┘  │   reads)  │
                                       └───────────┘
```

**Three-layer authorization:** product authz → cluster authz → execution authz.

| Authz Class | Identity Used | Example |
|-------------|--------------|---------|
| Product-authenticated read | Session | List tasks, view history |
| Observer read | Observer SA | Background scanning, non-sensitive reads |
| User-sensitive read | User binding | Secrets, exec, private data |
| Cluster-user write | User binding | Scale, restart, patch, rollback |
| Admin control-plane | Session + admin role | Cluster registry, policy rules |

**Binding states:** `missing` → `valid` → `expiring` → `expired` → `revoked`. Binding loss auto-reassigns tasks to team queue.

**>5 clusters:** external OIDC required. Per-cluster OAuth only for <=5.

## Security

- **Sessions:** HTTP-only, Secure, SameSite=Strict cookies. Redis-backed with idle/absolute timeout. CSRF via double-submit cookie (`X-CSRF-Token`).
- **Encryption:** AES-256-GCM envelope encryption with key version prefix + AAD binding. HMAC-SHA256 for token hashing. 90-day key rotation.
- **CSP:** Strict — no `unsafe-inline`, no `unsafe-eval`. CSP reporting enabled.
- **Headers:** HSTS, X-Content-Type-Options, Referrer-Policy, Permissions-Policy, X-Frame-Options.
- **Containers:** Non-root (UID 1001), read-only rootfs.
- **LLM safety:** Evidence redacted before prompts (bearer tokens, connection strings, env vars). Redaction failures fail closed.
- **Network:** Hub-spoke model — outbound-only from control plane to managed clusters. Kubernetes NetworkPolicy for pod isolation.

## Extensibility: Markdown Definitions

Same pattern as Claude Code skills. Frontmatter carries config, body carries LLM-readable instructions.

```
definitions/
  scanners/        What to observe (resource types, check conditions)
  tools/           What The Brain can use (kubectl, helm, prometheus-query)
  skills/          How The Brain approaches problems (investigation strategy)
  pipelines/       How signals flow (triage steps, gating logic)
  policies/        Declarative triage rules (suppress, observe, investigate)
  redaction-rules/ Patterns to strip before LLM prompts
  approval-policies/ Per-cluster/namespace/risk approval chains
```

**Loading:** filesystem defaults → DB overrides via API → 30s cache TTL. Operators extend without writing Python.

**Tool credential resolution:** tools declare `authz_class` or `service` in frontmatter. Runtime resolves credentials at execution time — tools never see raw credentials.

## Task Lifecycle

```
ready ──Accept──► accepted ──Start──► in_progress ──Complete──► done ──► History
                                         │    │
                                         │    └──Request Approval──► waiting_for_approval
                                         │                              │
                                         └──Mark Blocked──► blocked     │
                                                                        │
                                         ◄──approve─────────────────────┘
                                         ◄──reject (revision needed)────┘

Binding loss ──► auto-reassign to team queue
```

Tasks exist only after The Brain can attach a coherent plan. Raw signals stay in Watch.

## Product Surfaces

| Surface | Purpose |
|---------|---------|
| **Tasks** | Prioritized work inbox. Only human-actionable items with plans. |
| **Watch** | What The Brain is doing now: analyzing, suppressing, auto-remediating, correlating. |
| **History** | Completed work, suppressions, approvals, rollbacks. Canonical done surface. 90-day retention. |
| **Alerts** | Raw signals and observability context, separate from work queue. |
| **Settings** | Cluster registry, bindings, definitions, policies, webhooks, analytics, API tokens. |
| **Dashboard** | Metrics and operational overview. |

## Repo Layout

```
apps/web/           Next.js 15 + React 19 + TypeScript + Tailwind + shadcn/ui
apps/api/           FastAPI + SQLAlchemy 2 async + asyncpg + Pydantic v2
apps/worker/        Temporal workflows + cluster observer + LLM integration
apps/cli/           CLI wrapping REST API (typer + httpx)
packages/contracts/ Shared TypeScript types
packages/design-system/ React component library
definitions/        Markdown-driven extensibility (scanners, skills, policies, tools)
infra/docker/       docker-compose for local dev (Postgres, Redis, Temporal)
infra/helm/         Helm chart for OpenShift / Kubernetes deployment
```

## Quick Start

```bash
# Prerequisites: Python 3.12+, Node 20+, pnpm, Podman/Docker

# 1. Start infrastructure
make dev-infra          # Postgres, Redis, Temporal via podman compose

# 2. Start services (each in a separate terminal, or use `make dev`)
make dev-api            # FastAPI on :8000
make dev-worker         # Temporal worker + cluster observer
make dev-web            # Next.js on :3000

# Or all at once:
make dev
```

## Database

23 tables across 5 bounded contexts:

| Context | Tables |
|---------|--------|
| **Identity** | `principals`, `sessions`, `session_audit_log`, `api_tokens` |
| **Fleet** | `cluster_registry`, `cluster_observer_bindings`, `cluster_identity_bindings`, `service_bindings` |
| **Operations** | `observations`, `issues`, `work_items`, `executions`, `execution_events`, `approvals` |
| **History & Events** | `history_events`, `domain_events`, `analytics_events`, `projection_cursors` |
| **Extensibility** | `definitions`, `policy_rules`, `webhook_subscriptions`, `webhook_deliveries`, `eval_runs` |

`execution_events`, `history_events`, and `analytics_events` are partitioned by month (pg_partman). Work items and issues support labels (JSONB with GIN indexes) for filtering.

## API

38 endpoints across auth, fleet, operations, extensibility, and analytics. Cursor-based pagination (default 50, max 200).

```
Auth:        /v1/auth/{login,callback,logout,session}
Fleet:       /v1/clusters, /v1/cluster-bindings, /v1/service-bindings
Operations:  /v1/work-items, /v1/issues, /v1/executions, /v1/history, /v1/alerts
Streams:     /v1/streams/{work-items,watch,issues,executions/{id}}
Extensibility: /v1/definitions, /v1/policy-rules, /v1/webhook-subscriptions
Analytics:   /v1/analytics/{roi,scanners,export}
```

## CLI

```bash
pinky login [--token <api-token>]
pinky tasks list [--status ready,accepted] [--cluster <id>]
pinky tasks accept <id>
pinky watch
pinky definitions list --kind scanner
pinky definitions create -f scanner.md
pinky analytics roi [--since 30d] [--format json]
```

## Testing

~370 tests across 6 packages:

```bash
make verify             # lint + typecheck + test (all packages)
```

| Layer | Tests | Command |
|-------|------:|---------|
| API | 99 | `cd apps/api && pytest tests/ --ignore=tests/benchmark -v` |
| Worker unit | 72 | `cd apps/worker && pytest tests/ --ignore=tests/integration -v` |
| Worker integration | 26 | `cd apps/worker && pytest tests/integration/ -v` |
| CLI | 18 | `cd apps/cli && pytest tests/ -v` |
| Contracts | 11 | `pnpm --filter @pinky/contracts test` |
| Web E2E | 104 | `cd apps/web && npx playwright test` |
| **Total** | **330** | |

**Additional (weekly CI):**
- LLM eval: 36 deterministic graders (`cd apps/worker && pytest evals/ -v`)
- Performance: 10 API latency benchmarks (`cd apps/api && pytest tests/benchmark/ -v`)

### LLM Evaluation

Deterministic graders test investigation output quality without LLM calls:
- **Structure**: output has summary, root cause, recommendation sections
- **Safety**: no dangerous actions (namespace deletion, RBAC disabling)
- **Relevance**: output mentions expected keywords from evidence
- **Redaction**: no secrets survive in LLM prompts

## Deploying

```bash
# Preflight check (cluster connectivity, secrets, images)
./scripts/preflight.sh infra/helm/values-dev.yaml

# Deploy (creates K8s secrets from secrets/ dir, runs helm upgrade)
./scripts/deploy.sh infra/helm/values-dev.yaml
```

### Deployment Topology

| Component | Type | Replicas | Notes |
|-----------|------|----------|-------|
| `web` | Stateless | 2+ | Next.js, behind ingress |
| `api` | Stateless | 2+ | FastAPI, behind ingress |
| `worker` | Stateless | 2+ | Temporal workers, observers, projectors |
| `postgres` | Stateful | 1 primary + 1 replica | PVC-backed, operator-managed |
| `redis` | Stateful | 1 primary + 1 replica | Session cache |
| `temporal` | Stateful | 1 (dev) / 3 (prod) | Own Postgres backend |

### Secrets

Secrets live in `secrets/` (gitignored). The deploy script creates K8s secrets from these files:
- `secrets/oauth-client-secret` — OpenShift OAuth client secret
- `secrets/vertex-credentials.json` — Google Vertex AI service account key

Pre-commit and pre-push hooks block accidental secret commits.

## CI

**Every PR** (`.github/workflows/ci.yml`):
- `api-tests` — lint + 99 tests against Postgres
- `worker-tests` — lint + 72 unit tests
- `worker-integration` — 26 tests against Postgres + Temporal
- `web-checks` — typecheck + build

**Weekly**:
- `eval.yml` — LLM evaluation graders (36 tests)
- `perf.yml` — API latency benchmarks (10 endpoints)

## Failure Modes

| Failure | Degradation |
|---------|-------------|
| Redis unavailable | Fall back to Postgres session lookup. New sessions blocked. |
| Postgres unavailable | API returns 503. SSE sends error event. Workflows pause. |
| Temporal unavailable | New submissions queued in-memory (bounded 100). API returns 503 for execution-start. |
| LLM provider timeout | Return cached investigation if <1h old. Otherwise mark work item `blocked`. |
| Cluster unreachable | Observer marks `degraded`. After 3 consecutive failures: `unhealthy`. |
| SSE connection drop | Client reconnects with backoff. Server replays from buffer. Outside buffer: `snapshot_required`. |

## Scale Targets

- 10-100 clusters
- Dozens to low hundreds of users
- Task freshness: <10s
- Watch/execution update latency: <10s

## Key Concepts

**Tasks** -- Prioritized work items generated from cluster observations. A task exists only after The Brain can attach a coherent plan. Status: `ready` -> `accepted` -> `in_progress` -> `done` (or `blocked`, `waiting_for_approval`).

**Issues** -- Correlated operational problems. Multiple observations from the same source deduplicate into one issue via stable fingerprinting. Issues reopen if re-detected within 1hr of resolution.

**Investigations** -- LLM-powered analysis. The Brain gathers evidence (pods, events), redacts secrets, and produces structured findings (summary, root cause, recommendation, confidence score).

**Executions** -- Temporal workflows for remediation. Require human approval with immutable change-set digest, execute K8s changes using the operator's own cluster credentials, and verify results automatically.

**Definitions** -- Markdown files with YAML frontmatter that define scanners, skills, policies, tools, and pipelines. The extensibility mechanism — operators extend without writing code.

**Policy Engine** -- Deterministic, priority-ordered rules. First match wins. No LLM in the policy pipeline. Every decision logged to analytics.

**Domain Events** -- Every significant state transition emits a domain event. External systems subscribe via webhooks with event pattern filtering and built-in formatters (Slack, Teams, generic JSON).
