"""Observer loop — periodically scans clusters and feeds the pipeline.

One observer task per registered cluster. Uses observer identity
(read-only SA) for all reads. Dispatches Temporal workflows based
on policy decisions.
"""

from __future__ import annotations

import asyncio

import structlog

from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.k8s_client import (
    create_client,
    list_cronjobs,
    list_daemonsets,
    list_deployments,
    list_ingresses,
    list_jobs,
    list_nodes,
    list_pods,
    list_pvcs,
    list_resource_quotas,
    list_services,
    list_statefulsets,
    list_tls_secrets,
)
from pinky_worker.observation.scanner_runner import SCANNER_RUNNERS
from pinky_worker.policy.engine import PolicyInput, evaluate, rules_from_definitions
from pinky_worker.queues import INVESTIGATION_QUEUE

logger = structlog.get_logger(__name__)

async def _fetch_jobs_and_cronjobs(api_client):
    jobs = await list_jobs(api_client)
    cronjobs = await list_cronjobs(api_client)
    return jobs + cronjobs


SCANNER_FETCHERS = {
    "pod-health": list_pods,
    "node-conditions": list_nodes,
    "deployment-health": list_deployments,
    "cert-expiry": list_tls_secrets,
    "pvc-health": list_pvcs,
    "resource-quotas": list_resource_quotas,
    "ingress-health": list_ingresses,
    "statefulset-health": list_statefulsets,
    "job-health": _fetch_jobs_and_cronjobs,
    "service-endpoints": list_services,
    "daemonset-health": list_daemonsets,
}


async def _dispatch_investigation(
    temporal_client,
    cluster_id: str,
    obs,
    result,
    decision,
    registry: DefinitionRegistry,
) -> None:
    skill_body = ""
    skill_tools: list[str] = []
    skill_name = decision.action.skill
    if skill_name:
        skill_def = registry.get("skill", skill_name)
        if skill_def:
            skill_body = skill_def.body
            skill_tools = skill_def.frontmatter.get("tools", [])
        else:
            logger.warning("skill not found", skill=skill_name)

    workflow_id = f"investigation-{cluster_id[:8]}-{obs.fingerprint[:16]}"

    try:
        await temporal_client.start_workflow(
            "InvestigationWorkflow",
            {
                "issue_id": result.issue_id or "",
                "cluster_id": cluster_id,
                "correlation_key": obs.correlation_key,
                "evidence_hash": "",
                "skill_body": skill_body,
                "skill_tools": skill_tools,
            },
            id=workflow_id,
            task_queue=INVESTIGATION_QUEUE,
        )
        logger.info(
            "dispatched investigation",
            workflow_id=workflow_id,
            skill=skill_name or "<generic>",
            issue_id=result.issue_id,
        )
    except Exception:
        logger.exception("failed to dispatch investigation", workflow_id=workflow_id)


async def _handle_suppress(result, decision) -> None:
    if result.issue_id and decision.action.suppress_duration_minutes:
        from datetime import UTC, datetime, timedelta

        from pinky_worker.db import get_pool

        suppress_until = datetime.now(UTC) + timedelta(
            minutes=decision.action.suppress_duration_minutes,
        )
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE issues SET status = 'suppressed', suppressed_until = $1, "
                "updated_at = now() WHERE id = $2::uuid",
                suppress_until, result.issue_id,
            )
        logger.info("suppressed issue", issue_id=result.issue_id, until=suppress_until)


async def observe_cluster(
    cluster_id: str,
    registry: DefinitionRegistry,
    correlator: DbIssueCorrelator,
    scan_interval: int = 60,
    max_cycles: int = 0,
    temporal_client=None,
) -> None:
    scanner_defs = registry.list_by_kind("scanner")
    policy_defs = registry.list_by_kind("policy")
    policy_rules = rules_from_definitions(policy_defs)

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
                observations: list = []
                for scanner_def in scanner_defs:
                    runner = SCANNER_RUNNERS.get(scanner_def.name)
                    fetcher = SCANNER_FETCHERS.get(scanner_def.name)
                    if runner is None or fetcher is None:
                        continue
                    try:
                        data = await fetcher(api_client)
                        observations.extend(runner(data, cluster_id, scanner_def))
                    except Exception:
                        logger.exception("scanner failed", scanner=scanner_def.name)

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
                        recurrence_count=result.observation_count,
                    )
                    decision = evaluate(policy_rules, policy_input)
                    logger.info(
                        "policy decision",
                        rule=decision.rule_name,
                        action=decision.action.action_type,
                        resource=f"{obs.resource_namespace}/{obs.resource_name}",
                    )

                    if temporal_client and decision.action.action_type == "investigate":
                        await _dispatch_investigation(
                            temporal_client, cluster_id, obs, result, decision, registry,
                        )
                    elif decision.action.action_type == "suppress":
                        await _handle_suppress(result, decision)

                if not observations:
                    logger.info("clean scan", cluster_id=cluster_id)

            except Exception:
                logger.exception("scan cycle failed", cluster_id=cluster_id, cycle=cycle)

            if max_cycles == 0 or cycle < max_cycles:
                await asyncio.sleep(scan_interval)
    finally:
        await api_client.close()
