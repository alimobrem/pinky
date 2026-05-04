"""Shared fixtures for worker integration tests."""

from __future__ import annotations

import os
import shutil
import uuid

import asyncpg
import pytest
from temporalio.testing import WorkflowEnvironment

TEMPORAL_PATH = shutil.which("temporal") or os.environ.get("TEMPORAL_PATH", "")
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://pinky:pinky@localhost:5432/pinky",
)


@pytest.fixture(scope="session")
def _check_temporal() -> None:
    if not TEMPORAL_PATH:
        pytest.skip("temporal CLI not found — install via `brew install temporal`")


@pytest.fixture(scope="session")
async def workflow_env(_check_temporal: None):
    async with await WorkflowEnvironment.start_local(
        dev_server_existing_path=TEMPORAL_PATH,
        dev_server_log_level="error",
    ) as env:
        yield env


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


class FakePool:
    """Wraps an asyncpg connection to satisfy both pool usage patterns."""

    def __init__(self, c: asyncpg.Connection) -> None:
        self._c = c

    async def fetchrow(self, query: str, *args):
        return await self._c.fetchrow(query, *args)

    async def fetchval(self, query: str, *args):
        return await self._c.fetchval(query, *args)

    async def execute(self, query: str, *args):
        return await self._c.execute(query, *args)

    def acquire(self):
        return _FakeAcquire(self._c)


class _FakeAcquire:
    def __init__(self, c: asyncpg.Connection) -> None:
        self._c = c

    async def __aenter__(self):
        return self._c

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def fake_pool(conn: asyncpg.Connection) -> FakePool:
    return FakePool(conn)


@pytest.fixture
async def cluster_id(conn: asyncpg.Connection) -> str:
    cid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO cluster_registry (id, display_name, api_endpoint, onboarding_state, created_at, updated_at)
           VALUES ($1::uuid, 'test-cluster', 'https://api.test:6443', 'ready', now(), now())""",
        cid,
    )
    return cid


@pytest.fixture
async def execution_id(conn: asyncpg.Connection, cluster_id: str) -> str:
    eid = str(uuid.uuid4())
    await conn.execute(
        """INSERT INTO executions (id, cluster_id, execution_type, status, created_at)
           VALUES ($1::uuid, $2::uuid, 'investigation', 'pending', now())""",
        eid, cluster_id,
    )
    return eid
