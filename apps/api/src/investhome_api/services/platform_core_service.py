"""G15A Platform Core service — modules, flags, entitlements, webhooks, integrations."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.feature_flags import FeatureFlags, get_feature_flags
from investhome_api.config.settings import get_settings
from investhome_api.models.platform_core import (
    EntitlementEffect,
    IntegrationStatus,
    ModuleLifecycleStatus,
    PlatformBrandingConfig,
    PlatformEntitlement,
    PlatformExternalAccessAudit,
    PlatformExternalUserType,
    PlatformIntegration,
    PlatformModule,
    PlatformWebhookDelivery,
    PlatformWebhookSubscription,
    WebhookDeliveryStatus,
)
from investhome_api.models.security_enterprise import FeatureFlagOverride, PlatformApiKey
from investhome_api.models.user_auth import User
from investhome_api.services import webhook_signing
from investhome_api.services.notification_gateway import get_notification_gateway
from investhome_api.services.platform_catalog import (
    API_SCOPE_CATALOG,
    ARCHITECTURE_AUDIT,
    FORBIDDEN_SCOPES,
    INTEGRATION_SEED,
    MODULE_SEED,
    deterministic_rollout,
    validate_dependency_update,
)
from investhome_api.services.session_service import generate_api_key_secret, hash_api_key
from investhome_api.services import security_center_service as sec_service

EXTERNAL_TYPE_SEED: list[dict] = [
    {
        "code": "contractor",
        "name_en": "Contractor",
        "name_tr": "Yüklenici",
        "description_en": "Project-scoped access; daily logs; NO full budgets",
        "description_tr": "Proje kapsamlı erişim; günlük kayıtlar; TAM bütçe YOK",
        "isolation_rules_json": {
            "scope": "assigned_projects",
            "deny_resources": ["project_budgets", "finance", "full_cost_breakdown"],
            "allow_resources": ["daily_logs", "assigned_tasks", "project_documents_shared"],
        },
        "default_scopes_json": ["projects:read_assigned", "daily_logs:write", "tasks:read_assigned"],
        "can_see_budgets": False,
    },
    {
        "code": "investor",
        "name_en": "Investor",
        "name_tr": "Yatırımcı",
        "description_en": "Existing portal isolation (G9)",
        "description_tr": "Mevcut portal izolasyonu (G9)",
        "isolation_rules_json": {"scope": "investor_holdings"},
        "default_scopes_json": ["portal:read"],
        "can_see_budgets": False,
    },
    {
        "code": "partner",
        "name_en": "Partner",
        "name_tr": "İş Ortağı",
        "description_en": "Planned — G15C",
        "description_tr": "Planlandı — G15C",
        "isolation_rules_json": {"scope": "partner_deals"},
        "default_scopes_json": [],
        "can_see_budgets": False,
        "enabled": False,
    },
    {
        "code": "vendor",
        "name_en": "Vendor",
        "name_tr": "Tedarikçi",
        "description_en": "Planned — G15D",
        "description_tr": "Planlandı — G15D",
        "isolation_rules_json": {"scope": "vendor_pos"},
        "default_scopes_json": [],
        "can_see_budgets": False,
        "enabled": False,
    },
    {
        "code": "agent",
        "name_en": "Sales Agent",
        "name_tr": "Satış Acentası",
        "description_en": "Planned — G15E",
        "description_tr": "Planlandı — G15E",
        "isolation_rules_json": {"scope": "agent_leads"},
        "default_scopes_json": [],
        "can_see_budgets": False,
        "enabled": False,
    },
]

ENTITLEMENT_SEED: list[dict] = [
    {
        "code": "ent.platform.admin",
        "name_en": "Platform Admin Access",
        "name_tr": "Platform Yönetim Erişimi",
        "module_code": "platform_admin",
        "capability": "platform.admin",
        "effect": EntitlementEffect.ALLOW.value,
        "target_roles_json": ["super_admin"],
        "enabled": True,
    },
    {
        "code": "ent.contractor.portal",
        "name_en": "Contractor Portal Access",
        "name_tr": "Yüklenici Portalı Erişimi",
        "module_code": "contractor_portal",
        "capability": "contractor.portal",
        "effect": EntitlementEffect.ALLOW.value,
        "target_external_types_json": ["contractor"],
        "target_roles_json": ["super_admin", "construction", "operations"],
        "enabled": True,
        "notes": "Pilot — requires module enable + flag",
    },
    {
        "code": "ent.contractor.deny_budgets",
        "name_en": "Deny Contractor Budget Access",
        "name_tr": "Yüklenici Bütçe Erişimini Reddet",
        "module_code": "contractor_portal",
        "capability": "project_budgets.view",
        "effect": EntitlementEffect.DENY.value,
        "target_external_types_json": ["contractor"],
        "enabled": True,
        "notes": "Hard deny — contractors must never see full project budgets",
    },
    {
        "code": "ent.mga.blocked",
        "name_en": "MGA Module Blocked",
        "name_tr": "MGA Modülü Engellendi",
        "module_code": "mga_insurance",
        "capability": "mga.access",
        "effect": EntitlementEffect.DENY.value,
        "enabled": True,
        "notes": "Regulatory BLOCKED — do not enable",
    },
]


def ensure_platform_seed(db: Session) -> None:
    """Idempotent seed for registry tables."""
    existing_modules = {m.code for m in db.scalars(select(PlatformModule)).all()}
    for item in MODULE_SEED:
        if item["code"] in existing_modules:
            continue
        enabled = item.get("enabled", False)
        db.add(
            PlatformModule(
                id=uuid4(),
                code=item["code"],
                name_en=item["name_en"],
                name_tr=item["name_tr"],
                description_en=item.get("description_en"),
                description_tr=item.get("description_tr"),
                lifecycle_status=item["lifecycle_status"],
                enabled=enabled,
                env_enabled=True,
                kill_switch=item.get("kill_switch", False),
                depends_on_json=item.get("depends_on_json", []),
                feature_flag_key=item.get("feature_flag_key"),
                route_prefix=item.get("route_prefix"),
                admin_only=item.get("admin_only", False),
                pilot_phase=item.get("pilot_phase"),
                block_reason=item.get("block_reason"),
                sort_order=item.get("sort_order", 100),
                activated_at=datetime.now(UTC) if enabled else None,
                key_locked=bool(enabled),
            )
        )

    existing_int = {i.code for i in db.scalars(select(PlatformIntegration)).all()}
    for item in INTEGRATION_SEED:
        if item["code"] in existing_int:
            continue
        db.add(
            PlatformIntegration(
                id=uuid4(),
                code=item["code"],
                name_en=item["name_en"],
                name_tr=item["name_tr"],
                category=item.get("category", "general"),
                status=item["status"],
                description_en=item.get("description_en"),
                description_tr=item.get("description_tr"),
                env_keys_json=item.get("env_keys_json"),
                block_reason=item.get("block_reason"),
                sort_order=item.get("sort_order", 100),
                configured=False,
            )
        )

    existing_ext = {e.code for e in db.scalars(select(PlatformExternalUserType)).all()}
    for item in EXTERNAL_TYPE_SEED:
        if item["code"] in existing_ext:
            continue
        db.add(
            PlatformExternalUserType(
                id=uuid4(),
                code=item["code"],
                name_en=item["name_en"],
                name_tr=item["name_tr"],
                description_en=item.get("description_en"),
                description_tr=item.get("description_tr"),
                isolation_rules_json=item.get("isolation_rules_json", {}),
                default_scopes_json=item.get("default_scopes_json", []),
                can_see_budgets=item.get("can_see_budgets", False),
                enabled=item.get("enabled", True),
            )
        )

    existing_ent = {e.code for e in db.scalars(select(PlatformEntitlement)).all()}
    for item in ENTITLEMENT_SEED:
        if item["code"] in existing_ent:
            continue
        db.add(
            PlatformEntitlement(
                id=uuid4(),
                code=item["code"],
                name_en=item["name_en"],
                name_tr=item["name_tr"],
                description_en=item.get("description_en"),
                description_tr=item.get("description_tr"),
                module_code=item.get("module_code"),
                capability=item["capability"],
                effect=item.get("effect", EntitlementEffect.ALLOW.value),
                target_roles_json=item.get("target_roles_json"),
                target_company_ids_json=item.get("target_company_ids_json"),
                target_user_ids_json=item.get("target_user_ids_json"),
                target_external_types_json=item.get("target_external_types_json"),
                enabled=item.get("enabled", True),
                notes=item.get("notes"),
            )
        )

    branding = db.scalar(select(PlatformBrandingConfig).where(PlatformBrandingConfig.code == "default"))
    if branding is None:
        db.add(
            PlatformBrandingConfig(
                id=uuid4(),
                code="default",
                display_name_en="InvestHome",
                display_name_tr="InvestHome",
                primary_color="#1B3A4B",
                accent_color="#C4A35A",
                support_email="support@investhome.demo",
            )
        )
    db.flush()


def _module_effective(mod: PlatformModule) -> dict:
    effective_enabled = bool(
        mod.enabled
        and mod.env_enabled
        and not mod.kill_switch
        and mod.lifecycle_status
        not in {ModuleLifecycleStatus.BLOCKED.value, ModuleLifecycleStatus.DISABLED.value}
    )
    if mod.lifecycle_status == ModuleLifecycleStatus.BLOCKED.value:
        effective_enabled = False
    health = "healthy" if effective_enabled else ("blocked" if mod.lifecycle_status == "blocked" else "inactive")
    if mod.kill_switch:
        health = "kill_switch"
    return {
        "id": str(mod.id),
        "code": mod.code,
        "name_en": mod.name_en,
        "name_tr": mod.name_tr,
        "description_en": mod.description_en,
        "description_tr": mod.description_tr,
        "lifecycle_status": mod.lifecycle_status,
        "enabled": mod.enabled,
        "env_enabled": mod.env_enabled,
        "kill_switch": mod.kill_switch,
        "effective_enabled": effective_enabled,
        "depends_on": list(mod.depends_on_json or []),
        "feature_flag_key": mod.feature_flag_key,
        "route_prefix": mod.route_prefix,
        "admin_only": mod.admin_only,
        "pilot_phase": mod.pilot_phase,
        "block_reason": mod.block_reason,
        "sort_order": mod.sort_order,
        "activated_at": mod.activated_at.isoformat() if getattr(mod, "activated_at", None) else None,
        "key_locked": bool(getattr(mod, "key_locked", False)),
        "key_immutable": bool(getattr(mod, "key_locked", False) or getattr(mod, "activated_at", None)),
        "health": health,
        "updated_at": mod.updated_at.isoformat() if mod.updated_at else None,
    }


def list_modules(db: Session) -> list[dict]:
    ensure_platform_seed(db)
    rows = db.scalars(select(PlatformModule).order_by(PlatformModule.sort_order)).all()
    return [_module_effective(m) for m in rows]


def get_module(db: Session, code: str) -> dict | None:
    ensure_platform_seed(db)
    row = db.scalar(select(PlatformModule).where(PlatformModule.code == code))
    return _module_effective(row) if row else None


def is_module_effectively_enabled(db: Session, code: str) -> bool:
    mod = get_module(db, code)
    return bool(mod and mod["effective_enabled"])


def update_module(
    db: Session,
    *,
    code: str,
    enabled: bool | None = None,
    env_enabled: bool | None = None,
    kill_switch: bool | None = None,
    depends_on: list[str] | None = None,
    rename_code: str | None = None,
    actor_id: UUID | None = None,
) -> dict:
    ensure_platform_seed(db)
    row = db.scalar(select(PlatformModule).where(PlatformModule.code == code))
    if row is None:
        raise ValueError(f"Unknown module: {code}")
    if rename_code and rename_code != code:
        if row.key_locked or row.activated_at is not None or row.enabled:
            raise ValueError(
                f"Module key '{code}' is immutable after activation (key_locked={row.key_locked})"
            )
        row.code = rename_code
    if row.lifecycle_status == ModuleLifecycleStatus.BLOCKED.value and enabled is True:
        raise ValueError(f"Module {code} is BLOCKED and cannot be enabled: {row.block_reason}")
    if depends_on is not None:
        all_deps = {
            m.code: list(m.depends_on_json or [])
            for m in db.scalars(select(PlatformModule)).all()
        }
        validate_dependency_update(row.code, depends_on, all_deps)
        row.depends_on_json = depends_on
    if enabled is not None:
        row.enabled = enabled
        if enabled and row.activated_at is None:
            row.activated_at = datetime.now(UTC)
            row.key_locked = True
    if env_enabled is not None:
        row.env_enabled = env_enabled
    if kill_switch is not None:
        row.kill_switch = kill_switch
    row.updated_by_user_id = actor_id
    row.updated_at = datetime.now(UTC)
    db.flush()
    return _module_effective(row)


def module_dependency_map(db: Session) -> dict:
    modules = list_modules(db)
    edges = []
    for m in modules:
        for dep in m["depends_on"]:
            edges.append({"from": m["code"], "to": dep})
    from investhome_api.services.platform_catalog import detect_circular_dependencies

    cycle = detect_circular_dependencies([(e["from"], e["to"]) for e in edges])
    return {
        "modules": modules,
        "edges": edges,
        "has_cycle": bool(cycle),
        "cycle": cycle,
        "visualization": [{"id": m["code"], "depends_on": m["depends_on"], "health": m["health"]} for m in modules],
    }


def validate_module_deps_preview(db: Session, code: str, depends_on: list[str]) -> dict:
    ensure_platform_seed(db)
    all_deps = {
        m.code: list(m.depends_on_json or [])
        for m in db.scalars(select(PlatformModule)).all()
    }
    try:
        validate_dependency_update(code, depends_on, all_deps)
        return {"ok": True, "depends_on": depends_on}
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}


def list_feature_flags_platform(db: Session) -> list[dict]:
    """Extended flag view: env + override + kill_switch + company/role/user targeting."""
    from investhome_api.services.security_center_service import list_feature_flags

    base = list_feature_flags(db)
    # Also expose platform-specific keys from FeatureFlags if present
    flags = get_feature_flags()
    known = {f["key"] for f in base}
    for key in FeatureFlags.model_fields:
        if key not in known:
            base.append(
                {
                    "key": key,
                    "enabled": bool(getattr(flags, key, False)),
                    "source": "env",
                    "rollout_percent": 100,
                    "target_roles": [],
                    "notes": None,
                    "env_default": bool(getattr(flags, key, False)),
                }
            )

    overrides = {o.flag_key: o for o in db.scalars(select(FeatureFlagOverride)).all()}
    enriched = []
    for item in base:
        o = overrides.get(item["key"])
        kill = bool(getattr(o, "kill_switch", False)) if o else False
        target_companies = list(getattr(o, "target_company_ids_json", None) or []) if o else []
        target_users = list(getattr(o, "target_user_ids_json", None) or []) if o else []
        env_scope = getattr(o, "environment_scope", None) if o else None
        effective = False if kill else bool(item["enabled"])
        enriched.append(
            {
                **item,
                "kill_switch": kill,
                "effective_enabled": effective,
                "target_companies": target_companies,
                "target_users": target_users,
                "environment_scope": env_scope or "all",
            }
        )
    return enriched


def upsert_feature_flag_platform(
    db: Session,
    *,
    flag_key: str,
    enabled: bool,
    rollout_percent: int = 100,
    target_roles: list[str] | None = None,
    target_companies: list[str] | None = None,
    target_users: list[str] | None = None,
    kill_switch: bool = False,
    environment_scope: str = "all",
    notes: str | None = None,
    actor_id: UUID | None = None,
) -> dict:
    from investhome_api.services.security_center_service import upsert_feature_flag

    allowed = set(FeatureFlags.model_fields.keys())
    if flag_key not in allowed:
        # Allow dynamic platform keys by creating override anyway for known platform flags
        platform_keys = {
            "platform_admin",
            "contractor_portal",
            "partner_workspace",
            "vendor_portal",
            "agent_crm_lite",
            "mga_insurance",
        }
        if flag_key not in platform_keys:
            raise ValueError(f"Unknown feature flag: {flag_key}")

    # Ensure override row exists
    try:
        upsert_feature_flag(
            db,
            flag_key=flag_key,
            enabled=False if kill_switch else enabled,
            rollout_percent=rollout_percent,
            target_roles=target_roles or [],
            notes=notes,
            actor_id=actor_id,
        )
    except ValueError:
        # Create override for platform-only keys
        row = db.scalar(select(FeatureFlagOverride).where(FeatureFlagOverride.flag_key == flag_key))
        if row is None:
            row = FeatureFlagOverride(id=uuid4(), flag_key=flag_key)
            db.add(row)
        row.enabled = False if kill_switch else enabled
        row.rollout_percent = rollout_percent
        row.target_roles_json = target_roles or []
        row.notes = notes
        row.updated_by_user_id = actor_id
        row.updated_at = datetime.now(UTC)

    row = db.scalar(select(FeatureFlagOverride).where(FeatureFlagOverride.flag_key == flag_key))
    if row is None:
        raise ValueError("Failed to upsert feature flag")
    if hasattr(row, "kill_switch"):
        row.kill_switch = kill_switch
    if hasattr(row, "target_company_ids_json"):
        row.target_company_ids_json = target_companies or []
    if hasattr(row, "target_user_ids_json"):
        row.target_user_ids_json = target_users or []
    if hasattr(row, "environment_scope"):
        row.environment_scope = environment_scope
    row.enabled = False if kill_switch else enabled
    db.flush()

    return {
        "key": flag_key,
        "enabled": row.enabled,
        "kill_switch": bool(getattr(row, "kill_switch", False)),
        "effective_enabled": False if kill_switch else bool(row.enabled),
        "source": "override",
        "rollout_percent": row.rollout_percent,
        "target_roles": list(row.target_roles_json or []),
        "target_companies": list(getattr(row, "target_company_ids_json", None) or []),
        "target_users": list(getattr(row, "target_user_ids_json", None) or []),
        "environment_scope": getattr(row, "environment_scope", None) or "all",
        "notes": row.notes,
    }


def evaluate_flag_for_user(
    db: Session,
    flag_key: str,
    *,
    user: User | None = None,
    company_id: str | None = None,
) -> bool:
    flags = {f["key"]: f for f in list_feature_flags_platform(db)}
    item = flags.get(flag_key)
    if item is None:
        return False
    if item.get("kill_switch"):
        return False
    if not item.get("effective_enabled"):
        return False
    env_scope = item.get("environment_scope") or "all"
    if env_scope != "all":
        settings = get_settings()
        if settings.environment.lower() != env_scope.lower():
            return False
    roles = item.get("target_roles") or []
    companies = item.get("target_companies") or []
    users = item.get("target_users") or []
    if roles and user is not None:
        user_roles = {r.code for r in (user.roles or [])} if hasattr(user, "roles") else set()
        # Also check via role relations
        if hasattr(user, "user_roles"):
            user_roles |= {ur.role.code for ur in user.user_roles if ur.role}
        if user_roles and not user_roles.intersection(set(roles)):
            return False
    if companies and company_id and company_id not in companies:
        return False
    if users and user is not None and str(user.id) not in users:
        return False
    return True


def list_entitlements(db: Session) -> list[dict]:
    ensure_platform_seed(db)
    rows = db.scalars(select(PlatformEntitlement).order_by(PlatformEntitlement.code)).all()
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "name_en": r.name_en,
            "name_tr": r.name_tr,
            "description_en": r.description_en,
            "description_tr": r.description_tr,
            "module_code": r.module_code,
            "capability": r.capability,
            "effect": r.effect,
            "target_roles": list(r.target_roles_json or []),
            "target_companies": list(r.target_company_ids_json or []),
            "target_users": list(r.target_user_ids_json or []),
            "target_external_types": list(r.target_external_types_json or []),
            "enabled": r.enabled,
            "notes": r.notes,
        }
        for r in rows
    ]


def check_entitlement(
    db: Session,
    capability: str,
    *,
    role_codes: list[str] | None = None,
    external_type: str | None = None,
    user_id: str | None = None,
    company_id: str | None = None,
) -> dict:
    ensure_platform_seed(db)
    rows = db.scalars(
        select(PlatformEntitlement).where(
            PlatformEntitlement.capability == capability,
            PlatformEntitlement.enabled.is_(True),
        )
    ).all()
    if not rows:
        return {"capability": capability, "allowed": False, "reason": "no_entitlement", "matched": None}

    # DENY wins
    for r in rows:
        if r.effect != EntitlementEffect.DENY.value:
            continue
        if _entitlement_matches(r, role_codes, external_type, user_id, company_id):
            return {
                "capability": capability,
                "allowed": False,
                "reason": "denied",
                "matched": r.code,
                "notes": r.notes,
            }

    for r in rows:
        if r.effect != EntitlementEffect.ALLOW.value:
            continue
        if _entitlement_matches(r, role_codes, external_type, user_id, company_id):
            # Module kill / disabled check
            if r.module_code and not is_module_effectively_enabled(db, r.module_code):
                return {
                    "capability": capability,
                    "allowed": False,
                    "reason": "module_disabled",
                    "matched": r.code,
                    "module_code": r.module_code,
                }
            return {"capability": capability, "allowed": True, "reason": "allowed", "matched": r.code}

    return {"capability": capability, "allowed": False, "reason": "no_matching_allow", "matched": None}


def _entitlement_matches(
    r: PlatformEntitlement,
    role_codes: list[str] | None,
    external_type: str | None,
    user_id: str | None,
    company_id: str | None,
) -> bool:
    roles = list(r.target_roles_json or [])
    ext = list(r.target_external_types_json or [])
    users = list(r.target_user_ids_json or [])
    companies = list(r.target_company_ids_json or [])
    # Empty targeting = applies broadly for that effect
    if not roles and not ext and not users and not companies:
        return True
    if roles and role_codes and set(roles).intersection(role_codes):
        return True
    if ext and external_type and external_type in ext:
        return True
    if users and user_id and user_id in users:
        return True
    if companies and company_id and company_id in companies:
        return True
    return False


def list_external_user_types(db: Session) -> list[dict]:
    ensure_platform_seed(db)
    rows = db.scalars(select(PlatformExternalUserType).order_by(PlatformExternalUserType.code)).all()
    return [
        {
            "id": str(r.id),
            "code": r.code,
            "name_en": r.name_en,
            "name_tr": r.name_tr,
            "description_en": r.description_en,
            "description_tr": r.description_tr,
            "isolation_rules": r.isolation_rules_json or {},
            "default_scopes": list(r.default_scopes_json or []),
            "can_see_budgets": r.can_see_budgets,
            "enabled": r.enabled,
        }
        for r in rows
    ]


def list_api_clients(db: Session) -> list[dict]:
    rows = db.scalars(select(PlatformApiKey).order_by(PlatformApiKey.created_at.desc())).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "key_prefix": r.key_prefix,
            "scopes": list(r.scopes_json or []),
            "status": r.status,
            "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            "last_used_at": r.last_used_at.isoformat() if r.last_used_at else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def list_api_scopes() -> list[dict]:
    return list(API_SCOPE_CATALOG)


def _validate_scopes(scopes: list[str]) -> list[str]:
    allowed = {s["code"] for s in API_SCOPE_CATALOG}
    cleaned: list[str] = []
    for scope in scopes:
        if scope in FORBIDDEN_SCOPES or "*" in scope:
            raise ValueError(f"Wildcard/forbidden scope rejected: {scope}")
        if scope not in allowed:
            raise ValueError(f"Unknown scope (not in catalog): {scope}")
        cleaned.append(scope)
    return cleaned


def create_api_client(
    db: Session,
    *,
    name: str,
    scopes: list[str],
    actor_id: UUID | None,
    expires_at: datetime | None = None,
) -> tuple[dict, str]:
    scopes = _validate_scopes(scopes)
    raw, prefix, key_hash = generate_api_key_secret()
    row = PlatformApiKey(
        id=uuid4(),
        created_by_user_id=actor_id,
        name=name,
        key_prefix=prefix,
        key_hash=key_hash,
        scopes_json=scopes,
        expires_at=expires_at,
    )
    db.add(row)
    db.flush()
    return (
        {
            "id": str(row.id),
            "name": row.name,
            "key_prefix": row.key_prefix,
            "scopes": list(row.scopes_json or []),
            "status": row.status,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "secret_display": "one_time",
        },
        raw,
    )


def rotate_api_client(db: Session, key_id: UUID) -> tuple[dict, str]:
    row = db.get(PlatformApiKey, key_id)
    if row is None:
        raise ValueError("API client not found")
    row, raw = sec_service.rotate_api_key(db, row)
    return (
        {
            "id": str(row.id),
            "name": row.name,
            "key_prefix": row.key_prefix,
            "scopes": list(row.scopes_json or []),
            "status": row.status,
            "secret_display": "one_time",
        },
        raw,
    )


def revoke_api_client(db: Session, key_id: UUID) -> dict:
    row = db.get(PlatformApiKey, key_id)
    if row is None:
        raise ValueError("API client not found")
    row = sec_service.revoke_api_key(db, row)
    return {"id": str(row.id), "status": row.status, "revoked_at": row.revoked_at.isoformat() if row.revoked_at else None}


def api_key_has_scope(db: Session, key_hash: str, required_scope: str) -> bool:
    row = db.scalar(
        select(PlatformApiKey).where(
            PlatformApiKey.key_hash == key_hash,
            PlatformApiKey.status == "active",
        )
    )
    if row is None:
        return False
    if row.expires_at and row.expires_at < datetime.now(UTC):
        return False
    scopes = list(row.scopes_json or [])
    # No wildcards — exact catalog scope only
    return required_scope in scopes


def authenticate_api_key(db: Session, raw_key: str) -> PlatformApiKey | None:
    digest = hash_api_key(raw_key)
    row = db.scalar(
        select(PlatformApiKey).where(
            PlatformApiKey.key_hash == digest,
            PlatformApiKey.status == "active",
        )
    )
    if row is None:
        return None
    if row.expires_at and row.expires_at < datetime.now(UTC):
        return None
    row.last_used_at = datetime.now(UTC)
    db.flush()
    return row


def require_api_scope(db: Session, raw_key: str, required_scope: str) -> dict:
    key = authenticate_api_key(db, raw_key)
    if key is None:
        return {"allowed": False, "reason": "invalid_key"}
    scopes = list(key.scopes_json or [])
    if required_scope in scopes:
        return {"allowed": True, "reason": "ok", "key_id": str(key.id), "scopes": scopes}
    return {
        "allowed": False,
        "reason": "scope_rejected",
        "key_id": str(key.id),
        "scopes": scopes,
        "required_scope": required_scope,
    }


def list_webhooks(db: Session) -> list[dict]:
    rows = db.scalars(
        select(PlatformWebhookSubscription).order_by(PlatformWebhookSubscription.created_at.desc())
    ).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "target_url": r.target_url,
            "secret_prefix": r.secret_prefix,
            "event_types": list(r.event_types_json or []),
            "enabled": r.enabled,
            "max_retries": r.max_retries,
            "last_delivery_at": r.last_delivery_at.isoformat() if r.last_delivery_at else None,
            "last_status": r.last_status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def create_webhook(
    db: Session,
    *,
    name: str,
    target_url: str,
    event_types: list[str],
    actor_id: UUID | None,
) -> tuple[dict, str]:
    raw, prefix, secret_hash = webhook_signing.generate_webhook_secret()
    row = PlatformWebhookSubscription(
        id=uuid4(),
        name=name,
        target_url=target_url,
        secret_hash=secret_hash,
        secret_prefix=prefix,
        event_types_json=event_types,
        created_by_user_id=actor_id,
    )
    db.add(row)
    db.flush()
    return (
        {
            "id": str(row.id),
            "name": row.name,
            "target_url": row.target_url,
            "secret_prefix": row.secret_prefix,
            "event_types": list(row.event_types_json or []),
            "enabled": row.enabled,
        },
        raw,
    )


def enqueue_webhook_delivery(
    db: Session,
    *,
    subscription_id: UUID,
    event_type: str,
    payload: dict,
    signing_secret: str | None = None,
) -> dict:
    """Foundation: create signed delivery record (actual HTTP dispatch may be async later)."""
    sub = db.get(PlatformWebhookSubscription, subscription_id)
    if sub is None:
        raise ValueError("Webhook subscription not found")

    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    # Demo/foundation: if raw secret not available, sign with hash-derived placeholder marker
    secret_for_sign = signing_secret or f"hash:{sub.secret_hash[:16]}"
    signature = webhook_signing.sign_payload(secret_for_sign, body)

    delivery = PlatformWebhookDelivery(
        id=uuid4(),
        subscription_id=subscription_id,
        event_type=event_type,
        payload_json=payload,
        signature_header=signature,
        status=WebhookDeliveryStatus.PENDING.value,
        attempt_count=0,
    )
    db.add(delivery)
    sub.last_status = WebhookDeliveryStatus.PENDING.value
    db.flush()
    return {
        "id": str(delivery.id),
        "subscription_id": str(subscription_id),
        "event_type": event_type,
        "status": delivery.status,
        "signature_header": signature,
        "signature_algorithm": "hmac-sha256",
        "headers": {
            webhook_signing.SIGNATURE_HEADER: signature,
            webhook_signing.TIMESTAMP_HEADER: signature.split(",")[0].replace("t=", ""),
        },
    }


def list_webhook_deliveries(db: Session, limit: int = 50) -> list[dict]:
    rows = db.scalars(
        select(PlatformWebhookDelivery)
        .order_by(PlatformWebhookDelivery.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "subscription_id": str(r.subscription_id),
            "event_type": r.event_type,
            "status": r.status,
            "attempt_count": r.attempt_count,
            "http_status": r.http_status,
            "signature_header": r.signature_header,
            "error_message": r.error_message,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
        }
        for r in rows
    ]


def verify_webhook_signature_demo(secret: str, payload: dict, signature_header: str) -> dict:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ok = webhook_signing.verify_signature(secret, body, signature_header)
    return {"valid": ok, "algorithm": "hmac-sha256"}


def list_integrations(db: Session) -> list[dict]:
    ensure_platform_seed(db)
    rows = db.scalars(select(PlatformIntegration).order_by(PlatformIntegration.sort_order)).all()
    settings = get_settings()
    # Refresh honest status for AI key
    result = []
    for r in rows:
        status = r.status
        configured = r.configured
        if r.code == "openai":
            configured = bool(getattr(settings, "ai_api_key", None))
            if configured and status == IntegrationStatus.NOT_CONNECTED.value:
                status = IntegrationStatus.PARTIAL.value
        if r.code == "n8n":
            flags = get_feature_flags()
            if flags.n8n_automation:
                status = IntegrationStatus.PARTIAL.value
                configured = True
        result.append(
            {
                "id": str(r.id),
                "code": r.code,
                "name_en": r.name_en,
                "name_tr": r.name_tr,
                "category": r.category,
                "status": status,
                "description_en": r.description_en,
                "description_tr": r.description_tr,
                "env_keys": list(r.env_keys_json or []),
                "configured": configured,
                "block_reason": r.block_reason,
                "docs_url": r.docs_url,
            }
        )
    return result


def get_branding(db: Session) -> dict:
    ensure_platform_seed(db)
    row = db.scalar(select(PlatformBrandingConfig).where(PlatformBrandingConfig.code == "default"))
    if row is None:
        raise ValueError("Branding config missing")
    return {
        "id": str(row.id),
        "code": row.code,
        "display_name_en": row.display_name_en,
        "display_name_tr": row.display_name_tr,
        "logo_url": row.logo_url,
        "favicon_url": row.favicon_url,
        "primary_color": row.primary_color,
        "accent_color": row.accent_color,
        "secondary_color": row.secondary_color,
        "support_email": row.support_email,
        "footer_en": row.footer_en,
        "footer_tr": row.footer_tr,
        "allowed_token_keys": list(row.allowed_token_keys_json or []),
        "custom_css_allowed": False,
        "note": "Arbitrary CSS injection is forbidden — only named brand tokens",
        "company_foundation_path": "/dashboard/settings?tab=brand",
    }


def update_branding(
    db: Session,
    *,
    actor_id: UUID | None,
    display_name_en: str | None = None,
    display_name_tr: str | None = None,
    logo_url: str | None = None,
    favicon_url: str | None = None,
    primary_color: str | None = None,
    accent_color: str | None = None,
    secondary_color: str | None = None,
    support_email: str | None = None,
    footer_en: str | None = None,
    footer_tr: str | None = None,
    custom_css: str | None = None,
) -> dict:
    if custom_css is not None and custom_css.strip():
        raise ValueError("Arbitrary CSS injection is forbidden. Use brand color/logo tokens only.")
    ensure_platform_seed(db)
    row = db.scalar(select(PlatformBrandingConfig).where(PlatformBrandingConfig.code == "default"))
    if row is None:
        raise ValueError("Branding config missing")
    if display_name_en is not None:
        row.display_name_en = display_name_en
    if display_name_tr is not None:
        row.display_name_tr = display_name_tr
    if logo_url is not None:
        row.logo_url = logo_url
    if favicon_url is not None:
        row.favicon_url = favicon_url
    if primary_color is not None:
        row.primary_color = primary_color
    if accent_color is not None:
        row.accent_color = accent_color
    if secondary_color is not None:
        row.secondary_color = secondary_color
    if support_email is not None:
        row.support_email = support_email
    if footer_en is not None:
        row.footer_en = footer_en
    if footer_tr is not None:
        row.footer_tr = footer_tr
    row.updated_by_user_id = actor_id
    row.updated_at = datetime.now(UTC)
    db.flush()
    return get_branding(db)


def list_external_access_audit(db: Session, limit: int = 100) -> list[dict]:
    rows = db.scalars(
        select(PlatformExternalAccessAudit)
        .order_by(PlatformExternalAccessAudit.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "actor_user_id": str(r.actor_user_id) if r.actor_user_id else None,
            "external_type": r.external_type,
            "action": r.action,
            "resource": r.resource,
            "resource_id": r.resource_id,
            "project_id": str(r.project_id) if r.project_id else None,
            "outcome": r.outcome,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def record_external_access(
    db: Session,
    *,
    actor_user_id: UUID | None,
    external_type: str | None,
    action: str,
    resource: str,
    outcome: str,
    resource_id: str | None = None,
    project_id: UUID | None = None,
    detail: str | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
) -> dict:
    row = PlatformExternalAccessAudit(
        id=uuid4(),
        actor_user_id=actor_user_id,
        external_type=external_type,
        action=action,
        resource=resource,
        resource_id=resource_id,
        project_id=project_id,
        outcome=outcome,
        detail=detail,
        ip_address=ip_address,
        metadata_json=metadata,
    )
    db.add(row)
    db.flush()
    return {
        "id": str(row.id),
        "outcome": row.outcome,
        "action": row.action,
        "resource": row.resource,
    }


def architecture_audit() -> list[dict]:
    return list(ARCHITECTURE_AUDIT)


def module_health(db: Session) -> dict:
    modules = list_modules(db)
    return {
        "items": [
            {
                "code": m["code"],
                "lifecycle_status": m["lifecycle_status"],
                "effective_enabled": m["effective_enabled"],
                "kill_switch": m["kill_switch"],
                "env_enabled": m["env_enabled"],
                "health": m["health"],
                "depends_on": m["depends_on"],
            }
            for m in modules
        ],
        "summary": {
            "healthy": sum(1 for m in modules if m["health"] == "healthy"),
            "inactive": sum(1 for m in modules if m["health"] == "inactive"),
            "kill_switch": sum(1 for m in modules if m["health"] == "kill_switch"),
            "blocked": sum(1 for m in modules if m["health"] == "blocked"),
        },
    }


def emergency_kill_switches(db: Session) -> dict:
    modules = [m for m in list_modules(db) if m["kill_switch"]]
    flags = [f for f in list_feature_flags_platform(db) if f.get("kill_switch")]
    return {
        "modules": modules,
        "flags": flags,
        "note": "Kill switches force effective disable regardless of env defaults",
    }


def environment_controls(db: Session) -> dict:
    settings = get_settings()
    flags = get_feature_flags()
    return {
        "environment": settings.environment,
        "auth_enabled": settings.auth_enabled,
        "feature_env_defaults": flags.model_dump(),
        "modules_env_gate": [
            {"code": m["code"], "env_enabled": m["env_enabled"], "effective_enabled": m["effective_enabled"]}
            for m in list_modules(db)
        ],
        "note": "Environment-level module controls via env_enabled + FEATURE_* defaults",
    }


def mark_delivery_dead(db: Session, delivery_id: UUID) -> dict:
    row = db.get(PlatformWebhookDelivery, delivery_id)
    if row is None:
        raise ValueError("Delivery not found")
    row.status = WebhookDeliveryStatus.DEAD.value
    row.error_message = row.error_message or "Moved to dead-letter after max retries"
    db.flush()
    return {"id": str(row.id), "status": row.status}


def retry_delivery(db: Session, delivery_id: UUID) -> dict:
    row = db.get(PlatformWebhookDelivery, delivery_id)
    if row is None:
        raise ValueError("Delivery not found")
    row.status = WebhookDeliveryStatus.RETRYING.value
    row.attempt_count = int(row.attempt_count or 0) + 1
    row.next_retry_at = datetime.now(UTC)
    if row.attempt_count >= 5:
        row.status = WebhookDeliveryStatus.DEAD.value
        row.error_message = "Dead-lettered after 5 attempts"
    db.flush()
    return {"id": str(row.id), "status": row.status, "attempt_count": row.attempt_count}


def platform_health(db: Session) -> dict:
    ensure_platform_seed(db)
    settings = get_settings()
    modules = list_modules(db)
    enabled_count = sum(1 for m in modules if m["effective_enabled"])
    blocked = [m for m in modules if m["lifecycle_status"] == ModuleLifecycleStatus.BLOCKED.value]
    gateway = get_notification_gateway()
    api_key_count = db.scalar(select(func.count()).select_from(PlatformApiKey)) or 0
    webhook_count = db.scalar(select(func.count()).select_from(PlatformWebhookSubscription)) or 0
    dead = (
        db.scalar(
            select(func.count())
            .select_from(PlatformWebhookDelivery)
            .where(PlatformWebhookDelivery.status == WebhookDeliveryStatus.DEAD.value)
        )
        or 0
    )
    mh = module_health(db)["summary"]
    return {
        "status": "healthy",
        "environment": settings.environment,
        "modules_total": len(modules),
        "modules_enabled": enabled_count,
        "modules_blocked": len(blocked),
        "module_health": mh,
        "api_clients": api_key_count,
        "webhook_subscriptions": webhook_count,
        "webhook_dead_letter": dead,
        "notification_gateway": gateway.list_providers(),
        "billing": "out_of_scope",
        "mga_status": "blocked",
        "architecture_audit_count": len(ARCHITECTURE_AUDIT),
        "generated_at": datetime.now(UTC).isoformat(),
        "kpis": [
            {"key": "modules_enabled", "label": "Modules enabled", "value": enabled_count, "available": True},
            {"key": "modules_blocked", "label": "Modules blocked", "value": len(blocked), "available": True},
            {"key": "api_clients", "label": "API clients", "value": api_key_count, "available": True},
            {"key": "webhooks", "label": "Webhooks", "value": webhook_count, "available": True},
            {"key": "dead_letter", "label": "Dead-letter", "value": dead, "available": True},
            {"key": "kill_switches", "label": "Kill switches", "value": mh["kill_switch"], "available": True},
        ],
    }


def platform_overview(db: Session) -> dict:
    health = platform_health(db)
    integrations = list_integrations(db)
    return {
        "health": health,
        "modules": list_modules(db),
        "architecture_audit": ARCHITECTURE_AUDIT,
        "integrations_summary": {
            "total": len(integrations),
            "available": sum(1 for i in integrations if i["status"] == "available"),
            "planned": sum(1 for i in integrations if i["status"] == "planned"),
            "blocked": sum(1 for i in integrations if i["status"] == "blocked"),
            "not_connected": sum(1 for i in integrations if i["status"] == "not_connected"),
            "partial": sum(1 for i in integrations if i["status"] == "partial"),
        },
        "roadmap": {
            "G15A": "shipping_platform_core_only",
            "G15B_contractor_pilot": "recommended_after_approval_not_built",
            "G15C_partner": "planned",
            "G15D_vendor": "planned",
            "G15E_agent": "planned",
            "G15F_white_label": "planned",
            "G15G_cms_mobile_assets": "planned",
            "G15H_mga": "blocked_regulatory",
        },
        "recommended_next_pilot": {
            "code": "contractor_portal",
            "phase": "G15B",
            "implemented_in_g15a": False,
            "reason_en": (
                "Recommended first product pilot AFTER G15A approval: lowest regulatory risk, "
                "clear project scoping, reuses tasks/documents/notifications. NOT built in G15A."
            ),
            "reason_tr": (
                "G15A onayından SONRA önerilen ilk ürün pilotu: düşük düzenleyici risk, "
                "net proje kapsamı. G15A'da uygulanmadı."
            ),
        },
    }
