"""Test feature flag API routes — basic CRUD only.

Service-level tests are minimal since feature flags are a cutover enabler,
not a core product feature. We test the API contract and admin enforcement.
"""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from pinky_api.services import feature_flags as ff_service


@pytest.fixture(autouse=True)
def clear_cache():
    ff_service.clear_cache()
    yield
    ff_service.clear_cache()


def test_create_flag_as_admin(authed_client: TestClient):
    resp = authed_client.post(
        "/api/v1/feature-flags",
        json={"flag_name": f"test_{uuid4().hex[:8]}", "enabled": True, "scope_type": "global"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["enabled"] is True
    assert data["scope_type"] == "global"
    assert data["scope_id"] is None


def test_create_flag_as_non_admin(non_admin_client: TestClient):
    resp = non_admin_client.post(
        "/api/v1/feature-flags",
        json={"flag_name": f"blocked_{uuid4().hex[:8]}", "enabled": False},
    )
    assert resp.status_code == 403


def test_list_flags(authed_client: TestClient):
    flag_a = f"flag_a_{uuid4().hex[:8]}"
    flag_b = f"flag_b_{uuid4().hex[:8]}"

    authed_client.post("/api/v1/feature-flags", json={"flag_name": flag_a, "enabled": True})
    authed_client.post("/api/v1/feature-flags", json={"flag_name": flag_b, "enabled": False})

    resp = authed_client.get("/api/v1/feature-flags")
    assert resp.status_code == 200
    flags = resp.json()["flags"]
    assert len(flags) >= 2
    names = [f["flag_name"] for f in flags]
    assert flag_a in names
    assert flag_b in names


def test_update_flag(authed_client: TestClient):
    create_resp = authed_client.post(
        "/api/v1/feature-flags",
        json={"flag_name": f"toggle_{uuid4().hex[:8]}", "enabled": False},
    )
    flag_id = create_resp.json()["id"]

    resp = authed_client.patch(f"/api/v1/feature-flags/{flag_id}", json={"enabled": True})
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True


def test_update_nonexistent_flag(authed_client: TestClient):
    resp = authed_client.patch(f"/api/v1/feature-flags/{uuid4()}", json={"enabled": True})
    assert resp.status_code == 404


def test_delete_flag(authed_client: TestClient):
    flag_name = f"delete_{uuid4().hex[:8]}"
    create_resp = authed_client.post(
        "/api/v1/feature-flags",
        json={"flag_name": flag_name, "enabled": True},
    )
    flag_id = create_resp.json()["id"]

    resp = authed_client.delete(f"/api/v1/feature-flags/{flag_id}")
    assert resp.status_code == 204

    get_resp = authed_client.get("/api/v1/feature-flags")
    names = [f["flag_name"] for f in get_resp.json()["flags"]]
    assert flag_name not in names


def test_delete_nonexistent_flag(authed_client: TestClient):
    resp = authed_client.delete(f"/api/v1/feature-flags/{uuid4()}")
    assert resp.status_code == 404
