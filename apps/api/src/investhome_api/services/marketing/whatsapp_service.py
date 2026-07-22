"""Marketing WhatsApp channel service."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.marketing_channel_communications import (
    ChannelApprovalStatus,
    ChannelCampaignStatus,
    ChannelReadinessState,
    DeliveryEventType,
    WhatsAppCampaign,
    WhatsAppConversation,
    WhatsAppSenderProfile,
    WhatsAppTemplate,
    WhatsAppTemplateStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.channel_shared_service import (
    calculate_recipients,
    check_readiness,
    compute_material_change_hash,
    create_send_operation,
    get_provider_status,
    record_delivery_event,
    record_idempotent_operation,
)
from investhome_api.services.marketing.providers.whatsapp_marketing import get_whatsapp_marketing_provider


def _get_campaign_or_404(db: Session, campaign_id: UUID) -> WhatsAppCampaign:
    campaign = db.get(WhatsAppCampaign, campaign_id)
    if campaign is None or campaign.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WhatsApp campaign not found")
    return campaign


def list_whatsapp_campaigns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[WhatsAppCampaign], int]:
    query = select(WhatsAppCampaign).where(WhatsAppCampaign.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(WhatsAppCampaign.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_whatsapp_dashboard(db: Session) -> dict:
    total = db.scalar(select(func.count()).where(WhatsAppCampaign.archived_at.is_(None))) or 0
    return {"total_campaigns": total, "provider_status": get_provider_status("whatsapp")}


def create_whatsapp_campaign(db: Session, user: User, payload: dict) -> WhatsAppCampaign:
    campaign = WhatsAppCampaign(
        name=payload["name"],
        audience_id=payload.get("audience_id"),
        template_id=payload.get("template_id"),
        sender_profile_id=payload.get("sender_profile_id"),
        content_id=payload.get("content_id"),
        content_version_id=payload.get("content_version_id"),
        marketing_campaign_id=payload.get("marketing_campaign_id"),
        created_by_user_id=user.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_whatsapp_campaign(db: Session, campaign_id: UUID) -> WhatsAppCampaign:
    return _get_campaign_or_404(db, campaign_id)


def update_whatsapp_campaign(db: Session, user: User, campaign_id: UUID, payload: dict) -> WhatsAppCampaign:
    campaign = _get_campaign_or_404(db, campaign_id)
    for field in ("name", "audience_id", "template_id", "sender_profile_id", "scheduled_at", "content_id", "content_version_id"):
        if field in payload:
            setattr(campaign, field, payload[field])
    campaign.material_change_hash = compute_material_change_hash({
        "template_id": str(campaign.template_id) if campaign.template_id else None,
    })
    if campaign.approval_status == ChannelApprovalStatus.APPROVED:
        campaign.approval_status = ChannelApprovalStatus.INVALIDATED
    campaign.updated_by_user_id = user.id
    db.flush()
    return campaign


def calculate_whatsapp_readiness(db: Session, campaign_id: UUID) -> dict:
    campaign = _get_campaign_or_404(db, campaign_id)
    template_status = None
    if campaign.template_id:
        template = db.get(WhatsAppTemplate, campaign.template_id)
        template_status = template.status.value if template else "missing"
    recipients = calculate_recipients(db, campaign.audience_id, "whatsapp")
    campaign.recipient_count = recipients["total"]
    campaign.eligible_recipient_count = recipients["eligible"]
    result = check_readiness(
        db,
        channel="whatsapp",
        audience_id=campaign.audience_id,
        content_id=campaign.content_id,
        content_version_id=campaign.content_version_id,
        approval_status=campaign.approval_status.value,
        scheduled_at=campaign.scheduled_at,
        whatsapp_template_status=template_status,
    )
    campaign.readiness_state = ChannelReadinessState(result["state"])
    campaign.readiness_checks_json = result
    db.flush()
    return {**result, "recipients": recipients}


def schedule_whatsapp_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    idempotency_key: str,
    scheduled_at: datetime | None = None,
) -> dict:
    existing = record_idempotent_operation(
        db, idempotency_key=idempotency_key, channel="whatsapp", operation="schedule",
        resource_type="whatsapp_campaign", resource_id=campaign_id, user=user,
    )
    if existing:
        return {"idempotent": True, **(existing.result_json or {})}

    campaign = _get_campaign_or_404(db, campaign_id)
    readiness = calculate_whatsapp_readiness(db, campaign_id)
    if readiness["state"] == ChannelReadinessState.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=readiness)

    provider = get_whatsapp_marketing_provider()
    schedule_time = scheduled_at or campaign.scheduled_at or datetime.now(UTC)
    result = provider.schedule_campaign({"campaign_id": str(campaign_id)}, schedule_time)

    campaign.status = ChannelCampaignStatus.SCHEDULED
    campaign.scheduled_at = schedule_time
    campaign.last_idempotency_key = idempotency_key

    record_delivery_event(
        db,
        channel="whatsapp",
        campaign_type="whatsapp_campaign",
        campaign_id=campaign_id,
        event_type=DeliveryEventType.NOT_CONNECTED if not result.get("scheduled") else DeliveryEventType.QUEUED,
        payload_json=result,
    )
    op = create_send_operation(
        db,
        idempotency_key=idempotency_key,
        channel="whatsapp",
        operation="schedule",
        resource_type="whatsapp_campaign",
        resource_id=campaign_id,
        status_value="not_connected" if not result.get("scheduled") else "scheduled",
        result_json=result,
        user=user,
    )
    db.flush()
    return {"idempotent": False, "operation_id": str(op.id), **result}


def list_whatsapp_templates(db: Session) -> list[WhatsAppTemplate]:
    return list(db.scalars(
        select(WhatsAppTemplate).where(WhatsAppTemplate.archived_at.is_(None)).order_by(WhatsAppTemplate.name)
    ).all())


def create_whatsapp_template(db: Session, user: User, payload: dict) -> WhatsAppTemplate:
    template = WhatsAppTemplate(
        name=payload["name"],
        language=payload.get("language", "en"),
        category=payload.get("category"),
        body_text=payload.get("body_text"),
        header_text=payload.get("header_text"),
        footer_text=payload.get("footer_text"),
        placeholders_json=payload.get("placeholders_json"),
        content_id=payload.get("content_id"),
        created_by_user_id=user.id,
    )
    db.add(template)
    db.flush()
    return template


def submit_whatsapp_template(db: Session, template_id: UUID) -> dict:
    template = db.get(WhatsAppTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    provider = get_whatsapp_marketing_provider()
    result = provider.submit_template({"template_id": str(template_id), "name": template.name})
    if result.get("submitted"):
        template.status = WhatsAppTemplateStatus.SUBMITTED
    else:
        template.status = WhatsAppTemplateStatus.PENDING_SUBMISSION
    db.flush()
    return result


def list_whatsapp_senders(db: Session) -> list[WhatsAppSenderProfile]:
    return list(db.scalars(select(WhatsAppSenderProfile).where(WhatsAppSenderProfile.is_active.is_(True))).all())


def list_whatsapp_conversations(db: Session) -> list[WhatsAppConversation]:
    return list(db.scalars(
        select(WhatsAppConversation).order_by(WhatsAppConversation.last_message_at.desc()).limit(100)
    ).all())
