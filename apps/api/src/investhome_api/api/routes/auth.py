"""Authentication routes."""

from datetime import UTC, datetime, timedelta
from typing import NoReturn
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import extract_token, get_current_user
from investhome_api.config.settings import Settings, get_settings
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.auth import (
    ChangePasswordRequest,
    CsrfTokenResponse,
    CurrentUserResponse,
    LoginRequest,
    MessageResponse,
    MfaChallengeRequiredResponse,
    MfaEnrollConfirmRequest,
    MfaEnrollConfirmResponse,
    MfaEnrollStartResponse,
    MfaEnrollmentChallengeRequest,
    MfaEnrollmentCompleteResponse,
    MfaEnrollmentConfirmRequiredRequest,
    MfaEnrollmentRequiredResponse,
    MfaVerifyRequest,
)
from investhome_api.services import session_service
from investhome_api.services.csrf import csrf_binding_key, issue_csrf_token
from investhome_api.services.audit_service import record_auth_event, record_login_failed
from investhome_api.services.auth_service import (
    cookie_samesite,
    create_access_token,
    decode_access_token,
    hash_password,
    set_session_cookie,
    verify_password,
)
from investhome_api.services.password_policy import (
    GENERIC_PASSWORD_ERROR,
    PasswordPolicyError,
    production_blocks_demo_staff_login,
    validate_new_password,
)
from investhome_api.services.login_rate_limit import (
    clear_failed_login_attempts_for_identity,
    clear_mfa_confirm_failures,
    clear_mfa_verify_failures,
    enforce_login_rate_limit,
    enforce_mfa_confirm_rate_limit,
    enforce_mfa_verify_rate_limit,
    normalize_login_identity,
    record_failed_login_attempt,
    record_failed_mfa_confirm,
    record_failed_mfa_verify,
    resolve_client_ip,
)
from investhome_api.services.mfa_challenge import (
    consume_mfa_challenge,
    create_mfa_challenge,
    hash_challenge_token,
    peek_mfa_challenge,
)
from investhome_api.services.mfa_enrollment import confirm_enrollment, start_enrollment
from investhome_api.services.mfa_enforcement import (
    PURPOSE_ENROLLMENT,
    PURPOSE_LOGIN,
    user_needs_mfa_enrollment,
)
from investhome_api.services.mfa_login import (
    INVALID_MFA_MESSAGE,
    mark_recovery_code_used,
    user_requires_mfa_challenge,
    verify_login_mfa_code,
)
from investhome_api.services.permission_service import load_user_with_roles
from investhome_api.services.user_service import serialize_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


def _clear_auth_cookie(response: Response, settings: Settings) -> None:
    """Clear ih_session with the same attributes used by set_cookie on login."""
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path="/",
        secure=settings.auth_cookie_secure,
        httponly=True,
        samesite=cookie_samesite(settings),
    )


def _reject_mfa_verify(*, ip: str, identity: str) -> NoReturn:
    record_failed_mfa_verify(ip=ip, identity=identity)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=INVALID_MFA_MESSAGE,
    )


def _reject_enrollment_challenge(*, ip: str, identity: str) -> NoReturn:
    record_failed_mfa_verify(ip=ip, identity=identity)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=INVALID_MFA_MESSAGE,
    )


def _issue_authenticated_session(
    *,
    db: Session,
    user: User,
    request: Request,
    response: Response,
) -> CurrentUserResponse:
    settings = get_settings()
    user.last_login_at = datetime.now(UTC)
    if user.status == UserStatus.INVITED:
        user.status = UserStatus.ACTIVE
    db.flush()

    from investhome_api.services.session_lifetime import compute_access_expiry, session_started_at

    loaded = load_user_with_roles(db, user.id)
    assert loaded is not None

    started = datetime.now(UTC)
    expires_at_preview = compute_access_expiry(started_at=started, now=started)
    if expires_at_preview is None:
        expires_at_preview = started + timedelta(minutes=settings.jwt_expire_minutes)
    auth_session = session_service.create_session(
        db, user=loaded, expires_at=expires_at_preview, request=request
    )
    token, expires_at, _jti = create_access_token(
        loaded.id,
        jti=auth_session.token_jti,
        auth_time=session_started_at(auth_session),
    )
    auth_session.expires_at = expires_at
    set_session_cookie(response, token, expires_at)

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


@router.post(
    "/login",
    response_model=CurrentUserResponse | MfaChallengeRequiredResponse | MfaEnrollmentRequiredResponse,
)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUserResponse | MfaChallengeRequiredResponse | MfaEnrollmentRequiredResponse:
    identity = normalize_login_identity(str(payload.email))
    client_ip = resolve_client_ip(request)
    enforce_login_rate_limit(ip=client_ip, identity=identity)

    user = db.scalar(
        select(User).where(User.email == identity, User.archived_at.is_(None))
    )

    if user is None or not verify_password(payload.password, user.hashed_password):
        record_login_failed(db, email=identity, user=user, request=request)
        record_failed_login_attempt(ip=client_ip, identity=identity)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.is_demo and production_blocks_demo_staff_login():
        record_login_failed(db, email=identity, user=user, request=request)
        record_failed_login_attempt(ip=client_ip, identity=identity)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user.status == UserStatus.INACTIVE:
        record_login_failed(db, email=identity, user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )

    if user.status == UserStatus.SUSPENDED:
        record_login_failed(db, email=identity, user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is suspended",
        )

    clear_failed_login_attempts_for_identity(identity)

    loaded = load_user_with_roles(db, user.id)
    if loaded is None:
        record_login_failed(db, email=identity, user=user, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if user_requires_mfa_challenge(loaded):
        challenge_token, expires_in = create_mfa_challenge(
            user_id=str(loaded.id), purpose=PURPOSE_LOGIN
        )
        return MfaChallengeRequiredResponse(
            mfa_required=True,
            mfa_challenge_token=challenge_token,
            mfa_method=loaded.mfa_method or "totp",
            expires_in=expires_in,
        )

    if user_needs_mfa_enrollment(loaded):
        challenge_token, expires_in = create_mfa_challenge(
            user_id=str(loaded.id), purpose=PURPOSE_ENROLLMENT
        )
        return MfaEnrollmentRequiredResponse(
            mfa_enrollment_required=True,
            mfa_enrollment_challenge_token=challenge_token,
            expires_in=expires_in,
        )

    return _issue_authenticated_session(db=db, user=loaded, request=request, response=response)


@router.post("/logout", response_model=MessageResponse)
def logout(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    ih_session: str | None = Cookie(default=None),
) -> MessageResponse:
    """Always clear the session cookie — even when the JWT/session is already invalid.

    Never 401 before clearing: stale cookies must be removable so the shell can recover.
    """
    settings = get_settings()
    token = extract_token(
        authorization,
        ih_session or request.cookies.get(settings.auth_cookie_name),
    )
    user: User | None = None
    did_mutate = False

    if token:
        decoded = decode_access_token(token)
        if decoded is not None:
            user_id, jti = decoded
            if jti:
                auth_session = session_service.get_active_session(db, jti)
                if auth_session is not None:
                    session_service.revoke_session(db, auth_session, reason="logout")
                    did_mutate = True
            user = load_user_with_roles(db, user_id)

    # Clear cookie before any audit/commit so clients always get Set-Cookie deletion.
    _clear_auth_cookie(response, settings)

    if user is not None:
        record_auth_event(
            "auth.logout",
            db=db,
            actor=user,
            actor_id=user.id,
            target_id=user.id,
            request=request,
            commit=True,
        )
    elif did_mutate:
        db.commit()

    return MessageResponse(message="Logged out")


@router.get("/me", response_model=CurrentUserResponse)
def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return serialize_current_user(user)


@router.get("/csrf", response_model=CsrfTokenResponse)
def csrf_token(user: User = Depends(get_current_user)) -> CsrfTokenResponse:
    binding = csrf_binding_key(user_id=str(user.id), jti=getattr(user, "_session_jti", None))
    return CsrfTokenResponse(csrf_token=issue_csrf_token(binding))


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

    try:
        validate_new_password(
            payload.new_password,
            email=user.email,
            full_name=user.full_name,
            user_id=user.id,
        )
    except PasswordPolicyError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=GENERIC_PASSWORD_ERROR,
        )

    user.hashed_password = hash_password(payload.new_password)
    user.updated_at = datetime.now(UTC)
    current_jti = getattr(user, "_session_jti", None)
    session_service.revoke_user_sessions(
        db,
        user.id,
        reason="password_changed",
        except_jti=current_jti,
    )
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


@router.post("/mfa/enroll", response_model=MfaEnrollStartResponse)
def mfa_enroll_start(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MfaEnrollStartResponse:
    result = start_enrollment(db, current_user)
    db.commit()
    return MfaEnrollStartResponse.model_validate(result)


@router.post("/mfa/enroll/confirm", response_model=MfaEnrollConfirmResponse)
def mfa_enroll_confirm(
    payload: MfaEnrollConfirmRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MfaEnrollConfirmResponse:
    client_ip = resolve_client_ip(request)
    user_key = str(current_user.id)
    enforce_mfa_confirm_rate_limit(ip=client_ip, user_id=user_key)
    try:
        result = confirm_enrollment(db, current_user, payload.code)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            record_failed_mfa_confirm(ip=client_ip, user_id=user_key)
        raise
    clear_mfa_confirm_failures(user_id=user_key)
    db.commit()
    return MfaEnrollConfirmResponse.model_validate(result)


def _enrollment_challenge_user(
    *,
    db: Session,
    challenge_token: str,
    ip: str,
) -> tuple[User, object]:
    challenge = peek_mfa_challenge(challenge_token)
    identity = challenge.user_id if challenge is not None else hash_challenge_token(challenge_token)
    enforce_mfa_verify_rate_limit(ip=ip, identity=identity)
    if challenge is None or challenge.purpose != PURPOSE_ENROLLMENT:
        _reject_enrollment_challenge(ip=ip, identity=identity)
    try:
        user_id = UUID(challenge.user_id)
    except (ValueError, AttributeError):
        _reject_enrollment_challenge(ip=ip, identity=identity)
    user = load_user_with_roles(db, user_id)
    if (
        user is None
        or user.archived_at is not None
        or user.status not in {UserStatus.ACTIVE, UserStatus.INVITED}
        or not user_needs_mfa_enrollment(user)
    ):
        _reject_enrollment_challenge(ip=ip, identity=identity)
    return user, challenge


@router.post("/mfa/enroll/required", response_model=MfaEnrollStartResponse)
def mfa_enroll_required_start(
    payload: MfaEnrollmentChallengeRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> MfaEnrollStartResponse:
    client_ip = resolve_client_ip(request)
    user, _challenge = _enrollment_challenge_user(
        db=db, challenge_token=payload.challenge_token, ip=client_ip
    )
    result = start_enrollment(db, user)
    db.commit()
    return MfaEnrollStartResponse.model_validate(result)


@router.post("/mfa/enroll/required/confirm", response_model=MfaEnrollmentCompleteResponse)
def mfa_enroll_required_confirm(
    payload: MfaEnrollmentConfirmRequiredRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> MfaEnrollmentCompleteResponse:
    client_ip = resolve_client_ip(request)
    user, _challenge = _enrollment_challenge_user(
        db=db, challenge_token=payload.challenge_token, ip=client_ip
    )
    user_key = str(user.id)
    enforce_mfa_confirm_rate_limit(ip=client_ip, user_id=user_key)
    try:
        result = confirm_enrollment(db, user, payload.code)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_400_BAD_REQUEST:
            record_failed_mfa_confirm(ip=client_ip, user_id=user_key)
        raise
    consumed = consume_mfa_challenge(payload.challenge_token)
    if consumed is None or consumed.user_id != str(user.id) or consumed.purpose != PURPOSE_ENROLLMENT:
        _reject_enrollment_challenge(ip=client_ip, identity=user_key)
    clear_mfa_confirm_failures(user_id=user_key)
    current = _issue_authenticated_session(db=db, user=user, request=request, response=response)
    return MfaEnrollmentCompleteResponse(
        mfa_enabled=bool(result["mfa_enabled"]),
        mfa_method=str(result["mfa_method"]),
        recovery_codes=list(result["recovery_codes"]),
        user=current,
    )


@router.post("/mfa/verify", response_model=CurrentUserResponse)
def mfa_verify(
    payload: MfaVerifyRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    client_ip = resolve_client_ip(request)
    challenge = peek_mfa_challenge(payload.challenge_token)
    identity = challenge.user_id if challenge is not None else hash_challenge_token(payload.challenge_token)
    enforce_mfa_verify_rate_limit(ip=client_ip, identity=identity)
    if challenge is None or challenge.purpose != PURPOSE_LOGIN:
        _reject_mfa_verify(ip=client_ip, identity=identity)

    try:
        user_id = UUID(challenge.user_id)
    except (ValueError, AttributeError):
        _reject_mfa_verify(ip=client_ip, identity=identity)

    user = load_user_with_roles(db, user_id)
    if (
        user is None
        or user.archived_at is not None
        or user.status not in {UserStatus.ACTIVE, UserStatus.INVITED}
        or not user_requires_mfa_challenge(user)
    ):
        _reject_mfa_verify(ip=client_ip, identity=identity)

    verified = verify_login_mfa_code(db, user, payload.code)
    if verified is False:
        _reject_mfa_verify(ip=client_ip, identity=identity)

    consumed = consume_mfa_challenge(payload.challenge_token)
    if consumed is None or consumed.user_id != str(user.id) or consumed.purpose != PURPOSE_LOGIN:
        _reject_mfa_verify(ip=client_ip, identity=identity)

    if verified is not True:
        mark_recovery_code_used(verified)
    clear_mfa_verify_failures(identity=identity)
    return _issue_authenticated_session(db=db, user=user, request=request, response=response)
