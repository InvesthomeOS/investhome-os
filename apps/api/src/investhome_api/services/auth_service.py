"""Authentication helpers: password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID, uuid4

import bcrypt
import jwt
from starlette.responses import Response

from investhome_api.config.settings import Settings, get_settings

_SameSite = Literal["lax", "strict", "none"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: UUID, *, jti: str | None = None) -> tuple[str, datetime, str]:
    settings = get_settings()
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    token_jti = jti or str(uuid4())
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "jti": token_jti,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_at, token_jti


def decode_access_token(token: str) -> tuple[UUID, str | None] | None:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        sub = payload.get("sub")
        if not sub:
            return None
        jti = payload.get("jti")
        return UUID(str(sub)), (str(jti) if jti else None)
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
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=cookie_samesite(settings),
        max_age=settings.jwt_expire_minutes * 60,
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
