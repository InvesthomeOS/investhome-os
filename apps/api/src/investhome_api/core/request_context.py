"""Request-scoped context for correlation IDs and logging."""

from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

REQUEST_ID_HEADER = "X-Request-Id"

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    return _request_id.get()


def set_request_id(request_id: str) -> None:
    _request_id.set(request_id)


def generate_request_id() -> str:
    return str(uuid4())


def resolve_request_id(incoming: str | None) -> str:
    value = (incoming or "").strip()
    if value:
        return value[:128]
    return generate_request_id()
