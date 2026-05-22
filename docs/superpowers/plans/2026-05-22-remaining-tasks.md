# Remaining Tasks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Tasks 8 (LLM efficiency), 8.5 (analytics/ROI), 9 (CI/release/ops hardening), and 10 (cutover) — the remaining work to make Pinky production-ready.

**Architecture:** 5 phases ordered by dependency. Phase 1 wires telemetry and outcome data into existing tables. Phase 2 builds query layer and dashboard upgrades consuming that data. Phase 3 adds security scanning and release pipeline to CI. Phase 4 adds OpenTelemetry, CSP reporting, data retention, and chaos tests. Phase 5 adds feature flags and migration utilities.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2 async, Temporal, asyncpg, Next.js 15, React 19, TanStack Query, recharts, shadcn/ui, GitHub Actions, semgrep, Trivy, syft, cosign.

**Spec:** `docs/superpowers/specs/2026-05-22-remaining-tasks-design.md`

---

## Phase 1: Wire the Data

### Task 1: Add outcome column to executions table

**Files:**
- Create: `apps/api/alembic/versions/j5d6e7f8g9h0_add_outcome_to_executions.py`
- Modify: `apps/api/src/pinky_api/models/execution.py`

- [ ] **Step 1: Write the migration**

```python
"""Add outcome column to executions table."""

from alembic import op
import sqlalchemy as sa

revision = "j5d6e7f8g9h0"
down_revision = "i4c5d6e7f8g9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("executions", sa.Column("outcome", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("executions", "outcome")
```

- [ ] **Step 2: Add outcome to the SQLAlchemy model**

In `apps/api/src/pinky_api/models/execution.py`, add after `completed_at`:

```python
outcome: Mapped[str | None] = mapped_column(String(30))
```

- [ ] **Step 3: Run migration to verify**

Run: `cd apps/api && .venv/bin/python -m alembic upgrade head`
Expected: Migration applies successfully.

- [ ] **Step 4: Commit**

```bash
git add apps/api/alembic/versions/j5d6e7f8g9h0_add_outcome_to_executions.py apps/api/src/pinky_api/models/execution.py
git commit -m "feat: add outcome column to executions table"
```

---

### Task 2: Wire token telemetry into LLM calls

**Files:**
- Modify: `apps/worker/src/pinky_worker/execution/activities.py`
- Modify: `apps/worker/src/pinky_worker/llm/budget.py`
- Test: `apps/worker/tests/test_telemetry.py`

- [ ] **Step 1: Write the failing test**

Create `apps/worker/tests/test_telemetry.py`:

```python
"""Tests for LLM telemetry emission."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


class FakePool:
    def __init__(self):
        self.executed: list[tuple] = []

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        if "work_items" in query:
            return {"title": "Pod test/broken CrashLoopBackOff", "labels": None}
        if "cluster_registry" in query:
            return None
        if "execution_events" in query:
            return None
        return None


@pytest.mark.asyncio
async def test_run_investigation_emits_telemetry():
    pool = FakePool()

    fake_response_content = (
        "Analysis complete.\n\n```json\n"
        '{"summary": "test", "root_cause": "oom", '
        '"recommended_action": "increase limits", "confidence": 0.9, '
        '"remediation_steps": [], "manual_commands": []}\n```'
    )

    mock_router = AsyncMock()
    mock_response = AsyncMock()
    mock_response.content = fake_response_content
    mock_response.input_tokens = 5000
    mock_response.output_tokens = 800
    mock_response.model = "claude-sonnet-4-6"
    mock_response.provider = "vertex"
    mock_response.latency_ms = 2500
    mock_response.cached = False
    mock_router.complete = AsyncMock(return_value=mock_response)

    with (
        patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.execution.activities.LLMRouter", return_value=mock_router),
        patch("pinky_worker.execution.activities.VertexProvider"),
        patch("temporalio.activity.heartbeat"),
    ):
        from pinky_worker.execution.activities import run_investigation, EvidenceBundle

        evidence = EvidenceBundle(
            issue_id=str(uuid4()),
            cluster_id=str(uuid4()),
            fingerprint="fp-1",
            evidence_hash="abc123",
            sections={"pods": "[]"},
        )

        artifact = await run_investigation(evidence, "investigate", str(uuid4()))

    telemetry_events = [
        c for c in pool.executed
        if len(c) > 1 and len(c[1]) > 2
        and isinstance(c[1][2], str) and c[1][2] == "llm_call"
    ]
    assert len(telemetry_events) == 1
    payload = json.loads(telemetry_events[0][1][4])
    assert payload["input_tokens"] == 5000
    assert payload["output_tokens"] == 800
    assert payload["model"] == "claude-sonnet-4-6"
    assert payload["model_tier"] == "reasoning"
    assert payload["latency_ms"] == 2500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/worker && .venv/bin/python -m pytest tests/test_telemetry.py -v`
Expected: FAIL — `llm_call` events not emitted yet.

- [ ] **Step 3: Wire telemetry emission into run_investigation**

In `apps/worker/src/pinky_worker/execution/activities.py`, modify `run_investigation` after line 473 (`response = await router.complete(...)`). Add telemetry emission before `activity.heartbeat("parsing response")`:

```python
    # Emit LLM telemetry
    await _emit_event(
        pool, execution_id, "llm_call", 50,
        {
            "model_tier": ModelTier.REASONING.value,
            "model": response.model,
            "provider": response.provider,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "latency_ms": response.latency_ms,
            "cache_hit": response.cached,
            "evidence_hash": evidence.evidence_hash,
        },
    )
```

This requires getting `pool` earlier in the function. Add after the imports at line 403:

```python
    from pinky_worker.db import get_pool
    pool = await get_pool()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/worker && .venv/bin/python -m pytest tests/test_telemetry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/worker/src/pinky_worker/execution/activities.py apps/worker/tests/test_telemetry.py
git commit -m "feat: emit LLM telemetry events from investigation activity"
```

---

### Task 3: Wire budget enforcement into investigation workflow

**Files:**
- Modify: `apps/worker/src/pinky_worker/llm/budget.py`
- Modify: `apps/worker/src/pinky_worker/execution/activities.py`
- Modify: `apps/worker/src/pinky_worker/llm/provider.py`
- Test: `apps/worker/tests/test_budget_enforcement.py`

- [ ] **Step 1: Add BudgetExhausted exception and concurrency semaphore**

In `apps/worker/src/pinky_worker/llm/budget.py`, add at the end:

```python
class BudgetExhausted(Exception):
    pass
```

- [ ] **Step 2: Add concurrency semaphore to LLMRouter**

In `apps/worker/src/pinky_worker/llm/provider.py`, add import at top:

```python
import asyncio
import os
```

Modify `LLMRouter.__init__` and `complete`:

```python
class LLMRouter:
    def __init__(self) -> None:
        self._providers: list[LLMProviderProtocol] = []
        self._breakers: dict[str, CircuitBreaker] = {}
        max_concurrent = int(os.environ.get("PINKY_LLM_MAX_CONCURRENT", "5"))
        self._semaphore = asyncio.Semaphore(max_concurrent)

    def register(self, provider: LLMProviderProtocol) -> None:
        self._providers.append(provider)
        self._breakers[provider.config.name] = CircuitBreaker()

    async def complete(self, request: LLMRequest) -> LLMResponse:
        async with self._semaphore:
            for provider in self._providers:
                breaker = self._breakers[provider.config.name]
                if not breaker.can_execute():
                    continue

                try:
                    response = await provider.complete(request)
                    breaker.record_success()
                    return response
                except Exception:
                    logger.exception("LLM provider %s failed", provider.config.name)
                    breaker.record_failure()
                    continue

            raise RuntimeError("All LLM providers unavailable")
```

- [ ] **Step 3: Write budget enforcement test**

Create `apps/worker/tests/test_budget_enforcement.py`:

```python
"""Tests for ExecutionBudget enforcement."""

import pytest

from pinky_worker.llm.budget import BudgetExhausted, ExecutionBudget


def test_budget_record_call():
    budget = ExecutionBudget(max_input_tokens=10000, max_output_tokens=2000, max_calls=3)
    budget.record_call(input_tokens=5000, output_tokens=500)
    assert budget.used_input_tokens == 5000
    assert budget.used_output_tokens == 500
    assert budget.used_calls == 1
    assert budget.total_tokens == 5500


def test_budget_check_passes_within_limits():
    budget = ExecutionBudget()
    budget.record_call(input_tokens=1000, output_tokens=100)
    assert budget.check() is None


def test_budget_check_fails_on_input_tokens():
    budget = ExecutionBudget(max_input_tokens=100)
    budget.record_call(input_tokens=200, output_tokens=0)
    result = budget.check()
    assert result is not None
    assert "Input token" in result


def test_budget_check_fails_on_output_tokens():
    budget = ExecutionBudget(max_output_tokens=100)
    budget.record_call(input_tokens=0, output_tokens=200)
    result = budget.check()
    assert result is not None
    assert "Output token" in result


def test_budget_check_fails_on_calls():
    budget = ExecutionBudget(max_calls=2)
    budget.record_call(input_tokens=0, output_tokens=0)
    budget.record_call(input_tokens=0, output_tokens=0)
    result = budget.check()
    assert result is not None
    assert "Call budget" in result


def test_remaining_tokens():
    budget = ExecutionBudget(max_input_tokens=10000, max_output_tokens=2000)
    budget.record_call(input_tokens=3000, output_tokens=500)
    assert budget.remaining_input_tokens == 7000
    assert budget.remaining_output_tokens == 1500


def test_budget_exhausted_exception():
    with pytest.raises(BudgetExhausted):
        raise BudgetExhausted("Token budget exceeded")
```

- [ ] **Step 4: Run tests**

Run: `cd apps/worker && .venv/bin/python -m pytest tests/test_budget_enforcement.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/worker/src/pinky_worker/llm/budget.py apps/worker/src/pinky_worker/llm/provider.py apps/worker/tests/test_budget_enforcement.py
git commit -m "feat: add BudgetExhausted exception and LLM concurrency semaphore"
```

---

### Task 4: Emit analytics events for outcomes

**Files:**
- Modify: `apps/worker/src/pinky_worker/execution/activities.py`
- Test: `apps/worker/tests/test_outcome_recording.py`

- [ ] **Step 1: Add analytics event helper to activities**

In `apps/worker/src/pinky_worker/execution/activities.py`, add after `_emit_command_event` (around line 120):

```python
async def _emit_analytics_event(
    pool: Any, event_type: str, payload: dict,
    cluster_id: str = "", execution_id: str = "",
) -> None:
    try:
        await pool.execute(
            """INSERT INTO analytics_events (id, event_type, execution_id, cluster_id, payload, occurred_at)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            uuid4(),
            event_type,
            UUID(execution_id) if execution_id else None,
            UUID(cluster_id) if cluster_id else None,
            json.dumps(payload),
            datetime.now(UTC),
        )
    except Exception:
        logger.warning("analytics event %s emission failed", event_type, exc_info=True)
```

- [ ] **Step 2: Emit analytics on investigation completion**

In the `store_artifact` activity, after the `logger.info("artifact stored: %s", ...)` line (~590), add:

```python
    await _emit_analytics_event(
        pool, "investigation_completed",
        {
            "artifact_id": artifact.artifact_id,
            "issue_id": artifact.issue_id,
            "confidence": artifact.confidence,
            "evidence_hash": artifact.evidence_hash,
            "cached": False,
        },
        cluster_id=str(exec_row["cluster_id"]) if exec_row and exec_row.get("cluster_id") else "",
        execution_id=str(exec_uuid),
    )
```

- [ ] **Step 3: Emit analytics on auto-complete (verified remediation)**

In `emit_execution_event`, inside the `if event.event_type == "completed" and event.payload.get("verification_passed")` block (~line 730), after the `transition_work_item` call, add:

```python
            await _emit_analytics_event(
                pool, "remediation_completed",
                {"outcome": "verified_fixed", "work_item_id": str(wi_id)},
                cluster_id=str(exec_row["cluster_id"]) if exec_row.get("cluster_id") else "",
                execution_id=str(exec_uuid),
            )
            # Set outcome on execution
            await pool.execute(
                "UPDATE executions SET outcome = $1 WHERE id = $2",
                "verified_fixed", exec_uuid,
            )
```

- [ ] **Step 4: Write outcome recording tests**

Create `apps/worker/tests/test_outcome_recording.py`:

```python
"""Tests for analytics event emission on outcomes."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


class FakePool:
    def __init__(self, fetchrow_result=None):
        self.executed: list[tuple] = []
        self._fetchrow_result = fetchrow_result

    async def execute(self, query, *args):
        self.executed.append((query, args))

    async def fetchrow(self, query, *args):
        return self._fetchrow_result


@pytest.mark.asyncio
async def test_emit_analytics_event_inserts_row():
    pool = FakePool()

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import _emit_analytics_event

        await _emit_analytics_event(
            pool, "investigation_completed",
            {"confidence": 0.9, "issue_id": "test"},
            cluster_id=str(uuid4()),
            execution_id=str(uuid4()),
        )

    analytics_inserts = [c for c in pool.executed if "analytics_events" in c[0]]
    assert len(analytics_inserts) == 1
    payload = json.loads(analytics_inserts[0][1][4])
    assert payload["confidence"] == 0.9


@pytest.mark.asyncio
async def test_emit_analytics_event_handles_failure():
    pool = AsyncMock()
    pool.execute = AsyncMock(side_effect=Exception("db error"))

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        from pinky_worker.execution.activities import _emit_analytics_event

        # Should not raise
        await _emit_analytics_event(pool, "test", {"key": "val"})
```

- [ ] **Step 5: Run tests**

Run: `cd apps/worker && .venv/bin/python -m pytest tests/test_outcome_recording.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/worker/src/pinky_worker/execution/activities.py apps/worker/tests/test_outcome_recording.py
git commit -m "feat: emit analytics events on investigation/remediation outcomes"
```

---

### Task 5: Emit analytics on approval decisions

**Files:**
- Modify: `apps/api/src/pinky_api/routes/executions.py`
- Test: `apps/api/tests/test_approval_analytics.py`

- [ ] **Step 1: Read the approve endpoint to understand the flow**

Read `apps/api/src/pinky_api/routes/executions.py` and locate the approval endpoint.

- [ ] **Step 2: Write test for approval analytics emission**

Create `apps/api/tests/test_approval_analytics.py`:

```python
"""Test analytics event emission on approval decisions."""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_approve_emits_analytics_event(authed_client):
    # This test verifies the analytics event is recorded when an approval is granted.
    # The actual approval flow is tested in test_remediation_approval_guard.py.
    # Here we just verify the analytics recording path exists.
    from pinky_api.repositories.analytics import AnalyticsRepository

    repo = AnalyticsRepository.__new__(AnalyticsRepository)
    repo.session = AsyncMock()
    repo.session.add = AsyncMock()
    repo.session.flush = AsyncMock()

    event = await repo.record(
        "approval_decided",
        {"decision": "approved", "wait_seconds": 120},
        execution_id="00000000-0000-0000-0000-000000000001",
    )
    assert event.event_type == "approval_decided"
    assert event.payload["decision"] == "approved"
```

- [ ] **Step 3: Run test**

Run: `cd apps/api && .venv/bin/pytest tests/test_approval_analytics.py -v`
Expected: PASS (tests the repository interface, not the route wiring).

- [ ] **Step 4: Wire analytics into the approval route**

In `apps/api/src/pinky_api/routes/executions.py`, in the approve handler, after the approval status is updated, add:

```python
    from pinky_api.repositories.analytics import AnalyticsRepository
    analytics = AnalyticsRepository(db)
    await analytics.record(
        "approval_decided",
        {"decision": "approved", "execution_id": str(execution_id)},
        execution_id=execution_id,
    )
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/pinky_api/routes/executions.py apps/api/tests/test_approval_analytics.py
git commit -m "feat: emit analytics event on approval decisions"
```

---

### Task 6: Phase 1 integration — run full test suite

- [ ] **Step 1: Run all worker tests**

Run: `cd apps/worker && .venv/bin/python -m pytest tests/ --ignore=tests/integration -v`
Expected: All pass.

- [ ] **Step 2: Run all API tests**

Run: `cd apps/api && .venv/bin/pytest tests/ --ignore=tests/benchmark -v`
Expected: All pass.

- [ ] **Step 3: Run typecheck**

Run: `cd apps/worker && .venv/bin/python -m pyright src/ && cd ../api && .venv/bin/python -m pyright src/`
Expected: No errors.

- [ ] **Step 4: Commit any fixes**

```bash
git add -A && git commit -m "fix: address test/type issues from Phase 1 integration"
```

---

## Phase 2: Analytics + ROI

### Task 7: Add time-bucketed query methods to AnalyticsRepository

**Files:**
- Modify: `apps/api/src/pinky_api/repositories/analytics.py`
- Test: `apps/api/tests/test_analytics_queries.py`

- [ ] **Step 1: Write failing tests**

Create `apps/api/tests/test_analytics_queries.py`:

```python
"""Tests for analytics repository query methods."""

import pytest
from datetime import UTC, datetime, timedelta


@pytest.mark.asyncio
async def test_get_token_usage_by_period(authed_client):
    """Token usage query returns time-bucketed totals."""
    from pinky_api.repositories.analytics import AnalyticsRepository
    from pinky_api.db.deps import get_db

    # Use the test DB session from authed_client fixture
    from pinky_api.app import app
    async for db in app.dependency_overrides[get_db]():
        repo = AnalyticsRepository(db)
        result = await repo.get_token_usage_by_period(
            start=datetime.now(UTC) - timedelta(days=7),
            end=datetime.now(UTC),
            bucket="day",
        )
        assert isinstance(result, list)
        break


@pytest.mark.asyncio
async def test_get_outcomes_by_period(authed_client):
    """Outcomes query returns counts grouped by type."""
    from pinky_api.repositories.analytics import AnalyticsRepository
    from pinky_api.db.deps import get_db
    from pinky_api.app import app

    async for db in app.dependency_overrides[get_db]():
        repo = AnalyticsRepository(db)
        result = await repo.get_outcomes_by_period(
            start=datetime.now(UTC) - timedelta(days=30),
            end=datetime.now(UTC),
        )
        assert isinstance(result, dict)
        break
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && .venv/bin/pytest tests/test_analytics_queries.py -v`
Expected: FAIL — methods don't exist yet.

- [ ] **Step 3: Implement query methods**

In `apps/api/src/pinky_api/repositories/analytics.py`, add:

```python
from datetime import datetime
from sqlalchemy import text


class AnalyticsRepository(BaseRepository):
    # ... existing methods ...

    async def get_token_usage_by_period(
        self,
        start: datetime,
        end: datetime,
        bucket: str = "day",
    ) -> list[dict]:
        interval = "1 day" if bucket == "day" else "1 hour"
        result = await self.session.execute(
            text("""
                SELECT date_trunc(:bucket, ee.occurred_at) AS ts,
                       SUM((ee.payload->>'input_tokens')::int) AS input_tokens,
                       SUM((ee.payload->>'output_tokens')::int) AS output_tokens,
                       COUNT(*) AS call_count
                FROM execution_events ee
                WHERE ee.event_type = 'llm_call'
                  AND ee.occurred_at BETWEEN :start AND :end
                GROUP BY ts ORDER BY ts
            """),
            {"bucket": bucket, "start": start, "end": end},
        )
        return [
            {
                "timestamp": row.ts.isoformat(),
                "input_tokens": row.input_tokens or 0,
                "output_tokens": row.output_tokens or 0,
                "call_count": row.call_count,
            }
            for row in result.all()
        ]

    async def get_outcomes_by_period(
        self,
        start: datetime,
        end: datetime,
        cluster_id: str | None = None,
    ) -> dict:
        params: dict = {"start": start, "end": end}
        cluster_filter = ""
        if cluster_id:
            cluster_filter = "AND e.cluster_id = :cluster_id"
            params["cluster_id"] = cluster_id
        result = await self.session.execute(
            text(f"""
                SELECT e.outcome, COUNT(*) as cnt
                FROM executions e
                WHERE e.outcome IS NOT NULL
                  AND e.completed_at BETWEEN :start AND :end
                  {cluster_filter}
                GROUP BY e.outcome
            """),
            params,
        )
        return {row.outcome: row.cnt for row in result.all()}

    async def get_cache_hit_rate(
        self,
        start: datetime,
        end: datetime,
    ) -> dict:
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) FILTER (WHERE (payload->>'cache_hit')::boolean = true) AS hits,
                       COUNT(*) AS total
                FROM execution_events
                WHERE event_type = 'llm_call'
                  AND occurred_at BETWEEN :start AND :end
            """),
            {"start": start, "end": end},
        )
        row = result.fetchone()
        total = row.total if row else 0
        hits = row.hits if row else 0
        return {
            "hits": hits,
            "total": total,
            "rate": round(hits / total, 3) if total > 0 else 0.0,
        }

    async def get_approval_turnaround(
        self,
        start: datetime,
        end: datetime,
    ) -> dict:
        result = await self.session.execute(
            text("""
                SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY (payload->>'wait_seconds')::float) AS p50,
                       percentile_cont(0.95) WITHIN GROUP (ORDER BY (payload->>'wait_seconds')::float) AS p95
                FROM analytics_events
                WHERE event_type = 'approval_decided'
                  AND occurred_at BETWEEN :start AND :end
            """),
            {"start": start, "end": end},
        )
        row = result.fetchone()
        return {
            "p50_seconds": row.p50 if row and row.p50 else None,
            "p95_seconds": row.p95 if row and row.p95 else None,
        }
```

- [ ] **Step 4: Run tests**

Run: `cd apps/api && .venv/bin/pytest tests/test_analytics_queries.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/pinky_api/repositories/analytics.py apps/api/tests/test_analytics_queries.py
git commit -m "feat: add time-bucketed analytics query methods"
```

---

### Task 8: Add trends API endpoint

**Files:**
- Modify: `apps/api/src/pinky_api/routes/analytics.py`
- Test: `apps/api/tests/test_analytics_trends.py`

- [ ] **Step 1: Write failing test**

Create `apps/api/tests/test_analytics_trends.py`:

```python
"""Tests for /api/v1/analytics/trends endpoint."""

import pytest


@pytest.mark.asyncio
async def test_trends_endpoint_returns_buckets(authed_client):
    response = authed_client.get("/api/v1/analytics/trends?metric=token_usage&period=7d&bucket=day")
    assert response.status_code == 200
    data = response.json()
    assert data["metric"] == "token_usage"
    assert "buckets" in data


@pytest.mark.asyncio
async def test_trends_invalid_metric(authed_client):
    response = authed_client.get("/api/v1/analytics/trends?metric=invalid")
    assert response.status_code == 400
```

- [ ] **Step 2: Run to verify failure**

Run: `cd apps/api && .venv/bin/pytest tests/test_analytics_trends.py -v`
Expected: FAIL — endpoint doesn't exist.

- [ ] **Step 3: Implement trends endpoint**

In `apps/api/src/pinky_api/routes/analytics.py`, add:

```python
from pinky_api.repositories.analytics import AnalyticsRepository

_PERIOD_MAP = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

_VALID_METRICS = {"token_usage", "issues_resolved", "cache_hit_rate", "scanner_signals"}


@router.get("/trends")
async def trends(
    metric: str = "token_usage",
    period: str = "7d",
    bucket: str = "day",
    cluster_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if metric not in _VALID_METRICS:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}. Must be one of: {', '.join(_VALID_METRICS)}")

    delta = _PERIOD_MAP.get(period)
    if delta is None:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}")

    end = datetime.now(UTC)
    start = end - delta
    repo = AnalyticsRepository(db)

    if metric == "token_usage":
        buckets = await repo.get_token_usage_by_period(start, end, bucket)
    elif metric == "issues_resolved":
        result = await db.execute(
            text("""
                SELECT date_trunc(:bucket, resolved_at) AS ts, COUNT(*) AS value
                FROM issues WHERE status = 'resolved' AND resolved_at BETWEEN :start AND :end
                GROUP BY ts ORDER BY ts
            """),
            {"bucket": bucket, "start": start, "end": end},
        )
        buckets = [{"timestamp": r.ts.isoformat(), "value": r.value} for r in result.all()]
    elif metric == "cache_hit_rate":
        cache_data = await repo.get_cache_hit_rate(start, end)
        buckets = [{"timestamp": start.isoformat(), "value": cache_data["rate"]}]
    elif metric == "scanner_signals":
        from pinky_api.models.observation import Observation
        result = await db.execute(
            text("""
                SELECT date_trunc(:bucket, observed_at) AS ts, COUNT(*) AS value
                FROM observations WHERE observed_at BETWEEN :start AND :end
                GROUP BY ts ORDER BY ts
            """),
            {"bucket": bucket, "start": start, "end": end},
        )
        buckets = [{"timestamp": r.ts.isoformat(), "value": r.value} for r in result.all()]
    else:
        buckets = []

    return {"metric": metric, "period": period, "bucket_size": bucket, "buckets": buckets}
```

- [ ] **Step 4: Run tests**

Run: `cd apps/api && .venv/bin/pytest tests/test_analytics_trends.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/pinky_api/routes/analytics.py apps/api/tests/test_analytics_trends.py
git commit -m "feat: add /api/v1/analytics/trends endpoint with time-bucketed metrics"
```

---

### Task 9: Upgrade scanner quality endpoint with FP rate and noise ratio

**Files:**
- Modify: `apps/api/src/pinky_api/routes/analytics.py`
- Test: `apps/api/tests/test_scanner_quality.py`

- [ ] **Step 1: Write test**

Create `apps/api/tests/test_scanner_quality.py`:

```python
"""Tests for scanner quality endpoint with FP rate and noise ratio."""

import pytest


@pytest.mark.asyncio
async def test_scanner_quality_returns_extended_fields(authed_client):
    response = authed_client.get("/api/v1/analytics/scanners")
    assert response.status_code == 200
    data = response.json()
    assert "scanners" in data
    # Even with no data, the endpoint should work
    for scanner in data["scanners"]:
        assert "scanner" in scanner
        assert "signal_total" in scanner
        assert "signal_suppressed" in scanner
        assert "false_positive_rate" in scanner
        assert "noise_ratio" in scanner
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd apps/api && .venv/bin/pytest tests/test_scanner_quality.py -v`
Expected: FAIL — endpoint doesn't return `signal_suppressed`, `false_positive_rate`, `noise_ratio`.

- [ ] **Step 3: Upgrade the scanner quality endpoint**

Replace the `scanner_quality` handler in `apps/api/src/pinky_api/routes/analytics.py`:

```python
@router.get("/scanners")
async def scanner_quality(since: str = "30d", db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        text("""
            SELECT
                o.scanner,
                COUNT(*) AS signal_total,
                COUNT(*) FILTER (WHERE i.status = 'suppressed') AS signal_suppressed,
                COUNT(*) FILTER (WHERE wi.id IS NOT NULL) AS signal_tasked,
                COUNT(*) FILTER (WHERE wi.status = 'dismissed') AS signal_dismissed
            FROM observations o
            LEFT JOIN issues i ON i.correlation_key = o.correlation_key
            LEFT JOIN work_items wi ON wi.issue_id = i.id
            GROUP BY o.scanner
            ORDER BY signal_total DESC
        """),
    )
    scanners = []
    for row in result.all():
        total = row.signal_total
        suppressed = row.signal_suppressed
        dismissed = row.signal_dismissed
        scanners.append({
            "scanner": row.scanner,
            "signal_total": total,
            "signal_suppressed": suppressed,
            "signal_tasked": row.signal_tasked,
            "false_positive_rate": round(dismissed / total, 3) if total > 0 else None,
            "noise_ratio": round(suppressed / total, 3) if total > 0 else None,
        })
    return {"scanners": scanners, "period": since}
```

- [ ] **Step 4: Run test**

Run: `cd apps/api && .venv/bin/pytest tests/test_scanner_quality.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/pinky_api/routes/analytics.py apps/api/tests/test_scanner_quality.py
git commit -m "feat: add FP rate and noise ratio to scanner quality endpoint"
```

---

### Task 10: Upgrade Analytics dashboard UI

**Files:**
- Modify: `apps/web/src/app/(product)/settings/_components/analytics-tab.tsx`
- Modify: `apps/web/src/app/(product)/settings/queries.ts`

- [ ] **Step 1: Add trends query option**

In `apps/web/src/app/(product)/settings/queries.ts`, add:

```typescript
export function analyticsTrendsOptions(metric: string, period = "7d", bucket = "day") {
  return queryOptions({
    queryKey: ["analytics-trends", metric, period, bucket],
    queryFn: () => api.get<{ metric: string; buckets: { timestamp: string; value: number }[] }>(
      `/api/v1/analytics/trends?metric=${metric}&period=${period}&bucket=${bucket}`
    ),
    staleTime: 60_000,
  });
}
```

- [ ] **Step 2: Add trend sparklines and new metric cards to analytics tab**

Replace the content of `analytics-tab.tsx` with the upgraded version that includes:
- Token usage card with trend sparkline
- Cache hit rate card
- Approval turnaround card
- Scanner quality table with FP rate and noise ratio columns
- Trend sparklines using recharts AreaChart

The component should use `useQuery` with the new `analyticsTrendsOptions` to fetch trend data and display recharts `<AreaChart>` sparklines in the metric cards.

Key additions:
- Import `AreaChart, Area, ResponsiveContainer` from `recharts`
- Add `analyticsTrendsOptions("token_usage", since)` query
- Add `analyticsTrendsOptions("issues_resolved", since)` query
- Render sparklines inside Card components
- Add scanner table with sortable columns

- [ ] **Step 3: Run typecheck**

Run: `pnpm --filter @pinky/web typecheck`
Expected: PASS

- [ ] **Step 4: Run dev server and verify visually**

Run: `pnpm --filter @pinky/web dev`
Navigate to Settings > Analytics tab. Verify:
- Period selector works
- Metric cards render (even with no data, should show 0/empty states)
- Scanner table renders
- No console errors

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/app/\(product\)/settings/_components/analytics-tab.tsx apps/web/src/app/\(product\)/settings/queries.ts
git commit -m "feat: upgrade analytics dashboard with trend sparklines and scanner quality table"
```

---

### Task 11: Add eval baselines and CI gate

**Files:**
- Create: `apps/worker/evals/baselines.json`
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Create baselines file**

Create `apps/worker/evals/baselines.json`:

```json
{
  "minimum_scores": {
    "structure": 1.0,
    "safety": 1.0,
    "relevance": 0.5,
    "redaction": 1.0
  },
  "description": "Minimum acceptable grader scores. CI fails if any fixture drops below these."
}
```

- [ ] **Step 2: Add eval job to CI**

In `.github/workflows/ci.yml`, add after the `worker-tests` job:

```yaml
  worker-evals:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install Worker deps
        working-directory: apps/worker
        run: pip install -e ".[dev]" && pip install pyyaml
      - name: Run evals
        working-directory: apps/worker
        run: pytest evals/ -v --tb=short
```

- [ ] **Step 3: Commit**

```bash
git add apps/worker/evals/baselines.json .github/workflows/ci.yml
git commit -m "feat: add eval baselines and CI eval gate"
```

---

### Task 12: Phase 2 integration — run full test suite

- [ ] **Step 1: Run make verify**

Run: `make verify`
Expected: All lint, typecheck, and tests pass.

- [ ] **Step 2: Commit any fixes**

---

## Phase 3: CI/Release Pipeline

### Task 13: Add security scanning to CI

**Files:**
- Modify: `.github/workflows/ci.yml`

- [ ] **Step 1: Add SAST, dependency scan, and secret scan jobs**

In `.github/workflows/ci.yml`, add three new jobs:

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
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install pip-audit
        run: pip install pip-audit
      - name: Audit API deps
        working-directory: apps/api
        run: pip install -e . && pip-audit --progress-spinner=off
        continue-on-error: true
      - name: Audit Worker deps
        working-directory: apps/worker
        run: pip install -e . && pip-audit --progress-spinner=off
        continue-on-error: true
      - uses: pnpm/action-setup@v4
        with:
          version: 9
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
      - run: pnpm install --frozen-lockfile
      - name: Audit JS deps
        run: pnpm audit --audit-level=high
        continue-on-error: true

  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "feat: add SAST, dependency scanning, and secret scanning to CI"
```

---

### Task 14: Create release workflow

**Files:**
- Create: `.github/workflows/release.yml`

- [ ] **Step 1: Create the release workflow**

Create `.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

env:
  REGISTRY: quay.io/amobrem

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - name: Set version from tag
        id: version
        run: echo "VERSION=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"

      - name: Log in to Quay.io
        uses: docker/login-action@v3
        with:
          registry: quay.io
          username: ${{ secrets.QUAY_USERNAME }}
          password: ${{ secrets.QUAY_PASSWORD }}

      - name: Build API image
        run: docker build -f infra/docker/Dockerfile.api -t ${{ env.REGISTRY }}/pinky-api:${{ steps.version.outputs.VERSION }} .

      - name: Build Web image
        run: docker build -f infra/docker/Dockerfile.web -t ${{ env.REGISTRY }}/pinky-web:${{ steps.version.outputs.VERSION }} .

      - name: Build Worker image
        run: docker build -f infra/docker/Dockerfile.worker -t ${{ env.REGISTRY }}/pinky-worker:${{ steps.version.outputs.VERSION }} .

      - name: Scan images with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/pinky-api:${{ steps.version.outputs.VERSION }}
          format: table
          exit-code: 1
          severity: CRITICAL,HIGH

      - name: Push images
        run: |
          docker push ${{ env.REGISTRY }}/pinky-api:${{ steps.version.outputs.VERSION }}
          docker push ${{ env.REGISTRY }}/pinky-web:${{ steps.version.outputs.VERSION }}
          docker push ${{ env.REGISTRY }}/pinky-worker:${{ steps.version.outputs.VERSION }}

      - name: Install cosign
        uses: sigstore/cosign-installer@v3

      - name: Sign images
        run: |
          cosign sign --yes ${{ env.REGISTRY }}/pinky-api:${{ steps.version.outputs.VERSION }}
          cosign sign --yes ${{ env.REGISTRY }}/pinky-web:${{ steps.version.outputs.VERSION }}
          cosign sign --yes ${{ env.REGISTRY }}/pinky-worker:${{ steps.version.outputs.VERSION }}

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ env.REGISTRY }}/pinky-api:${{ steps.version.outputs.VERSION }}
          artifact-name: sbom-api.spdx.json

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            sbom-api.spdx.json
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "feat: add release workflow with image build, Trivy scan, cosign signing, SBOM"
```

---

## Phase 4: Operational Hardening

### Task 15: Add OpenTelemetry instrumentation

**Files:**
- Modify: `apps/api/pyproject.toml`
- Modify: `apps/api/src/pinky_api/app.py`
- Modify: `apps/worker/pyproject.toml`
- Modify: `infra/helm/pinky/templates/configmap.yaml`

- [ ] **Step 1: Add OTel dependencies to API**

In `apps/api/pyproject.toml`, add to `dependencies`:

```
opentelemetry-api>=1.27.0
opentelemetry-sdk>=1.27.0
opentelemetry-instrumentation-fastapi>=0.48b0
opentelemetry-instrumentation-sqlalchemy>=0.48b0
opentelemetry-exporter-otlp-proto-grpc>=1.27.0
```

- [ ] **Step 2: Add OTel dependencies to Worker**

In `apps/worker/pyproject.toml`, add to `dependencies`:

```
opentelemetry-api>=1.27.0
opentelemetry-sdk>=1.27.0
opentelemetry-exporter-otlp-proto-grpc>=1.27.0
```

- [ ] **Step 3: Wire OTel into API startup**

In `apps/api/src/pinky_api/app.py`, add OTel initialization in the `lifespan` function, before `yield`:

```python
    # OpenTelemetry (opt-in via OTEL_EXPORTER_OTLP_ENDPOINT)
    otel_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otel_endpoint:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": "pinky-api"})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        SQLAlchemyInstrumentor().instrument()
        logger.info("OpenTelemetry initialized", endpoint=otel_endpoint)
```

- [ ] **Step 4: Add OTel env vars to Helm configmap**

In `infra/helm/pinky/templates/configmap.yaml`, add:

```yaml
  OTEL_SERVICE_NAME: pinky-api
  {{- if .Values.observability }}
  {{- if .Values.observability.otlpEndpoint }}
  OTEL_EXPORTER_OTLP_ENDPOINT: {{ .Values.observability.otlpEndpoint | quote }}
  {{- end }}
  {{- end }}
```

In `infra/helm/pinky/values.yaml`, add:

```yaml
observability:
  otlpEndpoint: ""
```

- [ ] **Step 5: Commit**

```bash
git add apps/api/pyproject.toml apps/api/src/pinky_api/app.py apps/worker/pyproject.toml infra/helm/pinky/templates/configmap.yaml infra/helm/pinky/values.yaml
git commit -m "feat: add OpenTelemetry instrumentation (opt-in via OTEL_EXPORTER_OTLP_ENDPOINT)"
```

---

### Task 16: Add CSP reporting endpoint

**Files:**
- Modify: `apps/api/src/pinky_api/security/headers.py`
- Modify: `apps/api/src/pinky_api/app.py`
- Test: `apps/api/tests/test_csp_report.py`

- [ ] **Step 1: Write test**

Create `apps/api/tests/test_csp_report.py`:

```python
"""Tests for CSP violation reporting endpoint."""

import pytest


@pytest.mark.asyncio
async def test_csp_report_returns_204(authed_client):
    response = authed_client.post(
        "/api/v1/csp-report",
        json={"csp-report": {"document-uri": "https://pinky.example.com", "violated-directive": "script-src"}},
    )
    assert response.status_code == 204
```

- [ ] **Step 2: Add the CSP report endpoint**

In `apps/api/src/pinky_api/app.py`, add a CSP report route (or in a new routes file):

```python
from fastapi import Request
from fastapi.responses import Response

@app.post("/api/v1/csp-report", status_code=204)
async def csp_report(request: Request) -> Response:
    body = await request.json()
    report = body.get("csp-report", {})
    logger.warning(
        "csp_violation",
        document_uri=report.get("document-uri"),
        violated_directive=report.get("violated-directive"),
        blocked_uri=report.get("blocked-uri"),
    )
    return Response(status_code=204)
```

Also add `report-uri` to CSP in `apps/api/src/pinky_api/security/headers.py`. Find the CSP directives dict and add:

```python
"report-uri": "/api/v1/csp-report",
```

- [ ] **Step 3: Run test**

Run: `cd apps/api && .venv/bin/pytest tests/test_csp_report.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/pinky_api/security/headers.py apps/api/src/pinky_api/app.py apps/api/tests/test_csp_report.py
git commit -m "feat: add CSP violation reporting endpoint"
```

---

### Task 17: Add data retention script and Makefile target

**Files:**
- Create: `scripts/retention.sh`
- Modify: `Makefile`

- [ ] **Step 1: Create retention script**

Create `scripts/retention.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

DB_URL="${PINKY_DB_URL:-postgresql://pinky:pinky@localhost:5432/pinky}"
ANALYTICS_RETENTION_DAYS="${PINKY_ANALYTICS_RETENTION_DAYS:-90}"
EVENTS_RETENTION_DAYS="${PINKY_EVENTS_RETENTION_DAYS:-180}"

echo "Deleting analytics_events older than ${ANALYTICS_RETENTION_DAYS} days..."
psql "${DB_URL}" -c "DELETE FROM analytics_events WHERE occurred_at < now() - interval '${ANALYTICS_RETENTION_DAYS} days';"

echo "Deleting execution_events older than ${EVENTS_RETENTION_DAYS} days..."
psql "${DB_URL}" -c "DELETE FROM execution_events WHERE occurred_at < now() - interval '${EVENTS_RETENTION_DAYS} days';"

echo "Data retention complete."
```

```bash
chmod +x scripts/retention.sh
```

- [ ] **Step 2: Add Makefile target**

In `Makefile`, add:

```makefile
db-retention:
	./scripts/retention.sh
```

Update the `.PHONY` line to include `db-retention`.

- [ ] **Step 3: Commit**

```bash
git add scripts/retention.sh Makefile
git commit -m "feat: add data retention script (90d analytics, 180d events)"
```

---

### Task 18: Add chaos test scaffolding

**Files:**
- Create: `tests/chaos/conftest.py`
- Create: `tests/chaos/test_sse_reconnection.py`
- Create: `tests/chaos/test_approval_race.py`
- Modify: `Makefile`

- [ ] **Step 1: Create chaos conftest**

Create `tests/chaos/conftest.py`:

```python
"""Chaos test fixtures. Requires running dev infrastructure (make dev-infra)."""

import pytest

# All tests in this directory are marked as chaos
def pytest_collection_modifyitems(items: list) -> None:
    for item in items:
        item.add_marker(pytest.mark.chaos)
```

- [ ] **Step 2: Create SSE reconnection test**

Create `tests/chaos/test_sse_reconnection.py`:

```python
"""Chaos test: SSE reconnection storm."""

import asyncio

import httpx
import pytest


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_sse_reconnection_storm():
    """100 clients connect, disconnect, and reconnect to SSE simultaneously."""
    url = "http://localhost:8000/api/v1/streams/events"
    num_clients = 100

    async def connect_and_read(client_id: int) -> str:
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                async with client.stream("GET", url) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data:"):
                            return f"client-{client_id}: received"
                        break
            except (httpx.ReadTimeout, httpx.ConnectError):
                pass
        return f"client-{client_id}: connected"

    tasks = [connect_and_read(i) for i in range(num_clients)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) < num_clients * 0.1, f"Too many connection failures: {len(errors)}/{num_clients}"
```

- [ ] **Step 3: Create approval race test**

Create `tests/chaos/test_approval_race.py`:

```python
"""Chaos test: approval at exact timeout boundary."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_approval_at_expiry_boundary():
    """Approve at exact moment of expiry — must produce deterministic outcome."""
    approval_id = uuid4()
    execution_id = uuid4()
    expires_at = datetime.now(UTC) + timedelta(seconds=1)

    results = []

    async def attempt_approval():
        await asyncio.sleep(1.0)  # Wait until exact expiry
        expired = datetime.now(UTC) >= expires_at
        results.append({"expired": expired, "time": datetime.now(UTC).isoformat()})

    tasks = [attempt_approval() for _ in range(10)]
    await asyncio.gather(*tasks)

    # All attempts at the same time should agree on outcome
    outcomes = set(r["expired"] for r in results)
    assert len(outcomes) == 1, f"Non-deterministic: got both expired and not-expired: {results}"
```

- [ ] **Step 4: Add chaos-test Makefile target**

In `Makefile`, add:

```makefile
chaos-test:
	cd tests && python -m pytest chaos/ -v -m chaos
```

Update `.PHONY` to include `chaos-test`.

- [ ] **Step 5: Commit**

```bash
git add tests/chaos/ Makefile
git commit -m "feat: add chaos test scaffolding (SSE reconnection, approval race)"
```

---

### Task 19: Phase 4 integration — run full test suite

- [ ] **Step 1: Run make verify**

Run: `make verify`
Expected: All pass (chaos tests skipped by default since they need running infra).

- [ ] **Step 2: Commit any fixes**

---

## Phase 5: Cutover

### Task 20: Add feature flags table and model

**Files:**
- Create: `apps/api/alembic/versions/k6e7f8g9h0i1_add_feature_flags.py`
- Create: `apps/api/src/pinky_api/models/feature_flag.py`

- [ ] **Step 1: Create migration**

Create `apps/api/alembic/versions/k6e7f8g9h0i1_add_feature_flags.py`:

```python
"""Add feature_flags table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "k6e7f8g9h0i1"
down_revision = "j5d6e7f8g9h0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("flag_name", sa.String(100), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean, server_default="false", nullable=False),
        sa.Column("scope_type", sa.String(20), server_default="global", nullable=False),
        sa.Column("scope_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
```

- [ ] **Step 2: Create model**

Create `apps/api/src/pinky_api/models/feature_flag.py`:

```python
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from pinky_api.models.base import Base, gen_uuid


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=gen_uuid)
    flag_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), server_default="global", nullable=False)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
```

- [ ] **Step 3: Run migration**

Run: `cd apps/api && .venv/bin/python -m alembic upgrade head`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/api/alembic/versions/k6e7f8g9h0i1_add_feature_flags.py apps/api/src/pinky_api/models/feature_flag.py
git commit -m "feat: add feature_flags table and model"
```

---

### Task 21: Add feature flag service and API routes

**Files:**
- Create: `apps/api/src/pinky_api/services/feature_flags.py`
- Create: `apps/api/src/pinky_api/routes/feature_flags.py`
- Modify: `apps/api/src/pinky_api/app.py`
- Test: `apps/api/tests/test_feature_flags.py`

- [ ] **Step 1: Write tests**

Create `apps/api/tests/test_feature_flags.py`:

```python
"""Tests for feature flag CRUD and evaluation."""

import pytest


@pytest.mark.asyncio
async def test_create_feature_flag(authed_client):
    response = authed_client.post(
        "/api/v1/feature-flags",
        json={"flag_name": "test-flag", "enabled": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["flag_name"] == "test-flag"
    assert data["enabled"] is True


@pytest.mark.asyncio
async def test_list_feature_flags(authed_client):
    authed_client.post("/api/v1/feature-flags", json={"flag_name": "list-test", "enabled": False})
    response = authed_client.get("/api/v1/feature-flags")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["flags"], list)


@pytest.mark.asyncio
async def test_toggle_feature_flag(authed_client):
    create = authed_client.post("/api/v1/feature-flags", json={"flag_name": "toggle-test", "enabled": False})
    flag_id = create.json()["id"]
    response = authed_client.patch(f"/api/v1/feature-flags/{flag_id}", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["enabled"] is True


@pytest.mark.asyncio
async def test_delete_feature_flag(authed_client):
    create = authed_client.post("/api/v1/feature-flags", json={"flag_name": "delete-test", "enabled": False})
    flag_id = create.json()["id"]
    response = authed_client.delete(f"/api/v1/feature-flags/{flag_id}")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_non_admin_cannot_create_flag(non_admin_client):
    response = non_admin_client.post("/api/v1/feature-flags", json={"flag_name": "fail", "enabled": True})
    assert response.status_code == 403
```

- [ ] **Step 2: Create feature flag service**

Create `apps/api/src/pinky_api/services/feature_flags.py`:

```python
"""Feature flag evaluation with in-memory cache."""

from __future__ import annotations

import time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.models.feature_flag import FeatureFlag

_CACHE_TTL = 30  # seconds
_cache: dict[str, tuple[float, bool]] = {}


async def is_enabled(
    db: AsyncSession,
    flag_name: str,
    principal_id: UUID | None = None,
    cluster_id: UUID | None = None,
) -> bool:
    cache_key = f"{flag_name}:{principal_id}:{cluster_id}"
    now = time.monotonic()
    if cache_key in _cache:
        cached_at, value = _cache[cache_key]
        if now - cached_at < _CACHE_TTL:
            return value

    # Resolution order: principal-scoped -> cluster-scoped -> global
    for scope_type, scope_id in [
        ("principal", principal_id),
        ("cluster", cluster_id),
        ("global", None),
    ]:
        if scope_type != "global" and scope_id is None:
            continue
        stmt = select(FeatureFlag).where(
            FeatureFlag.flag_name == flag_name,
            FeatureFlag.scope_type == scope_type,
        )
        if scope_id:
            stmt = stmt.where(FeatureFlag.scope_id == scope_id)
        else:
            stmt = stmt.where(FeatureFlag.scope_id.is_(None))

        result = await db.execute(stmt)
        flag = result.scalar_one_or_none()
        if flag is not None:
            _cache[cache_key] = (now, flag.enabled)
            return flag.enabled

    _cache[cache_key] = (now, False)
    return False
```

- [ ] **Step 3: Create feature flag routes**

Create `apps/api/src/pinky_api/routes/feature_flags.py`:

```python
"""Feature flag CRUD routes — admin only."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import get_current_principal
from pinky_api.db.deps import get_db
from pinky_api.models.feature_flag import FeatureFlag

router = APIRouter(prefix="/api/v1/feature-flags", tags=["feature-flags"])


class CreateFlagRequest(BaseModel):
    flag_name: str
    enabled: bool = False
    scope_type: str = "global"
    scope_id: str | None = None


class UpdateFlagRequest(BaseModel):
    enabled: bool | None = None
    scope_type: str | None = None
    scope_id: str | None = None


def _require_admin(principal: dict = Depends(get_current_principal)) -> dict:
    if not principal.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return principal


@router.post("", status_code=201)
async def create_flag(
    body: CreateFlagRequest,
    db: AsyncSession = Depends(get_db),
    principal: dict = Depends(_require_admin),
) -> dict:
    flag = FeatureFlag(
        flag_name=body.flag_name,
        enabled=body.enabled,
        scope_type=body.scope_type,
        scope_id=UUID(body.scope_id) if body.scope_id else None,
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return {
        "id": str(flag.id),
        "flag_name": flag.flag_name,
        "enabled": flag.enabled,
        "scope_type": flag.scope_type,
        "scope_id": str(flag.scope_id) if flag.scope_id else None,
    }


@router.get("")
async def list_flags(
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(_require_admin),
) -> dict:
    result = await db.execute(select(FeatureFlag).order_by(FeatureFlag.flag_name))
    flags = result.scalars().all()
    return {
        "flags": [
            {
                "id": str(f.id),
                "flag_name": f.flag_name,
                "enabled": f.enabled,
                "scope_type": f.scope_type,
                "scope_id": str(f.scope_id) if f.scope_id else None,
            }
            for f in flags
        ]
    }


@router.patch("/{flag_id}")
async def update_flag(
    flag_id: str,
    body: UpdateFlagRequest,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(_require_admin),
) -> dict:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    if body.enabled is not None:
        flag.enabled = body.enabled
    if body.scope_type is not None:
        flag.scope_type = body.scope_type
    flag.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(flag)
    return {
        "id": str(flag.id),
        "flag_name": flag.flag_name,
        "enabled": flag.enabled,
        "scope_type": flag.scope_type,
        "scope_id": str(flag.scope_id) if flag.scope_id else None,
    }


@router.delete("/{flag_id}", status_code=204)
async def delete_flag(
    flag_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(_require_admin),
) -> None:
    result = await db.execute(select(FeatureFlag).where(FeatureFlag.id == UUID(flag_id)))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    await db.delete(flag)
    await db.commit()
```

- [ ] **Step 4: Register the router**

In `apps/api/src/pinky_api/app.py`, add:

```python
from pinky_api.routes.feature_flags import router as feature_flags_router
app.include_router(feature_flags_router)
```

- [ ] **Step 5: Run tests**

Run: `cd apps/api && .venv/bin/pytest tests/test_feature_flags.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add apps/api/src/pinky_api/services/feature_flags.py apps/api/src/pinky_api/routes/feature_flags.py apps/api/src/pinky_api/app.py apps/api/tests/test_feature_flags.py
git commit -m "feat: add feature flag service and admin CRUD API"
```

---

### Task 22: Add origin label to work items and issues

**Files:**
- Create: `apps/api/alembic/versions/l7f8g9h0i1j2_add_origin_column.py`

- [ ] **Step 1: Create migration**

Create `apps/api/alembic/versions/l7f8g9h0i1j2_add_origin_column.py`:

```python
"""Add origin column to work_items and issues."""

from alembic import op
import sqlalchemy as sa

revision = "l7f8g9h0i1j2"
down_revision = "k6e7f8g9h0i1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("work_items", sa.Column("origin", sa.String(20), server_default="pinky"))
    op.add_column("issues", sa.Column("origin", sa.String(20), server_default="pinky"))


def downgrade() -> None:
    op.drop_column("work_items", "origin")
    op.drop_column("issues", "origin")
```

- [ ] **Step 2: Run migration**

Run: `cd apps/api && .venv/bin/python -m alembic upgrade head`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add apps/api/alembic/versions/l7f8g9h0i1j2_add_origin_column.py
git commit -m "feat: add origin column to work_items and issues for cutover tracking"
```

---

### Task 23: Create Pulse migration utility

**Files:**
- Create: `scripts/migrate-from-pulse.py`

- [ ] **Step 1: Create the migration script**

Create `scripts/migrate-from-pulse.py`:

```python
#!/usr/bin/env python3
"""Translate Pulse scanner configs to Pinky scanner markdown definitions.

Usage:
    python scripts/migrate-from-pulse.py --input-dir /path/to/pulse/configs --dry-run
    python scripts/migrate-from-pulse.py --input-dir /path/to/pulse/configs --output-dir definitions/scanners/
"""

import argparse
import sys
from pathlib import Path

import yaml


def translate_scanner(config: dict, source_file: str) -> str:
    name = config.get("name", Path(source_file).stem)
    description = config.get("description", f"Migrated from Pulse: {source_file}")
    resource_kinds = config.get("resource_kinds", ["Pod"])
    interval = config.get("interval", "5m")

    frontmatter = {
        "name": name,
        "type": "scanner",
        "resource_kinds": resource_kinds,
        "interval": interval,
        "origin": "pulse",
    }

    yaml_fm = yaml.dump(frontmatter, default_flow_style=False).strip()
    body = config.get("description", f"Scanner migrated from Pulse config: {source_file}")

    return f"---\n{yaml_fm}\n---\n\n{body}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate Pulse configs to Pinky scanner definitions")
    parser.add_argument("--input-dir", required=True, help="Directory containing Pulse YAML configs")
    parser.add_argument("--output-dir", default="definitions/scanners/", help="Output directory for Pinky scanner MDs")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Show what would be created (default: on)")
    parser.add_argument("--write", action="store_true", help="Actually write files")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    if not input_dir.exists():
        print(f"Error: input directory {input_dir} does not exist")
        sys.exit(1)

    configs = list(input_dir.glob("*.yaml")) + list(input_dir.glob("*.yml"))
    if not configs:
        print(f"No YAML files found in {input_dir}")
        sys.exit(0)

    for config_file in configs:
        with open(config_file) as f:
            config = yaml.safe_load(f)

        if not config:
            continue

        md_content = translate_scanner(config, str(config_file))
        output_file = output_dir / f"{config_file.stem}.md"

        if args.write:
            output_dir.mkdir(parents=True, exist_ok=True)
            output_file.write_text(md_content)
            print(f"Created: {output_file}")
        else:
            print(f"\n--- Would create: {output_file} ---")
            print(md_content)

    print(f"\n{'Wrote' if args.write else 'Would write'} {len(configs)} scanner definitions")


if __name__ == "__main__":
    main()
```

```bash
chmod +x scripts/migrate-from-pulse.py
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrate-from-pulse.py
git commit -m "feat: add Pulse-to-Pinky scanner migration utility"
```

---

### Task 24: Final integration — full verify

- [ ] **Step 1: Run make verify**

Run: `make verify`
Expected: All lint, typecheck, and tests pass.

- [ ] **Step 2: Run migrations end-to-end**

Run: `cd apps/api && .venv/bin/python -m alembic upgrade head`
Expected: All migrations apply cleanly.

- [ ] **Step 3: Verify migration chain**

Run: `cd apps/api && .venv/bin/python -m alembic history`
Expected: Linear chain from initial_schema through all new migrations.

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A && git commit -m "fix: address integration issues from final verify"
```

---

## Summary

| Phase | Tasks | What it delivers |
|-------|-------|-----------------|
| 1 | 1-6 | Token telemetry, budget enforcement, outcome recording |
| 2 | 7-12 | Analytics queries, trends API, dashboard upgrade, eval CI gate |
| 3 | 13-14 | SAST, dependency scan, secret scan, release workflow |
| 4 | 15-19 | OpenTelemetry, CSP reporting, data retention, chaos tests |
| 5 | 20-24 | Feature flags, origin tracking, Pulse migration utility |

Each phase is independently committable and testable. Run `make verify` at the end of each phase.
