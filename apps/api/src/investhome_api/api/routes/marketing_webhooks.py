"""Marketing webhooks and domains API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import require_permission
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.marketing_landing_conversion import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookResponse,
)
from investhome_api.services.marketing.webhook_service import (
    create_webhook,
    list_deliveries,
    list_webhooks,
    queue_webhook_delivery,
)

router = APIRouter(prefix="/marketing/webhooks", tags=["marketing-webhooks"])
domains_router = APIRouter(prefix="/marketing/domains", tags=["marketing-domains"])


@router.get("", response_model=list[WebhookResponse])
def list_webhooks_route(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_webhooks")),
):
    webhooks = list_webhooks(db)
    return [
        WebhookResponse(
            id=w.id,
            name=w.name,
            url=w.url,
            event_types_json=w.event_types_json,
            is_active=w.is_active,
            form_id=w.form_id,
        )
        for w in webhooks
    ]


@router.post("", response_model=WebhookResponse, status_code=201)
def create_webhook_route(
    payload: WebhookCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_webhooks")),
):
    webhook = create_webhook(db, payload.model_dump())
    db.commit()
    return WebhookResponse(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        event_types_json=webhook.event_types_json,
        is_active=webhook.is_active,
        form_id=webhook.form_id,
    )


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_deliveries_route(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_webhooks")),
):
    deliveries = list_deliveries(db, webhook_id)
    return [
        WebhookDeliveryResponse(
            id=d.id,
            webhook_id=d.webhook_id,
            event_type=d.event_type,
            status=d.status.value if hasattr(d.status, "value") else d.status,
            response_code=d.response_code,
            created_at=d.created_at,
        )
        for d in deliveries
    ]


@router.post("/{webhook_id}/test", response_model=WebhookDeliveryResponse, status_code=201)
def test_webhook_route(
    webhook_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("marketing", "manage_webhooks")),
):
    delivery = queue_webhook_delivery(db, webhook_id, "test", {"test": True})
    db.commit()
    return WebhookDeliveryResponse(
        id=delivery.id,
        webhook_id=delivery.webhook_id,
        event_type=delivery.event_type,
        status=delivery.status.value if hasattr(delivery.status, "value") else delivery.status,
        response_code=delivery.response_code,
        created_at=delivery.created_at,
    )


@domains_router.get("/providers")
def domain_providers_route(
    user: User = Depends(require_permission("marketing", "manage_domains")),
):
    from investhome_api.services.marketing.conversion_service import get_provider_statuses

    return [p for p in get_provider_statuses() if p["provider"] == "hosting"]
