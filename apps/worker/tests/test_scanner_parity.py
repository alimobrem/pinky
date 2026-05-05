"""Scanner parity tests — runs real scanner definitions against synthetic K8s data.

Each test loads the actual scanner definition from definitions/scanners/,
builds resource dicts matching the k8s_client summary shapes, runs
run_generic_checks, and asserts correct observations.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from pinky_worker.definitions.loader import Definition, parse_md_definition
from pinky_worker.observation.generic_scanner import run_generic_checks

DEFINITIONS_DIR = Path(__file__).parent.parent.parent.parent / "definitions"
CLUSTER = "test-cluster-1"


def _load_scanner(name: str) -> Definition:
    path = DEFINITIONS_DIR / "scanners" / f"{name}.md"
    return parse_md_definition(path.read_text(), source="filesystem")


# ---------------------------------------------------------------------------
# pod-health scanner
# ---------------------------------------------------------------------------


class TestPodHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("pod-health")

    def test_crashloop_detected(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "web-abc",
                "namespace": "prod",
                "phase": "Running",
                "creation_timestamp": datetime.now(UTC).isoformat(),
                "restart_count": 5,
                "containers": [
                    {
                        "name": "web",
                        "ready": False,
                        "restart_count": 5,
                        "state": {"type": "waiting", "reason": "CrashLoopBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        crash = [o for o in obs if o.check_id == "crash-loop-backoff"]
        assert len(crash) == 1
        assert crash[0].severity == "high"
        assert crash[0].resource_name == "web-abc"

    def test_oom_killed_detected(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "worker-xyz",
                "namespace": "prod",
                "phase": "Running",
                "creation_timestamp": datetime.now(UTC).isoformat(),
                "restart_count": 3,
                "containers": [
                    {
                        "name": "worker",
                        "ready": True,
                        "restart_count": 3,
                        "state": {"type": "running"},
                        "last_state": {"type": "terminated", "reason": "OOMKilled", "exit_code": 137},
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        oom = [o for o in obs if o.check_id == "oom-killed"]
        assert len(oom) == 1
        assert oom[0].severity == "critical"

    def test_healthy_pod_no_observations(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "healthy",
                "namespace": "prod",
                "phase": "Running",
                "creation_timestamp": datetime.now(UTC).isoformat(),
                "restart_count": 0,
                "containers": [
                    {
                        "name": "app",
                        "ready": True,
                        "restart_count": 0,
                        "state": {"type": "running"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        assert obs == []

    def test_excessive_restarts(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "flaky",
                "namespace": "staging",
                "phase": "Running",
                "creation_timestamp": datetime.now(UTC).isoformat(),
                "restart_count": 10,
                "containers": [
                    {
                        "name": "app",
                        "ready": True,
                        "restart_count": 10,
                        "state": {"type": "running"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        restarts = [o for o in obs if o.check_id == "excessive-restarts"]
        assert len(restarts) == 1
        assert restarts[0].severity == "medium"

    def test_image_pull_backoff(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "bad-image",
                "namespace": "dev",
                "phase": "Pending",
                "creation_timestamp": datetime.now(UTC).isoformat(),
                "restart_count": 0,
                "containers": [
                    {
                        "name": "app",
                        "ready": False,
                        "restart_count": 0,
                        "state": {"type": "waiting", "reason": "ImagePullBackOff"},
                        "last_state": None,
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        img = [o for o in obs if o.check_id == "image-pull-error"]
        assert len(img) == 1
        assert img[0].severity == "high"

    def test_pending_too_long(self, scanner: Definition) -> None:
        old_ts = (datetime.now(UTC) - timedelta(minutes=10)).isoformat()
        pods = [
            {
                "name": "stuck",
                "namespace": "prod",
                "phase": "Pending",
                "creation_timestamp": old_ts,
                "restart_count": 0,
                "containers": [],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        pending = [o for o in obs if o.check_id == "pending-too-long"]
        assert len(pending) == 1
        assert pending[0].severity == "medium"

    def test_pending_recently_created_no_observation(self, scanner: Definition) -> None:
        recent_ts = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
        pods = [
            {
                "name": "new-pod",
                "namespace": "prod",
                "phase": "Pending",
                "creation_timestamp": recent_ts,
                "restart_count": 0,
                "containers": [],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        pending = [o for o in obs if o.check_id == "pending-too-long"]
        assert len(pending) == 0


# ---------------------------------------------------------------------------
# node-conditions scanner
# ---------------------------------------------------------------------------


class TestNodeConditionsScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("node-conditions")

    def test_memory_pressure(self, scanner: Definition) -> None:
        nodes = [
            {
                "name": "node-1",
                "unschedulable": False,
                "conditions": [
                    {"type": "Ready", "status": "True", "reason": ""},
                    {"type": "MemoryPressure", "status": "True", "reason": "EvictionThresholdMet"},
                ],
            },
        ]
        obs = run_generic_checks(nodes, CLUSTER, scanner)
        mp = [o for o in obs if o.check_id == "memory-pressure"]
        assert len(mp) == 1
        assert mp[0].severity == "high"

    def test_not_ready(self, scanner: Definition) -> None:
        nodes = [
            {
                "name": "node-2",
                "unschedulable": False,
                "conditions": [
                    {"type": "Ready", "status": "False", "reason": "KubeletNotReady"},
                ],
            },
        ]
        obs = run_generic_checks(nodes, CLUSTER, scanner)
        nr = [o for o in obs if o.check_id == "not-ready"]
        assert len(nr) == 1
        assert nr[0].severity == "critical"

    def test_unschedulable(self, scanner: Definition) -> None:
        nodes = [
            {
                "name": "node-3",
                "unschedulable": True,
                "conditions": [
                    {"type": "Ready", "status": "True", "reason": ""},
                ],
            },
        ]
        obs = run_generic_checks(nodes, CLUSTER, scanner)
        unsched = [o for o in obs if o.check_id == "unschedulable"]
        assert len(unsched) == 1
        assert unsched[0].severity == "medium"

    def test_healthy_node_no_observations(self, scanner: Definition) -> None:
        nodes = [
            {
                "name": "node-ok",
                "unschedulable": False,
                "conditions": [
                    {"type": "Ready", "status": "True", "reason": ""},
                    {"type": "MemoryPressure", "status": "False", "reason": ""},
                    {"type": "DiskPressure", "status": "False", "reason": ""},
                    {"type": "PIDPressure", "status": "False", "reason": ""},
                ],
            },
        ]
        obs = run_generic_checks(nodes, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# deployment-health scanner
# ---------------------------------------------------------------------------


class TestDeploymentHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("deployment-health")

    def test_rollout_stalled(self, scanner: Definition) -> None:
        deps = [
            {
                "name": "api",
                "namespace": "prod",
                "desired_replicas": 3,
                "ready_replicas": 1,
                "unavailable_replicas": 2,
                "conditions": [
                    {"type": "Progressing", "status": "False", "reason": "ProgressDeadlineExceeded", "message": ""},
                ],
            },
        ]
        obs = run_generic_checks(deps, CLUSTER, scanner)
        stalled = [o for o in obs if o.check_id == "rollout-stalled"]
        assert len(stalled) == 1
        assert stalled[0].severity == "high"

    def test_unavailable_replicas(self, scanner: Definition) -> None:
        deps = [
            {
                "name": "web",
                "namespace": "prod",
                "desired_replicas": 3,
                "ready_replicas": 1,
                "unavailable_replicas": 2,
                "conditions": [
                    {"type": "Progressing", "status": "True", "reason": "NewReplicaSetAvailable", "message": ""},
                ],
            },
        ]
        obs = run_generic_checks(deps, CLUSTER, scanner)
        unavail = [o for o in obs if o.check_id == "replicas-unavailable"]
        assert len(unavail) == 1
        assert unavail[0].severity == "high"

    def test_healthy_deployment_no_observations(self, scanner: Definition) -> None:
        deps = [
            {
                "name": "stable",
                "namespace": "prod",
                "desired_replicas": 3,
                "ready_replicas": 3,
                "unavailable_replicas": 0,
                "conditions": [
                    {"type": "Progressing", "status": "True", "reason": "NewReplicaSetAvailable", "message": ""},
                    {"type": "Available", "status": "True", "reason": "", "message": ""},
                ],
            },
        ]
        obs = run_generic_checks(deps, CLUSTER, scanner)
        assert obs == []

    def test_replica_mismatch(self, scanner: Definition) -> None:
        """replica-mismatch check uses value_from to compare ready_replicas < replicas.

        This documents the current behavior: the check silently returns False.
        """
        deps = [
            {
                "name": "mismatched",
                "namespace": "prod",
                "desired_replicas": 3,
                "replicas": 3,
                "ready_replicas": 1,
                "unavailable_replicas": 0,
                "conditions": [
                    {"type": "Progressing", "status": "True", "reason": "", "message": ""},
                ],
            },
        ]
        obs = run_generic_checks(deps, CLUSTER, scanner)
        mismatch = [o for o in obs if o.check_id == "replica-mismatch"]
        assert len(mismatch) == 1
        assert mismatch[0].severity == "medium"


# ---------------------------------------------------------------------------
# cert-expiry scanner
# ---------------------------------------------------------------------------


class TestCertExpiryScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("cert-expiry")

    def test_no_cert_data_no_observations(self, scanner: Definition) -> None:
        secrets = [
            {
                "name": "my-tls",
                "namespace": "prod",
                "data_keys": ["tls.crt", "tls.key"],
                "tls_crt": None,
            },
        ]
        obs = run_generic_checks(secrets, CLUSTER, scanner)
        assert obs == []

    def test_empty_cert_no_observations(self, scanner: Definition) -> None:
        secrets = [
            {
                "name": "empty-tls",
                "namespace": "prod",
                "data_keys": ["tls.crt"],
                "tls_crt": "",
            },
        ]
        obs = run_generic_checks(secrets, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# pvc-health scanner
# ---------------------------------------------------------------------------


class TestPvcHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("pvc-health")

    def test_pvc_pending(self, scanner: Definition) -> None:
        pvcs = [
            {"name": "data-vol", "namespace": "prod", "phase": "Pending"},
        ]
        obs = run_generic_checks(pvcs, CLUSTER, scanner)
        pending = [o for o in obs if o.check_id == "pvc-pending"]
        assert len(pending) == 1
        assert pending[0].severity == "high"

    def test_pvc_lost(self, scanner: Definition) -> None:
        pvcs = [
            {"name": "data-vol", "namespace": "prod", "phase": "Lost"},
        ]
        obs = run_generic_checks(pvcs, CLUSTER, scanner)
        lost = [o for o in obs if o.check_id == "pvc-lost"]
        assert len(lost) == 1
        assert lost[0].severity == "critical"

    def test_bound_pvc_no_observations(self, scanner: Definition) -> None:
        pvcs = [
            {"name": "healthy-vol", "namespace": "prod", "phase": "Bound"},
        ]
        obs = run_generic_checks(pvcs, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# resource-quotas scanner
# ---------------------------------------------------------------------------


class TestResourceQuotasScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("resource-quotas")

    def test_quota_exceeded_with_scalar_paths(self, scanner: Definition) -> None:
        """quantity_gte works when used_path/hard_path resolve to scalar values."""
        quotas = [
            {
                "name": "cpu-quota",
                "namespace": "team-a",
                "hard": "10",
                "used": "10",
            },
        ]
        obs = run_generic_checks(quotas, CLUSTER, scanner)
        exceeded = [o for o in obs if o.check_id == "quota-exceeded"]
        assert len(exceeded) == 1
        assert exceeded[0].severity == "high"

    def test_quota_dict_values_do_not_fire(self, scanner: Definition) -> None:
        """When used/hard are dicts (real k8s shape), quantity_gte can't parse them.

        This documents the current limitation: the operator tries to parse
        the entire dict as a single quantity string, which fails silently.
        """
        quotas = [
            {
                "name": "team-quota",
                "namespace": "team-a",
                "hard": {"cpu": "10", "memory": "20Gi"},
                "used": {"cpu": "10", "memory": "20Gi"},
            },
        ]
        obs = run_generic_checks(quotas, CLUSTER, scanner)
        exceeded = [o for o in obs if o.check_id == "quota-exceeded"]
        assert len(exceeded) == 0

    def test_quota_under_limit_no_observations(self, scanner: Definition) -> None:
        quotas = [
            {
                "name": "cpu-quota",
                "namespace": "team-a",
                "hard": "10",
                "used": "2",
            },
        ]
        obs = run_generic_checks(quotas, CLUSTER, scanner)
        exceeded = [o for o in obs if o.check_id == "quota-exceeded"]
        assert len(exceeded) == 0

    def test_quota_near_limit(self, scanner: Definition) -> None:
        quotas = [
            {
                "name": "cpu-quota",
                "namespace": "team-a",
                "hard": "10",
                "used": "9",
            },
        ]
        obs = run_generic_checks(quotas, CLUSTER, scanner)
        near = [o for o in obs if o.check_id == "quota-near-limit"]
        assert len(near) == 1
        assert near[0].severity == "medium"


# ---------------------------------------------------------------------------
# ingress-health scanner
# ---------------------------------------------------------------------------


class TestIngressHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("ingress-health")

    def test_ingress_no_backend(self, scanner: Definition) -> None:
        """Ingress with endpoints_ready=0 should fire."""
        ingresses = [
            {
                "name": "app-ingress",
                "namespace": "prod",
                "endpoints_ready": 0,
                "rules": [
                    {"host": "app.example.com", "path": "/", "service_name": "app", "service_port": 8080},
                ],
            },
        ]
        obs = run_generic_checks(ingresses, CLUSTER, scanner)
        no_backend = [o for o in obs if o.check_id == "ingress-no-backend"]
        assert len(no_backend) == 1
        assert no_backend[0].severity == "high"

    def test_ingress_with_backends_no_observations(self, scanner: Definition) -> None:
        ingresses = [
            {
                "name": "healthy-ingress",
                "namespace": "prod",
                "endpoints_ready": 3,
                "rules": [
                    {"host": "app.example.com", "path": "/", "service_name": "app", "service_port": 8080},
                ],
            },
        ]
        obs = run_generic_checks(ingresses, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# statefulset-health scanner
# ---------------------------------------------------------------------------


class TestStatefulsetHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("statefulset-health")

    def test_rollout_stuck(self, scanner: Definition) -> None:
        sts = [
            {
                "name": "db",
                "namespace": "prod",
                "replicas": 3,
                "ready_replicas": 1,
                "updated_replicas": 1,
                "current_replicas": 3,
                "current_revision": "rev-1",
                "update_revision": "rev-2",
            },
        ]
        obs = run_generic_checks(sts, CLUSTER, scanner)
        stuck = [o for o in obs if o.check_id == "sts-rollout-stuck"]
        assert len(stuck) == 1
        assert stuck[0].severity == "high"

    def test_replicas_unavailable(self, scanner: Definition) -> None:
        sts = [
            {
                "name": "cache",
                "namespace": "prod",
                "replicas": 3,
                "ready_replicas": 1,
                "updated_replicas": 3,
                "current_replicas": 3,
                "current_revision": "rev-1",
                "update_revision": "rev-1",
            },
        ]
        obs = run_generic_checks(sts, CLUSTER, scanner)
        unavail = [o for o in obs if o.check_id == "sts-replicas-unavailable"]
        assert len(unavail) == 1
        assert unavail[0].severity == "high"

    def test_healthy_statefulset(self, scanner: Definition) -> None:
        sts = [
            {
                "name": "db",
                "namespace": "prod",
                "replicas": 3,
                "ready_replicas": 3,
                "updated_replicas": 3,
                "current_replicas": 3,
                "current_revision": "rev-1",
                "update_revision": "rev-1",
            },
        ]
        obs = run_generic_checks(sts, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# job-health scanner
# ---------------------------------------------------------------------------


class TestJobHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("job-health")

    def test_job_failed(self, scanner: Definition) -> None:
        jobs = [
            {
                "kind": "Job",
                "name": "migration",
                "namespace": "prod",
                "succeeded": 0,
                "failed": 6,
                "backoff_limit": 6,
                "conditions": [],
            },
        ]
        obs = run_generic_checks(jobs, CLUSTER, scanner)
        failed = [o for o in obs if o.check_id == "job-failed"]
        assert len(failed) == 1
        assert failed[0].severity == "high"

    def test_job_deadline_exceeded(self, scanner: Definition) -> None:
        jobs = [
            {
                "kind": "Job",
                "name": "etl",
                "namespace": "prod",
                "succeeded": 0,
                "failed": 1,
                "backoff_limit": 6,
                "conditions": [
                    {"type": "DeadlineExceeded", "status": "True", "reason": "DeadlineExceeded"},
                ],
            },
        ]
        obs = run_generic_checks(jobs, CLUSTER, scanner)
        deadline = [o for o in obs if o.check_id == "job-deadline-exceeded"]
        assert len(deadline) == 1
        assert deadline[0].severity == "high"

    def test_cronjob_missed_schedule(self, scanner: Definition) -> None:
        old_schedule = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
        cronjobs = [
            {
                "kind": "CronJob",
                "name": "cleanup",
                "namespace": "prod",
                "schedule": "0 * * * *",
                "last_schedule_time": old_schedule,
            },
        ]
        obs = run_generic_checks(cronjobs, CLUSTER, scanner)
        missed = [o for o in obs if o.check_id == "cronjob-missed"]
        assert len(missed) == 1
        assert missed[0].severity == "medium"

    def test_cronjob_recent_schedule_no_observation(self, scanner: Definition) -> None:
        recent = (datetime.now(UTC) - timedelta(minutes=30)).isoformat()
        cronjobs = [
            {
                "kind": "CronJob",
                "name": "backup",
                "namespace": "prod",
                "schedule": "0 * * * *",
                "last_schedule_time": recent,
            },
        ]
        obs = run_generic_checks(cronjobs, CLUSTER, scanner)
        missed = [o for o in obs if o.check_id == "cronjob-missed"]
        assert len(missed) == 0

    def test_healthy_job_no_observations(self, scanner: Definition) -> None:
        jobs = [
            {
                "kind": "Job",
                "name": "seed",
                "namespace": "prod",
                "succeeded": 1,
                "failed": 0,
                "backoff_limit": 6,
                "conditions": [
                    {"type": "Complete", "status": "True", "reason": ""},
                ],
            },
        ]
        obs = run_generic_checks(jobs, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# service-endpoints scanner
# ---------------------------------------------------------------------------


class TestServiceEndpointsScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("service-endpoints")

    def test_service_no_endpoints(self, scanner: Definition) -> None:
        services = [
            {
                "name": "api",
                "namespace": "prod",
                "type": "ClusterIP",
                "selector": {"app": "api"},
                "has_selector": True,
                "endpoints_ready": 0,
                "endpoints_not_ready": 0,
                "not_ready_endpoints": 0,
            },
        ]
        obs = run_generic_checks(services, CLUSTER, scanner)
        no_ep = [o for o in obs if o.check_id == "service-no-endpoints"]
        assert len(no_ep) == 1
        assert no_ep[0].severity == "high"

    def test_service_without_selector_no_observations(self, scanner: Definition) -> None:
        """Services without a selector (e.g. ExternalName) should not fire."""
        services = [
            {
                "name": "external",
                "namespace": "prod",
                "type": "ExternalName",
                "selector": {},
                "has_selector": False,
                "endpoints_ready": 0,
                "endpoints_not_ready": 0,
                "not_ready_endpoints": 0,
            },
        ]
        obs = run_generic_checks(services, CLUSTER, scanner)
        no_ep = [o for o in obs if o.check_id == "service-no-endpoints"]
        assert len(no_ep) == 0

    def test_service_with_endpoints_no_observations(self, scanner: Definition) -> None:
        services = [
            {
                "name": "web",
                "namespace": "prod",
                "type": "ClusterIP",
                "selector": {"app": "web"},
                "has_selector": True,
                "endpoints_ready": 3,
                "endpoints_not_ready": 0,
                "not_ready_endpoints": 0,
            },
        ]
        obs = run_generic_checks(services, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# daemonset-health scanner
# ---------------------------------------------------------------------------


class TestDaemonsetHealthScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("daemonset-health")

    def test_daemonset_unavailable(self, scanner: Definition) -> None:
        dsets = [
            {
                "name": "fluentd",
                "namespace": "logging",
                "desired": 5,
                "current": 5,
                "ready": 3,
                "number_unavailable": 2,
                "number_misscheduled": 0,
            },
        ]
        obs = run_generic_checks(dsets, CLUSTER, scanner)
        unavail = [o for o in obs if o.check_id == "daemonset-unavailable"]
        assert len(unavail) == 1
        assert unavail[0].severity == "high"

    def test_healthy_daemonset_no_observations(self, scanner: Definition) -> None:
        dsets = [
            {
                "name": "node-exporter",
                "namespace": "monitoring",
                "desired": 5,
                "current": 5,
                "ready": 5,
                "number_unavailable": 0,
                "number_misscheduled": 0,
            },
        ]
        obs = run_generic_checks(dsets, CLUSTER, scanner)
        assert obs == []

    def test_daemonset_misscheduled(self, scanner: Definition) -> None:
        dsets = [
            {
                "name": "kube-proxy",
                "namespace": "kube-system",
                "desired": 3,
                "current": 3,
                "ready": 3,
                "number_unavailable": 0,
                "number_misscheduled": 1,
            },
        ]
        obs = run_generic_checks(dsets, CLUSTER, scanner)
        missched = [o for o in obs if o.check_id == "daemonset-misscheduled"]
        assert len(missched) == 1
        assert missched[0].severity == "medium"

    def test_desired_mismatch(self, scanner: Definition) -> None:
        dsets = [
            {
                "name": "agent",
                "namespace": "monitoring",
                "desired": 5,
                "desired_number_scheduled": 5,
                "current": 3,
                "current_number_scheduled": 3,
                "ready": 3,
                "number_unavailable": 0,
                "number_misscheduled": 0,
            },
        ]
        obs = run_generic_checks(dsets, CLUSTER, scanner)
        mismatch = [o for o in obs if o.check_id == "daemonset-desired-mismatch"]
        assert len(mismatch) == 1
        assert mismatch[0].severity == "medium"


# ---------------------------------------------------------------------------
# pod-resource-usage scanner (PromQL-based, no prom_client → no observations)
# ---------------------------------------------------------------------------


class TestPodResourceUsageScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("pod-resource-usage")

    def test_no_prom_client_no_observations(self, scanner: Definition) -> None:
        """PromQL checks return False when no prom_client is provided."""
        pods = [
            {"name": "app", "namespace": "prod", "phase": "Running"},
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        assert obs == []


# ---------------------------------------------------------------------------
# resource-limits scanner
# ---------------------------------------------------------------------------


class TestResourceLimitsScanner:
    @pytest.fixture
    def scanner(self) -> Definition:
        return _load_scanner("resource-limits")

    def test_no_resource_limits(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "no-limits",
                "namespace": "dev",
                "containers": [
                    {"name": "app", "resources": {"limits": None, "requests": None}},
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        no_limits = [o for o in obs if o.check_id == "no-resource-limits"]
        assert len(no_limits) == 1
        assert no_limits[0].severity == "medium"

    def test_has_limits_no_observations(self, scanner: Definition) -> None:
        pods = [
            {
                "name": "with-limits",
                "namespace": "prod",
                "containers": [
                    {
                        "name": "app",
                        "resources": {
                            "limits": {"cpu": "500m", "memory": "256Mi"},
                            "requests": {"cpu": "100m", "memory": "128Mi"},
                        },
                    },
                ],
            },
        ]
        obs = run_generic_checks(pods, CLUSTER, scanner)
        assert obs == []
