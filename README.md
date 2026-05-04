# Pinky

Pinky is a task-first multi-cluster Kubernetes operations platform with an embedded SRE agent, `The Brain`.

## Repo Layout

- `apps/web`: Next.js product UI
- `apps/api`: FastAPI backend
- `apps/worker`: Temporal workflows, observers, and projections
- `packages/contracts`: shared TypeScript contracts
- `infra/docker`: local infrastructure compose stack
- `infra/helm/pinky`: Helm chart

## Local Development

```bash
make dev-infra
make dev-api
make dev-worker
make dev-web
```

Or start everything together:

```bash
make dev
```

## Verification

Core verification commands:

```bash
make lint
make typecheck
make test
make verify
```

Useful focused checks:

```bash
cd apps/api && .venv/bin/python -m pytest tests/ -q
cd apps/worker && .venv/bin/python -m pytest tests/ -q
pnpm --filter @pinky/web typecheck
pnpm --filter @pinky/web build
helm lint infra/helm/pinky
helm template pinky infra/helm/pinky >/tmp/pinky-rendered.yaml
podman compose -f infra/docker/docker-compose.yml config >/tmp/pinky-compose.yaml
```

The API test environment includes `pytest-timeout` in `apps/api` dev dependencies because CI runs the API suite with `pytest --timeout=30`.

## Deploying

Run the preflight before deploying:

```bash
./scripts/preflight.sh infra/helm/values-dev.yaml
```

Deploy with:

```bash
./scripts/deploy.sh infra/helm/values-dev.yaml
```

When `PINKY_BUILD=true`, the deploy script now assigns a unique image tag and deploy ID so Helm upgrades trigger real pod rollouts instead of reusing an unchanged `latest` template.

### Vertex Credentials

Cluster deployment only accepts a Vertex credential file whose JSON `type` is `service_account`.

- accepted: dedicated Google service account key JSON
- rejected: local `authorized_user` ADC credentials

The secure default is enforced by both `scripts/preflight.sh` and `scripts/deploy.sh`.

## Secret Protection

Sensitive local files should live under `secrets/`, which is gitignored.

For extra protection in this clone, install the local git hooks:

```bash
./scripts/install-git-hooks.sh
```

That installs `pre-commit` and `pre-push` hooks that block commits or pushes when they include secret-like files or high-signal credential material.
