"""Common response schemas shared across routes."""

from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    items: list
    next_cursor: str | None = None
    has_more: bool = False


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None
    request_id: str = ""


class ErrorResponse(BaseModel):
    error: ErrorDetail
