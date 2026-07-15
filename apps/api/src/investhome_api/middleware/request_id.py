"""Request ID propagation middleware."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from investhome_api.core.logging_config import get_logger
from investhome_api.core.request_context import REQUEST_ID_HEADER, resolve_request_id, set_request_id

logger = get_logger("investhome.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        set_request_id(request_id)
        request.state.request_id = request_id

        logger.info(
            "request.start method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )

        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request.error method=%s path=%s request_id=%s",
                request.method,
                request.url.path,
                request_id,
            )
            raise

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "request.end method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response
