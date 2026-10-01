"""Security Center API routes — Product Polish P11."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user, require_permission
from investhome_api.core.request_context import get_request_id
from investhome_api.db.session import get_db
from investhome_api.models.security_enterprise import AuthSession, PlatformApiKey, TemporaryPermissionGrant
from investhome_api.models.user_auth import User
from investhome_api.schemas.security_center import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyItem,
    ApiKeyListResponse,
    ApiKeyRotateResponse,
    AuditExportRequest,
    AuditExportResponse,
    AuthSessionItem,
    AuthSessionListResponse,
    BackupStatusResponse,
    ComplianceOverviewResponse,
    DataGovernanceResponse,
    FeatureFlagItem,
    FeatureFlagListResponse,
    FeatureFlagUpdateRequest,
    MessageResponse,
    MfaPolicyResponse,
    ProviderStatusItem,
    ProviderStatusListResponse,
    SecurityDashboardResponse,
    SecurityIncidentCreateRequest,
    SecurityIncidentItem,
    SecurityIncidentListResponse,
    SecurityKpiItem,
    SecuritySignalItem,
    SecuritySignalListResponse,
    SystemConfigResponse,
    SystemHealthComponent,
    SystemHealthResponse,
    TemporaryGrantCreateRequest,
    TemporaryGrantItem,
    TemporaryGrantListResponse,
    UserSecurityActionsResponse,
)
from investhome_api.services import security_center_service as service
from investhome_api.services import session_service
from investhome_api.services.audit_service import record_auth_event
from investhome_api.services.auth_service import hash_password
from investhome_api.services.password_policy import generate_temporary_password
from investhome_api.services.mfa_admin import reset_user_mfa

router = APIRouter(prefix="/security", tags=["security-center"])


def _session_item(row: AuthSession, users: dict[UUID, User], current_jti: str | None) -> AuthSessionItem:
    user = users.get(row.user_id)
    return AuthSessionItem(
        id=row.id,
        user_id=row.user_id,
        user_email=user.email if user else None,
        user_name=user.full_name if user else None,
        ip_address=row.ip_address,
        user_agent=row.user_agent,
        device_label=row.device_label,
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        is_current=bool(current_jti and row.token_jti == current_jti),
    )


def _api_key_item(row: PlatformApiKey) -> ApiKeyItem:
    return ApiKeyItem(
        id=row.id,
        name=row.name,
        key_prefix=row.key_prefix,
        scopes=list(row.scopes_json or []),
        status=row.status,
        expires_at=row.expires_at,
        last_used_at=row.last_used_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        created_by_user_id=row.created_by_user_id,
    )


@router.get("/dashboard", response_model=SecurityDashboardResponse)
def security_dashboard(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> SecurityDashboardResponse:
    data = service.security_dashboard(db)
    return SecurityDashboardResponse(
        kpis=[SecurityKpiItem(**k) for k in data["kpis"]],
        alerts=data["alerts"],
        signals=[SecuritySignalItem(**item) for item in data.get("signals") or []],
        generated_at=data["generated_at"],
    )


@router.get("/signals", response_model=SecuritySignalListResponse)
def security_signals(
    _user: User = Depends(require_permission("security", "view")),
) -> SecuritySignalListResponse:
    from investhome_api.services.security_monitoring import list_active_signals

    items = list_active_signals()
    return SecuritySignalListResponse(
        items=[SecuritySignalItem(**item) for item in items],
        total=len(items),
    )


@router.get("/sessions", response_model=AuthSessionListResponse)
def list_sessions(
    user_id: UUID | None = None,
    include_revoked: bool = False,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "view")),
) -> AuthSessionListResponse:
    rows = session_service.list_sessions(db, user_id=user_id, include_revoked=include_revoked)
    user_ids = {r.user_id for r in rows}
    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    } if user_ids else {}
    current_jti = getattr(actor, "_session_jti", None)
    return AuthSessionListResponse(
        items=[_session_item(r, users, current_jti) for r in rows],
        total=len(rows),
    )


@router.post("/sessions/{session_id}/terminate", response_model=MessageResponse)
def terminate_session(
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> MessageResponse:
    row = db.get(AuthSession, session_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    session_service.revoke_session(db, row, reason="admin_terminate")
    record_auth_event(
        "security.session_terminated",
        db=db,
        actor=actor,
        target_id=row.user_id,
        metadata={"session_id": str(row.id)},
        request=request,
        commit=True,
    )
    return MessageResponse(message="Session terminated")


@router.post("/sessions/terminate-all", response_model=UserSecurityActionsResponse)
def terminate_all_sessions(
    request: Request,
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> UserSecurityActionsResponse:
    target = user_id or actor.id
    count = session_service.revoke_user_sessions(db, target, reason="admin_terminate_all")
    record_auth_event(
        "security.sessions_terminated",
        db=db,
        actor=actor,
        target_id=target,
        metadata={"count": count},
        request=request,
        commit=True,
    )
    return UserSecurityActionsResponse(message="Sessions terminated", sessions_revoked=count)


@router.get("/sso", response_model=ProviderStatusListResponse)
def sso_providers(
    _user: User = Depends(require_permission("security", "view")),
) -> ProviderStatusListResponse:
    return ProviderStatusListResponse(items=[ProviderStatusItem(**p) for p in service.list_sso_providers()])


@router.get("/mfa", response_model=MfaPolicyResponse)
def mfa_policy(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> MfaPolicyResponse:
    data = service.mfa_policy(db)
    return MfaPolicyResponse(
        enforcement=data["enforcement"],
        methods=[ProviderStatusItem(**m) for m in data["methods"]],
        recovery_codes_available=data["recovery_codes_available"],
        adoption=SecurityKpiItem(**data["adoption"]),
    )


@router.get("/secrets", response_model=ProviderStatusListResponse)
def secret_providers(
    _user: User = Depends(require_permission("security", "view")),
) -> ProviderStatusListResponse:
    return ProviderStatusListResponse(items=[ProviderStatusItem(**p) for p in service.list_secret_providers()])


@router.get("/api-keys", response_model=ApiKeyListResponse)
def list_api_keys(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> ApiKeyListResponse:
    rows = service.list_api_keys(db)
    return ApiKeyListResponse(items=[_api_key_item(r) for r in rows], total=len(rows))


@router.post("/api-keys", response_model=ApiKeyCreateResponse, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: ApiKeyCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> ApiKeyCreateResponse:
    row, secret = service.create_api_key(
        db,
        name=payload.name,
        scopes=payload.scopes,
        expires_at=payload.expires_at,
        actor_id=actor.id,
    )
    record_auth_event(
        "security.api_key_created",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"key_id": str(row.id), "name": row.name, "prefix": row.key_prefix},
        request=request,
    )
    db.commit()
    return ApiKeyCreateResponse(key=_api_key_item(row), secret=secret)


@router.post("/api-keys/{key_id}/rotate", response_model=ApiKeyRotateResponse)
def rotate_api_key(
    key_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> ApiKeyRotateResponse:
    row = db.get(PlatformApiKey, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    row, secret = service.rotate_api_key(db, row)
    record_auth_event(
        "security.api_key_rotated",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"key_id": str(row.id), "prefix": row.key_prefix},
        request=request,
        commit=True,
    )
    return ApiKeyRotateResponse(key=_api_key_item(row), secret=secret)


@router.post("/api-keys/{key_id}/revoke", response_model=ApiKeyItem)
def revoke_api_key(
    key_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> ApiKeyItem:
    row = db.get(PlatformApiKey, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    row = service.revoke_api_key(db, row)
    record_auth_event(
        "security.api_key_revoked",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"key_id": str(row.id)},
        request=request,
        commit=True,
    )
    return _api_key_item(row)


@router.get("/temporary-grants", response_model=TemporaryGrantListResponse)
def list_temp_grants(
    active_only: bool = True,
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("roles", "view")),
) -> TemporaryGrantListResponse:
    rows = service.list_temporary_grants(db, active_only=active_only)
    return TemporaryGrantListResponse(
        items=[
            TemporaryGrantItem(
                id=r.id,
                user_id=r.user_id,
                resource=r.resource,
                action=r.action,
                reason=r.reason,
                starts_at=r.starts_at,
                expires_at=r.expires_at,
                revoked_at=r.revoked_at,
                granted_by_user_id=r.granted_by_user_id,
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.post("/temporary-grants", response_model=TemporaryGrantItem, status_code=status.HTTP_201_CREATED)
def create_temp_grant(
    payload: TemporaryGrantCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("roles", "manage")),
) -> TemporaryGrantItem:
    if payload.expires_at <= datetime.now(UTC):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="expires_at must be in the future")
    grant = service.create_temporary_grant(
        db,
        user_id=payload.user_id,
        resource=payload.resource,
        action=payload.action,
        reason=payload.reason,
        expires_at=payload.expires_at,
        actor_id=actor.id,
    )
    record_auth_event(
        "security.temp_grant_created",
        db=db,
        actor=actor,
        target_id=payload.user_id,
        metadata={"resource": payload.resource, "action": payload.action},
        request=request,
        commit=True,
    )
    return TemporaryGrantItem(
        id=grant.id,
        user_id=grant.user_id,
        resource=grant.resource,
        action=grant.action,
        reason=grant.reason,
        starts_at=grant.starts_at,
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
        granted_by_user_id=grant.granted_by_user_id,
    )


@router.post("/temporary-grants/{grant_id}/revoke", response_model=TemporaryGrantItem)
def revoke_temp_grant(
    grant_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("roles", "manage")),
) -> TemporaryGrantItem:
    grant = db.get(TemporaryPermissionGrant, grant_id)
    if grant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grant not found")
    grant = service.revoke_temporary_grant(db, grant)
    record_auth_event(
        "security.temp_grant_revoked",
        db=db,
        actor=actor,
        target_id=grant.user_id,
        metadata={"grant_id": str(grant.id)},
        request=request,
        commit=True,
    )
    return TemporaryGrantItem(
        id=grant.id,
        user_id=grant.user_id,
        resource=grant.resource,
        action=grant.action,
        reason=grant.reason,
        starts_at=grant.starts_at,
        expires_at=grant.expires_at,
        revoked_at=grant.revoked_at,
        granted_by_user_id=grant.granted_by_user_id,
    )


@router.get("/feature-flags", response_model=FeatureFlagListResponse)
def feature_flags(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("settings", "view")),
) -> FeatureFlagListResponse:
    return FeatureFlagListResponse(items=[FeatureFlagItem(**f) for f in service.list_feature_flags(db)])


@router.put("/feature-flags/{flag_key}", response_model=FeatureFlagItem)
def update_feature_flag(
    flag_key: str,
    payload: FeatureFlagUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("settings", "update")),
) -> FeatureFlagItem:
    try:
        item = service.upsert_feature_flag(
            db,
            flag_key=flag_key,
            enabled=payload.enabled,
            rollout_percent=payload.rollout_percent,
            target_roles=payload.target_roles,
            notes=payload.notes,
            actor_id=actor.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_auth_event(
        "security.feature_flag_updated",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"flag_key": flag_key, "enabled": payload.enabled},
        request=request,
        commit=True,
    )
    return FeatureFlagItem(**item)


@router.get("/compliance", response_model=ComplianceOverviewResponse)
def compliance(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> ComplianceOverviewResponse:
    return ComplianceOverviewResponse(**service.compliance_overview(db))


@router.get("/data-governance", response_model=DataGovernanceResponse)
def data_governance(
    _user: User = Depends(require_permission("security", "view")),
) -> DataGovernanceResponse:
    return DataGovernanceResponse(**service.data_governance())


@router.get("/backup", response_model=BackupStatusResponse)
def backup(
    _user: User = Depends(require_permission("security", "view")),
) -> BackupStatusResponse:
    return BackupStatusResponse(**service.backup_status())


@router.get("/system-config", response_model=SystemConfigResponse)
def system_config(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("settings", "view")),
) -> SystemConfigResponse:
    data = service.system_config(db)
    return SystemConfigResponse(
        currencies=data["currencies"],
        languages=data["languages"],
        timezones=data["timezones"],
        feature_flags=[FeatureFlagItem(**f) for f in data["feature_flags"]],
        brand_settings_path=data["brand_settings_path"],
        organization_path=data["organization_path"],
    )


@router.get("/health", response_model=SystemHealthResponse)
def system_health(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> SystemHealthResponse:
    data = service.system_health(db)
    return SystemHealthResponse(
        components=[SystemHealthComponent(**c) for c in data["components"]],
        overall=data["overall"],
    )


@router.get("/incidents", response_model=SecurityIncidentListResponse)
def list_incidents(
    db: Session = Depends(get_db),
    _user: User = Depends(require_permission("security", "view")),
) -> SecurityIncidentListResponse:
    rows = service.list_incidents(db)
    return SecurityIncidentListResponse(
        items=[
            SecurityIncidentItem(
                id=r.id,
                title=r.title,
                severity=r.severity,
                status=r.status,
                category=r.category,
                summary=r.summary,
                created_at=r.created_at,
                updated_at=r.updated_at,
                resolved_at=r.resolved_at,
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.post("/incidents", response_model=SecurityIncidentItem, status_code=status.HTTP_201_CREATED)
def create_incident(
    payload: SecurityIncidentCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> SecurityIncidentItem:
    row = service.create_incident(
        db,
        title=payload.title,
        severity=payload.severity,
        category=payload.category,
        summary=payload.summary,
        actor_id=actor.id,
    )
    record_auth_event(
        "security.incident_created",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"incident_id": str(row.id), "severity": row.severity},
        request=request,
        commit=True,
    )
    return SecurityIncidentItem(
        id=row.id,
        title=row.title,
        severity=row.severity,
        status=row.status,
        category=row.category,
        summary=row.summary,
        created_at=row.created_at,
        updated_at=row.updated_at,
        resolved_at=row.resolved_at,
    )


@router.post("/audit/export", response_model=AuditExportResponse)
def audit_export(
    payload: AuditExportRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("activity", "view")),
) -> AuditExportResponse:
    data = service.export_audit(
        db,
        from_date=payload.from_date,
        to_date=payload.to_date,
        actions=payload.actions,
    )
    record_auth_event(
        "security.audit_exported",
        db=db,
        actor=actor,
        target_id=actor.id,
        metadata={"total": data["total"]},
        request=request,
        commit=True,
    )
    return AuditExportResponse(**data)


@router.get("/audit/categories")
def audit_categories(
    _user: User = Depends(require_permission("activity", "view")),
) -> dict:
    return {
        "categories": [
            {"id": "auth", "actions": ["login", "logout", "login_failed", "password_changed"]},
            {"id": "permissions", "actions": ["permission_changed", "role_assigned", "role_removed"]},
            {"id": "users", "actions": ["invited", "activated", "deactivated", "updated"]},
            {"id": "exports", "actions": ["exported"]},
            {"id": "approvals", "actions": ["approved", "rejected"]},
            {"id": "config", "actions": ["updated", "created", "deleted"]},
        ]
    }


# --- User security actions (also under /users via include in users router) ---

users_security_router = APIRouter(prefix="/users", tags=["users-security"])


@users_security_router.post("/{user_id}/force-logout", response_model=UserSecurityActionsResponse)
def force_logout_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users", "manage")),
) -> UserSecurityActionsResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    count = session_service.revoke_user_sessions(db, user_id, reason="force_logout")
    record_auth_event(
        "security.force_logout",
        db=db,
        actor=actor,
        target_id=user_id,
        metadata={"sessions_revoked": count},
        request=request,
        commit=True,
    )
    return UserSecurityActionsResponse(message="User sessions revoked", sessions_revoked=count)


@users_security_router.post("/{user_id}/reset-password", response_model=MessageResponse)
def reset_password_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users", "manage")),
) -> MessageResponse:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    # Temporary password — operator must communicate out-of-band; never return in response.
    temp = generate_temporary_password()
    user.hashed_password = hash_password(temp)
    user.updated_at = datetime.now(UTC)
    session_service.revoke_user_sessions(db, user_id, reason="password_reset")
    record_auth_event(
        "security.password_reset",
        db=db,
        actor=actor,
        target_id=user_id,
        metadata={"sessions_revoked": True},
        request=request,
        commit=True,
    )
    return MessageResponse(
        message="Password reset. Temporary credential must be delivered out-of-band; it is not returned by the API."
    )


@users_security_router.post("/{user_id}/suspend", response_model=MessageResponse)
def suspend_user(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users", "manage")),
) -> MessageResponse:
    from investhome_api.models.user_auth import UserStatus

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if actor.id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot suspend your own account")
    user.status = UserStatus.SUSPENDED
    user.updated_at = datetime.now(UTC)
    session_service.revoke_user_sessions(db, user_id, reason="suspended")
    record_auth_event(
        "security.user_suspended",
        db=db,
        actor=actor,
        target_id=user_id,
        request=request,
        commit=True,
    )
    return MessageResponse(message="User suspended and sessions revoked")


@users_security_router.post("/{user_id}/mfa/reset", response_model=UserSecurityActionsResponse)
def reset_user_mfa_endpoint(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("security", "manage")),
) -> UserSecurityActionsResponse:
    user = db.get(User, user_id)
    if user is None or user.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    count = reset_user_mfa(db, user)
    record_auth_event(
        "security.mfa_reset",
        db=db,
        actor=actor,
        actor_id=actor.id,
        target_id=user.id,
        metadata={
            "action": "mfa_reset",
            "actor_user_id": str(actor.id),
            "target_user_id": str(user.id),
            "sessions_revoked": count,
            "request_id": get_request_id(),
        },
        request=request,
        commit=True,
    )
    return UserSecurityActionsResponse(
        message="MFA reset. User must sign in again with password.",
        sessions_revoked=count,
    )


def uuid4_hex() -> str:
    from uuid import uuid4

    return uuid4().hex
