"""Marketing email channel service."""

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
    EmailCampaign,
    EmailSenderProfile,
    EmailSendingDomain,
    EmailSequence,
    EmailSequenceStep,
    EmailTemplate,
)
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.channel_shared_service import (
    calculate_recipients,
    check_readiness,
    compute_material_change_hash,
    create_send_operation,
    record_delivery_event,
    record_idempotent_operation,
)
from investhome_api.services.marketing.providers.email_marketing import get_email_marketing_provider


def _get_campaign_or_404(db: Session, campaign_id: UUID) -> EmailCampaign:
    campaign = db.get(EmailCampaign, campaign_id)
    if campaign is None or campaign.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email campaign not found")
    return campaign


def list_email_campaigns(
    db: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    status_filter: str | None = None,
) -> tuple[list[EmailCampaign], int]:
    query = select(EmailCampaign).where(EmailCampaign.archived_at.is_(None))
    if status_filter:
        query = query.where(EmailCampaign.status == ChannelCampaignStatus(status_filter))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(EmailCampaign.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def get_email_dashboard(db: Session) -> dict:
    from investhome_api.services.marketing.channel_shared_service import get_provider_status

    total = db.scalar(select(func.count()).where(EmailCampaign.archived_at.is_(None))) or 0
    scheduled = db.scalar(
        select(func.count()).where(
            EmailCampaign.archived_at.is_(None),
            EmailCampaign.status == ChannelCampaignStatus.SCHEDULED,
        )
    ) or 0
    return {
        "total_campaigns": total,
        "scheduled_campaigns": scheduled,
        "provider_status": get_provider_status("email"),
    }


def create_email_campaign(db: Session, user: User, payload: dict) -> EmailCampaign:
    campaign = EmailCampaign(
        name=payload["name"],
        subject=payload.get("subject"),
        preview_text=payload.get("preview_text"),
        audience_id=payload.get("audience_id"),
        marketing_campaign_id=payload.get("marketing_campaign_id"),
        content_id=payload.get("content_id"),
        content_version_id=payload.get("content_version_id"),
        template_id=payload.get("template_id"),
        sender_profile_id=payload.get("sender_profile_id"),
        unsubscribe_required=payload.get("unsubscribe_required", True),
        unsubscribe_link_present=payload.get("unsubscribe_link_present", False),
        wizard_step=payload.get("wizard_step", 1),
        wizard_state_json=payload.get("wizard_state_json"),
        created_by_user_id=user.id,
    )
    db.add(campaign)
    db.flush()
    return campaign


def get_email_campaign(db: Session, campaign_id: UUID) -> EmailCampaign:
    return _get_campaign_or_404(db, campaign_id)


def update_email_campaign(db: Session, user: User, campaign_id: UUID, payload: dict) -> EmailCampaign:
    campaign = _get_campaign_or_404(db, campaign_id)
    fields = (
        "name", "subject", "preview_text", "audience_id", "content_id", "content_version_id",
        "template_id", "sender_profile_id", "scheduled_at", "unsubscribe_link_present",
        "wizard_step", "wizard_state_json", "personalisation_config_json",
    )
    for field in fields:
        if field in payload:
            setattr(campaign, field, payload[field])
    campaign.material_change_hash = compute_material_change_hash({
        "subject": campaign.subject,
        "content_version_id": str(campaign.content_version_id) if campaign.content_version_id else None,
    })
    if campaign.approval_status == ChannelApprovalStatus.APPROVED:
        campaign.approval_status = ChannelApprovalStatus.INVALIDATED
    campaign.updated_by_user_id = user.id
    db.flush()
    return campaign


def calculate_email_readiness(db: Session, campaign_id: UUID) -> dict:
    campaign = _get_campaign_or_404(db, campaign_id)
    recipients = calculate_recipients(db, campaign.audience_id, "email")
    campaign.recipient_count = recipients["total"]
    campaign.eligible_recipient_count = recipients["eligible"]
    result = check_readiness(
        db,
        channel="email",
        audience_id=campaign.audience_id,
        content_id=campaign.content_id,
        content_version_id=campaign.content_version_id,
        approval_status=campaign.approval_status.value,
        scheduled_at=campaign.scheduled_at,
        frequency_policy_id=campaign.frequency_policy_id,
        unsubscribe_required=campaign.unsubscribe_required,
        unsubscribe_link_present=campaign.unsubscribe_link_present,
    )
    campaign.readiness_state = ChannelReadinessState(result["state"])
    campaign.readiness_checks_json = result
    db.flush()
    return {**result, "recipients": recipients}


def schedule_email_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    idempotency_key: str,
    scheduled_at: datetime | None = None,
) -> dict:
    existing = record_idempotent_operation(
        db, idempotency_key=idempotency_key, channel="email", operation="schedule",
        resource_type="email_campaign", resource_id=campaign_id, user=user,
    )
    if existing:
        return {"idempotent": True, **(existing.result_json or {})}

    campaign = _get_campaign_or_404(db, campaign_id)
    readiness = calculate_email_readiness(db, campaign_id)
    if readiness["state"] == ChannelReadinessState.BLOCKED.value:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=readiness)

    provider = get_email_marketing_provider()
    schedule_time = scheduled_at or campaign.scheduled_at or datetime.now(UTC)
    result = provider.schedule_campaign(
        {"campaign_id": str(campaign_id), "subject": campaign.subject},
        schedule_time,
    )

    campaign.status = ChannelCampaignStatus.SCHEDULED
    campaign.scheduled_at = schedule_time
    campaign.last_idempotency_key = idempotency_key

    record_delivery_event(
        db,
        channel="email",
        campaign_type="email_campaign",
        campaign_id=campaign_id,
        event_type=DeliveryEventType.NOT_CONNECTED if not result.get("scheduled") else DeliveryEventType.QUEUED,
        payload_json=result,
    )
    op = create_send_operation(
        db,
        idempotency_key=idempotency_key,
        channel="email",
        operation="schedule",
        resource_type="email_campaign",
        resource_id=campaign_id,
        status_value="not_connected" if not result.get("scheduled") else "scheduled",
        result_json=result,
        user=user,
    )
    db.flush()
    return {"idempotent": False, "operation_id": str(op.id), **result}


def send_test_email(db: Session, user: User, campaign_id: UUID, *, recipient_email: str) -> dict:
    campaign = _get_campaign_or_404(db, campaign_id)
    provider = get_email_marketing_provider()
    return provider.send_test_email({
        "campaign_id": str(campaign_id),
        "subject": campaign.subject,
        "to": recipient_email,
    })


def list_email_templates(db: Session) -> list[EmailTemplate]:
    return list(db.scalars(
        select(EmailTemplate).where(EmailTemplate.archived_at.is_(None)).order_by(EmailTemplate.name)
    ).all())


def create_email_template(db: Session, user: User, payload: dict) -> EmailTemplate:
    template = EmailTemplate(
        name=payload["name"],
        subject=payload.get("subject"),
        html_body=payload.get("html_body"),
        text_body=payload.get("text_body"),
        content_id=payload.get("content_id"),
        content_version_id=payload.get("content_version_id"),
        created_by_user_id=user.id,
    )
    db.add(template)
    db.flush()
    return template


def list_email_senders(db: Session) -> list[EmailSenderProfile]:
    return list(db.scalars(select(EmailSenderProfile).where(EmailSenderProfile.is_active.is_(True))).all())


def list_email_domains(db: Session) -> list[EmailSendingDomain]:
    return list(db.scalars(select(EmailSendingDomain)).all())


def create_email_domain(db: Session, payload: dict) -> EmailSendingDomain:
    domain = EmailSendingDomain(domain=payload["domain"])
    db.add(domain)
    db.flush()
    return domain


def list_email_sequences(db: Session) -> list[EmailSequence]:
    return list(db.scalars(
        select(EmailSequence).where(EmailSequence.archived_at.is_(None)).order_by(EmailSequence.name)
    ).all())


def get_email_sequence(db: Session, sequence_id: UUID) -> EmailSequence:
    seq = db.get(EmailSequence, sequence_id)
    if seq is None or seq.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found")
    return seq


def list_sequence_steps(db: Session, sequence_id: UUID) -> list[EmailSequenceStep]:
    return list(db.scalars(
        select(EmailSequenceStep)
        .where(EmailSequenceStep.sequence_id == sequence_id)
        .order_by(EmailSequenceStep.step_order)
    ).all())
