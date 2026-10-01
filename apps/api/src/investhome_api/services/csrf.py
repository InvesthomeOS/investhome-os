"""CSRF tokens bound to cookie session identity (jti)."""

from __future__ import annotations

import base64
import hmac
from hashlib import sha256

from investhome_api.config.settings import get_settings

CSRF_HEADER = "X-CSRF-Token"
CSRF_PURPOSE = b"csrf-v1:"

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})
STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Pre-session auth flows. Cookie may be stale; do not block login/MFA.
CSRF_EXEMPT_PATHS = frozenset(
    {
        "/auth/login",
        "/auth/mfa/verify",
        "/auth/mfa/enroll/required",
        "/auth/mfa/enroll/required/confirm",
        "/webhooks/whatsapp",
        "/webhooks/whatsapp/",
    }
)


def csrf_binding_key(*, user_id: str, jti: str | None) -> str:
    if jti and jti.strip():
        return jti.strip()
    return f"sub:{user_id}"


def issue_csrf_token(binding_key: str) -> str:
    secret = get_settings().jwt_secret.encode("utf-8")
    digest = hmac.new(secret, CSRF_PURPOSE + binding_key.encode("utf-8"), sha256).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def csrf_token_is_valid(binding_key: str, provided: str | None) -> bool:
    if not binding_key or not provided:
        return False
    token = provided.strip()
    if not token:
        return False
    expected = issue_csrf_token(binding_key)
    if len(token) != len(expected):
        return False
    return hmac.compare_digest(expected, token)
