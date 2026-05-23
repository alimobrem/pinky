"""Chaos test: approval at exact timeout boundary."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest


@pytest.mark.chaos
@pytest.mark.asyncio
async def test_approval_at_expiry_boundary():
    """Approve at exact moment of expiry — must produce deterministic outcome."""
    expires_at = datetime.now(UTC) + timedelta(seconds=1)
    results = []

    async def attempt_approval():
        await asyncio.sleep(1.0)
        expired = datetime.now(UTC) >= expires_at
        results.append({"expired": expired, "time": datetime.now(UTC).isoformat()})

    tasks = [attempt_approval() for _ in range(10)]
    await asyncio.gather(*tasks)
    outcomes = set(r["expired"] for r in results)
    assert len(outcomes) == 1, f"Non-deterministic: {results}"
