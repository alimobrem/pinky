"""Investigation workflow — gathers evidence, runs LLM analysis, produces artifact."""

from dataclasses import dataclass, field
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from pinky_worker.execution.activities import (
        ExecutionEventPayload,
        check_artifact_cache,
        emit_execution_event,
        gather_evidence,
        run_investigation,
        store_artifact,
    )


@dataclass
class InvestigationInput:
    issue_id: str
    cluster_id: str
    correlation_key: str
    evidence_hash: str
    skill_body: str = ""
    skill_tools: list[str] = field(default_factory=list)
    execution_id: str = ""


@dataclass
class InvestigationResult:
    artifact_id: str
    summary: str
    recommended_action: str
    confidence: float
    tool_calls: list[str]
    cached: bool = False


@workflow.defn
class InvestigationWorkflow:
    @workflow.run
    async def run(self, input: InvestigationInput) -> InvestigationResult:
        exec_id = input.execution_id or workflow.info().workflow_id

        await workflow.execute_activity(
            emit_execution_event,
            ExecutionEventPayload(
                execution_id=exec_id,
                event_type="started",
                sequence=0,
                payload={"issue_id": input.issue_id, "type": "investigation"},
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        try:
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="progress",
                    sequence=1,
                    payload={
                        "step_description": "Gathering evidence from cluster",
                        "progress": 0.1,
                        "tools": input.skill_tools,
                    },
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            evidence = await workflow.execute_activity(
                gather_evidence,
                args=[input.issue_id, input.cluster_id, input.skill_tools, exec_id],
                start_to_close_timeout=timedelta(seconds=180),
                retry_policy=RetryPolicy(maximum_attempts=3),
            )

            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="progress",
                    sequence=2,
                    payload={"step_description": "Checking analysis cache", "progress": 0.3},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            cached = await workflow.execute_activity(
                check_artifact_cache,
                args=[evidence.evidence_hash, input.correlation_key],
                start_to_close_timeout=timedelta(seconds=30),
            )

            if cached is not None:
                await workflow.execute_activity(
                    emit_execution_event,
                    ExecutionEventPayload(
                        execution_id=exec_id,
                        event_type="completed",
                        sequence=10,
                        payload={"artifact_id": cached.artifact_id, "cached": True},
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                )
                return InvestigationResult(
                    artifact_id=cached.artifact_id,
                    summary=cached.summary,
                    recommended_action=cached.recommended_action,
                    confidence=cached.confidence,
                    tool_calls=cached.tool_calls,
                    cached=True,
                )

            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="progress",
                    sequence=3,
                    payload={"step_description": "Analyzing with The Brain", "progress": 0.5},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            artifact = await workflow.execute_activity(
                run_investigation,
                args=[evidence, input.skill_body, exec_id],
                start_to_close_timeout=timedelta(seconds=300),
                heartbeat_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="progress",
                    sequence=4,
                    payload={"step_description": "Storing investigation results", "progress": 0.9},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            await workflow.execute_activity(
                store_artifact,
                artifact,
                start_to_close_timeout=timedelta(seconds=30),
            )

            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="completed",
                    sequence=10,
                    payload={"artifact_id": artifact.artifact_id, "confidence": artifact.confidence},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            return InvestigationResult(
                artifact_id=artifact.artifact_id,
                summary=artifact.summary,
                recommended_action=artifact.recommended_action,
                confidence=artifact.confidence,
                tool_calls=artifact.tool_calls,
            )
        except Exception as err:
            await workflow.execute_activity(
                emit_execution_event,
                ExecutionEventPayload(
                    execution_id=exec_id,
                    event_type="failed",
                    sequence=99,
                    payload={"error": str(err)},
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            raise
