"""Remediation workflow — waits for approval signal, then executes plan against cluster."""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import CancelledError

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import (
        ExecutionEventPayload,
        apply_change,
        emit_execution_event,
        revalidate_binding,
        validate_approval,
    )
    from pinky_worker.queues import VERIFICATION_TIMEOUT
    from pinky_worker.workflows.verification import VerificationInput, VerificationWorkflow


@dataclass
class RemediationInput:
    execution_id: str
    approval_id: str
    cluster_id: str
    binding_id: str
    plan_steps: list[dict]
    changeset_digest: str = ""
    target_resources: list[dict] = field(default_factory=list)


@dataclass
class RemediationResult:
    status: str
    verification_passed: bool | None = None


@workflow.defn
class RemediationWorkflow:
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
    async def run(self, input: RemediationInput) -> RemediationResult:
        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=input.execution_id,
                event_type="started",
                sequence=0,
                payload={"type": "remediation", "steps": len(input.plan_steps)},
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=input.execution_id,
                event_type="approval_required",
                sequence=1,
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
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="timed_out",
                    sequence=2,
                    payload={"reason": "approval_timeout"},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="timed_out")

        if not self._approved:
            reason = self._decision.get("reason", "rejected") if self._decision else "rejected"
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="approval_rejected",
                    sequence=3,
                    payload={"reason": reason},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="rejected")

        signal_digest = self._decision.get("changeset_digest", "") if self._decision else ""

        approval = await workflow.execute_activity(
            validate_approval,
            args=[input.approval_id, signal_digest],
            start_to_close_timeout=timedelta(seconds=5),
        )

        if not approval.get("valid"):
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="failed",
                    sequence=4,
                    payload={"reason": "approval_invalidated", "detail": approval.get("reason", "")},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="approval_invalidated")

        binding_check = await workflow.execute_activity(
            revalidate_binding,
            args=[input.binding_id],
            start_to_close_timeout=timedelta(seconds=5),
        )
        if not binding_check.get("valid"):
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="failed",
                    sequence=5,
                    payload={"reason": "binding_expired", "detail": binding_check.get("reason", "")},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="binding_expired")

        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=input.execution_id,
                event_type="approval_granted",
                sequence=6,
                payload={"changeset_digest": signal_digest},
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        try:
            for i, step in enumerate(input.plan_steps):
                await workflow.execute_activity(
                    emit_execution_event,
                    ExecutionEventPayload(
                        execution_id=input.execution_id,
                        event_type="progress",
                        sequence=10 + i * 2,
                        payload={
                            "step": i + 1,
                            "total": len(input.plan_steps),
                            "description": step.get("description", ""),
                        },
                    ),
                    start_to_close_timeout=timedelta(seconds=5),
                )

                await workflow.execute_activity(
                    apply_change,
                    args=[input.execution_id, input.cluster_id, input.binding_id, {**step, "_step_index": i}],
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )

            verification = await workflow.execute_child_workflow(
                VerificationWorkflow.run,
                VerificationInput(
                    execution_id=input.execution_id,
                    cluster_id=input.cluster_id,
                    target_resources=input.target_resources,
                ),
                execution_timeout=VERIFICATION_TIMEOUT,
            )

            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="completed",
                    sequence=100,
                    payload={"verification_passed": verification.passed},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )

            return RemediationResult(
                status="completed",
                verification_passed=verification.passed,
            )
        except CancelledError:
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="failed",
                    sequence=99,
                    payload={"reason": "cancelled"},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="cancelled")
        except Exception as exc:
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="failed",
                    sequence=99,
                    payload={"reason": "step_failed", "error": str(exc)},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="failed")
