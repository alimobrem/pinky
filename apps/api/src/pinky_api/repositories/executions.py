"""Execution repository."""

import builtins
from typing import Any
from uuid import UUID

from sqlalchemy import select

from pinky_api.models.execution import Execution, ExecutionEvent
from pinky_api.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository):
    async def list(
        self, work_item_id: str | None = None, cluster_id: str | None = None,
        status: str | None = None, limit: int = 50, cursor: str | None = None,
    ) -> dict:
        stmt = select(Execution)
        if work_item_id:
            stmt = stmt.where(Execution.work_item_id == work_item_id)
        if cluster_id:
            stmt = stmt.where(Execution.cluster_id == cluster_id)
        if status:
            statuses = [s.strip() for s in status.split(",")]
            stmt = stmt.where(Execution.status.in_(statuses))
        return await self.paginate(stmt, Execution, limit=limit, cursor=cursor)

    async def get(self, execution_id: UUID) -> Execution | None:
        result = await self.session.execute(select(Execution).where(Execution.id == execution_id))
        return result.scalar_one_or_none()

    async def create(self, **kwargs: object) -> Execution:
        ex = Execution(**kwargs)
        self.session.add(ex)
        await self.session.flush()
        return ex

    async def update_status(self, execution_id: UUID, status: str) -> None:
        from sqlalchemy import update
        await self.session.execute(
            update(Execution).where(Execution.id == execution_id).values(status=status)
        )
        await self.session.flush()

    async def get_events_for_work_item(self, work_item_id: UUID) -> builtins.list[Any]:
        executions = await self.session.execute(
            select(Execution.id).where(Execution.work_item_id == work_item_id)
        )
        exec_ids = [r[0] for r in executions.all()]
        if not exec_ids:
            return []

        events = await self.session.execute(
            select(ExecutionEvent)
            .where(ExecutionEvent.execution_id.in_(exec_ids))
            .order_by(ExecutionEvent.occurred_at)
        )
        return list(events.scalars().all())

    async def get_investigation_for_work_item(self, work_item_id: UUID) -> dict | None:
        executions = await self.session.execute(
            select(Execution.id).where(Execution.work_item_id == work_item_id)
        )
        exec_ids = [r[0] for r in executions.all()]
        if not exec_ids:
            return None

        event = None

        # Try 1: investigation_completed events directly linked
        result = await self.session.execute(
            select(ExecutionEvent)
            .where(ExecutionEvent.execution_id.in_(exec_ids), ExecutionEvent.event_type == "investigation_completed")
            .order_by(ExecutionEvent.occurred_at.desc()).limit(1)
        )
        event = result.scalar_one_or_none()

        # Try 2: completed event has artifact_id — look up artifact
        if event is None:
            result = await self.session.execute(
                select(ExecutionEvent)
                .where(ExecutionEvent.execution_id.in_(exec_ids), ExecutionEvent.event_type == "completed")
                .order_by(ExecutionEvent.occurred_at.desc()).limit(1)
            )
            completed = result.scalar_one_or_none()
            if completed and isinstance(completed.payload, dict):
                artifact_id = completed.payload.get("artifact_id")
                if artifact_id:
                    try:
                        art_result = await self.session.execute(
                            select(ExecutionEvent)
                            .where(
                                ExecutionEvent.execution_id == UUID(artifact_id),
                                ExecutionEvent.event_type == "investigation_completed",
                            )
                            .limit(1)
                        )
                        event = art_result.scalar_one_or_none()
                    except (ValueError, Exception):
                        pass

        if event is None:
            return None

        payload = event.payload if isinstance(event.payload, dict) else {}
        return {
            "artifact_id": payload.get("artifact_id", ""),
            "summary": payload.get("summary", ""),
            "root_cause": payload.get("root_cause", ""),
            "recommended_action": payload.get("recommended_action", ""),
            "confidence": payload.get("confidence", 0.0),
            "tool_calls": payload.get("tool_calls", []),
            "evidence_hash": payload.get("evidence_hash", ""),
            "created_at": payload.get("created_at", event.occurred_at.isoformat() if event.occurred_at else ""),
        }
