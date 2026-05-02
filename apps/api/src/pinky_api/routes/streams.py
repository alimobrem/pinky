"""SSE stream routes — real-time updates for all product surfaces."""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/api/v1/streams", tags=["streams"])

HEARTBEAT_INTERVAL = 15


async def _sse_generator(request: Request, stream_name: str) -> None:
    """Generic SSE generator with heartbeat and graceful disconnect."""
    sequence = 0
    while True:
        if await request.is_disconnected():
            break

        # TODO: poll Postgres projections or listen to NOTIFY for real events
        # For now, emit heartbeat only
        heartbeat = json.dumps({"ts": datetime.now(timezone.utc).isoformat()})
        yield f"event: heartbeat\ndata: {heartbeat}\n\n"

        await asyncio.sleep(HEARTBEAT_INTERVAL)


@router.get("/work-items")
async def stream_work_items(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request, "work-items"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/watch")
async def stream_watch(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request, "watch"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/issues")
async def stream_issues(request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request, "issues"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/executions/{execution_id}")
async def stream_execution(execution_id: str, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_generator(request, f"executions/{execution_id}"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
