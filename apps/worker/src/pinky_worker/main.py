"""Pinky worker entry point — connects to Temporal and runs workflow workers."""

import asyncio
import structlog

from temporalio.client import Client
from temporalio.worker import Worker

from pinky_worker.config import get_settings
from pinky_worker.queues import ALL_QUEUES, INVESTIGATION_QUEUE
from pinky_worker.workflows.investigation import InvestigationWorkflow
from pinky_worker.workflows.remediation import RemediationWorkflow
from pinky_worker.workflows.approval import ApprovalWorkflow
from pinky_worker.workflows.verification import VerificationWorkflow

logger = structlog.get_logger()

WORKFLOW_REGISTRY = {
    INVESTIGATION_QUEUE: [InvestigationWorkflow],
    "remediation": [RemediationWorkflow],
    "observation": [],
    "projection": [],
}

APPROVAL_WORKFLOWS = [ApprovalWorkflow]
VERIFICATION_WORKFLOWS = [VerificationWorkflow]


async def run() -> None:
    settings = get_settings()
    logger.info("connecting to temporal", address=settings.temporal.address, namespace=settings.temporal.namespace)

    client = await Client.connect(settings.temporal.address, namespace=settings.temporal.namespace)
    logger.info("temporal connected")

    workers = []
    for queue in ALL_QUEUES:
        workflows = WORKFLOW_REGISTRY.get(queue, [])
        if queue == "remediation":
            workflows = workflows + APPROVAL_WORKFLOWS + VERIFICATION_WORKFLOWS
        if workflows:
            worker = Worker(client, task_queue=queue, workflows=workflows, activities=[])
            workers.append(worker)
            logger.info("registered worker", queue=queue, workflows=[w.__name__ for w in workflows])

    if not workers:
        logger.warning("no workers registered, nothing to do")
        return

    logger.info("starting workers", count=len(workers))
    await asyncio.gather(*[w.run() for w in workers])


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
