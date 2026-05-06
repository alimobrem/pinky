"""SSE stream routes — real-time updates via Postgres LISTEN/NOTIFY.

Each stream listens on a Postgres NOTIFY channel for domain events.
Events are broadcast to all connected SSE clients matching the stream.
Heartbeats sent every 15s. Clients reconnect with Last-Event-ID for
stateless resume (refetch from API on reconnect).
"""

import asyncio
import contextlib
import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import asyncpg
from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

from pinky_api.config import get_settings

router = APIRouter(prefix="/api/v1/streams", tags=["streams"])

HEARTBEAT_INTERVAL = 15
SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


def _raw_pg_url() -> str:
    url = get_settings().database.url
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def _sse_with_notify(request: Request, channel: str) -> AsyncGenerator[str, None]:
    """SSE generator that listens to Postgres NOTIFY on a channel."""
    sequence = 0
    last_event_id = request.headers.get("last-event-id")
    if last_event_id:
        with contextlib.suppress(ValueError):
            sequence = int(last_event_id)
    conn: asyncpg.Connection | None = None

    try:
        conn = await asyncpg.connect(_raw_pg_url())
        assert conn is not None
        await conn.add_listener(channel, lambda *_: None)

        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)

        def _on_notify(conn: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait(payload)

        await conn.remove_listener(channel, lambda *_: None)
        await conn.add_listener(channel, _on_notify)

        while True:
            if await request.is_disconnected():
                break

            try:
                payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                sequence += 1
                payload_data = json.loads(payload)
                envelope = {
                    "event_id": payload_data.get("event_id", ""),
                    "stream": channel,
                    "aggregate_id": payload_data.get("aggregate_id", ""),
                    "type": payload_data.get("event_type", "update"),
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "sequence": sequence,
                    "payload": payload_data,
                }
                yield f"id: {sequence}\nevent: update\ndata: {json.dumps(envelope)}\n\n"
            except TimeoutError:
                heartbeat = json.dumps({"ts": datetime.now(UTC).isoformat()})
                yield f"event: heartbeat\ndata: {heartbeat}\n\n"

    except Exception:
        error = json.dumps({"error": "stream_error", "message": "Connection to event source failed"})
        yield f"event: error\ndata: {error}\n\n"
    finally:
        if conn and not conn.is_closed():
            await conn.close()


async def _sse_multi_channel(request: Request, channels: list[str]) -> AsyncGenerator[str, None]:
    """SSE generator that listens to multiple Postgres NOTIFY channels."""
    sequence = 0
    conn: asyncpg.Connection | None = None

    try:
        conn = await asyncpg.connect(_raw_pg_url())
        assert conn is not None

        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=200)

        def _on_notify(conn: asyncpg.Connection, pid: int, channel: str, payload: str) -> None:
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait((channel, payload))

        for ch in channels:
            await conn.add_listener(ch, _on_notify)

        while True:
            if await request.is_disconnected():
                break

            try:
                channel, payload = await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_INTERVAL)
                sequence += 1
                payload_data = json.loads(payload)
                envelope = {
                    "event_id": payload_data.get("event_id", ""),
                    "stream": channel,
                    "aggregate_id": payload_data.get("aggregate_id", ""),
                    "type": payload_data.get("event_type", "update"),
                    "occurred_at": datetime.now(UTC).isoformat(),
                    "sequence": sequence,
                    "payload": payload_data,
                }
                yield f"id: {sequence}\nevent: update\ndata: {json.dumps(envelope)}\n\n"
            except TimeoutError:
                heartbeat = json.dumps({"ts": datetime.now(UTC).isoformat()})
                yield f"event: heartbeat\ndata: {heartbeat}\n\n"

    except Exception:
        error = json.dumps({"error": "stream_error", "message": "Connection to event source failed"})
        yield f"event: error\ndata: {error}\n\n"
    finally:
        if conn and not conn.is_closed():
            await conn.close()


async def _sse_poll(request: Request, stream_name: str) -> AsyncGenerator[str, None]:
    """Fallback SSE generator when NOTIFY isn't available (e.g., tests)."""
    while True:
        if await request.is_disconnected():
            break
        heartbeat = json.dumps({"ts": datetime.now(UTC).isoformat()})
        yield f"event: heartbeat\ndata: {heartbeat}\n\n"
        await asyncio.sleep(HEARTBEAT_INTERVAL)


def _make_stream(request: Request, channel: str) -> StreamingResponse:
    try:
        _raw_pg_url()
        generator = _sse_with_notify(request, channel)
    except Exception:
        generator = _sse_poll(request, channel)

    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/events")
async def stream_all_events(request: Request) -> StreamingResponse:
    """Unified SSE stream — listens to ALL Postgres NOTIFY channels at once."""
    channels = ["pinky_work_items", "pinky_watch", "pinky_issues"]
    try:
        _raw_pg_url()
        generator = _sse_multi_channel(request, channels)
    except Exception:
        generator = _sse_poll(request, "events")
    return StreamingResponse(generator, media_type="text/event-stream", headers=SSE_HEADERS)


@router.get("/work-items")
async def stream_work_items(request: Request) -> StreamingResponse:
    return _make_stream(request, "pinky_work_items")


@router.get("/watch")
async def stream_watch(request: Request) -> StreamingResponse:
    return _make_stream(request, "pinky_watch")


@router.get("/issues")
async def stream_issues(request: Request) -> StreamingResponse:
    return _make_stream(request, "pinky_issues")


@router.get("/executions/{execution_id}")
async def stream_execution(execution_id: str, request: Request) -> StreamingResponse:
    return _make_stream(request, f"pinky_execution_{execution_id}")
