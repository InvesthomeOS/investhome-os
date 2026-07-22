"""Auth API dependencies."""

from uuid import UUID

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.services.auth_service import decode_access_token
from investhome_api.services.permission_service import (
    load_user_with_roles,
    user_can_manage_roles,
    user_can_manage_users,
    user_has_permission,
)
from investhome_api.services import session_service


def _extract_token(
    authorization: str | None = None,
    session_cookie: str | None = None,
) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if session_cookie:
        return session_cookie
    return None


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    ih_session: str | None = Cookie(default=None),
) -> User:
    settings = get_settings()
    if not settings.auth_enabled:
        return _dev_bypass_user(db)

    token = _extract_token(authorization, ih_session)
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

    # Session revocation: tokens with jti must map to an active auth_sessions row.
    # Legacy tokens without jti remain valid until they expire (graceful rollout).
    if jti:
        auth_session = session_service.get_active_session(db, jti)
        if auth_session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been terminated",
            )
        # Short-lived SessionLocal + throttle — never write on the request session
        session_service.touch_session(db, auth_session)

    user = load_user_with_roles(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    if user.status not in {UserStatus.ACTIVE, UserStatus.INVITED}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    # Attach jti for logout / current-session detection (not persisted on User model)
    object.__setattr__(user, "_session_jti", jti)
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
        if not user_has_permission(user, resource, action, db=db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
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
        if any(user_has_permission(user, resource, action, db=db) for resource, action in permissions):
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )

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
