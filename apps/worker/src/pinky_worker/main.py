"""Pinky worker entry point — runs Temporal workers and observer daemon.

Starts three concurrent tasks:
1. Temporal workflow workers (investigation, remediation queues)
2. Cluster observer daemon (periodic scanning)
3. Health check (logs worker status)
"""

import asyncio
import logging
import os
import signal
from pathlib import Path

import structlog

from pinky_worker.config import get_settings
from pinky_worker.db import close_pool, get_pool
from pinky_worker.definitions.loader import DefinitionRegistry
from pinky_worker.issues.db_correlator import DbIssueCorrelator
from pinky_worker.observation.observer import observe_cluster
from pinky_worker.queues import INVESTIGATION_QUEUE

logger = structlog.get_logger()


async def run_temporal_workers() -> None:
    settings = get_settings()
    retry_seconds = int(os.environ.get("PINKY_TEMPORAL_RETRY_SECONDS", "10"))

    while True:
        try:
            from temporalio.client import Client
            from temporalio.worker import Worker

            from pinky_worker.execution.activities import (
                apply_change,
                check_artifact_cache,
                emit_execution_event,
                gather_evidence,
                revalidate_binding,
                run_investigation,
                store_artifact,
                validate_approval,
                verify_state,
            )
            from pinky_worker.workflows.investigation import InvestigationWorkflow
            from pinky_worker.workflows.remediation import RemediationWorkflow
            from pinky_worker.workflows.verification import VerificationWorkflow

            client = await Client.connect(settings.temporal.address, namespace=settings.temporal.namespace)
            logger.info("temporal connected", address=settings.temporal.address)

            activities = [
                gather_evidence, check_artifact_cache, run_investigation,
                store_artifact, emit_execution_event, validate_approval,
                apply_change, verify_state, revalidate_binding,
            ]

            workers = [
                Worker(
                    client, task_queue=INVESTIGATION_QUEUE,
                    workflows=[InvestigationWorkflow], activities=activities,
                ),
                Worker(
                    client, task_queue="remediation",
                    workflows=[RemediationWorkflow, VerificationWorkflow],
                    activities=activities,
                ),
            ]

            logger.info("starting temporal workers", count=len(workers))
            await asyncio.gather(*[w.run() for w in workers])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("temporal workers failed — retrying", retry_seconds=retry_seconds)
            await asyncio.sleep(retry_seconds)


async def run_observer(
    registry: DefinitionRegistry,
    correlator: DbIssueCorrelator,
    shutdown_event: asyncio.Event | None = None,
) -> None:
    scan_interval = int(os.environ.get("PINKY_SCAN_INTERVAL", "60"))
    temporal_enabled = os.environ.get("PINKY_TEMPORAL_ENABLED", "true") == "true"

    temporal_client = None

    logger.info("starting observer daemon", scan_interval=scan_interval)

    while True:
        if shutdown_event and shutdown_event.is_set():
            logger.info("shutdown requested, stopping observer daemon")
            break

        if temporal_enabled and temporal_client is None:
            try:
                from temporalio.client import Client
                settings = get_settings()
                temporal_client = await Client.connect(
                    settings.temporal.address, namespace=settings.temporal.namespace,
                )
                logger.info("observer connected to temporal")
            except Exception:
                logger.warning("observer temporal connection failed — will retry next cycle")

        try:
            pool = await get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("SELECT id::text FROM cluster_registry WHERE onboarding_state = 'ready'")
            cluster_ids = [r["id"] for r in rows]

            if not cluster_ids:
                logger.info("no clusters registered — waiting")
            else:
                for cluster_id in cluster_ids:
                    if shutdown_event and shutdown_event.is_set():
                        break
                    try:
                        await observe_cluster(
                            cluster_id=cluster_id,
                            registry=registry,
                            correlator=correlator,
                            scan_interval=scan_interval,
                            max_cycles=1,
                            temporal_client=temporal_client,
                            shutdown_event=shutdown_event,
                        )
                    except Exception:
                        logger.exception("observer scan failed", cluster_id=cluster_id)
        except Exception:
            logger.exception("observer cycle failed")

        await asyncio.sleep(scan_interval)


async def run() -> None:
    logger.info("pinky-worker starting")

    shutdown_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    await get_pool()
    logger.info("database pool initialized")

    default_defs = str(Path(__file__).parent.parent.parent.parent.parent / "definitions")
    definitions_dir = os.environ.get("PINKY_DEFINITIONS_DIR", default_defs)
    registry = DefinitionRegistry()
    loaded = registry.load_filesystem(definitions_dir)
    logger.info("definitions loaded", count=loaded)

    # Load DB definition overrides (API-created definitions take precedence)
    pool = await get_pool()
    db_rows = await pool.fetch(
        "SELECT kind, name, version, body, frontmatter, enabled FROM definitions"
    )
    if db_rows:
        from pinky_worker.definitions.loader import Definition

        db_defs = [
            Definition(
                kind=row["kind"],
                name=row["name"],
                version=row["version"] or "1.0.0",
                frontmatter=row["frontmatter"] or {},
                body=row["body"] or "",
                source="database",
                enabled=row["enabled"],
            )
            for row in db_rows
        ]
        registry.load_database_overrides(db_defs)
        logger.info("loaded DB definition overrides", count=len(db_defs))

    correlator = DbIssueCorrelator()

    observer_enabled = os.environ.get("PINKY_OBSERVER_ENABLED", "true") == "true"
    temporal_enabled = os.environ.get("PINKY_TEMPORAL_ENABLED", "true") == "true"
    webhooks_enabled = os.environ.get("PINKY_WEBHOOKS_ENABLED", "true") == "true"

    tasks = []
    if temporal_enabled:
        tasks.append(run_temporal_workers())
    if observer_enabled:
        tasks.append(run_observer(registry, correlator, shutdown_event=shutdown_event))
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
