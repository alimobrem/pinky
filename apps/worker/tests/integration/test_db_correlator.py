"""DbIssueCorrelator integration tests against real Postgres."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch

import asyncpg

from pinky_worker.issues.correlator import RawObservation
from pinky_worker.issues.db_correlator import DbIssueCorrelator

from .conftest import FakePool


def _make_obs(
    cluster_id: str,
    *,
    correlation_key: str = "pod-health::default/web-abc",
    title: str = "Pod CrashLoopBackOff",
    severity: str = "high",
    check_id: str = "crash-loop",
) -> RawObservation:
    return RawObservation(
        cluster_id=cluster_id,
        scanner="pod-health",
        scanner_version="1.0.0",
        check_id=check_id,
        severity=severity,
        resource_kind="Pod",
        resource_namespace="default",
        resource_name="web-abc",
        title=title,
        observed_at=datetime.now(UTC),
        correlation_key=correlation_key,
    )


async def _correlate(fake_pool: FakePool, obs: RawObservation):
    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=fake_pool):
        return await DbIssueCorrelator().correlate(obs)


async def test_first_observation_creates_issue_and_work_item(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    result = await _correlate(fake_pool, _make_obs(cluster_id))

    assert result.action == "created"
    issue = await conn.fetchrow(
        "SELECT status, severity, correlation_key FROM issues WHERE id = $1::uuid", result.issue_id,
    )
    assert issue["status"] == "open"
    assert issue["severity"] == "high"

    work_item = await conn.fetchrow("SELECT status, title FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item["status"] == "ready"
    assert work_item["title"] == "Pod CrashLoopBackOff"


async def test_duplicate_observation_attaches(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    obs = _make_obs(cluster_id)
    first = await _correlate(fake_pool, obs)
    second = await _correlate(fake_pool, obs)

    assert first.action == "created"
    assert second.action == "attached"
    assert second.issue_id == first.issue_id

    count = await conn.fetchval(
        "SELECT count(*) FROM issues WHERE correlation_key = $1 AND cluster_id = $2::uuid",
        obs.correlation_key, cluster_id,
    )
    assert count == 1


async def test_resolved_issue_reopens(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    obs = _make_obs(cluster_id)
    first = await _correlate(fake_pool, obs)

    await conn.execute(
        "UPDATE issues SET status = 'resolved', resolved_at = now() WHERE id = $1::uuid",
        first.issue_id,
    )

    reopened = await _correlate(fake_pool, obs)
    assert reopened.action == "reopened"
    assert reopened.issue_id == first.issue_id

    issue = await conn.fetchrow("SELECT status, resolved_at FROM issues WHERE id = $1::uuid", first.issue_id)
    assert issue["status"] == "open"
    assert issue["resolved_at"] is None


async def test_suppressed_issue_stays_suppressed(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    obs = _make_obs(cluster_id)
    first = await _correlate(fake_pool, obs)

    await conn.execute("UPDATE issues SET status = 'suppressed' WHERE id = $1::uuid", first.issue_id)

    result = await _correlate(fake_pool, obs)
    assert result.action == "attached"

    row = await conn.fetchrow("SELECT status FROM issues WHERE id = $1::uuid", first.issue_id)
    assert row["status"] == "suppressed"


async def test_priority_mapping_critical(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    result = await _correlate(fake_pool, _make_obs(cluster_id, severity="critical"))
    work_item = await conn.fetchrow("SELECT priority FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item["priority"] == "high"


async def test_priority_mapping_medium(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    result = await _correlate(fake_pool, _make_obs(cluster_id, severity="medium"))
    work_item = await conn.fetchrow("SELECT priority FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item["priority"] == "medium"


async def test_different_keys_create_separate_issues(
    conn: asyncpg.Connection, cluster_id: str, fake_pool: FakePool,
) -> None:
    r1 = await _correlate(fake_pool, _make_obs(cluster_id, correlation_key="pod-health::default/web-1"))
    r2 = await _correlate(fake_pool, _make_obs(cluster_id, correlation_key="pod-health::default/web-2"))

    assert r1.action == "created"
    assert r2.action == "created"
    assert r1.issue_id != r2.issue_id
