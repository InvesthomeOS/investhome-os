"""Security Center service — dashboard, SSO/MFA status, compliance, health (P11)."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.feature_flags import get_feature_flags
from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityAction, ActivityLog
from investhome_api.models.security_enterprise import (
    ApiKeyStatus,
    FeatureFlagOverride,
    PlatformApiKey,
    SecurityIncident,
    TemporaryPermissionGrant,
)
from investhome_api.models.user_auth import User
from investhome_api.services import session_service
from investhome_api.services.company_foundation_service import supported_options


SSO_PROVIDERS = (
    ("google", "SSO", "Google Workspace", ("SSO_GOOGLE_CLIENT_ID", "SSO_GOOGLE_CLIENT_SECRET")),
    ("microsoft", "SSO", "Microsoft Entra ID", ("SSO_MICROSOFT_CLIENT_ID", "SSO_MICROSOFT_CLIENT_SECRET")),
    ("okta", "SSO", "Okta", ("SSO_OKTA_DOMAIN", "SSO_OKTA_CLIENT_ID", "SSO_OKTA_CLIENT_SECRET")),
    ("azure_ad", "SSO", "Azure AD", ("SSO_AZURE_TENANT_ID", "SSO_AZURE_CLIENT_ID", "SSO_AZURE_CLIENT_SECRET")),
    ("saml", "SSO", "SAML 2.0", ("SSO_SAML_METADATA_URL", "SSO_SAML_ENTITY_ID")),
)

MFA_METHODS = (
    ("authenticator", "MFA", "Authenticator app (TOTP)", ("MFA_TOTP_ISSUER",)),
    ("email", "MFA", "Email one-time codes", ("MFA_EMAIL_ENABLED", "SMTP_HOST")),
    ("recovery", "MFA", "Recovery codes", ("MFA_RECOVERY_ENABLED",)),
)

SECRET_PROVIDERS = (
    ("env_file", "secrets", "Environment / .env", ()),
    ("vault", "secrets", "HashiCorp Vault", ("VAULT_ADDR", "VAULT_TOKEN")),
    ("aws_secrets", "secrets", "AWS Secrets Manager", ("AWS_SECRETS_REGION", "AWS_ACCESS_KEY_ID")),
    ("azure_keyvault", "secrets", "Azure Key Vault", ("AZURE_KEYVAULT_URL", "AZURE_CLIENT_ID")),
)


def _env_status(env_keys: tuple[str, ...], *, disabled_flag: str | None = None) -> tuple[str, bool]:
    if disabled_flag and os.getenv(disabled_flag, "").lower() in {"1", "true", "yes"}:
        return "disabled", False
    if not env_keys:
        return "configured", True
    values = [os.getenv(k) for k in env_keys]
    if all(v for v in values):
        return "configured", True
    if any(v for v in values):
        return "invalid", False
    return "missing", False


def list_sso_providers() -> list[dict]:
    items = []
    for pid, category, label, keys in SSO_PROVIDERS:
        status, configured = _env_status(keys)
        items.append(
            {
                "provider_id": pid,
                "category": category,
                "label": label,
                "status": status,
                "configured": configured,
                "message": "Adapter ready; connect credentials via environment."
                if status == "missing"
                else None,
                "env_keys": list(keys),
            }
        )
    return items


def list_mfa_methods() -> list[dict]:
    items = []
    for pid, category, label, keys in MFA_METHODS:
        if pid == "authenticator":
            # Issuer alone does not mean TOTP is wired — honest not_connected until adapter ships.
            status, configured = "not_connected", False
            message = "TOTP adapter prepared; enrollment not yet enforced."
        elif pid == "email":
            status, configured = _env_status(("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"))
            if status == "configured":
                status, configured = "not_connected", False
                message = "SMTP present; email MFA challenge adapter not wired."
            else:
                message = "Configure SMTP to enable email MFA later."
        else:
            status, configured = "not_connected", False
            message = "Recovery code adapter prepared; generation UI not connected."
        items.append(
            {
                "provider_id": pid,
                "category": category,
                "label": label,
                "status": status,
                "configured": configured,
                "message": message,
                "env_keys": list(keys),
            }
        )
    return items


def list_secret_providers() -> list[dict]:
    items = []
    for pid, category, label, keys in SECRET_PROVIDERS:
        if pid == "env_file":
            status, configured = "configured", True
            message = "Local development uses environment variables. Secret values are never exposed."
        else:
            status, configured = _env_status(keys)
            message = "Provider adapter status only — values are never returned."
        items.append(
            {
                "provider_id": pid,
                "category": category,
                "label": label,
                "status": status,
                "configured": configured,
                "message": message,
                "env_keys": list(keys),
            }
        )
    # Also surface AI/storage secrets without values
    settings = get_settings()
    items.append(
        {
            "provider_id": "ai_api_key",
            "category": "secrets",
            "label": "External AI API key",
            "status": "configured" if settings.ai_api_key else "missing",
            "configured": bool(settings.ai_api_key),
            "message": "Configured" if settings.ai_api_key else "AI_API_KEY not set",
            "env_keys": ["AI_API_KEY"],
        }
    )
    return items


def mfa_policy(db: Session) -> dict:
    total = db.scalar(select(func.count()).select_from(User).where(User.archived_at.is_(None))) or 0
    enabled = (
        db.scalar(
            select(func.count()).select_from(User).where(User.archived_at.is_(None), User.mfa_enabled.is_(True))
        )
        or 0
    )
    enforcement = os.getenv("MFA_ENFORCEMENT", "optional").lower()
    if enforcement not in {"optional", "required", "disabled"}:
        enforcement = "optional"
    return {
        "enforcement": enforcement,
        "methods": list_mfa_methods(),
        "recovery_codes_available": False,
        "adoption": {
            "key": "mfa_adoption",
            "label": "MFA adoption",
            "value": round((enabled / total) * 100, 1) if total else 0,
            "available": True,
            "note": f"{enabled}/{total} users with MFA enabled",
        },
    }


def security_dashboard(db: Session) -> dict:
    now = datetime.now(UTC)
    since = now - timedelta(days=7)

    from investhome_api.models.security_enterprise import AuthSession

    failed_logins = (
        db.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.action == ActivityAction.LOGIN_FAILED,
                ActivityLog.created_at >= since,
            )
        )
        or 0
    )
    active_sessions = (
        db.scalar(
            select(func.count()).select_from(AuthSession).where(AuthSession.revoked_at.is_(None))
        )
        or 0
    )
    permission_changes = (
        db.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(
                ActivityLog.action == ActivityAction.PERMISSION_CHANGED,
                ActivityLog.created_at >= since,
            )
        )
        or 0
    )
    expired_keys = (
        db.scalar(
            select(func.count())
            .select_from(PlatformApiKey)
            .where(
                PlatformApiKey.status == ApiKeyStatus.ACTIVE.value,
                PlatformApiKey.expires_at.is_not(None),
                PlatformApiKey.expires_at < now,
            )
        )
        or 0
    )
    mfa = mfa_policy(db)
    open_incidents = (
        db.scalar(
            select(func.count())
            .select_from(SecurityIncident)
            .where(SecurityIncident.status.in_(["open", "investigating"]))
        )
        or 0
    )

    kpis = [
        {
            "key": "failed_logins_7d",
            "label": "Failed logins (7d)",
            "value": failed_logins,
            "available": True,
            "note": None,
        },
        {
            "key": "active_sessions",
            "label": "Active sessions",
            "value": active_sessions,
            "available": True,
            "note": None,
        },
        {
            "key": "permission_changes_7d",
            "label": "Permission changes (7d)",
            "value": permission_changes,
            "available": True,
            "note": None,
        },
        {
            "key": "expired_api_keys",
            "label": "Expired API keys",
            "value": expired_keys,
            "available": True,
            "note": None,
        },
        mfa["adoption"],
        {
            "key": "open_incidents",
            "label": "Open security incidents",
            "value": open_incidents,
            "available": True,
            "note": None,
        },
        {
            "key": "sso_ready",
            "label": "SSO providers configured",
            "value": sum(1 for p in list_sso_providers() if p["configured"]),
            "available": True,
            "note": "Env-driven adapters; login flow not wired until credentials exist.",
        },
        {
            "key": "backup_health",
            "label": "Backup health",
            "value": None,
            "available": False,
            "note": "Backup provider not connected — see System → Backup.",
        },
    ]

    alerts: list[dict] = []
    if failed_logins >= 20:
        alerts.append(
            {
                "severity": "high",
                "title": "Elevated failed login volume",
                "detail": f"{failed_logins} failed logins in the last 7 days.",
            }
        )
    if expired_keys:
        alerts.append(
            {
                "severity": "medium",
                "title": "Expired API keys still marked active",
                "detail": f"{expired_keys} key(s) past expiration.",
            }
        )
    if open_incidents:
        alerts.append(
            {
                "severity": "medium",
                "title": "Open security incidents",
                "detail": f"{open_incidents} incident(s) need attention.",
            }
        )
    sso_missing = [p for p in list_sso_providers() if not p["configured"]]
    if len(sso_missing) == len(list_sso_providers()):
        alerts.append(
            {
                "severity": "low",
                "title": "SSO not configured",
                "detail": "All SSO adapters report Missing — password login only.",
            }
        )

    return {"kpis": kpis, "alerts": alerts, "generated_at": now}


def compliance_overview(db: Session) -> dict:
    legal_holds: list[dict] = []
    retention: list[dict] = []
    try:
        from investhome_api.models.company_workspace_document import (  # type: ignore
            CompanyDocumentLegalHold,
            CompanyDocumentRetentionPolicy,
        )

        holds = db.scalars(select(CompanyDocumentLegalHold).limit(50)).all()
        legal_holds = [
            {
                "id": str(h.id),
                "status": "active" if getattr(h, "is_active", True) else "released",
                "document_id": str(getattr(h, "workspace_document_id", "")),
                "reason": getattr(h, "reason", None),
            }
            for h in holds
        ]
        policies = db.scalars(select(CompanyDocumentRetentionPolicy).limit(50)).all()
        retention = [
            {
                "id": str(p.id),
                "name": getattr(p, "name", "Policy"),
                "retention_days": getattr(p, "retention_days", None),
                "status": "active" if getattr(p, "is_active", True) else "inactive",
            }
            for p in policies
        ]
    except Exception:
        retention = [
            {
                "id": "docs-default",
                "name": "Document workspace soft-delete retention (~30 days)",
                "status": "foundation",
            }
        ]
        legal_holds = []

    return {
        "policies": [
            {"id": "acceptable-use", "title": "Acceptable use", "status": "draft_placeholder"},
            {"id": "access-control", "title": "Access control", "status": "enforced_via_rbac"},
            {"id": "data-retention", "title": "Data retention", "status": "foundation"},
        ],
        "retention": retention,
        "consent": [
            {
                "id": "marketing-consent",
                "title": "Marketing consent",
                "status": "linked",
                "note": "Marketing consent service exists; admin policy UI is foundational.",
            }
        ],
        "legal_holds": legal_holds,
        "privacy": [
            {"id": "pii-masking", "title": "PII masking in activity logs", "status": "enforced"},
            {"id": "gdpr-export", "title": "Subject data export", "status": "planned"},
        ],
        "knowledge_retention_link": "/dashboard/documents",
        "notes": [
            "Retention purge jobs are not automated yet.",
            "Legal hold APIs from Knowledge Hub are surfaced when present.",
            "Audit exports are available from Admin → Audit.",
        ],
    }


def data_governance() -> dict:
    return {
        "classifications": [
            {"level": "public", "description": "Shareable outside the organization"},
            {"level": "internal", "description": "Default operational data"},
            {"level": "confidential", "description": "Requires documents:view_confidential"},
            {"level": "highly_confidential", "description": "Requires documents:view_highly_confidential"},
        ],
        "sensitive_fields": [
            {"field": "password / hashed_password", "masking": "never returned"},
            {"field": "api_key / secret", "masking": "redacted in activity + settings"},
            {"field": "AI_API_KEY", "masking": "status only"},
            {"field": "SSO client secrets", "masking": "env-only, never API-exposed"},
        ],
        "masking": [
            {
                "surface": "Activity logs",
                "status": "active",
                "note": "activity_config sensitive field redaction",
            },
            {
                "surface": "Admin UI",
                "status": "placeholder",
                "note": "UI masks secret-looking fields; backend must still refuse.",
            },
        ],
        "notes": [
            "Frontend permission checks are advisory — API enforce via require_permission.",
            "Risk scores are not computed yet; do not display fake risk values.",
        ],
    }


def backup_status() -> dict:
    last = os.getenv("BACKUP_LAST_SUCCESS_AT")
    provider = os.getenv("BACKUP_PROVIDER", "none")
    if provider in {"", "none", "disabled"}:
        return {
            "status": "not_configured",
            "last_backup_at": None,
            "health": "unavailable",
            "provider": "none",
            "message": "No backup provider connected. Set BACKUP_PROVIDER and related env vars.",
            "env_keys": ["BACKUP_PROVIDER", "BACKUP_LAST_SUCCESS_AT", "BACKUP_HEALTH_URL"],
        }
    health = os.getenv("BACKUP_HEALTH", "unknown")
    parsed = None
    if last:
        try:
            parsed = datetime.fromisoformat(last.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
    return {
        "status": "configured" if health != "unknown" else "invalid",
        "last_backup_at": parsed,
        "health": health,
        "provider": provider,
        "message": "Status from environment — no live probe in this release."
        if health == "unknown"
        else f"Provider {provider} reports {health}.",
        "env_keys": ["BACKUP_PROVIDER", "BACKUP_LAST_SUCCESS_AT", "BACKUP_HEALTH", "BACKUP_HEALTH_URL"],
    }


COMMON_TIMEZONES = [
    "UTC",
    "Europe/Istanbul",
    "Europe/London",
    "Europe/Berlin",
    "America/New_York",
    "America/Los_Angeles",
    "Asia/Dubai",
    "Asia/Singapore",
]


def system_config(db: Session) -> dict:
    opts = supported_options()
    return {
        "currencies": opts.get("currencies", []),
        "languages": opts.get("languages", []),
        "timezones": COMMON_TIMEZONES,
        "feature_flags": list_feature_flags(db),
        "brand_settings_path": "/dashboard/settings?tab=brand",
        "organization_path": "/dashboard/settings?tab=organization",
    }


def list_feature_flags(db: Session) -> list[dict]:
    flags = get_feature_flags()
    env_map = {
        "company_foundation": flags.company_foundation,
        "document_intelligence": flags.document_intelligence,
        "drawing_intelligence": flags.drawing_intelligence,
        "universal_search": flags.universal_search,
        "notification_center": flags.notification_center,
        "activity_log": flags.activity_log,
        "executive_dashboard": flags.executive_dashboard,
        "n8n_automation": flags.n8n_automation,
        "external_ai": flags.external_ai,
        "external_storage": flags.external_storage,
        "platform_admin": flags.platform_admin,
        "contractor_portal": flags.contractor_portal,
        "partner_workspace": flags.partner_workspace,
        "vendor_portal": flags.vendor_portal,
        "agent_crm_lite": flags.agent_crm_lite,
        "mga_insurance": flags.mga_insurance,
    }
    overrides = {
        o.flag_key: o for o in db.scalars(select(FeatureFlagOverride)).all()
    }
    items = []
    for key, env_default in env_map.items():
        override = overrides.get(key)
        if override:
            items.append(
                {
                    "key": key,
                    "enabled": override.enabled,
                    "source": "override",
                    "rollout_percent": override.rollout_percent,
                    "target_roles": list(override.target_roles_json or []),
                    "notes": override.notes,
                    "env_default": env_default,
                }
            )
        else:
            items.append(
                {
                    "key": key,
                    "enabled": env_default,
                    "source": "env",
                    "rollout_percent": 100,
                    "target_roles": [],
                    "notes": None,
                    "env_default": env_default,
                }
            )
    return items


def upsert_feature_flag(
    db: Session,
    *,
    flag_key: str,
    enabled: bool,
    rollout_percent: int,
    target_roles: list[str],
    notes: str | None,
    actor_id: UUID | None,
) -> dict:
    known = {f["key"] for f in list_feature_flags(db)}
    # Allow upsert even if only env-known keys
    from investhome_api.config.feature_flags import FeatureFlags

    allowed = set(FeatureFlags.model_fields.keys())
    if flag_key not in allowed and flag_key not in known:
        raise ValueError(f"Unknown feature flag: {flag_key}")

    row = db.scalar(select(FeatureFlagOverride).where(FeatureFlagOverride.flag_key == flag_key))
    if row is None:
        row = FeatureFlagOverride(id=uuid4(), flag_key=flag_key)
        db.add(row)
    row.enabled = enabled
    row.rollout_percent = rollout_percent
    row.target_roles_json = target_roles
    row.notes = notes
    row.updated_by_user_id = actor_id
    row.updated_at = datetime.now(UTC)
    db.flush()
    return {
        "key": row.flag_key,
        "enabled": row.enabled,
        "source": "override",
        "rollout_percent": row.rollout_percent,
        "target_roles": list(row.target_roles_json or []),
        "notes": row.notes,
        "env_default": None,
    }


def system_health(db: Session) -> dict:
    settings = get_settings()
    components = []

    # API
    components.append(
        {
            "id": "api",
            "label": "API",
            "status": "healthy",
            "detail": f"{settings.app_name} {settings.app_version}",
            "link": "/health",
        }
    )

    # Database — if we can query, it's up
    try:
        db.execute(select(1))
        components.append(
            {
                "id": "database",
                "label": "Database",
                "status": "healthy",
                "detail": "Query probe succeeded",
                "link": None,
            }
        )
    except Exception as exc:  # noqa: BLE001
        components.append(
            {
                "id": "database",
                "label": "Database",
                "status": "unavailable",
                "detail": str(exc)[:200],
                "link": None,
            }
        )

    # Redis / queue
    redis_url = settings.redis_url
    components.append(
        {
            "id": "queue",
            "label": "Queue / Redis",
            "status": "not_configured" if not redis_url else "degraded",
            "detail": "Redis URL present; live ping not performed in Security Center."
            if redis_url
            else "REDIS_URL not set",
            "link": "/dashboard/automation",
        }
    )

    # Workers / automation
    try:
        from investhome_api.services import automation_center_service as auto

        health = auto.get_system_health(db)
        status = health.get("status") or health.get("overall") or "degraded"
        components.append(
            {
                "id": "automation",
                "label": "Automation / workers",
                "status": "healthy" if status in {"healthy", "ok"} else "degraded",
                "detail": str(status),
                "link": "/dashboard/automation",
            }
        )
    except Exception:
        components.append(
            {
                "id": "automation",
                "label": "Automation / workers",
                "status": "not_configured",
                "detail": "Automation Center health unavailable",
                "link": "/dashboard/automation",
            }
        )

    components.append(
        {
            "id": "storage",
            "label": "Document storage",
            "status": "healthy" if settings.document_storage_provider == "local" else "not_configured",
            "detail": f"Provider: {settings.document_storage_provider}",
            "link": None,
        }
    )
    components.append(
        {
            "id": "search",
            "label": "Search",
            "status": "healthy" if get_feature_flags().universal_search else "disabled",
            "detail": "Universal search feature flag",
            "link": None,
        }
    )
    components.append(
        {
            "id": "ai",
            "label": "AI providers",
            "status": "healthy" if settings.ai_provider == "local" else (
                "configured" if settings.ai_api_key else "not_configured"
            ),
            "detail": f"Provider: {settings.ai_provider}",
            "link": None,
        }
    )

    statuses = {c["status"] for c in components}
    if "unavailable" in statuses:
        overall = "unavailable"
    elif "degraded" in statuses or "not_configured" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {"components": components, "overall": overall}


def list_api_keys(db: Session) -> list[PlatformApiKey]:
    return list(db.scalars(select(PlatformApiKey).order_by(PlatformApiKey.created_at.desc())).all())


def create_api_key(
    db: Session,
    *,
    name: str,
    scopes: list[str],
    expires_at: datetime | None,
    actor_id: UUID | None,
) -> tuple[PlatformApiKey, str]:
    secret, prefix, key_hash = session_service.generate_api_key_secret()
    row = PlatformApiKey(
        id=uuid4(),
        created_by_user_id=actor_id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes_json=scopes,
        status=ApiKeyStatus.ACTIVE.value,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return row, secret


def rotate_api_key(db: Session, key: PlatformApiKey) -> tuple[PlatformApiKey, str]:
    secret, prefix, key_hash = session_service.generate_api_key_secret()
    key.key_prefix = prefix
    key.key_hash = key_hash
    key.status = ApiKeyStatus.ACTIVE.value
    key.revoked_at = None
    key.updated_at = datetime.now(UTC)
    db.flush()
    return key, secret


def revoke_api_key(db: Session, key: PlatformApiKey) -> PlatformApiKey:
    key.status = ApiKeyStatus.REVOKED.value
    key.revoked_at = datetime.now(UTC)
    key.updated_at = datetime.now(UTC)
    db.flush()
    return key


def list_temporary_grants(db: Session, *, active_only: bool = True) -> list[TemporaryPermissionGrant]:
    query = select(TemporaryPermissionGrant).order_by(TemporaryPermissionGrant.created_at.desc())
    if active_only:
        now = datetime.now(UTC)
        query = query.where(
            TemporaryPermissionGrant.revoked_at.is_(None),
            TemporaryPermissionGrant.expires_at > now,
        )
    return list(db.scalars(query.limit(200)).all())


def create_temporary_grant(
    db: Session,
    *,
    user_id: UUID,
    resource: str,
    action: str,
    reason: str | None,
    expires_at: datetime,
    actor_id: UUID | None,
) -> TemporaryPermissionGrant:
    grant = TemporaryPermissionGrant(
        id=uuid4(),
        user_id=user_id,
        granted_by_user_id=actor_id,
        resource=resource,
        action=action,
        reason=reason,
        expires_at=expires_at,
    )
    db.add(grant)
    db.flush()
    return grant


def revoke_temporary_grant(db: Session, grant: TemporaryPermissionGrant) -> TemporaryPermissionGrant:
    grant.revoked_at = datetime.now(UTC)
    db.flush()
    return grant


def user_has_temporary_permission(db: Session, user_id: UUID, resource: str, action: str) -> bool:
    now = datetime.now(UTC)
    row = db.scalar(
        select(TemporaryPermissionGrant).where(
            TemporaryPermissionGrant.user_id == user_id,
            TemporaryPermissionGrant.resource == resource,
            TemporaryPermissionGrant.action == action,
            TemporaryPermissionGrant.revoked_at.is_(None),
            TemporaryPermissionGrant.starts_at <= now,
            TemporaryPermissionGrant.expires_at > now,
        )
    )
    return row is not None


def list_incidents(db: Session) -> list[SecurityIncident]:
    return list(
        db.scalars(select(SecurityIncident).order_by(SecurityIncident.created_at.desc()).limit(100)).all()
    )


def create_incident(
    db: Session,
    *,
    title: str,
    severity: str,
    category: str,
    summary: str | None,
    actor_id: UUID | None,
) -> SecurityIncident:
    row = SecurityIncident(
        id=uuid4(),
        title=title,
        severity=severity,
        category=category,
        summary=summary,
        reported_by_user_id=actor_id,
        status="open",
    )
    db.add(row)
    db.flush()
    return row


def export_audit(db: Session, *, from_date: datetime | None, to_date: datetime | None, actions: list[str]) -> dict:
    query = select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(1000)
    if from_date:
        query = query.where(ActivityLog.created_at >= from_date)
    if to_date:
        query = query.where(ActivityLog.created_at <= to_date)
    if actions:
        try:
            action_enums = [ActivityAction(a) for a in actions]
            query = query.where(ActivityLog.action.in_(action_enums))
        except ValueError:
            pass
    rows = db.scalars(query).all()
    items = [
        {
            "id": str(r.id),
            "action": r.action.value if hasattr(r.action, "value") else str(r.action),
            "entity_type": r.entity_type.value if hasattr(r.entity_type, "value") else str(r.entity_type),
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "description_key": r.description_key,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "actor_id": str(r.actor_user_id) if r.actor_user_id else None,
        }
        for r in rows
    ]
    return {
        "exported_at": datetime.now(UTC),
        "total": len(items),
        "items": items,
        "note": "Export capped at 1000 events. Sensitive metadata already redacted at write time.",
    }
