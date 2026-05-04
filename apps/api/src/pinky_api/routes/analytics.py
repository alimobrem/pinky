"""Analytics and ROI routes — proving Pinky's value."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.models.execution import Execution
from pinky_api.models.issue import Issue
from pinky_api.models.work_item import WorkItem

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


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
    from pinky_api.models.observation import Observation
    result = await db.execute(
        select(Observation.scanner, func.count(Observation.id).label("total"))
        .group_by(Observation.scanner)
    )
    scanners = [{"scanner": row.scanner, "signal_total": row.total} for row in result.all()]
    return {"scanners": scanners, "period": since}


@router.get("/export")
async def export_analytics(since: str = "30d", format: str = "json", db: AsyncSession = Depends(get_db)) -> dict:
    roi = await roi_metrics(since=since, db=db)
    scanners = await scanner_quality(since=since, db=db)
    return {"roi": roi, "scanners": scanners, "format": format}
