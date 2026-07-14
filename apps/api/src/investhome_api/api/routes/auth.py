"""Authentication routes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user
from investhome_api.config.settings import get_settings
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.auth import (
    ChangePasswordRequest,
    CurrentUserResponse,
    LoginRequest,
    MessageResponse,
)
from investhome_api.services.audit_service import record_auth_event, record_login_failed
from investhome_api.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)
from investhome_api.services.permission_service import load_user_with_roles
from investhome_api.services.user_service import serialize_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=CurrentUserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    settings = get_settings()
    user = db.scalar(
        select(User).where(User.email == payload.email.lower(), User.archived_at.is_(None))
    )

    if user is None or not verify_password(payload.password, user.hashed_password):
        record_login_failed(db, email=payload.email.lower(), user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.status == UserStatus.INACTIVE:
        record_login_failed(db, email=payload.email.lower(), user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    if user.status == UserStatus.SUSPENDED:
        record_login_failed(db, email=payload.email.lower(), user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    user.last_login_at = datetime.now(UTC)
    if user.status == UserStatus.INVITED:
        user.status = UserStatus.ACTIVE
    db.flush()

    loaded = load_user_with_roles(db, user.id)
    assert loaded is not None

    token, expires_at = create_access_token(loaded.id)
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_samesite,
        max_age=settings.jwt_expire_minutes * 60,
        expires=expires_at,
        path="/",
    )

    record_auth_event(
        "auth.login",
        db=db,
        actor=loaded,
        actor_id=loaded.id,
        target_id=loaded.id,
        request=request,
    )
    db.commit()
    return serialize_current_user(loaded)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/")
    record_auth_event(
        "auth.logout",
        db=db,
        actor=user,
        actor_id=user.id,
        target_id=user.id,
        request=request,
        commit=True,
    )
    return MessageResponse(message="Logged out")


@router.get("/me", response_model=CurrentUserResponse)
def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return serialize_current_user(user)


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MessageResponse:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password",
        )

    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = datetime.now(UTC)
    record_auth_event(
        "auth.password_changed",
        db=db,
        actor=user,
        actor_id=user.id,
        target_id=user.id,
        request=request,
    )
    db.commit()
    return MessageResponse(message="Password updated")
