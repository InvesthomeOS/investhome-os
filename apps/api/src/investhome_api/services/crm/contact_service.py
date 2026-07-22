"""CRM contact management service."""

from __future__ import annotations

import csv
import io
import re
from datetime import UTC, datetime
from math import ceil
from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, or_, select
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
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import (
    CrmBrokerProfileSchema,
    CrmBuyerProfileSchema,
    CrmContactBulkUpdateRequest,
    CrmContactCreate,
    CrmContactDetail,
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
    CrmVendorProfileSchema,
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
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if not digits:
        return None
    if len(digits) == 10:
        return f"+1{digits}"
    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return f"+{digits}" if not value.strip().startswith("+") else f"+{digits.lstrip('+')}"


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
) -> CrmContactSummary:
    rel_score, eng_score = compute_relationship_scores(contact)
    return CrmContactSummary(
        id=contact.id,
        contact_type=contact.contact_type,
        contact_types=_contact_types(contact),
        record_kind=contact.record_kind,
        display_name=contact.display_name,
        organization_name=contact.organization_name,
        primary_email=contact.primary_email,
        primary_phone=contact.primary_phone,
        status=contact.status,
        lifecycle_stage=contact.lifecycle_stage,
        relationship_status=contact.relationship_status,
        relationship_strength=contact.relationship_strength,
        priority=contact.priority,
        tags=contact.tags,
        is_favorite=contact.is_favorite,
        is_pinned=contact.is_pinned,
        owner_user_id=contact.owner_user_id,
        owner_name=_resolve_owner_name(db, contact.owner_user_id),
        company_id=contact.company_id,
        company_name=_resolve_company_name(db, contact.company_id),
        lead_id=contact.lead_id,
        investor_id=contact.investor_id,
        last_contact_at=contact.last_contact_at,
        next_follow_up_at=contact.next_follow_up_at,
        relationship_score=rel_score,
        engagement_score=eng_score,
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

    detail = CrmContactDetail(
        **summary.model_dump(),
        first_name=contact.first_name,
        last_name=contact.last_name,
        job_title=contact.job_title,
        department=contact.department,
        secondary_emails=contact.secondary_emails,
        secondary_phones=contact.secondary_phones,
        linkedin_url=contact.linkedin_url,
        whatsapp=contact.whatsapp,
        website=contact.website,
        address_line1=contact.address_line1,
        address_line2=contact.address_line2,
        city=contact.city,
        state_province=contact.state_province,
        postal_code=contact.postal_code,
        country=contact.country,
        source=contact.source,
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


def update_contact(db: Session, contact: CrmContact, payload: CrmContactUpdate) -> CrmContact:
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
        data["primary_email"] = normalize_email(data["primary_email"])
    if "primary_phone" in data:
        data["primary_phone"] = normalize_phone(data["primary_phone"])

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
    tags: list[str] | None = None,
    include_archived: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmContactSummary], int]:
    query = select(CrmContact).options(selectinload(CrmContact.type_assignments))

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
            )
        )

    if contact_type is not None:
        query = query.where(CrmContact.contact_type == contact_type)

    if contact_types:
        query = query.join(CrmContactTypeAssignment).where(
            CrmContactTypeAssignment.contact_type.in_(contact_types)
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

    if tags:
        for tag in tags:
            query = query.where(CrmContact.tags.contains([tag]))

    sort_column = getattr(CrmContact, sort_by if sort_by in SORTABLE_COLUMNS else "updated_at")
    order = sort_column.asc() if sort_dir == "asc" else sort_column.desc()

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = max(page - 1, 0) * page_size
    rows = db.scalars(query.order_by(order).offset(offset).limit(page_size)).all()
    return [serialize_contact_summary(db, row) for row in rows], total


def archive_contact(db: Session, contact: CrmContact) -> CrmContact:
    contact.archived_at = datetime.now(UTC)
    contact.status = CrmContactStatus.ARCHIVED
    db.flush()
    return contact


def restore_contact(db: Session, contact: CrmContact) -> CrmContact:
    contact.archived_at = None
    if contact.status == CrmContactStatus.ARCHIVED:
        contact.status = CrmContactStatus.ACTIVE
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

    email = normalize_email(payload.primary_email)
    if email:
        for row in db.scalars(select(CrmContact).where(CrmContact.primary_email == email)).all():
            _add(row, "email", 1.0)

    phone = normalize_phone(payload.primary_phone)
    if phone:
        for row in db.scalars(select(CrmContact).where(CrmContact.primary_phone == phone)).all():
            _add(row, "phone", 0.95)

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


def get_contact_timeline(
    db: Session,
    contact_id: UUID,
    user: User,
    *,
    limit: int = 50,
) -> list[CrmContactTimelineEntry]:
    from investhome_api.services.activity_service import list_entity_activity

    activities = list_entity_activity(
        db,
        user,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact_id,
        limit=limit,
    )
    return [
        CrmContactTimelineEntry(
            id=entry.id,
            action=entry.action.value,
            description_key=entry.description_key,
            actor_name=entry.actor_name,
            created_at=entry.created_at,
            metadata=entry.metadata_json,
        )
        for entry in activities
    ]


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
        primary_phone=contact.primary_phone,
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
