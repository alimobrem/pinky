"""Tests for scanner runner — pod health checks against mock K8s data."""

from pinky_worker.definitions.loader import parse_md_definition
from pinky_worker.observation.scanner_runner import run_pod_health_checks

SCANNER_MD = """---
name: pod-health
kind: scanner
version: 1.0.0
resource_kinds: [Pod]
---
# Pod Health Scanner
"""

SCANNER_DEF = parse_md_definition(SCANNER_MD)


def _pod(name: str, namespace: str = "default", containers: list | None = None) -> dict:
    return {
        "name": name,
        "namespace": namespace,
        "phase": "Running",
        "restart_count": sum(c.get("restart_count", 0) for c in (containers or [])),
        "containers": containers or [],
    }


def test_detects_crashloop() -> None:
    pods = [_pod("app-1", "ns1", containers=[{
        "name": "main",
        "ready": False,
        "restart_count": 3,
        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
        "last_state": None,
    }])]
    obs = run_pod_health_checks(pods, "cluster-1", SCANNER_DEF)
    assert len(obs) == 1
    assert obs[0].check_id == "crash-loop-backoff"
    assert obs[0].severity == "high"


def test_detects_oom_killed() -> None:
    pods = [_pod("app-2", "ns1", containers=[{
        "name": "main",
        "ready": True,
        "restart_count": 1,
        "state": {"type": "running"},
        "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
    }])]
    obs = run_pod_health_checks(pods, "cluster-1", SCANNER_DEF)
    assert len(obs) == 1
    assert obs[0].check_id == "oom-killed"
    assert obs[0].severity == "critical"


def test_detects_excessive_restarts() -> None:
    pods = [_pod("app-3", "ns1", containers=[{
        "name": "main",
        "ready": True,
        "restart_count": 10,
        "state": {"type": "running"},
        "last_state": None,
    }])]
    obs = run_pod_health_checks(pods, "cluster-1", SCANNER_DEF)
    assert len(obs) == 1
    assert obs[0].check_id == "excessive-restarts"


def test_healthy_pod_produces_no_observations() -> None:
    pods = [_pod("healthy", "ns1", containers=[{
        "name": "main",
        "ready": True,
        "restart_count": 0,
        "state": {"type": "running"},
        "last_state": None,
    }])]
    obs = run_pod_health_checks(pods, "cluster-1", SCANNER_DEF)
    assert len(obs) == 0


def test_multiple_issues_on_same_pod() -> None:
    pods = [_pod("troubled", "ns1", containers=[{
        "name": "main",
        "ready": False,
        "restart_count": 10,
        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
        "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
    }])]
    obs = run_pod_health_checks(pods, "cluster-1", SCANNER_DEF)
    check_ids = {o.check_id for o in obs}
    assert "crash-loop-backoff" in check_ids
    assert "oom-killed" in check_ids
    assert "excessive-restarts" in check_ids
