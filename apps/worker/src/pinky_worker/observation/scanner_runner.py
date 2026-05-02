"""Scanner runner — executes scanner definitions against a cluster.

Loads scanner definitions from the registry, runs each scanner's checks
against K8s API data, and produces RawObservations.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pinky_worker.definitions.loader import Definition
from pinky_worker.issues.correlator import RawObservation
from pinky_worker.observation.fingerprint import compute_correlation_key, compute_observation_fingerprint

logger = logging.getLogger(__name__)


def run_pod_health_checks(pods: list[dict], cluster_id: str, scanner_def: Definition) -> list[RawObservation]:
    observations: list[RawObservation] = []
    now = datetime.now(timezone.utc)

    for pod in pods:
        ns = pod["namespace"]
        name = pod["name"]

        for container in pod.get("containers", []):
            state = container.get("state") or {}
            last_state = container.get("last_state") or {}

            if state.get("type") == "waiting" and state.get("reason") == "CrashLoopBackOff":
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
                    payload={"container": container["name"], "restart_count": container["restart_count"]},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if last_state.get("type") == "terminated" and last_state.get("reason") == "OOMKilled":
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
                    payload={"container": container["name"], "exit_code": last_state.get("exit_code")},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

            if container.get("restart_count", 0) > 5:
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
                    title=f"Pod {ns}/{name} has {container['restart_count']} restarts",
                    payload={"container": container["name"], "restart_count": container["restart_count"]},
                    observed_at=now,
                    fingerprint=fp,
                    correlation_key=ck,
                ))

        if state.get("type") == "waiting" and state.get("reason") in ("ImagePullBackOff", "ErrImagePull"):
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
                payload={"reason": state.get("reason")},
                observed_at=now,
                fingerprint=fp,
                correlation_key=ck,
            ))

    return observations
