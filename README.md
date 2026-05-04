# Pinky

Task-first multi-cluster Kubernetes operations platform with an embedded SRE agent, **The Brain**.

Pinky observes clusters, correlates problems into actionable tasks, investigates root causes with LLM analysis, and orchestrates remediations through approval-gated Temporal workflows. Operators work from a prioritized task inbox — not a wall of alerts.

## Architecture

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Next.js    │   │   FastAPI    │   │   Temporal   │
│   Web UI     │──▶│   API        │──▶│   Worker     │
│   :3000      │   │   :8000      │   │              │
└──────────────┘   └──────┬───────┘   └──────┬───────┘
                          │                  │
                   ┌──────▼───────┐   ┌──────▼───────┐
                   │  PostgreSQL  │   │  K8s Clusters │
                   │  + Redis     │   │  (observed)   │
                   └──────────────┘   └──────────────┘
```

**Web** → Task inbox, watch feed, dashboard, settings, history, alerts. Real-time via SSE.
**API** → REST endpoints, auth (OpenShift OAuth / OIDC), RBAC, session management.
**Worker** → Cluster observer, issue correlator, investigation/remediation/approval/verification workflows, LLM integration (Vertex AI Claude).

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

### Worker Integration Tests

Require local Postgres and Temporal CLI:
```bash
brew install temporal                        # macOS
cd apps/worker && pytest tests/integration/  # 26 tests
```

Tests use transaction rollback — no data persists between tests.

### LLM Evaluation

Deterministic graders test investigation output quality without LLM calls:
- **Structure**: output has summary, root cause, recommendation sections
- **Safety**: no dangerous actions (namespace deletion, RBAC disabling)
- **Relevance**: output mentions expected keywords from evidence
- **Redaction**: no secrets survive in LLM prompts

```bash
cd apps/worker && pytest evals/ -v           # 36 tests, no API key needed
```

## Deploying

```bash
# Preflight check (cluster connectivity, secrets, images)
./scripts/preflight.sh infra/helm/values-dev.yaml

# Deploy (creates K8s secrets from secrets/ dir, runs helm upgrade)
./scripts/deploy.sh infra/helm/values-dev.yaml
```

### Secrets

Secrets live in `secrets/` (gitignored). The deploy script creates K8s secrets from these files:
- `secrets/oauth-client-secret` — OpenShift OAuth client secret
- `secrets/vertex-credentials.json` — Google Vertex AI service account key

Pre-commit and pre-push hooks block accidental secret commits.

### Vertex AI Setup

1. Create a GCP service account with `Vertex AI User` role
2. Download JSON key to `secrets/vertex-credentials.json`
3. Set `llm.vertexProjectId` in `infra/helm/values-dev.yaml`
4. Run `./scripts/deploy.sh`

## CI

**Every PR** (`.github/workflows/ci.yml`):
- `api-tests` — lint + 99 tests against Postgres
- `worker-tests` — lint + 72 unit tests
- `worker-integration` — 26 tests against Postgres + Temporal
- `web-checks` — typecheck + build

**Weekly**:
- `eval.yml` — LLM evaluation graders (36 tests)
- `perf.yml` — API latency benchmarks (10 endpoints)

## Key Concepts

**Tasks** — Prioritized work items generated from cluster observations. Status: ready → accepted → in_progress → done (or blocked).

**Issues** — Correlated operational problems. Multiple observations from the same source deduplicate into one issue. Issues reopen if re-detected after resolution.

**Investigations** — LLM-powered analysis. The Brain gathers evidence (pods, events), redacts secrets, and produces structured findings (summary, root cause, recommendation).

**Executions** — Temporal workflows for remediation. Require human approval, execute K8s changes (scale, restart, patch, rollback), and verify results.

**Definitions** — Markdown files with YAML frontmatter that define scanners, skills, policies, tools, and pipelines. The extensibility mechanism.

**Policy Engine** — Deterministic, priority-ordered rules. First match wins. No LLM in the policy pipeline.
