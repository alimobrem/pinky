"""Declarative policy rule engine.

Evaluates rules in priority order (lowest number = highest priority).
First matching rule wins. No LLM calls — purely deterministic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class PolicyConditions:
    scanner: str | None = None
    check_id: str | None = None
    severity_gte: str | None = None
    resource_kind: str | None = None
    resource_namespace_regex: str | None = None
    cluster_id: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    recurrence_count_gte: int | None = None


@dataclass(frozen=True)
class PolicyAction:
    action_type: str  # suppress, observe, investigate, auto_resolve, create_task
    suppress_duration_minutes: int | None = None
    risk_class: str | None = None
    runbook_url: str | None = None
    skill: str | None = None


@dataclass(frozen=True)
class PolicyRule:
    name: str
    priority: int
    conditions: PolicyConditions
    action: PolicyAction
    description: str = ""


@dataclass
class PolicyInput:
    scanner: str = ""
    check_id: str = ""
    severity: str = "medium"
    resource_kind: str = ""
    resource_namespace: str = ""
    cluster_id: str = ""
    labels: dict[str, str] = field(default_factory=dict)
    recurrence_count: int = 1


@dataclass(frozen=True)
class PolicyDecision:
    rule_name: str
    action: PolicyAction
    matched: bool


DEFAULT_ACTION = PolicyAction(action_type="observe")
NO_MATCH = PolicyDecision(rule_name="<default>", action=DEFAULT_ACTION, matched=False)


def matches(conditions: PolicyConditions, input: PolicyInput) -> bool:
    if conditions.scanner and conditions.scanner != input.scanner:
        return False
    if conditions.check_id and conditions.check_id != input.check_id:
        return False
    if conditions.severity_gte:
        required = SEVERITY_ORDER.get(conditions.severity_gte, 0)
        actual = SEVERITY_ORDER.get(input.severity, 0)
        if actual < required:
            return False
    if conditions.resource_kind and conditions.resource_kind != input.resource_kind:
        return False
    if conditions.resource_namespace_regex:
        if not re.match(conditions.resource_namespace_regex, input.resource_namespace):
            return False
    if conditions.cluster_id and conditions.cluster_id != input.cluster_id:
        return False
    if conditions.labels:
        for k, v in conditions.labels.items():
            if input.labels.get(k) != v:
                return False
    if conditions.recurrence_count_gte is not None:
        if input.recurrence_count < conditions.recurrence_count_gte:
            return False
    return True


def evaluate(rules: list[PolicyRule], input: PolicyInput) -> PolicyDecision:
    sorted_rules = sorted(rules, key=lambda r: r.priority)
    for rule in sorted_rules:
        if matches(rule.conditions, input):
            return PolicyDecision(rule_name=rule.name, action=rule.action, matched=True)
    return NO_MATCH


def rules_from_definitions(definitions: list) -> list[PolicyRule]:
    results = []
    for d in definitions:
        fm = d.frontmatter
        conditions_raw = fm.get("conditions", {})
        action_raw = fm.get("action", {})

        conditions = PolicyConditions(
            scanner=conditions_raw.get("scanner"),
            check_id=conditions_raw.get("check_id"),
            severity_gte=conditions_raw.get("severity_gte"),
            resource_kind=conditions_raw.get("resource_kind"),
            resource_namespace_regex=conditions_raw.get("resource_namespace_regex"),
            cluster_id=conditions_raw.get("cluster_id"),
            labels=conditions_raw.get("labels", {}),
            recurrence_count_gte=conditions_raw.get("recurrence_count_gte"),
        )

        action = PolicyAction(
            action_type=action_raw.get("type", "observe"),
            suppress_duration_minutes=action_raw.get("suppress_duration_minutes"),
            risk_class=action_raw.get("risk_class"),
            runbook_url=action_raw.get("runbook_url"),
            skill=action_raw.get("skill"),
        )

        results.append(PolicyRule(
            name=d.name,
            priority=fm.get("priority", 100),
            conditions=conditions,
            action=action,
            description=d.body[:200] if d.body else "",
        ))
    return results
