"""Observer loop — periodically scans clusters and feeds the pipeline.

One observer task per registered cluster. Uses observer identity
(read-only SA) for all reads. Dispatches Temporal workflows based
on policy decisions. Scanners are interpreted from structured YAML
checks in definition frontmatter — no hardcoded runner functions.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.generic_scanner import run_generic_checks
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
from pinky_worker.policy.engine import PolicyInput, evaluate, rules_from_definitions
from pinky_worker.queues import INVESTIGATION_QUEUE

logger = structlog.get_logger(__name__)

Fetcher = Callable[..., Coroutine[Any, Any, list[dict]]]

RESOURCE_KIND_FETCHERS: dict[str, Fetcher] = {
    "Pod": list_pods,
    "Node": list_nodes,
    "Deployment": list_deployments,
    "StatefulSet": list_statefulsets,
    "DaemonSet": list_daemonsets,
    "Job": list_jobs,
    "CronJob": list_cronjobs,
    "Service": list_services,
    "PersistentVolumeClaim": list_pvcs,
    "Ingress": list_ingresses,
    "Secret": list_tls_secrets,
    "ResourceQuota": list_resource_quotas,
}


async def _fetch_for_scanner(api_client, scanner_def) -> list[dict]:
    resource_kinds = scanner_def.frontmatter.get("resource_kinds", [])
    resources: list[dict] = []
    for kind in resource_kinds:
        fetcher = RESOURCE_KIND_FETCHERS.get(kind)
        if fetcher:
            try:
                resources.extend(await fetcher(api_client))
            except Exception:
                logger.exception("fetcher failed", kind=kind)
    return resources


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
    shutdown_event: asyncio.Event | None = None,
) -> None:
    scanner_defs = registry.list_by_kind("scanner")
    policy_defs = registry.list_by_kind("policy")
    policy_rules = rules_from_definitions(policy_defs)

    prom_client = None

    logger.info("starting observer", cluster_id=cluster_id, scanners=len(scanner_defs))

    cycle = 0
    try:
        api_client = await create_client(in_cluster=True)
    except Exception:
        logger.exception("failed to create K8s client for cluster %s", cluster_id)
        return

    try:
        try:
            from pinky_worker.observation.prom_client import PromClient
            prom_client = PromClient(api_client)
            logger.info("prometheus client initialized")
        except Exception:
            logger.info("prometheus client not available — PromQL checks disabled")

        while max_cycles == 0 or cycle < max_cycles:
            if shutdown_event and shutdown_event.is_set():
                logger.info("shutdown requested, stopping observer", cluster_id=cluster_id)
                break
            cycle += 1
            logger.info("scan cycle", cluster_id=cluster_id, cycle=cycle)

            try:
                observations: list = []
                for scanner_def in scanner_defs:
                    if not scanner_def.frontmatter.get("checks"):
                        continue
                    try:
                        data = await _fetch_for_scanner(api_client, scanner_def)
                        observations.extend(
                            run_generic_checks(data, cluster_id, scanner_def, prom_client=prom_client),
                        )
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
