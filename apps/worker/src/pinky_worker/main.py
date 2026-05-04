"""Pinky worker entry point — runs Temporal workers and observer daemon.

Starts three concurrent tasks:
1. Temporal workflow workers (investigation, remediation queues)
2. Cluster observer daemon (periodic scanning)
3. Health check (logs worker status)
"""

import asyncio
import logging
import os
from pathlib import Path

import structlog

from pinky_worker.config import get_settings
from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.db import get_pool, close_pool
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.observer import observe_cluster
from pinky_worker.queues import ALL_QUEUES, INVESTIGATION_QUEUE

logger = structlog.get_logger()


async def run_temporal_workers() -> None:
    settings = get_settings()
    try:
        from temporalio.client import Client
        from temporalio.worker import Worker
        from pinky_worker.workflows.investigation import InvestigationWorkflow
        from pinky_worker.workflows.remediation import RemediationWorkflow
        from pinky_worker.workflows.approval import ApprovalWorkflow
        from pinky_worker.workflows.verification import VerificationWorkflow
        from pinky_worker.execution.activities import (
            gather_evidence, check_artifact_cache, run_investigation,
            store_artifact, emit_execution_event, validate_approval,
            apply_change, verify_state, project_to_postgres,
        )

        client = await Client.connect(settings.temporal.address, namespace=settings.temporal.namespace)
        logger.info("temporal connected", address=settings.temporal.address)

        activities = [
            gather_evidence, check_artifact_cache, run_investigation,
            store_artifact, emit_execution_event, validate_approval,
            apply_change, verify_state, project_to_postgres,
        ]

        workers = [
            Worker(
                client, task_queue=INVESTIGATION_QUEUE,
                workflows=[InvestigationWorkflow], activities=activities,
            ),
            Worker(
                client, task_queue="remediation",
                workflows=[RemediationWorkflow, ApprovalWorkflow, VerificationWorkflow],
                activities=activities,
            ),
        ]

        logger.info("starting temporal workers", count=len(workers))
        await asyncio.gather(*[w.run() for w in workers])

    except Exception:
        logger.exception("temporal workers failed — running observer-only mode")
        await asyncio.Event().wait()


async def run_observer(registry: DefinitionRegistry, correlator: DbIssueCorrelator) -> None:
    scan_interval = int(os.environ.get("PINKY_SCAN_INTERVAL", "60"))

    logger.info("starting observer daemon", scan_interval=scan_interval)

    while True:
        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT id::text FROM cluster_registry WHERE onboarding_state = 'ready'")
            cluster_ids = [r["id"] for r in rows]

            if not cluster_ids:
                logger.info("no clusters registered — waiting")
            else:
                for cluster_id in cluster_ids:
                    try:
                        await observe_cluster(
                            cluster_id=cluster_id,
                            registry=registry,
                            correlator=correlator,
                            scan_interval=scan_interval,
                            max_cycles=1,
                        )
                    except Exception:
                        logger.exception("observer scan failed", cluster_id=cluster_id)
        except Exception:
            logger.exception("observer cycle failed")

        await asyncio.sleep(scan_interval)


async def run() -> None:
    logger.info("pinky-worker starting")

    await get_pool()
    logger.info("database pool initialized")

    definitions_dir = os.environ.get("PINKY_DEFINITIONS_DIR", str(Path(__file__).parent.parent.parent.parent.parent / "definitions"))
    registry = DefinitionRegistry()
    loaded = registry.load_filesystem(definitions_dir)
    logger.info("definitions loaded", count=loaded)

    correlator = DbIssueCorrelator()

    observer_enabled = os.environ.get("PINKY_OBSERVER_ENABLED", "true") == "true"
    temporal_enabled = os.environ.get("PINKY_TEMPORAL_ENABLED", "true") == "true"
    webhooks_enabled = os.environ.get("PINKY_WEBHOOKS_ENABLED", "true") == "true"

    tasks = []
    if temporal_enabled:
        tasks.append(run_temporal_workers())
    if observer_enabled:
        tasks.append(run_observer(registry, correlator))
    if webhooks_enabled:
        from pinky_worker.webhooks.delivery import run_delivery_loop
        tasks.append(run_delivery_loop())

    if not tasks:
        logger.warning("no tasks enabled — idling")
        await asyncio.Event().wait()
    else:
        try:
            await asyncio.gather(*tasks)
        finally:
            await close_pool()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
