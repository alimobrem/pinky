"""Issue routes — correlated operational problems."""

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from pinky_api.auth.deps import (
    principal_uuid,
    require_authenticated,
    require_cluster_read_access,
    require_cluster_write_access,
)
from pinky_api.db.deps import get_db
from pinky_api.events import emit
from pinky_api.repositories.bindings import BindingRepository
from pinky_api.repositories.issues import IssueRepository


class SuppressRequest(BaseModel):
    until: datetime | None = None

router = APIRouter(prefix="/api/v1/issues", tags=["issues"])


def _serialize(issue: Any) -> dict:
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
    principal: dict = Depends(require_authenticated),
) -> dict:
    binding_repo = BindingRepository(db)
    allowed_clusters = await binding_repo.list_accessible_cluster_ids(principal_uuid(principal))
    if cluster_id:
        await require_cluster_read_access(UUID(cluster_id), principal, db, require_binding=True)
    repo = IssueRepository(db)
    result = await repo.list(
        cluster_id=cluster_id,
        cluster_ids=None if cluster_id else allowed_clusters,
        status=status,
        severity=severity,
        limit=limit,
        cursor=cursor,
    )
    return {
        "items": [_serialize(i) for i in result["items"]],
        "next_cursor": result["next_cursor"],
        "has_more": result["has_more"],
        "total_count": result.get("total_count", len(result["items"])),
    }


@router.get("/{issue_id}")
async def get_issue(issue_id: str, db: AsyncSession = Depends(get_db), principal: dict = Depends(require_authenticated)) -> dict:
    repo = IssueRepository(db)
    issue = await repo.get(UUID(issue_id))
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    await require_cluster_read_access(issue.cluster_id, principal, db, require_binding=True)
    return _serialize(issue)


@router.post("/{issue_id}/suppress")
async def suppress_issue(
    issue_id: str,
    req: SuppressRequest,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = IssueRepository(db)
    current = await repo.get(UUID(issue_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    issue = await repo.suppress(UUID(issue_id), until=req.until)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    await emit(db, "issue.suppressed", "issue", UUID(issue_id), {"status": "suppressed"})
    await db.commit()
    return _serialize(issue)


@router.post("/{issue_id}/resolve")
async def resolve_issue(
    issue_id: str,
    db: AsyncSession = Depends(get_db),
    _principal: dict = Depends(require_authenticated),
) -> dict:
    repo = IssueRepository(db)
    current = await repo.get(UUID(issue_id))
    if current is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    await require_cluster_write_access(current.cluster_id, _principal, db)
    issue = await repo.resolve(UUID(issue_id))
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    await emit(db, "issue.resolved", "issue", UUID(issue_id), {"status": "resolved"})
    await db.commit()
    return _serialize(issue)
