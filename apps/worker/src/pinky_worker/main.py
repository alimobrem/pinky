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
from pinky_worker.issues.correlator import IssueCorrelator
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


async def run_observer(registry: DefinitionRegistry, correlator: IssueCorrelator) -> None:
    cluster_id = os.environ.get("PINKY_OBSERVER_CLUSTER_ID", "default")
    scan_interval = int(os.environ.get("PINKY_SCAN_INTERVAL", "60"))

    logger.info("starting observer daemon", cluster_id=cluster_id, scan_interval=scan_interval)

    while True:
        try:
            await observe_cluster(
                cluster_id=cluster_id,
                registry=registry,
                correlator=correlator,
                scan_interval=scan_interval,
                max_cycles=1,
            )
        except Exception:
            logger.exception("observer scan cycle failed", cluster_id=cluster_id)

        await asyncio.sleep(scan_interval)


async def run() -> None:
    logger.info("pinky-worker starting")

    definitions_dir = os.environ.get("PINKY_DEFINITIONS_DIR", str(Path(__file__).parent.parent.parent.parent.parent / "definitions"))
    registry = DefinitionRegistry()
    loaded = registry.load_filesystem(definitions_dir)
    logger.info("definitions loaded", count=loaded)

    correlator = IssueCorrelator()

    observer_enabled = os.environ.get("PINKY_OBSERVER_ENABLED", "true") == "true"
    temporal_enabled = os.environ.get("PINKY_TEMPORAL_ENABLED", "true") == "true"

    tasks = []
    if temporal_enabled:
        tasks.append(run_temporal_workers())
    if observer_enabled:
        tasks.append(run_observer(registry, correlator))

    if not tasks:
        logger.warning("no tasks enabled — idling")
        await asyncio.Event().wait()
    else:
        await asyncio.gather(*tasks)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())


if __name__ == "__main__":
    main()
