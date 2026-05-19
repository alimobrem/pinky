# Pinky

**AI-powered Kubernetes operations platform that investigates cluster issues, proposes fixes, and applies them with human approval.**

[![CI](https://github.com/alimobrem/pinky/actions/workflows/ci.yml/badge.svg)](https://github.com/alimobrem/pinky/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Pinky replaces alert fatigue with a task-first workflow. It continuously observes your clusters, correlates problems into actionable tasks, uses LLM analysis to investigate root causes, and orchestrates remediations through approval-gated workflows. Operators work from a prioritized task inbox — not a wall of alerts.

## Key Features

- **Automated Investigation** — Scanners detect issues, the Brain gathers evidence and produces root cause analysis with confidence scores
- **Remediation with Approval Gate** — Proposed fixes show a dry-run preview, changeset digest, and countdown timer. Nothing changes without human approval
- **Markdown-Driven Extensibility** — Add scanners, tools, skills, policies, and pipelines by writing markdown files. No code changes needed. 53 definitions ship out of the box
- **Multi-Cluster** — Per-cluster OAuth bindings with identity isolation. Observer reads use a service account; remediations use the approver's token
- **Real-Time** — SSE-powered UI with live execution logs, progress tracking, and auto-updating task states
- **Audit Trail** — Every action (investigate, approve, reject, remediate, verify) is recorded with who, what, when, and why
- **Conversational** — Chat with the Brain about any task. It queries your cluster live (kubectl, metrics, Prometheus) and generates charts

## Architecture

```mermaid
graph LR
    subgraph Cluster
        O[Observer] -->|scan| K8s[K8s API]
    end

    O -->|observations| C[Correlator]
    C -->|issues| P[Policy Engine]
    P -->|investigate| I[Investigation Workflow]
    I -->|evidence + LLM| A[Artifact: Root Cause + Plan]
    A -->|approval required| AG[Approval Gate]
    AG -->|approved| R[Remediation Workflow]
    R -->|apply changes| K8s
    R -->|verify| V[Verification]
    V -->|pass/fail| Complete[Auto-Complete Task]

    style AG fill:#f9a825,stroke:#f57f17,color:#000
    style P fill:#7e57c2,stroke:#512da8,color:#fff
```

**Observer** scans clusters using markdown-defined scanners (13 shipped). **Policy Engine** applies deterministic rules to decide actions. **Investigation** gathers evidence and uses Claude to analyze root cause. **Remediation** applies fixes with signal-based approval, digest validation, and binding revalidation. **Verification** checks target resources with retry.

## Quick Start

### Prerequisites

- Node.js >= 20, pnpm >= 9
- Python 3.12+
- Podman or Docker
- Temporal CLI (`brew install temporal`)

### Run Locally

```bash
git clone https://github.com/alimobrem/pinky.git
cd pinky
cp .env.example .env

# Start Postgres, Redis, Temporal
make dev-infra

# Run migrations
make db-upgrade

# Start API + Worker + Web
make dev
```

- **Web UI:** http://localhost:3000
- **API:** http://localhost:8000
- **Temporal UI:** http://localhost:8080

## Configuration

Copy `.env.example` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `PINKY_DATABASE_URL` | PostgreSQL connection string | `postgresql://pinky:pinky@localhost:5432/pinky` |
| `PINKY_REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `PINKY_ENCRYPTION_KEY` | 256-bit hex key for credential encryption | (required) |
| `PINKY_AUTH__OPENSHIFT_*` | OpenShift OAuth configuration | (see .env.example) |
| `GOOGLE_CLOUD_PROJECT` | GCP project for Vertex AI (Claude) | (optional) |
| `PINKY_DEBUG` | Disable TLS verification for dev clusters | `false` |

See [`.env.example`](.env.example) for the full list.

## Deployment

### Helm (Kubernetes / OpenShift)

```bash
# Create secrets
export PINKY_ENCRYPTION_KEY=$(openssl rand -hex 32)
kubectl create secret generic pinky-auth \
  --from-literal=encryption-key=$PINKY_ENCRYPTION_KEY

# Install
helm install pinky infra/helm/pinky \
  --set api.corsOrigins='["https://pinky.your-domain.com"]' \
  --set auth.callbackBaseUrl=https://pinky.your-domain.com
```

See [`infra/helm/`](infra/helm/) for full chart documentation and `values.yaml` reference.

### Container Images

```bash
make docker-build   # Build all images
make docker-push    # Push to quay.io/pinky-project
```

## Extensibility

Pinky's behavior is defined by markdown files in `definitions/`. No code changes needed.

### Scanners

Define what to detect. 18 operators available (eq, gt, age_gt, cert_expires_within, quantity_gte, promql_gt, etc.):

```yaml
# definitions/scanners/pod-health.md (frontmatter)
name: pod-health
resource_kinds: [Pod]
checks:
  - id: crash-loop
    title: "Pod CrashLoopBackOff"
    severity: high
    conditions:
      - field: status.containerStatuses[*].state.waiting.reason
        operator: eq
        value: "CrashLoopBackOff"
```

### Policies

Define what to do about it. Deterministic, priority-ordered, first-match-wins:

```yaml
# definitions/policies/investigate-critical.md (frontmatter)
name: investigate-critical
priority: 100
conditions:
  severity: critical
  observation_count_gte: 2
action:
  type: investigate
  skill: k8s-crash-investigation
```

### Tools, Skills, Pipelines

- **Tools** define K8s API operations the Brain can use during investigation
- **Skills** define investigation strategies (which tools, what to analyze)
- **Pipelines** compose scanners into named groups with scheduling

See [`definitions/`](definitions/) for all 53 shipped definitions.

## Testing

```bash
make verify   # lint + typecheck + 1,156 tests
```

| Suite | Tests |
|-------|-------|
| API unit/integration | 417 |
| Worker unit | 611 |
| Worker integration (Temporal) | 70 |
| LLM evaluation graders | 36 |
| Contracts | 22 |
| **Total** | **1,156** |

## Project Structure

```
apps/
  api/              FastAPI backend — 63 REST endpoints, auth, CRUD, SSE
  web/              Next.js 15 frontend — Dashboard, Tasks, Watch, History
  worker/           Temporal workflows, cluster observers, LLM integration
  cli/              CLI tool wrapping the REST API
packages/
  contracts/        Shared TypeScript domain types
  design-system/    React component library (shadcn/ui)
definitions/        Markdown-driven scanners, tools, skills, policies, pipelines
infra/
  docker/           Docker Compose for local development
  helm/             Helm chart for Kubernetes/OpenShift
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query |
| API | FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg |
| Worker | Temporal SDK, kubernetes-asyncio, Anthropic SDK (Vertex AI) |
| Database | PostgreSQL 16 (24 tables, Alembic migrations) |
| Cache/Sessions | Redis 7 |
| Workflows | Temporal |
| Real-Time | Server-Sent Events (SSE) via pg_notify |
| Encryption | AES-256-GCM with key versioning |
| Containers | Non-root (UID 1001), read-only rootfs |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code standards, and how to submit changes.

Contributions of new scanner definitions, tools, skills, and policies are especially welcome — they're just markdown files.

## Security

See [SECURITY.md](SECURITY.md) for the security architecture and how to report vulnerabilities.

## License

[MIT](LICENSE) - Copyright (c) 2026 Ali Mobrem
