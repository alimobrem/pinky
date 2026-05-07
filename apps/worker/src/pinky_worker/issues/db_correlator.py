"""Database-backed issue correlator — persists observations, issues, and work items to Postgres."""

from __future__ import annotations

import uuid

import structlog

from pinky_worker.db import get_pool
from pinky_worker.issues.correlator import CorrelationResult, RawObservation

logger = structlog.get_logger(__name__)


class DbIssueCorrelator:
    async def _count_observations(self, conn, correlation_key: str) -> int:
        try:
            row = await conn.fetchrow(
                "SELECT COUNT(*) as cnt FROM observations WHERE correlation_key = $1",
                correlation_key,
            )
            return row["cnt"] if row else 1
        except Exception:
            logger.warning("failed to count observations", correlation_key=correlation_key, exc_info=True)
            return 1

    async def correlate(self, obs: RawObservation) -> CorrelationResult:
        pool = await get_pool()
        async with pool.acquire() as conn:
            obs_id = uuid.uuid4()
            try:
                await conn.execute(
                    """INSERT INTO observations (id, cluster_id, scanner, fingerprint, severity,
                    resource_kind, resource_namespace, resource_name, payload,
                    observed_at, correlation_key)
                    VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT DO NOTHING""",
                    obs_id, obs.cluster_id, obs.scanner, obs.fingerprint, obs.severity,
                    obs.resource_kind, obs.resource_namespace or "", obs.resource_name,
                    "{}", obs.observed_at, obs.correlation_key,
                )
            except Exception:
                await conn.execute(
                    """INSERT INTO observations (id, cluster_id, scanner, fingerprint, severity,
                    resource_kind, resource_namespace, resource_name, payload, observed_at)
                    VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8, $9, $10)
                    ON CONFLICT DO NOTHING""",
                    obs_id, obs.cluster_id, obs.scanner, obs.fingerprint, obs.severity,
                    obs.resource_kind, obs.resource_namespace or "", obs.resource_name,
                    "{}", obs.observed_at,
                )

            obs_count = await self._count_observations(conn, obs.correlation_key)

            existing = await conn.fetchrow(
                "SELECT id, status FROM issues WHERE correlation_key = $1 AND cluster_id = $2::uuid",
                obs.correlation_key, obs.cluster_id,
            )

            if existing and existing["status"] == "open":
                await conn.execute(
                    "UPDATE issues SET last_seen_at = $1, updated_at = $1 WHERE id = $2",
                    obs.observed_at, existing["id"],
                )
                return CorrelationResult(
                    action="attached", issue_id=str(existing["id"]),
                    observation_count=obs_count,
                )

            if existing and existing["status"] == "suppressed":
                await conn.execute(
                    "UPDATE issues SET last_seen_at = $1, updated_at = $1 WHERE id = $2",
                    obs.observed_at, existing["id"],
                )
                return CorrelationResult(
                    action="attached", issue_id=str(existing["id"]),
                    observation_count=obs_count,
                )

            if existing and existing["status"] == "resolved":
                await conn.execute(
                    "UPDATE issues SET status = 'open', last_seen_at = $1, "
                    "resolved_at = NULL, resolved_by = NULL, updated_at = $1 WHERE id = $2",
                    obs.observed_at, existing["id"],
                )
                logger.info(
                    "reopened issue", issue_id=str(existing["id"]),
                    correlation_key=obs.correlation_key,
                )
                return CorrelationResult(
                    action="reopened", issue_id=str(existing["id"]),
                    observation_count=obs_count,
                )

            issue_id = uuid.uuid4()
            await conn.execute(
                """INSERT INTO issues (id, cluster_id, correlation_key, title, severity,
                status, labels, annotations, first_seen_at, last_seen_at, created_at, updated_at)
                VALUES ($1, $2::uuid, $3, $4, $5, 'open', $6, '{}', $7, $7, $7, $7)""",
                issue_id, obs.cluster_id, obs.correlation_key, obs.title, obs.severity,
                f'{{"scanner": "{obs.scanner}", "check_id": "{obs.check_id}", "resource_kind": "{obs.resource_kind}"}}',
                obs.observed_at,
            )

            work_item_id = uuid.uuid4()
            why_now = f"{obs.resource_kind}/{obs.resource_namespace}/{obs.resource_name}: {obs.title}"
            recommended = f"Investigate {obs.check_id} on {obs.resource_namespace}/{obs.resource_name}"

            await conn.execute(
                """INSERT INTO work_items (id, issue_id, cluster_id, title, why_now,
                recommended_next_step, status, confidence, priority, labels,
                annotations, artifact_refs, created_at, updated_at)
                VALUES ($1, $2, $3::uuid, $4, $5, $6, 'ready', 0.7, $7, $8, '{}', '{}', $9, $9)""",
                work_item_id, issue_id, obs.cluster_id, obs.title, why_now, recommended,
                "high" if obs.severity in ("critical", "high") else "medium",
                f'{{"component": "{obs.resource_kind}", "namespace": "{obs.resource_namespace}"}}',
                obs.observed_at,
            )

            await conn.execute(
                "SELECT pg_notify('pinky_work_items', $1)",
                f'{{"event_type": "work_item.created", "aggregate_id": "{work_item_id}"}}',
            )
            await conn.execute(
                "SELECT pg_notify('pinky_issues', $1)",
                f'{{"event_type": "issue.created", "aggregate_id": "{issue_id}"}}',
            )

            logger.info(
                "created issue + work_item",
                issue_id=str(issue_id), work_item_id=str(work_item_id), title=obs.title,
            )
            return CorrelationResult(
                action="created", issue_id=str(issue_id),
                observation_count=obs_count,
            )
