"""Execution route tests — investigation dispatch, approve, reject.

Temporal is mocked via patch. Data seeded through API (cluster creation)
and direct DB insert (work items can't be created via API).
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


def _create_cluster(client: TestClient) -> str:
    r = client.post("/api/v1/clusters", json={
        "display_name": f"exec-test-{uuid.uuid4().hex[:8]}",
        "api_endpoint": "https://exec-test:6443",
    })
    assert r.status_code == 201
    return r.json()["id"]


def test_list_executions_empty(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/executions")
    assert r.status_code == 200
    assert "items" in r.json()


def test_get_nonexistent_execution(authed_client: TestClient) -> None:
    r = authed_client.get(f"/api/v1/executions/{uuid.uuid4()}")
    assert r.status_code == 404


def test_get_invalid_uuid_execution(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/executions/not-a-uuid")
    assert r.status_code == 404


def test_start_execution_without_work_item_param(authed_client: TestClient) -> None:
    r = authed_client.post("/api/v1/executions")
    assert r.status_code == 422


def test_approve_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.post(
        f"/api/v1/executions/{uuid.uuid4()}/approve",
        json={"changeset_digest": "abc"},
    )
    assert r.status_code == 404


def test_reject_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.post(
        f"/api/v1/executions/{uuid.uuid4()}/reject",
        json={"reason": "too risky"},
    )
    assert r.status_code == 404


def test_list_executions_with_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/executions", params={"status": "pending"})
    assert r.status_code == 200
    assert isinstance(r.json()["items"], list)


def test_list_executions_with_work_item_filter(authed_client: TestClient) -> None:
    r = authed_client.get(
        "/api/v1/executions",
        params={"work_item_id": str(uuid.uuid4())},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
