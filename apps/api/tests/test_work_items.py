"""Work item route tests — CRUD, status transitions, assignment, reset, bulk."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from .conftest import TEST_PRINCIPAL


def _create_cluster_with_binding(client: TestClient) -> str:
    import asyncio

    from sqlalchemy import text

    from .conftest import _test_engine

    r = client.post("/api/v1/clusters", json={
        "display_name": f"wi-test-{uuid.uuid4().hex[:8]}",
        "api_endpoint": "https://wi-test:6443",
    })
    assert r.status_code == 201
    cluster_id = r.json()["id"]

    async def seed():
        async with _test_engine.begin() as conn:
            await conn.execute(text(
                "INSERT INTO principals (id, provider, subject, email, display_name, groups, created_at, updated_at) "
                "VALUES (:id, 'test', 'test-subject', :email, 'Test User', '[]'::jsonb, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ), {"id": TEST_PRINCIPAL["id"], "email": TEST_PRINCIPAL["email"]})
            await conn.execute(text(
                "INSERT INTO cluster_identity_bindings "
                "(id, principal_id, cluster_id, binding_method, status, encrypted_token, created_at, updated_at) "
                "VALUES (:id, :pid, :cid, 'token', 'valid', :tok, now(), now()) "
                "ON CONFLICT DO NOTHING"
            ), {
                "id": str(uuid.uuid4()),
                "pid": TEST_PRINCIPAL["id"],
                "cid": cluster_id,
                "tok": b"\x01" + b"\x00" * 12 + b"fake",
            })

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, seed()).result()
    else:
        asyncio.run(seed())

    return cluster_id


def _create_work_item(client: TestClient, cluster_id: str, **overrides) -> dict:
    body = {
        "cluster_id": cluster_id,
        "title": f"Test task {uuid.uuid4().hex[:8]}",
        "priority": "medium",
        **overrides,
    }
    r = client.post("/api/v1/work-items", json=body)
    assert r.status_code == 200, f"Create failed: {r.status_code} {r.text}"
    return r.json()


# --- List ---


def test_list_work_items_empty(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/work-items")
    assert r.status_code == 200
    assert "items" in r.json()
    assert "total_count" in r.json()


def test_list_work_items_with_status_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/work-items", params={"status": "ready"})
    assert r.status_code == 200


def test_list_work_items_with_priority_filter(authed_client: TestClient) -> None:
    r = authed_client.get("/api/v1/work-items", params={"priority": "high"})
    assert r.status_code == 200


def test_list_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.get("/api/v1/work-items")
    assert r.status_code == 401


# --- Create ---


def test_create_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id, title="Pod CrashLoop", priority="high")
    assert item["title"] == "Pod CrashLoop"
    assert item["status"] == "ready"
    assert item["priority"] == "high"
    assert item["cluster_id"] == cluster_id


def test_create_work_item_defaults(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    assert item["priority"] == "medium"
    assert item["owner_id"] is None
    assert item["blocked_reason"] is None


def test_create_requires_auth(unauthed_client: TestClient) -> None:
    r = unauthed_client.post("/api/v1/work-items", json={
        "cluster_id": str(uuid.uuid4()), "title": "test",
    })
    assert r.status_code == 401


# --- Get ---


def test_get_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    created = _create_work_item(authed_client, cluster_id)
    r = authed_client.get(f"/api/v1/work-items/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_nonexistent(authed_client: TestClient) -> None:
    r = authed_client.get(f"/api/v1/work-items/{uuid.uuid4()}")
    assert r.status_code == 404


# --- Status Transitions ---


def test_start_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/start")
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"


def test_complete_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    authed_client.post(f"/api/v1/work-items/{item['id']}/start")
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/complete")
    assert r.status_code == 200
    assert r.json()["status"] == "done"


def test_block_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    authed_client.post(f"/api/v1/work-items/{item['id']}/start")
    r = authed_client.post(
        f"/api/v1/work-items/{item['id']}/block",
        json={"reason": "Waiting for PVC"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    assert r.json()["blocked_reason"] == "Waiting for PVC"


def test_invalid_transition_returns_409(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/block", json={"reason": "test"})
    assert r.status_code == 409


def test_start_nonexistent_returns_404(authed_client: TestClient) -> None:
    r = authed_client.post(f"/api/v1/work-items/{uuid.uuid4()}/start")
    assert r.status_code == 404


# --- Take / Release ---


def test_take_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/take")
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["owner_id"] is not None


def test_release_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    authed_client.post(f"/api/v1/work-items/{item['id']}/take")
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/release")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
    assert r.json()["owner_id"] is None


def test_release_from_ready_returns_409(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/release")
    assert r.status_code == 409


# --- Reset ---


def test_reset_work_item(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    authed_client.post(f"/api/v1/work-items/{item['id']}/take")
    r = authed_client.post(f"/api/v1/work-items/{item['id']}/reset")
    assert r.status_code == 200
    refreshed = authed_client.get(f"/api/v1/work-items/{item['id']}").json()
    assert refreshed["status"] == "ready"
    assert refreshed["owner_id"] is None
    assert refreshed["artifact_refs"] == {}


def test_reset_nonexistent_returns_404(authed_client: TestClient) -> None:
    r = authed_client.post(f"/api/v1/work-items/{uuid.uuid4()}/reset")
    assert r.status_code == 404


# --- Annotations ---


def test_update_annotations(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.patch(
        f"/api/v1/work-items/{item['id']}/annotations",
        json={"annotations": {"team": "platform", "env": "prod"}},
    )
    assert r.status_code == 200
    assert r.json()["annotations"]["team"] == "platform"


def test_annotations_merge(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    authed_client.patch(
        f"/api/v1/work-items/{item['id']}/annotations",
        json={"annotations": {"key1": "val1"}},
    )
    r = authed_client.patch(
        f"/api/v1/work-items/{item['id']}/annotations",
        json={"annotations": {"key2": "val2"}},
    )
    assert r.json()["annotations"]["key1"] == "val1"
    assert r.json()["annotations"]["key2"] == "val2"


# --- Bulk ---


def test_bulk_action(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    items = [_create_work_item(authed_client, cluster_id) for _ in range(3)]
    ids = [i["id"] for i in items]
    r = authed_client.post("/api/v1/work-items/bulk", json={"ids": ids, "action": "in_progress"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert all(r["status"] == "ok" for r in results)


def test_bulk_action_partial_failure(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.post("/api/v1/work-items/bulk", json={
        "ids": [item["id"], str(uuid.uuid4())],
        "action": "in_progress",
    })
    assert r.status_code == 200
    results = r.json()["results"]
    statuses = {r["id"]: r["status"] for r in results}
    assert statuses[item["id"]] == "ok"


# --- Events / Investigation ---


def test_get_work_item_events(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.get(f"/api/v1/work-items/{item['id']}/events")
    assert r.status_code == 200
    assert "items" in r.json()


def test_get_investigation_no_results(authed_client: TestClient) -> None:
    cluster_id = _create_cluster_with_binding(authed_client)
    item = _create_work_item(authed_client, cluster_id)
    r = authed_client.get(f"/api/v1/work-items/{item['id']}/investigation")
    assert r.status_code == 200
    assert r.json()["has_investigation"] is False
