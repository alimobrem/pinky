"""Shared fixtures for worker integration tests."""

from __future__ import annotations

import os
import shutil

import pytest
from temporalio.testing import WorkflowEnvironment

TEMPORAL_PATH = shutil.which("temporal") or os.environ.get("TEMPORAL_PATH", "")


@pytest.fixture(scope="session")
def _check_temporal() -> None:
    if not TEMPORAL_PATH:
        pytest.skip("temporal CLI not found — install via `brew install temporal`")


@pytest.fixture
async def workflow_env(_check_temporal: None):
    env = await WorkflowEnvironment.start_local(
        dev_server_existing_path=TEMPORAL_PATH,
        dev_server_log_level="error",
    )
    try:
        yield env
    finally:
        await env.__aexit__(None, None, None)
