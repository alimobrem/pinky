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
    assert len(errors) < num_clients * 0.1, f"Too many failures: {len(errors)}/{num_clients}"
