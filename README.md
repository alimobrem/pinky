<p align="center">
  <img src=".github/assets/banner.svg" alt="Pinky — AI-powered Kubernetes operations" width="800" />
</p>

<p align="center">
  <a href="https://github.com/alimobrem/pinky/actions/workflows/ci.yml"><img src="https://github.com/alimobrem/pinky/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT" /></a>
  <img src="https://img.shields.io/badge/tests-1%2C217%20passing-brightgreen" alt="Tests" />
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/node-%3E%3D20-brightgreen" alt="Node >= 20" />
  <img src="https://img.shields.io/badge/k8s-1.28%2B-326CE5?logo=kubernetes&logoColor=white" alt="Kubernetes 1.28+" />
</p>

<p align="center">
  <strong>Pinky replaces alert fatigue with a task-first workflow.</strong><br />
  It continuously observes your clusters, correlates problems into actionable tasks, investigates root causes with AI, and orchestrates remediations through approval-gated workflows.
</p>

---

## Why Pinky?

Most Kubernetes monitoring tools stop at alerts. Pinky goes further:

1. **Observe** — 15 markdown-defined scanners continuously detect issues across pods, deployments, statefulsets, jobs, PVCs, resource quotas, and more
2. **Correlate** — Noisy observations become deduplicated, prioritized tasks in a single inbox
3. **Investigate** — The Brain gathers evidence from your cluster and uses Claude to produce root cause analysis with confidence scores
4. **Remediate** — Proposed fixes show a dry-run preview and changeset digest. Nothing changes without human approval
5. **Verify** — Post-remediation health checks confirm the fix worked, with automatic retry

Operators work from a **prioritized task inbox** — not a wall of alerts.

## Key Features

| Feature | Description |
|---------|-------------|
| **Automated Investigation** | Scanners detect issues, the Brain gathers evidence and produces root cause analysis |
| **Approval Gate** | Dry-run preview, changeset digest, countdown timer. Nothing changes without human approval |
| **Markdown Extensibility** | Add scanners, tools, skills, policies by writing markdown. 64 definitions ship out of the box |
| **Multi-Cluster** | Per-cluster OAuth bindings with identity isolation. Observer reads vs. user writes |
| **Real-Time UI** | SSE-powered live execution logs, progress tracking, auto-updating states |
| **Brain Chat** | Conversational interface with live cluster queries and auto-generated charts |
| **Audit Trail** | Every action recorded with who, what, when, and why |
| **Secure by Default** | AES-256-GCM encryption, credential redaction, non-root containers, TLS verification |

## Architecture

```mermaid
graph LR
    subgraph Cluster["Kubernetes Cluster"]
        O["Observer<br/><i>15 scanners</i>"] -->|scan| K8s["K8s API"]
    end

    O -->|observations| C["Correlator<br/><i>dedup + fingerprint</i>"]
    C -->|issues| P["Policy Engine<br/><i>deterministic, first-match</i>"]
    P -->|investigate| I["Investigation<br/><i>evidence + Claude</i>"]
    I -->|root cause + plan| AG["Approval Gate<br/><i>dry-run + digest</i>"]
    AG -->|approved| R["Remediation<br/><i>patch / scale / rollback</i>"]
    R -->|apply| K8s
    R -->|verify| V["Verification<br/><i>retry with backoff</i>"]
    V -->|pass| Done["Auto-Complete<br/><i>task done + issue resolved</i>"]

    style AG fill:#f9a825,stroke:#f57f17,color:#000
    style P fill:#7e57c2,stroke:#512da8,color:#fff
    style Done fill:#16a34a,stroke:#15803d,color:#fff
```

## Screenshots

| | |
|:---:|:---:|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Tasks](docs/screenshots/tasks.png) |
| **Dashboard** — Fleet overview, stat cards, Brain status, open issues | **Tasks** — Prioritized task inbox with search, filters, and preview |
| ![Task Detail](docs/screenshots/task-detail.png) | ![Watch](docs/screenshots/watch.png) |
| **Task Detail** — Brain investigation, confidence score, remediation steps | **Watch** — Live issue feed with severity filtering and SSE |
| ![Signals](docs/screenshots/watch-signals.png) | ![History](docs/screenshots/history.png) |
| **Signals** — Raw observations by scanner, check, severity, and resource | **History** — Audit trail of all events across the fleet |
| ![Analytics](docs/screenshots/analytics.png) | ![Definitions](docs/screenshots/settings-definitions.png) |
| **Analytics** — ROI metrics, token usage, cache hit rate, scanner quality | **Definitions** — 64 markdown-driven scanners, tools, skills, policies |
| ![Access](docs/screenshots/settings-access.png) | ![Maintenance](docs/screenshots/settings-maintenance.png) |
| **Access** — Cluster bindings with status and expiry | **Maintenance** — Workflow health checks and stale data cleanup |
| ![Login](docs/screenshots/login.png) | |
| **Login** — OpenShift OAuth + external OIDC | |

<details>
<summary><strong>More screenshots</strong> — Task detail views, Brain chat, cluster detail</summary>

| | |
|:---:|:---:|
| ![Remediation](docs/screenshots/task-detail-actions.png) | ![Reasoning](docs/screenshots/task-detail-reasoning.png) |
| **Remediation Steps** — Selectable actions with risk badges and "Apply" button | **Investigation Reasoning** — Full Brain analysis with root cause details |
| ![Timeline](docs/screenshots/task-detail-timeline.png) | ![Brain Chat](docs/screenshots/brain-chat.png) |
| **Timeline** — Execution lifecycle from evidence gathering to completion | **Brain Chat** — Conversational interface with suggestion chips |
| ![Cluster Detail](docs/screenshots/cluster-detail.png) | |
| **Cluster Detail** — Overview, nodes, namespaces, issues, events tabs | |

</details>

## Quick Start

### Prerequisites

- **Node.js** >= 20, **pnpm** >= 9
- **Python** 3.12+
- **Podman** or **Docker**
- **Temporal CLI** (`brew install temporal`)

### Run Locally

```bash
git clone https://github.com/alimobrem/pinky.git
cd pinky
cp .env.example .env

make dev-infra    # Start Postgres, Redis, Temporal
make db-upgrade   # Run migrations
make dev          # Start API + Worker + Web
```

| Service | URL |
|---------|-----|
| Web UI | http://localhost:3000 |
| API | http://localhost:8000 |
| Temporal UI | http://localhost:8233 |

## Configuration

Copy `.env.example` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `PINKY_DATABASE_URL` | PostgreSQL connection string | `postgresql://pinky:pinky@localhost:5432/pinky` |
| `PINKY_REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `PINKY_ENCRYPTION_KEY` | 256-bit hex key for credential encryption | *(required)* |
| `PINKY_AUTH__OPENSHIFT_*` | OpenShift OAuth configuration | *(see .env.example)* |
| `GOOGLE_CLOUD_PROJECT` | GCP project for Vertex AI (Claude) | *(optional)* |
| `PINKY_DEBUG` | Disable TLS verification for dev clusters | `false` |

See [`.env.example`](.env.example) for the full list.

## Deployment

### Helm (Kubernetes / OpenShift)

```bash
# Generate encryption key
export PINKY_ENCRYPTION_KEY=$(openssl rand -hex 32)

# Create secrets
kubectl create secret generic pinky-auth \
  --from-literal=encryption-key=$PINKY_ENCRYPTION_KEY

# Install
helm install pinky infra/helm/pinky \
  --set api.corsOrigins='["https://pinky.your-domain.com"]' \
  --set auth.callbackBaseUrl=https://pinky.your-domain.com
```

See [`infra/helm/`](infra/helm/) for the full chart documentation.

### Container Images

```bash
make docker-build   # Build all images
make docker-push    # Push to quay.io/pinky-project
```

## Extensibility

Pinky's behavior is defined by markdown files in [`definitions/`](definitions/). No code changes needed.

<details>
<summary><strong>Scanners</strong> — Define what to detect (18 operators)</summary>

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

Available operators: `eq`, `neq`, `gt`, `lt`, `gte`, `lte`, `in`, `not_in`, `contains`, `regex`, `exists`, `not_exists`, `condition_status`, `age_gt`, `cert_expires_within`, `quantity_gte`, `quantity_lt`, `promql_gt`
</details>

<details>
<summary><strong>Policies</strong> — Define what to do about it</summary>

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

Actions: `suppress`, `observe`, `investigate`, `auto-resolve`, `create-task`
</details>

<details>
<summary><strong>Tools, Skills, Pipelines</strong></summary>

- **Tools** define K8s API operations the Brain can use during investigation
- **Skills** define investigation strategies (which tools to use, what to analyze)
- **Pipelines** compose scanners into named groups with scheduling

64 definitions ship out of the box: 15 scanners, 8 tools, 12 skills, 24 policies, 3 pipelines, 2 redaction rules.
</details>

## Testing

```bash
make verify   # lint + typecheck + 1,217 tests
```

| Suite | Tests |
|-------|------:|
| API unit/integration | 430 |
| Worker unit | 611 |
| Worker integration (Temporal) | 70 |
| LLM evaluation graders | 36 |
| Contracts | 52 |
| CLI | 18 |
| **Total** | **1,217** |

## Project Structure

```
pinky/
  apps/
    api/              FastAPI backend — 78 REST endpoints, auth, CRUD, SSE
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
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS v4, shadcn/ui, TanStack Query |
| **API** | FastAPI, Pydantic v2, SQLAlchemy 2 async, asyncpg |
| **Worker** | Temporal SDK, kubernetes-asyncio, Anthropic SDK (Vertex AI) |
| **Database** | PostgreSQL 16 (24 tables, Alembic migrations) |
| **Cache** | Redis 7 |
| **Workflows** | Temporal |
| **Real-Time** | Server-Sent Events (SSE) via pg_notify |
| **Encryption** | AES-256-GCM with key versioning and AAD |
| **Containers** | Non-root (UID 1001), read-only rootfs |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code standards, and how to submit changes.

Contributions of new scanner definitions, tools, skills, and policies are especially welcome — they're just markdown files.

## Security

See [SECURITY.md](SECURITY.md) for the security architecture and how to report vulnerabilities.

## License

[MIT](LICENSE) &copy; 2026 Ali Mobrem
