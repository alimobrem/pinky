"""Tests for scanner runner — health checks against mock K8s data."""

from datetime import UTC, datetime, timedelta

from pinky_worker.definitions.loader import parse_md_definition
from pinky_worker.observation.scanner_runner import (
    run_daemonset_health_checks,
    run_job_health_checks,
    run_pod_health_checks,
    run_service_endpoint_checks,
    run_statefulset_health_checks,
)

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


# ---------------------------------------------------------------------------
# StatefulSet health checks
# ---------------------------------------------------------------------------

STS_SCANNER_MD = """---
name: statefulset-health
kind: scanner
version: 1.0.0
resource_kinds: [StatefulSet]
---
# StatefulSet Health Scanner
"""
STS_SCANNER_DEF = parse_md_definition(STS_SCANNER_MD)


def test_sts_rollout_stuck() -> None:
    items = [{
        "name": "db",
        "namespace": "prod",
        "replicas": 3,
        "ready_replicas": 3,
        "updated_replicas": 1,
        "current_replicas": 3,
        "current_revision": "rev-1",
        "update_revision": "rev-2",
    }]
    obs = run_statefulset_health_checks(items, "c1", STS_SCANNER_DEF)
    check_ids = {o.check_id for o in obs}
    assert "sts-rollout-stuck" in check_ids


def test_sts_replicas_unavailable() -> None:
    items = [{
        "name": "cache",
        "namespace": "prod",
        "replicas": 3,
        "ready_replicas": 1,
        "updated_replicas": 3,
        "current_replicas": 3,
        "current_revision": "rev-1",
        "update_revision": "rev-1",
    }]
    obs = run_statefulset_health_checks(items, "c1", STS_SCANNER_DEF)
    assert any(o.check_id == "sts-replicas-unavailable" for o in obs)


def test_healthy_statefulset() -> None:
    items = [{
        "name": "ok",
        "namespace": "prod",
        "replicas": 3,
        "ready_replicas": 3,
        "updated_replicas": 3,
        "current_replicas": 3,
        "current_revision": "rev-1",
        "update_revision": "rev-1",
    }]
    obs = run_statefulset_health_checks(items, "c1", STS_SCANNER_DEF)
    assert len(obs) == 0


# ---------------------------------------------------------------------------
# Job / CronJob health checks
# ---------------------------------------------------------------------------

JOB_SCANNER_MD = """---
name: job-health
kind: scanner
version: 1.0.0
resource_kinds: [Job, CronJob]
---
# Job Health Scanner
"""
JOB_SCANNER_DEF = parse_md_definition(JOB_SCANNER_MD)


def test_job_failed() -> None:
    items = [{
        "kind": "Job",
        "name": "migrate",
        "namespace": "prod",
        "succeeded": 0,
        "failed": 6,
        "backoff_limit": 6,
        "conditions": [],
    }]
    obs = run_job_health_checks(items, "c1", JOB_SCANNER_DEF)
    assert any(o.check_id == "job-failed" for o in obs)


def test_job_deadline_exceeded() -> None:
    items = [{
        "kind": "Job",
        "name": "batch",
        "namespace": "prod",
        "succeeded": 0,
        "failed": 0,
        "backoff_limit": 6,
        "conditions": [{"type": "DeadlineExceeded", "status": "True", "reason": ""}],
    }]
    obs = run_job_health_checks(items, "c1", JOB_SCANNER_DEF)
    assert any(o.check_id == "job-deadline-exceeded" for o in obs)


def test_cronjob_missed() -> None:
    old_time = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    items = [{
        "kind": "CronJob",
        "name": "cleanup",
        "namespace": "prod",
        "schedule": "*/5 * * * *",
        "last_schedule_time": old_time,
    }]
    obs = run_job_health_checks(items, "c1", JOB_SCANNER_DEF)
    assert any(o.check_id == "cronjob-missed" for o in obs)


def test_healthy_job() -> None:
    items = [{
        "kind": "Job",
        "name": "ok",
        "namespace": "prod",
        "succeeded": 1,
        "failed": 0,
        "backoff_limit": 6,
        "conditions": [],
    }]
    obs = run_job_health_checks(items, "c1", JOB_SCANNER_DEF)
    assert len(obs) == 0


# ---------------------------------------------------------------------------
# Service endpoint checks
# ---------------------------------------------------------------------------

SVC_SCANNER_MD = """---
name: service-endpoints
kind: scanner
version: 1.0.0
resource_kinds: [Service]
---
# Service Endpoint Scanner
"""
SVC_SCANNER_DEF = parse_md_definition(SVC_SCANNER_MD)


def test_service_no_endpoints() -> None:
    items = [{
        "name": "api",
        "namespace": "prod",
        "type": "ClusterIP",
        "selector": {"app": "api"},
        "ready_endpoints": 0,
        "not_ready_endpoints": 0,
    }]
    obs = run_service_endpoint_checks(items, "c1", SVC_SCANNER_DEF)
    assert any(o.check_id == "service-no-endpoints" for o in obs)


def test_service_partial_endpoints() -> None:
    items = [{
        "name": "web",
        "namespace": "prod",
        "type": "ClusterIP",
        "selector": {"app": "web"},
        "ready_endpoints": 1,
        "not_ready_endpoints": 3,
    }]
    obs = run_service_endpoint_checks(items, "c1", SVC_SCANNER_DEF)
    assert any(o.check_id == "service-partial-endpoints" for o in obs)


def test_service_no_selector_skipped() -> None:
    items = [{
        "name": "external",
        "namespace": "prod",
        "type": "ExternalName",
        "selector": {},
        "ready_endpoints": 0,
        "not_ready_endpoints": 0,
    }]
    obs = run_service_endpoint_checks(items, "c1", SVC_SCANNER_DEF)
    assert len(obs) == 0


def test_healthy_service() -> None:
    items = [{
        "name": "ok",
        "namespace": "prod",
        "type": "ClusterIP",
        "selector": {"app": "ok"},
        "ready_endpoints": 3,
        "not_ready_endpoints": 0,
    }]
    obs = run_service_endpoint_checks(items, "c1", SVC_SCANNER_DEF)
    assert len(obs) == 0


# ---------------------------------------------------------------------------
# DaemonSet health checks
# ---------------------------------------------------------------------------

DS_SCANNER_MD = """---
name: daemonset-health
kind: scanner
version: 1.0.0
resource_kinds: [DaemonSet]
---
# DaemonSet Health Scanner
"""
DS_SCANNER_DEF = parse_md_definition(DS_SCANNER_MD)


def test_daemonset_unavailable() -> None:
    items = [{
        "name": "node-exporter",
        "namespace": "monitoring",
        "desired": 5,
        "current": 5,
        "ready": 3,
        "number_unavailable": 2,
        "number_misscheduled": 0,
    }]
    obs = run_daemonset_health_checks(items, "c1", DS_SCANNER_DEF)
    assert any(o.check_id == "daemonset-unavailable" for o in obs)


def test_daemonset_misscheduled() -> None:
    items = [{
        "name": "fluentd",
        "namespace": "logging",
        "desired": 3,
        "current": 3,
        "ready": 3,
        "number_unavailable": 0,
        "number_misscheduled": 1,
    }]
    obs = run_daemonset_health_checks(items, "c1", DS_SCANNER_DEF)
    assert any(o.check_id == "daemonset-misscheduled" for o in obs)


def test_daemonset_desired_mismatch() -> None:
    items = [{
        "name": "kube-proxy",
        "namespace": "kube-system",
        "desired": 5,
        "current": 3,
        "ready": 3,
        "number_unavailable": 0,
        "number_misscheduled": 0,
    }]
    obs = run_daemonset_health_checks(items, "c1", DS_SCANNER_DEF)
    assert any(o.check_id == "daemonset-desired-mismatch" for o in obs)


def test_healthy_daemonset() -> None:
    items = [{
        "name": "ok",
        "namespace": "kube-system",
        "desired": 3,
        "current": 3,
        "ready": 3,
        "number_unavailable": 0,
        "number_misscheduled": 0,
    }]
    obs = run_daemonset_health_checks(items, "c1", DS_SCANNER_DEF)
    assert len(obs) == 0
