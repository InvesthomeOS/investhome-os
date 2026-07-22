"""Shared marketing channel services — readiness, eligibility, idempotency, opt-out."""

from __future__ import annotations

import hashlib
import math
from datetime import UTC, datetime, time
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.marketing import AudienceMembership, MarketingChannel
from investhome_api.models.marketing_channel_communications import (
    ChannelDeliveryEvent,
    ChannelReadinessState,
    ChannelSendOperation,
    DeliveryEventType,
    MarketingFrequencyPolicy,
)
from investhome_api.models.marketing_content_studio import ContentVersion
from investhome_api.models.user_auth import User
from investhome_api.services.marketing.campaign_service import compute_pages
from investhome_api.services.marketing.consent_eligibility_service import (
    resolve_membership_eligibility,
)
from investhome_api.services.marketing.providers import MarketingProviderConnectionStatus
from investhome_api.services.marketing.providers.email_marketing import get_email_marketing_provider
from investhome_api.services.marketing.providers.sms_marketing import get_sms_marketing_provider
from investhome_api.services.marketing.providers.social import get_social_provider
from investhome_api.services.marketing.providers.whatsapp_marketing import get_whatsapp_marketing_provider


def compute_material_change_hash(fields: dict[str, Any]) -> str:
    payload = "|".join(f"{k}={v}" for k, v in sorted(fields.items()) if v is not None)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def get_provider_status(channel: str) -> dict[str, Any]:
    """Return honest provider connection status — never fake connected."""
    if channel == "email":
        adapter = get_email_marketing_provider()
        st = adapter.get_status()
    elif channel == "whatsapp":
        adapter = get_whatsapp_marketing_provider()
        st = adapter.get_status()
    elif channel == "sms":
        adapter = get_sms_marketing_provider()
        st = adapter.get_status()
    elif channel == "social":
        adapter = get_social_provider("linkedin")
        st = adapter.get_status()
    else:
        st = MarketingProviderConnectionStatus.NOT_CONNECTED
    return {
        "channel": channel,
        "status": st.value,
        "connected": st == MarketingProviderConnectionStatus.CONNECTED,
        "message": "Provider integration not configured" if st != MarketingProviderConnectionStatus.CONNECTED else None,
    }


def list_channel_provider_statuses(db: Session) -> list[dict[str, Any]]:
    channels = db.scalars(select(MarketingChannel)).all()
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ch in channels:
        cat = ch.category.value if hasattr(ch.category, "value") else str(ch.category)
        if cat in ("email", "sms", "whatsapp", "social_organic", "paid_social"):
            key = "social" if cat in ("social_organic", "paid_social") else cat
            if key not in seen:
                seen.add(key)
                provider = get_provider_status(key)
                provider["channel_id"] = str(ch.id)
                provider["connection_status"] = ch.connection_status.value if ch.connection_status else "not_connected"
                results.append(provider)
    for key in ("email", "whatsapp", "sms", "social"):
        if key not in seen:
            results.append(get_provider_status(key))
    return results


def calculate_recipients(
    db: Session,
    audience_id: UUID | None,
    channel: str,
) -> dict[str, Any]:
    """Calculate eligible recipients with exclusion drill-down."""
    if audience_id is None:
        return {
            "total": 0,
            "eligible": 0,
            "excluded": 0,
            "exclusions": [],
            "duplicate_count": 0,
        }

    memberships = db.scalars(
        select(AudienceMembership).where(
            AudienceMembership.audience_id == audience_id,
            AudienceMembership.is_included.is_(True),
        )
    ).all()

    seen_contacts: set[UUID] = set()
    duplicate_count = 0
    eligible = 0
    exclusions: list[dict[str, Any]] = []

    for m in memberships:
        contact_key = m.contact_id or m.company_id
        if contact_key is None:
            continue
        if m.contact_id and m.contact_id in seen_contacts:
            duplicate_count += 1
            continue
        if m.contact_id:
            seen_contacts.add(m.contact_id)

        is_eligible, explain = resolve_membership_eligibility(
            db,
            contact_id=m.contact_id,
            company_id=m.company_id,
            channel=channel,
            suppression_json=getattr(m, "suppression_json", None),
            explicit_excluded=not m.is_included,
        )
        if is_eligible:
            eligible += 1
        else:
            exclusions.append({
                "contact_id": str(m.contact_id) if m.contact_id else None,
                "company_id": str(m.company_id) if m.company_id else None,
                "reason": explain.get("reason"),
                "exclusion_reason": explain.get("exclusion_reason"),
                "consent_status": explain.get("consent_status"),
            })

    total = len(memberships)
    return {
        "total": total,
        "eligible": eligible,
        "excluded": total - eligible - duplicate_count,
        "duplicate_count": duplicate_count,
        "exclusions": exclusions[:50],
    }


def _check_content_approval(db: Session, content_id: UUID | None, content_version_id: UUID | None) -> dict[str, Any]:
    from investhome_api.models.marketing import MarketingApproval, MarketingApprovalStatus

    if content_id is None and content_version_id is None:
        return {"passed": True, "message": "No content linked"}
    resolved_content_id = content_id
    if content_version_id and not resolved_content_id:
        version = db.get(ContentVersion, content_version_id)
        if version is None:
            return {"passed": False, "message": "Content version not found"}
        resolved_content_id = version.content_id
    if resolved_content_id is None:
        return {"passed": False, "message": "Content not found"}
    query = select(MarketingApproval).where(
        MarketingApproval.entity_type == "content",
        MarketingApproval.entity_id == resolved_content_id,
        MarketingApproval.status == MarketingApprovalStatus.APPROVED,
    )
    if content_version_id:
        query = query.where(MarketingApproval.version_id == content_version_id)
    approved = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    if approved == 0:
        return {"passed": False, "message": "Approved content version required"}
    return {"passed": True, "message": "Content version approved"}


def _check_quiet_hours(policy: MarketingFrequencyPolicy | None, scheduled_at: datetime | None) -> dict[str, Any]:
    if policy is None or not policy.quiet_hours_start or not policy.quiet_hours_end:
        return {"passed": True}
    if scheduled_at is None:
        return {"passed": True}
    tz = ZoneInfo(policy.timezone or "UTC")
    local_time = scheduled_at.astimezone(tz).time()
    start = time.fromisoformat(policy.quiet_hours_start)
    end = time.fromisoformat(policy.quiet_hours_end)
    if start <= end:
        in_quiet = start <= local_time <= end
    else:
        in_quiet = local_time >= start or local_time <= end
    if in_quiet:
        return {"passed": False, "message": f"Scheduled during quiet hours ({policy.quiet_hours_start}-{policy.quiet_hours_end})"}
    return {"passed": True}


def check_readiness(
    db: Session,
    *,
    channel: str,
    audience_id: UUID | None,
    content_id: UUID | None = None,
    content_version_id: UUID | None = None,
    approval_status: str = "not_required",
    scheduled_at: datetime | None = None,
    frequency_policy_id: UUID | None = None,
    unsubscribe_required: bool = False,
    unsubscribe_link_present: bool = False,
    opt_out_required: bool = False,
    opt_out_text_present: bool = False,
    whatsapp_template_status: str | None = None,
    provider_channel: str | None = None,
    require_audience: bool = True,
) -> dict[str, Any]:
    """Readiness check — unknown consent NEVER eligible."""
    checks: list[dict[str, Any]] = []
    blocked = False
    warnings = False

    provider = get_provider_status(provider_channel or channel)
    provider_check = {
        "key": "provider",
        "label": "Provider connection",
        "passed": provider["connected"],
        "message": provider.get("message") or ("Connected" if provider["connected"] else "Not connected"),
    }
    checks.append(provider_check)
    if not provider["connected"]:
        warnings = True

    if audience_id:
        recipients = calculate_recipients(db, audience_id, channel)
        consent_blocked = any(
            e.get("reason") == "consent" for e in recipients.get("exclusions", [])
        )
        unknown_consent = any(
            (e.get("consent_status") or {}).get(channel) == "unknown"
            for e in recipients.get("exclusions", [])
            if e.get("reason") == "consent"
        )
        audience_check = {
            "key": "audience",
            "label": "Audience eligibility",
            "passed": recipients["eligible"] > 0 and not unknown_consent,
            "message": f"{recipients['eligible']} eligible of {recipients['total']}",
            "details": recipients,
        }
        checks.append(audience_check)
        if unknown_consent or recipients["eligible"] == 0:
            blocked = True
        elif recipients["excluded"] > 0:
            warnings = True
    elif require_audience:
        checks.append({"key": "audience", "label": "Audience", "passed": False, "message": "No audience selected"})
        blocked = True

    content_check = _check_content_approval(db, content_id, content_version_id)
    checks.append({"key": "content", "label": "Content approval", **content_check})
    if not content_check["passed"] and content_id:
        blocked = True

    if approval_status == "pending":
        checks.append({"key": "approval", "label": "Channel approval", "passed": False, "message": "Pending approval"})
        blocked = True
    elif approval_status == "rejected":
        checks.append({"key": "approval", "label": "Channel approval", "passed": False, "message": "Rejected"})
        blocked = True
    elif approval_status == "invalidated":
        checks.append({"key": "approval", "label": "Channel approval", "passed": False, "message": "Approval invalidated"})
        blocked = True

    if unsubscribe_required and not unsubscribe_link_present:
        checks.append({"key": "unsubscribe", "label": "Unsubscribe link", "passed": False, "message": "Required"})
        blocked = True
    elif unsubscribe_required:
        checks.append({"key": "unsubscribe", "label": "Unsubscribe link", "passed": True, "message": "Present"})

    if opt_out_required and not opt_out_text_present:
        checks.append({"key": "opt_out", "label": "SMS opt-out text", "passed": False, "message": "Required"})
        blocked = True
    elif opt_out_required:
        checks.append({"key": "opt_out", "label": "SMS opt-out text", "passed": True, "message": "Present"})

    if whatsapp_template_status and whatsapp_template_status != "approved":
        checks.append({
            "key": "whatsapp_template",
            "label": "WhatsApp template",
            "passed": False,
            "message": f"Template status: {whatsapp_template_status}",
        })
        blocked = True

    policy = db.get(MarketingFrequencyPolicy, frequency_policy_id) if frequency_policy_id else None
    quiet_check = _check_quiet_hours(policy, scheduled_at)
    if quiet_check.get("passed") is False:
        checks.append({"key": "quiet_hours", "label": "Quiet hours", **quiet_check})
        blocked = True

    if blocked:
        state = ChannelReadinessState.BLOCKED.value
    elif warnings:
        state = ChannelReadinessState.WARNING.value
    else:
        state = ChannelReadinessState.READY.value

    return {"state": state, "checks": checks, "ready": state == ChannelReadinessState.READY.value}


def record_idempotent_operation(
    db: Session,
    *,
    idempotency_key: str,
    channel: str,
    operation: str,
    resource_type: str,
    resource_id: UUID,
    user: User | None = None,
) -> ChannelSendOperation | None:
    """Return existing operation if idempotency key already used."""
    existing = db.scalar(
        select(ChannelSendOperation).where(ChannelSendOperation.idempotency_key == idempotency_key)
    )
    return existing


def create_send_operation(
    db: Session,
    *,
    idempotency_key: str,
    channel: str,
    operation: str,
    resource_type: str,
    resource_id: UUID,
    status_value: str,
    result_json: dict | None,
    user: User | None = None,
) -> ChannelSendOperation:
    op_record = ChannelSendOperation(
        idempotency_key=idempotency_key,
        channel=channel,
        operation=operation,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status_value,
        result_json=result_json,
        created_by_user_id=user.id if user else None,
    )
    db.add(op_record)
    db.flush()
    return op_record


def record_delivery_event(
    db: Session,
    *,
    channel: str,
    campaign_type: str,
    campaign_id: UUID,
    event_type: DeliveryEventType,
    contact_id: UUID | None = None,
    payload_json: dict | None = None,
) -> ChannelDeliveryEvent:
    event = ChannelDeliveryEvent(
        channel=channel,
        campaign_type=campaign_type,
        campaign_id=campaign_id,
        contact_id=contact_id,
        event_type=event_type,
        payload_json=payload_json,
        occurred_at=datetime.now(UTC),
    )
    db.add(event)
    db.flush()
    return event


def process_opt_out(
    db: Session,
    *,
    contact_id: UUID | None,
    company_id: UUID | None,
    channel: str,
) -> dict[str, Any]:
    """Update canonical CRM consent via authorized contract."""
    if contact_id is None and company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contact or company required")

    entity_type = "contact" if contact_id else "company"
    entity_id = contact_id or company_id
    pref = db.scalar(
        select(CrmCommunicationPreference).where(
            CrmCommunicationPreference.entity_type == entity_type,
            CrmCommunicationPreference.entity_id == entity_id,
        )
    )
    consent_field_map = {
        "email": "consent_email",
        "sms": "consent_sms",
        "whatsapp": "consent_whatsapp",
    }
    field = consent_field_map.get(channel)
    if field is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported channel: {channel}")

    if pref is None:
        pref = CrmCommunicationPreference(
            entity_type=entity_type,
            entity_id=entity_id,
            do_not_contact=False,
        )
        db.add(pref)
    setattr(pref, field, False)
    db.flush()
    return {"updated": True, "channel": channel, "consent": "denied"}


def preview_personalization(config: dict | None, sample_contact: dict | None = None) -> dict[str, Any]:
    sample = sample_contact or {"first_name": "Sample", "last_name": "Contact", "email": "sample@example.com"}
    tokens = config or {}
    preview_body = tokens.get("body_template", "Hello {{first_name}}")
    for key, value in sample.items():
        preview_body = preview_body.replace(f"{{{{{key}}}}}", str(value))
    return {"preview": preview_body, "tokens_used": list(sample.keys()), "config": tokens}


def list_frequency_policies(db: Session, channel: str | None = None) -> list[MarketingFrequencyPolicy]:
    query = select(MarketingFrequencyPolicy).where(MarketingFrequencyPolicy.is_active.is_(True))
    if channel:
        query = query.where(MarketingFrequencyPolicy.channel == channel)
    return list(db.scalars(query.order_by(MarketingFrequencyPolicy.name)).all())


def create_frequency_policy(db: Session, payload: dict) -> MarketingFrequencyPolicy:
    policy = MarketingFrequencyPolicy(**payload)
    db.add(policy)
    db.flush()
    return policy


def list_delivery_events(
    db: Session,
    *,
    channel: str | None = None,
    campaign_type: str | None = None,
    campaign_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[ChannelDeliveryEvent], int]:
    query = select(ChannelDeliveryEvent)
    if channel:
        query = query.where(ChannelDeliveryEvent.channel == channel)
    if campaign_type:
        query = query.where(ChannelDeliveryEvent.campaign_type == campaign_type)
    if campaign_id:
        query = query.where(ChannelDeliveryEvent.campaign_id == campaign_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(ChannelDeliveryEvent.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def compute_sms_segments(body: str) -> dict[str, int]:
    length = len(body)
    if length <= 160:
        return {"character_count": length, "segment_count": 1}
    return {"character_count": length, "segment_count": math.ceil(length / 153)}
