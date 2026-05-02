from pinky_worker.policy.engine import (
    PolicyAction,
    PolicyConditions,
    PolicyDecision,
    PolicyInput,
    PolicyRule,
    evaluate,
    matches,
)


def _rule(name: str, priority: int, action_type: str, **conditions: object) -> PolicyRule:
    return PolicyRule(
        name=name,
        priority=priority,
        conditions=PolicyConditions(**conditions),
        action=PolicyAction(action_type=action_type),
    )


def test_empty_conditions_match_everything() -> None:
    assert matches(PolicyConditions(), PolicyInput(scanner="any", severity="low"))


def test_scanner_condition_filters() -> None:
    cond = PolicyConditions(scanner="pod-health")
    assert matches(cond, PolicyInput(scanner="pod-health"))
    assert not matches(cond, PolicyInput(scanner="cert-expiry"))


def test_severity_gte_condition() -> None:
    cond = PolicyConditions(severity_gte="high")
    assert matches(cond, PolicyInput(severity="critical"))
    assert matches(cond, PolicyInput(severity="high"))
    assert not matches(cond, PolicyInput(severity="medium"))
    assert not matches(cond, PolicyInput(severity="low"))


def test_namespace_regex_condition() -> None:
    cond = PolicyConditions(resource_namespace_regex="^test-.*")
    assert matches(cond, PolicyInput(resource_namespace="test-runner"))
    assert not matches(cond, PolicyInput(resource_namespace="production"))


def test_labels_condition() -> None:
    cond = PolicyConditions(labels={"team": "payments"})
    assert matches(cond, PolicyInput(labels={"team": "payments", "env": "prod"}))
    assert not matches(cond, PolicyInput(labels={"team": "platform"}))


def test_recurrence_count_condition() -> None:
    cond = PolicyConditions(recurrence_count_gte=3)
    assert matches(cond, PolicyInput(recurrence_count=3))
    assert matches(cond, PolicyInput(recurrence_count=5))
    assert not matches(cond, PolicyInput(recurrence_count=2))


def test_first_matching_rule_wins() -> None:
    rules = [
        _rule("critical-investigate", 10, "investigate", severity_gte="critical"),
        _rule("high-observe", 50, "observe", severity_gte="high"),
        _rule("default", 1000, "observe"),
    ]
    decision = evaluate(rules, PolicyInput(severity="critical"))
    assert decision.rule_name == "critical-investigate"
    assert decision.action.action_type == "investigate"
    assert decision.matched


def test_lower_priority_wins_when_higher_doesnt_match() -> None:
    rules = [
        _rule("critical-investigate", 10, "investigate", severity_gte="critical"),
        _rule("default", 1000, "observe"),
    ]
    decision = evaluate(rules, PolicyInput(severity="medium"))
    assert decision.rule_name == "default"
    assert decision.action.action_type == "observe"


def test_no_match_returns_default() -> None:
    rules = [
        _rule("specific", 10, "investigate", scanner="nonexistent"),
    ]
    decision = evaluate(rules, PolicyInput(scanner="pod-health"))
    assert not decision.matched
    assert decision.action.action_type == "observe"


def test_suppress_action() -> None:
    rules = [
        _rule("suppress-test", 5, "suppress", resource_namespace_regex="^test-.*"),
    ]
    decision = evaluate(rules, PolicyInput(resource_namespace="test-runner"))
    assert decision.action.action_type == "suppress"


def test_multiple_conditions_all_must_match() -> None:
    cond = PolicyConditions(scanner="pod-health", severity_gte="high")
    assert matches(cond, PolicyInput(scanner="pod-health", severity="critical"))
    assert not matches(cond, PolicyInput(scanner="pod-health", severity="low"))
    assert not matches(cond, PolicyInput(scanner="cert-expiry", severity="critical"))
