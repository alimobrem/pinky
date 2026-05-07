"""Comprehensive action lifecycle integration tests.

Seeds real data in Postgres via direct SQL (using the async session factory)
and exercises state transitions, CRUD operations, and authorization via
the httpx async client pattern from test_integration.py.
"""

from datetime import datetime
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from pinky_api.app import app
from pinky_api.auth.middleware import get_current_principal
from pinky_api.db.deps import get_db
from pinky_api.models.fleet import ClusterIdentityBinding, ClusterRegistry
from pinky_api.models.issue import Issue
from pinky_api.models.principal import Principal
from pinky_api.models.work_item import WorkItem

TEST_DB_URL = "postgresql+asyncpg://pinky:pinky@localhost:5432/pinky"
_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_factory = async_sessionmaker(_engine, expire_on_commit=False)

ADMIN_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-aaaaaaaaa010")
NON_ADMIN_PRINCIPAL_ID = UUID("00000000-0000-0000-0000-aaaaaaaaa011")


async def _admin_principal() -> dict:
    return {
        "id": str(ADMIN_PRINCIPAL_ID),
        "provider": "test",
        "email": "admin@lifecycle.test",
        "groups": ["pinky-admins"],
        "is_admin": True,
    }


async def _non_admin_principal() -> dict:
    return {
        "id": str(NON_ADMIN_PRINCIPAL_ID),
        "provider": "test",
        "email": "user@lifecycle.test",
        "groups": ["users"],
        "is_admin": False,
    }


async def _test_db():
    async with _factory() as s:
        yield s


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def lifecycle_env():
    """Seed a full environment: principal, cluster, binding, work items, issue."""
    app.dependency_overrides[get_current_principal] = _admin_principal
    app.dependency_overrides[get_db] = _test_db

    cluster_id = uuid4()
    wi_ids = [uuid4() for _ in range(4)]
    issue_id = uuid4()
    now = datetime.utcnow()

    async with _factory() as s:
        # Principal
        s.add(Principal(
            id=ADMIN_PRINCIPAL_ID, provider="test", subject="lifecycle-admin",
            email="admin@lifecycle.test", display_name="Lifecycle Admin",
            groups=["pinky-admins"],
        ))
        # Cluster
        s.add(ClusterRegistry(
            id=cluster_id, display_name="lifecycle-cluster",
            api_endpoint="https://lifecycle:6443", onboarding_state="ready",
        ))
        await s.flush()
        # Binding (required for write access)
        s.add(ClusterIdentityBinding(
            principal_id=ADMIN_PRINCIPAL_ID, cluster_id=cluster_id,
            binding_method="oauth_login", status="valid",
        ))
        # Work items in various states
        s.add(WorkItem(id=wi_ids[0], cluster_id=cluster_id, title="WI-Ready-A", status="ready", priority="high"))
        s.add(WorkItem(id=wi_ids[1], cluster_id=cluster_id, title="WI-Ready-B", status="ready", priority="medium"))
        s.add(WorkItem(id=wi_ids[2], cluster_id=cluster_id, title="WI-Ready-C", status="ready", priority="low"))
        s.add(WorkItem(id=wi_ids[3], cluster_id=cluster_id, title="WI-Ready-D", status="ready", priority="high"))
        # Issue
        s.add(Issue(
            id=issue_id, cluster_id=cluster_id, correlation_key="lifecycle-issue-1",
            title="Lifecycle Issue", severity="high", status="open",
            first_seen_at=now, last_seen_at=now,
        ))
        await s.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "cluster_id": str(cluster_id),
            "wi_ids": [str(wid) for wid in wi_ids],
            "issue_id": str(issue_id),
        }

    # Cleanup
    async with _factory() as s:
        for wid in wi_ids:
            await s.execute(WorkItem.__table__.delete().where(WorkItem.id == wid))
        await s.execute(Issue.__table__.delete().where(Issue.id == issue_id))
        await s.execute(
            ClusterIdentityBinding.__table__.delete().where(ClusterIdentityBinding.cluster_id == cluster_id)
        )
        await s.execute(ClusterRegistry.__table__.delete().where(ClusterRegistry.id == cluster_id))
        await s.execute(Principal.__table__.delete().where(Principal.id == ADMIN_PRINCIPAL_ID))
        await s.commit()

    app.dependency_overrides.clear()


@pytest.fixture
async def non_admin_env():
    """Env with non-admin principal — no cluster binding, so writes should fail."""
    app.dependency_overrides[get_current_principal] = _non_admin_principal
    app.dependency_overrides[get_db] = _test_db

    cluster_id = uuid4()
    wi_id = uuid4()

    async with _factory() as s:
        s.add(Principal(
            id=NON_ADMIN_PRINCIPAL_ID, provider="test", subject="lifecycle-user",
            email="user@lifecycle.test", display_name="Lifecycle User",
            groups=["users"],
        ))
        s.add(ClusterRegistry(
            id=cluster_id, display_name="non-admin-cluster",
            api_endpoint="https://nonadmin:6443", onboarding_state="ready",
        ))
        await s.flush()
        # Binding for the non-admin principal (needed for read access)
        s.add(ClusterIdentityBinding(
            principal_id=NON_ADMIN_PRINCIPAL_ID, cluster_id=cluster_id,
            binding_method="oauth_login", status="valid",
        ))
        s.add(WorkItem(id=wi_id, cluster_id=cluster_id, title="WI-NonAdmin", status="ready", priority="medium"))
        await s.commit()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield {
            "client": client,
            "cluster_id": str(cluster_id),
            "wi_id": str(wi_id),
        }

    async with _factory() as s:
        await s.execute(WorkItem.__table__.delete().where(WorkItem.id == wi_id))
        await s.execute(
            ClusterIdentityBinding.__table__.delete().where(ClusterIdentityBinding.cluster_id == cluster_id)
        )
        await s.execute(ClusterRegistry.__table__.delete().where(ClusterRegistry.id == cluster_id))
        await s.execute(Principal.__table__.delete().where(Principal.id == NON_ADMIN_PRINCIPAL_ID))
        await s.commit()

    app.dependency_overrides.clear()


# ===========================================================================
# Work Item Lifecycle — Happy Paths
# ===========================================================================


@pytest.mark.asyncio
class TestWorkItemLifecycle:
    async def test_take_starts_and_assigns(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]

        r = await c.post(f"/api/v1/work-items/{wid}/take")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "in_progress"
        assert body["owner_id"] == str(ADMIN_PRINCIPAL_ID)

    async def test_full_lifecycle_take_to_done(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][1]

        r = await c.post(f"/api/v1/work-items/{wid}/take")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"

        r = await c.post(f"/api/v1/work-items/{wid}/complete")
        assert r.status_code == 200
        assert r.json()["status"] == "done"

        r = await c.get(f"/api/v1/work-items/{wid}")
        assert r.json()["status"] == "done"

    async def test_block_unblock_complete(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][2]

        await c.post(f"/api/v1/work-items/{wid}/take")

        r = await c.post(f"/api/v1/work-items/{wid}/block", json={"reason": "waiting on CR"})
        assert r.status_code == 200
        assert r.json()["status"] == "blocked"
        assert r.json()["blocked_reason"] == "waiting on CR"

        r = await c.post(f"/api/v1/work-items/{wid}/start")
        assert r.status_code == 200
        assert r.json()["status"] == "in_progress"
        assert r.json()["blocked_reason"] is None

        r = await c.post(f"/api/v1/work-items/{wid}/complete")
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    async def test_blocked_to_done(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][3]

        await c.post(f"/api/v1/work-items/{wid}/take")
        await c.post(f"/api/v1/work-items/{wid}/block", json={"reason": "blocked"})

        r = await c.post(f"/api/v1/work-items/{wid}/complete")
        assert r.status_code == 200
        assert r.json()["status"] == "done"

    async def test_release_returns_to_ready(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]

        await c.post(f"/api/v1/work-items/{wid}/take")

        r = await c.post(f"/api/v1/work-items/{wid}/release")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ready"
        assert body["owner_id"] is None

    async def test_release_from_blocked(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][1]

        await c.post(f"/api/v1/work-items/{wid}/take")
        await c.post(f"/api/v1/work-items/{wid}/block", json={"reason": "waiting"})

        r = await c.post(f"/api/v1/work-items/{wid}/release")
        assert r.status_code == 200
        assert r.json()["status"] == "ready"
        assert r.json()["owner_id"] is None


# ===========================================================================
# Work Item Lifecycle — Invalid Transitions
# ===========================================================================


@pytest.mark.asyncio
class TestWorkItemInvalidTransitions:
    async def test_ready_cannot_complete(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]

        r = await c.post(f"/api/v1/work-items/{wid}/complete")
        assert r.status_code == 409

    async def test_ready_cannot_block(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]

        r = await c.post(f"/api/v1/work-items/{wid}/block", json={"reason": "nope"})
        assert r.status_code == 409

    async def test_done_cannot_transition(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][1]

        await c.post(f"/api/v1/work-items/{wid}/take")
        await c.post(f"/api/v1/work-items/{wid}/complete")

        for endpoint in ["start", "complete"]:
            r = await c.post(f"/api/v1/work-items/{wid}/{endpoint}")
            assert r.status_code == 409, f"Expected 409 for {endpoint} on done item"

    async def test_release_from_ready_fails(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][2]

        r = await c.post(f"/api/v1/work-items/{wid}/release")
        assert r.status_code == 409

    async def test_release_from_done_fails(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][3]

        await c.post(f"/api/v1/work-items/{wid}/take")
        await c.post(f"/api/v1/work-items/{wid}/complete")

        r = await c.post(f"/api/v1/work-items/{wid}/release")
        assert r.status_code == 409

    async def test_get_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())
        r = await c.get(f"/api/v1/work-items/{fake_id}")
        assert r.status_code == 404


# ===========================================================================
# Bulk Actions
# ===========================================================================


@pytest.mark.asyncio
class TestBulkActions:
    async def test_bulk_start_multiple(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        ids = lifecycle_env["wi_ids"][:2]

        r = await c.post("/api/v1/work-items/bulk", json={"ids": ids, "action": "in_progress"})
        assert r.status_code == 200
        results = r.json()["results"]
        assert len(results) == 2
        assert all(res["status"] == "ok" for res in results)

    async def test_bulk_with_invalid_transition(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid_ready = lifecycle_env["wi_ids"][2]
        wid_done = lifecycle_env["wi_ids"][3]

        await c.post(f"/api/v1/work-items/{wid_done}/take")
        await c.post(f"/api/v1/work-items/{wid_done}/complete")

        r = await c.post("/api/v1/work-items/bulk", json={
            "ids": [wid_ready, wid_done], "action": "in_progress",
        })
        assert r.status_code == 200
        results = {res["id"]: res["status"] for res in r.json()["results"]}
        assert results[wid_ready] == "ok"
        assert results[wid_done] == "error"

    async def test_bulk_with_nonexistent_id(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())

        r = await c.post("/api/v1/work-items/bulk", json={"ids": [fake_id], "action": "in_progress"})
        assert r.status_code == 200
        assert r.json()["results"][0]["status"] == "not_found"


# ===========================================================================
# Annotations
# ===========================================================================


@pytest.mark.asyncio
class TestAnnotations:
    async def test_set_and_merge_annotations(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]

        # Set initial annotation
        r = await c.patch(f"/api/v1/work-items/{wid}/annotations", json={
            "annotations": {"ticket_url": "https://jira.example.com/OPS-1"},
        })
        assert r.status_code == 200
        assert r.json()["annotations"]["ticket_url"] == "https://jira.example.com/OPS-1"

        # Merge second annotation
        r = await c.patch(f"/api/v1/work-items/{wid}/annotations", json={
            "annotations": {"runbook": "https://wiki.example.com/rb-1"},
        })
        assert r.status_code == 200
        annotations = r.json()["annotations"]
        assert annotations["ticket_url"] == "https://jira.example.com/OPS-1"
        assert annotations["runbook"] == "https://wiki.example.com/rb-1"

    async def test_annotations_on_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())
        r = await c.patch(f"/api/v1/work-items/{fake_id}/annotations", json={
            "annotations": {"key": "val"},
        })
        assert r.status_code == 404


# ===========================================================================
# Reassign
# ===========================================================================


@pytest.mark.asyncio
class TestReassign:
    async def test_reassign_sets_owner(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]
        assignee_id = str(ADMIN_PRINCIPAL_ID)

        r = await c.post(f"/api/v1/work-items/{wid}/reassign?assignee_id={assignee_id}")
        assert r.status_code == 200
        assert r.json()["owner_id"] == assignee_id

    async def test_reassign_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())
        r = await c.post(f"/api/v1/work-items/{fake_id}/reassign?assignee_id={str(uuid4())}")
        assert r.status_code == 404


# ===========================================================================
# Issue Lifecycle
# ===========================================================================


@pytest.mark.asyncio
class TestIssueLifecycle:
    async def test_suppress_issue(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]

        r = await c.post(f"/api/v1/issues/{issue_id}/suppress", json={})
        assert r.status_code == 200
        assert r.json()["status"] == "suppressed"

        # Verify via GET
        r = await c.get(f"/api/v1/issues/{issue_id}")
        assert r.json()["status"] == "suppressed"

    async def test_resolve_issue(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]

        r = await c.post(f"/api/v1/issues/{issue_id}/resolve")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "resolved"
        assert body["resolved_at"] is not None

    async def test_suppress_with_until(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]

        until = "2099-12-31T23:59:59"
        r = await c.post(f"/api/v1/issues/{issue_id}/suppress", json={"until": until})
        assert r.status_code == 200
        assert r.json()["status"] == "suppressed"
        assert r.json()["suppressed_until"] is not None

    async def test_suppress_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())
        r = await c.post(f"/api/v1/issues/{fake_id}/suppress", json={})
        assert r.status_code == 404

    async def test_resolve_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        fake_id = str(uuid4())
        r = await c.post(f"/api/v1/issues/{fake_id}/resolve")
        assert r.status_code == 404

    async def test_issue_list_returns_seeded(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.get("/api/v1/issues")
        assert r.status_code == 200
        titles = {i["title"] for i in r.json()["items"]}
        assert "Lifecycle Issue" in titles

    async def test_issue_get_by_id(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]
        r = await c.get(f"/api/v1/issues/{issue_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "Lifecycle Issue"
        assert body["severity"] == "high"
        assert body["status"] == "open"

    async def test_issue_get_nonexistent_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.get(f"/api/v1/issues/{uuid4()}")
        assert r.status_code == 404


# ===========================================================================
# Cluster CRUD
# ===========================================================================


@pytest.mark.asyncio
class TestClusterCRUD:
    async def test_create_list_delete_cluster(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]

        # Create
        r = await c.post("/api/v1/clusters", json={
            "display_name": "ephemeral-test-cluster",
            "api_endpoint": "https://ephemeral:6443",
        })
        assert r.status_code == 201
        created = r.json()
        new_id = created["id"]
        assert created["display_name"] == "ephemeral-test-cluster"

        # List — verify it appears
        r = await c.get("/api/v1/clusters")
        assert r.status_code == 200
        ids = {item["id"] for item in r.json()["items"]}
        assert new_id in ids

        # Delete
        r = await c.delete(f"/api/v1/clusters/{new_id}")
        assert r.status_code == 204

        # Verify soft-delete: cluster still listed but state changed to offboarded
        r = await c.get("/api/v1/clusters")
        items = r.json()["items"]
        deleted_cluster = next((i for i in items if i["id"] == new_id), None)
        assert deleted_cluster is not None
        assert deleted_cluster["onboarding_state"] == "offboarded"

    async def test_delete_nonexistent_cluster_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.delete(f"/api/v1/clusters/{uuid4()}")
        assert r.status_code == 404

    async def test_create_cluster_returns_expected_fields(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.post("/api/v1/clusters", json={
            "display_name": "fields-check",
            "api_endpoint": "https://fields:6443",
        })
        assert r.status_code == 201
        body = r.json()
        for field in ("id", "display_name", "api_endpoint", "onboarding_state", "created_at"):
            assert field in body, f"Missing field: {field}"

        # Cleanup
        await c.delete(f"/api/v1/clusters/{body['id']}")


# ===========================================================================
# Cluster CRUD — Non-Admin Authorization
# ===========================================================================


@pytest.mark.asyncio
class TestClusterCRUDNonAdmin:
    async def test_non_admin_cannot_create_cluster(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.post("/api/v1/clusters", json={
            "display_name": "should-fail",
            "api_endpoint": "https://fail:6443",
        })
        assert r.status_code == 403

    async def test_non_admin_cannot_delete_cluster(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        cluster_id = non_admin_env["cluster_id"]
        r = await c.delete(f"/api/v1/clusters/{cluster_id}")
        assert r.status_code == 403

    async def test_non_admin_can_list_clusters(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.get("/api/v1/clusters")
        assert r.status_code == 200

    async def test_non_admin_can_read_work_item(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        wid = non_admin_env["wi_id"]
        r = await c.get(f"/api/v1/work-items/{wid}")
        assert r.status_code == 200
        assert r.json()["title"] == "WI-NonAdmin"


# ===========================================================================
# Definition CRUD
# ===========================================================================


@pytest.mark.asyncio
class TestDefinitionCRUD:
    async def test_create_list_get_delete_definition(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]

        # Create
        r = await c.post("/api/v1/definitions", json={
            "kind": "scanner",
            "name": "lifecycle-test-scanner",
            "version": "1.0.0",
            "frontmatter": {"schedule": "*/5 * * * *"},
            "body": "# Lifecycle Test Scanner\nChecks pod health.",
        })
        assert r.status_code == 201
        body = r.json()
        assert body["kind"] == "scanner"
        assert body["name"] == "lifecycle-test-scanner"
        assert body["version"] == "1.0.0"
        assert body["frontmatter"]["schedule"] == "*/5 * * * *"
        assert body["enabled"] is True

        # List
        r = await c.get("/api/v1/definitions?kind=scanner")
        assert r.status_code == 200
        names = {d["name"] for d in r.json()["items"]}
        assert "lifecycle-test-scanner" in names

        # Get by kind/name
        r = await c.get("/api/v1/definitions/scanner/lifecycle-test-scanner")
        assert r.status_code == 200
        assert r.json()["body"] == "# Lifecycle Test Scanner\nChecks pod health."

        # Delete
        r = await c.delete("/api/v1/definitions/scanner/lifecycle-test-scanner")
        assert r.status_code == 204

        # Verify gone
        r = await c.get("/api/v1/definitions/scanner/lifecycle-test-scanner")
        assert r.status_code == 404

    async def test_delete_nonexistent_definition_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.delete("/api/v1/definitions/scanner/does-not-exist")
        assert r.status_code == 404

    async def test_upsert_updates_existing_definition(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]

        # Create v1
        await c.post("/api/v1/definitions", json={
            "kind": "tool",
            "name": "lifecycle-upsert-tool",
            "version": "1.0.0",
            "frontmatter": {"timeout": 30},
            "body": "v1 body",
        })

        # Upsert v2
        r = await c.post("/api/v1/definitions", json={
            "kind": "tool",
            "name": "lifecycle-upsert-tool",
            "version": "2.0.0",
            "frontmatter": {"timeout": 60},
            "body": "v2 body",
        })
        assert r.status_code == 201
        assert r.json()["version"] == "2.0.0"
        assert r.json()["body"] == "v2 body"

        # Cleanup
        await c.delete("/api/v1/definitions/tool/lifecycle-upsert-tool")


# ===========================================================================
# Definition CRUD — Non-Admin Authorization
# ===========================================================================


@pytest.mark.asyncio
class TestDefinitionCRUDNonAdmin:
    async def test_non_admin_cannot_create_definition(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.post("/api/v1/definitions", json={
            "kind": "scanner",
            "name": "should-fail",
            "version": "1.0.0",
            "frontmatter": {},
            "body": "nope",
        })
        assert r.status_code == 403

    async def test_non_admin_cannot_delete_definition(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.delete("/api/v1/definitions/scanner/anything")
        assert r.status_code in (403, 404)  # 403 before 404 check

    async def test_non_admin_can_list_definitions(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.get("/api/v1/definitions")
        assert r.status_code == 200


# ===========================================================================
# Webhook CRUD
# ===========================================================================


@pytest.mark.asyncio
class TestWebhookCRUD:
    async def test_create_list_delete_webhook(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]

        # Create
        r = await c.post("/api/v1/webhook-subscriptions", json={
            "name": "lifecycle-hook",
            "url": "https://hooks.example.com/lifecycle",
            "event_patterns": ["work_item.*", "issue.*"],
            "formatter": "generic",
        })
        assert r.status_code == 201
        body = r.json()
        hook_id = body["id"]
        assert body["name"] == "lifecycle-hook"
        assert body["url"] == "https://hooks.example.com/lifecycle"
        assert "work_item.*" in body["event_patterns"]
        assert body["enabled"] is True

        # List
        r = await c.get("/api/v1/webhook-subscriptions")
        assert r.status_code == 200
        ids = {s["id"] for s in r.json()["items"]}
        assert hook_id in ids

        # Delete
        r = await c.delete(f"/api/v1/webhook-subscriptions/{hook_id}")
        assert r.status_code == 204

        # Verify gone
        r = await c.get("/api/v1/webhook-subscriptions")
        ids = {s["id"] for s in r.json()["items"]}
        assert hook_id not in ids

    async def test_delete_nonexistent_webhook_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.delete(f"/api/v1/webhook-subscriptions/{uuid4()}")
        assert r.status_code == 404


# ===========================================================================
# Webhook CRUD — Non-Admin Authorization
# ===========================================================================


@pytest.mark.asyncio
class TestWebhookCRUDNonAdmin:
    async def test_non_admin_cannot_create_webhook(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.post("/api/v1/webhook-subscriptions", json={
            "name": "should-fail",
            "url": "https://fail.example.com",
            "event_patterns": ["*"],
            "formatter": "generic",
        })
        assert r.status_code == 403

    async def test_non_admin_cannot_delete_webhook(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.delete(f"/api/v1/webhook-subscriptions/{uuid4()}")
        assert r.status_code in (403, 404)

    async def test_non_admin_can_list_webhooks(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.get("/api/v1/webhook-subscriptions")
        assert r.status_code == 200


# ===========================================================================
# Policy Rule CRUD
# ===========================================================================


@pytest.mark.asyncio
class TestPolicyRuleCRUD:
    async def test_create_list_delete_policy_rule(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]

        # Create
        r = await c.post("/api/v1/policy-rules", json={
            "name": "lifecycle-suppress-noisy",
            "description": "Suppress noisy alerts from kube-system",
            "priority": 50,
            "conditions": {
                "resource_namespace": "kube-system",
                "severity": "low",
            },
            "action": {"action_type": "suppress"},
        })
        assert r.status_code == 201
        body = r.json()
        rule_id = body["id"]
        assert body["name"] == "lifecycle-suppress-noisy"
        assert body["priority"] == 50
        assert body["enabled"] is True
        assert body["conditions"]["resource_namespace"] == "kube-system"
        assert body["action"]["action_type"] == "suppress"

        # List
        r = await c.get("/api/v1/policy-rules")
        assert r.status_code == 200
        names = {pr["name"] for pr in r.json()["items"]}
        assert "lifecycle-suppress-noisy" in names

        # Delete
        r = await c.delete(f"/api/v1/policy-rules/{rule_id}")
        assert r.status_code == 204

        # Verify gone
        r = await c.get("/api/v1/policy-rules")
        names = {pr["name"] for pr in r.json()["items"]}
        assert "lifecycle-suppress-noisy" not in names

    async def test_delete_nonexistent_policy_rule_returns_404(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.delete(f"/api/v1/policy-rules/{uuid4()}")
        assert r.status_code == 404

    async def test_evaluate_policy_rule(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        cluster_id = lifecycle_env["cluster_id"]

        r = await c.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "pod-health",
            "check_id": "crash-loop",
            "severity": "high",
            "resource_kind": "Pod",
            "resource_namespace": "default",
            "cluster_id": cluster_id,
        })
        assert r.status_code == 200
        body = r.json()
        assert "matched" in body
        assert "action" in body


# ===========================================================================
# Policy Rule CRUD — Non-Admin Authorization
# ===========================================================================


@pytest.mark.asyncio
class TestPolicyRuleCRUDNonAdmin:
    async def test_non_admin_cannot_create_policy_rule(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.post("/api/v1/policy-rules", json={
            "name": "should-fail",
            "priority": 100,
            "conditions": {},
            "action": {"action_type": "observe"},
        })
        assert r.status_code == 403

    async def test_non_admin_cannot_delete_policy_rule(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.delete(f"/api/v1/policy-rules/{uuid4()}")
        assert r.status_code in (403, 404)

    async def test_non_admin_cannot_evaluate_policy_rule(self, non_admin_env) -> None:
        c = non_admin_env["client"]
        r = await c.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "pod-health",
            "check_id": "crash-loop",
            "severity": "high",
            "resource_kind": "Pod",
            "resource_namespace": "default",
            "cluster_id": str(uuid4()),
        })
        assert r.status_code == 403


# ===========================================================================
# Work Item List & Filter
# ===========================================================================


@pytest.mark.asyncio
class TestWorkItemListAndFilter:
    async def test_list_all_work_items(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.get("/api/v1/work-items")
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total_count" in body
        titles = {i["title"] for i in body["items"]}
        assert "WI-Ready-A" in titles

    async def test_filter_by_status(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.get("/api/v1/work-items?status=ready")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["status"] == "ready"

    async def test_filter_by_priority(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        r = await c.get("/api/v1/work-items?priority=high")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["priority"] == "high"

    async def test_filter_by_cluster(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        cluster_id = lifecycle_env["cluster_id"]
        r = await c.get(f"/api/v1/work-items?cluster_id={cluster_id}")
        assert r.status_code == 200
        for item in r.json()["items"]:
            assert item["cluster_id"] == cluster_id

    async def test_work_item_response_fields(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        wid = lifecycle_env["wi_ids"][0]
        r = await c.get(f"/api/v1/work-items/{wid}")
        assert r.status_code == 200
        body = r.json()
        expected_fields = {
            "id", "issue_id", "cluster_id", "title", "why_now",
            "recommended_next_step", "status", "owner_id", "confidence",
            "priority", "labels", "annotations", "runbook_url",
            "artifact_refs", "blocked_reason", "created_at", "updated_at",
        }
        assert expected_fields.issubset(set(body.keys()))


# ===========================================================================
# Manual Task Creation
# ===========================================================================


@pytest.mark.asyncio
class TestManualTaskCreation:
    async def test_create_standalone_task(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        cluster_id = lifecycle_env["cluster_id"]

        r = await c.post("/api/v1/work-items", json={
            "cluster_id": cluster_id,
            "title": "Manual task from test",
            "priority": "high",
            "why_now": "Testing manual creation",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "Manual task from test"
        assert body["priority"] == "high"
        assert body["status"] == "ready"
        assert body["confidence"] == 1.0
        assert body["issue_id"] is None
        assert body["why_now"] == "Testing manual creation"

        # Cleanup
        async with _factory() as s:
            await s.execute(
                WorkItem.__table__.delete().where(WorkItem.id == UUID(body["id"]))
            )
            await s.commit()

    async def test_create_task_with_defaults(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        cluster_id = lifecycle_env["cluster_id"]

        r = await c.post("/api/v1/work-items", json={
            "cluster_id": cluster_id,
            "title": "Minimal task",
        })
        assert r.status_code == 200
        body = r.json()
        assert body["priority"] == "medium"
        assert body["why_now"] is None

        async with _factory() as s:
            await s.execute(
                WorkItem.__table__.delete().where(WorkItem.id == UUID(body["id"]))
            )
            await s.commit()

    async def test_create_task_without_title_fails(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        cluster_id = lifecycle_env["cluster_id"]

        r = await c.post("/api/v1/work-items", json={
            "cluster_id": cluster_id,
        })
        assert r.status_code == 422


# ===========================================================================
# Issue Resolve — resolved_by field
# ===========================================================================


@pytest.mark.asyncio
class TestIssueResolvedBy:
    async def test_resolve_sets_resolved_by_manual(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]

        r = await c.post(f"/api/v1/issues/{issue_id}/resolve")
        assert r.status_code == 200
        body = r.json()
        assert body["resolved_by"] == "manual"

    async def test_issue_serialization_includes_resolved_by(self, lifecycle_env) -> None:
        c = lifecycle_env["client"]
        issue_id = lifecycle_env["issue_id"]

        r = await c.get(f"/api/v1/issues/{issue_id}")
        assert r.status_code == 200
        assert "resolved_by" in r.json()
