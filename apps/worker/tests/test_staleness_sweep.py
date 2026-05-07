"""Tests for staleness-based auto-resolution of issues."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from pinky_worker.definitions.loader import Definition, DefinitionRegistry
from pinky_worker.observation.observer import _sweep_stale_issues


class FakeConn:
    def __init__(self):
        self.executed: list[tuple] = []

    async def execute(self, query, *args):
        self.executed.append((query, args))


class FakePool:
    def __init__(self, fetch_result=None):
        self.conn = FakeConn()
        self._fetch_result = fetch_result or []

    async def fetch(self, query, *args):
        return self._fetch_result

    @asynccontextmanager
    async def acquire(self):
        yield self.conn


def _mock_registry(scanner_thresholds: dict[str, int] | None = None) -> DefinitionRegistry:
    registry = DefinitionRegistry()
    defs = {}
    if scanner_thresholds:
        for name, threshold in scanner_thresholds.items():
            defs[("scanner", name)] = Definition(
                kind="scanner",
                name=name,
                version="1.0.0",
                frontmatter={
                    "kind": "scanner",
                    "name": name,
                    "staleness_threshold_seconds": threshold,
                    "checks": [],
                },
                body="",
                source="test",
            )
    registry._definitions = defs
    return registry


def _make_issue(
    last_seen_ago_seconds: int,
    scanner: str = "pod-health",
) -> dict:
    return {
        "id": uuid.uuid4(),
        "correlation_key": f"test-{uuid.uuid4().hex[:8]}",
        "labels": {"scanner": scanner, "check_id": "test-check"},
        "last_seen_at": datetime.now(UTC) - timedelta(seconds=last_seen_ago_seconds),
    }


@pytest.mark.asyncio
async def test_sweep_resolves_stale_issue() -> None:
    stale_issue = _make_issue(last_seen_ago_seconds=1200)
    pool = FakePool(fetch_result=[stale_issue])

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stale_issues("cluster-1", _mock_registry(), scan_healthy=True)

    assert count == 1
    queries = [q for q, _ in pool.conn.executed]
    assert any("resolved_by = 'staleness'" in q for q in queries)
    assert any("pg_notify" in q for q in queries)
    assert any("domain_events" in q for q in queries)


@pytest.mark.asyncio
async def test_sweep_skips_when_scan_unhealthy() -> None:
    count = await _sweep_stale_issues("cluster-1", _mock_registry(), scan_healthy=False)
    assert count == 0


@pytest.mark.asyncio
async def test_sweep_skips_recent_issue() -> None:
    pool = FakePool(fetch_result=[])

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stale_issues("cluster-1", _mock_registry(), scan_healthy=True)

    assert count == 0


@pytest.mark.asyncio
async def test_sweep_marks_work_items_done() -> None:
    stale_issue = _make_issue(last_seen_ago_seconds=1200)
    pool = FakePool(fetch_result=[stale_issue])

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        await _sweep_stale_issues("cluster-1", _mock_registry(), scan_healthy=True)

    queries = [q for q, _ in pool.conn.executed]
    assert any("work_items" in q and "done" in q for q in queries)


@pytest.mark.asyncio
async def test_sweep_respects_per_scanner_threshold() -> None:
    issue = _make_issue(last_seen_ago_seconds=1200, scanner="cert-expiry")
    pool = FakePool(fetch_result=[issue])
    registry = _mock_registry(scanner_thresholds={"cert-expiry": 7200})

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stale_issues("cluster-1", registry, scan_healthy=True)

    assert count == 0


@pytest.mark.asyncio
async def test_sweep_resolves_past_per_scanner_threshold() -> None:
    issue = _make_issue(last_seen_ago_seconds=8000, scanner="cert-expiry")
    pool = FakePool(fetch_result=[issue])
    registry = _mock_registry(scanner_thresholds={"cert-expiry": 7200})

    with patch("pinky_worker.db.get_pool", AsyncMock(return_value=pool)):
        count = await _sweep_stale_issues("cluster-1", registry, scan_healthy=True)

    assert count == 1
