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

    # Cleanup seeded data — clear FK refs before deleting principal
    pid = UUID("00000000-0000-0000-0000-000000000010")
    async with _factory() as s:
        from sqlalchemy import text
        await s.execute(text(
            "UPDATE work_items SET owner_id = NULL WHERE owner_id = :pid"
        ), {"pid": str(pid)})
        await s.execute(WorkItem.__table__.delete().where(WorkItem.id.in_([wi1_id, wi2_id])))
        await s.execute(
            ClusterIdentityBinding.__table__.delete().where(
                ClusterIdentityBinding.principal_id == pid
            )
        )
        from pinky_api.models.issue import Issue
        await s.execute(Issue.__table__.delete().where(Issue.cluster_id == cluster_id))
        await s.execute(ClusterRegistry.__table__.delete().where(ClusterRegistry.id == cluster_id))
        await s.execute(
            Principal.__table__.delete().where(Principal.id == pid)
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
async def test_take_transitions_to_in_progress(seeded) -> None:
    client, _, wi1_id, _ = seeded
    response = await client.post(f"/api/v1/work-items/{wi1_id}/take")
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_invalid_transition_returns_409(seeded) -> None:
    client, _, _, wi2_id = seeded
    response = await client.post(f"/api/v1/work-items/{wi2_id}/block", json={"reason": "test"})
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_full_lifecycle_ready_to_done(seeded) -> None:
    client, _, wi1_id, _ = seeded

    r = await client.post(f"/api/v1/work-items/{wi1_id}/take")
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
    await client.post(f"/api/v1/work-items/{wi1_id}/take")
    r = await client.post(f"/api/v1/work-items/{wi1_id}/block", json={"reason": "waiting on vendor"})
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    assert r.json()["blocked_reason"] == "waiting on vendor"


@pytest.mark.asyncio
async def test_block_then_start_clears_reason(seeded) -> None:
    client, _, wi1_id, _ = seeded
    await client.post(f"/api/v1/work-items/{wi1_id}/take")
    await client.post(f"/api/v1/work-items/{wi1_id}/block", json={"reason": "blocked"})
    r = await client.post(f"/api/v1/work-items/{wi1_id}/start")
    assert r.json()["status"] == "in_progress"
    assert r.json()["blocked_reason"] is None


@pytest.mark.asyncio
async def test_bulk_start(seeded) -> None:
    client, _, wi1_id, wi2_id = seeded
    r = await client.post("/api/v1/work-items/bulk", json={"ids": [wi1_id, wi2_id], "action": "in_progress"})
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


@pytest.mark.asyncio
async def test_history_shows_events_from_mutations(seeded) -> None:
    """Verify that actions (take, complete) produce domain events visible via the History API."""
    client, _, wi1_id, _ = seeded

    await client.post(f"/api/v1/work-items/{wi1_id}/take")
    await client.post(f"/api/v1/work-items/{wi1_id}/complete")

    r = await client.get("/api/v1/history")
    assert r.status_code == 200
    items = r.json()["items"]
    event_types = {e["event_type"] for e in items}
    assert "work_item.taken" in event_types
    assert "work_item.completed" in event_types

    for event in items:
        assert event["id"]
        assert event["event_type"]
        assert event["aggregate_type"]
        assert event["aggregate_id"]
        assert event["occurred_at"]

    # Cleanup domain events
    from pinky_api.models.extensibility import DomainEvent
    async with _factory() as s:
        await s.execute(DomainEvent.__table__.delete().where(DomainEvent.aggregate_id == UUID(wi1_id)))
        await s.commit()


@pytest.mark.asyncio
async def test_history_enrichment(seeded) -> None:
    """Verify history events include description, actor name, and cluster name."""
    client, cluster_id, wi1_id, _ = seeded

    await client.post(f"/api/v1/work-items/{wi1_id}/take")

    r = await client.get("/api/v1/history")
    assert r.status_code == 200
    taken = next((e for e in r.json()["items"] if e["event_type"] == "work_item.taken"), None)
    assert taken is not None
    assert taken["description"]
    assert taken["principal_display_name"] is not None
    assert taken["cluster_display_name"] == "int-test-cluster"

    from pinky_api.models.extensibility import DomainEvent
    async with _factory() as s:
        await s.execute(DomainEvent.__table__.delete().where(DomainEvent.aggregate_id == UUID(wi1_id)))
        await s.commit()


@pytest.mark.asyncio
async def test_cluster_display_name_in_work_items(seeded) -> None:
    """Verify work items include cluster_display_name from API."""
    client, cluster_id, wi1_id, _ = seeded

    r = await client.get(f"/api/v1/work-items/{wi1_id}")
    assert r.status_code == 200
    assert r.json()["cluster_display_name"] == "int-test-cluster"

    r = await client.get("/api/v1/work-items")
    assert r.status_code == 200
    item = next((i for i in r.json()["items"] if i["id"] == wi1_id), None)
    assert item is not None
    assert item["cluster_display_name"] == "int-test-cluster"


@pytest.mark.asyncio
async def test_work_items_exclude_done_by_default(seeded) -> None:
    """Verify done tasks are excluded from the default list."""
    client, _, wi1_id, wi2_id = seeded

    await client.post(f"/api/v1/work-items/{wi1_id}/take")
    await client.post(f"/api/v1/work-items/{wi1_id}/complete")

    r = await client.get("/api/v1/work-items")
    assert r.status_code == 200
    ids = {i["id"] for i in r.json()["items"]}
    assert wi1_id not in ids
    assert wi2_id in ids

    r = await client.get("/api/v1/work-items?status=done")
    assert r.status_code == 200
    ids = {i["id"] for i in r.json()["items"]}
    assert wi1_id in ids


@pytest.mark.asyncio
async def test_pagination_cursor(seeded) -> None:
    """Verify cursor-based pagination returns has_more and next_cursor."""
    client, *_ = seeded

    r = await client.get("/api/v1/work-items?limit=1")
    assert r.status_code == 200
    body = r.json()
    assert len(body["items"]) == 1
    assert body["has_more"] is True
    assert body["next_cursor"] is not None
    assert body["total_count"] >= 2


@pytest.mark.asyncio
async def test_history_export_csv(seeded) -> None:
    """Verify CSV export returns proper content-type and data."""
    client, _, wi1_id, _ = seeded

    await client.post(f"/api/v1/work-items/{wi1_id}/take")

    r = await client.get("/api/v1/history/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    assert "pinky-history.csv" in r.headers.get("content-disposition", "")
    lines = r.text.strip().split("\n")
    assert len(lines) >= 2
    assert "Time" in lines[0]

    from pinky_api.models.extensibility import DomainEvent
    async with _factory() as s:
        await s.execute(DomainEvent.__table__.delete().where(DomainEvent.aggregate_id == UUID(wi1_id)))
        await s.commit()
