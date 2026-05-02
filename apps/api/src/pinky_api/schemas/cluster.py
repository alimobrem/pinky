"""Cluster response schema — matches @pinky/contracts ClusterRegistryEntry type."""

from pydantic import BaseModel


class ClusterResponse(BaseModel):
    id: str
    display_name: str
    api_endpoint: str
    fleet_identifier: str | None = None
    onboarding_state: str
    offboarding_state: str | None = None
    created_at: str = ""
    warning: str | None = None


class ClusterListResponse(BaseModel):
    items: list[ClusterResponse]
    next_cursor: str | None = None
    has_more: bool = False
