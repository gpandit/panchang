"""Standard API envelope, error, and pagination types.

Every v1 endpoint wraps its payload in ApiResponse or returns ApiErrorResponse
so clients have a consistent shape regardless of domain.
"""

from __future__ import annotations

from pydantic import BaseModel


class ApiResponse[T](BaseModel):
    """Success envelope for all v1 endpoints."""

    data: T
    meta: dict[str, object] | None = None


class ApiError(BaseModel):
    code: str
    message: str
    details: object | None = None


class ApiErrorResponse(BaseModel):
    error: ApiError


class PaginatedMeta(BaseModel):
    total: int
    page: int
    page_size: int
    has_next: bool


class PaginatedResponse[T](BaseModel):
    """Paginated success envelope."""

    data: list[T]
    meta: PaginatedMeta
