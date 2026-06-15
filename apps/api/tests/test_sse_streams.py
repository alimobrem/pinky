"""Tests for SSE stream infrastructure — auth, queue overflow, envelope."""

from __future__ import annotations

import asyncio
import json
import logging
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient


class TestSSEAuth:
    def test_events_stream_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.get("/api/v1/streams/events")
        assert r.status_code == 401

    def test_execution_stream_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.get(
            "/api/v1/streams/executions/00000000-0000-0000-0000-000000000000",
        )
        assert r.status_code == 401

    def test_work_items_stream_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.get("/api/v1/streams/work-items")
        assert r.status_code == 401

    def test_watch_stream_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.get("/api/v1/streams/watch")
        assert r.status_code == 401

    def test_issues_stream_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.get("/api/v1/streams/issues")
        assert r.status_code == 401


class TestQueueOverflow:
    def test_overflow_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        from pinky_api.routes.streams import _on_notify_factory

        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=2)
        queue.put_nowait(("ch", "a"))
        queue.put_nowait(("ch", "b"))

        with caplog.at_level(logging.WARNING, logger="pinky_api.routes.streams"):
            on_notify = _on_notify_factory(queue)
            on_notify(MagicMock(), 0, "test_channel", "overflow_payload")

        assert any("queue full" in r.message.lower() for r in caplog.records)
        assert queue.qsize() == 2

    def test_normal_enqueue_succeeds(self) -> None:
        from pinky_api.routes.streams import _on_notify_factory

        queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=10)
        on_notify = _on_notify_factory(queue)
        on_notify(MagicMock(), 0, "pinky_issues", '{"event_type": "test"}')

        assert queue.qsize() == 1
        channel, payload = queue.get_nowait()
        assert channel == "pinky_issues"
        assert json.loads(payload)["event_type"] == "test"


class TestSSEEndpointRegistration:
    def test_all_stream_endpoints_registered(self) -> None:
        from pinky_api.app import app
        from tests.conftest import collect_route_paths

        registered = collect_route_paths(app)
        assert "/api/v1/streams/events" in registered
        assert "/api/v1/streams/work-items" in registered
        assert "/api/v1/streams/watch" in registered
        assert "/api/v1/streams/issues" in registered
        assert "/api/v1/streams/executions/{execution_id}" in registered
