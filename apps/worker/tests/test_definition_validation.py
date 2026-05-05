"""Validates all scanner, policy, and skill definition files.

Loads every definition from definitions/ and checks structural
correctness: required fields, valid operators, valid cross-references.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pinky_worker.definitions.loader import load_from_directory, parse_md_definition

DEFINITIONS_DIR = Path(__file__).parent.parent.parent.parent / "definitions"

VALID_SEVERITIES = {"info", "low", "medium", "high", "critical"}

KNOWN_OPS = {
    "eq", "neq", "gt", "gte", "lt", "lte", "in",
    "is_empty", "is_set", "is_true", "is_false", "contains",
    "condition_status", "age_gt",
    "cert_expires_within", "cert_expired",
    "quantity_gte", "quantity_gte_pct",
    "promql_gt", "promql_lt", "promql_eq", "promql_absent",
}

VALID_POLICY_ACTION_TYPES = {
    "suppress", "observe", "investigate", "auto_resolve", "create_task",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_all_definitions() -> list:
    return load_from_directory(DEFINITIONS_DIR)


def _load_kind(kind: str) -> list:
    return [d for d in _load_all_definitions() if d.kind == kind]


def _collect_leaf_ops(condition: dict) -> list[str]:
    """Recursively collect all leaf 'op' values from a condition tree."""
    ops: list[str] = []
    if "all" in condition:
        for sub in condition["all"]:
            ops.extend(_collect_leaf_ops(sub))
    elif "any" in condition:
        for sub in condition["any"]:
            ops.extend(_collect_leaf_ops(sub))
    elif "op" in condition:
        ops.append(condition["op"])
    return ops


def _scanner_ids() -> list[str]:
    scanners = _load_kind("scanner")
    return [s.name for s in scanners]


# ---------------------------------------------------------------------------
# Category 1: Scanner definition validation
# ---------------------------------------------------------------------------


class TestScannerDefinitions:
    """Validate every scanner definition under definitions/scanners/."""

    @pytest.fixture(scope="class")
    def scanners(self) -> list:
        return _load_kind("scanner")

    def test_all_scanners_loaded(self, scanners: list) -> None:
        md_files = list((DEFINITIONS_DIR / "scanners").glob("*.md"))
        assert len(scanners) == len(md_files), (
            f"Expected {len(md_files)} scanners, loaded {len(scanners)}"
        )

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_has_checks(self, name: str) -> None:
        defn = _load_scanner(name)
        checks = defn.frontmatter.get("checks")
        assert isinstance(checks, list), f"{name}: missing 'checks' list"
        assert len(checks) > 0, f"{name}: empty checks list"

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_has_resource_kinds(self, name: str) -> None:
        defn = _load_scanner(name)
        rk = defn.frontmatter.get("resource_kinds")
        assert isinstance(rk, list) and len(rk) > 0, f"{name}: missing or empty resource_kinds"

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_check_fields(self, name: str) -> None:
        defn = _load_scanner(name)
        for check in defn.frontmatter["checks"]:
            check_id = check.get("id")
            assert isinstance(check_id, str) and check_id, (
                f"{name}: check missing 'id': {check}"
            )
            sev = check.get("severity")
            assert sev in VALID_SEVERITIES, (
                f"{name}/{check_id}: invalid severity '{sev}'"
            )
            condition = check.get("condition")
            assert isinstance(condition, dict), (
                f"{name}/{check_id}: missing or non-dict condition"
            )
            assert "op" in condition or "all" in condition or "any" in condition, (
                f"{name}/{check_id}: condition has no 'op', 'all', or 'any'"
            )

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_leaf_ops_are_known(self, name: str) -> None:
        defn = _load_scanner(name)
        for check in defn.frontmatter["checks"]:
            check_id = check.get("id", "?")
            condition = check.get("condition", {})
            ops = _collect_leaf_ops(condition)
            for op in ops:
                assert op in KNOWN_OPS, (
                    f"{name}/{check_id}: unknown operator '{op}'"
                )

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_iterate_syntax(self, name: str) -> None:
        defn = _load_scanner(name)
        for check in defn.frontmatter["checks"]:
            iterate = check.get("iterate")
            if iterate is not None:
                assert isinstance(iterate, str), (
                    f"{name}/{check.get('id')}: iterate must be a string"
                )
                assert "[*]" in iterate, (
                    f"{name}/{check.get('id')}: iterate missing [*] syntax: '{iterate}'"
                )

    @pytest.mark.parametrize("name", _scanner_ids())
    def test_title_template_sanity(self, name: str) -> None:
        defn = _load_scanner(name)
        for check in defn.frontmatter["checks"]:
            tmpl = check.get("title_template")
            if tmpl:
                assert "{name}" in tmpl or "{namespace}" in tmpl, (
                    f"{name}/{check.get('id')}: title_template should contain "
                    f"{{name}} or {{namespace}}: '{tmpl}'"
                )


# ---------------------------------------------------------------------------
# Category 1b: Policy definition validation
# ---------------------------------------------------------------------------


def _policy_names() -> list[str]:
    return [p.name for p in _load_kind("policy")]


class TestPolicyDefinitions:
    """Validate every policy definition under definitions/policies/."""

    @pytest.mark.parametrize("name", _policy_names())
    def test_has_priority(self, name: str) -> None:
        defn = _load_policy(name)
        priority = defn.frontmatter.get("priority")
        assert isinstance(priority, int), f"{name}: priority must be int, got {type(priority)}"

    @pytest.mark.parametrize("name", _policy_names())
    def test_has_conditions(self, name: str) -> None:
        defn = _load_policy(name)
        conditions = defn.frontmatter.get("conditions")
        assert isinstance(conditions, dict), f"{name}: conditions must be dict"

    @pytest.mark.parametrize("name", _policy_names())
    def test_has_valid_action(self, name: str) -> None:
        defn = _load_policy(name)
        action = defn.frontmatter.get("action")
        assert isinstance(action, dict), f"{name}: action must be dict"
        action_type = action.get("type")
        assert action_type in VALID_POLICY_ACTION_TYPES, (
            f"{name}: invalid action type '{action_type}'"
        )

    @pytest.mark.parametrize("name", _policy_names())
    def test_skill_reference_valid(self, name: str) -> None:
        defn = _load_policy(name)
        action = defn.frontmatter.get("action", {})
        skill_name = action.get("skill")
        if skill_name is None:
            return
        skill_path = DEFINITIONS_DIR / "skills" / f"{skill_name}.md"
        assert skill_path.exists(), (
            f"{name}: references skill '{skill_name}' but {skill_path} does not exist"
        )


# ---------------------------------------------------------------------------
# Category 1c: Skill definition validation
# ---------------------------------------------------------------------------


def _skill_names() -> list[str]:
    return [s.name for s in _load_kind("skill")]


class TestSkillDefinitions:
    """Validate every skill definition under definitions/skills/."""

    @pytest.mark.parametrize("name", _skill_names())
    def test_has_tools(self, name: str) -> None:
        defn = _load_skill(name)
        tools = defn.frontmatter.get("tools")
        assert isinstance(tools, list) and len(tools) > 0, (
            f"{name}: missing or empty tools list"
        )

    @pytest.mark.parametrize("name", _skill_names())
    def test_has_model_tier(self, name: str) -> None:
        defn = _load_skill(name)
        tier = defn.frontmatter.get("model_tier")
        assert isinstance(tier, str) and tier, f"{name}: missing model_tier"

    @pytest.mark.parametrize("name", _skill_names())
    def test_has_timeout_seconds(self, name: str) -> None:
        defn = _load_skill(name)
        timeout = defn.frontmatter.get("timeout_seconds")
        assert isinstance(timeout, int) and timeout > 0, (
            f"{name}: timeout_seconds must be positive int"
        )

    @pytest.mark.parametrize("name", _skill_names())
    def test_tool_references_valid(self, name: str) -> None:
        defn = _load_skill(name)
        tools = defn.frontmatter.get("tools", [])
        for tool_name in tools:
            tool_path = DEFINITIONS_DIR / "tools" / f"{tool_name}.md"
            assert tool_path.exists(), (
                f"{name}: references tool '{tool_name}' but {tool_path} does not exist"
            )


# ---------------------------------------------------------------------------
# Helpers for loading individual definitions
# ---------------------------------------------------------------------------


def _load_scanner(name: str):
    path = DEFINITIONS_DIR / "scanners" / f"{name}.md"
    return parse_md_definition(path.read_text(), source="filesystem")


def _load_policy(name: str):
    path = DEFINITIONS_DIR / "policies" / f"{name}.md"
    return parse_md_definition(path.read_text(), source="filesystem")


def _load_skill(name: str):
    path = DEFINITIONS_DIR / "skills" / f"{name}.md"
    return parse_md_definition(path.read_text(), source="filesystem")
