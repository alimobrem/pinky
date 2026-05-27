"""Analytics and ROI routes — proving Pinky's value."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.models.execution import Execution
from pinky_api.models.issue import Issue
from pinky_api.models.work_item import WorkItem
from pinky_api.repositories.analytics import AnalyticsRepository

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_SINCE_MAP = {
    "1h": timedelta(hours=1),
    "4h": timedelta(hours=4),
    "24h": timedelta(hours=24),
}

_PERIOD_MAP = {
    "1d": timedelta(days=1),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "90d": timedelta(days=90),
}

_VALID_METRICS = {"token_usage", "issues_resolved", "cache_hit_rate", "scanner_signals"}


@router.get("/watch-summary")
async def watch_summary(since: str = "1h", db: AsyncSession = Depends(get_db)) -> dict:
    delta = _SINCE_MAP.get(since)
    if delta is None:
        raise HTTPException(status_code=400, detail=f"Invalid since value: {since}. Must be one of: 1h, 4h, 24h")
    cutoff = datetime.now(UTC) - delta

    signals_processed = (await db.execute(
        text("SELECT COUNT(*) FROM observations WHERE observed_at > :cutoff"),
        {"cutoff": cutoff},
    )).scalar_one()

    suppressed = (await db.execute(
        text("SELECT COUNT(*) FROM issues WHERE status = 'suppressed' AND updated_at > :cutoff"),
        {"cutoff": cutoff},
    )).scalar_one()

    investigating = (await db.execute(
        text("SELECT COUNT(*) FROM executions WHERE execution_type = 'investigation' AND status = 'running'"),
    )).scalar_one()

    tasks_created = (await db.execute(
        text("SELECT COUNT(*) FROM work_items WHERE created_at > :cutoff"),
        {"cutoff": cutoff},
    )).scalar_one()

    auto_resolved = (await db.execute(
        text("SELECT COUNT(*) FROM issues WHERE status = 'resolved' AND resolved_at > :cutoff"),
        {"cutoff": cutoff},
    )).scalar_one()

    since_seconds = int(delta.total_seconds())
    coverage_result = await db.execute(text("""
        SELECT count(DISTINCT resource_namespace || '/' || resource_name) as workloads_scanned,
               max(observed_at) as last_scan_at
        FROM observations
        WHERE observed_at > now() - make_interval(secs => :since_seconds)
    """), {"since_seconds": since_seconds})
    coverage = coverage_result.fetchone()

    return {
        "since": since,
        "signals_processed": signals_processed,
        "suppressed": suppressed,
        "investigating": investigating,
        "tasks_created": tasks_created,
        "auto_resolved": auto_resolved,
        "workloads_scanned": coverage.workloads_scanned if coverage else 0,
        "last_scan_at": coverage.last_scan_at.isoformat() if coverage and coverage.last_scan_at else None,
        "operator_managed_skipped": 0,
    }


@router.get("/roi")
async def roi_metrics(since: str = "30d", cluster_id: str | None = None, db: AsyncSession = Depends(get_db)) -> dict:
    issues_total = (await db.execute(select(func.count(Issue.id)))).scalar_one()
    issues_resolved = (await db.execute(select(func.count(Issue.id)).where(Issue.status == "resolved"))).scalar_one()
    tasks_total = (await db.execute(select(func.count(WorkItem.id)))).scalar_one()
    tasks_done = (await db.execute(select(func.count(WorkItem.id)).where(WorkItem.status == "done"))).scalar_one()
    executions_total = (await db.execute(select(func.count(Execution.id)))).scalar_one()

    return {
        "period": since,
        "metrics": {
            "issues_total": issues_total,
            "issues_resolved": issues_resolved,
            "tasks_total": tasks_total,
            "tasks_completed": tasks_done,
            "executions_total": executions_total,
            "task_completion_rate": round(tasks_done / tasks_total, 2) if tasks_total > 0 else None,
        },
    }


@router.get("/scanners")
async def scanner_quality(since: str = "30d", db: AsyncSession = Depends(get_db)) -> dict:
    repo = AnalyticsRepository(db)
    scanners = await repo.get_scanner_quality()
    return {"scanners": scanners, "period": since}


@router.get("/trends")
async def trends(
    metric: str = "token_usage",
    period: str = "7d",
    bucket: str = "day",
    cluster_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    if metric not in _VALID_METRICS:
        valid = ", ".join(_VALID_METRICS)
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}. Must be one of: {valid}")
    delta = _PERIOD_MAP.get(period)
    if delta is None:
        raise HTTPException(status_code=400, detail=f"Invalid period: {period}")
    end = datetime.now(UTC)
    start = end - delta
    repo = AnalyticsRepository(db)

    if metric == "token_usage":
        buckets = await repo.get_token_usage_by_period(start, end, bucket)
    elif metric == "issues_resolved":
        buckets = await repo.get_issues_resolved_by_period(start, end, bucket)
    elif metric == "cache_hit_rate":
        cache_data = await repo.get_cache_hit_rate(start, end)
        buckets = [{"timestamp": start.isoformat(), "value": cache_data["rate"]}]
    elif metric == "scanner_signals":
        buckets = await repo.get_scanner_signals_by_period(start, end, bucket)
    else:
        buckets = []

    return {"metric": metric, "period": period, "bucket_size": bucket, "buckets": buckets}


@router.get("/export")
async def export_analytics(since: str = "30d", format: str = "json", db: AsyncSession = Depends(get_db)) -> dict:
    roi = await roi_metrics(since=since, db=db)
    scanners = await scanner_quality(since=since, db=db)
    return {"roi": roi, "scanners": scanners, "format": format}
