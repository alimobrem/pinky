"""Issue routes — correlated operational problems."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.db.deps import get_db
from pinky_api.repositories.issues import IssueRepository

router = APIRouter(prefix="/api/v1/issues", tags=["issues"])


def _serialize(issue: object) -> dict:
    return {
        "id": str(issue.id),
        "cluster_id": str(issue.cluster_id),
        "correlation_key": issue.correlation_key,
        "title": issue.title,
        "severity": issue.severity,
        "status": issue.status,
        "labels": issue.labels or {},
        "annotations": issue.annotations or {},
        "runbook_url": issue.runbook_url,
        "first_seen_at": issue.first_seen_at.isoformat() if issue.first_seen_at else "",
        "last_seen_at": issue.last_seen_at.isoformat() if issue.last_seen_at else "",
        "resolved_at": issue.resolved_at.isoformat() if issue.resolved_at else None,
        "created_at": issue.created_at.isoformat() if issue.created_at else "",
        "suppressed_until": issue.suppressed_until.isoformat() if issue.suppressed_until else None,
        "updated_at": issue.updated_at.isoformat() if issue.updated_at else "",
    }


@router.get("")
async def list_issues(
    cluster_id: str | None = None,
    status: str | None = None,
    severity: str | None = None,
    cursor: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = IssueRepository(db)
    result = await repo.list(cluster_id=cluster_id, status=status, severity=severity, limit=limit, cursor=cursor)
    return {
        "items": [_serialize(i) for i in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
    }


@router.get("/{issue_id}")
async def get_issue(issue_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    repo = IssueRepository(db)
    issue = await repo.get(UUID(issue_id))
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    return _serialize(issue)
