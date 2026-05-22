"""Analytics repository — event recording and ROI queries."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select, text

from pinky_api.models.analytics import AnalyticsEvent
from pinky_api.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository):
    async def record(self, event_type: str, payload: dict, **kwargs: object) -> AnalyticsEvent:
        event = AnalyticsEvent(
            event_type=event_type,
            payload=payload,
            occurred_at=datetime.now(UTC),
            **kwargs,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_by_type(
        self,
        event_type: str,
        limit: int = 100,
        cursor: str | None = None,
    ) -> dict:
        stmt = select(AnalyticsEvent).where(AnalyticsEvent.event_type == event_type)
        return await self.paginate(stmt, AnalyticsEvent, limit=limit, cursor=cursor, order_column="occurred_at")

    async def get_token_usage_by_period(
        self, start: datetime, end: datetime, bucket: str = "day",
    ) -> list[dict]:
        result = await self.session.execute(
            text("""
                SELECT date_trunc(:bucket, ee.occurred_at) AS ts,
                       SUM((ee.payload->>'input_tokens')::int) AS input_tokens,
                       SUM((ee.payload->>'output_tokens')::int) AS output_tokens,
                       COUNT(*) AS call_count
                FROM execution_events ee
                WHERE ee.event_type = 'llm_call'
                  AND ee.occurred_at BETWEEN :start AND :end
                GROUP BY ts ORDER BY ts
            """),
            {"bucket": bucket, "start": start, "end": end},
        )
        return [
            {"timestamp": row.ts.isoformat(), "input_tokens": row.input_tokens or 0,
             "output_tokens": row.output_tokens or 0, "call_count": row.call_count}
            for row in result.all()
        ]

    async def get_outcomes_by_period(
        self, start: datetime, end: datetime, cluster_id: str | None = None,
    ) -> dict:
        params: dict = {"start": start, "end": end}
        cluster_filter = ""
        if cluster_id:
            cluster_filter = "AND e.cluster_id = :cluster_id"
            params["cluster_id"] = cluster_id
        result = await self.session.execute(
            text(f"""
                SELECT e.outcome, COUNT(*) as cnt
                FROM executions e
                WHERE e.outcome IS NOT NULL
                  AND e.completed_at BETWEEN :start AND :end
                  {cluster_filter}
                GROUP BY e.outcome
            """),
            params,
        )
        return {row.outcome: row.cnt for row in result.all()}

    async def get_cache_hit_rate(self, start: datetime, end: datetime) -> dict:
        result = await self.session.execute(
            text("""
                SELECT COUNT(*) FILTER (WHERE (payload->>'cache_hit')::boolean = true) AS hits,
                       COUNT(*) AS total
                FROM execution_events
                WHERE event_type = 'llm_call'
                  AND occurred_at BETWEEN :start AND :end
            """),
            {"start": start, "end": end},
        )
        row = result.fetchone()
        total = row.total if row else 0
        hits = row.hits if row else 0
        return {"hits": hits, "total": total, "rate": round(hits / total, 3) if total > 0 else 0.0}

    async def get_approval_turnaround(self, start: datetime, end: datetime) -> dict:
        result = await self.session.execute(
            text("""
                SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY (payload->>'wait_seconds')::float) AS p50,
                       percentile_cont(0.95) WITHIN GROUP (ORDER BY (payload->>'wait_seconds')::float) AS p95
                FROM analytics_events
                WHERE event_type = 'approval_decided'
                  AND occurred_at BETWEEN :start AND :end
            """),
            {"start": start, "end": end},
        )
        row = result.fetchone()
        return {
            "p50_seconds": row.p50 if row and row.p50 else None,
            "p95_seconds": row.p95 if row and row.p95 else None,
        }
