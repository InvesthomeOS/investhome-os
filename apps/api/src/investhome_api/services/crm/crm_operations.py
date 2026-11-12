"""Shared CRM person, agent, agency-customer, and agreement conversion flows.

One person stays one CrmContact. Lead stage stays on the Lead. Agreement stage
stays on the Agreement. These helpers reuse the existing contact and agreement
services instead of a second CRM model.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant, CrmAgreementStatus
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.crm_relationship import (
    CrmRelationship,
    CrmRelationshipCategory,
    CrmRelationshipDirection,
    CrmRelationshipEntityType,
    CrmRelationshipStatus,
    CrmRelationshipStrength,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_contacts import CrmContactCreate, CrmDuplicateCheckRequest
from investhome_api.services.activity_service import log_activity
from investhome_api.services.crm.agreement_service import (
    create_manual_agreement,
    normalize_agreement_stage,
    set_agreement_stage,
)
from investhome_api.services.crm.agreement_service import _display_stage, _meta
from investhome_api.services.crm.contact_service import check_duplicates, create_contact
from investhome_api.services.crm.crm_lead_service import (
    LeadValidationError,
    _link_manual_lead_contact,
    _person_matches,
    _to_detail,
    _unique_person_matches,
    stage_of,
)


class CrmOperationError(ValueError):
    pass


def _blank(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def ensure_person_contact(
    db: Session,
    *,
    actor: User | None,
    contact_id: UUID | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    source: str | None = None,
    address_line1: str | None = None,
    city: str | None = None,
    state_province: str | None = None,
    country: str | None = None,
    language: str | None = None,
    organization_name: str | None = None,
    job_title: str | None = None,
    notes: str | None = None,
    owner_user_id: UUID | None = None,
    next_follow_up_at: datetime | None = None,
    contact_type: CrmContactType = CrmContactType.PROSPECT,
    contact_types: list[CrmContactType] | None = None,
    status: CrmContactStatus = CrmContactStatus.PROSPECT,
) -> tuple[CrmContact, bool]:
    """Reuse a selected or exactly matched Contact. Create one only when none exists."""
    if contact_id is not None:
        contact = db.get(CrmContact, contact_id)
        if contact is None or contact.archived_at is not None:
            raise CrmOperationError("Seçilen kişi bulunamadı")
        return contact, True

    display = " ".join(part for part in (_blank(first_name), _blank(last_name)) if part).strip()
    matches = _unique_person_matches(
        _person_matches(db, email=_blank(email), phone=_blank(phone), name=display or None)
    )
    strong = check_duplicates(
        db,
        CrmDuplicateCheckRequest(primary_email=_blank(email), primary_phone=_blank(phone), display_name=display or None),
    )
    strong_ids = {item.contact_id for item in strong if item.match_reason in {"phone", "email"} and item.match_score >= 1}
    exact = [item for item in matches if item.id in strong_ids] or matches
    if len(exact) > 1:
        raise CrmOperationError("Birden fazla kişi eşleşti. Mevcut kişiyi seçin.")
    if len(exact) == 1:
        contact = db.get(CrmContact, exact[0].id)
        if contact is None or contact.archived_at is not None:
            raise CrmOperationError("Seçilen kişi bulunamadı")
        return contact, True
    if not display and not _blank(phone) and not _blank(email):
        raise CrmOperationError("Ad, telefon veya e-posta gerekli")
    prefs = {"language": language.strip()} if _blank(language) else None
    try:
        contact = create_contact(
            db,
            CrmContactCreate(
                contact_type=contact_type,
                contact_types=contact_types or [contact_type],
                record_kind=CrmRecordKind.PERSON,
                display_name=display or _blank(email) or _blank(phone) or "Adsız kişi",
                first_name=_blank(first_name),
                last_name=_blank(last_name),
                primary_email=_blank(email),
                primary_phone=_blank(phone),
                source=_blank(source),
                address_line1=_blank(address_line1),
                city=_blank(city),
                state_province=_blank(state_province),
                country=_blank(country),
                organization_name=_blank(organization_name),
                job_title=_blank(job_title),
                notes=_blank(notes),
                owner_user_id=owner_user_id,
                next_follow_up_at=next_follow_up_at,
                communication_prefs=prefs,
                lifecycle_stage=CrmLifecycleStage.NEW,
                status=status,
            ),
            actor=actor,
        )
    except ValueError as exc:
        raise CrmOperationError(str(exc)) from exc
    return contact, False


def _mark_metadata(contact: CrmContact, values: dict[str, Any]) -> None:
    meta = dict(contact.metadata_json) if isinstance(contact.metadata_json, dict) else {}
    crm = dict(meta.get("crm") or {}) if isinstance(meta.get("crm"), dict) else {}
    crm.update(values)
    meta["crm"] = crm
    contact.metadata_json = meta


def _ensure_relationship(
    db: Session,
    *,
    source_id: UUID,
    target_id: UUID,
    relationship_type: str,
    actor: User | None,
) -> None:
    existing = db.scalar(
        select(CrmRelationship.id).where(
            CrmRelationship.source_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.source_entity_id == source_id,
            CrmRelationship.target_entity_type == CrmRelationshipEntityType.CONTACT,
            CrmRelationship.target_entity_id == target_id,
            CrmRelationship.relationship_type == relationship_type,
            CrmRelationship.archived_at.is_(None),
        )
    )
    if existing is not None:
        return
    db.add(
        CrmRelationship(
            source_entity_type=CrmRelationshipEntityType.CONTACT,
            source_entity_id=source_id,
            target_entity_type=CrmRelationshipEntityType.CONTACT,
            target_entity_id=target_id,
            relationship_type=relationship_type,
            reciprocal_type="agency_of" if relationship_type == "agency_customer" else None,
            category=CrmRelationshipCategory.COMMERCIAL,
            status=CrmRelationshipStatus.ACTIVE,
            strength=CrmRelationshipStrength.MODERATE,
            direction=CrmRelationshipDirection.OUTBOUND,
            owner_user_id=actor.id if actor is not None else None,
        )
    )


def create_agent_contact(db: Session, *, actor: User | None, **person: Any) -> tuple[CrmContact, bool]:
    contact, reused = ensure_person_contact(
        db,
        actor=actor,
        contact_type=CrmContactType.BROKER,
        contact_types=[CrmContactType.BROKER],
        status=CrmContactStatus.ACTIVE,
        **person,
    )
    if contact.contact_type not in {CrmContactType.BROKER, CrmContactType.REALTOR}:
        types = {item.contact_type for item in list(contact.type_assignments or [])}
        if CrmContactType.BROKER not in types and CrmContactType.REALTOR not in types:
            from investhome_api.models.crm_contact import CrmContactTypeAssignment

            contact.type_assignments.append(
                CrmContactTypeAssignment(contact_type=CrmContactType.BROKER, is_primary=False)
            )
    _mark_metadata(contact, {"agent": "true"})
    db.flush()
    return contact, reused


def create_agency_customer(
    db: Session,
    *,
    actor: User | None,
    agency_contact_id: UUID,
    **person: Any,
) -> tuple[CrmContact, bool]:
    agency = db.get(CrmContact, agency_contact_id)
    if agency is None or agency.archived_at is not None:
        raise CrmOperationError("Acente bulunamadı")
    contact, reused = ensure_person_contact(
        db,
        actor=actor,
        contact_type=CrmContactType.PROSPECT,
        status=CrmContactStatus.ACTIVE,
        **person,
    )
    if contact.id == agency.id:
        raise CrmOperationError("Acente kendisinin müşterisi olamaz")
    _mark_metadata(
        contact,
        {
            "agency_customer": "true",
            "agency_contact_id": str(agency.id),
            "agency_name": agency.display_name,
        },
    )
    _ensure_relationship(
        db,
        source_id=agency.id,
        target_id=contact.id,
        relationship_type="agency_customer",
        actor=actor,
    )
    db.flush()
    return contact, reused


def _lead_for_contact(db: Session, contact: CrmContact) -> list[Lead]:
    clauses = [Lead.converted_contact_id == contact.id]
    if contact.lead_id is not None:
        clauses.append(Lead.id == contact.lead_id)
    email = (contact.primary_email or "").strip().lower()
    phone = (contact.primary_phone or "").strip()
    if email:
        clauses.append(Lead.email.ilike(email))
    if phone:
        clauses.append(Lead.phone == phone)
    return list(
        db.scalars(
            select(Lead).where(Lead.archived_at.is_(None), Lead.is_demo.is_(False), or_(*clauses))
        ).all()
    )


def _agreement_rows_for_contact(db: Session, contact_id: UUID) -> list[CrmAgreement]:
    participant_ids = select(CrmAgreementParticipant.agreement_id).where(
        CrmAgreementParticipant.contact_id == contact_id
    )
    return list(
        db.scalars(
            select(CrmAgreement).where(
                or_(CrmAgreement.contact_id == contact_id, CrmAgreement.id.in_(participant_ids)),
                CrmAgreement.status != CrmAgreementStatus.CANCELLED,
            )
        ).all()
    )


def list_contact_processes(
    db: Session,
    contact_id: UUID,
    *,
    focus_lead_id: UUID | None = None,
    focus_agreement_id: UUID | None = None,
) -> dict[str, Any]:
    contact = db.get(CrmContact, contact_id)
    if contact is None or contact.archived_at is not None:
        raise CrmOperationError("Kişi bulunamadı")
    leads = []
    seen: set[UUID] = set()
    for lead in _lead_for_contact(db, contact):
        if lead.id in seen:
            continue
        seen.add(lead.id)
        stage = stage_of(lead)
        active = lead.status not in {LeadStatus.WON, LeadStatus.LOST}
        leads.append(
            {
                "id": lead.id,
                "name": contact.display_name or lead.full_name,
                "stage": stage,
                "active": active,
                "focused": focus_lead_id == lead.id,
            }
        )
    agreements = []
    for row in _agreement_rows_for_contact(db, contact.id):
        meta = _meta(row)
        live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
        label = _display_stage(meta, live) or ""
        stage = normalize_agreement_stage(label, str(meta.get("stage_id") or live.get("stage_id") or ""))
        from investhome_api.services.crm.agreement_service import _project_label

        agreements.append(
            {
                "id": row.id,
                "project_group": row.project_group,
                "project_label": _project_label(row.project_group, meta),
                "unit_number": row.unit_number,
                "stage": stage,
                "stage_label": label or stage,
                "active": row.status == CrmAgreementStatus.ACTIVE,
                "focused": focus_agreement_id == row.id,
            }
        )
    return {"contact_id": contact.id, "leads": leads, "agreements": agreements}


def _contact_for_lead(db: Session, lead: Lead, *, actor: User | None) -> CrmContact:
    if lead.converted_contact_id is not None:
        contact = db.get(CrmContact, lead.converted_contact_id)
        if contact is not None and contact.archived_at is None:
            return contact
    linked = db.scalar(select(CrmContact).where(CrmContact.lead_id == lead.id, CrmContact.archived_at.is_(None)))
    if linked is not None:
        return linked
    people = _unique_person_matches(_person_matches(db, email=lead.email, phone=lead.phone, name=lead.full_name))
    if len(people) > 1:
        raise CrmOperationError("Birden fazla kişi eşleşti. Mevcut kişiyi seçin.")
    return _link_manual_lead_contact(db, lead, people=people, actor=actor)


def convert_lead_to_agreement(
    db: Session,
    lead_id: UUID,
    *,
    actor: User | None,
    project_group: str,
    unit_number: str | None,
    investment_amount: str | None,
    agreement_date: date | None,
    phase_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
) -> dict[str, Any]:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadValidationError("Lead bulunamadı")
    contact = _contact_for_lead(db, lead, actor=actor)
    agreement, reused = create_manual_agreement(
        db,
        contact=contact,
        project_group=project_group,
        unit_number=unit_number,
        investment_amount=investment_amount,
        agreement_date=agreement_date,
        source_lead_id=lead.id,
        stage_label="Kimlik Bilgileri",
        actor=actor,
        phase_id=phase_id,
        inventory_asset_id=inventory_asset_id,
    )
    if not reused:
        set_agreement_stage(agreement, "Kimlik Bilgileri")
    lead.converted_contact_id = contact.id
    lead.status = LeadStatus.WON
    if contact.lead_id is None:
        contact.lead_id = lead.id
    log_activity(
        db,
        action=ActivityAction.STATUS_CHANGED,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key="crm.leads.converted",
        actor_user=actor,
        metadata={
            "contact_id": str(contact.id),
            "agreement_id": str(agreement.id),
            "reused_existing": reused,
        },
        commit=False,
    )
    db.flush()
    detail = _to_detail(db, lead)
    return {
        "agreement_id": agreement.id,
        "contact_id": contact.id,
        "project_group": agreement.project_group,
        "unit_number": agreement.unit_number,
        "stage_label": "Kimlik Bilgileri",
        "reused_existing": reused,
        "lead_id": lead.id,
        "lead_stage": detail.stage,
    }


def create_agreement_for_person(
    db: Session,
    *,
    actor: User | None,
    project_group: str,
    unit_number: str | None,
    investment_amount: str | None,
    agreement_date: date | None,
    source_lead_id: UUID | None = None,
    phase_id: UUID | None = None,
    inventory_asset_id: UUID | None = None,
    **person: Any,
) -> dict[str, Any]:
    if source_lead_id is not None:
        return convert_lead_to_agreement(
            db,
            source_lead_id,
            actor=actor,
            project_group=project_group,
            unit_number=unit_number,
            investment_amount=investment_amount,
            agreement_date=agreement_date,
            phase_id=phase_id,
            inventory_asset_id=inventory_asset_id,
        )
    contact, _reused_contact = ensure_person_contact(db, actor=actor, **person)
    active_leads = [
        lead
        for lead in _lead_for_contact(db, contact)
        if lead.status not in {LeadStatus.WON, LeadStatus.LOST}
    ]
    lead_id = active_leads[0].id if len(active_leads) == 1 else None
    if lead_id is not None:
        return convert_lead_to_agreement(
            db,
            lead_id,
            actor=actor,
            project_group=project_group,
            unit_number=unit_number,
            investment_amount=investment_amount,
            agreement_date=agreement_date,
            phase_id=phase_id,
            inventory_asset_id=inventory_asset_id,
        )
    agreement, reused = create_manual_agreement(
        db,
        contact=contact,
        project_group=project_group,
        unit_number=unit_number,
        investment_amount=investment_amount,
        agreement_date=agreement_date,
        stage_label="Kimlik Bilgileri",
        actor=actor,
        phase_id=phase_id,
        inventory_asset_id=inventory_asset_id,
    )
    db.flush()
    return {
        "agreement_id": agreement.id,
        "contact_id": contact.id,
        "project_group": agreement.project_group,
        "unit_number": agreement.unit_number,
        "stage_label": "Kimlik Bilgileri",
        "reused_existing": reused,
        "lead_id": None,
        "lead_stage": None,
    }
