"""CRM operational leads — live Lead table, no demo seed, no purchase side effects."""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select
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
from investhome_api.services.crm.identity import (
    is_phone_lookup_query,
    normalize_email,
    parse_phone,
    phone_sql_needles,
    phones_match,
)

CRM_STAGES: tuple[str, ...] = (
    "yeni",
    "contacted",
    "following",
    "proposal",
    "qualified",
    "negotiation",
    "long_term",
    "unqualified",
    "converted",
)

STATUS_TO_STAGE: dict[LeadStatus, CrmLeadStage] = {
    LeadStatus.NEW: "yeni",
    LeadStatus.CONTACTED: "contacted",
    LeadStatus.FOLLOW_UP: "following",
    LeadStatus.PROPOSAL_SENT: "proposal",
    LeadStatus.QUALIFIED: "qualified",
    LeadStatus.NEGOTIATION: "negotiation",
    LeadStatus.MEETING_SCHEDULED: "long_term",
    LeadStatus.LOST: "unqualified",
    LeadStatus.WON: "converted",
}

STAGE_TO_STATUS: dict[str, LeadStatus] = {
    "yeni": LeadStatus.NEW,
    "contacted": LeadStatus.CONTACTED,
    "following": LeadStatus.FOLLOW_UP,
    "proposal": LeadStatus.PROPOSAL_SENT,
    "qualified": LeadStatus.QUALIFIED,
    "negotiation": LeadStatus.NEGOTIATION,
    "long_term": LeadStatus.MEETING_SCHEDULED,
    "unqualified": LeadStatus.LOST,
    "converted": LeadStatus.WON,
}

FOLLOWING_STATUSES = {
    LeadStatus.FOLLOW_UP,
}

KNOWN_SOURCES = ("manual", "website", "meta", "instagram", "google", "referral", "other")
FUTURE_PROVIDERS = ("meta", "facebook", "instagram", "google", "website", "manual")
UNNAMED_LEAD = "Adsız lead"
UNMATCHED_LEAD = "Eşleşmeyen kaynak lead"
DEFAULT_BUDGET_CURRENCY = "USD"
_TASK_TZ = ZoneInfo("Europe/Istanbul")
AUTO_FOLLOWUP_STAGES: frozenset[str] = frozenset({"contacted", "proposal"})
_AUTO_TASK_SOURCE = "stage_automation"
JUNK_REASON_CODES: frozenset[str] = frozenset(
    {
        "unreachable",
        "insufficient_budget",
        "not_interested",
        "no_suitable_project",
        "timing",
        "invested_elsewhere",
        "invalid_contact",
        "duplicate",
        "spam",
        "other",
    }
)
_JUNK_DETAIL_MIN = 3
_JUNK_DETAIL_MAX = 500
logger = logging.getLogger(__name__)
_BUDGET_CURRENCY_RE = re.compile(r"^[A-Za-z]{3}$")
_BUDGET_AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")


class LeadConflictError(Exception):
    def __init__(self, body: CrmLeadConflictBody) -> None:
        super().__init__(body.message)
        self.body = body


class LeadNotFoundError(Exception):
    pass


class LeadValidationError(Exception):
    def __init__(self, message: str, *, code: str | None = None, status_code: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _blank_junk(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


def _parse_junk_reason(
    junk_reason: str | None,
    junk_reason_detail: str | None,
) -> tuple[str, str | None]:
    code = (junk_reason or "").strip().lower() or None
    if not code:
        raise LeadValidationError("junk_reason_required", code="junk_reason_required", status_code=422)
    if code not in JUNK_REASON_CODES:
        raise LeadValidationError("invalid_junk_reason", code="invalid_junk_reason", status_code=422)
    detail = _blank_junk(junk_reason_detail)
    if code == "other":
        if not detail or len(detail) < _JUNK_DETAIL_MIN:
            raise LeadValidationError(
                "junk_reason_detail_required",
                code="junk_reason_detail_required",
                status_code=422,
            )
        return code, detail[:_JUNK_DETAIL_MAX]
    return code, None


def _apply_junk_reason(lead: Lead, junk_reason: str | None, junk_reason_detail: str | None) -> tuple[str, str | None]:
    code, detail = _parse_junk_reason(junk_reason, junk_reason_detail)
    lead.junk_reason = code
    lead.junk_reason_detail = detail
    lead.junked_at = datetime.now(tz=UTC)
    return code, detail


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
    return phones_match(left, right)


def _live_leads(db: Session):
    return select(Lead).where(Lead.archived_at.is_(None), Lead.is_demo.is_(False))


def _is_facebook_messenger_lead(lead: Lead) -> bool:
    """Messenger inbound creates Contact+Lead but is not a sales-pipeline card."""
    meta = lead.metadata_json if isinstance(lead.metadata_json, dict) else {}
    if str(meta.get("intake") or "").strip().lower() == "facebook_messenger":
        return True
    return (lead.source or "").strip().lower() == "facebook" and (lead.provider or "").strip().lower() == "facebook"


def _is_instagram_dm_lead(lead: Lead) -> bool:
    """Instagram DM inbound creates Contact+Lead but is not a sales-pipeline card."""
    meta = lead.metadata_json if isinstance(lead.metadata_json, dict) else {}
    if str(meta.get("intake") or "").strip().lower() == "instagram_dm":
        return True
    return (lead.source or "").strip().lower() == "instagram" and (lead.provider or "").strip().lower() == "instagram"


def _is_meta_dm_lead(lead: Lead) -> bool:
    return _is_facebook_messenger_lead(lead) or _is_instagram_dm_lead(lead)


def _exclude_facebook_messenger_pipeline(query):
    """Hide Facebook Messenger and Instagram DM leads from the sales pipeline kanban."""
    return query.where(
        ~or_(
            and_(
                func.lower(func.coalesce(Lead.source, "")) == "facebook",
                func.lower(func.coalesce(Lead.provider, "")) == "facebook",
            ),
            and_(
                func.lower(func.coalesce(Lead.source, "")) == "instagram",
                func.lower(func.coalesce(Lead.provider, "")) == "instagram",
            ),
        )
    )


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


def parse_investment_budget_amount(raw: object | None) -> Decimal | None:
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise LeadValidationError("Yatırım bütçesi geçersiz")
    if isinstance(raw, Decimal):
        value = raw
    elif isinstance(raw, int):
        value = Decimal(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        negative = text.startswith("-")
        text = (
            text.replace("$", "")
            .replace("€", "")
            .replace("£", "")
            .replace(" ", "")
            .replace("\u00a0", "")
        )
        if text.startswith("-"):
            text = text[1:]
            negative = True
        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif text.count(",") == 1 and len(text.split(",")[1]) <= 2:
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
        if not _BUDGET_AMOUNT_RE.fullmatch(text):
            raise LeadValidationError("Yatırım bütçesi geçersiz")
        try:
            value = Decimal(text)
        except InvalidOperation as exc:
            raise LeadValidationError("Yatırım bütçesi geçersiz") from exc
        if negative:
            value = -value
    else:
        raise LeadValidationError("Yatırım bütçesi geçersiz")
    if value < 0:
        raise LeadValidationError("Yatırım bütçesi negatif olamaz")
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def normalize_budget_currency(raw: str | None, *, amount: Decimal | None) -> str | None:
    if amount is None:
        return None
    code = (raw or DEFAULT_BUDGET_CURRENCY).strip().upper()
    if not _BUDGET_CURRENCY_RE.fullmatch(code):
        raise LeadValidationError("Para birimi geçersiz")
    return code


def _unique_person_matches(matches: list[CrmLeadMatch]) -> list[CrmLeadMatch]:
    seen: set[UUID] = set()
    unique: list[CrmLeadMatch] = []
    for item in matches:
        if item.id in seen:
            continue
        seen.add(item.id)
        unique.append(item)
    return unique


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


def _linked_contact(db: Session, lead: Lead) -> CrmContact | None:
    if lead.converted_contact_id is not None:
        contact = db.get(CrmContact, lead.converted_contact_id)
        if contact is not None and contact.archived_at is None:
            return contact
    meta_id = _meta(lead).get("existing_person_id")
    if meta_id:
        try:
            contact = db.get(CrmContact, UUID(str(meta_id)))
        except ValueError:
            contact = None
        if contact is not None and contact.archived_at is None:
            return contact
    return db.scalar(
        select(CrmContact).where(CrmContact.lead_id == lead.id, CrmContact.archived_at.is_(None)).limit(1)
    )


def _to_item(db: Session, lead: Lead, *, owners: dict[UUID, str] | None = None) -> CrmLeadItem:
    meta = _meta(lead)
    linked = _linked_contact(db, lead)
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
        contact_id=linked.id if linked is not None else None,
        contact_name=linked.display_name if linked is not None else None,
        investment_budget_amount=lead.estimated_budget,
        investment_budget_currency=lead.estimated_budget_currency,
        junk_reason=lead.junk_reason,
        junk_reason_detail=lead.junk_reason_detail,
        junked_at=lead.junked_at,
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
    from investhome_api.services.crm.activity_service import list_tasks_for_lead

    item = _to_item(db, lead)
    return CrmLeadDetail(
        **item.model_dump(),
        existing_person_id=item.contact_id,
        existing_person_name=item.contact_name,
        metadata=_meta(lead) or None,
        activity=_activity_items(db, lead.id),
        tasks=list_tasks_for_lead(db, lead.id),
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


def _apply_investment_budget(lead: Lead, payload: CrmLeadCreate | CrmLeadUpdate, *, unset_ok: bool = True) -> bool:
    data = payload.model_dump(exclude_unset=True)
    if "investment_budget_amount" not in data and "investment_budget_currency" not in data:
        return False
    amount = parse_investment_budget_amount(data.get("investment_budget_amount", lead.estimated_budget))
    if amount is None:
        if not unset_ok:
            return False
        lead.estimated_budget = None
        lead.estimated_budget_currency = None
        return True
    currency = normalize_budget_currency(
        data.get("investment_budget_currency", lead.estimated_budget_currency),
        amount=amount,
    )
    lead.estimated_budget = amount
    lead.estimated_budget_currency = currency
    return True


def _link_manual_lead_contact(
    db: Session,
    lead: Lead,
    *,
    people: list[CrmLeadMatch],
    actor: User | None,
) -> CrmContact:
    unique = _unique_person_matches(people)
    contact: CrmContact | None = None
    if len(unique) == 1:
        contact = db.get(CrmContact, unique[0].id)
    if contact is None or contact.archived_at is not None:
        first_name, last_name = _split_name(lead.full_name)
        try:
            contact = create_contact(
                db,
                CrmContactCreate(
                    contact_type=CrmContactType.PROSPECT,
                    record_kind=CrmRecordKind.PERSON,
                    display_name=lead.full_name,
                    first_name=first_name,
                    last_name=last_name,
                    primary_email=lead.email,
                    primary_phone=lead.phone,
                    source=lead.source,
                    owner_user_id=lead.assigned_manager_id,
                    lead_id=lead.id,
                    notes=lead.notes,
                    lifecycle_stage=CrmLifecycleStage.NEW,
                    status=CrmContactStatus.PROSPECT,
                ),
                actor=actor,
            )
        except ValueError as exc:
            raise LeadValidationError(str(exc)) from exc
    if contact.lead_id is None:
        contact.lead_id = lead.id
    if not contact.source and lead.source:
        contact.source = lead.source
    _put_meta(
        lead,
        existing_person_id=str(contact.id),
        existing_person_name=contact.display_name,
    )
    return contact


def _log(
    db: Session,
    lead: Lead,
    *,
    action: ActivityAction,
    description_key: str,
    actor: User | None,
    metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> None:
    log_activity(
        db,
        action=action,
        entity_type=ActivityEntityType.LEAD,
        entity_id=lead.id,
        description_key=description_key,
        actor_user=actor,
        metadata=metadata,
        created_at=created_at,
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
    junk_reason: str | None = None,
    surface: str | None = None,
) -> CrmLeadListResponse:
    query = _live_leads(db)
    pipeline_surface = (surface or "").strip().lower() == "pipeline"
    if pipeline_surface:
        query = _exclude_facebook_messenger_pipeline(query)
    needle = _blank(search)
    if needle:
        like = f"%{needle}%"
        clauses = [
            Lead.full_name.ilike(like),
            Lead.email.ilike(like),
            Lead.phone.ilike(like),
            Lead.notes.ilike(like),
            Lead.campaign.ilike(like),
            Lead.interested_project.ilike(like),
        ]
        if is_phone_lookup_query(needle):
            for phone_needle in phone_sql_needles(needle):
                clauses.append(Lead.phone.ilike(f"%{phone_needle}%"))
        query = query.where(or_(*clauses))
    if stage:
        if stage in STAGE_TO_STATUS:
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
    reason_code = (junk_reason or "").strip().lower() or None
    if reason_code:
        query = query.where(Lead.junk_reason == reason_code)
        if not stage:
            query = query.where(Lead.status == LeadStatus.LOST)

    rows = list(db.scalars(query.order_by(Lead.created_at.desc()).limit(500)).all())
    kpi_query = _live_leads(db)
    if pipeline_surface:
        kpi_query = _exclude_facebook_messenger_pipeline(kpi_query)
    kpi_rows = list(db.scalars(kpi_query).all())
    if pipeline_surface:
        rows = [row for row in rows if not _is_meta_dm_lead(row)]
        kpi_rows = [row for row in kpi_rows if not _is_meta_dm_lead(row)]
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
    person_matches = _unique_person_matches(_person_matches(db, email=email, phone=phone, name=display))
    if lead_matches:
        raise LeadConflictError(
            CrmLeadConflictBody(
                code="existing_lead",
                message="Bu telefon veya e-posta ile kayıtlı bir lead var",
                matches=_lead_match_items(lead_matches),
            )
        )
    if len(person_matches) > 1:
        raise LeadConflictError(
            CrmLeadConflictBody(
                code="ambiguous_person",
                message="Birden fazla kişi eşleşti. Yeni kişi sessizce oluşturulmaz.",
                matches=person_matches,
            )
        )
    if person_matches and not confirm:
        raise LeadConflictError(
            CrmLeadConflictBody(
                code="existing_person",
                message="Bu kişi CRM'de zaten var. Yeni kişi oluşturulmayacak.",
                matches=person_matches,
            )
        )

    stage = payload.stage or "yeni"
    if stage == "converted":
        raise LeadValidationError("Satış Kapama yalnızca dönüşüm işlemi ile yapılır")
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
    _apply_investment_budget(lead, payload, unset_ok=True)
    created_junk: tuple[str, str | None] | None = None
    if stage == "unqualified":
        created_junk = _apply_junk_reason(lead, payload.junk_reason, payload.junk_reason_detail)
    db.add(lead)
    db.flush()
    _put_meta(
        lead,
        ad_id=_blank(payload.ad_id),
        form_id=_blank(payload.form_id),
        intake="manual",
    )
    contact = _link_manual_lead_contact(db, lead, people=person_matches, actor=actor)
    _log(
        db,
        lead,
        action=ActivityAction.CREATED,
        description_key="crm.leads.created",
        actor=actor,
        metadata={
            "source": lead.source,
            "provider": lead.provider,
            "contact_id": str(contact.id),
            **({"junk_reason": created_junk[0], "junk_reason_detail": created_junk[1]} if created_junk else {}),
        },
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
    if _apply_investment_budget(lead, payload, unset_ok=True):
        changed.append("investment_budget")
    if "owner_user_id" in data:
        _apply_owner(db, lead, payload.owner_user_id)
        changed.append("owner")
    if "ad_id" in data or "form_id" in data:
        _put_meta(lead, ad_id=_blank(payload.ad_id), form_id=_blank(payload.form_id))
        changed.append("attribution")
    if "stage" in data and payload.stage:
        move_crm_lead_stage(
            db,
            lead_id,
            payload.stage,
            actor=actor,
            junk_reason=payload.junk_reason,
            junk_reason_detail=payload.junk_reason_detail,
        )
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


def _auto_followup_due_at(transition_at: datetime) -> datetime:
    local = transition_at.astimezone(_TASK_TZ) if transition_at.tzinfo else transition_at.replace(tzinfo=_TASK_TZ)
    return (local + timedelta(days=2)).astimezone(UTC)


def _auto_task_is_active(row) -> bool:
    from investhome_api.models.crm_activity import CrmActivityStatus, CrmTaskStatus

    if getattr(row, "archived_at", None) is not None:
        return False
    task_status = getattr(row, "task_status", None)
    status = getattr(row, "status", None)
    closed_task = {CrmTaskStatus.COMPLETED, CrmTaskStatus.CANCELLED, CrmTaskStatus.DEFERRED}
    closed_status = {CrmActivityStatus.COMPLETED, CrmActivityStatus.CANCELLED, CrmActivityStatus.ARCHIVED}
    if task_status in closed_task or status in closed_status:
        return False
    return True


def _find_active_stage_auto_task(db: Session, lead_id: UUID, stage: str):
    from investhome_api.models.crm_activity import CrmActivity, CrmActivityType
    from investhome_api.services.crm.activity_service import _task_lead_clause

    rows = db.scalars(
        select(CrmActivity).where(
            CrmActivity.activity_type == CrmActivityType.TASK,
            CrmActivity.archived_at.is_(None),
            _task_lead_clause(lead_id),
        )
    ).all()
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if meta.get("source") != _AUTO_TASK_SOURCE:
            continue
        if str(meta.get("source_stage_id") or "") != stage:
            continue
        if _auto_task_is_active(row):
            return row
    return None


def _ensure_stage_followup_task(
    db: Session,
    lead: Lead,
    stage: str,
    *,
    actor: User,
    transition_at: datetime,
) -> None:
    from investhome_api.models.crm_activity import CrmReminderChannel
    from investhome_api.schemas.crm_activities import CrmActivityReminderInput, CrmTaskCreate
    from investhome_api.services.crm.activity_service import ActivityValidationError, create_workspace_task

    existing = _find_active_stage_auto_task(db, lead.id, stage)
    if existing is not None:
        logger.info(
            "crm_lead_stage_auto_task_skipped lead=%s stage=%s reason=active_duplicate task=%s",
            lead.id,
            stage,
            existing.id,
        )
        return
    contact = _linked_contact(db, lead)
    contact_id = contact.id if contact is not None else None
    name = ((contact.display_name if contact is not None else None) or lead.full_name).strip() or lead.full_name
    due = _auto_followup_due_at(transition_at)
    assignee = lead.assigned_manager_id or actor.id
    metadata: dict[str, object] = {
        "source": _AUTO_TASK_SOURCE,
        "source_stage_id": stage,
        "lead_id": str(lead.id),
        "title_en": f"Follow-up — {name}",
    }
    if contact_id is not None:
        metadata["contact_id"] = str(contact_id)
    try:
        created = create_workspace_task(
            db,
            actor,
            CrmTaskCreate(
                title=f"Takip — {name}"[:500],
                lead_id=lead.id,
                contact_id=contact_id,
                assigned_user_id=assignee,
                due_date=due,
                timezone="Europe/Istanbul",
                reminder_date=due,
                reminders=[
                    CrmActivityReminderInput(
                        channel=CrmReminderChannel.IN_APP,
                        remind_at=due,
                        offset_minutes=0,
                    )
                ],
                metadata_json=metadata,
            ),
            commit=False,
        )
    except ActivityValidationError as exc:
        logger.exception("crm_lead_stage_auto_task_invalid lead=%s stage=%s", lead.id, stage)
        raise LeadValidationError(str(exc)) from exc
    except Exception:
        logger.exception("crm_lead_stage_auto_task_failed lead=%s stage=%s", lead.id, stage)
        raise
    logger.info(
        "crm_lead_stage_auto_task_created lead=%s stage=%s task=%s due=%s",
        lead.id,
        stage,
        created.id,
        due.isoformat(),
    )


def move_crm_lead_stage(
    db: Session,
    lead_id: UUID,
    stage: CrmLeadStage,
    *,
    actor: User | None,
    junk_reason: str | None = None,
    junk_reason_detail: str | None = None,
) -> CrmLeadDetail:
    lead = db.scalar(select(Lead).where(Lead.id == lead_id).with_for_update())
    if lead is None or lead.archived_at is not None or lead.is_demo:
        raise LeadNotFoundError()
    if stage == "converted":
        raise LeadValidationError("Satış Kapama yalnızca dönüşüm işlemi ile yapılır")
    if stage not in STAGE_TO_STATUS:
        raise LeadValidationError("Geçersiz aşama")
    previous = stage_of(lead)
    if previous == stage:
        return _to_detail(db, lead)
    log_meta: dict[str, Any] = {"from": previous, "to": stage}
    if stage == "unqualified":
        code, detail = _apply_junk_reason(lead, junk_reason, junk_reason_detail)
        log_meta["junk_reason"] = code
        if detail:
            log_meta["junk_reason_detail"] = detail
    elif previous == "unqualified":
        if lead.junk_reason:
            log_meta["previous_junk_reason"] = lead.junk_reason
        if lead.junk_reason_detail:
            log_meta["previous_junk_reason_detail"] = lead.junk_reason_detail
    lead.status = STAGE_TO_STATUS[stage]
    _log(
        db,
        lead,
        action=ActivityAction.STATUS_CHANGED,
        description_key="crm.leads.stage_changed",
        actor=actor,
        metadata=log_meta,
    )
    db.flush()
    if previous != stage and stage in AUTO_FOLLOWUP_STAGES:
        if actor is None:
            logger.error("crm_lead_stage_auto_task_missing_actor lead=%s stage=%s", lead.id, stage)
            raise LeadValidationError("Otomatik görev için kullanıcı gerekli")
        _ensure_stage_followup_task(
            db,
            lead,
            stage,
            actor=actor,
            transition_at=datetime.now(tz=UTC),
        )
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
    people = _unique_person_matches(_person_matches(db, email=email, phone=phone, name=lead.full_name))
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
