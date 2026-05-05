"""Edge case tests for generic scanner — None states, missing fields, empty containers."""

from pinky_worker.definitions.loader import Definition
from pinky_worker.observation.generic_scanner import run_generic_checks

SCANNER_DEF = Definition(
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
                "payload_fields": ["name", "restart_count"],
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
                "payload_fields": ["name"],
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
            {
                "id": "image-pull-error",
                "severity": "high",
                "iterate": "containers[*]",
                "condition": {
                    "path": "state.reason",
                    "op": "in",
                    "value": ["ImagePullBackOff", "ErrImagePull"],
                },
                "resource_kind": "Pod",
                "title_template": "Pod {namespace}/{name} image pull error",
                "payload_fields": ["name", "state.reason"],
            },
        ],
    },
    body="",
    source="test",
)


async def test_pod_with_no_containers() -> None:
    pods = [{"name": "empty", "namespace": "ns", "phase": "Pending", "containers": []}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


async def test_pod_with_none_state() -> None:
    pods = [{"name": "weird", "namespace": "ns", "containers": [
        {"name": "main", "restart_count": 0, "state": None, "last_state": None},
    ]}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


async def test_pod_with_empty_state_dict() -> None:
    pods = [{"name": "empty-state", "namespace": "ns", "containers": [
        {"name": "main", "restart_count": 0, "state": {}, "last_state": {}},
    ]}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


async def test_pod_missing_containers_key() -> None:
    pods = [{"name": "no-containers", "namespace": "ns", "phase": "Pending"}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    # iterate on containers[*] resolves to None → no observations
    assert obs == []


async def test_image_pull_error_inside_container_loop() -> None:
    pods = [{"name": "img-err", "namespace": "ns", "containers": [
        {"name": "app", "restart_count": 0, "state": {"type": "waiting", "reason": "ImagePullBackOff"}, "last_state": None},
    ]}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    assert len(obs) == 1
    assert obs[0].check_id == "image-pull-error"


async def test_multiple_containers_each_checked() -> None:
    pods = [{"name": "multi", "namespace": "ns", "containers": [
        {"name": "sidecar", "restart_count": 0, "state": {"type": "running"}, "last_state": None},
        {"name": "main", "restart_count": 10, "state": {"type": "waiting", "reason": "CrashLoopBackOff"}, "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137}},
    ]}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    check_ids = {o.check_id for o in obs}
    assert "crash-loop-backoff" in check_ids
    assert "oom-killed" in check_ids
    assert "excessive-restarts" in check_ids


async def test_restart_count_none_treated_as_zero() -> None:
    pods = [{"name": "null-restarts", "namespace": "ns", "containers": [
        {"name": "main", "restart_count": None, "state": {"type": "running"}, "last_state": None},
    ]}]
    obs = await run_generic_checks(pods, "c1", SCANNER_DEF)
    assert obs == []
