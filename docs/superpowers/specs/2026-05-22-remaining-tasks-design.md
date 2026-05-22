# Pinky Platform — Remaining Tasks Design

**Date:** 2026-05-22
**Scope:** Tasks 8 (remainder), 8.5, 9, 10
**Phases:** 5, ordered by dependency graph

---

## Phase 1: Wire the Data

Complete LLM telemetry and outcome recording — the foundation everything else reads from.

### 1.1 Token Telemetry Persistence

Wire `ExecutionTelemetry` into investigation and remediation workflows. After each `router.complete()` call, invoke `budget.record_call()` with actual token counts from the LLM response.

Persist telemetry as `execution_event` type `llm_call` with JSONB payload:

```json
{
  "event_type": "llm_call",
  "model_tier": "reasoning",
  "model": "claude-sonnet-4-6",
  "input_tokens": 12400,
  "output_tokens": 1800,
  "latency_ms": 3200,
  "cache_hit": false,
  "evidence_hash": "a1b2c3d4e5f6g7h8"
}
```

No new table — reuse `execution_events`. Also track Brain chat turns: each `/work-items/{id}/chat` response emits an `analytics_event` of type `chat_llm_call` (not `execution_event`, since chat may not have an active execution). Payload includes `work_item_id`, token counts, model, and latency.

**Files to modify:**
- `apps/worker/src/pinky_worker/execution/activities.py` — emit telemetry after LLM calls
- `apps/worker/src/pinky_worker/llm/provider.py` — return token counts from `complete()`
- `apps/worker/src/pinky_worker/llm/vertex_provider.py` — extract token counts from Vertex response
- `apps/worker/src/pinky_worker/llm/anthropic_provider.py` — extract token counts from Anthropic response
- `apps/api/src/pinky_api/routes/work_items.py` — emit telemetry from chat endpoint

### 1.2 Budget Enforcement

Instantiate `ExecutionBudget` at investigation workflow start. Pass through activities. Call `budget.check()` before each LLM call. Raise `BudgetExhausted` (new exception) if exceeded — workflow catches it, marks execution as `budget_exceeded`, emits event.

Add `asyncio.Semaphore(max_concurrent_llm_calls)` in `LLMRouter`. Default 5, configurable via `PINKY_LLM_MAX_CONCURRENT` env var.

**Files to modify:**
- `apps/worker/src/pinky_worker/llm/budget.py` — add `BudgetExhausted` exception
- `apps/worker/src/pinky_worker/llm/provider.py` — add semaphore to `LLMRouter.complete()`
- `apps/worker/src/pinky_worker/workflows/investigation.py` — instantiate and pass budget
- `apps/worker/src/pinky_worker/execution/activities.py` — check budget before LLM calls

### 1.3 Outcome Recording

Emit `analytics_event` records at these points:

| Trigger | Event Type | Payload |
|---------|-----------|---------|
| Investigation completes | `investigation_completed` | execution_id, issue_id, cluster_id, confidence, tokens_used, cache_hit, duration_ms |
| Remediation completes | `remediation_completed` | execution_id, issue_id, cluster_id, outcome, tokens_used, duration_ms |
| Issue resolved | `issue_resolved` | issue_id, cluster_id, resolution_method (auto/manual), scanner |
| Issue recurred | `issue_recurred` | issue_id, cluster_id, days_since_resolution |
| Operator overrides | `operator_override` | execution_id, work_item_id, override_type |
| Approval decided | `approval_decided` | execution_id, decision (approved/rejected/expired), wait_seconds |

New migration: add `outcome` column to `executions` table (`VARCHAR(30)`, nullable). Values: `verified_fixed`, `recurred`, `operator_overridden`, `rolled_back`, `dismissed`. Set by verification workflow and operator actions.

**Files to modify:**
- New migration in `apps/api/alembic/versions/`
- `apps/worker/src/pinky_worker/execution/activities.py` — emit analytics events
- `apps/worker/src/pinky_worker/workflows/verification.py` — set outcome on execution
- `apps/worker/src/pinky_worker/workflows/remediation.py` — set outcome on failure
- `apps/api/src/pinky_api/routes/executions.py` — emit on operator override/dismiss
- `apps/api/src/pinky_api/routes/work_items.py` — emit on operator actions
- `apps/api/src/pinky_api/models/execution.py` — add outcome column

### 1.4 Tests

- Unit: `test_budget_enforcement.py` — budget check, budget exhausted, record_call accumulation
- Unit: `test_telemetry_emission.py` — mock LLM response, verify event payload structure
- Unit: `test_outcome_recording.py` — verify each trigger emits correct event type/payload
- Integration: `test_budget_workflow.py` — budget enforcement in Temporal workflow context
- Migration: verify `outcome` column added, nullable, correct type

---

## Phase 2: Analytics + ROI

Build the query layer and dashboards that consume Phase 1 data.

### 2.1 Metrics Computation Layer

Add methods to `AnalyticsRepository`:

- `get_outcomes_by_period(start, end, cluster_id?)` — returns outcome counts grouped by type
- `get_token_usage_by_period(start, end, bucket=day)` — returns time-bucketed token totals from `llm_call` execution events
- `get_cache_hit_rate(start, end)` — cache hits / total LLM calls
- `get_approval_turnaround(start, end)` — p50/p95 seconds from `approval_decided` events
- `get_signal_to_task_latency(start, end)` — p50/p95 seconds from first observation to work item creation

Wire existing `compute_*` functions in `metrics.py` to call these repository methods.

**Files to modify:**
- `apps/api/src/pinky_api/repositories/analytics.py` — add query methods
- `apps/api/src/pinky_api/analytics/metrics.py` — wire to repository

### 2.2 Scanner Quality

Populate `ScannerQuality` with real data:
- `false_positive_rate` = dismissed work items / total work items per scanner
- `noise_ratio` = suppressed observations / total observations per scanner

Query from `observations` → `issues` → `work_items` join.

**Files to modify:**
- `apps/api/src/pinky_api/routes/analytics.py` — update `/scanners` endpoint

### 2.3 Time-Series Trends API

New endpoint:

```
GET /api/v1/analytics/trends
  ?metric=issues_resolved|automation_success_rate|token_usage|cache_hit_rate|scanner_signals
  &period=1d|7d|30d|90d
  &bucket=hour|day
  &cluster_id=<optional>
```

Response: `{ metric, period, bucket_size, buckets: [{ timestamp, value }] }`

**Files to create:**
- Route handler in `apps/api/src/pinky_api/routes/analytics.py`
- Query method in `apps/api/src/pinky_api/repositories/analytics.py`

### 2.4 ROI Dashboard Upgrade

Expand `analytics-tab.tsx`:
- Trend sparklines using recharts `<AreaChart>` for key metrics (7-day default)
- Token usage card: total tokens, avg per execution, cost estimate
- Cache hit rate card with trend
- Approval turnaround card (p50/p95)
- Confidence calibration mini-chart (bar chart, 5 buckets)
- Scanner quality table: sortable columns (name, signals, suppressed, FP rate, noise ratio)

Use `queryOptions` pattern co-located in `queries.ts`. TanStack Query for data fetching.

**Files to modify:**
- `apps/web/src/app/(product)/settings/_components/analytics-tab.tsx`
- `apps/web/src/app/(product)/settings/_components/queries.ts` (or create if missing)

### 2.5 Eval Persistence

New migration: `eval_results` table:
- `id` UUID PK
- `run_id` UUID (groups results from one CI run)
- `fixture_id` VARCHAR — e.g. `oom-kill-simple`
- `grader_scores` JSONB — `{ structure: 1.0, safety: 1.0, relevance: 0.85, redaction: 1.0 }`
- `token_usage` INTEGER — total tokens for this fixture run
- `model_version` VARCHAR
- `created_at` TIMESTAMPTZ

Baselines file: `evals/baselines.json` — minimum acceptable scores per grader. CI step runs evals and compares.

**Files to create:**
- Migration in `apps/api/alembic/versions/`
- `apps/worker/evals/persist.py` — writes results to DB (or JSON file for CI)
- `evals/baselines.json`
- CI step in `.github/workflows/ci.yml`

### 2.6 Tests

- Unit: `test_analytics_queries.py` — each repository method returns correct aggregations
- Unit: `test_trends_endpoint.py` — time-series buckets, filtering, edge cases
- Unit: `test_scanner_quality.py` — FP rate and noise ratio calculations
- Frontend: vitest for analytics tab — mock API responses, verify card rendering
- Eval: `test_eval_persistence.py` — scores written and compared to baselines

---

## Phase 3: CI/Release Pipeline

### 3.1 Security Scanning

Add to `.github/workflows/ci.yml`:

```yaml
sast:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: returntocorp/semgrep-action@v1
      with:
        config: p/python p/typescript

dependency-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install pip-audit && pip-audit -r apps/api/requirements.txt
    - run: pip-audit -r apps/worker/requirements.txt
    - run: cd apps/web && npm audit --audit-level=high

secret-scan:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: trufflesecurity/trufflehog@main
      with:
        extra_args: --only-verified
```

### 3.2 Release Workflow

New file: `.github/workflows/release.yml`

Trigger: `push` on `tags: ['v*']`

Steps:
1. Build 3 container images (api, web, worker) with tag from git tag
2. Scan each image with Trivy (fail on CRITICAL/HIGH)
3. Generate SBOM with `syft` for each image
4. Sign each image with `cosign` (keyless, OIDC-based)
5. Push to `quay.io/amobrem/pinky-{api,web,worker}`
6. Create GitHub release with auto-generated changelog

### 3.3 Tests

- CI: verify semgrep, pip-audit, npm-audit, trufflehog steps pass on current codebase
- Release: dry-run workflow test (build images, don't push)

---

## Phase 4: Operational Hardening

### 4.1 OpenTelemetry

API instrumentation:
- Add `opentelemetry-instrumentation-fastapi` and `opentelemetry-instrumentation-sqlalchemy` to `apps/api/pyproject.toml`
- Initialize in `app.py` startup: `FastAPIInstrumentor.instrument_app(app)`, `SQLAlchemyInstrumentor().instrument()`
- Export: OTLP to stdout by default, configurable via `OTEL_EXPORTER_OTLP_ENDPOINT`

Worker instrumentation:
- Add `opentelemetry-sdk` to `apps/worker/pyproject.toml`
- Manual spans for: scan cycle, investigation workflow, remediation workflow, LLM call
- Temporal activity spans auto-linked to workflow traces

Helm:
- Add `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_ENDPOINT` env vars to deployments
- Optional `ServiceMonitor` template (disabled by default)

**Files to modify:**
- `apps/api/pyproject.toml`, `apps/api/src/pinky_api/app.py`
- `apps/worker/pyproject.toml`, `apps/worker/src/pinky_worker/main.py`
- `infra/helm/pinky/templates/api-deployment.yaml`, `worker-deployment.yaml`
- New: `infra/helm/pinky/templates/servicemonitor.yaml`

### 4.2 CSP Reporting

Add `report-uri /api/v1/csp-report` to CSP header directives.

New endpoint:
```python
@router.post("/csp-report")
async def csp_report(request: Request):
    body = await request.json()
    logger.warning("csp_violation", **body.get("csp-report", {}))
    return Response(status_code=204)
```

No DB storage — structured log only. Operators grep logs or route to their SIEM.

**Files to modify:**
- `apps/api/src/pinky_api/security/headers.py` — add report-uri
- `apps/api/src/pinky_api/routes/` — new csp_report route (or add to health routes)

### 4.3 Data Retention

SQL-based retention:
- `analytics_events`: delete rows older than 90 days
- `execution_events`: delete rows older than 180 days

Implemented as:
- `scripts/retention.sh` — runs the DELETE queries
- `make db-retention` Makefile target
- Documented in README as a cron job (`0 3 * * 0` — weekly at 3am)

No object storage archival in this pass — just delete. Add archival when there's a compliance requirement.

### 4.4 Chaos Testing

`tests/chaos/` directory. All tests use `@pytest.mark.chaos` (skipped by default).

| Test | What It Does |
|------|-------------|
| `test_redis_eviction.py` | FLUSHALL Redis, verify session loss triggers re-login, no data corruption |
| `test_temporal_crash.py` | SIGKILL worker mid-investigation, restart, verify workflow resumes |
| `test_sse_reconnection.py` | 100 concurrent SSE clients disconnect+reconnect, verify buffer replay |
| `test_approval_race.py` | Approve at exact timeout boundary, verify deterministic outcome |

Requires running infrastructure (`make dev-infra`). Not run in CI — manual via `make chaos-test`.

**Files to create:**
- `tests/chaos/conftest.py` — infrastructure fixtures
- `tests/chaos/test_redis_eviction.py`
- `tests/chaos/test_temporal_crash.py`
- `tests/chaos/test_sse_reconnection.py`
- `tests/chaos/test_approval_race.py`
- Makefile: `chaos-test` target

### 4.5 Tests

- OTel: verify spans emitted for API routes and DB calls (mock exporter)
- CSP: verify report endpoint logs violations
- Retention: verify DELETE queries remove old rows, keep recent ones
- Chaos: the chaos tests themselves

---

## Phase 5: Cutover

### 5.1 Feature Flags

New migration: `feature_flags` table:
- `id` UUID PK
- `flag_name` VARCHAR(100) UNIQUE
- `enabled` BOOLEAN DEFAULT false
- `scope_type` VARCHAR(20) — `global`, `principal`, `cluster`
- `scope_id` UUID nullable (null = global)
- `created_at` TIMESTAMPTZ
- `updated_at` TIMESTAMPTZ

`FeatureFlagService` class:
- `is_enabled(flag_name, principal_id=None, cluster_id=None)` — check with 30s in-memory cache
- Resolution order: principal-scoped → cluster-scoped → global → false

API: CRUD at `/api/v1/feature-flags` (admin only).

Settings UI: new "Feature Flags" tab showing all flags with toggle switches.

**Files to create:**
- Migration
- `apps/api/src/pinky_api/models/feature_flag.py`
- `apps/api/src/pinky_api/repositories/feature_flags.py`
- `apps/api/src/pinky_api/services/feature_flags.py`
- `apps/api/src/pinky_api/routes/feature_flags.py`
- `apps/web/src/app/(product)/settings/_components/feature-flags-tab.tsx`

### 5.2 Migration Utilities

`scripts/migrate-from-pulse.py`:
- Reads Pulse scanner YAML configs from a directory
- Outputs Pinky scanner markdown files to `definitions/scanners/`
- Interactive prompts for mapping decisions
- `--dry-run` flag (default on) — shows what would be created without writing

Add `origin` label to work items and issues:
- New migration: add `origin VARCHAR(20) DEFAULT 'pinky'` to `work_items` and `issues`
- Imported items tagged `origin='pulse'`

### 5.3 Tests

- Unit: `test_feature_flags.py` — flag resolution order, caching, scope precedence
- Unit: `test_feature_flag_routes.py` — CRUD, admin-only enforcement
- Unit: `test_migration_script.py` — Pulse YAML → Pinky MD conversion
- Integration: flag toggle affects runtime behavior

---

## Out of Scope (Deferred)

- Weekly/monthly analytics digest emails
- Adaptive policy threshold adjustment (needs weeks of outcome data)
- Object storage archival for analytics
- Pulse data import translators beyond scanner configs
- A/B test framework for parallel running
