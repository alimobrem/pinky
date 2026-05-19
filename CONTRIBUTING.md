# Contributing to Pinky

Thank you for your interest in contributing to Pinky. This guide covers the development workflow, code standards, and how to submit changes.

## Prerequisites

- **Node.js** >= 20, **pnpm** >= 9
- **Python** 3.12+
- **Podman** or **Docker** (for local infrastructure)
- **Temporal CLI** (`brew install temporal` on macOS)
- **PostgreSQL 16** and **Redis 7** (provided via `make dev-infra`)

## Getting Started

```bash
# Clone the repo
git clone https://github.com/alimobrem/pinky.git
cd pinky

# Copy environment config
cp .env.example .env

# Start infrastructure (Postgres, Redis, Temporal)
make dev-infra

# Run database migrations
make db-upgrade

# Start all services
make dev
```

The API runs on `http://localhost:8000`, the web UI on `http://localhost:3000`.

## Development Workflow

1. **Fork** the repository and create a feature branch from `main`
2. **Make your changes** — keep PRs focused on a single concern
3. **Run `make verify`** — this runs lint, typecheck, and all tests. Your PR will not be merged if this fails.
4. **Submit a pull request** against `main`

## Code Standards

### Python (API + Worker)

- **Formatter/linter:** [ruff](https://docs.astral.sh/ruff/)
- **Type checker:** [pyright](https://github.com/microsoft/pyright) in strict mode
- **Style:** No `# type: ignore`, no `except Exception: pass`, no inline comments explaining what code does

### TypeScript (Web + Contracts)

- **Linter:** ESLint
- **Type checker:** `tsc --noEmit`
- **Styling:** Tailwind CSS v4 utility classes only — no inline styles, no CSS modules
- **Components:** Use shadcn/ui primitives, import types from `@pinky/contracts`
- **Data fetching:** TanStack Query with co-located `queries.ts` per page

### Running Checks

```bash
make lint        # ruff + eslint
make typecheck   # pyright + tsc
make test        # pytest + vitest
make verify      # all of the above
```

## Project Structure

```
apps/
  api/       FastAPI backend (Python)
  web/       Next.js frontend (TypeScript)
  worker/    Temporal workflows + observers (Python)
  cli/       CLI tool (Python)
packages/
  contracts/       Shared TypeScript types
  design-system/   React component library
definitions/       Markdown-driven scanners, tools, skills, policies
infra/
  docker/    Docker Compose for local dev
  helm/      Helm chart for Kubernetes/OpenShift
```

## Contributing Definitions

Pinky's extensibility is driven by markdown files in `definitions/`. You can contribute new scanners, tools, skills, policies, and pipelines without writing any Python or TypeScript.

### Adding a Scanner

Create a markdown file in `definitions/scanners/` with YAML frontmatter:

```markdown
---
name: my-scanner
resource_kinds: [Pod]
schedule: "*/5 * * * *"
checks:
  - id: my-check
    title: "My custom check"
    severity: medium
    conditions:
      - field: status.phase
        operator: eq
        value: "Failed"
---

# My Scanner

Description of what this scanner detects and why it matters.
```

See existing scanners in `definitions/scanners/` for examples.

### Adding a Tool

Create a markdown file in `definitions/tools/` — tools are K8s API operations that the investigation workflow can use to gather evidence.

### Adding a Skill

Create a markdown file in `definitions/skills/` — skills are investigation strategies that define which tools to use and how to analyze the evidence.

### Adding a Policy

Create a markdown file in `definitions/policies/` — policies are deterministic rules that map scanner results to actions (suppress, observe, investigate, auto-resolve).

## Commit Messages

Write concise commit messages that explain **why**, not what:

```
Fix verification false negatives on slow rollouts

Verification now retries up to 3 times with 60s backoff instead of
a single check. Database deployments often take >60s to roll out.
```

## Developer Certificate of Origin

By contributing to this project, you certify that your contribution was created in whole or in part by you and you have the right to submit it under the MIT license. All commits must include a `Signed-off-by` line:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s` to add this automatically.

## Reporting Issues

- **Bugs:** Use the [bug report template](https://github.com/alimobrem/pinky/issues/new?template=bug_report.md)
- **Features:** Use the [feature request template](https://github.com/alimobrem/pinky/issues/new?template=feature_request.md)
- **Security:** See [SECURITY.md](SECURITY.md) for responsible disclosure

## Questions?

Open a [Discussion](https://github.com/alimobrem/pinky/discussions) for general questions about using or developing Pinky.
