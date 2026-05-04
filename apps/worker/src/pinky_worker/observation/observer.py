"""Observer loop — periodically scans clusters and feeds the pipeline.

One observer task per registered cluster. Uses observer identity
(read-only SA) for all reads.
"""

from __future__ import annotations

import asyncio

import structlog

from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.k8s_client import create_client, list_pods
from pinky_worker.observation.scanner_runner import run_pod_health_checks
from pinky_worker.policy.engine import PolicyInput, evaluate, rules_from_definitions

logger = structlog.get_logger(__name__)


async def observe_cluster(
    cluster_id: str,
    registry: DefinitionRegistry,
    correlator: DbIssueCorrelator,
    scan_interval: int = 60,
    max_cycles: int = 0,
) -> None:
    scanner_defs = registry.list_by_kind("scanner")
    policy_defs = registry.list_by_kind("policy")
    policy_rules = rules_from_definitions(policy_defs)

    pod_health_def = registry.get("scanner", "pod-health")
    if pod_health_def is None:
        logger.warning("pod-health scanner not found in registry")
        return

    logger.info("starting observer", cluster_id=cluster_id, scanners=len(scanner_defs))

    cycle = 0
    try:
        api_client = await create_client(in_cluster=True)
    except Exception:
        logger.exception("failed to create K8s client for cluster %s", cluster_id)
        return

    try:
        while max_cycles == 0 or cycle < max_cycles:
            cycle += 1
            logger.info("scan cycle", cluster_id=cluster_id, cycle=cycle)

            try:
                pods = await list_pods(api_client)
                observations = run_pod_health_checks(pods, cluster_id, pod_health_def)

                for obs in observations:
                    result = await correlator.correlate(obs)
                    logger.info(
                        "observation",
                        action=result.action,
                        check=obs.check_id,
                        resource=f"{obs.resource_namespace}/{obs.resource_name}",
                        severity=obs.severity,
                    )

                    policy_input = PolicyInput(
                        scanner=obs.scanner,
                        check_id=obs.check_id or "",
                        severity=obs.severity,
                        resource_kind=obs.resource_kind,
                        resource_namespace=obs.resource_namespace or "",
                        cluster_id=cluster_id,
                    )
                    decision = evaluate(policy_rules, policy_input)
                    logger.info(
                        "policy decision",
                        rule=decision.rule_name,
                        action=decision.action.action_type,
                        resource=f"{obs.resource_namespace}/{obs.resource_name}",
                    )

                if not observations:
                    logger.info("clean scan", cluster_id=cluster_id, pods_checked=len(pods))

            except Exception:
                logger.exception("scan cycle failed", cluster_id=cluster_id, cycle=cycle)

            if max_cycles == 0 or cycle < max_cycles:
                await asyncio.sleep(scan_interval)
    finally:
        await api_client.close()
