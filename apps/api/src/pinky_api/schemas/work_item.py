"""Work item response schema — matches @pinky/contracts WorkItem type."""

from pydantic import BaseModel


class WorkItemResponse(BaseModel):
    id: str
    issue_id: str | None = None
    cluster_id: str
    title: str
    why_now: str | None = None
    recommended_next_step: str | None = None
    status: str
    owner_id: str | None = None
    confidence: float | None = None
    priority: str = "medium"
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    runbook_url: str | None = None
    created_at: str = ""
    updated_at: str = ""


class WorkItemListResponse(BaseModel):
    items: list[WorkItemResponse]
    next_cursor: str | None = None
    has_more: bool = False
