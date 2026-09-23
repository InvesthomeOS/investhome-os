"""Workspace CRM timeline: real activities, purchases, documents, and contact updates."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityEntityType,
    CrmActivityStatus,
    CrmActivityType,
)
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document, DocumentLink, DocumentStatus
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_activities import CrmTimelineEntry

_EVENT_KIND_ACTIVITY_TYPES: dict[str, list[CrmActivityType]] = {
    "whatsapp": [CrmActivityType.WHATSAPP],
    "email": [CrmActivityType.EMAIL],
    "call": [CrmActivityType.PHONE_CALL, CrmActivityType.SMS],
    "meeting": [
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.SITE_VISIT,
        CrmActivityType.PROPERTY_TOUR,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
    ],
    "note": [CrmActivityType.NOTE, CrmActivityType.COMMENT, CrmActivityType.INTERNAL_DISCUSSION],
    "task": [CrmActivityType.TASK, CrmActivityType.REMINDER, CrmActivityType.FOLLOW_UP],
    "payment": [CrmActivityType.PAYMENT, CrmActivityType.CLOSING],
    "document": [
        CrmActivityType.DOCUMENT_SENT,
        CrmActivityType.DOCUMENT_RECEIVED,
        CrmActivityType.PROPOSAL_SENT,
        CrmActivityType.PROPOSAL_RECEIVED,
    ],
    "purchase": [CrmActivityType.RESERVATION, CrmActivityType.CONTRACT_SIGNED],
    "system": [CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT],
}

_PAYMENT_DOC_MARKERS = ("ödeme", "dekont", "swift", "wire", "receipt", "makbuz")
_CLOSING_DOC_MARKERS = ("tapu", "closing", "title", "deed")
_OA_DOC_MARKERS = ("operating agreement", "işletme sözleşmesi")
_GENERIC_PLACEHOLDER_NAMES = {
    "contact",
    "company",
    "investor",
    "project",
    "lead",
    "crm",
    "kişiler",
    "unknown person",
    "unknown",
}

NOTE_TYPES = {CrmActivityType.NOTE, CrmActivityType.INTERNAL_DISCUSSION}
TASK_TYPES = {CrmActivityType.TASK, CrmActivityType.REMINDER}


def _timeline_project_label(project_group: str, meta: dict | None) -> str:
    from investhome_api.services.crm.agreement_service import _project_label

    try:
        return _project_label(project_group, meta)
    except TypeError:
        return str(_project_label(project_group) or project_group)


def _clean_person_name(value: str | None) -> str | None:
    name = (value or "").strip()
    if not name or name.casefold() in _GENERIC_PLACEHOLDER_NAMES:
        return None
    return name


def _source_badge(kind: str) -> str:
    return {
        "whatsapp": "WhatsApp",
        "email": "Email",
        "call": "Arama",
        "meeting": "Toplantı",
        "document": "Belge",
        "purchase": "Satın Alma",
        "payment": "Ödeme",
        "note": "Not",
        "task": "Görev",
        "system": "Sistem",
    }.get(kind, "Sistem")


def _priority_tier(kind: str, *, high: bool = False) -> str:
    if high or kind in {"purchase", "payment"}:
        return "high"
    return "normal"


def _document_kind_and_summary(
    category: str | None,
    title: str,
    document_type: str | None,
    original_name: str | None = None,
) -> tuple[str, str, bool]:
    blob = " ".join(part for part in (category, title, original_name, document_type) if part).casefold()
    generic_categories = {"bitrix", "other", "diğer", "misc", "document", "belge", "file"}
    raw_category = (category or "").strip()
    file_stem = (original_name or "").rsplit(".", 1)[0].replace("_", " ").strip()
    if raw_category and raw_category.casefold() not in generic_categories:
        label = raw_category
    elif file_stem:
        label = file_stem
    else:
        label = (title or "Belge").strip()
    if label.casefold().endswith(" eklendi"):
        summary = label
    else:
        summary = f"{label} eklendi"
    if any(marker in blob for marker in _PAYMENT_DOC_MARKERS) or document_type in {
        "receipt",
        "bank_statement",
        "invoice",
    }:
        return "payment", "Ödeme dekontu eklendi", True
    if any(marker in blob for marker in _CLOSING_DOC_MARKERS) or document_type in {
        "title_document",
        "closing_document",
    }:
        return "document", f"{label} eklendi", True
    if "ön rezervasyon" in blob or "on rezervasyon" in blob or "pre-reservation" in blob:
        return "document", "Ön Rezervasyon Sözleşmesi eklendi", True
    if any(marker in blob for marker in _OA_DOC_MARKERS) or "operating_agreement" in blob:
        return "document", "Operating Agreement eklendi", True
    return "document", summary, document_type in {
        "contract",
        "operating_agreement",
        "legal_document",
    }


def _whatsapp_summary(meta: dict | None) -> str:
    payload = meta if isinstance(meta, dict) else {}
    history = payload.get("bitrix_history") if isinstance(payload.get("bitrix_history"), dict) else {}
    direction = str(history.get("direction") or payload.get("direction") or "").casefold()
    if direction in {"incoming", "in", "received"}:
        return "WhatsApp mesajı alındı"
    if direction in {"outgoing", "out", "sent"}:
        return "WhatsApp mesajı gönderildi"
    return "WhatsApp mesajı"


def _activity_kind(activity_type: CrmActivityType) -> str:
    if activity_type == CrmActivityType.WHATSAPP:
        return "whatsapp"
    if activity_type == CrmActivityType.EMAIL:
        return "email"
    if activity_type in {CrmActivityType.PHONE_CALL, CrmActivityType.SMS}:
        return "call"
    if activity_type in {
        CrmActivityType.MEETING,
        CrmActivityType.ZOOM_MEETING,
        CrmActivityType.TEAMS_MEETING,
        CrmActivityType.SITE_VISIT,
        CrmActivityType.PROPERTY_TOUR,
        CrmActivityType.INVESTOR_MEETING,
        CrmActivityType.CONSTRUCTION_MEETING,
    }:
        return "meeting"
    if activity_type in NOTE_TYPES or activity_type == CrmActivityType.COMMENT:
        return "note"
    if activity_type in TASK_TYPES or activity_type == CrmActivityType.FOLLOW_UP:
        return "task"
    if activity_type in {
        CrmActivityType.DOCUMENT_SENT,
        CrmActivityType.DOCUMENT_RECEIVED,
        CrmActivityType.PROPOSAL_SENT,
        CrmActivityType.PROPOSAL_RECEIVED,
    }:
        return "document"
    if activity_type in {CrmActivityType.PAYMENT, CrmActivityType.CLOSING}:
        return "payment"
    if activity_type in {CrmActivityType.RESERVATION, CrmActivityType.CONTRACT_SIGNED}:
        return "purchase"
    return "system"


def _activity_summary(activity: CrmActivity, kind: str) -> str:
    meta = activity.metadata_json if isinstance(activity.metadata_json, dict) else {}
    status_value = activity.status.value if activity.status else ""
    if kind == "whatsapp":
        return _whatsapp_summary(meta)
    if kind == "email":
        history = meta.get("bitrix_history") if isinstance(meta.get("bitrix_history"), dict) else {}
        direction = str(history.get("direction") or meta.get("direction") or "").casefold()
        if direction in {"incoming", "in", "received"}:
            return "Email alındı"
        return "Email gönderildi"
    if kind == "call":
        if status_value == CrmActivityStatus.MISSED.value:
            return "Cevapsız arama"
        return "Arama yapıldı"
    if kind == "meeting":
        return "Toplantı"
    if kind == "note":
        return "Not eklendi"
    if kind == "task":
        if status_value == CrmActivityStatus.COMPLETED.value:
            return "Görev tamamlandı"
        return activity.title.strip() if activity.title else "Görev"
    if kind == "document":
        return activity.title.strip() if activity.title else "Belge eklendi"
    if kind == "payment":
        return "Ödeme kaydedildi"
    if kind == "purchase":
        return "Satın alma oluşturuldu"
    return (activity.summary or activity.title or "").strip() or "CRM olayı"


def _resolve_timeline_contact_ids(
    db: Session,
    *,
    entity_type: CrmActivityEntityType | None,
    entity_id: UUID | None,
    contact_search: str | None,
    project_group: str | None,
) -> set[UUID] | None:
    ids: set[UUID] | None = None
    if entity_id is not None and entity_type in {None, CrmActivityEntityType.CONTACT}:
        ids = {entity_id}
    if contact_search and contact_search.strip():
        pattern = f"%{contact_search.strip()}%"
        matched = set(
            db.scalars(select(CrmContact.id).where(CrmContact.display_name.ilike(pattern))).all()
        )
        ids = matched if ids is None else ids & matched
    if project_group and project_group.strip():
        project_contacts = set(
            db.scalars(
                select(CrmAgreement.contact_id).where(CrmAgreement.project_group == project_group.strip())
            ).all()
        )
        ids = project_contacts if ids is None else ids & project_contacts
    return ids


def _agreement_context_by_contact(
    db: Session, contact_ids: set[UUID]
) -> dict[UUID, tuple[CrmAgreement, CrmAgreement | None]]:
    from investhome_api.services.crm.unit_change import is_historical_unit_change

    if not contact_ids:
        return {}
    rows = db.scalars(
        select(CrmAgreement)
        .where(CrmAgreement.contact_id.in_(contact_ids))
        .order_by(CrmAgreement.created_at.desc())
    ).all()
    current: dict[UUID, CrmAgreement] = {}
    historical: dict[UUID, CrmAgreement] = {}
    for row in rows:
        if is_historical_unit_change(row):
            historical.setdefault(row.contact_id, row)
        else:
            current.setdefault(row.contact_id, row)
    out: dict[UUID, tuple[CrmAgreement, CrmAgreement | None]] = {}
    for contact_id in set(current) | set(historical):
        primary = current.get(contact_id) or historical.get(contact_id)
        if primary is None:
            continue
        peer = historical.get(contact_id) if primary is current.get(contact_id) else current.get(contact_id)
        out[contact_id] = (primary, peer)
    return out


def _timeline_entry(
    *,
    id: str,
    source: str,
    activity_type: str,
    title: str,
    summary: str | None,
    status: str | None,
    entity_type: str | None,
    entity_id: UUID | None,
    created_at: datetime,
    event_kind: str,
    person_name: str | None = None,
    project_label: str | None = None,
    unit_number: str | None = None,
    agreement_id: UUID | None = None,
    document_id: UUID | None = None,
    document_name: str | None = None,
    actor_name: str | None = None,
    metadata_json: dict[str, object] | None = None,
    description: str | None = None,
    high_priority: bool = False,
    is_system_event: bool = False,
) -> CrmTimelineEntry:
    high = high_priority or event_kind in {"purchase", "payment"}
    return CrmTimelineEntry(
        id=id,
        source=source,
        activity_type=activity_type,
        title=title,
        summary=summary,
        status=status,
        priority="high" if high else "medium",
        entity_type=entity_type,
        entity_id=entity_id,
        actor_name=actor_name,
        created_at=created_at,
        is_system_event=is_system_event or event_kind == "system",
        metadata_json=metadata_json,
        person_name=_clean_person_name(person_name),
        project_label=project_label or None,
        unit_number=unit_number or None,
        agreement_id=agreement_id,
        document_id=document_id,
        document_name=document_name,
        event_kind=event_kind,
        source_badge=_source_badge(event_kind),
        priority_tier=_priority_tier(event_kind, high=high),
        description=description,
    )


def build_operational_timeline(
    db: Session,
    user: User,
    *,
    search: str | None = None,
    entity_type: CrmActivityEntityType | None = None,
    entity_id: UUID | None = None,
    activity_type: CrmActivityType | None = None,
    activity_types: list[CrmActivityType] | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 30,
    contact_search: str | None = None,
    project_group: str | None = None,
    event_kind: str | None = None,
    owner_id: UUID | None = None,
    status: CrmActivityStatus | None = None,
) -> tuple[list[CrmTimelineEntry], dict[str, int]]:
    from investhome_api.services.crm.activity_service import (
        _apply_activity_filters,
        _paginate,
        _visibility_filter,
    )
    from investhome_api.services.crm.unit_change import is_historical_unit_change

    kind = (event_kind or "").strip().casefold() or None
    owner_scoped = owner_id is not None
    status_completed = status == CrmActivityStatus.COMPLETED if status is not None else False
    extras_ok = not owner_scoped and (status is None or status_completed)
    include_activities = kind is None or kind in _EVENT_KIND_ACTIVITY_TYPES
    include_agreements = extras_ok and (kind is None or kind in {"purchase", "system"})
    include_documents = extras_ok and (kind is None or kind in {"document", "payment"})
    include_logs = extras_ok and (kind is None or kind == "system")

    contact_ids = _resolve_timeline_contact_ids(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        contact_search=contact_search,
        project_group=project_group,
    )
    if contact_ids is not None and len(contact_ids) == 0:
        return [], _paginate(0, page, page_size)

    if kind and kind in _EVENT_KIND_ACTIVITY_TYPES:
        mapped = _EVENT_KIND_ACTIVITY_TYPES[kind]
        activity_types = list({*(activity_types or []), *mapped})
        if activity_type is None and len(mapped) == 1:
            activity_type = mapped[0]

    fetch_n = max(page * page_size, 300)
    entries: list[CrmTimelineEntry] = []
    activity_total = 0

    if include_activities:
        query = select(CrmActivity)
        vis = _visibility_filter(user)
        if vis is not None:
            query = query.where(vis)
        query = _apply_activity_filters(
            query,
            search=search,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type=activity_type,
            activity_types=activity_types,
            date_from=date_from,
            date_to=date_to,
            status=status,
            responsible_user_id=owner_id,
        )
        if contact_ids is not None:
            query = query.where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
            )
        count_query = select(func.count()).select_from(CrmActivity)
        if vis is not None:
            count_query = count_query.where(vis)
        count_query = _apply_activity_filters(
            count_query,
            search=search,
            entity_type=entity_type,
            entity_id=entity_id,
            activity_type=activity_type,
            activity_types=activity_types,
            date_from=date_from,
            date_to=date_to,
            status=status,
            responsible_user_id=owner_id,
        )
        if contact_ids is not None:
            count_query = count_query.where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
            )
        activity_total = db.scalar(count_query) or 0
        rows = list(db.scalars(query.order_by(CrmActivity.created_at.desc()).limit(fetch_n)).all())
        activity_contact_ids = {
            row.entity_id for row in rows if row.entity_type == CrmActivityEntityType.CONTACT
        }
        names = (
            {
                contact.id: contact.display_name
                for contact in db.scalars(
                    select(CrmContact).where(CrmContact.id.in_(activity_contact_ids))
                ).all()
            }
            if activity_contact_ids
            else {}
        )
        agreement_ctx = _agreement_context_by_contact(db, activity_contact_ids)
        user_ids = {
            user_id
            for row in rows
            for user_id in (row.owner_id, row.assigned_user_id, row.created_by)
            if user_id
        }
        owners = (
            {
                user.id: user.full_name
                for user in db.scalars(select(User).where(User.id.in_(user_ids))).all()
            }
            if user_ids
            else {}
        )
        for row in rows:
            person = names.get(row.entity_id) if row.entity_type == CrmActivityEntityType.CONTACT else None
            ctx = agreement_ctx.get(row.entity_id) if row.entity_type == CrmActivityEntityType.CONTACT else None
            agreement = ctx[0] if ctx else None
            event_kind_value = _activity_kind(row.activity_type)
            project_label = (
                _timeline_project_label(agreement.project_group, agreement.metadata_json)
                if agreement
                else None
            )
            owner_name = None
            if row.owner_id:
                owner_name = owners.get(row.owner_id)
            if not owner_name and row.assigned_user_id:
                owner_name = owners.get(row.assigned_user_id)
            if not owner_name and row.created_by:
                owner_name = owners.get(row.created_by)
            entries.append(
                _timeline_entry(
                    id=str(row.id),
                    source="crm_activity",
                    activity_type=row.activity_type.value,
                    title=row.title,
                    summary=_activity_summary(row, event_kind_value),
                    status=row.status.value if row.status else None,
                    entity_type=row.entity_type.value if row.entity_type else None,
                    entity_id=row.entity_id,
                    created_at=row.start_date or row.created_at,
                    event_kind=event_kind_value,
                    person_name=person,
                    project_label=project_label,
                    unit_number=agreement.unit_number if agreement else None,
                    agreement_id=agreement.id if agreement else None,
                    actor_name=owner_name,
                    metadata_json=row.metadata_json if isinstance(row.metadata_json, dict) else None,
                    description=row.description or row.summary,
                    high_priority=event_kind_value in {"purchase", "payment"},
                    is_system_event=row.activity_type
                    in {CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT},
                )
            )

    agreement_total = 0
    if include_agreements and entity_type in {None, CrmActivityEntityType.CONTACT}:
        agreement_query = select(CrmAgreement)
        if contact_ids is not None:
            agreement_query = agreement_query.where(CrmAgreement.contact_id.in_(contact_ids))
        if project_group and project_group.strip():
            agreement_query = agreement_query.where(CrmAgreement.project_group == project_group.strip())
        if date_from is not None:
            agreement_query = agreement_query.where(CrmAgreement.created_at >= date_from)
        if date_to is not None:
            agreement_query = agreement_query.where(CrmAgreement.created_at <= date_to)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            agreement_query = agreement_query.where(
                or_(
                    CrmAgreement.unit_number.ilike(pattern),
                    CrmAgreement.project_group.ilike(pattern),
                )
            )
        agreements = list(db.scalars(agreement_query.order_by(CrmAgreement.created_at.desc())).all())
        agreement_total = 0
        contact_name_ids = {row.contact_id for row in agreements}
        contact_names = (
            {
                contact.id: contact.display_name
                for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_name_ids))).all()
            }
            if contact_name_ids
            else {}
        )
        current_by_contact: dict[UUID, CrmAgreement] = {}
        extras = agreements
        if contact_name_ids:
            extras = list(
                db.scalars(
                    select(CrmAgreement)
                    .where(CrmAgreement.contact_id.in_(contact_name_ids))
                    .order_by(CrmAgreement.created_at.desc())
                ).all()
            )
        for row in extras:
            if not is_historical_unit_change(row):
                current_by_contact.setdefault(row.contact_id, row)
        for row in agreements:
            historical = is_historical_unit_change(row)
            project_label = _timeline_project_label(row.project_group, row.metadata_json)
            person = contact_names.get(row.contact_id)
            status_value = row.status.value if row.status else None
            occurred = row.created_at
            if row.agreement_date:
                occurred = datetime.combine(row.agreement_date, datetime.min.time(), tzinfo=UTC)
            if historical:
                if kind == "purchase":
                    continue
                current = current_by_contact.get(row.contact_id)
                from_unit = (row.unit_number or "").strip()
                to_unit = (current.unit_number or "").strip() if current else ""
                if from_unit and to_unit and from_unit != to_unit:
                    summary = f"Daire değişimi: {from_unit} → {to_unit}"
                elif from_unit:
                    summary = f"Daire değişimi: {from_unit}"
                else:
                    summary = "Daire değişimi"
                entries.append(
                    _timeline_entry(
                        id=f"agreement-{row.id}",
                        source="crm_agreement",
                        activity_type="unit_change",
                        title=summary,
                        summary=summary,
                        status=status_value,
                        entity_type="contact",
                        entity_id=row.contact_id,
                        created_at=row.updated_at or occurred,
                        event_kind="system",
                        person_name=person,
                        project_label=project_label,
                        unit_number=row.unit_number,
                        agreement_id=row.id,
                        description=summary,
                        high_priority=True,
                        is_system_event=True,
                    )
                )
                agreement_total += 1
                continue
            if kind == "system":
                continue
            signed = row.status == CrmAgreementStatus.COMPLETED
            summary = "İmzalı anlaşma" if signed else "Satın alma oluşturuldu"
            activity_type_value = "contract_signed" if signed else "reservation"
            entries.append(
                _timeline_entry(
                    id=f"agreement-{row.id}",
                    source="crm_agreement",
                    activity_type=activity_type_value,
                    title=summary,
                    summary=summary,
                    status=status_value,
                    entity_type="contact",
                    entity_id=row.contact_id,
                    created_at=occurred,
                    event_kind="purchase",
                    person_name=person,
                    project_label=project_label,
                    unit_number=row.unit_number,
                    agreement_id=row.id,
                    description=summary,
                    high_priority=True,
                    is_system_event=True,
                )
            )
            agreement_total += 1

    document_total = 0
    if include_documents and entity_type in {None, CrmActivityEntityType.CONTACT}:
        link_types = ("crm_contact", "contact", "crm_agreement")
        doc_query = (
            select(Document, DocumentLink)
            .join(DocumentLink, DocumentLink.document_id == Document.id)
            .where(
                Document.archived_at.is_(None),
                Document.is_demo.is_(False),
                Document.status != DocumentStatus.ARCHIVED,
                DocumentLink.hidden_from_view.is_(False),
                DocumentLink.entity_type.in_(link_types),
            )
        )
        if date_from is not None:
            doc_query = doc_query.where(Document.created_at >= date_from)
        if date_to is not None:
            doc_query = doc_query.where(Document.created_at <= date_to)
        if search and search.strip():
            pattern = f"%{search.strip()}%"
            doc_query = doc_query.where(
                or_(
                    Document.title.ilike(pattern),
                    Document.original_file_name.ilike(pattern),
                    Document.category.ilike(pattern),
                )
            )
        doc_rows = list(db.execute(doc_query.order_by(Document.created_at.desc()).limit(800)).all())
        agreement_ids = {
            link.entity_id for _doc, link in doc_rows if link.entity_type == "crm_agreement"
        }
        agreements_by_id = (
            {
                row.id: row
                for row in db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(agreement_ids))).all()
            }
            if agreement_ids
            else {}
        )
        contact_from_docs: set[UUID] = set()
        for _doc, link in doc_rows:
            if link.entity_type in {"crm_contact", "contact"}:
                contact_from_docs.add(link.entity_id)
            elif link.entity_type == "crm_agreement":
                agreement = agreements_by_id.get(link.entity_id)
                if agreement:
                    contact_from_docs.add(agreement.contact_id)
        if contact_ids is not None:
            contact_from_docs &= contact_ids
        contact_names = (
            {
                contact.id: contact.display_name
                for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_from_docs))).all()
            }
            if contact_from_docs
            else {}
        )
        agreement_ctx = _agreement_context_by_contact(db, contact_from_docs)
        seen_docs: set[UUID] = set()
        document_entries: list[CrmTimelineEntry] = []
        for doc, link in doc_rows:
            if doc.id in seen_docs:
                continue
            contact_id: UUID | None = None
            agreement: CrmAgreement | None = None
            if link.entity_type == "crm_agreement":
                agreement = agreements_by_id.get(link.entity_id)
                contact_id = agreement.contact_id if agreement else None
            elif link.entity_type in {"crm_contact", "contact"}:
                contact_id = link.entity_id
            if contact_id is None:
                continue
            if contact_ids is not None and contact_id not in contact_ids:
                continue
            seen_docs.add(doc.id)
            ctx = agreement_ctx.get(contact_id)
            display_agreement = agreement or (ctx[0] if ctx else None)
            doc_type = (
                doc.document_type.value if hasattr(doc.document_type, "value") else str(doc.document_type or "")
            )
            kind_value, summary, high = _document_kind_and_summary(
                doc.category, doc.title, doc_type, doc.original_file_name
            )
            if kind == "payment" and kind_value != "payment":
                continue
            if kind == "document" and kind_value == "payment":
                continue
            project_label = (
                _timeline_project_label(display_agreement.project_group, display_agreement.metadata_json)
                if display_agreement
                else None
            )
            document_entries.append(
                _timeline_entry(
                    id=f"document-{doc.id}",
                    source="crm_document",
                    activity_type="document_received" if kind_value == "document" else "payment",
                    title=summary,
                    summary=summary,
                    status=None,
                    entity_type="contact",
                    entity_id=contact_id,
                    created_at=doc.created_at,
                    event_kind=kind_value,
                    person_name=contact_names.get(contact_id),
                    project_label=project_label,
                    unit_number=display_agreement.unit_number if display_agreement else None,
                    agreement_id=display_agreement.id if display_agreement else None,
                    document_id=doc.id,
                    document_name=doc.original_file_name or doc.title,
                    description=doc.title,
                    high_priority=high,
                    is_system_event=True,
                )
            )
        document_total = len(document_entries)
        entries.extend(document_entries)

    log_total = 0
    if include_logs and entity_type in {None, CrmActivityEntityType.CONTACT}:
        log_query = select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.CRM_CONTACT,
            ActivityLog.is_demo.is_(False),
            ActivityLog.action.in_({ActivityAction.CREATED, ActivityAction.UPDATED}),
        )
        if contact_ids is not None:
            log_query = log_query.where(ActivityLog.entity_id.in_(contact_ids))
        if date_from is not None:
            log_query = log_query.where(ActivityLog.created_at >= date_from)
        if date_to is not None:
            log_query = log_query.where(ActivityLog.created_at <= date_to)
        logs = list(db.scalars(log_query.order_by(ActivityLog.created_at.desc()).limit(fetch_n)).all())
        log_contact_ids = {log.entity_id for log in logs}
        log_names = (
            {
                contact.id: contact.display_name
                for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(log_contact_ids))).all()
            }
            if log_contact_ids
            else {}
        )
        log_ctx = _agreement_context_by_contact(db, log_contact_ids)
        needle = (search or "").strip().casefold()
        kept_logs = 0
        for log in logs:
            person = log_names.get(log.entity_id)
            ctx = log_ctx.get(log.entity_id)
            agreement = ctx[0] if ctx else None
            summary = (
                "Kişi oluşturuldu" if log.action == ActivityAction.CREATED else "Kişi bilgileri güncellendi"
            )
            if needle and needle not in summary.casefold() and needle not in (person or "").casefold():
                continue
            kept_logs += 1
            entries.append(
                _timeline_entry(
                    id=f"log-{log.id}",
                    source="audit_log",
                    activity_type="system_event",
                    title=summary,
                    summary=summary,
                    status=None,
                    entity_type="contact",
                    entity_id=log.entity_id,
                    created_at=log.created_at,
                    event_kind="system",
                    person_name=person,
                    project_label=(
                        _timeline_project_label(agreement.project_group, agreement.metadata_json)
                        if agreement
                        else None
                    ),
                    unit_number=agreement.unit_number if agreement else None,
                    agreement_id=agreement.id if agreement else None,
                    actor_name=log.actor_name,
                    metadata_json=log.metadata_json if isinstance(log.metadata_json, dict) else None,
                    description=summary,
                    high_priority=False,
                    is_system_event=True,
                )
            )
        log_total = kept_logs

    entries.sort(key=lambda item: item.created_at, reverse=True)
    total = activity_total + agreement_total + document_total + log_total
    start = (page - 1) * page_size
    return entries[start : start + page_size], _paginate(total, page, page_size)
