"""Marketing SMS channel service."""

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
    SmsCampaign,
    SmsSenderProfile,
    SmsTemplate,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.channel_shared_service import (
    calculate_recipients,
    check_readiness,
    compute_material_change_hash,
    compute_sms_segments,
    create_send_operation,
    get_provider_status,
    record_delivery_event,
    record_idempotent_operation,
)
from investhome_api.services.marketing.providers.sms_marketing import get_sms_marketing_provider


def _get_campaign_or_404(db: Session, campaign_id: UUID) -> SmsCampaign:
    campaign = db.get(SmsCampaign, campaign_id)
    if campaign is None or campaign.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="SMS campaign not found")
    return campaign


def list_sms_campaigns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[SmsCampaign], int]:
    query = select(SmsCampaign).where(SmsCampaign.archived_at.is_(None))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(SmsCampaign.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_sms_dashboard(db: Session) -> dict:
    total = db.scalar(select(func.count()).where(SmsCampaign.archived_at.is_(None))) or 0
    return {"total_campaigns": total, "provider_status": get_provider_status("sms")}


def create_sms_campaign(db: Session, user: User, payload: dict) -> SmsCampaign:
    body = payload.get("message_body", "")
    segments = compute_sms_segments(body) if body else {}
    campaign = SmsCampaign(
        name=payload["name"],
        message_body=body or None,
        audience_id=payload.get("audience_id"),
        template_id=payload.get("template_id"),
        sender_profile_id=payload.get("sender_profile_id"),
        content_id=payload.get("content_id"),
        content_version_id=payload.get("content_version_id"),
        marketing_campaign_id=payload.get("marketing_campaign_id"),
        opt_out_required=payload.get("opt_out_required", True),
        opt_out_text_present=payload.get("opt_out_text_present", False),
        character_count=segments.get("character_count"),
        segment_count=segments.get("segment_count"),
        created_by_user_id=user.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_sms_campaign(db: Session, campaign_id: UUID) -> SmsCampaign:
    return _get_campaign_or_404(db, campaign_id)


def update_sms_campaign(db: Session, user: User, campaign_id: UUID, payload: dict) -> SmsCampaign:
    campaign = _get_campaign_or_404(db, campaign_id)
    for field in ("name", "message_body", "audience_id", "template_id", "sender_profile_id", "scheduled_at", "opt_out_text_present"):
        if field in payload:
            setattr(campaign, field, payload[field])
    if campaign.message_body:
        segments = compute_sms_segments(campaign.message_body)
        campaign.character_count = segments["character_count"]
        campaign.segment_count = segments["segment_count"]
    campaign.material_change_hash = compute_material_change_hash({"body": campaign.message_body})
    if campaign.approval_status == ChannelApprovalStatus.APPROVED:
        campaign.approval_status = ChannelApprovalStatus.INVALIDATED
    campaign.updated_by_user_id = user.id
    db.flush()
    return campaign


def validate_sms_body(body: str) -> dict:
    return compute_sms_segments(body)


def calculate_sms_readiness(db: Session, campaign_id: UUID) -> dict:
    campaign = _get_campaign_or_404(db, campaign_id)
    recipients = calculate_recipients(db, campaign.audience_id, "sms")
    campaign.recipient_count = recipients["total"]
    campaign.eligible_recipient_count = recipients["eligible"]
    result = check_readiness(
        db,
        channel="sms",
        audience_id=campaign.audience_id,
        content_id=campaign.content_id,
        content_version_id=campaign.content_version_id,
        approval_status=campaign.approval_status.value,
        scheduled_at=campaign.scheduled_at,
        opt_out_required=campaign.opt_out_required,
        opt_out_text_present=campaign.opt_out_text_present,
    )
    campaign.readiness_state = ChannelReadinessState(result["state"])
    campaign.readiness_checks_json = result
    db.flush()
    return {**result, "recipients": recipients}


def schedule_sms_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    idempotency_key: str,
    scheduled_at: datetime | None = None,
) -> dict:
    existing = record_idempotent_operation(
        db, idempotency_key=idempotency_key, channel="sms", operation="schedule",
        resource_type="sms_campaign", resource_id=campaign_id, user=user,
    )
    if existing:
        return {"idempotent": True, **(existing.result_json or {})}

    campaign = _get_campaign_or_404(db, campaign_id)
    readiness = calculate_sms_readiness(db, campaign_id)
    if readiness["state"] == ChannelReadinessState.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=readiness)

    provider = get_sms_marketing_provider()
    schedule_time = scheduled_at or campaign.scheduled_at or datetime.now(UTC)
    result = provider.schedule_campaign({"campaign_id": str(campaign_id), "body": campaign.message_body}, schedule_time)

    campaign.status = ChannelCampaignStatus.SCHEDULED
    campaign.scheduled_at = schedule_time
    campaign.last_idempotency_key = idempotency_key

    record_delivery_event(
        db,
        channel="sms",
        campaign_type="sms_campaign",
        campaign_id=campaign_id,
        event_type=DeliveryEventType.NOT_CONNECTED if not result.get("scheduled") else DeliveryEventType.QUEUED,
        payload_json=result,
    )
    op = create_send_operation(
        db,
        idempotency_key=idempotency_key,
        channel="sms",
        operation="schedule",
        resource_type="sms_campaign",
        resource_id=campaign_id,
        status_value="not_connected" if not result.get("scheduled") else "scheduled",
        result_json=result,
        user=user,
    )
    db.flush()
    return {"idempotent": False, "operation_id": str(op.id), **result}


def send_test_sms(db: Session, campaign_id: UUID, *, phone_number: str) -> dict:
    campaign = _get_campaign_or_404(db, campaign_id)
    provider = get_sms_marketing_provider()
    return provider.send_test_sms({"campaign_id": str(campaign_id), "body": campaign.message_body, "to": phone_number})


def list_sms_templates(db: Session) -> list[SmsTemplate]:
    return list(db.scalars(
        select(SmsTemplate).where(SmsTemplate.archived_at.is_(None)).order_by(SmsTemplate.name)
    ).all())


def create_sms_template(db: Session, user: User, payload: dict) -> SmsTemplate:
    body = payload["body_text"]
    segments = compute_sms_segments(body)
    template = SmsTemplate(
        name=payload["name"],
        body_text=body,
        character_count=segments["character_count"],
        segment_count=segments["segment_count"],
        content_id=payload.get("content_id"),
        created_by_user_id=user.id,
    )
    db.add(template)
    db.flush()
    return template


def list_sms_senders(db: Session) -> list[SmsSenderProfile]:
    return list(db.scalars(select(SmsSenderProfile).where(SmsSenderProfile.is_active.is_(True))).all())
