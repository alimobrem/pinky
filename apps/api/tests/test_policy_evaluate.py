"""Tests for policy evaluate endpoint — real rule matching against DB-stored rules."""

import uuid


def _unique(prefix: str = "eval-rule") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _create_rule(client, *, name=None, priority=100, conditions=None, action=None):
    name = name or _unique()
    r = client.post("/api/v1/policy-rules", json={
        "name": name, "priority": priority,
        "conditions": conditions or {},
        "action": action or {"type": "observe"},
    })
    assert r.status_code in (200, 201), f"Failed to create rule: {r.text}"
    return r.json()


def _cleanup(client, rule_id):
    client.delete(f"/api/v1/policy-rules/{rule_id}")


class TestPolicyEvaluateMatching:
    def test_matches_severity(self, authed_client):
        rule = _create_rule(
            authed_client, priority=10,
            conditions={"severity": "critical"},
            action={"type": "investigate"},
        )
        try:
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "pod-health", "check_id": "crash-loop",
                "severity": "critical", "resource_kind": "Pod",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r.status_code == 200
            result = r.json()
            assert result["matched"] is True
            assert result["rule_name"] == rule["name"]
            assert result["action"] == "investigate"
        finally:
            _cleanup(authed_client, rule["id"])

    def test_matches_scanner_and_check_id(self, authed_client):
        rule = _create_rule(
            authed_client, priority=5,
            conditions={"scanner": "pod-health", "check_id": "oom-killed"},
            action={"type": "auto_resolve", "skill": "restart-pod"},
        )
        try:
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "pod-health", "check_id": "oom-killed",
                "severity": "high", "resource_kind": "Pod",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r.status_code == 200
            result = r.json()
            assert result["matched"] is True
            assert result["rule_name"] == rule["name"]
            assert result["action"] == "auto_resolve"
            assert result["action_details"]["skill"] == "restart-pod"
        finally:
            _cleanup(authed_client, rule["id"])

    def test_matches_severity_gte(self, authed_client):
        rule = _create_rule(
            authed_client, priority=10,
            conditions={"severity_gte": "high"},
            action={"type": "investigate"},
        )
        try:
            # critical >= high -> should match
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "x", "check_id": "x",
                "severity": "critical", "resource_kind": "",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r.json()["matched"] is True

            # medium < high -> should NOT match
            r2 = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "x", "check_id": "x",
                "severity": "medium", "resource_kind": "",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r2.json()["matched"] is False
        finally:
            _cleanup(authed_client, rule["id"])

    def test_matches_resource_kind(self, authed_client):
        rule = _create_rule(
            authed_client, priority=10,
            conditions={"resource_kind": "Deployment"},
            action={"type": "create_task"},
        )
        try:
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "", "check_id": "",
                "severity": "medium", "resource_kind": "Deployment",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r.json()["matched"] is True
            assert r.json()["action"] == "create_task"
        finally:
            _cleanup(authed_client, rule["id"])


class TestPolicyEvaluateNoMatch:
    def test_no_rules_returns_default(self, authed_client):
        """With no matching rules, evaluate returns the default observe action."""
        r = authed_client.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "nonexistent-scanner-" + uuid.uuid4().hex[:8],
            "check_id": "nonexistent-check",
            "severity": "info", "resource_kind": "ConfigMap",
            "cluster_id": "", "labels": {}, "recurrence_count": 1,
        })
        assert r.status_code == 200
        result = r.json()
        assert result["matched"] is False
        assert result["rule_name"] == "<default>"
        assert result["action"] == "observe"

    def test_condition_mismatch_no_match(self, authed_client):
        rule = _create_rule(
            authed_client, priority=10,
            conditions={"scanner": "node-health"},
            action={"type": "investigate"},
        )
        try:
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "pod-health", "check_id": "x",
                "severity": "critical", "resource_kind": "Pod",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            assert r.json()["matched"] is False
        finally:
            _cleanup(authed_client, rule["id"])


class TestPolicyEvaluatePriority:
    def test_lower_priority_number_wins(self, authed_client):
        """Lower priority number = higher priority = evaluated first."""
        low = _create_rule(
            authed_client, priority=50,
            conditions={"severity": "critical"},
            action={"type": "observe"},
        )
        high = _create_rule(
            authed_client, priority=10,
            conditions={"severity": "critical"},
            action={"type": "investigate"},
        )
        try:
            r = authed_client.post("/api/v1/policy-rules/evaluate", json={
                "scanner": "", "check_id": "",
                "severity": "critical", "resource_kind": "",
                "cluster_id": "", "labels": {}, "recurrence_count": 1,
            })
            result = r.json()
            assert result["matched"] is True
            assert result["rule_name"] == high["name"]
            assert result["action"] == "investigate"
        finally:
            _cleanup(authed_client, low["id"])
            _cleanup(authed_client, high["id"])


class TestPolicyEvaluateAuth:
    def test_non_admin_rejected(self, non_admin_client):
        r = non_admin_client.post("/api/v1/policy-rules/evaluate", json={
            "scanner": "x", "check_id": "x", "severity": "low",
            "resource_kind": "Pod", "cluster_id": "", "labels": {},
            "recurrence_count": 1,
        })
        assert r.status_code == 403
