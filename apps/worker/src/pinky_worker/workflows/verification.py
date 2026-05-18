"""Verification workflow — checks cluster state after remediation."""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event, verify_state


@dataclass
class VerificationInput:
    execution_id: str
    cluster_id: str
    delay_seconds: int = 60
    expected_state: dict = field(default_factory=dict)
    target_resources: list[dict] = field(default_factory=list)


@dataclass
class VerificationResult:
    passed: bool
    details: dict = field(default_factory=dict)


@workflow.defn
class VerificationWorkflow:
    @workflow.run
    async def run(self, input: VerificationInput) -> VerificationResult:
        await workflow.sleep(timedelta(seconds=input.delay_seconds))

        result = await workflow.execute_activity(
            verify_state,
            args=[input.cluster_id, input.expected_state, input.target_resources],
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        event_type = "verified" if result.get("passed") else "failed"
        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=input.execution_id,
                event_type=event_type,
                sequence=200,
                payload=result,
            ),
            start_to_close_timeout=timedelta(seconds=5),
        )

        return VerificationResult(
            passed=result.get("passed", False),
            details=result.get("details", {}),
        )
