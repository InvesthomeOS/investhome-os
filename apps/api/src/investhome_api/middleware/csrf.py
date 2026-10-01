"""Reject cookie-authenticated state-changing requests without a valid CSRF header."""

from __future__ import annotations

from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from investhome_api.api.responses import error_response
from investhome_api.config.settings import get_settings
from investhome_api.core.request_context import get_request_id
from investhome_api.services.auth_service import decode_access_token
from investhome_api.services.csrf import (
    CSRF_EXEMPT_PATHS,
    CSRF_HEADER,
    SAFE_METHODS,
    csrf_binding_key,
    csrf_token_is_valid,
)


def _csrf_rejected() -> JSONResponse:
    payload = error_response(
        code="csrf_rejected",
        message="CSRF token missing or invalid",
    )
    body = payload.model_dump()
    body["detail"] = payload.error.message
    headers = {}
    request_id = get_request_id()
    if request_id:
        headers["X-Request-Id"] = request_id
    return JSONResponse(status_code=403, content=body, headers=headers or None)


class CsrfProtectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method.upper() in SAFE_METHODS:
            return await call_next(request)

        settings = get_settings()
        if not settings.auth_enabled:
            return await call_next(request)

        path = request.url.path
        if path in CSRF_EXEMPT_PATHS:
            return await call_next(request)

        cookie = request.cookies.get(settings.auth_cookie_name)
        if not cookie or not cookie.strip():
            return await call_next(request)

        decoded = decode_access_token(cookie)
        if decoded is None:
            return await call_next(request)

        user_id, jti = decoded
        binding = csrf_binding_key(user_id=str(user_id), jti=jti)
        header_token = request.headers.get(CSRF_HEADER)
        if request.query_params.get("csrf") or request.query_params.get("csrf_token"):
            # Tokens in the query string are ignored and never accepted.
            pass
        if not csrf_token_is_valid(binding, header_token):
            try:
                from investhome_api.services.login_rate_limit import resolve_client_ip
                from investhome_api.services.security_monitoring import SecurityEventKind, observe_security_event

                observe_security_event(
                    SecurityEventKind.CSRF_REJECTED,
                    ip=resolve_client_ip(request),
                )
            except Exception:
                pass
            return _csrf_rejected()
        return await call_next(request)
