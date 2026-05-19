"""Issue route tests — list, get, suppress, resolve, escalate."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient


# --- List ---


def test_list_issues_empty(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/issues")
    assert r.status_code == 200
    assert "items" in r.json()
    assert "total_count" in r.json()


def test_list_issues_with_status_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/issues", params={"status": "open"})
    assert r.status_code == 200


def test_list_issues_with_severity_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/issues", params={"severity": "critical"})
    assert r.status_code == 200


def test_list_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/issues")
    assert r.status_code == 401


# --- Get ---


def test_get_nonexistent_issue(authed_client: TestClient) -> None:
    r = authed_client.get(f"/api/v1/issues/{uuid.uuid4()}")
    assert r.status_code == 404


# --- Suppress ---


def test_suppress_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.post(
        f"/api/v1/issues/{uuid.uuid4()}/suppress",
        json={},
    )
    assert r.status_code == 404


def test_suppress_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.post(
        f"/api/v1/issues/{uuid.uuid4()}/suppress",
        json={},
    )
    assert r.status_code == 401


# --- Resolve ---


def test_resolve_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.post(f"/api/v1/issues/{uuid.uuid4()}/resolve")
    assert r.status_code == 404


def test_resolve_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.post(f"/api/v1/issues/{uuid.uuid4()}/resolve")
    assert r.status_code == 401


# --- Escalate ---


def test_escalate_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.post(f"/api/v1/issues/{uuid.uuid4()}/escalate")
    assert r.status_code == 404


def test_escalate_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.post(f"/api/v1/issues/{uuid.uuid4()}/escalate")
    assert r.status_code == 401
