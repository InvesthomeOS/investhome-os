"""CRM contact management service."""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from datetime import UTC, datetime
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func, not_, or_, select
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.activity import ActivityEntityType
from investhome_api.models.company import Company
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactBrokerProfile,
    CrmContactBuyerProfile,
    CrmContactDuplicateCandidate,
    CrmContactInvestmentProfile,
    CrmContactMergeHistory,
    CrmContactPriority,
    CrmContactSavedView,
    CrmContactStatus,
    CrmContactTag,
    CrmContactType,
    CrmContactTypeAssignment,
    CrmContactVendorProfile,
    CrmLifecycleStage,
    CrmTag,
)
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import (
    CrmBitrixHistory,
    CrmBitrixVerificationSummary,
    CrmBrokerProfileSchema,
    CrmBuyerProfileSchema,
    CrmContactBulkUpdateRequest,
    CrmContactCreate,
    CrmContactDetail,
    CrmContactActivityVerification,
    CrmContactAgentVerification,
    CrmContactAgreementVerification,
    CrmContactImportRequest,
    CrmContactImportResponse,
    CrmContactImportRow,
    CrmContactSavedViewCreate,
    CrmContactSavedViewResponse,
    CrmContactSavedViewUpdate,
    CrmContactSummary,
    CrmContactTimelineEntry,
    CrmContactUpdate,
    CrmDuplicateCheckRequest,
    CrmDuplicateMatch,
    CrmInvestmentProfileSchema,
    CrmJunkReasonCount,
    CrmVendorProfileSchema,
)
from investhome_api.services.crm.bitrix_project_aliases import (
    BITRIX_PROJECT_GROUP_LABELS,
    BitrixProjectGroup,
)
from investhome_api.services.crm.identity import (
    displayable_phone,
    displayable_phones,
    normalize_email as identity_normalize_email,
    normalize_full_name,
    normalize_phone as identity_normalize_phone,
    parse_phone,
)
from investhome_api.services.permission_service import user_has_permission

CRM_CONTACT_ACTIVITY_FIELDS = [
    "display_name",
    "contact_type",
    "status",
    "lifecycle_stage",
    "relationship_status",
    "priority",
    "owner_user_id",
    "primary_email",
    "primary_phone",
    "organization_name",
]

SORTABLE_COLUMNS = {
    "display_name",
    "contact_type",
    "organization_name",
    "lifecycle_stage",
    "relationship_status",
    "priority",
    "relationship_score",
    "engagement_score",
    "last_contact_at",
    "next_follow_up_at",
    "updated_at",
    "created_at",
}


def paginate_total_pages(total: int, page_size: int) -> int:
    return max(1, ceil(total / page_size)) if page_size else 1


def contact_list_meta(*, total: int, page: int, page_size: int) -> dict[str, int | str]:
    pages = paginate_total_pages(total, page_size)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": pages,
    }


def normalize_email(value: str | None) -> str | None:
    return identity_normalize_email(value)


def normalize_phone(value: str | None) -> str | None:
    return identity_normalize_phone(value)


def _contact_types(contact: CrmContact) -> list[CrmContactType]:
    if contact.type_assignments:
        return [assignment.contact_type for assignment in contact.type_assignments]
    return [contact.contact_type]


def _resolve_owner_name(db: Session, owner_user_id: UUID | None) -> str | None:
    if owner_user_id is None:
        return None
    user = db.get(User, owner_user_id)
    if user is None:
        return None
    return user.full_name or user.email


def _resolve_company_name(db: Session, company_id: UUID | None) -> str | None:
    if company_id is None:
        return None
    company = db.get(Company, company_id)
    return company.company_name if company else None


def _agreement_meta_text(agreement: CrmAgreement, keys: tuple[str, ...]) -> str | None:
    raw = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    folded = {str(key).casefold().replace("ı", "i"): value for key, value in raw.items()}
    for key in keys:
        value = raw.get(key)
        if value is None:
            value = folded.get(key.casefold().replace("ı", "i"))
        if value is None or str(value).strip() in {"", "—", "-", "none", "null"}:
            continue
        return str(value).strip()
    return None


def compute_relationship_scores(contact: CrmContact) -> tuple[int, int]:
    """Deterministic relationship and engagement scores from contact attributes."""
    relationship = 0
    engagement = 0

    if contact.primary_email:
        relationship += 10
    if contact.primary_phone:
        relationship += 10
    if contact.linkedin_url:
        relationship += 5
    if contact.last_contact_at:
        days = (datetime.now(UTC) - contact.last_contact_at.replace(tzinfo=UTC)).days
        if days <= 7:
            engagement += 30
        elif days <= 30:
            engagement += 20
        elif days <= 90:
            engagement += 10
    if contact.next_follow_up_at:
        engagement += 5
    if contact.is_favorite:
        relationship += 10
    if contact.lead_id:
        relationship += 10
    if contact.investor_id:
        relationship += 15

    strength_bonus = {
        "weak": 0,
        "moderate": 10,
        "strong": 20,
        "strategic": 30,
    }
    relationship += strength_bonus.get(contact.relationship_strength.value, 0)

    status_bonus = {
        "hot": 20,
        "active": 15,
        "warm": 10,
        "cold": 0,
        "at_risk": 5,
        "lost": 0,
        "unknown": 0,
    }
    relationship += status_bonus.get(contact.relationship_status.value, 0)

    return min(relationship, 100), min(engagement, 100)


def _strip_sensitive_fields(
    detail: CrmContactDetail,
    *,
    can_view_financial: bool,
    can_view_compliance: bool,
) -> CrmContactDetail:
    if not can_view_financial:
        detail.investment_profile = None
        if detail.buyer_profile:
            detail.buyer_profile = CrmBuyerProfileSchema(
                preferred_locations=detail.buyer_profile.preferred_locations,
                property_types=detail.buyer_profile.property_types,
                bedroom_min=detail.buyer_profile.bedroom_min,
                financing_status=detail.buyer_profile.financing_status,
                purchase_timeline=detail.buyer_profile.purchase_timeline,
                notes=detail.buyer_profile.notes,
            )
        if detail.broker_profile:
            detail.broker_profile = CrmBrokerProfileSchema(
                license_number=detail.broker_profile.license_number,
                brokerage_name=detail.broker_profile.brokerage_name,
                specialization=detail.broker_profile.specialization,
                service_areas=detail.broker_profile.service_areas,
                notes=detail.broker_profile.notes,
            )
        if detail.vendor_profile:
            detail.vendor_profile = CrmVendorProfileSchema(
                vendor_category=detail.vendor_profile.vendor_category,
                service_scope=detail.vendor_profile.service_scope,
                contract_status=detail.vendor_profile.contract_status,
                insurance_verified=detail.vendor_profile.insurance_verified,
                notes=detail.vendor_profile.notes,
            )
    if not can_view_compliance:
        detail.compliance_data = None
    return detail


def serialize_contact_summary(
    db: Session,
    contact: CrmContact,
    *,
    agreement_projects: list[str] | None = None,
) -> CrmContactSummary:
    rel_score, eng_score = compute_relationship_scores(contact)
    original_asama = None
    historical_junk = False
    source_channel = None
    bitrix_responsible = None
    bitrix = (contact.metadata_json or {}).get("bitrix_import")
    if isinstance(bitrix, dict):
        raw_stage = bitrix.get("original_asama")
        original_asama = str(raw_stage) if raw_stage else None
        historical_junk = bool(bitrix.get("historical_junk"))
        extras = bitrix.get("source_extras") if isinstance(bitrix.get("source_extras"), dict) else {}
        source_channel = bitrix.get("source_channel") or extras.get("source_channel")
        if source_channel:
            source_channel = str(source_channel)
        bitrix_responsible = extras.get("responsible")
        if bitrix_responsible:
            bitrix_responsible = str(bitrix_responsible)
        roles = [str(value) for value in bitrix.get("source_roles", []) if value]
        if not original_asama and "junk" in roles:
            original_asama = "Junk Lead"
    contact_types = _contact_types(contact)
    is_agent = bool({CrmContactType.BROKER, CrmContactType.REALTOR}.intersection(contact_types))
    projects = agreement_projects
    if projects is None:
        projects = [
            row.project_group
            for row in db.scalars(
                select(CrmAgreement).where(CrmAgreement.contact_id == contact.id)
            ).all()
        ]
    return CrmContactSummary(
        id=contact.id,
        contact_type=contact.contact_type,
        contact_types=contact_types,
        record_kind=contact.record_kind,
        display_name=contact.display_name,
        organization_name=contact.organization_name,
        primary_email=contact.primary_email,
        primary_phone=displayable_phone(contact.primary_phone),
        source=contact.source,
        status=contact.status,
        lifecycle_stage=contact.lifecycle_stage,
        relationship_status=contact.relationship_status,
        relationship_strength=contact.relationship_strength,
        priority=contact.priority,
        tags=contact.tags,
        is_favorite=contact.is_favorite,
        is_pinned=contact.is_pinned,
        owner_user_id=contact.owner_user_id,
        owner_name=_resolve_owner_name(db, contact.owner_user_id) or bitrix_responsible,
        company_id=contact.company_id,
        company_name=_resolve_company_name(db, contact.company_id),
        lead_id=contact.lead_id,
        investor_id=contact.investor_id,
        last_contact_at=contact.last_contact_at,
        next_follow_up_at=contact.next_follow_up_at,
        relationship_score=rel_score,
        engagement_score=eng_score,
        junk_reason=contact.junk_reason,
        junked_at=contact.junked_at,
        review_required=bool(contact.review_required),
        is_agent=is_agent,
        has_agreements=bool(projects),
        agreement_projects=projects,
        bitrix_original_stage=original_asama,
        bitrix_historical_junk=historical_junk,
        bitrix_source_channel=source_channel,
        bitrix_responsible=bitrix_responsible,
        secondary_emails=contact.secondary_emails,
        secondary_phones=displayable_phones(contact.secondary_phones),
        whatsapp=displayable_phone(contact.whatsapp),
        job_title=contact.job_title,
        updated_at=contact.updated_at,
        created_at=contact.created_at,
    )


def serialize_contact_detail(
    db: Session,
    contact: CrmContact,
    *,
    user: User | None = None,
) -> CrmContactDetail:
    summary = serialize_contact_summary(db, contact)
    can_view_financial = user is None or user_has_permission(user, "crm", "view_financial")
    can_view_compliance = user is None or user_has_permission(user, "crm", "view_compliance")
    bitrix = (contact.metadata_json or {}).get("bitrix_import")
    bitrix_history = None
    if isinstance(bitrix, dict):
        conflicts = bitrix.get("conflicts") if isinstance(bitrix.get("conflicts"), list) else []
        bitrix_history = CrmBitrixHistory(
            external_ids=[str(value) for value in bitrix.get("external_ids", []) if value],
            source_files=[str(value) for value in bitrix.get("source_files", []) if value],
            source_roles=[str(value) for value in bitrix.get("source_roles", []) if value],
            historical_junk=bool(bitrix.get("historical_junk")),
            original_asama=str(bitrix["original_asama"]) if bitrix.get("original_asama") else None,
            mapped_sales_stage=(
                str(bitrix["mapped_sales_stage"]) if bitrix.get("mapped_sales_stage") else None
            ),
            conflict_fields=sorted(
                {
                    str(item.get("field"))
                    for item in conflicts
                    if isinstance(item, dict) and item.get("field")
                }
            ),
            warning_flags=[str(value) for value in bitrix.get("warning_flags", []) if value],
            junk_reason=contact.junk_reason
            or (str(bitrix.get("junk_reason")) if bitrix.get("junk_reason") else None),
            review_required=bool(contact.review_required),
        )
    activities = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id == contact.id,
                CrmActivity.archived_at.is_(None),
            )
            .order_by(CrmActivity.created_at.desc())
            .limit(100)
        ).all()
    )
    agreements = list(
        db.scalars(
            select(CrmAgreement)
            .where(CrmAgreement.contact_id == contact.id)
            .order_by(CrmAgreement.created_at.desc())
        ).all()
    )
    contact_types = _contact_types(contact)
    is_agent = bool(
        {CrmContactType.BROKER, CrmContactType.REALTOR}.intersection(contact_types)
    )

    detail = CrmContactDetail(
        **summary.model_dump(),
        first_name=contact.first_name,
        last_name=contact.last_name,
        department=contact.department,
        linkedin_url=contact.linkedin_url,
        website=contact.website,
        address_line1=contact.address_line1,
        address_line2=contact.address_line2,
        city=contact.city,
        state_province=contact.state_province,
        postal_code=contact.postal_code,
        country=contact.country,
        referred_by_contact_id=contact.referred_by_contact_id,
        notes=contact.notes,
        communication_prefs=contact.communication_prefs,
        compliance_data=contact.compliance_data if can_view_compliance else None,
        investment_profile=(
            CrmInvestmentProfileSchema.model_validate(contact.investment_profile)
            if contact.investment_profile
            else None
        ),
        buyer_profile=(
            CrmBuyerProfileSchema.model_validate(contact.buyer_profile) if contact.buyer_profile else None
        ),
        broker_profile=(
            CrmBrokerProfileSchema.model_validate(contact.broker_profile) if contact.broker_profile else None
        ),
        vendor_profile=(
            CrmVendorProfileSchema.model_validate(contact.vendor_profile) if contact.vendor_profile else None
        ),
        bitrix_history=bitrix_history,
        crm_activities=[
            CrmContactActivityVerification(
                id=activity.id,
                activity_type=activity.activity_type.value,
                activity_category=activity.activity_category.value,
                title=activity.title,
                description=activity.description,
                status=activity.status.value,
                imported_historical_comment=isinstance(
                    (activity.metadata_json or {}).get("bitrix_historical_comment"),
                    dict,
                ),
                due_date=activity.due_date,
                assigned_user_id=activity.assigned_user_id,
                task_status=activity.task_status.value if activity.task_status else None,
                created_at=activity.created_at,
            )
            for activity in activities
        ],
        crm_agreements=[
            CrmContactAgreementVerification(
                id=agreement.id,
                project_group=agreement.project_group,
                project_label=BITRIX_PROJECT_GROUP_LABELS.get(
                    BitrixProjectGroup(agreement.project_group),
                    agreement.project_group,
                ),
                status=agreement.status.value,
                agreement_date=agreement.agreement_date,
                unit_number=(
                    None
                    if agreement.project_group == BitrixProjectGroup.REIT.value
                    else agreement.unit_number
                ),
                investment_amount=(
                    agreement.investment_amount
                    if agreement.project_group == BitrixProjectGroup.REIT.value
                    else None
                ),
                email=(
                    (agreement.metadata_json or {}).get("contact_email")
                    if isinstance(agreement.metadata_json, dict)
                    else None
                )
                or contact.primary_email,
                phone=displayable_phone(
                    contact.primary_phone,
                    (
                        str((agreement.metadata_json or {}).get("contact_phone") or "")
                        if isinstance(agreement.metadata_json, dict)
                        else None
                    )
                    or None,
                ),
                payment_amount=_agreement_meta_text(agreement, ("payment_amount", "ödeme tutarı", "gelir")),
                deposit=_agreement_meta_text(agreement, ("deposit", "kapora")),
                purchase_price=_agreement_meta_text(
                    agreement, ("purchase_price", "agreement_price", "fiyat", "satis fiyati")
                ),
                review_required=bool(agreement.review_required),
                relationship="Anlaşma tarafı",
            )
            for agreement in agreements
        ],
        agent=(
            CrmContactAgentVerification(
                is_agent=True,
                status=contact.status.value,
                contact_types=contact_types,
                brokerage_name=contact.broker_profile.brokerage_name if contact.broker_profile else None,
                specialization=contact.broker_profile.specialization if contact.broker_profile else None,
            )
            if is_agent
            else None
        ),
    )
    return _strip_sensitive_fields(
        detail,
        can_view_financial=can_view_financial,
        can_view_compliance=can_view_compliance,
    )


def _load_contact_query():
    return select(CrmContact).options(
        selectinload(CrmContact.type_assignments),
        selectinload(CrmContact.investment_profile),
        selectinload(CrmContact.buyer_profile),
        selectinload(CrmContact.broker_profile),
        selectinload(CrmContact.vendor_profile),
        selectinload(CrmContact.tag_links).selectinload(CrmContactTag.tag),
    )


def get_contact_or_none(db: Session, contact_id: UUID) -> CrmContact | None:
    return db.scalar(_load_contact_query().where(CrmContact.id == contact_id))


def _sync_type_assignments(
    db: Session,
    contact: CrmContact,
    primary_type: CrmContactType,
    contact_types: list[CrmContactType] | None,
) -> None:
    types = contact_types or [primary_type]
    if primary_type not in types:
        types = [primary_type, *types]
    contact.type_assignments.clear()
    for ct in types:
        contact.type_assignments.append(
            CrmContactTypeAssignment(contact_type=ct, is_primary=(ct == primary_type))
        )
    contact.contact_type = primary_type


def _upsert_profile(
    db: Session,
    contact: CrmContact,
    profile_data: Any,
    model_class: type,
    attr_name: str,
) -> None:
    if profile_data is None:
        return
    existing = getattr(contact, attr_name)
    payload = profile_data.model_dump(exclude_unset=True) if hasattr(profile_data, "model_dump") else profile_data
    if existing is None:
        profile = model_class(contact_id=contact.id, **payload)
        db.add(profile)
        setattr(contact, attr_name, profile)
    else:
        for key, value in payload.items():
            setattr(existing, key, value)


def _apply_tags(db: Session, contact: CrmContact, tag_names: list[str] | None) -> None:
    if tag_names is None:
        return
    contact.tags = tag_names
    contact.tag_links.clear()
    for name in tag_names:
        normalized = name.strip()
        if not normalized:
            continue
        tag = db.scalar(select(CrmTag).where(func.lower(CrmTag.name) == normalized.lower()))
        if tag is None:
            tag = CrmTag(name=normalized)
            db.add(tag)
            db.flush()
        contact.tag_links.append(CrmContactTag(tag_id=tag.id))


def create_contact(db: Session, payload: CrmContactCreate, *, actor: User | None = None) -> CrmContact:
    del actor
    data = payload.model_dump(
        exclude={
            "contact_types",
            "investment_profile",
            "buyer_profile",
            "broker_profile",
            "vendor_profile",
            "tags",
        }
    )
    data["primary_email"] = normalize_email(data.get("primary_email"))
    data["primary_phone"] = normalize_phone(data.get("primary_phone"))
    if not data.get("display_name"):
        raise ValueError("crm.contacts.errors.display_name_required")

    contact = CrmContact(**data)
    db.add(contact)
    db.flush()
    _sync_type_assignments(db, contact, payload.contact_type, payload.contact_types)
    _apply_tags(db, contact, payload.tags)
    _upsert_profile(db, contact, payload.investment_profile, CrmContactInvestmentProfile, "investment_profile")
    _upsert_profile(db, contact, payload.buyer_profile, CrmContactBuyerProfile, "buyer_profile")
    _upsert_profile(db, contact, payload.broker_profile, CrmContactBrokerProfile, "broker_profile")
    _upsert_profile(db, contact, payload.vendor_profile, CrmContactVendorProfile, "vendor_profile")
    rel, eng = compute_relationship_scores(contact)
    contact.relationship_score = rel
    contact.engagement_score = eng
    db.flush()
    return contact


_CONTACT_FIELD_LABELS = {
    "display_name": "Ad Soyad",
    "primary_phone": "Telefon",
    "secondary_phones": "Ek telefonlar",
    "primary_email": "E-posta",
    "secondary_emails": "Ek e-postalar",
    "organization_name": "Şirket",
    "job_title": "Pozisyon",
    "status": "Durum",
    "junk_reason": "Junk sebebi",
    "next_follow_up_at": "Sonraki takip",
    "whatsapp": "WhatsApp",
    "notes": "Notlar",
}


def _format_field_value(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "—"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item)
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _normalize_optional_phone(raw: Any) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    normalized = normalize_phone(str(raw))
    if not normalized:
        raise ValueError("crm.contacts.errors.invalid_phone")
    return normalized


def _normalize_optional_email(raw: Any) -> str | None:
    if raw is None or str(raw).strip() == "":
        return None
    normalized = normalize_email(str(raw))
    if not normalized:
        raise ValueError("crm.contacts.errors.invalid_email")
    return normalized


def _record_contact_field_changes(
    db: Session,
    contact: CrmContact,
    before: dict[str, Any],
    after: dict[str, Any],
    *,
    actor: User | None,
) -> None:
    lines: list[str] = []
    for key, label in _CONTACT_FIELD_LABELS.items():
        previous = before.get(key)
        current = after.get(key)
        if previous == current:
            continue
        if key == "owner_user_id":
            previous = _resolve_owner_name(db, previous) or previous
            current = _resolve_owner_name(db, current) or current
        lines.append(f"{label}: {_format_field_value(previous)} → {_format_field_value(current)}")
    if not lines:
        return
    _append_contact_activity(
        db,
        contact,
        activity_type=CrmActivityType.SYSTEM_EVENT,
        category=CrmActivityCategory.SYSTEM,
        title="Kişi bilgileri güncellendi",
        description="\n".join(lines),
        actor=actor,
        metadata={"event": "field_change", "changes": lines},
    )


def update_contact(
    db: Session,
    contact: CrmContact,
    payload: CrmContactUpdate,
    *,
    actor: User | None = None,
) -> CrmContact:
    data = payload.model_dump(exclude_unset=True)
    for key in (
        "contact_types",
        "investment_profile",
        "buyer_profile",
        "broker_profile",
        "vendor_profile",
        "tags",
    ):
        data.pop(key, None)

    if "primary_email" in data:
        data["primary_email"] = _normalize_optional_email(data["primary_email"])
    if "primary_phone" in data:
        data["primary_phone"] = _normalize_optional_phone(data["primary_phone"])
    if "whatsapp" in data:
        data["whatsapp"] = _normalize_optional_phone(data["whatsapp"]) if data["whatsapp"] else None
    if "secondary_phones" in data and data["secondary_phones"] is not None:
        data["secondary_phones"] = [
            phone
            for phone in (_normalize_optional_phone(item) for item in data["secondary_phones"])
            if phone
        ]
    if "secondary_emails" in data and data["secondary_emails"] is not None:
        data["secondary_emails"] = [
            email
            for email in (_normalize_optional_email(item) for item in data["secondary_emails"])
            if email
        ]

    tracked_before = {key: getattr(contact, key) for key in _CONTACT_FIELD_LABELS}
    owner_changed = "owner_user_id" in data and data["owner_user_id"] != contact.owner_user_id
    previous_owner = contact.owner_user_id
    previous_owner_name = _resolve_owner_name(db, previous_owner) if owner_changed else None

    for key, value in data.items():
        setattr(contact, key, value)

    if payload.contact_type is not None or payload.contact_types is not None:
        primary = payload.contact_type or contact.contact_type
        _sync_type_assignments(db, contact, primary, payload.contact_types)
    if payload.tags is not None:
        _apply_tags(db, contact, payload.tags)
    _upsert_profile(db, contact, payload.investment_profile, CrmContactInvestmentProfile, "investment_profile")
    _upsert_profile(db, contact, payload.buyer_profile, CrmContactBuyerProfile, "buyer_profile")
    _upsert_profile(db, contact, payload.broker_profile, CrmContactBrokerProfile, "broker_profile")
    _upsert_profile(db, contact, payload.vendor_profile, CrmContactVendorProfile, "vendor_profile")

    rel, eng = compute_relationship_scores(contact)
    contact.relationship_score = rel
    contact.engagement_score = eng
    tracked_after = {key: getattr(contact, key) for key in _CONTACT_FIELD_LABELS}
    _record_contact_field_changes(db, contact, tracked_before, tracked_after, actor=actor)
    if owner_changed:
        new_name = _resolve_owner_name(db, contact.owner_user_id)
        _append_contact_activity(
            db,
            contact,
            activity_type=CrmActivityType.SYSTEM_EVENT,
            category=CrmActivityCategory.SYSTEM,
            title=f"Sorumlu: {previous_owner_name or '—'} → {new_name or '—'}",
            actor=actor,
            metadata={
                "event": "owner_assigned",
                "from_owner_user_id": str(previous_owner) if previous_owner else None,
                "to_owner_user_id": str(contact.owner_user_id) if contact.owner_user_id else None,
            },
        )
    db.flush()
    return contact


def list_crm_contacts(
    db: Session,
    *,
    search: str | None = None,
    contact_type: CrmContactType | None = None,
    contact_types: list[CrmContactType] | None = None,
    lifecycle_stage: CrmLifecycleStage | None = None,
    priority: CrmContactPriority | None = None,
    owner_user_id: UUID | None = None,
    company_id: UUID | None = None,
    status: CrmContactStatus | None = None,
    source_group: str | None = None,
    role_group: str | None = None,
    category: str | None = None,
    junk_reason: str | None = None,
    agreement_project: str | None = None,
    bitrix_list: str | None = None,
    tags: list[str] | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmContactSummary], int]:
    query = select(CrmContact).options(selectinload(CrmContact.type_assignments))

    if bitrix_list == "current_junk" or status == CrmContactStatus.ARCHIVED or junk_reason:
        include_archived = True

    if bitrix_list == "current_junk":
        query = query.where(
            CrmContact.status == CrmContactStatus.ARCHIVED,
            func.lower(CrmContact.source) == "bitrix",
            cast(CrmContact.metadata_json, String).like('%"junk"%'),
        )

    if not include_archived:
        query = query.where(CrmContact.archived_at.is_(None))

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                CrmContact.display_name.ilike(term),
                CrmContact.primary_email.ilike(term),
                CrmContact.primary_phone.ilike(term),
                CrmContact.organization_name.ilike(term),
                CrmContact.whatsapp.ilike(term),
                CrmContact.job_title.ilike(term),
                CrmContact.junk_reason.ilike(term),
                cast(CrmContact.secondary_emails, String).ilike(term),
                cast(CrmContact.secondary_phones, String).ilike(term),
            )
        )

    if contact_type is not None:
        query = query.where(CrmContact.contact_type == contact_type)

    if contact_types:
        query = query.where(
            or_(
                CrmContact.contact_type.in_(contact_types),
                CrmContact.id.in_(
                    select(CrmContactTypeAssignment.contact_id).where(
                        CrmContactTypeAssignment.contact_type.in_(contact_types)
                    )
                ),
            )
        )

    if lifecycle_stage is not None:
        query = query.where(CrmContact.lifecycle_stage == lifecycle_stage)
    if priority is not None:
        query = query.where(CrmContact.priority == priority)
    if owner_user_id is not None:
        query = query.where(CrmContact.owner_user_id == owner_user_id)
    if company_id is not None:
        query = query.where(CrmContact.company_id == company_id)
    if status is not None:
        query = query.where(CrmContact.status == status)
    if junk_reason:
        query = query.where(CrmContact.junk_reason == junk_reason)
    if source_group == "bitrix":
        query = query.where(func.lower(CrmContact.source) == "bitrix")
    elif source_group == "other":
        query = query.where(
            or_(CrmContact.source.is_(None), func.lower(CrmContact.source) != "bitrix")
        )
    agent_ids = select(CrmContactTypeAssignment.contact_id).where(
        CrmContactTypeAssignment.contact_type.in_(
            [CrmContactType.BROKER, CrmContactType.REALTOR]
        )
    )
    agent_condition = or_(
        CrmContact.contact_type.in_([CrmContactType.BROKER, CrmContactType.REALTOR]),
        CrmContact.id.in_(agent_ids),
    )
    agreement_ids = select(CrmAgreement.contact_id)
    if agreement_project:
        agreement_ids = select(CrmAgreement.contact_id).where(
            CrmAgreement.project_group == agreement_project
        )
        query = query.where(CrmContact.id.in_(agreement_ids))
    if role_group == "agent" or category == "agent":
        query = query.where(agent_condition)
    elif role_group == "other":
        query = query.where(not_(agent_condition))
    if category == "agreement":
        query = query.where(CrmContact.id.in_(select(CrmAgreement.contact_id)))
    elif category == "customer":
        query = query.where(not_(agent_condition))

    if tags:
        for tag in tags:
            query = query.where(CrmContact.tags.contains([tag]))

    sort_column = getattr(CrmContact, sort_by if sort_by in SORTABLE_COLUMNS else "updated_at")
    order = sort_column.asc() if sort_dir == "asc" else sort_column.desc()

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = max(page - 1, 0) * page_size
    rows = db.scalars(query.order_by(order).offset(offset).limit(page_size)).all()
    project_map: dict[UUID, list[str]] = defaultdict(list)
    if rows:
        for agreement in db.scalars(
            select(CrmAgreement).where(CrmAgreement.contact_id.in_([row.id for row in rows]))
        ).all():
            if agreement.project_group not in project_map[agreement.contact_id]:
                project_map[agreement.contact_id].append(agreement.project_group)
    return [
        serialize_contact_summary(db, row, agreement_projects=project_map.get(row.id, []))
        for row in rows
    ], total


def _append_contact_activity(
    db: Session,
    contact: CrmContact,
    *,
    activity_type: CrmActivityType,
    category: CrmActivityCategory,
    title: str,
    description: str | None = None,
    actor: User | None = None,
    metadata: dict[str, Any] | None = None,
) -> CrmActivity:
    activity = CrmActivity(
        entity_type=CrmActivityEntityType.CONTACT,
        entity_id=contact.id,
        activity_type=activity_type,
        activity_category=category,
        title=title,
        description=description,
        status=CrmActivityStatus.COMPLETED,
        priority=CrmActivityPriority.MEDIUM,
        visibility=CrmActivityVisibility.ORGANIZATION,
        owner_id=actor.id if actor else contact.owner_user_id,
        created_by=actor.id if actor else None,
        updated_by=actor.id if actor else None,
        metadata_json=metadata,
        completed_at=datetime.now(UTC),
    )
    db.add(activity)
    db.flush()
    return activity


def archive_contact(
    db: Session,
    contact: CrmContact,
    *,
    junk_reason: str | None = None,
    actor: User | None = None,
) -> CrmContact:
    reason = (junk_reason or contact.junk_reason or "").strip() or None
    contact.archived_at = datetime.now(UTC)
    contact.status = CrmContactStatus.ARCHIVED
    if reason:
        contact.junk_reason = reason
        if contact.junked_at is None:
            contact.junked_at = contact.archived_at
    _append_contact_activity(
        db,
        contact,
        activity_type=CrmActivityType.SYSTEM_EVENT,
        category=CrmActivityCategory.SYSTEM,
        title=f"Durum Junk{': ' + reason if reason else ''}",
        description=reason,
        actor=actor,
        metadata={
            "event": "status_junk",
            "junk_reason": reason,
            "actor_user_id": str(actor.id) if actor else None,
        },
    )
    db.flush()
    return contact


def restore_contact(db: Session, contact: CrmContact, *, actor: User | None = None) -> CrmContact:
    previous_reason = contact.junk_reason
    contact.archived_at = None
    if contact.status == CrmContactStatus.ARCHIVED:
        contact.status = CrmContactStatus.ACTIVE
    _append_contact_activity(
        db,
        contact,
        activity_type=CrmActivityType.SYSTEM_EVENT,
        category=CrmActivityCategory.SYSTEM,
        title="Durum Aktif",
        description=f"Önceki Junk sebebi korundu: {previous_reason}" if previous_reason else None,
        actor=actor,
        metadata={
            "event": "status_active",
            "previous_junk_reason": previous_reason,
        },
    )
    db.flush()
    return contact


def change_contact_status(
    db: Session,
    contact: CrmContact,
    *,
    status: CrmContactStatus,
    junk_reason: str | None = None,
    next_follow_up_at: datetime | None = None,
    actor: User | None = None,
) -> CrmContact:
    if status == CrmContactStatus.ARCHIVED:
        reason = (junk_reason or contact.junk_reason or "").strip()
        if not reason:
            raise ValueError("crm.contacts.errors.junk_reason_required")
        if contact.status == CrmContactStatus.ARCHIVED:
            if contact.junk_reason != reason:
                contact.junk_reason = reason
                if contact.junked_at is None:
                    contact.junked_at = datetime.now(UTC)
                _append_contact_activity(
                    db,
                    contact,
                    activity_type=CrmActivityType.SYSTEM_EVENT,
                    category=CrmActivityCategory.SYSTEM,
                    title=f"Junk sebebi güncellendi: {reason}",
                    description=reason,
                    actor=actor,
                    metadata={"event": "junk_reason_updated", "junk_reason": reason},
                )
            if next_follow_up_at is not None:
                contact.next_follow_up_at = next_follow_up_at
            db.flush()
            return contact
        return archive_contact(db, contact, junk_reason=reason, actor=actor)
    if status == CrmContactStatus.ACTIVE:
        if next_follow_up_at is not None:
            contact.next_follow_up_at = next_follow_up_at
        return restore_contact(db, contact, actor=actor)
    previous = contact.status
    contact.status = status
    if next_follow_up_at is not None:
        contact.next_follow_up_at = next_follow_up_at
    _append_contact_activity(
        db,
        contact,
        activity_type=CrmActivityType.SYSTEM_EVENT,
        category=CrmActivityCategory.SYSTEM,
        title=f"Durum: {previous.value} → {status.value}",
        actor=actor,
        metadata={"event": "status_change", "from": previous.value, "to": status.value},
    )
    db.flush()
    return contact


def assign_contact_owner(
    db: Session,
    contact: CrmContact,
    *,
    owner_user_id: UUID,
    actor: User | None = None,
) -> CrmContact:
    previous = contact.owner_user_id
    previous_name = _resolve_owner_name(db, previous)
    contact.owner_user_id = owner_user_id
    owner_name = _resolve_owner_name(db, owner_user_id)
    _append_contact_activity(
        db,
        contact,
        activity_type=CrmActivityType.SYSTEM_EVENT,
        category=CrmActivityCategory.SYSTEM,
        title=f"Sorumlu: {previous_name or '—'} → {owner_name or '—'}",
        actor=actor,
        metadata={
            "event": "owner_assigned",
            "from_owner_user_id": str(previous) if previous else None,
            "to_owner_user_id": str(owner_user_id),
        },
    )
    db.flush()
    return contact


def delete_contact(db: Session, contact: CrmContact) -> None:
    db.delete(contact)
    db.flush()


def check_duplicates(db: Session, payload: CrmDuplicateCheckRequest) -> list[CrmDuplicateMatch]:
    matches: list[CrmDuplicateMatch] = []
    seen: set[UUID] = set()
    if payload.exclude_contact_id:
        seen.add(payload.exclude_contact_id)

    def _add(contact: CrmContact, reason: str, score: float) -> None:
        if contact.id in seen:
            return
        seen.add(contact.id)
        matches.append(
            CrmDuplicateMatch(
                contact_id=contact.id,
                display_name=contact.display_name,
                match_reason=reason,
                match_score=score,
            )
        )

    parsed_phone = parse_phone(payload.primary_phone)
    if parsed_phone is not None:
        phone_keys = {parsed_phone.match_key, parsed_phone.e164, parsed_phone.digits}
        if parsed_phone.e164 is None and len(parsed_phone.digits) == 10:
            phone_keys.update({f"+1{parsed_phone.digits}", f"+90{parsed_phone.digits}"})
        elif parsed_phone.country == "US" and len(parsed_phone.digits) >= 10:
            phone_keys.add(f"d:{parsed_phone.digits[-10:]}")
        phone_keys.discard(None)
        for row in db.scalars(
            select(CrmContact).where(CrmContact.primary_phone.in_(list(phone_keys)))
        ).all():
            _add(row, "phone", 1.0)

    email = normalize_email(payload.primary_email)
    if email:
        for row in db.scalars(select(CrmContact).where(CrmContact.primary_email == email)).all():
            _add(row, "email", 1.0)

    if payload.linkedin_url:
        url = payload.linkedin_url.strip().lower()
        for row in db.scalars(
            select(CrmContact).where(func.lower(CrmContact.linkedin_url) == url)
        ).all():
            _add(row, "linkedin", 0.9)

    whatsapp = normalize_phone(payload.whatsapp)
    if whatsapp:
        for row in db.scalars(select(CrmContact).where(CrmContact.whatsapp == whatsapp)).all():
            _add(row, "whatsapp", 0.9)

    if payload.display_name and payload.organization_name:
        name = payload.display_name.strip().lower()
        org = payload.organization_name.strip().lower()
        for row in db.scalars(
            select(CrmContact).where(
                func.lower(CrmContact.display_name) == name,
                func.lower(CrmContact.organization_name) == org,
            )
        ).all():
            _add(row, "name_company", 0.85)

    if parsed_phone is None and not email and payload.display_name:
        name_key = normalize_full_name(payload.display_name)
        if name_key:
            for row in db.scalars(select(CrmContact)).all():
                if normalize_full_name(row.display_name) == name_key:
                    _add(row, "name_review", 0.4)

    matches.sort(key=lambda item: item.match_score, reverse=True)
    return matches


def merge_contacts(
    db: Session,
    *,
    survivor: CrmContact,
    merged: CrmContact,
    actor: User | None,
) -> CrmContact:
    if survivor.id == merged.id:
        raise ValueError("crm.contacts.errors.cannot_merge_self")

    snapshot = serialize_contact_detail(db, merged, user=actor).model_dump(mode="json")
    history = CrmContactMergeHistory(
        survivor_contact_id=survivor.id,
        merged_contact_id=merged.id,
        merged_snapshot=snapshot,
        merged_by_user_id=actor.id if actor else None,
    )
    db.add(history)

    if not survivor.primary_email and merged.primary_email:
        survivor.primary_email = merged.primary_email
    if not survivor.primary_phone and merged.primary_phone:
        survivor.primary_phone = merged.primary_phone
    if not survivor.linkedin_url and merged.linkedin_url:
        survivor.linkedin_url = merged.linkedin_url
    if merged.notes:
        survivor.notes = (
            f"{survivor.notes}\n\n--- Merged ---\n{merged.notes}" if survivor.notes else merged.notes
        )

    merged_tags = set(survivor.tags or [])
    merged_tags.update(merged.tags or [])
    survivor.tags = list(merged_tags)

    merged.archived_at = datetime.now(UTC)
    merged.status = CrmContactStatus.ARCHIVED
    db.flush()
    return survivor


def bulk_update_contacts(db: Session, payload: CrmContactBulkUpdateRequest) -> int:
    count = 0
    for contact_id in payload.contact_ids:
        contact = get_contact_or_none(db, contact_id)
        if contact is None:
            continue
        if payload.owner_user_id is not None:
            contact.owner_user_id = payload.owner_user_id
        if payload.lifecycle_stage is not None:
            contact.lifecycle_stage = payload.lifecycle_stage
        if payload.priority is not None:
            contact.priority = payload.priority
        if payload.tags is not None:
            _apply_tags(db, contact, payload.tags)
        if payload.archive:
            archive_contact(db, contact)
        count += 1
    db.flush()
    return count


def import_contacts(
    db: Session,
    payload: CrmContactImportRequest,
    *,
    actor: User | None = None,
) -> CrmContactImportResponse:
    del actor
    result = CrmContactImportResponse()
    for index, row in enumerate(payload.rows, start=1):
        try:
            _import_row(db, row, payload.mode, result)
        except ValueError as exc:
            result.errors.append(f"Row {index}: {exc}")
    db.flush()
    return result


def _maybe_import_attribution(db: Session, row: CrmContactImportRow, email: str | None) -> None:
    has_campaign = row.campaign_id or row.campaign_name
    has_utm = any([row.utm_source, row.utm_medium, row.utm_campaign, row.utm_term, row.utm_content])
    if not has_campaign and not has_utm:
        return
    if not email:
        raise ValueError("Attribution import requires primary_email to link lead")
    contact = db.scalar(select(CrmContact).where(CrmContact.primary_email == email))
    if contact is None or contact.lead_id is None:
        return
    from investhome_api.schemas.marketing_performance import LeadAttributionFields
    from investhome_api.services.marketing.lead_attribution_service import (
        resolve_campaign_by_name_or_id,
        upsert_lead_attribution,
    )

    campaign_id = None
    if row.campaign_id or row.campaign_name:
        campaign_id = resolve_campaign_by_name_or_id(db, row.campaign_id or row.campaign_name or "")
    upsert_lead_attribution(
        db,
        contact.lead_id,
        LeadAttributionFields(
            campaign_id=campaign_id,
            attribution_source="import",
            utm_source=row.utm_source,
            utm_medium=row.utm_medium,
            utm_campaign=row.utm_campaign,
            utm_term=row.utm_term,
            utm_content=row.utm_content,
        ),
        default_source="import",
    )


def _import_row(
    db: Session,
    row: CrmContactImportRow,
    mode: str,
    result: CrmContactImportResponse,
) -> None:
    email = normalize_email(row.primary_email)
    existing = None
    if email:
        existing = db.scalar(select(CrmContact).where(CrmContact.primary_email == email))

    if existing and mode == "skip":
        result.skipped += 1
        return
    if existing and mode == "update":
        update_contact(
            db,
            existing,
            CrmContactUpdate(
                display_name=row.display_name,
                contact_type=row.contact_type,
                primary_phone=row.primary_phone,
                organization_name=row.organization_name,
                tags=row.tags,
            ),
        )
        result.updated += 1
        return
    if existing and mode == "merge":
        result.skipped += 1
        return
    if existing and mode == "create":
        result.errors.append(f"Duplicate email: {email}")
        result.skipped += 1
        return

    create_contact(
        db,
        CrmContactCreate(
            display_name=row.display_name,
            contact_type=row.contact_type,
            primary_email=row.primary_email,
            primary_phone=row.primary_phone,
            organization_name=row.organization_name,
            tags=row.tags,
        ),
    )
    result.created += 1
    _maybe_import_attribution(db, row, email)


def export_contacts_csv(db: Session, *, include_archived: bool = False) -> str:
    items, _ = list_crm_contacts(db, page=1, page_size=10_000, include_archived=include_archived)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "display_name",
            "contact_type",
            "organization_name",
            "primary_email",
            "primary_phone",
            "lifecycle_stage",
            "relationship_status",
            "priority",
            "owner_user_id",
            "status",
            "tags",
            "relationship_score",
            "engagement_score",
            "updated_at",
        ]
    )
    for item in items:
        writer.writerow(
            [
                str(item.id),
                item.display_name,
                item.contact_type.value,
                item.organization_name or "",
                item.primary_email or "",
                item.primary_phone or "",
                item.lifecycle_stage.value,
                item.relationship_status.value,
                item.priority.value,
                str(item.owner_user_id) if item.owner_user_id else "",
                item.status.value,
                ",".join(item.tags or []),
                item.relationship_score,
                item.engagement_score,
                item.updated_at.isoformat(),
            ]
        )
    return buffer.getvalue()


def get_bitrix_verification_summary(db: Session) -> CrmBitrixVerificationSummary:
    bitrix_contacts = list(
        db.scalars(
            select(CrmContact).where(func.lower(CrmContact.source) == "bitrix")
        ).all()
    )
    agreement_rows = list(
        db.scalars(select(CrmAgreement).where(CrmAgreement.source == "bitrix")).all()
    )
    agreements_by_project: dict[str, int] = {}
    for agreement in agreement_rows:
        agreements_by_project[agreement.project_group] = (
            agreements_by_project.get(agreement.project_group, 0) + 1
        )
    imported_comments = sum(
        1
        for activity in db.scalars(select(CrmActivity)).all()
        if isinstance(
            (activity.metadata_json or {}).get("bitrix_historical_comment"),
            dict,
        )
    )
    return CrmBitrixVerificationSummary(
        total_contacts=db.query(CrmContact).count(),
        bitrix_contacts=len(bitrix_contacts),
        non_bitrix_contacts=db.query(CrmContact).count() - len(bitrix_contacts),
        active_bitrix=sum(
            contact.status == CrmContactStatus.ACTIVE for contact in bitrix_contacts
        ),
        archived_bitrix=sum(
            contact.status == CrmContactStatus.ARCHIVED for contact in bitrix_contacts
        ),
        bitrix_with_phone=sum(bool(contact.primary_phone) for contact in bitrix_contacts),
        bitrix_with_email=sum(bool(contact.primary_email) for contact in bitrix_contacts),
        bitrix_with_external_id=sum(
            bool(
                ((contact.metadata_json or {}).get("bitrix_import") or {}).get(
                    "external_ids"
                )
            )
            for contact in bitrix_contacts
        ),
        imported_historical_comments=imported_comments,
        imported_agents=sum(
            isinstance((contact.metadata_json or {}).get("bitrix_agent"), dict)
            for contact in bitrix_contacts
        ),
        imported_agreements=len(agreement_rows),
        agreements_by_project=agreements_by_project,
    )


def export_bitrix_verification_csv(db: Session) -> str:
    contacts = list(
        db.scalars(
            select(CrmContact)
            .where(func.lower(CrmContact.source) == "bitrix")
            .options(selectinload(CrmContact.type_assignments))
            .order_by(CrmContact.display_name.asc(), CrmContact.id.asc())
        ).all()
    )
    contact_ids = {contact.id for contact in contacts}
    comment_contact_ids = {
        activity.entity_id
        for activity in db.scalars(
            select(CrmActivity).where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
            )
        ).all()
        if isinstance(
            (activity.metadata_json or {}).get("bitrix_historical_comment"),
            dict,
        )
    }
    agreement_groups: dict[UUID, set[str]] = {}
    for agreement in db.scalars(
        select(CrmAgreement).where(CrmAgreement.contact_id.in_(contact_ids))
    ).all():
        agreement_groups.setdefault(agreement.contact_id, set()).add(
            agreement.project_group
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "canonical_contact_id",
            "name",
            "phone",
            "email",
            "current_status",
            "source",
            "contact_roles",
            "bitrix_external_ids",
            "has_imported_comment",
            "agreement_project_groups",
            "agent",
        ]
    )
    for contact in contacts:
        metadata = (contact.metadata_json or {}).get("bitrix_import")
        external_ids = (
            [str(value) for value in metadata.get("external_ids", []) if value]
            if isinstance(metadata, dict)
            else []
        )
        roles = _contact_types(contact)
        is_agent = bool(
            {CrmContactType.BROKER, CrmContactType.REALTOR}.intersection(roles)
        )
        writer.writerow(
            [
                str(contact.id),
                contact.display_name,
                contact.primary_phone or "",
                contact.primary_email or "",
                contact.status.value,
                contact.source or "",
                ";".join(role.value for role in roles),
                ";".join(sorted(external_ids)),
                "yes" if contact.id in comment_contact_ids else "no",
                ";".join(sorted(agreement_groups.get(contact.id, set()))),
                "yes" if is_agent else "no",
            ]
        )
    return buffer.getvalue()


def get_contact_timeline(
    db: Session,
    contact_id: UUID,
    user: User,
    *,
    limit: int = 80,
) -> list[CrmContactTimelineEntry]:
    from investhome_api.services.activity_service import list_entity_activity

    entries: list[CrmContactTimelineEntry] = []
    activities = list(
        db.scalars(
            select(CrmActivity)
            .where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id == contact_id,
                CrmActivity.archived_at.is_(None),
            )
            .order_by(CrmActivity.created_at.desc())
            .limit(limit)
        ).all()
    )
    for activity in activities:
        metadata = activity.metadata_json if isinstance(activity.metadata_json, dict) else None
        imported = isinstance((metadata or {}).get("bitrix_historical_comment"), dict)
        summary = activity.description or activity.summary
        entries.append(
            CrmContactTimelineEntry(
                id=str(activity.id),
                source="crm_activity",
                activity_type=activity.activity_type.value,
                title=(
                    "Tarihsel Bitrix yorumu"
                    if imported
                    else activity.title
                ),
                summary=summary,
                status=activity.status.value,
                actor_name=_resolve_owner_name(
                    db, activity.created_by or activity.owner_id or activity.assigned_user_id
                ),
                created_at=activity.start_date or activity.created_at,
                is_system_event=activity.activity_type
                in {CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT},
                imported_historical_comment=imported,
                metadata=metadata,
            )
        )

    contact = get_contact_or_none(db, contact_id)
    if contact is not None:
        for agreement in db.scalars(
            select(CrmAgreement).where(CrmAgreement.contact_id == contact.id)
        ).all():
            label = BITRIX_PROJECT_GROUP_LABELS.get(
                BitrixProjectGroup(agreement.project_group),
                agreement.project_group,
            )
            entries.append(
                CrmContactTimelineEntry(
                    id=f"agreement-{agreement.id}",
                    source="crm_agreement",
                    activity_type="contract_signed",
                    title=f"Anlaşma: {label}",
                    summary=f"{agreement.status.value} · Anlaşma tarafı",
                    status=agreement.status.value,
                    created_at=agreement.created_at,
                    is_system_event=True,
                    metadata={
                        "project_group": agreement.project_group,
                        "agreement_date": str(agreement.agreement_date)
                        if agreement.agreement_date
                        else None,
                    },
                )
            )
        if contact.next_follow_up_at:
            entries.append(
                CrmContactTimelineEntry(
                    id=f"follow-up-{contact.id}",
                    source="crm_contact",
                    activity_type="follow_up",
                    title="Sonraki iletişim",
                    summary=contact.next_follow_up_at.isoformat(),
                    created_at=contact.next_follow_up_at,
                    is_system_event=False,
                    metadata={"next_follow_up_at": contact.next_follow_up_at.isoformat()},
                )
            )

    logs = list_entity_activity(
        db,
        user,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact_id,
        limit=limit,
    )
    seen_log_keys = {
        (entry.action, entry.created_at.isoformat())
        for entry in entries
        if entry.action
    }
    audit_titles = {
        "activity.crm_contact.created": "Kişi oluşturuldu",
        "activity.crm_contact.archived": "Kişi arşivlendi",
        "activity.crm_contact.restored": "Kişi geri alındı",
    }
    for log in logs:
        if log.description_key in {
            "activity.crm_contact.updated",
            "activity.crm_contact.merged",
        }:
            continue
        key = (log.action.value, log.created_at.isoformat())
        if key in seen_log_keys:
            continue
        entries.append(
            CrmContactTimelineEntry(
                id=f"log-{log.id}",
                source="audit_log",
                activity_type="system_event",
                title=audit_titles.get(log.description_key, log.description_key),
                actor_name=log.actor_name,
                created_at=log.created_at,
                is_system_event=True,
                action=log.action.value,
                description_key=log.description_key,
            )
        )

    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries[:limit]


def list_junk_reasons(db: Session) -> list[CrmJunkReasonCount]:
    rows = db.execute(
        select(CrmContact.junk_reason, func.count())
        .where(CrmContact.junk_reason.is_not(None), CrmContact.junk_reason != "")
        .group_by(CrmContact.junk_reason)
        .order_by(func.count().desc(), CrmContact.junk_reason.asc())
    ).all()
    return [CrmJunkReasonCount(reason=str(reason), count=int(count)) for reason, count in rows]


def get_contact_relationships(db: Session, contact: CrmContact) -> list[CrmContactSummary]:
    if contact.referred_by_contact_id:
        referred = get_contact_or_none(db, contact.referred_by_contact_id)
        if referred:
            return [serialize_contact_summary(db, referred)]
    rows = db.scalars(
        select(CrmContact)
        .options(selectinload(CrmContact.type_assignments))
        .where(
            CrmContact.referred_by_contact_id == contact.id,
            CrmContact.archived_at.is_(None),
        )
        .limit(20)
    ).all()
    return [serialize_contact_summary(db, row) for row in rows]


def list_saved_views(db: Session, user: User) -> list[CrmContactSavedViewResponse]:
    rows = db.scalars(
        select(CrmContactSavedView).where(
            or_(
                CrmContactSavedView.owner_user_id == user.id,
                CrmContactSavedView.is_shared.is_(True),
            )
        )
    ).all()
    return [CrmContactSavedViewResponse.model_validate(row) for row in rows]


def create_saved_view(
    db: Session,
    user: User,
    payload: CrmContactSavedViewCreate,
) -> CrmContactSavedView:
    if payload.is_default:
        db.execute(
            select(CrmContactSavedView).where(
                CrmContactSavedView.owner_user_id == user.id,
                CrmContactSavedView.is_default.is_(True),
            )
        )
        for existing in db.scalars(
            select(CrmContactSavedView).where(
                CrmContactSavedView.owner_user_id == user.id,
                CrmContactSavedView.is_default.is_(True),
            )
        ).all():
            existing.is_default = False

    view = CrmContactSavedView(owner_user_id=user.id, **payload.model_dump())
    db.add(view)
    db.flush()
    return view


def update_saved_view(
    db: Session,
    view: CrmContactSavedView,
    payload: CrmContactSavedViewUpdate,
) -> CrmContactSavedView:
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(view, key, value)
    db.flush()
    return view


def delete_saved_view(db: Session, view: CrmContactSavedView) -> None:
    db.delete(view)
    db.flush()


# Dashboard helpers (backward compat)
def count_active_contacts(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(
                CrmContact.archived_at.is_(None),
                CrmContact.status != CrmContactStatus.ARCHIVED,
            )
        )
        or 0
    )


def count_contacts_with_email(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(
                CrmContact.archived_at.is_(None),
                CrmContact.primary_email.is_not(None),
                CrmContact.primary_email != "",
            )
        )
        or 0
    )


def count_contacts_with_phone(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(
                CrmContact.archived_at.is_(None),
                CrmContact.primary_phone.is_not(None),
                CrmContact.primary_phone != "",
            )
        )
        or 0
    )


def count_favorite_contacts(db: Session) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CrmContact)
            .where(
                CrmContact.archived_at.is_(None),
                CrmContact.is_favorite.is_(True),
            )
        )
        or 0
    )


def fetch_recent_contacts(db: Session, *, limit: int = 10) -> list[CrmContactSummary]:
    rows = db.scalars(
        _load_contact_query()
        .where(CrmContact.archived_at.is_(None))
        .order_by(CrmContact.created_at.desc())
        .limit(limit)
    ).all()
    return [serialize_contact_summary(db, row) for row in rows]


def fetch_recently_updated_contacts(db: Session, *, limit: int = 10) -> list[CrmContactSummary]:
    rows = db.scalars(
        _load_contact_query()
        .where(CrmContact.archived_at.is_(None))
        .order_by(CrmContact.updated_at.desc())
        .limit(limit)
    ).all()
    return [serialize_contact_summary(db, row) for row in rows]


def fetch_favorite_contacts(db: Session, *, limit: int = 10) -> list[CrmContactSummary]:
    rows = db.scalars(
        _load_contact_query()
        .where(
            CrmContact.archived_at.is_(None),
            CrmContact.is_favorite.is_(True),
        )
        .order_by(CrmContact.display_name.asc())
        .limit(limit)
    ).all()
    return [serialize_contact_summary(db, row) for row in rows]


def fetch_pinned_companies(db: Session, *, limit: int = 10) -> list[CrmContact]:
    from investhome_api.models.crm_contact import CrmRecordKind

    return list(
        db.scalars(
            _load_contact_query()
            .where(
                CrmContact.archived_at.is_(None),
                CrmContact.is_pinned.is_(True),
                CrmContact.record_kind == CrmRecordKind.ORGANIZATION,
            )
            .order_by(CrmContact.display_name.asc())
            .limit(limit)
        ).all()
    )


def serialize_contact(contact: CrmContact) -> CrmContactSummary:
    """Legacy alias used by dashboard — requires db session via contact attributes only."""
    rel, eng = compute_relationship_scores(contact)
    return CrmContactSummary(
        id=contact.id,
        contact_type=contact.contact_type,
        contact_types=_contact_types(contact),
        record_kind=contact.record_kind,
        display_name=contact.display_name,
        organization_name=contact.organization_name,
        primary_email=contact.primary_email,
        primary_phone=displayable_phone(contact.primary_phone),
        status=contact.status,
        lifecycle_stage=contact.lifecycle_stage,
        relationship_status=contact.relationship_status,
        relationship_strength=contact.relationship_strength,
        priority=contact.priority,
        tags=contact.tags,
        is_favorite=contact.is_favorite,
        is_pinned=contact.is_pinned,
        owner_user_id=contact.owner_user_id,
        lead_id=contact.lead_id,
        investor_id=contact.investor_id,
        company_id=contact.company_id,
        last_contact_at=contact.last_contact_at,
        next_follow_up_at=contact.next_follow_up_at,
        relationship_score=rel,
        engagement_score=eng,
        updated_at=contact.updated_at,
        created_at=contact.created_at,
    )
