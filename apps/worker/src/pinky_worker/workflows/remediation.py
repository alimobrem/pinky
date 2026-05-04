"""Remediation workflow — executes approved plan against a cluster."""

from dataclasses import dataclass
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import (
        ExecutionEventPayload,
        apply_change,
        emit_execution_event,
        validate_approval,
    )
    from pinky_worker.workflows.verification import VerificationInput, VerificationWorkflow


@dataclass
class RemediationInput:
    execution_id: str
    approval_id: str
    cluster_id: str
    binding_id: str
    plan_steps: list[dict]


@dataclass
class RemediationResult:
    status: str
    verification_passed: bool | None = None


@workflow.defn
class RemediationWorkflow:
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

        approval = await workflow.execute_activity(
            validate_approval,
            args=[input.approval_id, ""],
            start_to_close_timeout=timedelta(seconds=5),
        )

        if not approval.get("valid"):
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="failed",
                    sequence=1,
                    payload={"reason": "approval_invalidated"},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )
            return RemediationResult(status="approval_invalidated")

        for i, step in enumerate(input.plan_steps):
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type="progress",
                    sequence=2 + i * 2,
                    payload={"step": i + 1, "total": len(input.plan_steps), "description": step.get("description", "")},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )

            await workflow.execute_activity(
                apply_change,
                args=[input.cluster_id, input.binding_id, step],
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

        verification = await workflow.execute_child_workflow(
            VerificationWorkflow.run,
            VerificationInput(
                execution_id=input.execution_id,
                cluster_id=input.cluster_id,
            ),
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
