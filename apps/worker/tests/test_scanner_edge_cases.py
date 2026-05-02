"""Edge case tests for scanner runner — None states, missing fields, empty containers."""

from pinky_worker.definitions.loader import parse_md_definition
from pinky_worker.observation.scanner_runner import run_pod_health_checks

SCANNER_DEF = parse_md_definition("""---
name: pod-health
kind: scanner
version: 1.0.0
---
# Pod Health Scanner
""")


def test_pod_with_no_containers() -> None:
    pods = [{"name": "empty", "namespace": "ns", "phase": "Pending", "restart_count": 0, "containers": []}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


def test_pod_with_none_state() -> None:
    pods = [{"name": "weird", "namespace": "ns", "phase": "Running", "restart_count": 0, "containers": [
        {"name": "main", "ready": True, "restart_count": 0, "state": None, "last_state": None}
    ]}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


def test_pod_with_empty_state_dict() -> None:
    pods = [{"name": "empty-state", "namespace": "ns", "phase": "Running", "restart_count": 0, "containers": [
        {"name": "main", "ready": True, "restart_count": 0, "state": {}, "last_state": {}}
    ]}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


def test_pod_missing_containers_key() -> None:
    pods = [{"name": "no-containers", "namespace": "ns", "phase": "Pending", "restart_count": 0}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert obs == []


def test_image_pull_error_inside_container_loop() -> None:
    pods = [{"name": "img-err", "namespace": "ns", "phase": "Pending", "restart_count": 0, "containers": [
        {"name": "app", "ready": False, "restart_count": 0, "state": {"type": "waiting", "reason": "ImagePullBackOff"}, "last_state": None}
    ]}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert len(obs) == 1
    assert obs[0].check_id == "image-pull-error"


def test_multiple_containers_each_checked() -> None:
    pods = [{"name": "multi", "namespace": "ns", "phase": "Running", "restart_count": 12, "containers": [
        {"name": "sidecar", "ready": True, "restart_count": 0, "state": {"type": "running"}, "last_state": None},
        {"name": "main", "ready": False, "restart_count": 10, "state": {"type": "waiting", "reason": "CrashLoopBackOff"}, "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137}},
    ]}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    check_ids = {o.check_id for o in obs}
    assert "crash-loop-backoff" in check_ids
    assert "oom-killed" in check_ids
    assert "excessive-restarts" in check_ids
    # sidecar should produce no observations
    assert all(o.payload.get("container") == "main" for o in obs)


def test_restart_count_none_treated_as_zero() -> None:
    pods = [{"name": "null-restarts", "namespace": "ns", "phase": "Running", "restart_count": 0, "containers": [
        {"name": "main", "ready": True, "restart_count": None, "state": {"type": "running"}, "last_state": None}
    ]}]
    obs = run_pod_health_checks(pods, "c1", SCANNER_DEF)
    assert obs == []
