"""SSE stream tests — verify endpoints are registered and respond to auth.

SSE connections are long-lived, so we only test registration and auth
enforcement (not content), to avoid test timeouts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

STREAM_ENDPOINTS = [
    "/api/v1/streams/events",
    "/api/v1/streams/work-items",
    "/api/v1/streams/watch",
    "/api/v1/streams/issues",
    "/api/v1/streams/executions/test-exec-id",
]


def test_unauthed_stream_rejected(unauthed_client: TestClient) -> None:
    for endpoint in STREAM_ENDPOINTS:
        r = unauthed_client.get(endpoint)
        assert r.status_code == 401, f"{endpoint} should require auth"


def test_stream_routes_registered() -> None:
    from pinky_api.app import app

    stream_paths = {
        "/api/v1/streams/events",
        "/api/v1/streams/work-items",
        "/api/v1/streams/watch",
        "/api/v1/streams/issues",
    }
    registered = {r.path for r in app.routes if hasattr(r, "path")}
    for path in stream_paths:
        assert path in registered, f"{path} not registered in app"


def test_unified_stream_registered() -> None:
    from pinky_api.app import app

    registered = {r.path for r in app.routes if hasattr(r, "path")}
    assert "/api/v1/streams/events" in registered


class TestChatEndpoint:
    def test_chat_requires_auth(self, unauthed_client: TestClient) -> None:
        r = unauthed_client.post(
            "/api/v1/work-items/00000000-0000-0000-0000-000000000000/chat",
            json={"message": "hello"},
        )
        assert r.status_code == 401

    def test_chat_not_found_for_invalid_task(self, authed_client: TestClient) -> None:
        r = authed_client.post(
            "/api/v1/work-items/00000000-0000-0000-0000-000000000000/chat",
            json={"message": "hello"},
        )
        assert r.status_code == 404

    def test_chat_validates_body(self, authed_client: TestClient) -> None:
        r = authed_client.post(
            "/api/v1/work-items/00000000-0000-0000-0000-000000000000/chat",
            json={},
        )
        assert r.status_code == 422
