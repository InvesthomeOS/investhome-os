"""Marketing webhooks — delivery tracking, honest not_connected."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_landing_conversion import (
    MarketingWebhook,
    WebhookDelivery,
    WebhookDeliveryStatus,
)


def list_webhooks(db: Session, form_id: UUID | None = None) -> list[MarketingWebhook]:
    query = select(MarketingWebhook)
    if form_id:
        query = query.where(MarketingWebhook.form_id == form_id)
    return list(db.scalars(query.order_by(MarketingWebhook.created_at.desc())).all())


def create_webhook(db: Session, payload: dict) -> MarketingWebhook:
    webhook = MarketingWebhook(**payload)
    db.add(webhook)
    db.flush()
    return webhook


def get_webhook(db: Session, webhook_id: UUID) -> MarketingWebhook:
    webhook = db.get(MarketingWebhook, webhook_id)
    if webhook is None:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return webhook


def queue_webhook_delivery(db: Session, webhook_id: UUID, event_type: str, payload: dict) -> WebhookDelivery:
    """Queue delivery — does not simulate successful HTTP calls."""
    webhook = get_webhook(db, webhook_id)
    if not webhook.is_active:
        raise HTTPException(status_code=422, detail="Webhook is inactive")
    delivery = WebhookDelivery(
        webhook_id=webhook_id,
        event_type=event_type,
        payload_json=payload,
        status=WebhookDeliveryStatus.PENDING,
        error_message="Provider not connected — delivery queued only",
    )
    db.add(delivery)
    db.flush()
    return delivery


def list_deliveries(db: Session, webhook_id: UUID) -> list[WebhookDelivery]:
    get_webhook(db, webhook_id)
    return list(
        db.scalars(
            select(WebhookDelivery)
            .where(WebhookDelivery.webhook_id == webhook_id)
            .order_by(WebhookDelivery.created_at.desc())
        ).all()
    )
