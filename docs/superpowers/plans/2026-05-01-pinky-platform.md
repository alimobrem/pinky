# Pinky Platform Implementation Plan

**Goal:** Build `Pinky`, a greenfield multi-cluster operations product with a bundled UI and a first-class SRE agent named `The Brain`, centered on task-first operations, strong security, efficient LLM usage, and measurable ROI.

**Architecture:** Monorepo product bundling web UI, API, worker runtime, shared contracts, and design system. Core model: `Principal -> ClusterIdentityBinding -> Observation -> Issue -> WorkItem -> Execution -> HistoryEvent`. Auth supports OpenShift OAuth and external OIDC (required for >5 clusters). Runtime is async-first with Temporal for durable workflows. Deterministic policy before LLM. Strict security/session/CSP/timeout baselines from day one. Every operation is instrumented for analytics, outcome tracking, and ROI measurement.

**Tech Stack:** Next.js + React + TypeScript (UI), Python + FastAPI (API), Temporal (workflow runtime), PostgreSQL (system of record), Redis (sessions), SSE (real-time), Pydantic v2, SQLAlchemy 2 async, Alembic (migrations), pytest, Playwright.

**Key docs:**
- PRD: `../specs/2026-05-01-pinky-prd.md`
- SDS: `../specs/2026-05-01-pinky-sds.md`
- UI design: `../specs/2026-05-01-pinky-ui-design.md`
- Architecture decisions: `../specs/2026-05-01-pinky-architecture-decisions.md`

---

## Repo Shape

```text
/Users/amobrem/ali/pinky/
  apps/
    web/          # Next.js + React + TypeScript
    api/          # FastAPI + SQLAlchemy + Pydantic
    worker/       # Temporal workers + observer loops + projectors
    cli/          # Python CLI wrapping REST API (typer)
  packages/
    contracts/    # Shared TypeScript types
    design-system/ # React component library
  definitions/    # Markdown-driven extensibility (scanners, tools, skills, pipelines, policies, redaction-rules, approval-policies)
  infra/
    docker/       # Dockerfiles + docker-compose.yml
    helm/         # Helm chart
  docs/
```

---

## Dependency Graph

```
Task 2 (bootstrap) ─┬─► Task 2.5 (dev env) ─► Task 2.7 (database) ─► Task 2.8 (temporal)
                     │
                     ├─► Task 3a (auth/sessions) ─► Task 3b (cluster/bindings/authz)
                     │
                     └─► Task 4 (design system + UI shell)
                              │
Task 5 (observation pipeline) ◄── depends on Task 2.7
                              │
Task 6 (end-to-end surfaces) ◄── depends on Tasks 3a, 3b, 4, 5
                              │
Task 7 (Brain execution) ◄── depends on Tasks 2.8, 6
                              │
Task 8 (LLM efficiency) ◄── depends on Task 7
                              │
Task 8.5 (analytics + ROI) ◄── depends on Tasks 6, 7, 8
                              │
Task 9 (deployment) ◄── depends on Task 8.5
                              │
Task 10 (migration) ◄── depends on Task 9
```

**Parallelizable:** Tasks 3a, 4, and 5 can run in parallel after Task 2 completes.

---

## Task 1: Lock product definition docs

**Status:** Done.

---

## Task 2: Bootstrap monorepo and shared contracts

**Depends on:** nothing

- [ ] Create monorepo root with pnpm workspace config, shared tsconfig, .gitignore, .editorconfig
- [ ] Create `apps/web/` with Next.js + TypeScript
- [ ] Create `apps/api/` with FastAPI, pyproject.toml (src layout), Pydantic v2, SQLAlchemy 2 async
- [ ] Create `apps/worker/` with pyproject.toml (src layout), Temporal SDK
- [ ] Create `packages/contracts/` with initial domain types: Principal, ClusterRegistryEntry, ClusterIdentityBinding, WorkItem, Observation, Issue, Execution, ExecutionEvent, HistoryEvent, Approval
- [ ] Create `packages/design-system/` with package.json
- [ ] Create `apps/cli/` with pyproject.toml, typer dependency, basic command structure
- [ ] Create `definitions/` directory with subdirs: scanners/, tools/, skills/, pipelines/, policies/, redaction-rules/, approval-policies/
- [ ] Add CI wiring: lint (eslint + ruff), typecheck (tsc + pyright), test (pytest + vitest)
- [ ] Add Makefile with dev commands: `make dev`, `make lint`, `make test`, `make typecheck`

**Done criteria:** `make lint` and `make typecheck` pass, packages install, contracts importable from web app.

---

## Task 2.5: Set up dev environment

**Depends on:** Task 2

- [ ] Create docker-compose.yml: PostgreSQL 16, Redis 7, Temporal server + UI, all with health checks
- [ ] Add `make dev-infra` to start services, `make dev-api`, `make dev-worker`, `make dev-web`, `make dev` for all
- [ ] Add `.env.example` with all required environment variables

**Done criteria:** `make dev-infra` starts all services with health checks passing; API/worker/web connect successfully.

---

## Task 2.7: Set up database and migrations

**Depends on:** Task 2.5

- [ ] Set up Alembic with async SQLAlchemy engine
- [ ] Create initial migration with all core tables:
  - `principals`, `sessions`, `session_audit_log`
  - `cluster_registry`, `cluster_observer_bindings`, `cluster_identity_bindings`
  - `observations`, `issues`, `work_items`
  - `executions`, `execution_events` (partitioned by month), `history_events` (partitioned by month)
  - `approvals`, `projection_cursors`, `feature_flags`
  - `analytics_events` — append-only table for product analytics (user actions, Brain actions, outcomes)
  - `eval_runs` — stores evaluation/replay fixture runs with baseline comparison results
  - `definitions` — markdown definition storage for runtime additions (scanner, tool, skill, pipeline, policy, redaction-rule, approval-policy)
  - `service_bindings` — external service connections (Prometheus, Datadog, etc.) with encrypted credentials
  - `domain_events` — append-only domain event bus
  - `webhook_subscriptions` — outbound webhook registration with event pattern filtering
  - `webhook_deliveries` — webhook delivery tracking with retry
  - `policy_rules` — declarative policy rules with priority ordering
  - `api_tokens` — long-lived API tokens for CLI/CI automation
- [ ] Add `labels JSONB`, `annotations JSONB`, `runbook_url TEXT` columns to `work_items` and `issues` tables with GIN indexes on labels
- [ ] Set up pg_partman for time-partitioned tables
- [ ] Add indexes: cluster_id prefix on cluster-scoped tables, correlation_key on issues, fingerprint on observations
- [ ] Add `make db-migrate` and `make db-upgrade` commands

**Done criteria:** Migration runs against real Postgres, all tables exist, downgrade works.

---

## Task 2.8: Set up Temporal infrastructure

**Depends on:** Task 2.5

- [ ] Create Temporal namespace `pinky`
- [ ] Define task queue constants: `investigation`, `remediation`, `observation`, `projection`
- [ ] Create worker registration config
- [ ] Add `make temporal-init` command

**Done criteria:** Namespace created, worker connects, trivial test workflow executes.

---

## Task 3a: Implement product auth and sessions

**Depends on:** Task 2, Task 2.7

- [ ] OpenShift OAuth provider: redirect, callback, token handling
- [ ] Optional external OIDC provider: discovery, redirect, callback
- [ ] Principal resolution: find-or-create, auto-link on verified email match
- [ ] Server-side session store (Redis) with Postgres audit log
- [ ] Session policy: idle timeout, absolute timeout, rotation, CSRF (double-submit cookie)
- [ ] Secure HTTP-only cookie issuance with `SameSite=Strict`
- [ ] Session validation middleware (401 on expired)
- [ ] Security headers: strict CSP, HSTS, X-Content-Type-Options
- [ ] AES-256-GCM envelope encryption module
- [ ] Web login page with provider choice
- [ ] **Analytics instrumentation:** log every auth event (login, logout, rotation, failure, provider) to `analytics_events`

**Done criteria:** Login flow works end-to-end, session rotation/expiry/CSRF verified by tests, security headers present, auth events logged.

---

## Task 3b: Implement cluster registry, bindings, and authorization

**Depends on:** Task 3a

- [ ] Shared cluster registry: admin-only CRUD, ACM/OCM registration
- [ ] Observer bindings: per-cluster SA, health tracking
- [ ] User cluster bindings: create/refresh/revoke, states (missing/valid/expiring/expired/revoked)
- [ ] External OIDC enforcement when >5 clusters registered
- [ ] Encrypted token storage
- [ ] Authorization matrix: observer_read, user_sensitive_read, user_write, admin_control_plane
- [ ] 401 vs 403 distinction
- [ ] Cluster removal cascade (archive tasks, preserve history)
- [ ] Binding expiry cascade (tasks return to team queue)
- [ ] Settings > Clusters UI
- [ ] **Analytics instrumentation:** log binding lifecycle events, cluster onboarding/offboarding, authz decisions

**Done criteria:** Admin CRUD works, binding lifecycle verified, authz matrix enforced, OIDC enforced at >5 clusters, analytics events logged.

---

## Task 4: Build design system and task-first UI shell

**Depends on:** Task 2

### 4.1 Design system primitives (build FIRST)
- [ ] Design tokens: colors, spacing, typography, component vocabulary
- [ ] Core primitives: Button, Badge, Chip, Card, Skeleton, Dialog, Toast
- [ ] Layout primitives: Stack, Grid, PageShell, NavRail, TopBar, ContextPanel
- [ ] Data primitives: DataTable, FilterBar, EmptyState, ErrorState

### 4.2 Page shells
- [ ] Branded shell with cluster selector, session status, NavRail
- [ ] Auth gate, hybrid cluster selector
- [ ] All 5 route shells with loading/empty/error states
- [ ] Responsive layout (Desktop ≥1280px, Tablet 768-1279px, Mobile <768px)
- [ ] Keyboard navigation (j/k, Cmd+K, Tab)

**Done criteria:** Auth gate works, all routes render, cluster selector switches context, responsive collapse works.

---

## Task 5: Build deterministic observation, issue correlation, and policy

**Depends on:** Task 2.7

- [ ] Implement markdown definition loader: parse frontmatter + body from `definitions/` directory, register in-memory, load DB overrides, cache with 30s TTL
- [ ] Implement scanner definition loading from `definitions/scanners/*.md`
- [ ] Implement tool definition loading from `definitions/tools/*.md` with credential resolution chain (authz_class → cluster binding, service → service binding)
- [ ] Implement skill definition loading from `definitions/skills/*.md` with scope-based override resolution
- [ ] Implement pipeline definition loading from `definitions/pipelines/*.md`
- [ ] Implement redaction rule loading from `definitions/redaction-rules/*.md` — apply patterns before any LLM prompt assembly
- [ ] Scanner plugin registry using loaded scanner definitions
- [ ] Observation normalization with stable fingerprints
- [ ] Issue correlation: group by fingerprint, merge duplicates, reopen/close
- [ ] Policy rule engine: load from `definitions/policies/*.md` + `policy_rules` DB table, priority-ordered, first-match-wins, deterministic
- [ ] Policy-first triage: suppress -> observe -> investigate -> auto-resolve -> create work item
- [ ] Scanner quality/noise controls
- [ ] False-positive feedback loop
- [ ] RBAC validation: validate observer binding has sufficient RBAC for each enabled scanner's declared resource_kinds/api_groups
- [ ] Write initial built-in definitions: `definitions/scanners/pod-health.md`, `definitions/tools/kubectl-get.md`, `definitions/skills/investigate-oom.md`, `definitions/pipelines/default-triage.md`, `definitions/policies/default-observe.md`, `definitions/redaction-rules/builtin-secrets.md`
- [ ] **Analytics instrumentation:** log every policy decision to `analytics_events` + emit domain event for webhook delivery

**Done criteria:** Definition loader loads MD files + DB overrides, scanner RBAC validation works, policy engine applies declarative rules, redaction strips sensitive patterns, tool credential resolution injects correct identity, no LLM calls in pipeline, analytics events logged.

---

## Task 6: Build Tasks, Watch, History, and Alerts end to end

**Depends on:** Tasks 3a, 3b, 4, 5

### 6.1 Schema-first API contracts (BEFORE routes)
- [ ] OpenAPI schemas for all resources
- [ ] Shared envelopes: paginated response, error response, SSE event envelope
- [ ] Filter/query schemas, SSE stream contracts

### 6.2 API routes
- [ ] Issues, work items (with lifecycle transitions), history, alerts, SSE streams
- [ ] Definition CRUD endpoints: list, get, create/update, delete (admin)
- [ ] Webhook subscription CRUD + delivery listing endpoints (admin)
- [ ] Policy rule CRUD + dry-run evaluation endpoint (admin)
- [ ] Service binding CRUD endpoints (admin)
- [ ] API token create/revoke/list endpoints
- [ ] Label-based filtering on work items and issues (`?label.key=value`)
- [ ] Domain event emission on every significant state transition
- [ ] Webhook delivery worker: poll `webhook_deliveries`, POST to subscribers, retry with backoff

### 6.4 Build CLI
- [ ] `apps/cli/` with `pinky` command wrapping REST API via `typer`
- [ ] Auth: browser-based OAuth flow + API token mode (`--token`)
- [ ] Commands: tasks, issues, executions, watch, history, alerts, definitions, webhooks, policy-rules, analytics
- [ ] `pinky definitions create -f scanner.md` to upload MD definitions via API
- [ ] CLI validates API contract completeness — every operator workflow must work via CLI

### 6.3 Wire UI to real data
- [ ] All 4 surfaces wired to APIs and SSE
- [ ] Real-time updates, optimistic UI
- [ ] **Analytics instrumentation:** log every user action (task accept/start/complete/reassign, approval, filter change, page view) to `analytics_events` with principal_id, cluster_id, work_item_id, timestamp

**Done criteria:** Contract tests pass, SSE delivers <10s, E2E login->task->accept->history works, all user actions logged.

---

## Task 7: Build The Brain execution layer with durable workflows

**Depends on:** Tasks 2.8, 6

### 7.1 Define workflow signatures
- [ ] InvestigationWorkflow, RemediationWorkflow, ApprovalWorkflow, VerificationWorkflow
- [ ] Shared activities: gather_evidence, run_llm_reasoning, apply_change, verify_state, project_to_postgres, emit_execution_event

### 7.2 Implement workflows
- [ ] Investigation: gather evidence -> check cache -> LLM -> store artifact -> project
- [ ] Remediation: validate approval -> apply via user binding -> emit progress -> verify
- [ ] Approval: emit approval_required -> wait for signal/timeout -> return
- [ ] Verification: wait delay -> re-scan -> compare -> record outcome
- [ ] Temporal -> Postgres projection: idempotent upserts, lag metrics
- [ ] Approval invalidation on drift, duplicate prevention via fingerprint-based workflow IDs

### 7.3 Execution API
- [ ] GET/POST executions, approve/reject, SSE stream
- [ ] **Analytics instrumentation:** log every execution event to `analytics_events`: investigation_started, investigation_completed, plan_generated, approval_requested, approval_granted/rejected/expired, remediation_started/completed/failed, verification_passed/failed, rollback_triggered. Include: execution_id, issue_id, cluster_id, duration_ms, token_count, model_tier, cache_hit, confidence_score, outcome.

**Done criteria:** Workflows execute, approval pause/resume/timeout works, projections are idempotent, all execution events logged with full telemetry.

---

## Task 8: Build LLM efficiency and performance controls

**Depends on:** Task 7

- [ ] Model tiering: utility (15s), interactive (30s), reasoning (120s), synthesis (60s)
- [ ] Investigation artifact caching (fingerprint + evidence_hash key)
- [ ] Evidence bundle construction: limits, truncation, redaction
- [ ] Token/call budgets per execution, concurrency limits
- [ ] Duplicate work avoidance: fingerprint + evidence hash check
- [ ] Per-execution telemetry: tokens, model tier, cache hit/miss, wall-clock duration
- [ ] Brain usage UI: token spend, cache hit rate, cost by issue category
- [ ] **Analytics instrumentation:** every LLM call logged to `analytics_events`: model, tier, input_tokens, output_tokens, cache_hit, latency_ms, execution_id, issue_fingerprint. Enables cost-per-issue, cost-per-cluster, cost-per-scanner breakdowns.

**Done criteria:** Cache hits avoid LLM calls, evidence redaction works, budgets enforced, telemetry records written, Brain usage UI shows real data.

---

## Task 8.5: Build analytics, eval system, and ROI measurement

**Depends on:** Tasks 6, 7, 8

This is the system that proves Pinky and The Brain are worth it. Every claim about value must be backed by data.

### 8.5.1 Analytics pipeline and dashboards
- [ ] Implement analytics query layer over `analytics_events` table: time-series aggregation, filtering by cluster/scanner/principal/execution_type
- [ ] Build ROI dashboard in web app (Settings > Analytics or top-level Analytics surface) showing:
  - **Time saved:** mean time from signal to task creation vs. manual triage baseline
  - **Issues resolved:** total issues resolved by The Brain (auto + assisted), with/without human intervention
  - **MTTR reduction:** mean time to remediation with Pinky vs. without (requires baseline)
  - **False positive rate:** % of created tasks that operators dismiss/reject/override
  - **Automation success rate:** % of auto-remediations that pass verification
  - **Cost per resolution:** LLM token cost per resolved issue (total cost / resolved issues)
  - **Operator override rate:** % of Brain recommendations that operators modify or reject
  - **Approval turnaround:** median time from approval request to decision
  - **Recurrence rate:** % of issues that reopen within 7 days of resolution
  - **Confidence calibration:** predicted confidence vs. actual outcome correctness (calibration curve)
- [ ] Build scanner quality dashboard:
  - Signal volume per scanner (total, suppressed, escalated, tasked)
  - False positive rate per scanner
  - Noise ratio: suppressed / total per scanner
  - Scanner ROI: issues-resolved-per-cost by scanner source
- [ ] Build cluster health dashboard:
  - Issues per cluster over time
  - Resolution rate per cluster
  - Binding health and observation currency per cluster
- [ ] Implement exportable analytics reports (CSV/JSON) for stakeholder ROI presentations

### 8.5.2 Eval and regression system
- [ ] Implement replay fixture system: record real investigation/plan/remediation workflows as fixtures, replay them against code changes to detect regressions
- [ ] Implement baseline comparison: store expected outputs per fixture, fail CI if output quality degrades (using deterministic quality metrics, not subjective)
- [ ] Implement eval scoring framework:
  - **Investigation quality:** does the investigation artifact correctly identify the root cause? (scored against labeled fixtures)
  - **Plan quality:** is the generated plan safe and correct? (scored against labeled fixtures)
  - **Confidence calibration:** are confidence scores accurate predictors of outcome?
  - **Tool selection:** does The Brain use the right tools for the job? (tool usage telemetry vs. expected tools per fixture)
  - **Cost efficiency:** does the same quality require fewer tokens over time?
- [ ] Implement eval run tracking: store eval results in `eval_runs` table with run_id, fixture_id, scores, token_usage, model_version, timestamp
- [ ] Add eval dashboard in web app: eval scores over time, regression alerts, cost efficiency trends
- [ ] Add CI gate: eval scores must not regress below baseline thresholds

### 8.5.3 Outcome tracking and feedback loops
- [ ] Track every resolution outcome explicitly: verified_fixed, recurred, operator_overridden, rolled_back, dismissed
- [ ] Feed outcomes back into policy: auto-resolve confidence thresholds adjust based on verified outcomes over time
- [ ] Feed outcomes back into scanner quality: scanners with high false-positive rates get demoted in policy triage
- [ ] Feed outcomes back into Brain tuning: investigation/plan quality scores feed into prompt iteration and model selection
- [ ] Implement weekly/monthly analytics digest: automated summary of key metrics, trends, and anomalies emailed to stakeholders or posted to Slack

**Done criteria:**
- ROI dashboard shows all key metrics with real data
- Scanner quality dashboard identifies best/worst scanners by ROI
- Eval system replays fixtures and detects regressions
- CI blocks on eval regression
- Outcome tracking records every resolution result
- Feedback loops adjust policy thresholds based on outcomes
- Analytics exportable for stakeholder presentations

---

## Task 9: Operational hardening and deployment

**Depends on:** Task 8.5

- [ ] Production Dockerfiles: multi-stage, non-root, read-only rootfs
- [ ] Helm chart: all components, ingress, network policies
- [ ] CI pipeline: lint, typecheck, test, build, SAST, dependency scan, secret scan, **eval regression gate**
- [ ] Release pipeline: container build, SBOM, cosign
- [ ] Observability: structured logging, audit events, OpenTelemetry, workflow metrics, LLM cost counters, CSP reporting
- [ ] Analytics data retention: 90-day online for `analytics_events`, archive older to object storage
- [ ] Chaos testing suite (`make chaos-test`):
  - Session expiry under load (expire sessions mid-request, verify 401 + reauth prompt)
  - Cluster binding revocation during active execution (verify graceful drain)
  - Temporal worker crash mid-investigation (verify workflow resumes on restart)
  - PostgreSQL failover (verify streaming replication promotes, projector recovers)
  - Redis eviction storm (verify session loss = re-login, no data corruption)
  - LLM provider outage (verify circuit breaker trips, cached artifacts served)
  - Cluster network partition (verify observer marks degraded, tasks show degraded indicator)
  - Webhook delivery failure cascade (verify retry backoff, DLQ after exhaustion)
  - SSE reconnection storm (100 clients reconnect simultaneously, verify buffer replay)
  - Approval timeout race (approve at exact expiry boundary, verify deterministic outcome)

**Done criteria:** All containers non-root, Helm deploys, CI blocks on failure + eval regression, audit log comprehensive, chaos tests pass.

---

## Task 10: Cutover and migration strategy

**Depends on:** Task 9

- [ ] Define coexistence with legacy Pulse
- [ ] Decide which historical objects to import
- [ ] Define rollback plan
- [ ] Only add legacy adapters with concrete user story
- [ ] **Define ROI comparison methodology:** how to measure Pinky vs. legacy Pulse on the same cluster fleet (A/B or before/after)

**Done criteria:** Migration doc covers coexistence, data import, rollback, ROI comparison methodology.

---

## Self-Review

### Scope coverage

This plan covers:
- greenfield bundled UI + backend + worker runtime
- branding (`Pinky` + `The Brain`)
- dev environment with docker-compose
- database schema and migrations with Alembic + pg_partman
- Temporal infrastructure
- auth + session management + security baseline (split: product auth vs cluster/authz)
- design system before page shells
- task-first product structure with four surfaces
- deterministic issue pipeline
- schema-first API contracts
- durable execution with Temporal
- LLM efficiency and performance
- **comprehensive analytics, eval system, and ROI measurement (Task 8.5)**
- **outcome tracking and feedback loops**
- **eval regression gates in CI**
- operational hardening and deployment
- explicit dependency graph and parallelism
- explicit done criteria for every task

### Non-goals

This plan intentionally does not preserve legacy `pulse-agent` contracts by default.
