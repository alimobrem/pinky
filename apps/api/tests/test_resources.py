"""Tests for resource GET/PUT endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

RESOLVE = "pinky_api.routes.resources._resolve_token"
GET = "pinky_api.routes.resources.get_resource"
APPLY = "pinky_api.routes.resources.apply_resource"
READ_ACCESS = "pinky_api.routes.resources.require_cluster_read_access"
WRITE_ACCESS = "pinky_api.routes.resources.require_cluster_write_access"


@pytest.fixture
def k8s_mocks():
    with (
        patch(RESOLVE, new_callable=AsyncMock) as resolve,
        patch(GET, new_callable=AsyncMock) as get,
        patch(APPLY, new_callable=AsyncMock) as apply,
        patch(READ_ACCESS, new_callable=AsyncMock),
        patch(WRITE_ACCESS, new_callable=AsyncMock),
    ):
        resolve.return_value = ("https://api.test:6443", "test-token")
        yield {"resolve": resolve, "get": get, "apply": apply}


def test_get_resource_returns_yaml(authed_client: TestClient, k8s_mocks):
    k8s_mocks["get"].return_value = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "web", "namespace": "default"},
        "spec": {"replicas": 3},
    }

    resp = authed_client.get(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/web",
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "yaml" in data
    assert data["resource"]["kind"] == "Deployment"


def test_get_resource_not_found(authed_client: TestClient, k8s_mocks):
    k8s_mocks["get"].return_value = {"error": "not_found", "status": 404}

    resp = authed_client.get(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/missing",
    )
    assert resp.status_code == 404


def test_get_resource_forbidden(authed_client: TestClient, k8s_mocks):
    k8s_mocks["get"].return_value = {"error": "forbidden", "status": 403}

    resp = authed_client.get(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/web",
    )
    assert resp.status_code == 403


def test_apply_resource_success(authed_client: TestClient, k8s_mocks):
    k8s_mocks["apply"].return_value = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "web", "namespace": "default"},
        "spec": {"replicas": 5},
    }

    resp = authed_client.put(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/web",
        json={"yaml_content": "spec:\n  replicas: 5\n"},
    )
    assert resp.status_code == 200
    assert resp.json()["resource"]["spec"]["replicas"] == 5


def test_apply_invalid_yaml(authed_client: TestClient, k8s_mocks):
    resp = authed_client.put(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/web",
        json={"yaml_content": ":\ninvalid: [yaml"},
    )
    assert resp.status_code == 400


def test_apply_resource_forbidden(authed_client: TestClient, k8s_mocks):
    k8s_mocks["apply"].return_value = {"error": "forbidden", "status": 403}

    resp = authed_client.put(
        f"/api/v1/clusters/{uuid.uuid4()}/resources/default/deployment/web",
        json={"yaml_content": "spec:\n  replicas: 5\n"},
    )
    assert resp.status_code == 403
