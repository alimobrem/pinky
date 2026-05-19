"""Alert route tests — watch page data source."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_list_alerts_empty(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/alerts")
    assert r.status_code == 200
    assert "items" in r.json()


def test_list_alerts_with_severity_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/alerts", params={"severity": "critical"})
    assert r.status_code == 200


def test_list_alerts_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/alerts")
    assert r.status_code == 401
