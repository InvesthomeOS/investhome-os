"""Consent and eligibility — consumes CRM consent truth, unknown consent ≠ eligible."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_communication import CrmCommunicationPreference
from investhome_api.models.marketing import MembershipExclusionReason

# Centralized inclusion/exclusion precedence (lower index = higher priority for exclusion)
PRECEDENCE_ORDER = [
    "legal",
    "suppression",
    "explicit_exclusion",
    "consent",
    "channel",
    "dynamic_exclusion",
    "explicit_inclusion",
    "dynamic_inclusion",
]

CHANNEL_CONSENT_MAP = {
    "email": "consent_email",
    "sms": "consent_sms",
    "whatsapp": "consent_whatsapp",
    "phone": "consent_phone",
}


@dataclass(frozen=True)
class EligibilityResult:
    eligible: bool
    reason: str | None
    precedence_level: str | None
    consent_status: dict[str, str | None]


def _get_crm_preferences(db: Session, contact_id: UUID | None, company_id: UUID | None) -> CrmCommunicationPreference | None:
    if contact_id:
        pref = db.scalar(
            select(CrmCommunicationPreference).where(
                CrmCommunicationPreference.entity_type == "contact",
                CrmCommunicationPreference.entity_id == contact_id,
            )
        )
        if pref:
            return pref
    if company_id:
        return db.scalar(
            select(CrmCommunicationPreference).where(
                CrmCommunicationPreference.entity_type == "company",
                CrmCommunicationPreference.entity_id == company_id,
            )
        )
    return None


def get_consent_status(db: Session, contact_id: UUID | None, company_id: UUID | None) -> dict[str, str | None]:
    """Return consent status per channel — unknown when no CRM record exists."""
    pref = _get_crm_preferences(db, contact_id, company_id)
    if pref is None:
        return {ch: "unknown" for ch in CHANNEL_CONSENT_MAP}
    if pref.do_not_contact:
        return {ch: "blocked" for ch in CHANNEL_CONSENT_MAP}
    result: dict[str, str | None] = {}
    for channel, attr in CHANNEL_CONSENT_MAP.items():
        value = getattr(pref, attr, None)
        if value is True:
            result[channel] = "granted"
        elif value is False:
            result[channel] = "denied"
        else:
            result[channel] = "unknown"
    return result


def is_channel_eligible(
    db: Session,
    contact_id: UUID | None,
    company_id: UUID | None,
    channel: str,
    *,
    suppression: dict | None = None,
    explicit_excluded: bool = False,
    legal_blocked: bool = False,
) -> EligibilityResult:
    """Apply centralized precedence — unknown consent blocks eligibility."""
    consent_status = get_consent_status(db, contact_id, company_id)

    if legal_blocked:
        return EligibilityResult(False, "legal_compliance", "legal", consent_status)
    if suppression and suppression.get("active"):
        return EligibilityResult(False, "suppression", "suppression", consent_status)
    if explicit_excluded:
        return EligibilityResult(False, "explicit_exclusion", "explicit_exclusion", consent_status)

    channel_consent = consent_status.get(channel, "unknown")
    if channel_consent in ("unknown", "denied", "blocked"):
        return EligibilityResult(False, "consent", "consent", consent_status)

    pref = _get_crm_preferences(db, contact_id, company_id)
    if pref and pref.blocked_channels and channel in (pref.blocked_channels or []):
        return EligibilityResult(False, "channel_blocked", "channel", consent_status)

    return EligibilityResult(True, None, None, consent_status)


def resolve_membership_eligibility(
    db: Session,
    *,
    contact_id: UUID | None,
    company_id: UUID | None,
    channel: str | None = None,
    suppression_json: dict | None = None,
    explicit_excluded: bool = False,
    legal_blocked: bool = False,
) -> tuple[bool, dict]:
    """Resolve final membership eligibility with explainability."""
    ch = channel or "email"
    result = is_channel_eligible(
        db,
        contact_id,
        company_id,
        ch,
        suppression=suppression_json,
        explicit_excluded=explicit_excluded,
        legal_blocked=legal_blocked,
    )
    explainability = {
        "eligible": result.eligible,
        "reason": result.reason,
        "precedence_level": result.precedence_level,
        "consent_status": result.consent_status,
        "precedence_order": PRECEDENCE_ORDER,
    }
    if not result.eligible and result.reason == "consent":
        explainability["exclusion_reason"] = MembershipExclusionReason.CONSENT.value
    elif not result.eligible and result.reason == "suppression":
        explainability["exclusion_reason"] = MembershipExclusionReason.SUPPRESSION.value
    elif not result.eligible and result.reason == "explicit_exclusion":
        explainability["exclusion_reason"] = MembershipExclusionReason.EXPLICIT.value
    elif not result.eligible and result.reason == "legal_compliance":
        explainability["exclusion_reason"] = MembershipExclusionReason.LEGAL.value
    elif not result.eligible and result.reason == "channel_blocked":
        explainability["exclusion_reason"] = MembershipExclusionReason.CHANNEL.value
    return result.eligible, explainability


def validate_audience_consent(db: Session, audience_id: UUID, required_channels: list[str]) -> dict:
    """Validate audience consent requirements — returns blocking summary."""
    from investhome_api.models.marketing import AudienceMembership

    memberships = db.scalars(
        select(AudienceMembership).where(AudienceMembership.audience_id == audience_id)
    ).all()
    blocked = 0
    unknown = 0
    for m in memberships:
        if not m.is_included:
            continue
        for ch in required_channels:
            eligible, _ = resolve_membership_eligibility(
                db, contact_id=m.contact_id, company_id=m.company_id, channel=ch
            )
            if not eligible:
                consent = get_consent_status(db, m.contact_id, m.company_id).get(ch, "unknown")
                if consent == "unknown":
                    unknown += 1
                else:
                    blocked += 1
    return {
        "audience_id": str(audience_id),
        "required_channels": required_channels,
        "blocked_count": blocked,
        "unknown_consent_count": unknown,
        "ready": blocked == 0 and unknown == 0,
    }
