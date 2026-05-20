"""Tests for domain event emission in DbIssueCorrelator."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from pinky_worker.issues.correlator import RawObservation


def _make_obs(
    correlation_key: str = "ck1",
    cluster_id: str = "c1",
) -> RawObservation:
    return RawObservation(
        cluster_id=cluster_id,
        scanner="pod-health",
        scanner_version="1.0.0",
        check_id="oom-killed",
        severity="critical",
        resource_kind="Pod",
        resource_namespace="ns1",
        resource_name="app-pod",
        title="Pod OOM",
        fingerprint=f"fp-{uuid.uuid4().hex[:8]}",
        correlation_key=correlation_key,
        observed_at=datetime.now(timezone.utc),
    )


class FakeConn:
    def __init__(self, existing_issue=None):
        self._existing_issue = existing_issue

    async def execute(self, query, *args):
        pass

    async def fetch(self, query, *args):
        return []

    async def fetchrow(self, query, *args):
        if "SELECT COUNT" in query:
            return {"cnt": 1}
        if "SELECT id, status FROM issues" in query:
            return self._existing_issue
        return None


def _make_pool(conn):
    pool = AsyncMock()

    @asynccontextmanager
    async def acquire():
        yield conn

    pool.acquire = acquire
    return pool


@pytest.mark.asyncio
async def test_correlate_new_issue_emits_domain_events() -> None:
    conn = FakeConn(existing_issue=None)
    pool = _make_pool(conn)

    with (
        patch("pinky_worker.issues.db_correlator.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.issues.db_correlator.emit_domain_event", new_callable=AsyncMock) as mock_emit,
    ):
        from pinky_worker.issues.db_correlator import DbIssueCorrelator
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(_make_obs())

    assert result.action == "created"
    assert mock_emit.call_count == 2
    assert mock_emit.call_args_list[0][0][1] == "issue.created"
    assert mock_emit.call_args_list[1][0][1] == "work_item.created"


@pytest.mark.asyncio
async def test_correlate_reopened_issue_emits_domain_event() -> None:
    existing = {"id": uuid.uuid4(), "status": "resolved"}
    conn = FakeConn(existing_issue=existing)
    pool = _make_pool(conn)

    with (
        patch("pinky_worker.issues.db_correlator.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.issues.db_correlator.emit_domain_event", new_callable=AsyncMock) as mock_emit,
    ):
        from pinky_worker.issues.db_correlator import DbIssueCorrelator
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(_make_obs())

    assert result.action == "reopened"
    assert mock_emit.call_count == 1
    assert mock_emit.call_args[0][1] == "issue.reopened"


@pytest.mark.asyncio
async def test_correlate_attached_does_not_emit() -> None:
    existing = {"id": uuid.uuid4(), "status": "open"}
    conn = FakeConn(existing_issue=existing)
    pool = _make_pool(conn)

    with (
        patch("pinky_worker.issues.db_correlator.get_pool", AsyncMock(return_value=pool)),
        patch("pinky_worker.issues.db_correlator.emit_domain_event", new_callable=AsyncMock) as mock_emit,
    ):
        from pinky_worker.issues.db_correlator import DbIssueCorrelator
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(_make_obs())

    assert result.action == "attached"
    mock_emit.assert_not_called()
