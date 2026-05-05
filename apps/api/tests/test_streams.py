"""SSE stream tests — verify endpoints are registered and respond to auth.

SSE connections are long-lived, so we only test registration and auth
enforcement (not content), to avoid test timeouts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

STREAM_ENDPOINTS = [
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

    stream_paths = {"/api/v1/streams/work-items", "/api/v1/streams/watch", "/api/v1/streams/issues"}
    registered = {r.path for r in app.routes if hasattr(r, "path")}
    for path in stream_paths:
        assert path in registered, f"{path} not registered in app"
