"""Verification workflow — checks cluster state after remediation."""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import CancelledError

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import ExecutionEventPayload, emit_execution_event, verify_state


@dataclass
class VerificationInput:
    execution_id: str
    cluster_id: str
    delay_seconds: int = 60
    max_attempts: int = 3
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
        try:
            await workflow.sleep(timedelta(seconds=input.delay_seconds))

            result: dict = {}
            attempt = 0
            for attempt in range(input.max_attempts):
                result = await workflow.execute_activity(
                    verify_state,
                    args=[input.cluster_id, input.expected_state, input.target_resources],
                    start_to_close_timeout=timedelta(seconds=30),
                    retry_policy=RetryPolicy(maximum_attempts=2),
                )
                if result.get("passed"):
                    break
                if attempt < input.max_attempts - 1:
                    await workflow.sleep(timedelta(seconds=input.delay_seconds))

            event_type = "verified" if result.get("passed") else "failed"
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=input.execution_id,
                    event_type=event_type,
                    sequence=200,
                    payload={**result, "attempts": attempt + 1},
                ),
                start_to_close_timeout=timedelta(seconds=5),
            )

            return VerificationResult(
                passed=result.get("passed", False),
                details=result.get("details", {}),
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
            raise
