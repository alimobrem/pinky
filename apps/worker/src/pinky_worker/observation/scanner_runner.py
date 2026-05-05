"""Scanner runner — executes scanner definitions against a cluster.

Loads scanner definitions from the registry, runs each scanner's checks
against K8s API data, and produces RawObservations.
"""

from __future__ import annotations

import base64
import logging
from datetime import UTC, datetime, timedelta

from pinky_worker.definitions.loader import Definition
from pinky_worker.issues.correlator import RawObservation
from pinky_worker.observation.fingerprint import compute_correlation_key, compute_observation_fingerprint

logger = logging.getLogger(__name__)

PENDING_THRESHOLD = timedelta(minutes=5)


def run_pod_health_checks(pods: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for pod in pods:
        ns = pod.get("namespace", "")
        name = pod.get("name", "")

        for container in pod.get("containers", []):
            state = container.get("state") or {}
            last_state = container.get("last_state") or {}
            state_type = state.get("type", "")
            state_reason = state.get("reason", "")
            last_type = last_state.get("type", "")
            last_reason = last_state.get("reason", "")
            restart_count = container.get("restart_count", 0) or 0
            container_name = container.get("name", "unknown")

            if state_type == "waiting" and state_reason == "CrashLoopBackOff":
                fp = compute_observation_fingerprint(cluster_id, "pod-health", "crash-loop-backoff", "Pod", ns, name)
                ck = compute_correlation_key(cluster_id, "Pod", ns, name, "pod-health", "crash-loop-backoff")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="pod-health",
                    scanner_version=scanner_def.version,
                    check_id="crash-loop-backoff",
                    severity="high",
                    resource_kind="Pod",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Pod {ns}/{name} in CrashLoopBackOff",
                    payload={"container": container_name, "restart_count": restart_count},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if last_type == "terminated" and last_reason == "OOMKilled":
                fp = compute_observation_fingerprint(cluster_id, "pod-health", "oom-killed", "Pod", ns, name)
                ck = compute_correlation_key(cluster_id, "Pod", ns, name, "pod-health", "oom-killed")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="pod-health",
                    scanner_version=scanner_def.version,
                    check_id="oom-killed",
                    severity="critical",
                    resource_kind="Pod",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Pod {ns}/{name} OOMKilled",
                    payload={"container": container_name, "exit_code": last_state.get("exit_code")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if restart_count > 5:
                fp = compute_observation_fingerprint(cluster_id, "pod-health", "excessive-restarts", "Pod", ns, name)
                ck = compute_correlation_key(cluster_id, "Pod", ns, name, "pod-health", "excessive-restarts")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="pod-health",
                    scanner_version=scanner_def.version,
                    check_id="excessive-restarts",
                    severity="medium",
                    resource_kind="Pod",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Pod {ns}/{name} has {restart_count} restarts",
                    payload={"container": container_name, "restart_count": restart_count},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if state_type == "waiting" and state_reason in ("ImagePullBackOff", "ErrImagePull"):
                fp = compute_observation_fingerprint(cluster_id, "pod-health", "image-pull-error", "Pod", ns, name)
                ck = compute_correlation_key(cluster_id, "Pod", ns, name, "pod-health", "image-pull-error")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="pod-health",
                    scanner_version=scanner_def.version,
                    check_id="image-pull-error",
                    severity="high",
                    resource_kind="Pod",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Pod {ns}/{name} image pull error",
                    payload={"container": container_name, "reason": state_reason},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

        phase = pod.get("phase", "")
        created_str = pod.get("creation_timestamp")
        if phase == "Pending" and created_str:
            created_at = datetime.fromisoformat(created_str)
            if (now - created_at) > PENDING_THRESHOLD:
                fp = compute_observation_fingerprint(cluster_id, "pod-health", "pending-too-long", "Pod", ns, name)
                ck = compute_correlation_key(cluster_id, "Pod", ns, name, "pod-health", "pending-too-long")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="pod-health",
                    scanner_version=scanner_def.version,
                    check_id="pending-too-long",
                    severity="medium",
                    resource_kind="Pod",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Pod {ns}/{name} pending for >{int(PENDING_THRESHOLD.total_seconds() // 60)}m",
                    payload={"phase": phase, "created_at": created_str},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

    return observations


def run_node_condition_checks(nodes: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    condition_checks = {
        "MemoryPressure": ("memory-pressure", "high"),
        "DiskPressure": ("disk-pressure", "high"),
        "PIDPressure": ("pid-pressure", "medium"),
    }

    for node in nodes:
        name = node.get("name", "")

        for cond in node.get("conditions", []):
            ctype = cond.get("type", "")
            cstatus = cond.get("status", "")

            if ctype in condition_checks and cstatus == "True":
                check_id, severity = condition_checks[ctype]
                fp = compute_observation_fingerprint(cluster_id, "node-conditions", check_id, "Node", "", name)
                ck = compute_correlation_key(cluster_id, "Node", "", name, "node-conditions", check_id)
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="node-conditions",
                    scanner_version=scanner_def.version,
                    check_id=check_id,
                    severity=severity,
                    resource_kind="Node",
                    resource_namespace="",
                    resource_name=name,
                    title=f"Node {name} has {ctype}",
                    payload={"condition": ctype, "reason": cond.get("reason", "")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if ctype == "Ready" and cstatus != "True":
                fp = compute_observation_fingerprint(cluster_id, "node-conditions", "not-ready", "Node", "", name)
                ck = compute_correlation_key(cluster_id, "Node", "", name, "node-conditions", "not-ready")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="node-conditions",
                    scanner_version=scanner_def.version,
                    check_id="not-ready",
                    severity="critical",
                    resource_kind="Node",
                    resource_namespace="",
                    resource_name=name,
                    title=f"Node {name} is NotReady",
                    payload={"condition": "Ready", "status": cstatus, "reason": cond.get("reason", "")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

        if node.get("unschedulable"):
            fp = compute_observation_fingerprint(cluster_id, "node-conditions", "unschedulable", "Node", "", name)
            ck = compute_correlation_key(cluster_id, "Node", "", name, "node-conditions", "unschedulable")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="node-conditions",
                scanner_version=scanner_def.version,
                check_id="unschedulable",
                severity="medium",
                resource_kind="Node",
                resource_namespace="",
                resource_name=name,
                title=f"Node {name} is unschedulable",
                payload={},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


def run_deployment_health_checks(
    deployments: list[dict], cluster_id: str, scanner_def: Definition,
) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for dep in deployments:
        ns = dep.get("namespace", "")
        name = dep.get("name", "")
        desired = dep.get("desired_replicas", 1)
        ready = dep.get("ready_replicas", 0)
        unavailable = dep.get("unavailable_replicas", 0)

        for cond in dep.get("conditions", []):
            if cond.get("type") == "Progressing" and cond.get("status") == "False":
                fp = compute_observation_fingerprint(
                    cluster_id, "deployment-health", "rollout-stalled", "Deployment", ns, name,
                )
                ck = compute_correlation_key(
                    cluster_id, "Deployment", ns, name, "deployment-health", "rollout-stalled",
                )
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="deployment-health",
                    scanner_version=scanner_def.version,
                    check_id="rollout-stalled",
                    severity="high",
                    resource_kind="Deployment",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Deployment {ns}/{name} rollout stalled",
                    payload={"reason": cond.get("reason", ""), "message": cond.get("message", "")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

        if unavailable > 0:
            fp = compute_observation_fingerprint(
                cluster_id, "deployment-health", "replicas-unavailable", "Deployment", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "Deployment", ns, name, "deployment-health", "replicas-unavailable",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="deployment-health",
                scanner_version=scanner_def.version,
                check_id="replicas-unavailable",
                severity="high",
                resource_kind="Deployment",
                resource_namespace=ns,
                resource_name=name,
                title=f"Deployment {ns}/{name} has {unavailable} unavailable replicas",
                payload={"unavailable": unavailable, "desired": desired},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

        if ready < desired:
            fp = compute_observation_fingerprint(
                cluster_id, "deployment-health", "replica-mismatch", "Deployment", ns, name,
            )
            ck = compute_correlation_key(cluster_id, "Deployment", ns, name, "deployment-health", "replica-mismatch")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="deployment-health",
                scanner_version=scanner_def.version,
                check_id="replica-mismatch",
                severity="medium",
                resource_kind="Deployment",
                resource_namespace=ns,
                resource_name=name,
                title=f"Deployment {ns}/{name} has {ready}/{desired} ready replicas",
                payload={"ready": ready, "desired": desired},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


def run_cert_expiry_checks(secrets: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    from cryptography.x509 import load_pem_x509_certificate

    observations: list[RawObservation] = []
    now = datetime.now(UTC)
    expiry_warn = timedelta(days=7)

    for secret in secrets:
        ns = secret.get("namespace", "")
        name = secret.get("name", "")
        crt_b64 = secret.get("tls_crt", "")
        if not crt_b64:
            continue

        try:
            pem_data = base64.b64decode(crt_b64)
            cert = load_pem_x509_certificate(pem_data)
            not_after = cert.not_valid_after_utc
        except Exception:
            logger.warning("failed to parse cert", secret=f"{ns}/{name}")
            continue

        if not_after < now:
            fp = compute_observation_fingerprint(cluster_id, "cert-expiry", "cert-expired", "Secret", ns, name)
            ck = compute_correlation_key(cluster_id, "Secret", ns, name, "cert-expiry", "cert-expired")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="cert-expiry",
                scanner_version=scanner_def.version,
                check_id="cert-expired",
                severity="critical",
                resource_kind="Secret",
                resource_namespace=ns,
                resource_name=name,
                title=f"TLS cert {ns}/{name} expired",
                payload={"not_after": not_after.isoformat()},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))
        elif not_after < (now + expiry_warn):
            fp = compute_observation_fingerprint(cluster_id, "cert-expiry", "cert-expiring-soon", "Secret", ns, name)
            ck = compute_correlation_key(cluster_id, "Secret", ns, name, "cert-expiry", "cert-expiring-soon")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="cert-expiry",
                scanner_version=scanner_def.version,
                check_id="cert-expiring-soon",
                severity="high",
                resource_kind="Secret",
                resource_namespace=ns,
                resource_name=name,
                title=f"TLS cert {ns}/{name} expires in <7d",
                payload={"not_after": not_after.isoformat()},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


def run_pvc_health_checks(pvcs: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for pvc in pvcs:
        ns = pvc.get("namespace", "")
        name = pvc.get("name", "")
        phase = pvc.get("phase", "")

        if phase == "Pending":
            fp = compute_observation_fingerprint(
                cluster_id, "pvc-health", "pvc-pending", "PersistentVolumeClaim", ns, name,
            )
            ck = compute_correlation_key(cluster_id, "PersistentVolumeClaim", ns, name, "pvc-health", "pvc-pending")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="pvc-health",
                scanner_version=scanner_def.version,
                check_id="pvc-pending",
                severity="high",
                resource_kind="PersistentVolumeClaim",
                resource_namespace=ns,
                resource_name=name,
                title=f"PVC {ns}/{name} is Pending",
                payload={"phase": phase},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))
        elif phase == "Lost":
            fp = compute_observation_fingerprint(
                cluster_id, "pvc-health", "pvc-lost", "PersistentVolumeClaim", ns, name,
            )
            ck = compute_correlation_key(cluster_id, "PersistentVolumeClaim", ns, name, "pvc-health", "pvc-lost")
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="pvc-health",
                scanner_version=scanner_def.version,
                check_id="pvc-lost",
                severity="critical",
                resource_kind="PersistentVolumeClaim",
                resource_namespace=ns,
                resource_name=name,
                title=f"PVC {ns}/{name} is Lost",
                payload={"phase": phase},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


def run_resource_quota_checks(quotas: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for quota in quotas:
        ns = quota.get("namespace", "")
        name = quota.get("name", "")
        hard = quota.get("hard", {})
        used = quota.get("used", {})

        for resource, hard_val in hard.items():
            used_val = used.get(resource)
            if used_val is None:
                continue
            try:
                h = _parse_quantity(hard_val)
                u = _parse_quantity(used_val)
            except (ValueError, TypeError):
                continue
            if h <= 0:
                continue

            if u >= h:
                fp = compute_observation_fingerprint(
                    cluster_id, "resource-quotas", "quota-exceeded", "ResourceQuota", ns, name,
                )
                ck = compute_correlation_key(
                    cluster_id, "ResourceQuota", ns, name, "resource-quotas", "quota-exceeded",
                )
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="resource-quotas",
                    scanner_version=scanner_def.version,
                    check_id="quota-exceeded",
                    severity="high",
                    resource_kind="ResourceQuota",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Quota {ns}/{name} exceeded for {resource}",
                    payload={"resource": resource, "hard": str(hard_val), "used": str(used_val)},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))
            elif u >= h * 0.8:
                fp = compute_observation_fingerprint(
                    cluster_id, "resource-quotas", "quota-near-limit", "ResourceQuota", ns, name,
                )
                ck = compute_correlation_key(
                    cluster_id, "ResourceQuota", ns, name, "resource-quotas", "quota-near-limit",
                )
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="resource-quotas",
                    scanner_version=scanner_def.version,
                    check_id="quota-near-limit",
                    severity="medium",
                    resource_kind="ResourceQuota",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Quota {ns}/{name} near limit for {resource} ({int(u / h * 100)}%)",
                    payload={
                        "resource": resource, "hard": str(hard_val),
                        "used": str(used_val), "pct": round(u / h * 100, 1),
                    },
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

    return observations


def _parse_quantity(val: str) -> float:
    """Parse K8s resource quantity string to a numeric value."""
    s = str(val).strip()
    suffixes = {
        "Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4,
        "m": 0.001, "k": 1000, "M": 1_000_000, "G": 1_000_000_000,
    }
    for suffix, multiplier in sorted(suffixes.items(), key=lambda x: -len(x[0])):
        if s.endswith(suffix):
            return float(s[: -len(suffix)]) * multiplier
    return float(s)


def run_ingress_health_checks(ingresses: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for ingress in ingresses:
        ns = ingress.get("namespace", "")
        name = ingress.get("name", "")
        rules = ingress.get("rules", [])

        for rule in rules:
            service_name = rule.get("service_name", "")
            if not service_name:
                fp = compute_observation_fingerprint(
                    cluster_id, "ingress-health", "ingress-no-backend", "Ingress", ns, name,
                )
                ck = compute_correlation_key(cluster_id, "Ingress", ns, name, "ingress-health", "ingress-no-backend")
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="ingress-health",
                    scanner_version=scanner_def.version,
                    check_id="ingress-no-backend",
                    severity="high",
                    resource_kind="Ingress",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Ingress {ns}/{name} has rule with no backend service",
                    payload={"host": rule.get("host", ""), "path": rule.get("path", "/")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))
                break

    return observations


def run_statefulset_health_checks(
    statefulsets: list[dict], cluster_id: str, scanner_def: Definition,
) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for sts in statefulsets:
        ns = sts.get("namespace", "")
        name = sts.get("name", "")
        replicas = sts.get("replicas", 1)
        ready_replicas = sts.get("ready_replicas", 0)
        updated_replicas = sts.get("updated_replicas", 0)
        current_revision = sts.get("current_revision", "")
        update_revision = sts.get("update_revision", "")

        if (
            updated_replicas < replicas
            and current_revision
            and update_revision
            and current_revision != update_revision
        ):
            fp = compute_observation_fingerprint(
                cluster_id, "statefulset-health", "sts-rollout-stuck", "StatefulSet", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "StatefulSet", ns, name, "statefulset-health", "sts-rollout-stuck",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="statefulset-health",
                scanner_version=scanner_def.version,
                check_id="sts-rollout-stuck",
                severity="high",
                resource_kind="StatefulSet",
                resource_namespace=ns,
                resource_name=name,
                title=f"StatefulSet {ns}/{name} rollout stuck",
                payload={
                    "updated_replicas": updated_replicas,
                    "replicas": replicas,
                    "current_revision": current_revision,
                    "update_revision": update_revision,
                },
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

        if ready_replicas < replicas:
            fp = compute_observation_fingerprint(
                cluster_id, "statefulset-health", "sts-replicas-unavailable", "StatefulSet", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "StatefulSet", ns, name, "statefulset-health", "sts-replicas-unavailable",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="statefulset-health",
                scanner_version=scanner_def.version,
                check_id="sts-replicas-unavailable",
                severity="high",
                resource_kind="StatefulSet",
                resource_namespace=ns,
                resource_name=name,
                title=f"StatefulSet {ns}/{name} has {ready_replicas}/{replicas} ready replicas",
                payload={"ready_replicas": ready_replicas, "replicas": replicas},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

        # TODO: sts-ordinal-stuck check needs per-pod ordinal inspection,
        # cannot be reliably detected from list data alone.

    return observations


CRONJOB_MISSED_THRESHOLD = timedelta(hours=2)


def run_job_health_checks(
    jobs: list[dict], cluster_id: str, scanner_def: Definition,
) -> list[RawObservation]:
    """Check health of Jobs and CronJobs (distinguished by 'kind' field)."""
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for item in jobs:
        kind = item.get("kind", "Job")
        ns = item.get("namespace", "")
        name = item.get("name", "")

        if kind == "Job":
            failed = item.get("failed", 0)
            backoff_limit = item.get("backoff_limit", 6)

            if failed >= backoff_limit:
                fp = compute_observation_fingerprint(
                    cluster_id, "job-health", "job-failed", "Job", ns, name,
                )
                ck = compute_correlation_key(
                    cluster_id, "Job", ns, name, "job-health", "job-failed",
                )
                observations.append(RawObservation(
                    cluster_id=cluster_id,
                    scanner="job-health",
                    scanner_version=scanner_def.version,
                    check_id="job-failed",
                    severity="high",
                    resource_kind="Job",
                    resource_namespace=ns,
                    resource_name=name,
                    title=f"Job {ns}/{name} failed (attempts: {failed}/{backoff_limit})",
                    payload={"failed": failed, "backoff_limit": backoff_limit},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            for cond in item.get("conditions", []):
                if cond.get("type") == "DeadlineExceeded" and cond.get("status") == "True":
                    fp = compute_observation_fingerprint(
                        cluster_id, "job-health", "job-deadline-exceeded", "Job", ns, name,
                    )
                    ck = compute_correlation_key(
                        cluster_id, "Job", ns, name, "job-health", "job-deadline-exceeded",
                    )
                    observations.append(RawObservation(
                        cluster_id=cluster_id,
                        scanner="job-health",
                        scanner_version=scanner_def.version,
                        check_id="job-deadline-exceeded",
                        severity="high",
                        resource_kind="Job",
                        resource_namespace=ns,
                        resource_name=name,
                        title=f"Job {ns}/{name} exceeded deadline",
                        payload={"reason": cond.get("reason", "")},
                        observed_at=now,
                        fingerprint=fp,
                        correlation_key=ck,
                    ))
                    break

        elif kind == "CronJob":
            last_schedule_str = item.get("last_schedule_time")
            if last_schedule_str:
                last_schedule = datetime.fromisoformat(last_schedule_str)
                if (now - last_schedule) > CRONJOB_MISSED_THRESHOLD:
                    fp = compute_observation_fingerprint(
                        cluster_id, "job-health", "cronjob-missed", "CronJob", ns, name,
                    )
                    ck = compute_correlation_key(
                        cluster_id, "CronJob", ns, name, "job-health", "cronjob-missed",
                    )
                    observations.append(RawObservation(
                        cluster_id=cluster_id,
                        scanner="job-health",
                        scanner_version=scanner_def.version,
                        check_id="cronjob-missed",
                        severity="medium",
                        resource_kind="CronJob",
                        resource_namespace=ns,
                        resource_name=name,
                        title=f"CronJob {ns}/{name} last scheduled >2h ago",
                        payload={
                            "last_schedule_time": last_schedule_str,
                            "schedule": item.get("schedule", ""),
                        },
                        observed_at=now,
                        fingerprint=fp,
                        correlation_key=ck,
                    ))

    return observations


def run_service_endpoint_checks(
    services: list[dict], cluster_id: str, scanner_def: Definition,
) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for svc in services:
        ns = svc.get("namespace", "")
        name = svc.get("name", "")
        selector = svc.get("selector", {})
        ready = svc.get("ready_endpoints", 0)
        not_ready = svc.get("not_ready_endpoints", 0)
        total = ready + not_ready

        # Only check services that have a selector (skip ExternalName, headless without selector)
        if not selector:
            continue

        if ready == 0:
            fp = compute_observation_fingerprint(
                cluster_id, "service-endpoints", "service-no-endpoints", "Service", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "Service", ns, name, "service-endpoints", "service-no-endpoints",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="service-endpoints",
                scanner_version=scanner_def.version,
                check_id="service-no-endpoints",
                severity="high",
                resource_kind="Service",
                resource_namespace=ns,
                resource_name=name,
                title=f"Service {ns}/{name} has no ready endpoints",
                payload={"ready": ready, "not_ready": not_ready},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))
        elif total > 0 and not_ready > total * 0.5:
            fp = compute_observation_fingerprint(
                cluster_id, "service-endpoints", "service-partial-endpoints", "Service", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "Service", ns, name, "service-endpoints", "service-partial-endpoints",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="service-endpoints",
                scanner_version=scanner_def.version,
                check_id="service-partial-endpoints",
                severity="medium",
                resource_kind="Service",
                resource_namespace=ns,
                resource_name=name,
                title=f"Service {ns}/{name} has >50% endpoints not ready ({not_ready}/{total})",
                payload={"ready": ready, "not_ready": not_ready, "total": total},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


def run_daemonset_health_checks(
    daemonsets: list[dict], cluster_id: str, scanner_def: Definition,
) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(UTC)

    for ds in daemonsets:
        ns = ds.get("namespace", "")
        name = ds.get("name", "")
        desired = ds.get("desired", 0)
        current = ds.get("current", 0)
        number_unavailable = ds.get("number_unavailable", 0)
        number_misscheduled = ds.get("number_misscheduled", 0)

        if number_unavailable > 0:
            fp = compute_observation_fingerprint(
                cluster_id, "daemonset-health", "daemonset-unavailable", "DaemonSet", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "DaemonSet", ns, name, "daemonset-health", "daemonset-unavailable",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="daemonset-health",
                scanner_version=scanner_def.version,
                check_id="daemonset-unavailable",
                severity="high",
                resource_kind="DaemonSet",
                resource_namespace=ns,
                resource_name=name,
                title=f"DaemonSet {ns}/{name} has {number_unavailable} unavailable",
                payload={"number_unavailable": number_unavailable, "desired": desired},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

        if number_misscheduled > 0:
            fp = compute_observation_fingerprint(
                cluster_id, "daemonset-health", "daemonset-misscheduled", "DaemonSet", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "DaemonSet", ns, name, "daemonset-health", "daemonset-misscheduled",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="daemonset-health",
                scanner_version=scanner_def.version,
                check_id="daemonset-misscheduled",
                severity="medium",
                resource_kind="DaemonSet",
                resource_namespace=ns,
                resource_name=name,
                title=f"DaemonSet {ns}/{name} has {number_misscheduled} misscheduled",
                payload={"number_misscheduled": number_misscheduled},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

        if desired != current:
            fp = compute_observation_fingerprint(
                cluster_id, "daemonset-health", "daemonset-desired-mismatch", "DaemonSet", ns, name,
            )
            ck = compute_correlation_key(
                cluster_id, "DaemonSet", ns, name, "daemonset-health", "daemonset-desired-mismatch",
            )
            observations.append(RawObservation(
                cluster_id=cluster_id,
                scanner="daemonset-health",
                scanner_version=scanner_def.version,
                check_id="daemonset-desired-mismatch",
                severity="medium",
                resource_kind="DaemonSet",
                resource_namespace=ns,
                resource_name=name,
                title=f"DaemonSet {ns}/{name} desired={desired} current={current}",
                payload={"desired": desired, "current": current},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations


SCANNER_RUNNERS = {
    "pod-health": run_pod_health_checks,
    "node-conditions": run_node_condition_checks,
    "deployment-health": run_deployment_health_checks,
    "cert-expiry": run_cert_expiry_checks,
    "pvc-health": run_pvc_health_checks,
    "resource-quotas": run_resource_quota_checks,
    "ingress-health": run_ingress_health_checks,
    "statefulset-health": run_statefulset_health_checks,
    "job-health": run_job_health_checks,
    "service-endpoints": run_service_endpoint_checks,
    "daemonset-health": run_daemonset_health_checks,
}
