"""Observer loop — periodically scans clusters and feeds the pipeline.

One observer task per registered cluster. Uses observer identity
(read-only SA) for all reads. Dispatches Temporal workflows based
on policy decisions. Scanners are interpreted from structured YAML
checks in definition frontmatter — no hardcoded runner functions.
"""

from __future__ import annotations

import asyncio
import json
import os
import re as re_mod
import uuid
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

import structlog

from pinky_worker.db import get_pool
from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.generic_scanner import run_generic_checks
from pinky_worker.observation.k8s_client import (
    create_client,
    list_cronjobs,
    list_daemonsets,
    list_deployments,
    list_hpas,
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
from pinky_worker.policy.engine import (
    PolicyAction,
    PolicyConditions,
    PolicyInput,
    PolicyRule,
    evaluate,
    rules_from_definitions,
)
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
    "HorizontalPodAutoscaler": list_hpas,
}


_DEFAULT_EXCLUDE_NS = os.environ.get(
    "PINKY_EXCLUDE_NAMESPACES_REGEX",
    r"^(openshift-|openshift$|kube-|default$|stackrox$)",
)


async def _fetch_for_scanner(api_client, scanner_def) -> list[dict]:
    resource_kinds = scanner_def.frontmatter.get("resource_kinds", [])
    exclude_ns = scanner_def.frontmatter.get("exclude_namespaces_regex", _DEFAULT_EXCLUDE_NS)
    exclude_re = re_mod.compile(exclude_ns) if exclude_ns else None
    resources: list[dict] = []
    for kind in resource_kinds:
        fetcher = RESOURCE_KIND_FETCHERS.get(kind)
        if fetcher:
            try:
                resources.extend(await fetcher(api_client))
            except Exception:
                logger.exception("fetcher failed", kind=kind)
    if exclude_re:
        resources = [r for r in resources if not exclude_re.match(r.get("namespace", ""))]
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

    from pinky_worker.db import get_pool

    pool = await get_pool()

    # Stable workflow ID for Temporal dedup (same issue = same workflow)
    workflow_id = f"investigation-{cluster_id[:8]}-{obs.fingerprint[:16]}"

    # Skip if there's already a pending/running OR recently completed investigation
    existing = await pool.fetchrow(
        "SELECT id, status FROM executions WHERE work_item_id IN "
        "(SELECT id FROM work_items WHERE issue_id = $1::uuid) "
        "AND (status IN ('pending', 'running') "
        "     OR (status IN ('completed', 'failed') AND completed_at > now() - interval '1 hour')) "
        "ORDER BY created_at DESC LIMIT 1",
        result.issue_id,
    )
    if existing:
        logger.debug("investigation cooldown active",
                     issue_id=result.issue_id, status=existing["status"])
        return

    exec_id = uuid.uuid4()
    work_item_id = None
    wi_row = await pool.fetchrow(
        "SELECT id FROM work_items WHERE issue_id = $1::uuid ORDER BY created_at DESC LIMIT 1",
        result.issue_id,
    )
    if wi_row:
        work_item_id = wi_row["id"]

    await pool.execute(
        """INSERT INTO executions (id, work_item_id, cluster_id, execution_type, status, created_at)
           VALUES ($1, $2, $3::uuid, 'investigation', 'pending', now())
           ON CONFLICT DO NOTHING""",
        exec_id, work_item_id, cluster_id,
    )

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
                "execution_id": str(exec_id),
            },
            id=workflow_id,
            task_queue=INVESTIGATION_QUEUE,
        )
        logger.info(
            "dispatched investigation",
            workflow_id=workflow_id,
            execution_id=str(exec_id),
            skill=skill_name or "<generic>",
            issue_id=result.issue_id,
        )
    except Exception as exc:
        if "already started" in str(exc).lower() or "already running" in str(exc).lower():
            logger.debug("investigation already running", workflow_id=workflow_id)
            await pool.execute("DELETE FROM executions WHERE id = $1", exec_id)
        else:
            logger.exception("failed to dispatch investigation", workflow_id=workflow_id)
            await pool.execute(
                "UPDATE executions SET status = 'failed' WHERE id = $1", exec_id,
            )


async def _handle_suppress(result, decision) -> None:
    if result.issue_id and decision.action.suppress_duration_minutes:
        from datetime import timedelta

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
            await conn.execute(
                "UPDATE work_items SET status = 'done', updated_at = now() "
                "WHERE issue_id = $1::uuid AND status IN ('ready', 'in_progress')",
                result.issue_id,
            )
        logger.info("suppressed issue", issue_id=result.issue_id, until=suppress_until)


DEFAULT_STALENESS_THRESHOLD_SECONDS = 900

RISK_CLASS_TO_PRIORITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}


async def _sweep_stale_issues(
    cluster_id: str,
    registry: DefinitionRegistry,
    scan_healthy: bool,
) -> int:
    if not scan_healthy:
        logger.info("skipping staleness sweep — scan had errors", cluster_id=cluster_id)
        return 0

    from pinky_worker.db import get_pool

    pool = await get_pool()

    scanner_thresholds: dict[str, int] = {}
    for scanner_def in registry.list_by_kind("scanner"):
        threshold = scanner_def.frontmatter.get("staleness_threshold_seconds")
        if threshold is not None:
            scanner_thresholds[scanner_def.name] = int(threshold)

    global_threshold = int(os.environ.get(
        "PINKY_STALENESS_THRESHOLD_SECONDS",
        str(DEFAULT_STALENESS_THRESHOLD_SECONDS),
    ))

    stale_issues = await pool.fetch(
        """SELECT id, correlation_key, labels, last_seen_at
           FROM issues
           WHERE cluster_id = $1::uuid
             AND status = 'open'
             AND last_seen_at < now() - make_interval(secs => $2)""",
        cluster_id,
        float(global_threshold),
    )

    resolved_count = 0
    now = datetime.now(UTC)
    for issue in stale_issues:
        issue_id = issue["id"]
        labels = issue["labels"] if isinstance(issue["labels"], dict) else {}
        scanner_name = labels.get("scanner", "")

        if scanner_name in scanner_thresholds:
            issue_age = (now - issue["last_seen_at"]).total_seconds()
            if issue_age < scanner_thresholds[scanner_name]:
                continue

        async with pool.acquire() as conn:
            await conn.execute(
                """UPDATE issues
                   SET status = 'resolved', resolved_at = now(),
                       resolved_by = 'staleness', updated_at = now()
                   WHERE id = $1 AND status = 'open'""",
                issue_id,
            )
            await conn.execute(
                """UPDATE work_items
                   SET status = 'done', updated_at = now()
                   WHERE issue_id = $1 AND status IN ('ready', 'in_progress')""",
                issue_id,
            )
            existing_event = await conn.fetchrow(
                """SELECT id, payload FROM domain_events
                   WHERE event_type = 'issue.auto_resolved'
                     AND aggregate_id = $1
                   ORDER BY occurred_at DESC LIMIT 1""",
                issue_id,
            )
            if existing_event:
                prev_payload = existing_event["payload"] if isinstance(existing_event["payload"], dict) else {}
                count = prev_payload.get("resolve_count", 1) + 1
                await conn.execute(
                    """UPDATE domain_events
                       SET payload = $2, occurred_at = now()
                       WHERE id = $1""",
                    existing_event["id"],
                    json.dumps({"status": "resolved", "resolved_by": "staleness", "resolve_count": count}),
                )
            else:
                await conn.execute(
                    """INSERT INTO domain_events
                       (id, event_type, aggregate_type, aggregate_id, cluster_id, payload, occurred_at)
                       VALUES ($1, 'issue.auto_resolved', 'issue', $2, $3::uuid,
                               '{"status": "resolved", "resolved_by": "staleness", "resolve_count": 1}', now())""",
                    uuid.uuid4(), issue_id, cluster_id,
                )
            await conn.execute(
                "SELECT pg_notify('pinky_issues', $1)",
                f'{{"event_type": "issue.auto_resolved", "aggregate_id": "{issue_id}"}}',
            )

        resolved_count += 1
        logger.info(
            "auto-resolved stale issue",
            issue_id=str(issue_id),
            correlation_key=issue["correlation_key"],
        )

    if resolved_count:
        logger.info("staleness sweep complete", cluster_id=cluster_id, resolved=resolved_count)
    return resolved_count


async def _handle_create_task(result, decision, obs) -> None:
    if not result.issue_id:
        return

    from pinky_worker.db import get_pool

    pool = await get_pool()
    work_item_id = uuid.uuid4()
    priority = RISK_CLASS_TO_PRIORITY.get(
        decision.action.risk_class or "", "medium",
    )

    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO work_items
               (id, issue_id, cluster_id, title, why_now, recommended_next_step,
                status, confidence, priority, runbook_url, labels, annotations,
                artifact_refs, created_at, updated_at)
               VALUES ($1, $2::uuid, $3::uuid, $4, $5, $6,
                       'ready', 0.7, $7, $8, $9, '{}', '{}', now(), now())""",
            work_item_id,
            result.issue_id,
            obs.cluster_id,
            obs.title,
            f"{obs.resource_kind}/{obs.resource_namespace}/{obs.resource_name}: {obs.title}",
            f"Investigate {obs.check_id} on {obs.resource_namespace}/{obs.resource_name}",
            priority,
            decision.action.runbook_url,
            f'{{"scanner": "{obs.scanner}", "check_id": "{obs.check_id}", "resource_kind": "{obs.resource_kind}"}}',
        )
        await conn.execute(
            "SELECT pg_notify('pinky_work_items', $1)",
            f'{{"event_type": "work_item.created", "aggregate_id": "{work_item_id}"}}',
        )

    logger.info(
        "created task from policy",
        work_item_id=str(work_item_id),
        issue_id=result.issue_id,
        priority=priority,
    )


async def _get_reopen_count(issue_id: str | None, hours: int = 24) -> int:
    if not issue_id:
        return 0
    from pinky_worker.db import get_pool

    pool = await get_pool()
    row = await pool.fetchrow(
        """SELECT COUNT(*) as cnt FROM domain_events
           WHERE aggregate_id = $1::uuid
           AND event_type IN ('issue.auto_resolved', 'issue.resolved')
           AND occurred_at > now() - make_interval(hours => $2)""",
        issue_id, hours,
    )
    return row["cnt"] if row else 0


async def _apply_policy_metadata(issue_id: str, action) -> None:
    from pinky_worker.db import get_pool

    pool = await get_pool()
    async with pool.acquire() as conn:
        if action.runbook_url:
            await conn.execute(
                "UPDATE issues SET runbook_url = $1 WHERE id = $2::uuid",
                action.runbook_url, issue_id,
            )
            await conn.execute(
                "UPDATE work_items SET runbook_url = $1 WHERE issue_id = $2::uuid",
                action.runbook_url, issue_id,
            )
        if action.risk_class:
            await conn.execute(
                """UPDATE issues SET labels = labels || $1::jsonb
                   WHERE id = $2::uuid""",
                f'{{"risk_class": "{action.risk_class}"}}',
                issue_id,
            )


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

    # Merge DB policy rules (API-created rules)
    try:
        pool = await get_pool()
        db_rules_rows = await pool.fetch(
            "SELECT name, priority, conditions, action FROM policy_rules "
            "WHERE enabled = true ORDER BY priority ASC"
        )
        for row in db_rules_rows:
            conditions_raw = row["conditions"] if isinstance(row["conditions"], dict) else {}
            action_raw = row["action"] if isinstance(row["action"], dict) else {}
            db_rule = PolicyRule(
                name=row["name"],
                priority=row["priority"],
                conditions=PolicyConditions(
                    scanner=conditions_raw.get("scanner"),
                    check_id=conditions_raw.get("check_id"),
                    check_id_regex=conditions_raw.get("check_id_regex"),
                    severity=conditions_raw.get("severity"),
                    severity_gte=conditions_raw.get("severity_gte"),
                    resource_kind=conditions_raw.get("resource_kind"),
                    resource_namespace_regex=conditions_raw.get("resource_namespace_regex"),
                    cluster_id=conditions_raw.get("cluster_id"),
                    labels=conditions_raw.get("labels", {}),
                    recurrence_count_gte=conditions_raw.get("recurrence_count_gte"),
                    reopen_count_gte=conditions_raw.get("reopen_count_gte"),
                    is_operator_managed=conditions_raw.get("is_operator_managed"),
                ),
                action=PolicyAction(
                    action_type=action_raw.get("type", "observe"),
                    suppress_duration_minutes=action_raw.get("suppress_duration_minutes"),
                    risk_class=action_raw.get("risk_class"),
                    runbook_url=action_raw.get("runbook_url"),
                    skill=action_raw.get("skill"),
                ),
            )
            policy_rules.append(db_rule)
        if db_rules_rows:
            policy_rules.sort(key=lambda r: r.priority)
            logger.info("merged DB policy rules", count=len(db_rules_rows))
    except Exception:
        logger.exception("failed to load DB policy rules, using filesystem only")

    prom_client = None

    logger.info("starting observer", cluster_id=cluster_id, scanners=len(scanner_defs))

    cycle = 0
    try:
        api_client = await create_client()
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
                scan_healthy = True
                for scanner_def in scanner_defs:
                    if not scanner_def.frontmatter.get("checks"):
                        continue
                    try:
                        data = await _fetch_for_scanner(api_client, scanner_def)
                        observations.extend(
                            await run_generic_checks(data, cluster_id, scanner_def, prom_client=prom_client),
                        )
                    except Exception:
                        scan_healthy = False
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

                    reopen_count = await _get_reopen_count(result.issue_id)
                    policy_input = PolicyInput(
                        scanner=obs.scanner,
                        check_id=obs.check_id or "",
                        severity=obs.severity,
                        resource_kind=obs.resource_kind,
                        resource_namespace=obs.resource_namespace or "",
                        cluster_id=cluster_id,
                        recurrence_count=result.observation_count,
                        reopen_count=reopen_count,
                        is_operator_managed=bool(obs.payload.get("operator_managed")) if obs.payload else False,
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
                    elif decision.action.action_type == "create_task":
                        await _handle_create_task(result, decision, obs)

                    if result.issue_id and (decision.action.runbook_url or decision.action.risk_class):
                        await _apply_policy_metadata(result.issue_id, decision.action)

                if not observations:
                    logger.info("clean scan", cluster_id=cluster_id)

                await _sweep_stale_issues(cluster_id, registry, scan_healthy)

            except Exception:
                logger.exception("scan cycle failed", cluster_id=cluster_id, cycle=cycle)

            if max_cycles == 0 or cycle < max_cycles:
                await asyncio.sleep(scan_interval)
    finally:
        await api_client.close()
