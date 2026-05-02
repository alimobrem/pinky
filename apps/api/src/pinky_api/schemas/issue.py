"""Issue response schema — matches @pinky/contracts Issue type."""

from pydantic import BaseModel


class IssueResponse(BaseModel):
    id: str
    cluster_id: str
    correlation_key: str
    title: str
    severity: str
    status: str
    labels: dict[str, str] = {}
    annotations: dict[str, str] = {}
    runbook_url: str | None = None
    first_seen_at: str
    last_seen_at: str
    resolved_at: str | None = None
    created_at: str = ""


class IssueListResponse(BaseModel):
    items: list[IssueResponse]
    next_cursor: str | None = None
    has_more: bool = False
