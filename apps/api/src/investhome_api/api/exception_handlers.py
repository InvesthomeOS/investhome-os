"""Global API exception handlers with standardized error envelopes."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from investhome_api.api.responses import ApiErrorResponse, ErrorDetail, error_response
from investhome_api.core.logging_config import get_logger
from investhome_api.core.request_context import get_request_id

logger = get_logger("investhome.errors")


def _json_error(payload: ApiErrorResponse, status_code: int) -> JSONResponse:
    body = payload.model_dump()
    # Legacy FastAPI clients expect `detail` (string or list).
    body["detail"] = payload.error.message
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed"
        code = _status_to_code(exc.status_code)
        payload = error_response(code=code, message=message)
        return _json_error(payload, exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        message = exc.detail if isinstance(exc.detail, str) else "Request failed"
        payload = error_response(code=_status_to_code(exc.status_code), message=message)
        return _json_error(payload, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[ErrorDetail] = []
        for err in exc.errors():
            loc = err.get("loc", ())
            field = ".".join(str(part) for part in loc if part != "body") or None
            details.append(
                ErrorDetail(
                    code="validation_error",
                    message=str(err.get("msg", "Invalid value")),
                    field=field,
                )
            )
        payload = error_response(
            code="validation_error",
            message="Validation failed",
            details=details or None,
        )
        return _json_error(payload, 422)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception request_id=%s", get_request_id())
        payload = error_response(code="internal_error", message="An unexpected error occurred")
        return _json_error(payload, 500)


def _status_to_code(status_code: int) -> str:
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        413: "payload_too_large",
        422: "validation_error",
        429: "rate_limited",
        500: "internal_error",
        503: "service_unavailable",
    }
    return mapping.get(status_code, "http_error")
