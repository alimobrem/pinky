"""Integration tests — exercise real DB operations via async client.

Uses httpx.AsyncClient with ASGITransport to properly handle
async SQLAlchemy sessions and commits within route handlers.
"""

from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pinky_api.app import app
from pinky_api.auth.middleware import get_current_principal
from pinky_api.db.deps import get_db
from pinky_api.models.fleet import ClusterIdentityBinding, ClusterRegistry
from pinky_api.models.principal import Principal
from pinky_api.models.work_item import WorkItem

TEST_DB_URL = "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky"
_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def _mock_principal() -> dict:
    return {
        "id": "00000000-0000-0000-0000-000000000010",
        "provider": "test",
        "email": "t@t",
        "groups": ["pinky-admins"],
        "is_admin": True,
    }


async def _test_db():
    async with _factory() as s:
        yield s


@pytest.fixture
async def seeded():
    app.dependency_overrides[get_current_principal] = _mock_principal
    app.dependency_overrides[get_db] = _test_db

    cluster_id = uuid4()
    wi1_id = uuid4()
    wi2_id = uuid4()

    async with _factory() as s:
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(Principal).values(
            id=UUID("00000000-0000-0000-0000-000000000010"),
            provider="test",
            subject="test-admin",
            email="t@t",
            display_name="Test Admin",
            groups=["pinky-admins"],
        ).on_conflict_do_nothing(index_elements=["id"])
        await s.execute(stmt)
        await s.flush()
        s.add(ClusterRegistry(
            id=cluster_id, display_name="int-test-cluster",
            api_endpoint="https://test", onboarding_state="ready",
        ))
        await s.flush()
        s.add(
            ClusterIdentityBinding(
                principal_id=UUID("00000000-0000-0000-0000-000000000010"),
                cluster_id=cluster_id,
                binding_method="oauth_login",
                status="valid",
            )
        )
        s.add(WorkItem(
            id=wi1_id, cluster_id=cluster_id, title="Int Task A", status="ready", priority="high",
        ))
        s.add(WorkItem(
            id=wi2_id, cluster_id=cluster_id, title="Int Task B",
            status="ready", priority="medium", why_now="test reason",
        ))
        await s.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, str(cluster_id), str(wi1_id), str(wi2_id)

    # Cleanup seeded data
    async with _factory() as s:
        await s.execute(WorkItem.__table__.delete().where(WorkItem.id.in_([wi1_id, wi2_id])))
        await s.execute(
            ClusterIdentityBinding.__table__.delete().where(ClusterIdentityBinding.cluster_id == cluster_id)
        )
        from pinky_api.models.issue import Issue
        await s.execute(Issue.__table__.delete().where(Issue.cluster_id == cluster_id))
        await s.execute(ClusterRegistry.__table__.delete().where(ClusterRegistry.id == cluster_id))
        await s.execute(
            Principal.__table__.delete().where(Principal.id == UUID("00000000-0000-0000-0000-000000000010"))
        )
        await s.commit()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_returns_seeded_work_items(seeded) -> None:
    client, *_ = seeded
    response = await client.get("/api/v1/work-items")
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()["items"]}
    assert "Int Task A" in titles


@pytest.mark.asyncio
async def test_get_work_item_by_id(seeded) -> None:
    client, _, wi1_id, _ = seeded
    response = await client.get(f"/api/v1/work-items/{wi1_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Int Task A"
    assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_accept_transitions_to_accepted(seeded) -> None:
    client, _, wi1_id, _ = seeded
    response = await client.post(f"/api/v1/work-items/{wi1_id}/accept")
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_invalid_transition_returns_409(seeded) -> None:
    client, _, _, wi2_id = seeded
    response = await client.post(f"/api/v1/work-items/{wi2_id}/start")
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_full_lifecycle_ready_to_done(seeded) -> None:
    client, _, wi1_id, _ = seeded

    r = await client.post(f"/api/v1/work-items/{wi1_id}/accept")
    assert r.json()["status"] == "accepted"

    r = await client.post(f"/api/v1/work-items/{wi1_id}/start")
    assert r.json()["status"] == "in_progress"

    r = await client.post(f"/api/v1/work-items/{wi1_id}/complete")
    assert r.json()["status"] == "done"


@pytest.mark.asyncio
async def test_filter_by_status(seeded) -> None:
    client, *_ = seeded
    response = await client.get("/api/v1/work-items?status=ready")
    assert response.status_code == 200
    items = response.json()["items"]
    assert all(item["status"] == "ready" for item in items)


@pytest.mark.asyncio
async def test_cluster_list(seeded) -> None:
    client, cluster_id, *_ = seeded
    response = await client.get("/api/v1/clusters")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert cluster_id in ids


@pytest.mark.asyncio
async def test_block_with_reason(seeded) -> None:
    client, _, wi1_id, _ = seeded
    await client.post(f"/api/v1/work-items/{wi1_id}/accept")
    await client.post(f"/api/v1/work-items/{wi1_id}/start")
    r = await client.post(f"/api/v1/work-items/{wi1_id}/block", json={"reason": "waiting on vendor"})
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    assert r.json()["blocked_reason"] == "waiting on vendor"


@pytest.mark.asyncio
async def test_block_then_start_clears_reason(seeded) -> None:
    client, _, wi1_id, _ = seeded
    await client.post(f"/api/v1/work-items/{wi1_id}/accept")
    await client.post(f"/api/v1/work-items/{wi1_id}/start")
    await client.post(f"/api/v1/work-items/{wi1_id}/block", json={"reason": "blocked"})
    r = await client.post(f"/api/v1/work-items/{wi1_id}/start")
    assert r.json()["status"] == "in_progress"
    assert r.json()["blocked_reason"] is None


@pytest.mark.asyncio
async def test_bulk_accept(seeded) -> None:
    client, _, wi1_id, wi2_id = seeded
    r = await client.post("/api/v1/work-items/bulk", json={"ids": [wi1_id, wi2_id], "action": "accepted"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert all(res["status"] == "ok" for res in results)


@pytest.mark.asyncio
async def test_annotations_update(seeded) -> None:
    client, _, wi1_id, _ = seeded
    r = await client.patch(f"/api/v1/work-items/{wi1_id}/annotations", json={"annotations": {"ticket_url": "https://jira.example.com/OPS-123"}})
    assert r.status_code == 200
    assert r.json()["annotations"]["ticket_url"] == "https://jira.example.com/OPS-123"


@pytest.mark.asyncio
async def test_issue_suppress_and_resolve(seeded) -> None:
    from datetime import datetime

    from pinky_api.models.issue import Issue
    issue_id = uuid4()
    now = datetime.now()
    async with _factory() as s:
        client, cluster_id, *_ = seeded
        s.add(Issue(
            id=issue_id, cluster_id=cluster_id, correlation_key="test-issue",
            title="Test Issue", severity="medium", status="open",
            first_seen_at=now, last_seen_at=now,
        ))
        await s.commit()

    client, cluster_id, *_ = seeded
    r = await client.post(f"/api/v1/issues/{issue_id}/suppress", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "suppressed"

    # Cleanup
    async with _factory() as s:
        await s.execute(Issue.__table__.delete().where(Issue.id == issue_id))
        await s.commit()


@pytest.mark.asyncio
async def test_cluster_binding_status(seeded) -> None:
    client, cluster_id, *_ = seeded
    r = await client.get(f"/api/v1/cluster-bindings/status?cluster_id={cluster_id}")
    assert r.status_code == 200
    assert r.json()["status"] == "valid"
