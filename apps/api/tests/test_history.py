"""History route tests — timeline and export endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def test_list_history_empty(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/history")
    assert r.status_code == 200
    assert "items" in r.json()


def test_list_history_with_cluster_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/history", params={"cluster_id": str(uuid.uuid4())})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_list_history_with_type_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/history", params={"event_type": "work_item.created"})
    assert r.status_code == 200


def test_list_history_pagination(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/history", params={"limit": 5})
    assert r.status_code == 200
    assert "next_cursor" in r.json()
    assert "has_more" in r.json()


def test_list_history_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/history")
    assert r.status_code == 401


def test_export_history(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/history/export")
    assert r.status_code == 200


def test_export_history_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/history/export")
    assert r.status_code == 401
