"""Tests for definition CRUD endpoints."""

import uuid


def _unique(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TestDefinitionCreate:
    def test_create_scanner(self, authed_client):
        name = _unique("scanner")
        r = authed_client.post("/api/v1/definitions", json={
            "kind": "scanner", "name": name, "version": "1.0.0",
            "frontmatter": {"severity": "high"}, "body": "# Check pods",
        })
        assert r.status_code == 201
        d = r.json()
        assert d["kind"] == "scanner"
        assert d["name"] == name
        assert d["frontmatter"]["severity"] == "high"
        assert d["body"] == "# Check pods"
        authed_client.delete(f"/api/v1/definitions/scanner/{name}")

    def test_create_skill(self, authed_client):
        name = _unique("skill")
        r = authed_client.post("/api/v1/definitions", json={
            "kind": "skill", "name": name,
            "frontmatter": {"tools": ["kubectl"]}, "body": "Diagnose OOM",
        })
        assert r.status_code == 201
        assert r.json()["kind"] == "skill"
        authed_client.delete(f"/api/v1/definitions/skill/{name}")

    def test_create_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.post("/api/v1/definitions", json={
            "kind": "scanner", "name": "x", "frontmatter": {}, "body": "",
        })
        assert r.status_code == 403

    def test_create_missing_name(self, authed_client):
        r = authed_client.post("/api/v1/definitions", json={
            "kind": "scanner", "frontmatter": {}, "body": "",
        })
        assert r.status_code == 422

    def test_create_upserts_duplicate(self, authed_client):
        name = _unique("upsert")
        authed_client.post("/api/v1/definitions", json={
            "kind": "scanner", "name": name, "frontmatter": {}, "body": "v1",
        })
        r2 = authed_client.post("/api/v1/definitions", json={
            "kind": "scanner", "name": name, "frontmatter": {}, "body": "v2",
        })
        assert r2.status_code == 201
        authed_client.delete(f"/api/v1/definitions/scanner/{name}")


class TestDefinitionRead:
    def test_get_by_kind_name(self, authed_client):
        name = _unique("get")
        authed_client.post("/api/v1/definitions", json={
            "kind": "tool", "name": name, "frontmatter": {"x": 1}, "body": "body",
        })
        r = authed_client.get(f"/api/v1/definitions/tool/{name}")
        assert r.status_code == 200
        assert r.json()["name"] == name
        assert r.json()["body"] == "body"
        authed_client.delete(f"/api/v1/definitions/tool/{name}")

    def test_get_not_found(self, authed_client):
        r = authed_client.get("/api/v1/definitions/scanner/nonexistent")
        assert r.status_code == 404

    def test_list_filter_by_kind(self, authed_client):
        name = _unique("filter")
        authed_client.post("/api/v1/definitions", json={
            "kind": "pipeline", "name": name, "frontmatter": {}, "body": "",
        })
        r = authed_client.get("/api/v1/definitions?kind=pipeline")
        assert r.status_code == 200
        names = [d["name"] for d in r.json()["items"]]
        assert name in names
        authed_client.delete(f"/api/v1/definitions/pipeline/{name}")


class TestDefinitionDelete:
    def test_delete(self, authed_client):
        name = _unique("del")
        authed_client.post("/api/v1/definitions", json={
            "kind": "scanner", "name": name, "frontmatter": {}, "body": "",
        })
        r = authed_client.delete(f"/api/v1/definitions/scanner/{name}")
        assert r.status_code == 204
        r2 = authed_client.get(f"/api/v1/definitions/scanner/{name}")
        assert r2.status_code == 404

    def test_delete_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.delete("/api/v1/definitions/scanner/x")
        assert r.status_code == 403

    def test_delete_not_found(self, authed_client):
        r = authed_client.delete("/api/v1/definitions/scanner/nonexistent")
        assert r.status_code == 404
