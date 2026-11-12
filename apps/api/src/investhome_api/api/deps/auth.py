"""Auth API dependencies."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings, validate_auth_bypass
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.auth_service import (
    create_access_token,
    decode_access_token,
    seconds_until_token_expiry,
    set_session_cookie,
)
from investhome_api.services.permission_service import (
    load_user_with_roles,
    user_can_manage_roles,
    user_can_manage_users,
    user_has_permission,
)
from investhome_api.services import session_service


def extract_token(
    authorization: str | None = None,
    session_cookie: str | None = None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization[7:].strip()
        if bearer:
            return bearer
    if session_cookie and session_cookie.strip():
        return session_cookie.strip()
    return None


def _pending_session_refresh(
    db: Session,
    user: User,
    token: str,
    jti: str | None,
    auth_session,
) -> tuple[str, datetime] | None:
    """Stage a sliding cookie from data already loaded. Must not query the database."""
    if not jti:
        return None
    remaining = seconds_until_token_expiry(token)
    if remaining is None:
        return None
    from investhome_api.services.session_lifetime import (
        compute_access_expiry,
        idle_timeout,
        session_started_at,
    )

    started = session_started_at(auth_session)
    capped_expiry = compute_access_expiry(started_at=started)
    if capped_expiry is None:
        return None
    idle_seconds = idle_timeout().total_seconds()
    until_cap = (capped_expiry - datetime.now(UTC)).total_seconds()
    if remaining > idle_seconds * 0.5 and remaining <= until_cap + 1:
        return None
    new_token, expires_at, _issued_jti = create_access_token(
        user.id,
        jti=jti,
        auth_time=started,
    )
    if expires_at <= datetime.now(UTC):
        return None
    session_service.extend_session_expiry(db, auth_session, expires_at)
    return new_token, expires_at


def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    ih_session: str | None = Cookie(default=None),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        try:
            validate_auth_bypass(settings)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Insecure authentication configuration",
            ) from exc
        return _dev_bypass_user(db)

    cookie_token = ih_session or request.cookies.get(settings.auth_cookie_name)
    token = extract_token(authorization, cookie_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    decoded = decode_access_token(token)
    if decoded is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )
    user_id, jti = decoded
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    refreshed: tuple[str, datetime] | None = None
    committed = False
    try:
        auth_session = session_service.get_active_session(db, jti)
        if auth_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been terminated",
            )
        user = load_user_with_roles(db, user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        if user.status not in {UserStatus.ACTIVE}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )

        # Attach jti for logout / current-session detection (not persisted on User model)
        object.__setattr__(user, "_session_jti", jti)
        # Role reads are finished. The auth_sessions row lock starts at touch and
        # ends at the commit below; refresh only mutates the loaded session.
        session_service.touch_session(db, auth_session)
        refreshed = _pending_session_refresh(db, user, token, jti, auth_session)
        committed = session_service.commit_auth_transaction(db)
    except HTTPException:
        session_service.abort_auth_transaction(db)
        raise
    except Exception:
        session_service.abort_auth_transaction(db)
        raise

    if committed and refreshed is not None:
        set_session_cookie(response, refreshed[0], refreshed[1])
    return user

def _dev_bypass_user(db: Session) -> User:
    """When auth is disabled, act as super admin for local/test compatibility."""
    user = load_user_with_roles(db, _lookup_super_admin_id(db))
    if user is not None:
        return user
    bypass_id = UUID("00000000-0000-0000-0000-000000000001")
    existing = db.get(User, bypass_id)
    if existing is not None:
        return existing
    bypass = User(
        id=bypass_id,
        full_name="Dev Bypass",
        email="dev-bypass@example.com",
        hashed_password="",
        status=UserStatus.ACTIVE,
    )
    db.add(bypass)
    db.flush()
    return bypass


def _lookup_super_admin_id(db: Session) -> UUID | None:
    from sqlalchemy import select

    from investhome_api.models.user_auth import Role, UserRole

    return db.scalar(
        select(UserRole.user_id)
        .join(Role, Role.id == UserRole.role_id)
        .where(Role.code == "super_admin")
        .limit(1)
    )


def require_permission(resource: str, action: str):
    def _dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        settings = get_settings()
        if not settings.auth_enabled:
            return user
        try:
            allowed = user_has_permission(user, resource, action, db=db)
        except Exception:
            session_service.abort_auth_transaction(db)
            raise
        if not allowed:
            session_service.abort_auth_transaction(db)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        session_service.release_read_transaction(db)
        return user

    return _dependency


def require_any_permission(*permissions: tuple[str, str]):
    """Require at least one of the given (resource, action) pairs."""

    def _dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        settings = get_settings()
        if not settings.auth_enabled:
            return user
        try:
            allowed = any(
                user_has_permission(user, resource, action, db=db) for resource, action in permissions
            )
        except Exception:
            session_service.abort_auth_transaction(db)
            raise
        if not allowed:
            session_service.abort_auth_transaction(db)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        session_service.release_read_transaction(db)
        return user

    return _dependency

def require_manage_users():
    def _dependency(user: User = Depends(get_current_user)) -> User:
        settings = get_settings()
        if not settings.auth_enabled:
            return user
        if not user_can_manage_users(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency


def require_manage_roles():
    def _dependency(user: User = Depends(get_current_user)) -> User:
        settings = get_settings()
        if not settings.auth_enabled:
            return user
        if not user_can_manage_roles(user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency
