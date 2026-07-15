"""Standard API response helpers (backward compatible with direct model returns)."""

from __future__ import annotations

from math import ceil
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

from investhome_api.core.request_context import get_request_id

T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    total: int | None = None
    pages: int | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard success envelope for new or migrated endpoints."""

    success: bool = True
    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ErrorDetail(BaseModel):
    code: str
    message: str
    field: str | None = None


class ApiErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    details: list[ErrorDetail] | None = None


def meta_with_request_id(**kwargs: Any) -> ResponseMeta:
    return ResponseMeta(request_id=get_request_id(), **kwargs)


def success_response(data: T, **meta_kwargs: Any) -> ApiResponse[T]:
    return ApiResponse(data=data, meta=meta_with_request_id(**meta_kwargs))


def paginated_response(
    items: list[T],
    *,
    total: int,
    page: int = 1,
    page_size: int = 25,
) -> ApiResponse[list[T]]:
    pages = max(1, ceil(total / page_size)) if page_size else 1
    return ApiResponse(
        data=items,
        meta=meta_with_request_id(page=page, page_size=page_size, total=total, pages=pages),
    )


def pagination_meta(*, total: int, page: int, page_size: int) -> dict[str, int]:
    """Shared pagination dict for legacy list responses."""
    pages = max(1, ceil(total / page_size)) if page_size else 1
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
        "request_id": get_request_id() or "",
    }


def error_response(
    *,
    code: str,
    message: str,
    field: str | None = None,
    details: list[ErrorDetail] | None = None,
) -> ApiErrorResponse:
    return ApiErrorResponse(
        error=ErrorDetail(code=code, message=message, field=field),
        meta=meta_with_request_id(),
        details=details,
    )
