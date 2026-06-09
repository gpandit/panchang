"""Standard API envelope, error, and pagination types.

Every v1 endpoint wraps its payload in ApiResponse or returns ApiErrorResponse
so clients have a consistent shape regardless of domain.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
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


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated success envelope."""

    data: list[T]
    meta: PaginatedMeta
