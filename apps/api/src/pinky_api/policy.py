"""Inlined policy evaluation logic — pure functions, no DB or async dependencies.

Mirrors the worker's policy/engine.py for use in the API evaluate endpoint.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass(frozen=True)
class PolicyConditions:
    scanner: str | None = None
    check_id: str | None = None
    check_id_regex: str | None = None
    severity: str | None = None
    severity_gte: str | None = None
    resource_kind: str | None = None
    resource_namespace_regex: str | None = None
    cluster_id: str | None = None
    labels: dict[str, str] = field(default_factory=dict)
    recurrence_count_gte: int | None = None
    reopen_count_gte: int | None = None
    is_operator_managed: bool | None = None


@dataclass(frozen=True)
class PolicyAction:
    action_type: str  # suppress, observe, investigate, auto_resolve, create_task
    suppress_duration_minutes: int | None = None
    risk_class: str | None = None
    runbook_url: str | None = None
    skill: str | None = None


@dataclass(frozen=True)
class EvalPolicyRule:
    name: str
    priority: int
    conditions: PolicyConditions
    action: PolicyAction


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
    reopen_count: int = 0
    is_operator_managed: bool = False


def matches(conditions: PolicyConditions, inp: PolicyInput) -> bool:
    if conditions.scanner and conditions.scanner != inp.scanner:
        return False
    if conditions.check_id and conditions.check_id != inp.check_id:
        return False
    if conditions.check_id_regex and not re.fullmatch(conditions.check_id_regex, inp.check_id):
        return False
    if conditions.severity and conditions.severity != inp.severity:
        return False
    if conditions.severity_gte:
        required = SEVERITY_ORDER.get(conditions.severity_gte, 0)
        actual = SEVERITY_ORDER.get(inp.severity, 0)
        if actual < required:
            return False
    if conditions.resource_kind and conditions.resource_kind != inp.resource_kind:
        return False
    if (
        conditions.resource_namespace_regex
        and not re.match(conditions.resource_namespace_regex, inp.resource_namespace)
    ):
        return False
    if conditions.cluster_id and conditions.cluster_id != inp.cluster_id:
        return False
    if conditions.labels:
        for k, v in conditions.labels.items():
            if inp.labels.get(k) != v:
                return False
    if (
        conditions.recurrence_count_gte is not None
        and inp.recurrence_count < conditions.recurrence_count_gte
    ):
        return False
    if (
        conditions.reopen_count_gte is not None
        and inp.reopen_count < conditions.reopen_count_gte
    ):
        return False
    return not (
        conditions.is_operator_managed is not None
        and conditions.is_operator_managed != inp.is_operator_managed
    )


def evaluate(rules: list[EvalPolicyRule], inp: PolicyInput) -> dict:
    for rule in rules:
        if matches(rule.conditions, inp):
            action = rule.action
            return {
                "matched": True,
                "rule_name": rule.name,
                "action": action.action_type,
                "action_details": {
                    "suppress_duration_minutes": action.suppress_duration_minutes,
                    "risk_class": action.risk_class,
                    "runbook_url": action.runbook_url,
                    "skill": action.skill,
                },
            }
    return {"matched": False, "rule_name": "<default>", "action": "observe"}


def rules_from_db_rows(rows: list) -> list[EvalPolicyRule]:
    """Convert PolicyRule DB model rows to evaluation dataclasses."""
    results = []
    for r in rows:
        cond_raw = r.conditions or {}
        act_raw = r.action or {}
        conditions = PolicyConditions(
            scanner=cond_raw.get("scanner"),
            check_id=cond_raw.get("check_id"),
            check_id_regex=cond_raw.get("check_id_regex"),
            severity=cond_raw.get("severity"),
            severity_gte=cond_raw.get("severity_gte"),
            resource_kind=cond_raw.get("resource_kind"),
            resource_namespace_regex=cond_raw.get("resource_namespace_regex"),
            cluster_id=cond_raw.get("cluster_id"),
            labels=cond_raw.get("labels", {}),
            recurrence_count_gte=cond_raw.get("recurrence_count_gte"),
            reopen_count_gte=cond_raw.get("reopen_count_gte"),
            is_operator_managed=cond_raw.get("is_operator_managed"),
        )
        action = PolicyAction(
            action_type=act_raw.get("type", "observe"),
            suppress_duration_minutes=act_raw.get("suppress_duration_minutes"),
            risk_class=act_raw.get("risk_class"),
            runbook_url=act_raw.get("runbook_url"),
            skill=act_raw.get("skill"),
        )
        results.append(EvalPolicyRule(
            name=r.name,
            priority=r.priority,
            conditions=conditions,
            action=action,
        ))
    return results
