"""Approval workflow — waits for human signal or timeout."""

import asyncio
from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow


@dataclass
class ApprovalInput:
    execution_id: str
    changeset: dict
    changeset_digest: str
    target_resources: list[dict]


@dataclass
class ApprovalResult:
    status: str  # "approved" | "rejected" | "expired"
    decision: dict | None = None


@workflow.defn
class ApprovalWorkflow:
    def __init__(self) -> None:
        self._decision: dict | None = None
        self._approved: bool = False

    @workflow.signal
    async def approve(self, payload: dict) -> None:
        self._approved = True
        self._decision = payload

    @workflow.signal
    async def reject(self, payload: dict) -> None:
        self._approved = False
        self._decision = payload

    @workflow.run
    async def run(self, input: ApprovalInput) -> ApprovalResult:
        # TODO: emit approval_required execution event

        try:
            await workflow.wait_condition(
                lambda: self._decision is not None,
                timeout=timedelta(hours=4),
            )
        except asyncio.TimeoutError:
            return ApprovalResult(status="expired")

        return ApprovalResult(
            status="approved" if self._approved else "rejected",
            decision=self._decision,
        )
