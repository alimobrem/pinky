"""Approval workflow — waits for human signal or timeout."""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event


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
        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=input.execution_id,
                event_type="approval_required",
                sequence=0,
                payload={
                    "changeset_digest": input.changeset_digest,
                    "target_resources": input.target_resources,
                },
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        try:
            await workflow.wait_condition(
                lambda: self._decision is not None,
                timeout=timedelta(hours=4),
            )
        except TimeoutError:
            return ApprovalResult(status="expired")

        return ApprovalResult(
            status="approved" if self._approved else "rejected",
            decision=self._decision,
        )
