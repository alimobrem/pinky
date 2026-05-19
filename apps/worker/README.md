# Pinky Worker

Temporal workflows, cluster observers, LLM integration, and policy engine. The operational brain of the platform.

## Running

```bash
make dev-worker   # Temporal worker with hot reload
```

Requires Temporal server (`make dev-infra` starts one locally).

## Directory Structure

```
src/pinky_worker/
  main.py                    Worker entry — registers workflows and activities
  workflows/
    investigation.py         Gather evidence → LLM analysis → root cause artifact
    remediation.py           Approval gate → apply changes → verify
    verification.py          Post-remediation health checks with retry
  execution/
    activities.py            Temporal activities (evidence, LLM, apply, verify, emit)
    state_machine.py         7-state execution lifecycle with validated transitions
  observation/
    observer.py              Cluster scan loop, investigation dispatch, stale sweep
    generic_scanner.py       YAML-driven scanner executor (18 operators)
    scanner_runner.py        Scanner scheduling and execution
    k8s_client.py            kubernetes-asyncio wrapper
    prom_client.py           Prometheus/Thanos query client
    fingerprint.py           Observation fingerprinting for dedup
  policy/
    engine.py                Deterministic policy evaluation (priority-ordered, first-match)
  llm/
    provider.py              LLM provider interface
    anthropic_provider.py    Anthropic API (direct)
    vertex_provider.py       Vertex AI (Claude via Google Cloud)
    cache.py                 Investigation result caching by evidence hash
    redaction.py             11-pattern credential redaction before LLM prompts
    budget.py                Token budget tracking
  issues/
    correlator.py            Observation → Issue correlation and dedup
    db_correlator.py         PostgreSQL-backed correlator with upsert
  definitions/
    loader.py                Markdown definition registry (scanners, tools, skills, policies)
  webhooks/
    delivery.py              Webhook payload formatting and delivery
    formatters.py            Event → webhook payload transformation
  security.py                AES-256-GCM decryption (mirrors API crypto module)
  db.py                      asyncpg connection pool
  config.py                  Worker configuration
```

## Workflows

### Investigation
1. `gather_evidence` — Calls K8s API using skill-defined tools (logs, describe, top, events, Prometheus)
2. `check_artifact_cache` — Skip LLM if identical evidence seen recently
3. `run_investigation` — LLM analyzes evidence, produces root cause + recommended action + plan steps
4. `store_artifact` — Persists artifact, creates approval record with changeset digest

### Remediation
1. Emit `approval_required` → workflow waits for signal (4h timeout)
2. On approve: `validate_approval` (digest match) → `revalidate_binding` (token still valid)
3. For each plan step: `apply_change` (patch, scale, delete_pod, rollback) via user's token
4. `VerificationWorkflow` (child) — checks target resources with up to 3 retries
5. Auto-complete: verified remediation → work_item done, issue resolved

### Verification
- Waits `delay_seconds` (default 60s), then checks each target resource
- Retries up to `max_attempts` times with backoff on failure
- Checks deployment Available condition + readyReplicas >= desired

## Observer

The observer runs a continuous scan loop:
1. Load scanner definitions from `DefinitionRegistry`
2. Execute each scanner against the cluster (generic YAML-driven execution)
3. Correlate observations into issues (dedup by correlation key)
4. Evaluate policy rules (first-match-wins, deterministic)
5. Dispatch investigation workflows for matching issues
6. Sweep stale issues (not seen in 2 scan cycles → resolve)

## Testing

```bash
cd apps/worker
.venv/bin/pytest tests/ -v                          # 681 tests (611 unit + 70 integration)
.venv/bin/pytest tests/integration/ -v              # 70 integration tests (needs Temporal + Postgres)
.venv/bin/pytest evals/ -v                          # 36 LLM evaluation graders
```

Integration tests use a real Temporal dev server and real Postgres with transaction rollback.
