"""Unit tests for the inlined policy evaluation logic — no DB required."""

from pinky_api.policy import (
    EvalPolicyRule,
    PolicyAction,
    PolicyConditions,
    PolicyInput,
    evaluate,
    matches,
    rules_from_db_rows,
)


class TestMatches:
    def test_empty_conditions_match_anything(self):
        cond = PolicyConditions()
        inp = PolicyInput(scanner="x", severity="critical")
        assert matches(cond, inp) is True

    def test_scanner_match(self):
        cond = PolicyConditions(scanner="pod-health")
        assert matches(cond, PolicyInput(scanner="pod-health")) is True
        assert matches(cond, PolicyInput(scanner="node-health")) is False

    def test_check_id_match(self):
        cond = PolicyConditions(check_id="oom-killed")
        assert matches(cond, PolicyInput(check_id="oom-killed")) is True
        assert matches(cond, PolicyInput(check_id="crash-loop")) is False

    def test_check_id_regex(self):
        cond = PolicyConditions(check_id_regex="crash-.*")
        assert matches(cond, PolicyInput(check_id="crash-loop")) is True
        assert matches(cond, PolicyInput(check_id="oom-killed")) is False

    def test_severity_exact(self):
        cond = PolicyConditions(severity="critical")
        assert matches(cond, PolicyInput(severity="critical")) is True
        assert matches(cond, PolicyInput(severity="high")) is False

    def test_severity_gte(self):
        cond = PolicyConditions(severity_gte="high")
        assert matches(cond, PolicyInput(severity="critical")) is True
        assert matches(cond, PolicyInput(severity="high")) is True
        assert matches(cond, PolicyInput(severity="medium")) is False
        assert matches(cond, PolicyInput(severity="low")) is False

    def test_resource_kind(self):
        cond = PolicyConditions(resource_kind="Pod")
        assert matches(cond, PolicyInput(resource_kind="Pod")) is True
        assert matches(cond, PolicyInput(resource_kind="Deployment")) is False

    def test_resource_namespace_regex(self):
        cond = PolicyConditions(resource_namespace_regex="kube-.*")
        assert matches(cond, PolicyInput(resource_namespace="kube-system")) is True
        assert matches(cond, PolicyInput(resource_namespace="default")) is False

    def test_cluster_id(self):
        cond = PolicyConditions(cluster_id="abc-123")
        assert matches(cond, PolicyInput(cluster_id="abc-123")) is True
        assert matches(cond, PolicyInput(cluster_id="xyz")) is False

    def test_labels(self):
        cond = PolicyConditions(labels={"env": "prod"})
        assert matches(cond, PolicyInput(labels={"env": "prod", "tier": "web"})) is True
        assert matches(cond, PolicyInput(labels={"env": "dev"})) is False
        assert matches(cond, PolicyInput(labels={})) is False

    def test_recurrence_count_gte(self):
        cond = PolicyConditions(recurrence_count_gte=3)
        assert matches(cond, PolicyInput(recurrence_count=5)) is True
        assert matches(cond, PolicyInput(recurrence_count=3)) is True
        assert matches(cond, PolicyInput(recurrence_count=2)) is False

    def test_compound_conditions(self):
        cond = PolicyConditions(scanner="pod-health", severity_gte="high")
        assert matches(cond, PolicyInput(scanner="pod-health", severity="critical")) is True
        assert matches(cond, PolicyInput(scanner="pod-health", severity="low")) is False
        assert matches(cond, PolicyInput(scanner="node-health", severity="critical")) is False


class TestEvaluate:
    def test_no_rules_returns_default(self):
        result = evaluate([], PolicyInput())
        assert result["matched"] is False
        assert result["rule_name"] == "<default>"
        assert result["action"] == "observe"

    def test_matching_rule(self):
        rules = [
            EvalPolicyRule(
                name="crit", priority=10,
                conditions=PolicyConditions(severity="critical"),
                action=PolicyAction(action_type="investigate"),
            ),
        ]
        result = evaluate(rules, PolicyInput(severity="critical"))
        assert result["matched"] is True
        assert result["rule_name"] == "crit"
        assert result["action"] == "investigate"

    def test_priority_ordering(self):
        rules = [
            EvalPolicyRule(
                name="low-pri", priority=50,
                conditions=PolicyConditions(severity="critical"),
                action=PolicyAction(action_type="observe"),
            ),
            EvalPolicyRule(
                name="high-pri", priority=10,
                conditions=PolicyConditions(severity="critical"),
                action=PolicyAction(action_type="investigate"),
            ),
        ]
        result = evaluate(rules, PolicyInput(severity="critical"))
        assert result["rule_name"] == "high-pri"
        assert result["action"] == "investigate"

    def test_first_match_wins(self):
        rules = [
            EvalPolicyRule(
                name="a", priority=10,
                conditions=PolicyConditions(severity="critical"),
                action=PolicyAction(action_type="suppress"),
            ),
            EvalPolicyRule(
                name="b", priority=20,
                conditions=PolicyConditions(severity="critical"),
                action=PolicyAction(action_type="investigate"),
            ),
        ]
        result = evaluate(rules, PolicyInput(severity="critical"))
        assert result["rule_name"] == "a"

    def test_action_details_returned(self):
        rules = [
            EvalPolicyRule(
                name="x", priority=1,
                conditions=PolicyConditions(),
                action=PolicyAction(
                    action_type="auto_resolve", skill="restart-pod",
                    risk_class="low",
                ),
            ),
        ]
        result = evaluate(rules, PolicyInput())
        assert result["action_details"]["skill"] == "restart-pod"
        assert result["action_details"]["risk_class"] == "low"


class TestRulesFromDbRows:
    def test_converts_row(self):
        class FakeRow:
            name = "test"
            priority = 42
            conditions = {"scanner": "pod-health", "severity_gte": "high"}
            action = {"type": "investigate", "skill": "diagnose"}

        rules = rules_from_db_rows([FakeRow()])
        assert len(rules) == 1
        r = rules[0]
        assert r.name == "test"
        assert r.priority == 42
        assert r.conditions.scanner == "pod-health"
        assert r.conditions.severity_gte == "high"
        assert r.action.action_type == "investigate"
        assert r.action.skill == "diagnose"

    def test_defaults_on_empty(self):
        class FakeRow:
            name = "empty"
            priority = 100
            conditions = {}
            action = {}

        rules = rules_from_db_rows([FakeRow()])
        r = rules[0]
        assert r.action.action_type == "observe"
        assert r.conditions.scanner is None
