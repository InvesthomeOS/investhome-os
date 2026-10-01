"""Authentication helpers: password hashing and JWT tokens."""

import hashlib
import re
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import bcrypt
import jwt
from starlette.responses import Response

from investhome_api.config.settings import Settings, get_settings

_SameSite = Literal["lax", "strict", "none"]
# bcrypt silently truncates beyond 72 bytes; pre-hash only those secrets.
_BCRYPT_MAX_BYTES = 72
_JTI_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def normalize_session_jti(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    jti = value.strip()
    if not jti or not _JTI_RE.fullmatch(jti):
        return None
    return jti


def _bcrypt_secret(password: str) -> bytes:
    raw = password.encode("utf-8")
    if len(raw) > _BCRYPT_MAX_BYTES:
        # Hex digest stays inside bcrypt's 72-byte limit and avoids NUL truncation.
        return hashlib.sha256(raw).hexdigest().encode("ascii")
    return raw


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_secret(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_bcrypt_secret(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    user_id: UUID,
    *,
    jti: str | None = None,
    auth_time: datetime | None = None,
    now: datetime | None = None,
) -> tuple[str, datetime, str]:
    from investhome_api.services.session_lifetime import (
        AUTH_TIME_CLAIM,
        auth_time_timestamp,
        compute_access_expiry,
    )

    settings = get_settings()
    current = now or datetime.now(UTC)
    started = auth_time or current
    expires_at = compute_access_expiry(started_at=started, now=current)
    if expires_at is None:
        expires_at = current
    token_jti = jti or str(uuid4())
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": current,
        "jti": token_jti,
        AUTH_TIME_CLAIM: auth_time_timestamp(started),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at, token_jti


def decode_access_token(token: str) -> tuple[UUID, str] | None:
    from investhome_api.services.session_lifetime import AUTH_TIME_CLAIM, absolute_timeout

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            return None
        auth_time = payload.get(AUTH_TIME_CLAIM)
        if isinstance(auth_time, (int, float)):
            started = datetime.fromtimestamp(float(auth_time), tz=UTC)
            if datetime.now(UTC) >= started + absolute_timeout():
                return None
        jti = normalize_session_jti(payload.get("jti"))
        if not jti:
            return None
        return UUID(str(sub)), jti
    except jwt.PyJWTError:
        return None


def cookie_samesite(settings: Settings | None = None) -> _SameSite:
    settings = settings or get_settings()
    value = (settings.auth_cookie_samesite or "lax").lower()
    if value in {"lax", "strict", "none"}:
        return value  # type: ignore[return-value]
    return "lax"


def set_session_cookie(response: Response, token: str, expires_at: datetime) -> None:
    """Write ih_session with the same attributes used by /auth/login."""
    settings = get_settings()
    remaining = int((expires_at - datetime.now(UTC)).total_seconds())
    max_age = max(1, remaining) if remaining > 0 else 0
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=cookie_samesite(settings),
        max_age=max_age,
        expires=expires_at,
        path="/",
    )


def seconds_until_token_expiry(token: str) -> float | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return None
        return float(exp) - datetime.now(UTC).timestamp()
    except jwt.PyJWTError:
        return None
