"""DbIssueCorrelator integration tests against real Postgres.

Each test runs inside a transaction that rolls back, leaving the DB clean.
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from unittest.mock import patch

import asyncpg
import pytest

from pinky_worker.issues.correlator import RawObservation
from pinky_worker.issues.db_correlator import DbIssueCorrelator

TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://pinky:pinky@localhost:5432/pinky",
)


@pytest.fixture
async def conn():
    c = await asyncpg.connect(TEST_DB_URL)
    tx = c.transaction()
    await tx.start()
    try:
        yield c
    finally:
        await tx.rollback()
        await c.close()


@pytest.fixture
def cluster_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
async def registered_cluster(conn: asyncpg.Connection, cluster_id: str) -> str:
    await conn.execute(
        """INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state, created_at, updated_at)
           VALUES ($1::uuid, $2, $3, 'ready', now(), now())""",
        cluster_id, f"test-cluster-{cluster_id[:8]}", "https://api.test:6443",
    )
    return cluster_id


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


def _mock_get_pool(conn: asyncpg.Connection):
    """Create a mock pool that returns the test connection."""

    class _FakePool:
        def acquire(self):
            return _FakeCtx(conn)

    class _FakeCtx:
        def __init__(self, c: asyncpg.Connection):
            self._c = c

        async def __aenter__(self):
            return self._c

        async def __aexit__(self, *args):
            pass

    return _FakePool()


async def test_first_observation_creates_issue_and_work_item(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster)

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(obs)

    assert result.action == "created"
    assert result.issue_id is not None

    issue = await conn.fetchrow("SELECT * FROM issues WHERE id = $1::uuid", result.issue_id)
    assert issue is not None
    assert issue["status"] == "open"
    assert issue["severity"] == "high"
    assert issue["correlation_key"] == "pod-health::default/web-abc"

    work_item = await conn.fetchrow("SELECT * FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item is not None
    assert work_item["status"] == "ready"
    assert work_item["title"] == "Pod CrashLoopBackOff"


async def test_duplicate_observation_attaches_to_existing_issue(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster)

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        first = await correlator.correlate(obs)
        second = await correlator.correlate(obs)

    assert first.action == "created"
    assert second.action == "attached"
    assert second.issue_id == first.issue_id

    issues = await conn.fetch(
        "SELECT * FROM issues WHERE correlation_key = $1 AND cluster_id = $2::uuid",
        obs.correlation_key, registered_cluster,
    )
    assert len(issues) == 1


async def test_resolved_issue_reopens_on_new_observation(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster)

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        first = await correlator.correlate(obs)

    await conn.execute(
        "UPDATE issues SET status = 'resolved', resolved_at = now() WHERE id = $1::uuid",
        first.issue_id,
    )

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        reopened = await correlator.correlate(obs)

    assert reopened.action == "reopened"
    assert reopened.issue_id == first.issue_id

    issue = await conn.fetchrow("SELECT * FROM issues WHERE id = $1::uuid", first.issue_id)
    assert issue["status"] == "open"
    assert issue["resolved_at"] is None


async def test_suppressed_issue_reopens_on_new_observation(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster)

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        first = await correlator.correlate(obs)

    await conn.execute(
        "UPDATE issues SET status = 'suppressed' WHERE id = $1::uuid",
        first.issue_id,
    )

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        reopened = await correlator.correlate(obs)

    assert reopened.action == "reopened"


async def test_priority_mapping_critical_to_high(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster, severity="critical")

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(obs)

    work_item = await conn.fetchrow("SELECT * FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item["priority"] == "high"


async def test_priority_mapping_medium_severity(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs = _make_obs(registered_cluster, severity="medium")

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        result = await correlator.correlate(obs)

    work_item = await conn.fetchrow("SELECT * FROM work_items WHERE issue_id = $1::uuid", result.issue_id)
    assert work_item["priority"] == "medium"


async def test_different_correlation_keys_create_separate_issues(
    conn: asyncpg.Connection, registered_cluster: str,
) -> None:
    obs1 = _make_obs(registered_cluster, correlation_key="pod-health::default/web-1")
    obs2 = _make_obs(registered_cluster, correlation_key="pod-health::default/web-2")

    with patch("pinky_worker.issues.db_correlator.get_pool", return_value=_mock_get_pool(conn)):
        correlator = DbIssueCorrelator()
        r1 = await correlator.correlate(obs1)
        r2 = await correlator.correlate(obs2)

    assert r1.action == "created"
    assert r2.action == "created"
    assert r1.issue_id != r2.issue_id

    count = await conn.fetchval(
        "SELECT count(*) FROM issues WHERE cluster_id = $1::uuid",
        registered_cluster,
    )
    assert count == 2
