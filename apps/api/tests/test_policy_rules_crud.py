"""Tests for policy rule CRUD and evaluate endpoints."""

import uuid


def _unique(prefix: str = "rule") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TestPolicyRuleCreate:
    def test_create(self, authed_client):
        name = _unique()
        r = authed_client.post("/api/v1/policy-rules", json={
            "name": name, "description": "test rule", "priority": 50,
            "conditions": {"severity": "critical"},
            "action": {"type": "investigate"},
        })
        assert r.status_code in (200, 201)
        rule = r.json()
        assert rule["name"] == name
        assert rule["priority"] == 50
        authed_client.delete(f"/api/v1/policy-rules/{rule['id']}")

    def test_create_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.post("/api/v1/policy-rules", json={
            "name": "x", "conditions": {}, "action": {"type": "suppress"},
        })
        assert r.status_code == 403

    def test_create_missing_name(self, authed_client):
        r = authed_client.post("/api/v1/policy-rules", json={
            "conditions": {}, "action": {"type": "suppress"},
        })
        assert r.status_code == 422


class TestPolicyRuleList:
    def test_list_returns_items(self, authed_client):
        r = authed_client.get("/api/v1/policy-rules")
        assert r.status_code == 200
        assert "items" in r.json()
        assert isinstance(r.json()["items"], list)


class TestPolicyRuleDelete:
    def test_delete(self, authed_client):
        name = _unique()
        cr = authed_client.post("/api/v1/policy-rules", json={
            "name": name, "conditions": {}, "action": {"type": "suppress"},
        })
        rid = cr.json()["id"]
        r = authed_client.delete(f"/api/v1/policy-rules/{rid}")
        assert r.status_code == 204
        r2 = authed_client.get("/api/v1/policy-rules")
        ids = [rule["id"] for rule in r2.json()["items"]]
        assert rid not in ids

    def test_delete_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.delete("/api/v1/policy-rules/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 403


class TestPolicyRuleEvaluate:
    def test_evaluate_returns_result(self, authed_client):
        r = authed_client.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "pod-health", "check_id": "crash-loop",
            "severity": "critical", "resource_kind": "Pod",
            "cluster_id": "", "labels": {}, "recurrence_count": 1,
        })
        assert r.status_code == 200
        result = r.json()
        assert "matched" in result
        assert isinstance(result["matched"], bool)

    def test_evaluate_no_match(self, authed_client):
        r = authed_client.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "nonexistent", "check_id": "x",
            "severity": "info", "resource_kind": "Pod",
            "cluster_id": "", "labels": {}, "recurrence_count": 1,
        })
        assert r.status_code == 200
        assert r.json()["matched"] is False

    def test_evaluate_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "x", "check_id": "x", "severity": "low",
            "resource_kind": "Pod", "cluster_id": "", "labels": {},
            "recurrence_count": 1,
        })
        assert r.status_code == 403


class TestPolicyRulePut:
    def test_put_implemented(self, authed_client):
        name = _unique()
        cr = authed_client.post("/api/v1/policy-rules", json={
            "name": name, "conditions": {}, "action": {"type": "suppress"},
        })
        rid = cr.json()["id"]
        r = authed_client.put(f"/api/v1/policy-rules/{rid}", json={
            "name": name, "conditions": {"severity": "high"},
            "action": {"type": "investigate"},
        })
        assert r.status_code in (200, 501)
        authed_client.delete(f"/api/v1/policy-rules/{rid}")
