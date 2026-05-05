"""Comprehensive tests for the generic scanner executor.

Tests resolve_path, parse_duration, parse_k8s_quantity, evaluate_op,
evaluate_condition, run_generic_checks (integration), and PromQL operators.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from pinky_worker.definitions.loader import Definition
from pinky_worker.observation.generic_scanner import (
    evaluate_condition,
    evaluate_op,
    parse_duration,
    parse_k8s_quantity,
    resolve_path,
    run_generic_checks,
)

# ---------------------------------------------------------------------------
# resolve_path
# ---------------------------------------------------------------------------


class TestResolvePath:
    def test_simple_key(self) -> None:
        assert resolve_path({"name": "foo"}, "name") == "foo"

    def test_nested(self) -> None:
        assert resolve_path({"spec": {"replicas": 3}}, "spec.replicas") == 3

    def test_missing_key(self) -> None:
        assert resolve_path({"a": 1}, "b") is None

    def test_wildcard(self) -> None:
        data = {"containers": [{"name": "a"}, {"name": "b"}]}
        assert resolve_path(data, "containers[*].name") == ["a", "b"]

    def test_filter(self) -> None:
        data = {
            "conditions": [
                {"type": "Ready", "status": "True"},
                {"type": "Disk", "status": "False"},
            ],
        }
        assert resolve_path(data, "conditions[type=Ready].status") == "True"

    def test_deep_path_after_wildcard(self) -> None:
        data = {
            "containers": [
                {"state": {"reason": "CrashLoop"}},
                {"state": {"reason": "Running"}},
            ],
        }
        assert resolve_path(data, "containers[*].state.reason") == ["CrashLoop", "Running"]

    def test_wildcard_on_non_list(self) -> None:
        assert resolve_path({"containers": "not-a-list"}, "containers[*].name") is None

    def test_filter_no_match(self) -> None:
        data = {"conditions": [{"type": "Disk", "status": "False"}]}
        assert resolve_path(data, "conditions[type=Ready].status") is None

    def test_deeply_nested(self) -> None:
        data = {"a": {"b": {"c": {"d": 42}}}}
        assert resolve_path(data, "a.b.c.d") == 42

    def test_empty_dict(self) -> None:
        assert resolve_path({}, "any.path") is None


# ---------------------------------------------------------------------------
# parse_duration
# ---------------------------------------------------------------------------


class TestParseDuration:
    def test_seconds(self) -> None:
        assert parse_duration("30s") == timedelta(seconds=30)

    def test_minutes(self) -> None:
        assert parse_duration("5m") == timedelta(minutes=5)

    def test_hours(self) -> None:
        assert parse_duration("1h") == timedelta(hours=1)

    def test_days(self) -> None:
        assert parse_duration("7d") == timedelta(days=7)

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid duration"):
            parse_duration("10x")

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid duration"):
            parse_duration("")

    def test_whitespace_stripped(self) -> None:
        assert parse_duration("  30s  ") == timedelta(seconds=30)


# ---------------------------------------------------------------------------
# parse_k8s_quantity
# ---------------------------------------------------------------------------


class TestParseK8sQuantity:
    def test_gi(self) -> None:
        assert parse_k8s_quantity("1Gi") == 1073741824.0

    def test_mi(self) -> None:
        assert parse_k8s_quantity("100Mi") == 104857600.0

    def test_millicpu(self) -> None:
        assert parse_k8s_quantity("500m") == 0.5

    def test_float_plain(self) -> None:
        assert parse_k8s_quantity("1.5") == 1.5

    def test_integer_plain(self) -> None:
        assert parse_k8s_quantity("100") == 100.0

    def test_ki(self) -> None:
        assert parse_k8s_quantity("1Ki") == 1024.0

    def test_whitespace_stripped(self) -> None:
        assert parse_k8s_quantity("  500m  ") == 0.5


# ---------------------------------------------------------------------------
# evaluate_op
# ---------------------------------------------------------------------------

NOW = datetime.now(UTC)
EMPTY_RESOURCE: dict = {}


def _op(value, op: str, condition: dict | None = None, **kw) -> bool:
    cond = condition or {}
    return evaluate_op(value, op, cond, NOW, kw.get("resource", EMPTY_RESOURCE), kw.get("prom_client"))


class TestEvaluateOp:
    def test_eq_true(self) -> None:
        assert _op(5, "eq", {"value": 5})

    def test_eq_false(self) -> None:
        assert not _op(5, "eq", {"value": 3})

    def test_neq_true(self) -> None:
        assert _op(5, "neq", {"value": 3})

    def test_neq_false(self) -> None:
        assert not _op(5, "neq", {"value": 5})

    def test_gt_true(self) -> None:
        assert _op(10, "gt", {"value": 5})

    def test_gt_false(self) -> None:
        assert not _op(3, "gt", {"value": 5})

    def test_gte_true_equal(self) -> None:
        assert _op(5, "gte", {"value": 5})

    def test_gte_true_greater(self) -> None:
        assert _op(6, "gte", {"value": 5})

    def test_lt_true(self) -> None:
        assert _op(3, "lt", {"value": 5})

    def test_lt_false(self) -> None:
        assert not _op(10, "lt", {"value": 5})

    def test_in_true(self) -> None:
        assert _op("CrashLoopBackOff", "in", {"value": ["CrashLoopBackOff", "Error"]})

    def test_in_false(self) -> None:
        assert not _op("Running", "in", {"value": ["CrashLoopBackOff", "Error"]})

    def test_is_empty_none(self) -> None:
        assert _op(None, "is_empty")

    def test_is_empty_string(self) -> None:
        assert not _op("hello", "is_empty")

    def test_is_empty_empty_string(self) -> None:
        assert _op("", "is_empty")

    def test_is_empty_empty_list(self) -> None:
        # Empty list hits the any() unwrap path — any() over [] is False.
        # is_empty on a list only fires when resolving a path yields None.
        assert not _op([], "is_empty")

    def test_is_set_true(self) -> None:
        assert _op("hello", "is_set")

    def test_is_set_none(self) -> None:
        assert not _op(None, "is_set")

    def test_is_set_empty_string(self) -> None:
        assert not _op("", "is_set")

    def test_is_true_bool(self) -> None:
        assert _op(True, "is_true")

    def test_is_true_string(self) -> None:
        assert _op("True", "is_true")

    def test_is_true_false(self) -> None:
        assert not _op(False, "is_true")

    def test_is_false_bool(self) -> None:
        assert _op(False, "is_false")

    def test_is_false_true(self) -> None:
        assert not _op(True, "is_false")

    def test_is_false_string_true(self) -> None:
        assert not _op("True", "is_false")

    def test_contains_true(self) -> None:
        assert _op("hello world", "contains", {"value": "world"})

    def test_contains_false(self) -> None:
        assert not _op("hello world", "contains", {"value": "planet"})

    def test_condition_status_true(self) -> None:
        value = [{"type": "Ready", "status": "True"}]
        assert _op(value, "condition_status", {"type": "Ready", "status": "True"})

    def test_condition_status_false(self) -> None:
        value = [{"type": "Ready", "status": "False"}]
        assert not _op(value, "condition_status", {"type": "Ready", "status": "True"})

    def test_condition_status_missing_type(self) -> None:
        value = [{"type": "Disk", "status": "True"}]
        assert not _op(value, "condition_status", {"type": "Ready", "status": "True"})

    def test_age_gt_true(self) -> None:
        ten_min_ago = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        assert _op(ten_min_ago, "age_gt", {"value": "5m"})

    def test_age_gt_false(self) -> None:
        one_min_ago = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
        assert not _op(one_min_ago, "age_gt", {"value": "5m"})

    def test_age_gt_none(self) -> None:
        assert not _op(None, "age_gt", {"value": "5m"})

    def test_list_values_any_semantics(self) -> None:
        """List values use any() — True if at least one element matches."""
        assert _op([1, 2, 10], "gt", {"value": 5})

    def test_list_values_all_fail(self) -> None:
        assert not _op([1, 2, 3], "gt", {"value": 5})

    def test_unknown_op(self) -> None:
        assert not _op("x", "nonexistent_op", {"value": "x"})


# ---------------------------------------------------------------------------
# PromQL operators
# ---------------------------------------------------------------------------


class TestPromQLOps:
    def _prom(self, return_value: float | None = None) -> MagicMock:
        client = MagicMock()
        client.query_value.return_value = return_value
        return client

    def test_promql_gt_true(self) -> None:
        client = self._prom(0.8)
        cond = {"query": "up{namespace='{namespace}'}", "value": 0.5}
        resource = {"namespace": "prod", "name": "app"}
        assert evaluate_op(None, "promql_gt", cond, NOW, resource, client)
        client.query_value.assert_called_once_with("up{namespace='prod'}")

    def test_promql_gt_false(self) -> None:
        client = self._prom(0.3)
        cond = {"query": "up{}", "value": 0.5}
        assert not evaluate_op(None, "promql_gt", cond, NOW, {}, client)

    def test_promql_lt_true(self) -> None:
        client = self._prom(0.3)
        cond = {"query": "up{}", "value": 0.5}
        assert evaluate_op(None, "promql_lt", cond, NOW, {}, client)

    def test_promql_lt_false(self) -> None:
        client = self._prom(0.8)
        cond = {"query": "up{}", "value": 0.5}
        assert not evaluate_op(None, "promql_lt", cond, NOW, {}, client)

    def test_promql_no_client_returns_false(self) -> None:
        cond = {"query": "up{}", "value": 0.5}
        assert not evaluate_op(None, "promql_gt", cond, NOW, {}, None)

    def test_promql_query_returns_none(self) -> None:
        client = self._prom(None)
        cond = {"query": "up{}", "value": 0.5}
        assert not evaluate_op(None, "promql_gt", cond, NOW, {}, client)


# ---------------------------------------------------------------------------
# evaluate_condition
# ---------------------------------------------------------------------------


class TestEvaluateCondition:
    def test_single_condition_match(self) -> None:
        resource = {"phase": "Pending"}
        cond = {"path": "phase", "op": "eq", "value": "Pending"}
        assert evaluate_condition(resource, cond, NOW)

    def test_single_condition_no_match(self) -> None:
        resource = {"phase": "Running"}
        cond = {"path": "phase", "op": "eq", "value": "Pending"}
        assert not evaluate_condition(resource, cond, NOW)

    def test_all_both_match(self) -> None:
        resource = {"phase": "Pending", "restarts": 10}
        cond = {
            "all": [
                {"path": "phase", "op": "eq", "value": "Pending"},
                {"path": "restarts", "op": "gt", "value": 5},
            ],
        }
        assert evaluate_condition(resource, cond, NOW)

    def test_all_one_fails(self) -> None:
        resource = {"phase": "Running", "restarts": 10}
        cond = {
            "all": [
                {"path": "phase", "op": "eq", "value": "Pending"},
                {"path": "restarts", "op": "gt", "value": 5},
            ],
        }
        assert not evaluate_condition(resource, cond, NOW)

    def test_any_one_matches(self) -> None:
        resource = {"phase": "Running", "restarts": 10}
        cond = {
            "any": [
                {"path": "phase", "op": "eq", "value": "Pending"},
                {"path": "restarts", "op": "gt", "value": 5},
            ],
        }
        assert evaluate_condition(resource, cond, NOW)

    def test_any_none_match(self) -> None:
        resource = {"phase": "Running", "restarts": 1}
        cond = {
            "any": [
                {"path": "phase", "op": "eq", "value": "Pending"},
                {"path": "restarts", "op": "gt", "value": 5},
            ],
        }
        assert not evaluate_condition(resource, cond, NOW)

    def test_missing_op_returns_false(self) -> None:
        assert not evaluate_condition({"a": 1}, {"path": "a"}, NOW)


# ---------------------------------------------------------------------------
# run_generic_checks — integration
# ---------------------------------------------------------------------------


def _pod_health_definition() -> Definition:
    """Build a Definition mimicking pod-health.md with structured checks."""
    return Definition(
        kind="scanner",
        name="pod-health",
        version="1.0.0",
        frontmatter={
            "kind": "scanner",
            "name": "pod-health",
            "version": "1.0.0",
            "resource_kinds": ["Pod"],
            "checks": [
                {
                    "id": "crash-loop-backoff",
                    "severity": "high",
                    "iterate": "containers[*]",
                    "condition": {
                        "all": [
                            {"path": "state.type", "op": "eq", "value": "waiting"},
                            {"path": "state.reason", "op": "eq", "value": "CrashLoopBackOff"},
                        ],
                    },
                    "resource_kind": "Pod",
                    "title_template": "Pod {namespace}/{name} in CrashLoopBackOff",
                    "payload_fields": ["name", "restart_count", "state.reason"],
                },
                {
                    "id": "oom-killed",
                    "severity": "critical",
                    "iterate": "containers[*]",
                    "condition": {
                        "all": [
                            {"path": "last_state.type", "op": "eq", "value": "terminated"},
                            {"path": "last_state.reason", "op": "eq", "value": "OOMKilled"},
                        ],
                    },
                    "resource_kind": "Pod",
                    "title_template": "Pod {namespace}/{name} OOMKilled",
                    "payload_fields": ["name", "last_state.exit_code"],
                },
                {
                    "id": "excessive-restarts",
                    "severity": "medium",
                    "iterate": "containers[*]",
                    "condition": {"path": "restart_count", "op": "gt", "value": 5},
                    "resource_kind": "Pod",
                    "title_template": "Pod {namespace}/{name} excessive restarts",
                    "payload_fields": ["name", "restart_count"],
                },
            ],
        },
        body="",
        source="test",
    )


class TestRunGenericChecks:
    def test_detects_crashloop(self) -> None:
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "app-1",
                "namespace": "ns1",
                "containers": [
                    {
                        "name": "main",
                        "restart_count": 3,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        assert len(obs) >= 1
        check_ids = {o.check_id for o in obs}
        assert "crash-loop-backoff" in check_ids
        crash_obs = next(o for o in obs if o.check_id == "crash-loop-backoff")
        assert crash_obs.severity == "high"
        assert crash_obs.scanner == "pod-health"
        assert crash_obs.resource_namespace == "ns1"
        assert crash_obs.resource_name == "app-1"
        assert crash_obs.fingerprint  # non-empty
        assert crash_obs.correlation_key  # non-empty

    def test_iterate_only_matching_elements(self) -> None:
        """iterate: containers[*] should produce observations only for matching containers."""
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "dual",
                "namespace": "prod",
                "containers": [
                    {
                        "name": "healthy",
                        "restart_count": 0,
                        "state": {"type": "running"},
                        "last_state": None,
                    },
                    {
                        "name": "crashing",
                        "restart_count": 8,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        crash_obs = [o for o in obs if o.check_id == "crash-loop-backoff"]
        assert len(crash_obs) == 1
        # excessive-restarts should also fire for the crashing container only
        restart_obs = [o for o in obs if o.check_id == "excessive-restarts"]
        assert len(restart_obs) == 1

    def test_no_matching_resources_returns_empty(self) -> None:
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "healthy",
                "namespace": "ns1",
                "containers": [
                    {
                        "name": "main",
                        "restart_count": 0,
                        "state": {"type": "running"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        assert obs == []

    def test_definition_without_checks_returns_empty(self) -> None:
        scanner_def = Definition(
            kind="scanner",
            name="empty",
            version="1.0.0",
            frontmatter={"kind": "scanner", "resource_kinds": ["Pod"]},
            body="",
            source="test",
        )
        obs = run_generic_checks([{"name": "x", "namespace": "y"}], "c1", scanner_def)
        assert obs == []

    def test_multiple_pods_multiple_checks(self) -> None:
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "crash-pod",
                "namespace": "prod",
                "containers": [
                    {
                        "name": "app",
                        "restart_count": 10,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        check_ids = {o.check_id for o in obs}
        assert "crash-loop-backoff" in check_ids
        assert "oom-killed" in check_ids
        assert "excessive-restarts" in check_ids

    def test_non_iterate_check(self) -> None:
        """A check without iterate evaluates against the resource directly."""
        scanner_def = Definition(
            kind="scanner",
            name="pending-check",
            version="1.0.0",
            frontmatter={
                "kind": "scanner",
                "resource_kinds": ["Pod"],
                "checks": [
                    {
                        "id": "pending-pod",
                        "severity": "medium",
                        "condition": {"path": "phase", "op": "eq", "value": "Pending"},
                        "resource_kind": "Pod",
                    },
                ],
            },
            body="",
            source="test",
        )
        pods = [{"name": "stuck", "namespace": "ns1", "phase": "Pending"}]
        obs = run_generic_checks(pods, "c1", scanner_def)
        assert len(obs) == 1
        assert obs[0].check_id == "pending-pod"

    def test_title_template_formatting(self) -> None:
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "app-1",
                "namespace": "ns1",
                "containers": [
                    {
                        "name": "main",
                        "restart_count": 3,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        crash_obs = next(o for o in obs if o.check_id == "crash-loop-backoff")
        assert crash_obs.title == "Pod ns1/app-1 in CrashLoopBackOff"

    def test_payload_fields_extracted(self) -> None:
        scanner_def = _pod_health_definition()
        pods = [
            {
                "name": "app-1",
                "namespace": "ns1",
                "containers": [
                    {
                        "name": "main",
                        "restart_count": 8,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, "cluster-1", scanner_def)
        crash_obs = next(o for o in obs if o.check_id == "crash-loop-backoff")
        assert crash_obs.payload.get("name") == "main"
        assert crash_obs.payload.get("restart_count") == 8
        assert crash_obs.payload.get("reason") == "CrashLoopBackOff"
