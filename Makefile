.PHONY: dev dev-infra dev-api dev-worker dev-web dev-web-clean lint typecheck test verify clean db-upgrade db-migrate db-retention docker-build docker-push helm-lint helm-template deploy

# Development
CONTAINER_ENGINE ?= podman

dev-infra:
	$(CONTAINER_ENGINE) compose -f infra/docker/docker-compose.yml up -d

dev-api:
	cd apps/api && .venv/bin/uvicorn pinky_api.app:app --reload --port 8000

dev-worker:
	cd apps/worker && .venv/bin/python -m pinky_worker.main

dev-web:
	pnpm --filter @pinky/web dev

dev-web-clean:
	rm -rf apps/web/.next && pnpm --filter @pinky/web dev

dev: dev-infra
	@echo "Starting all services..."
	$(MAKE) -j3 dev-api dev-worker dev-web

# Lint
lint:
	cd apps/api && .venv/bin/python -m ruff check src/
	cd apps/worker && .venv/bin/python -m ruff check src/
	cd apps/cli && .venv/bin/python -m ruff check src/
	pnpm -r lint

# Type check
typecheck:
	cd apps/api && .venv/bin/python -m pyright src/
	cd apps/worker && .venv/bin/python -m pyright src/
	pnpm -r typecheck

# Test
test:
	cd apps/api && .venv/bin/python -m pytest tests/ -v
	cd apps/worker && .venv/bin/python -m pytest tests/ -v
	cd apps/cli && .venv/bin/python -m pytest tests/ -v
	pnpm -r test

# All checks
verify: lint typecheck test

# Database
db-upgrade:
	cd apps/api && .venv/bin/python -m alembic upgrade head

db-migrate:
	cd apps/api && .venv/bin/python -m alembic revision --autogenerate -m "$(MSG)"

db-retention:
	./scripts/retention.sh

# Docker
REGISTRY ?= $(shell oc registry info 2>/dev/null || echo "localhost:5000")
TAG ?= latest
PLATFORM ?= linux/amd64

docker-build:
	$(CONTAINER_ENGINE) build --platform $(PLATFORM) -f infra/docker/Dockerfile.api -t $(REGISTRY)/pinky-api:$(TAG) .
	$(CONTAINER_ENGINE) build --platform $(PLATFORM) -f infra/docker/Dockerfile.web -t $(REGISTRY)/pinky-web:$(TAG) .
	$(CONTAINER_ENGINE) build --platform $(PLATFORM) -f infra/docker/Dockerfile.worker -t $(REGISTRY)/pinky-worker:$(TAG) .

docker-push:
	$(CONTAINER_ENGINE) push $(REGISTRY)/pinky-api:$(TAG)
	$(CONTAINER_ENGINE) push $(REGISTRY)/pinky-web:$(TAG)
	$(CONTAINER_ENGINE) push $(REGISTRY)/pinky-worker:$(TAG)

# Helm
helm-lint:
	helm lint infra/helm/pinky

helm-template:
	helm template pinky infra/helm/pinky

deploy:
	./scripts/deploy.sh $(VALUES)

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	pnpm -r clean
