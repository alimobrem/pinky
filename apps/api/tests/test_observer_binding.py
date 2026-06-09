"""Tests for observer binding CRUD endpoints."""

import uuid

from fastapi.testclient import TestClient

CLUSTER_PAYLOAD = {
    "display_name": "obs-test-cluster",
    "api_endpoint": "https://api.obs-test.example.com:6443",
}


def _create_cluster(client: TestClient) -> str:
    resp = client.post("/api/v1/clusters", json=CLUSTER_PAYLOAD)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_create_observer_binding(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    resp = authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "sa-token-abc123"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "configured"}


def test_create_observer_binding_upserts(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "first-token"},
    )
    resp = authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "second-token"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "configured"}


def test_get_observer_binding(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "sa-token-get"},
    )
    resp = authed_client.get(f"/api/v1/clusters/{cluster_id}/observer-binding")
    assert resp.status_code == 200
    body = resp.json()
    assert body["cluster_id"] == cluster_id
    assert body["auth_method"] == "service_account"
    assert body["health_state"] == "unknown"
    assert body["last_observation_at"] is None
    assert "token" not in body
    assert "encrypted_credential" not in body
    assert "created_at" in body


def test_get_observer_binding_not_found(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    resp = authed_client.get(f"/api/v1/clusters/{cluster_id}/observer-binding")
    assert resp.status_code == 404


def test_delete_observer_binding(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "sa-token-del"},
    )
    resp = authed_client.delete(f"/api/v1/clusters/{cluster_id}/observer-binding")
    assert resp.status_code == 204

    resp = authed_client.get(f"/api/v1/clusters/{cluster_id}/observer-binding")
    assert resp.status_code == 404


def test_delete_resets_onboarding_state(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "sa-token-onboard"},
    )
    # Binding sets onboarding to "ready"
    cluster = authed_client.get(f"/api/v1/clusters/{cluster_id}").json()
    assert cluster["onboarding_state"] == "ready"

    authed_client.delete(f"/api/v1/clusters/{cluster_id}/observer-binding")

    cluster = authed_client.get(f"/api/v1/clusters/{cluster_id}").json()
    assert cluster["onboarding_state"] == "pending"


def test_create_sets_onboarding_ready(authed_client: TestClient) -> None:
    cluster_id = _create_cluster(authed_client)
    cluster = authed_client.get(f"/api/v1/clusters/{cluster_id}").json()
    assert cluster["onboarding_state"] == "pending"

    authed_client.post(
        f"/api/v1/clusters/{cluster_id}/observer-binding",
        json={"token": "sa-token-ready"},
    )
    cluster = authed_client.get(f"/api/v1/clusters/{cluster_id}").json()
    assert cluster["onboarding_state"] == "ready"


def test_non_admin_rejected(non_admin_client: TestClient) -> None:
    fake_id = str(uuid.uuid4())
    assert non_admin_client.post(
        f"/api/v1/clusters/{fake_id}/observer-binding",
        json={"token": "nope"},
    ).status_code == 403
    assert non_admin_client.get(
        f"/api/v1/clusters/{fake_id}/observer-binding",
    ).status_code == 403
    assert non_admin_client.delete(
        f"/api/v1/clusters/{fake_id}/observer-binding",
    ).status_code == 403


def test_nonexistent_cluster(authed_client: TestClient) -> None:
    fake_id = str(uuid.uuid4())
    resp = authed_client.post(
        f"/api/v1/clusters/{fake_id}/observer-binding",
        json={"token": "sa-token-404"},
    )
    assert resp.status_code == 404
