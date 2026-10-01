"""Allow credentialed browser CORS only for configured origins."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from investhome_api.config.cors import (
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    CORS_EXPOSE_HEADERS,
)


class StrictCorsMiddleware:
    """Exact-origin CORS. No wildcard, no reflected arbitrary origins."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        allow_origins: list[str],
        allow_methods: list[str] | None = None,
        allow_headers: list[str] | None = None,
        expose_headers: list[str] | None = None,
        allow_credentials: bool = True,
    ) -> None:
        self.app = app
        self.allow_origins = frozenset(allow_origins)
        methods = allow_methods or list(CORS_ALLOWED_METHODS)
        headers = allow_headers or list(CORS_ALLOWED_HEADERS)
        self.allow_methods = frozenset(method.upper() for method in methods)
        self.allow_headers = frozenset(header.lower() for header in headers)
        self.expose_headers = tuple(expose_headers or CORS_EXPOSE_HEADERS)
        self.allow_credentials = bool(allow_credentials) and bool(self.allow_origins)
        self._methods_header = ", ".join(CORS_ALLOWED_METHODS)
        if allow_methods:
            self._methods_header = ", ".join(allow_methods)

    def _origin_allowed(self, origin: str | None) -> bool:
        return bool(origin) and origin in self.allow_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        origin = headers.get("origin")
        if origin is None:
            await self.app(scope, receive, send)
            return

        requested_method = headers.get("access-control-request-method")
        if scope["method"].upper() == "OPTIONS" and requested_method:
            response = self._preflight_response(origin, headers)
            await response(scope, receive, send)
            return

        await self.app(scope, receive, self._wrap_send(send, origin))

    def _preflight_response(self, origin: str, headers: Headers) -> PlainTextResponse:
        requested_method = (headers.get("access-control-request-method") or "").upper()
        requested_headers = headers.get("access-control-request-headers") or ""
        extra = [item.strip().lower() for item in requested_headers.split(",") if item.strip()]
        failures: list[str] = []
        if not self._origin_allowed(origin):
            failures.append("origin")
        if requested_method not in self.allow_methods:
            failures.append("method")
        if any(item not in self.allow_headers for item in extra):
            failures.append("headers")
        if failures:
            return PlainTextResponse("Disallowed CORS " + ", ".join(failures), status_code=400)

        response_headers: dict[str, str] = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": self._methods_header,
            "Access-Control-Allow-Headers": requested_headers or ", ".join(CORS_ALLOWED_HEADERS),
            "Vary": "Origin",
        }
        if self.allow_credentials:
            response_headers["Access-Control-Allow-Credentials"] = "true"
        return PlainTextResponse("OK", status_code=200, headers=response_headers)

    def _wrap_send(self, send: Send, origin: str) -> Send:
        allowed = self._origin_allowed(origin)

        async def send_wrapper(message: MutableMapping[str, Any]) -> None:
            if message["type"] == "http.response.start" and allowed:
                message.setdefault("headers", [])
                headers = MutableHeaders(raw=message["headers"])
                headers["Access-Control-Allow-Origin"] = origin
                vary = headers.get("vary")
                if vary and "origin" not in vary.lower():
                    headers["vary"] = f"{vary}, Origin"
                elif not vary:
                    headers["vary"] = "Origin"
                if self.allow_credentials:
                    headers["Access-Control-Allow-Credentials"] = "true"
                if self.expose_headers:
                    headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
            await send(message)

        return send_wrapper
