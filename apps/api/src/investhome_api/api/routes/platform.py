"""G15A Platform Core admin API — /platform/* (foundation only, no product pilots)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_any_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.platform_core import (
    ApiClientCreateRequest,
    ApiScopeCheckRequest,
    EntitlementCheckRequest,
    ExternalAccessRecordRequest,
    FeatureFlagPlatformUpdateRequest,
    ModuleDepsPreviewRequest,
    ModuleUpdateRequest,
    WebhookCreateRequest,
    WebhookEnqueueRequest,
    WebhookVerifyRequest,
)
from investhome_api.services import platform_core_service as service
from investhome_api.services.audit_service import record_auth_event
from investhome_api.services.notification_gateway import get_notification_gateway

router = APIRouter(prefix="/platform", tags=["platform-core"])

_platform_view = require_any_permission(("platform", "view"), ("security", "view"))
_platform_manage = require_any_permission(("platform", "manage"), ("security", "manage"))


@router.get("/overview")
def platform_overview(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.platform_overview(db)


@router.get("/health")
def platform_health(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.platform_health(db)


@router.get("/architecture-audit")
def architecture_audit(_user: User = Depends(_platform_view)) -> dict:
    return {"items": service.architecture_audit()}


@router.get("/modules")
def list_modules(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_modules(db)}


@router.get("/modules/dependencies")
def module_dependencies(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.module_dependency_map(db)


@router.get("/modules/health")
def modules_health(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.module_health(db)


@router.post("/modules/{code}/deps-preview")
def module_deps_preview(
    code: str,
    body: ModuleDepsPreviewRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.validate_module_deps_preview(db, code, body.depends_on)


@router.patch("/modules/{code}")
def update_module(
    code: str,
    body: ModuleUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.update_module(
            db,
            code=code,
            enabled=body.enabled,
            env_enabled=body.env_enabled,
            kill_switch=body.kill_switch,
            depends_on=body.depends_on,
            rename_code=body.rename_code,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_auth_event(
        "platform.module_updated",
        db=db,
        actor=user,
        metadata={"module": code, "enabled": body.enabled, "kill_switch": body.kill_switch},
    )
    db.commit()
    return result


@router.get("/feature-flags")
def list_feature_flags(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_feature_flags_platform(db)}


@router.put("/feature-flags/{flag_key}")
def upsert_feature_flag(
    flag_key: str,
    body: FeatureFlagPlatformUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.upsert_feature_flag_platform(
            db,
            flag_key=flag_key,
            enabled=body.enabled,
            rollout_percent=body.rollout_percent,
            target_roles=body.target_roles,
            target_companies=body.target_companies,
            target_users=body.target_users,
            kill_switch=body.kill_switch,
            environment_scope=body.environment_scope,
            notes=body.notes,
            actor_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_auth_event(
        "platform.feature_flag_updated",
        db=db,
        actor=user,
        metadata={"flag_key": flag_key, "enabled": body.enabled, "kill_switch": body.kill_switch},
    )
    db.commit()
    return result


@router.get("/kill-switches")
def kill_switches(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.emergency_kill_switches(db)


@router.get("/environment")
def environment_controls(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.environment_controls(db)


@router.get("/entitlements")
def list_entitlements(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_entitlements(db), "billing": "out_of_scope"}


@router.post("/entitlements/check")
def check_entitlement(
    body: EntitlementCheckRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.check_entitlement(
        db,
        body.capability,
        role_codes=body.role_codes,
        external_type=body.external_type,
        user_id=body.user_id,
        company_id=body.company_id,
    )


@router.get("/external-users")
def list_external_users(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_external_user_types(db)}


@router.get("/api-scopes")
def list_api_scopes(_user: User = Depends(_platform_view)) -> dict:
    return {
        "items": service.list_api_scopes(),
        "forbidden": ["*", "*:*", "admin", "admin:*", "all"],
        "note": "No wildcards — clients must use catalog scopes only",
    }


@router.get("/api-clients")
def list_api_clients(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_api_clients(db)}


@router.post("/api-clients", status_code=status.HTTP_201_CREATED)
def create_api_client(
    body: ApiClientCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        item, raw = service.create_api_client(
            db, name=body.name, scopes=body.scopes, actor_id=user.id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    record_auth_event(
        "platform.api_client_created",
        db=db,
        actor=user,
        metadata={"name": body.name, "key_id": item["id"]},
    )
    db.commit()
    return {**item, "secret": raw, "message": "Store the secret now — it will not be shown again."}


@router.post("/api-clients/{key_id}/rotate")
def rotate_api_client(
    key_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        item, raw = service.rotate_api_client(db, key_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return {**item, "secret": raw, "message": "Rotated — store the new secret now."}


@router.post("/api-clients/{key_id}/revoke")
def revoke_api_client(
    key_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.revoke_api_client(db, key_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/api-clients/check-scope")
def check_api_scope(
    body: ApiScopeCheckRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return service.require_api_scope(db, body.api_key, body.required_scope)


@router.get("/webhooks")
def list_webhooks(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    return {"items": service.list_webhooks(db)}


@router.post("/webhooks", status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    item, raw = service.create_webhook(
        db,
        name=body.name,
        target_url=body.target_url,
        event_types=body.event_types,
        actor_id=user.id,
    )
    db.commit()
    return {**item, "secret": raw, "message": "Store the webhook secret now — shown once."}


@router.get("/webhooks/deliveries")
def list_webhook_deliveries(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    return {"items": service.list_webhook_deliveries(db, limit=limit)}


@router.post("/webhooks/{subscription_id}/enqueue")
def enqueue_webhook(
    subscription_id: UUID,
    body: WebhookEnqueueRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.enqueue_webhook_delivery(
            db,
            subscription_id=subscription_id,
            event_type=body.event_type,
            payload=body.payload,
            signing_secret=body.signing_secret,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    record_auth_event(
        "platform.webhook_enqueued",
        db=db,
        actor=user,
        metadata={"subscription_id": str(subscription_id), "event_type": body.event_type},
    )
    db.commit()
    return result


@router.post("/webhooks/deliveries/{delivery_id}/retry")
def retry_webhook_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.retry_delivery(db, delivery_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/webhooks/deliveries/{delivery_id}/dead-letter")
def dead_letter_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_manage),
) -> dict:
    try:
        result = service.mark_delivery_dead(db, delivery_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    db.commit()
    return result


@router.post("/webhooks/verify-signature")
def verify_webhook_signature(
    body: WebhookVerifyRequest,
    _user: User = Depends(_platform_view),
) -> dict:
    return service.verify_webhook_signature_demo(body.secret, body.payload, body.signature_header)


@router.get("/integrations")
def list_integrations(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
) -> dict:
    items = service.list_integrations(db)
    db.commit()
    return {"items": items}


@router.get("/notification-gateway")
def notification_gateway_status(
    _user: User = Depends(_platform_view),
) -> dict:
    return {"providers": get_notification_gateway().list_providers()}


@router.get("/audit/external-access")
def external_access_audit(
    db: Session = Depends(get_db),
    _user: User = Depends(_platform_view),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    return {"items": service.list_external_access_audit(db, limit=limit)}


@router.post("/audit/external-access")
def record_external_access(
    body: ExternalAccessRecordRequest,
    db: Session = Depends(get_db),
    user: User = Depends(_platform_manage),
) -> dict:
    project_id = UUID(body.project_id) if body.project_id else None
    result = service.record_external_access(
        db,
        actor_user_id=user.id,
        external_type=body.external_type,
        action=body.action,
        resource=body.resource,
        outcome=body.outcome,
        resource_id=body.resource_id,
        project_id=project_id,
        detail=body.detail,
    )
    db.commit()
    return result
