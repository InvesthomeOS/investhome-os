"""CRM operational leads — live Lead table, no demo seed, no purchase side effects."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.crm_contacts import CrmContactCreate, CrmDuplicateCheckRequest
from investhome_api.schemas.crm_leads import (
    CrmLeadActivityItem,
    CrmLeadConflictBody,
    CrmLeadConvertResponse,
    CrmLeadCreate,
    CrmLeadDetail,
    CrmLeadIngestRequest,
    CrmLeadItem,
    CrmLeadKpis,
    CrmLeadListResponse,
    CrmLeadMatch,
    CrmLeadOwnerOption,
    CrmLeadStage,
    CrmLeadUpdate,
)
from investhome_api.services.activity_service import log_activity
from investhome_api.services.crm.contact_service import check_duplicates, create_contact
from investhome_api.services.crm.identity import normalize_email, parse_phone, phone_digits

CRM_STAGES: tuple[str, ...] = (
    "yeni",
    "contacted",
    "following",
    "qualified",
    "converted",
    "unqualified",
)

STATUS_TO_STAGE: dict[LeadStatus, CrmLeadStage] = {
    LeadStatus.NEW: "yeni",
    LeadStatus.CONTACTED: "contacted",
    LeadStatus.FOLLOW_UP: "following",
    LeadStatus.MEETING_SCHEDULED: "following",
    LeadStatus.PROPOSAL_SENT: "following",
    LeadStatus.NEGOTIATION: "following",
    LeadStatus.QUALIFIED: "qualified",
    LeadStatus.WON: "converted",
    LeadStatus.LOST: "unqualified",
}

STAGE_TO_STATUS: dict[str, LeadStatus] = {
    "yeni": LeadStatus.NEW,
    "contacted": LeadStatus.CONTACTED,
    "following": LeadStatus.FOLLOW_UP,
    "qualified": LeadStatus.QUALIFIED,
    "converted": LeadStatus.WON,
    "unqualified": LeadStatus.LOST,
}

FOLLOWING_STATUSES = {
    LeadStatus.FOLLOW_UP,
    LeadStatus.MEETING_SCHEDULED,
    LeadStatus.PROPOSAL_SENT,
    LeadStatus.NEGOTIATION,
}

KNOWN_SOURCES = ("manual", "website", "meta", "instagram", "google", "referral", "other")
FUTURE_PROVIDERS = ("meta", "facebook", "instagram", "google", "website", "manual")
UNNAMED_LEAD = "Adsız lead"
UNMATCHED_LEAD = "Eşleşmeyen kaynak lead"


class LeadConflictError(Exception):
    def __init__(self, body: CrmLeadConflictBody) -> None:
        super().__init__(body.message)
        self.body = body


class LeadNotFoundError(Exception):
    pass


class LeadValidationError(Exception):
    pass


def _as_status(value: LeadStatus | str) -> LeadStatus:
    if isinstance(value, LeadStatus):
        return value
    try:
        return LeadStatus(value)
    except ValueError:
        return LeadStatus.NEW


def stage_of(lead: Lead) -> CrmLeadStage:
    return STATUS_TO_STAGE.get(_as_status(lead.status), "yeni")


def _blank(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _meta(lead: Lead) -> dict[str, Any]:
    raw = lead.metadata_json
    return dict(raw) if isinstance(raw, dict) else {}


def _put_meta(lead: Lead, **fields: Any) -> None:
    data = _meta(lead)
    for key, value in fields.items():
        if value is None:
            data.pop(key, None)
        else:
            data[key] = value
    lead.metadata_json = data or None


def _split_name(full_name: str) -> tuple[str | None, str | None]:
    parts = [part for part in full_name.strip().split() if part]
    if not parts:
        return None, None
    if len(parts) == 1:
        return parts[0], None
    return parts[0], " ".join(parts[1:])


def _phone_keys(raw: str | None) -> set[str]:
    parsed = parse_phone(raw)
    if parsed is None:
        return set()
    keys = {parsed.match_key, parsed.e164, parsed.digits, parsed.raw}
    if parsed.e164 is None and len(parsed.digits) == 10:
        keys.update({f"+90{parsed.digits}", f"0{parsed.digits}"})
    keys.discard(None)
    return {str(key) for key in keys if key}


def _phones_match(left: str | None, right: str | None) -> bool:
    left_digits = phone_digits(left)
    right_digits = phone_digits(right)
    if len(left_digits) < 7 or len(right_digits) < 7:
        return False
    return left_digits[-10:] == right_digits[-10:] or left_digits in _phone_keys(right) or right_digits in _phone_keys(left)


def _live_leads(db: Session):
    return select(Lead).where(Lead.archived_at.is_(None), Lead.is_demo.is_(False))


def _find_lead_matches(db: Session, *, email: str | None, phone: str | None, exclude_id: UUID | None = None) -> list[Lead]:
    rows = list(db.scalars(_live_leads(db)).all())
    matches: list[Lead] = []
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        if email and normalize_email(row.email) == email:
            matches.append(row)
            continue
        if phone and _phones_match(row.phone, phone):
            matches.append(row)
    return matches


def _person_matches(db: Session, *, email: str | None, phone: str | None, name: str | None) -> list[CrmLeadMatch]:
    payload = CrmDuplicateCheckRequest(primary_email=email, primary_phone=phone, display_name=name)
    found = check_duplicates(db, payload)
    safe = [item for item in found if item.match_reason in {"phone", "email"} and item.match_score >= 1.0]
    matches: list[CrmLeadMatch] = []
    for item in safe:
        contact = db.get(CrmContact, item.contact_id)
        if contact is None or contact.archived_at is not None:
            continue
        matches.append(
            CrmLeadMatch(
                kind="person",
                id=contact.id,
                name=contact.display_name,
                phone=contact.primary_phone,
                email=contact.primary_email,
                reason=item.match_reason,
                href=f"/workspaces/crm/contacts/{contact.id}",
            )
        )
    return matches


def _lead_match_items(rows: list[Lead]) -> list[CrmLeadMatch]:
    return [
        CrmLeadMatch(
            kind="lead",
            id=row.id,
            name=row.full_name,
            phone=row.phone,
            email=row.email,
            reason="phone" if row.phone else "email",
            href=f"/workspaces/crm/leads?lead={row.id}",
        )
        for row in rows
    ]


def _owner_name(db: Session, user_id: UUID | None, cache: dict[UUID, str] | None = None) -> str | None:
    if user_id is None:
        return None
    if cache is not None and user_id in cache:
        return cache[user_id]
    user = db.get(User, user_id)
    name = user.full_name if user is not None else None
    if cache is not None and name:
        cache[user_id] = name
    return name


def _contact_name(db: Session, contact_id: UUID | None) -> str | None:
    if contact_id is None:
        return None
    contact = db.get(CrmContact, contact_id)
    return contact.display_name if contact is not None else None


def _to_item(db: Session, lead: Lead, *, owners: dict[UUID, str] | None = None) -> CrmLeadItem:
    meta = _meta(lead)
    existing_id = meta.get("existing_person_id")
    return CrmLeadItem(
        id=lead.id,
        full_name=lead.full_name,
        phone=lead.phone,
        email=lead.email,
        source=lead.source,
        campaign=lead.campaign,
        ad_id=str(meta["ad_id"]) if meta.get("ad_id") else None,
        form_id=str(meta["form_id"]) if meta.get("form_id") else None,
        project=lead.interested_project,
        owner_user_id=lead.assigned_manager_id,
        owner_name=_owner_name(db, lead.assigned_manager_id, owners),
        stage=stage_of(lead),
        notes=lead.notes,
        provider=lead.provider,
        ingest_status=lead.ingest_status or "ok",
        converted_contact_id=lead.converted_contact_id,
        converted_contact_name=_contact_name(db, lead.converted_contact_id),
        created_at=lead.created_at,
        updated_at=lead.updated_at,
    )


def _activity_items(db: Session, lead_id: UUID) -> list[CrmLeadActivityItem]:
    rows = list(
        db.scalars(
            select(ActivityLog)
            .where(
                ActivityLog.entity_type == ActivityEntityType.LEAD,
                ActivityLog.entity_id == lead_id,
            )
            .order_by(ActivityLog.created_at.desc())
            .limit(50)
        ).all()
    )
    items: list[CrmLeadActivityItem] = []
    for row in rows:
        items.append(
            CrmLeadActivityItem(
                id=row.id,
                action=str(getattr(row.action, "value", row.action)),
                description=row.description_key,
                actor_name=row.actor_name,
                created_at=row.created_at,
                metadata=row.metadata_json if isinstance(row.metadata_json, dict) else None,
            )
        )
    return items


def _to_detail(db: Session, lead: Lead) -> CrmLeadDetail:
    item = _to_item(db, lead)
    meta = _meta(lead)
    existing_id_raw = meta.get("existing_person_id")
    existing_id: UUID | None = None
    if existing_id_raw:
        try:
            existing_id = UUID(str(existing_id_raw))
        except ValueError:
            existing_id = None
    return CrmLeadDetail(
        **item.model_dump(),
        existing_person_id=existing_id or lead.converted_contact_id,
        existing_person_name=_contact_name(db, existing_id or lead.converted_contact_id),
        metadata=meta or None,
        activity=_activity_items(db, lead.id),
    )


def _require_identity(name: str | None, phone: str | None, email: str | None) -> str:
    if name:
        return name
    if email:
        return email
    if phone:
        return phone
    raise LeadValidationError("Ad soyad, telefon veya e-posta gerekli")


def _apply_owner(db: Session, lead: Lead, owner_user_id: UUID | None) -> None:
    lead.assigned_manager_id = owner_user_id
    lead.assigned_to = _owner_name(db, owner_user_id)


def _log(
    db: Session,
    lead: Lead,
    *,
    action: ActivityAction,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        commit=False,
    )


def _filter_options(db: Session) -> tuple[list[str], list[str], list[CrmLeadOwnerOption]]:
    source_rows = list(db.scalars(select(Lead.source).where(Lead.archived_at.is_(None), Lead.is_demo.is_(False)).distinct()).all())
    project_rows = list(
        db.scalars(
            select(Lead.interested_project).where(
                Lead.archived_at.is_(None),
                Lead.is_demo.is_(False),
                Lead.interested_project.isnot(None),
            ).distinct()
        ).all()
    )
    sources = list(dict.fromkeys([*KNOWN_SOURCES, *[str(item) for item in source_rows if item]]))
    projects = sorted({str(item) for item in project_rows if item})
    users = list(
        db.scalars(select(User).where(User.status == UserStatus.ACTIVE).order_by(User.full_name.asc())).all()
    )
    owners = [CrmLeadOwnerOption(id=user.id, name=user.full_name) for user in users]
    return sources, projects, owners


def _kpis(rows: list[Lead]) -> CrmLeadKpis:
    kpis = CrmLeadKpis(total=len(rows))
    for row in rows:
        status = _as_status(row.status)
        if status == LeadStatus.NEW:
            kpis.yeni += 1
        elif status in FOLLOWING_STATUSES:
            kpis.following += 1
        elif status == LeadStatus.QUALIFIED:
            kpis.qualified += 1
        elif status == LeadStatus.WON:
            kpis.converted += 1
        elif status == LeadStatus.LOST:
            kpis.unqualified += 1
        ingest = (row.ingest_status or "ok").lower()
        if ingest == "unmatched":
            kpis.unmatched += 1
        elif ingest == "failed":
            kpis.failed += 1
    kpis.active = kpis.total - kpis.converted - kpis.unqualified
    return kpis


def list_crm_leads(
    db: Session,
    *,
    search: str | None = None,
    stage: str | None = None,
    source: str | None = None,
    project: str | None = None,
    owner_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    ingest_status: str | None = None,
) -> CrmLeadListResponse:
    query = _live_leads(db)
    needle = _blank(search)
    if needle:
        like = f"%{needle}%"
        query = query.where(
            or_(
                Lead.full_name.ilike(like),
                Lead.email.ilike(like),
                Lead.phone.ilike(like),
                Lead.notes.ilike(like),
                Lead.campaign.ilike(like),
                Lead.interested_project.ilike(like),
            )
        )
    if stage:
        if stage == "following":
            query = query.where(Lead.status.in_(FOLLOWING_STATUSES))
        elif stage in STAGE_TO_STATUS:
            query = query.where(Lead.status == STAGE_TO_STATUS[stage])
    if source:
        query = query.where(func.lower(Lead.source) == source.strip().lower())
    if project:
        query = query.where(Lead.interested_project == project)
    if owner_id:
        query = query.where(Lead.assigned_manager_id == owner_id)
    if date_from:
        query = query.where(Lead.created_at >= date_from)
    if date_to:
        query = query.where(Lead.created_at <= date_to)
    if ingest_status == "attention":
        query = query.where(Lead.ingest_status.in_(["unmatched", "failed"]))
    elif ingest_status:
        query = query.where(Lead.ingest_status == ingest_status)

    rows = list(db.scalars(query.order_by(Lead.created_at.desc()).limit(500)).all())
    kpi_rows = list(db.scalars(_live_leads(db)).all())
    owners_cache: dict[UUID, str] = {}
    sources, projects, owners = _filter_options(db)
    return CrmLeadListResponse(
        items=[_to_item(db, row, owners=owners_cache) for row in rows],
        total=len(rows),
        kpis=_kpis(kpi_rows),
        sources=sources,
        projects=projects,
        owners=owners,
        stages=list(CRM_STAGES),
    )


def get_crm_lead(db: Session, lead_id: UUID) -> CrmLeadDetail:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadNotFoundError()
    return _to_detail(db, lead)


def _prepare_identity(payload: CrmLeadCreate | CrmLeadUpdate | CrmLeadIngestRequest) -> tuple[str, str | None, str | None]:
    email = normalize_email(getattr(payload, "email", None))
    phone_raw = _blank(getattr(payload, "phone", None))
    parsed = parse_phone(phone_raw)
    phone = parsed.e164 or parsed.match_key if parsed is not None else phone_raw
    name = _blank(getattr(payload, "full_name", None))
    return name or "", phone, email


def create_crm_lead(
    db: Session,
    payload: CrmLeadCreate,
    *,
    actor: User | None,
    confirm: bool = False,
) -> CrmLeadDetail:
    name, phone, email = _prepare_identity(payload)
    display = _require_identity(name, phone, email)
    lead_matches = _find_lead_matches(db, email=email, phone=phone)
    person_matches = _person_matches(db, email=email, phone=phone, name=display)
    if lead_matches and not confirm:
        raise LeadConflictError(
            CrmLeadConflictBody(
                code="existing_lead",
                message="Bu telefon veya e-posta ile kayıtlı bir lead var",
                matches=_lead_match_items(lead_matches),
            )
        )
    if person_matches and not confirm:
        code = "ambiguous_person" if len(person_matches) > 1 else "existing_person"
        raise LeadConflictError(
            CrmLeadConflictBody(
                code=code,
                message="Bu kişi CRM'de zaten var. Yeni kişi oluşturulmayacak.",
                matches=person_matches,
            )
        )

    stage = payload.stage or "yeni"
    if stage == "converted":
        raise LeadValidationError("Satışa dönüş yalnızca dönüşüm işlemi ile yapılır")
    lead = Lead(
        full_name=display,
        email=email,
        phone=phone,
        source=_blank(payload.source) or "manual",
        campaign=_blank(payload.campaign),
        interested_project=_blank(payload.project),
        notes=_blank(payload.notes),
        status=STAGE_TO_STATUS.get(stage, LeadStatus.NEW),
        provider=_blank(payload.provider) or "manual",
        ingest_status="ok",
        is_demo=False,
    )
    _apply_owner(db, lead, payload.owner_user_id)
    db.add(lead)
    db.flush()
    meta_fields: dict[str, Any] = {
        "ad_id": _blank(payload.ad_id),
        "form_id": _blank(payload.form_id),
        "intake": "manual",
    }
    if person_matches:
        meta_fields["existing_person_id"] = str(person_matches[0].id)
        meta_fields["existing_person_name"] = person_matches[0].name
        meta_fields["duplicate_warning"] = True
    _put_meta(lead, **meta_fields)
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key="crm.leads.created",
        actor=actor,
        metadata={"source": lead.source, "provider": lead.provider},
    )
    db.flush()
    return _to_detail(db, lead)


def update_crm_lead(
    db: Session,
    lead_id: UUID,
    payload: CrmLeadUpdate,
    *,
    actor: User | None,
) -> CrmLeadDetail:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadNotFoundError()
    data = payload.model_dump(exclude_unset=True)
    changed: list[str] = []
    if "full_name" in data:
        name = _blank(payload.full_name)
        if name:
            lead.full_name = name
            changed.append("full_name")
    if "phone" in data:
        _name, phone, _email = _prepare_identity(payload)
        lead.phone = phone
        changed.append("phone")
    if "email" in data:
        lead.email = normalize_email(payload.email)
        changed.append("email")
    if "source" in data:
        lead.source = _blank(payload.source)
        changed.append("source")
    if "campaign" in data:
        lead.campaign = _blank(payload.campaign)
        changed.append("campaign")
    if "project" in data:
        lead.interested_project = _blank(payload.project)
        changed.append("project")
    if "notes" in data:
        lead.notes = _blank(payload.notes)
        changed.append("notes")
    if "owner_user_id" in data:
        _apply_owner(db, lead, payload.owner_user_id)
        changed.append("owner")
    if "ad_id" in data or "form_id" in data:
        _put_meta(lead, ad_id=_blank(payload.ad_id), form_id=_blank(payload.form_id))
        changed.append("attribution")
    if "stage" in data and payload.stage:
        move_crm_lead_stage(db, lead_id, payload.stage, actor=actor)
        return get_crm_lead(db, lead_id)
    if changed:
        _log(
            db,
            lead,
            action=ActivityAction.UPDATED,
            description_key="crm.leads.updated",
            actor=actor,
            metadata={"fields": changed},
        )
    db.flush()
    return _to_detail(db, lead)


def move_crm_lead_stage(
    db: Session,
    lead_id: UUID,
    stage: CrmLeadStage,
    *,
    actor: User | None,
) -> CrmLeadDetail:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadNotFoundError()
    if stage == "converted":
        raise LeadValidationError("Satışa dönüş yalnızca dönüşüm işlemi ile yapılır")
    if stage not in STAGE_TO_STATUS:
        raise LeadValidationError("Geçersiz aşama")
    previous = stage_of(lead)
    lead.status = STAGE_TO_STATUS[stage]
    _log(
        db,
        lead,
        action=ActivityAction.STATUS_CHANGED,
        description_key="crm.leads.stage_changed",
        actor=actor,
        metadata={"from": previous, "to": stage},
    )
    db.flush()
    return _to_detail(db, lead)


def convert_crm_lead(
    db: Session,
    lead_id: UUID,
    *,
    actor: User | None,
    confirm_existing_person_id: UUID | None = None,
) -> CrmLeadConvertResponse:
    lead = db.get(Lead, lead_id)
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadNotFoundError()
    if lead.converted_contact_id is not None:
        contact = db.get(CrmContact, lead.converted_contact_id)
        if contact is not None:
            lead.status = LeadStatus.WON
            db.flush()
            return CrmLeadConvertResponse(
                lead=_to_detail(db, lead),
                contact_id=contact.id,
                contact_name=contact.display_name,
                reused_existing=True,
                href=f"/workspaces/crm/contacts/{contact.id}",
            )

    email = normalize_email(lead.email)
    phone = lead.phone
    people = _person_matches(db, email=email, phone=phone, name=lead.full_name)
    reused = False
    contact: CrmContact | None = None
    if confirm_existing_person_id:
        chosen = next((item for item in people if item.id == confirm_existing_person_id), None)
        if chosen is None:
            existing = db.get(CrmContact, confirm_existing_person_id)
            if existing is None or existing.archived_at is not None:
                raise LeadValidationError("Seçilen kişi bulunamadı")
            contact = existing
        else:
            contact = db.get(CrmContact, chosen.id)
        reused = contact is not None
    elif len(people) == 1:
        contact = db.get(CrmContact, people[0].id)
        reused = contact is not None
    elif len(people) > 1:
        raise LeadConflictError(
            CrmLeadConflictBody(
                code="ambiguous_person",
                message="Birden fazla kişi eşleşti. Dönüşüm için mevcut kişiyi seçin.",
                matches=people,
            )
        )

    history_line = _conversion_history_line(lead)
    if contact is None:
        first_name, last_name = _split_name(lead.full_name)
        person_notes = (lead.notes or "").strip()
        if history_line:
            person_notes = f"{person_notes}\n{history_line}".strip() if person_notes else history_line
        try:
            contact = create_contact(
                db,
                CrmContactCreate(
                    contact_type=CrmContactType.PROSPECT,
                    record_kind=CrmRecordKind.PERSON,
                    display_name=lead.full_name,
                    first_name=first_name,
                    last_name=last_name,
                    primary_email=email,
                    primary_phone=phone,
                    source=lead.source,
                    owner_user_id=lead.assigned_manager_id,
                    lead_id=lead.id,
                    notes=person_notes or None,
                    lifecycle_stage=CrmLifecycleStage.QUALIFIED,
                    status=CrmContactStatus.PROSPECT,
                ),
                actor=actor,
            )
        except ValueError as exc:
            raise LeadValidationError(str(exc)) from exc
        reused = False
    else:
        if contact.lead_id is None:
            contact.lead_id = lead.id
        if not contact.source and lead.source:
            contact.source = lead.source
        if history_line:
            existing_notes = (contact.notes or "").strip()
            if history_line not in existing_notes:
                contact.notes = f"{existing_notes}\n{history_line}".strip() if existing_notes else history_line
        meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
        meta["lead_conversion"] = {
            "lead_id": str(lead.id),
            "source": lead.source,
            "campaign": lead.campaign,
            "provider": lead.provider,
            "converted_at": datetime.now(UTC).isoformat(),
        }
        contact.metadata_json = meta

    lead.converted_contact_id = contact.id
    lead.status = LeadStatus.WON
    _put_meta(
        lead,
        converted_at=datetime.now(UTC).isoformat(),
        converted_contact_id=str(contact.id),
        source=lead.source,
        campaign=lead.campaign,
        provider=lead.provider,
        ad_id=_meta(lead).get("ad_id"),
        form_id=_meta(lead).get("form_id"),
    )
    _log(
        db,
        lead,
        action=ActivityAction.STATUS_CHANGED,
        description_key="crm.leads.converted",
        actor=actor,
        metadata={
            "contact_id": str(contact.id),
            "reused_existing": reused,
            "source": lead.source,
            "campaign": lead.campaign,
        },
    )
    log_activity(
        db,
        action=ActivityAction.CREATED if not reused else ActivityAction.UPDATED,
        entity_type=ActivityEntityType.CRM_CONTACT,
        entity_id=contact.id,
        description_key="crm.leads.converted_to_person",
        actor_user=actor,
        metadata={"lead_id": str(lead.id), "reused_existing": reused},
        commit=False,
    )
    db.flush()
    return CrmLeadConvertResponse(
        lead=_to_detail(db, lead),
        contact_id=contact.id,
        contact_name=contact.display_name,
        reused_existing=reused,
        href=f"/workspaces/crm/contacts/{contact.id}",
    )


def ingest_crm_lead(db: Session, payload: CrmLeadIngestRequest, *, actor: User | None) -> CrmLeadDetail:
    """Persist a future-provider lead. Never discard. Does not connect live ad accounts."""
    provider = (_blank(payload.provider) or "unknown").lower()
    name, phone, email = _prepare_identity(payload)
    has_identity = bool(name or phone or email)
    unique_people = _person_matches(db, email=email, phone=phone, name=name or None) if has_identity else []
    ingest_status = "ok"
    display = name or email or phone or UNMATCHED_LEAD
    if not has_identity:
        ingest_status = "failed"
        display = UNMATCHED_LEAD
    elif len(unique_people) > 1:
        ingest_status = "unmatched"
    elif not phone and not email:
        ingest_status = "unmatched"
        display = name or UNMATCHED_LEAD

    lead = Lead(
        full_name=display,
        email=email,
        phone=phone,
        source=_blank(payload.source) or provider,
        campaign=_blank(payload.campaign),
        interested_project=_blank(payload.project),
        notes=_blank(payload.notes),
        status=LeadStatus.NEW,
        provider=provider,
        ingest_status=ingest_status,
        is_demo=False,
    )
    db.add(lead)
    db.flush()
    _put_meta(
        lead,
        ad_id=_blank(payload.ad_id),
        form_id=_blank(payload.form_id),
        intake="provider",
        ingest_payload=payload.payload,
        unmatched_person_ids=[str(item.id) for item in unique_people] if ingest_status == "unmatched" else None,
        existing_person_id=str(unique_people[0].id) if len(unique_people) == 1 else None,
    )
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key=f"crm.leads.ingest.{ingest_status}",
        actor=actor,
        metadata={"provider": provider, "ingest_status": ingest_status},
    )
    db.flush()
    return _to_detail(db, lead)


def _conversion_history_line(lead: Lead) -> str:
    parts = [f"Lead kaynağı: {lead.source or '—'}"]
    if lead.campaign:
        parts.append(f"Kampanya: {lead.campaign}")
    if lead.provider:
        parts.append(f"Sağlayıcı: {lead.provider}")
    meta = _meta(lead)
    if meta.get("ad_id"):
        parts.append(f"Reklam: {meta['ad_id']}")
    if meta.get("form_id"):
        parts.append(f"Form: {meta['form_id']}")
    return " | ".join(parts)
