"""CRM Agreement list and Nedim purchase-card service."""

from __future__ import annotations

import json
import re
import urllib.parse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType, CrmActivityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.document import Document, DocumentLink
from investhome_api.schemas.crm_agreements import (
    CrmAgreementParticipantSummary,
    CrmAgreementSummary,
    CrmLabeledValue,
    CrmPurchaseCard,
    CrmPurchaseDocument,
    CrmRelatedPurchase,
)
from investhome_api.schemas.crm_contacts import CrmContactTimelineEntry, CrmPurchaseParticipant, CrmPurchaseSummary
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.contact_service import paginate_total_pages
from investhome_api.services.crm.identity import displayable_phone, is_agent_advisor_name
from investhome_api.services.crm.nedim_purchase_card import (
    IZZET_CANONICAL_ID,
    NEDIM_CANONICAL_ID,
    deal_id_for_agreement,
    is_deal_owned_activity,
    is_nedim_purchase_agreement,
)

FILENAME_STAR = re.compile(r"filename\*=(?:UTF-8''|utf-8'')([^;]+)", re.I)
BITRIX_TAG = re.compile(r"\[/?[^\]]+\]")


def is_purchase_owner_contact(contact: CrmContact) -> bool:
    if is_agent_advisor_name(contact.display_name):
        return False
    types = {contact.contact_type}
    for assignment in getattr(contact, "type_assignments", None) or []:
        types.add(assignment.contact_type)
    if types & {CrmContactType.BROKER, CrmContactType.REALTOR} and CrmContactType.BUYER not in types:
        return False
    return True


def _project_label(project_group: str) -> str:
    try:
        return BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup(project_group)]
    except ValueError:
        return project_group


def _meta(row: CrmAgreement) -> dict[str, Any]:
    return row.metadata_json if isinstance(row.metadata_json, dict) else {}


def _display_stage(meta: dict[str, Any], live: dict[str, Any]) -> str | None:
    label = str(meta.get("stage_label") or live.get("stage_label") or "").strip()
    raw = str(meta.get("stage_id") or live.get("stage_id") or "").strip()
    if not label:
        return None
    if label == raw:
        return None
    if re.fullmatch(r"(C\d+:)?[A-Z0-9_]+", label):
        return None
    return label


def format_money(amount: str | None, currency: str | None) -> str | None:
    raw = str(amount or "").strip()
    if not raw:
        return None
    currency_code = str(currency or "").strip().upper()
    try:
        number = Decimal(raw.replace(",", ""))
        if number == number.to_integral_value():
            formatted = f"{int(number):,}"
        else:
            formatted = f"{number:,.2f}"
    except (InvalidOperation, ValueError):
        formatted = raw
    if currency_code == "USD":
        return f"${formatted} USD"
    if currency_code:
        return f"{formatted} {currency_code}"
    return formatted


def _pct_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _plain_text(value: Any) -> str | None:
    text = BITRIX_TAG.sub("", str(value or ""))
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def _display_filename(*values: str | None) -> str | None:
    for raw in values:
        if not raw:
            continue
        match = FILENAME_STAR.search(raw)
        if match:
            decoded = urllib.parse.unquote(match.group(1)).strip()
            if decoded:
                return decoded
        cleaned = raw.split('"; filename*', 1)[0].strip().strip('"')
        if cleaned:
            return cleaned
    return None


def _file_type_label(mime_type: str | None, filename: str | None) -> str:
    mime = str(mime_type or "").lower()
    name = str(filename or "").lower()
    if "pdf" in mime or name.endswith(".pdf"):
        return "PDF"
    if "jpeg" in mime or "jpg" in mime or name.endswith(".jpg") or name.endswith(".jpeg"):
        return "JPEG"
    if "word" in mime or name.endswith(".docx") or name.endswith(".doc"):
        return "Word"
    return "Dosya"


def _contact_live(contact: CrmContact) -> dict[str, Any]:
    meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    live = meta.get("bitrix_live")
    return live if isinstance(live, dict) else {}


def _contact_address(contact: CrmContact) -> str | None:
    parts = [
        contact.address_line1,
        contact.address_line2,
        contact.city,
        contact.postal_code,
        contact.country,
    ]
    joined = ", ".join(str(part).strip() for part in parts if part and str(part).strip())
    return joined or None


def _participant_summaries(
    participants: list[tuple[CrmAgreementParticipant, CrmContact]],
) -> list[CrmAgreementParticipantSummary]:
    ordered = sorted(participants, key=lambda item: (not item[0].is_primary, item[1].display_name.lower()))
    items: list[CrmAgreementParticipantSummary] = []
    for row, contact in ordered:
        live = _contact_live(contact)
        items.append(
            CrmAgreementParticipantSummary(
                contact_id=contact.id,
                display_name=contact.display_name,
                role=row.role,
                ownership_pct=_pct_text(row.ownership_pct),
                is_primary=bool(row.is_primary),
                source=row.source,
                phone=displayable_phone(contact.primary_phone),
                email=contact.primary_email,
                address=_contact_address(contact),
                company=contact.organization_name,
                position=contact.job_title,
                responsible=str(live.get("assigned_name") or "").strip() or None,
            )
        )
    return items


def _owners_label(summaries: list[CrmAgreementParticipantSummary], fallback: str | None) -> str | None:
    names = [item.display_name for item in summaries if item.display_name]
    if names:
        return " + ".join(names)
    return fallback


def serialize_agreement(
    row: CrmAgreement,
    *,
    contact: CrmContact | None = None,
    contact_name: str | None = None,
    participants: list[tuple[CrmAgreementParticipant, CrmContact]] | None = None,
) -> CrmAgreementSummary:
    label = _project_label(row.project_group)
    meta = _meta(row)
    fields = meta.get("agreement_fields") if isinstance(meta.get("agreement_fields"), dict) else {}
    email = None
    phone = None
    if contact is not None:
        email = contact.primary_email
        phone = contact.primary_phone
        contact_name = contact_name or contact.display_name
    email = meta.get("contact_email") or fields.get("email") or email
    phone = displayable_phone(
        phone,
        str(meta.get("contact_phone") or "") or None,
        str(fields.get("phone") or "") or None,
    )
    name = meta.get("source_name") or fields.get("customer_name") or contact_name
    is_reit = row.project_group == BitrixProjectGroup.REIT.value
    unit_number = None if is_reit else (row.unit_number or fields.get("unit_number") or meta.get("unit_number"))
    investment_amount = row.investment_amount or (
        fields.get("payment_amount") if is_reit else None
    ) or (meta.get("investment_amount") if is_reit else None)
    participant_rows = _participant_summaries(participants or [])
    owners = _owners_label(participant_rows, str(name) if name else None)
    deal_id = deal_id_for_agreement(row.id, meta)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    amount, currency = (
        str(meta.get("opportunity") or live.get("opportunity") or row.investment_amount or "") or None,
        str(meta.get("currency") or live.get("currency") or "") or None,
    )
    if not amount:
        amount = str(investment_amount) if investment_amount else None
    stage_label = _display_stage(meta, live)
    return CrmAgreementSummary(
        id=row.id,
        contact_id=row.contact_id,
        contact_name=owners or (str(name) if name else None),
        project_id=row.project_id,
        project_group=row.project_group,
        project_group_label=label,
        source=row.source,
        source_external_id=row.source_external_id,
        status=row.status,
        agreement_date=row.agreement_date,
        unit_number=str(unit_number) if unit_number else None,
        investment_amount=str(investment_amount) if investment_amount else None,
        contact_email=str(email) if email else None,
        contact_phone=str(phone) if phone else None,
        review_required=bool(row.review_required or meta.get("review_required")),
        created_at=row.created_at,
        updated_at=row.updated_at,
        purchase_card_enabled=True,
        owners_label=owners,
        bitrix_deal_id=deal_id,
        amount_label=format_money(amount, currency) if amount else None,
        stage_label=stage_label,
        participants=participant_rows,
    )


def _load_participants_map(
    db: Session, agreement_ids: set[UUID]
) -> dict[UUID, list[tuple[CrmAgreementParticipant, CrmContact]]]:
    if not agreement_ids:
        return {}
    rows = list(
        db.execute(
            select(CrmAgreementParticipant, CrmContact)
            .join(CrmContact, CrmContact.id == CrmAgreementParticipant.contact_id)
            .where(CrmAgreementParticipant.agreement_id.in_(agreement_ids))
        ).all()
    )
    grouped: dict[UUID, list[tuple[CrmAgreementParticipant, CrmContact]]] = defaultdict(list)
    for participant, contact in rows:
        if not is_purchase_owner_contact(contact):
            continue
        grouped[participant.agreement_id].append((participant, contact))
    return grouped


def list_agreements(
    db: Session,
    *,
    project_group: str | None = None,
    status: CrmAgreementStatus | None = None,
    contact_id: UUID | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[CrmAgreementSummary], int]:
    query = select(CrmAgreement)
    if project_group:
        query = query.where(CrmAgreement.project_group == project_group)
    if status is not None:
        query = query.where(CrmAgreement.status == status)
    if contact_id is not None:
        query = query.where(CrmAgreement.contact_id == contact_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(
        db.scalars(
            query.order_by(CrmAgreement.agreement_date.desc().nullslast(), CrmAgreement.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    contact_ids = {row.contact_id for row in rows}
    contacts: dict[UUID, CrmContact] = {}
    if contact_ids:
        for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all():
            contacts[contact.id] = contact
    participants_map = _load_participants_map(db, {row.id for row in rows})
    items = [
        serialize_agreement(
            row,
            contact=contacts.get(row.contact_id),
            contact_name=(contacts[row.contact_id].display_name if row.contact_id in contacts else None),
            participants=participants_map.get(row.id),
        )
        for row in rows
    ]
    return items, int(total)


def agreement_list_meta(*, total: int, page: int, page_size: int) -> dict[str, int]:
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": paginate_total_pages(total, page_size),
    }


def get_agreement(db: Session, agreement_id: UUID) -> CrmAgreement | None:
    return db.get(CrmAgreement, agreement_id)


def _is_deal_owned_document(notes: dict[str, Any], deal_id: str | None) -> bool:
    if not deal_id:
        return False
    return (
        str(notes.get("bitrix_entity_type") or "").lower() == "deal"
        and str(notes.get("bitrix_entity_id") or "") == deal_id
    )


def _document_source_label(notes: dict[str, Any]) -> str | None:
    raw = str(notes.get("source_type") or notes.get("source") or "").strip().lower()
    if raw in {"deal_uf", "uf"}:
        return "Satış belgesi"
    if raw in {"activity", "email", "crm_activity", "activity_attachment"}:
        return "E-posta / Aktivite eki"
    if str(notes.get("bitrix_entity_type") or "").lower() == "deal":
        return "Satın alma belgesi"
    return str(notes.get("source_type") or notes.get("source") or "").strip() or None


def _document_notes(document: Document) -> dict[str, Any]:
    raw = document.notes
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _purchase_amount(row: CrmAgreement) -> tuple[str | None, str | None]:
    meta = _meta(row)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    amount = (
        meta.get("opportunity")
        or live.get("opportunity")
        or meta.get("amount")
        or row.investment_amount
    )
    currency = meta.get("currency") or live.get("currency") or meta.get("amount_currency")
    return str(amount) if amount else None, str(currency) if currency else None


def _deal_tutar_from_contact(contact: CrmContact | None, deal_id: str | None) -> tuple[str | None, str | None]:
    if contact is None or not deal_id:
        return None, None
    live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
    items = live.get("tutar_ve_para_birimi") if isinstance(live, dict) else None
    if not isinstance(items, list):
        return None, None
    for item in items:
        if not isinstance(item, dict):
            continue
        item_deal = str(item.get("deal_id") or item.get("related_entity_id") or "").strip()
        if item_deal != deal_id:
            continue
        amount = str(item.get("amount") or "").strip()
        currency = str(item.get("currency") or "").strip() or None
        if amount:
            return amount, currency
    return None, None


def serialize_purchase_summary(
    row: CrmAgreement,
    *,
    contact: CrmContact | None,
    participants: list[tuple[CrmAgreementParticipant, CrmContact]],
) -> CrmPurchaseSummary:
    meta = _meta(row)
    deal_id = deal_id_for_agreement(row.id, meta)
    amount, currency = _purchase_amount(row)
    if not amount:
        amount, currency = _deal_tutar_from_contact(contact, deal_id)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    summaries = _participant_summaries(participants)
    if not summaries and contact is not None:
        summaries = [
            CrmAgreementParticipantSummary(
                contact_id=contact.id,
                display_name=contact.display_name,
                role="owner",
                ownership_pct=None,
                is_primary=True,
                source=row.source,
            )
        ]
    purchase_participants = [
        CrmPurchaseParticipant(
            contact_id=item.contact_id,
            display_name=item.display_name,
            role=item.role,
            ownership_pct=item.ownership_pct,
            is_primary=item.is_primary,
            source=item.source,
        )
        for item in summaries
    ]
    stage_label = _display_stage(meta, live)
    return CrmPurchaseSummary(
        agreement_id=row.id,
        bitrix_deal_id=deal_id,
        project_group=row.project_group,
        project_label=_project_label(row.project_group),
        unit_number=row.unit_number,
        amount=amount,
        currency=currency,
        amount_label=format_money(amount, currency),
        stage=stage_label,
        begin_date=str(meta.get("begin_date") or live.get("begin_date") or "") or None,
        close_date=str(meta.get("close_date") or live.get("close_date") or "") or None,
        owners_label=_owners_label(summaries, contact.display_name if contact else None),
        participants=purchase_participants,
        opens_purchase_card=True,
        status=stage_label or (row.status.value if hasattr(row.status, "value") else str(row.status)),
    )


def list_contact_purchases(db: Session, contact_id: UUID) -> list[CrmPurchaseSummary]:
    viewer = db.get(CrmContact, contact_id)
    owned_ids = set(
        db.scalars(select(CrmAgreement.id).where(CrmAgreement.contact_id == contact_id)).all()
    )
    participant_ids: set[UUID] = set()
    if viewer is None or is_purchase_owner_contact(viewer):
        participant_ids = set(
            db.scalars(
                select(CrmAgreementParticipant.agreement_id).where(CrmAgreementParticipant.contact_id == contact_id)
            ).all()
        )
    agreement_ids = owned_ids | participant_ids
    if not agreement_ids:
        return []
    rows = list(db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(agreement_ids))).all())
    contacts = {
        contact.id: contact
        for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_({row.contact_id for row in rows}))).all()
    }
    participants_map = _load_participants_map(db, {row.id for row in rows})
    summaries = [
        serialize_purchase_summary(
            row,
            contact=contacts.get(row.contact_id),
            participants=participants_map.get(row.id, []),
        )
        for row in rows
    ]
    summaries.sort(
        key=lambda item: (
            item.project_label or "",
            item.unit_number or "",
            str(item.bitrix_deal_id or ""),
        )
    )
    return summaries


def _activity_entry(db: Session, activity: CrmActivity) -> CrmContactTimelineEntry:
    from investhome_api.services.crm.contact_service import _resolve_owner_name

    metadata = activity.metadata_json if isinstance(activity.metadata_json, dict) else None
    imported = isinstance((metadata or {}).get("bitrix_historical_comment"), dict)
    history = (metadata or {}).get("bitrix_history") if isinstance(metadata, dict) else None
    author_name = None
    if isinstance(history, dict):
        author_name = history.get("author_name") or None
        if not author_name:
            direction = str(history.get("direction") or "")
            if direction == "system":
                author_name = "Sistem"
            elif direction == "incoming":
                author_name = history.get("person_name")
            elif direction == "outgoing":
                author_name = "WhatsApp"
        actor_name = author_name
    else:
        actor_name = _resolve_owner_name(
            db, activity.created_by or activity.owner_id or activity.assigned_user_id
        )
    return CrmContactTimelineEntry(
        id=str(activity.id),
        source="crm_activity",
        activity_type=activity.activity_type.value,
        title="Tarihsel Bitrix yorumu" if imported else activity.title,
        summary=activity.description or activity.summary,
        status=activity.status.value,
        actor_name=actor_name,
        created_at=activity.start_date or activity.created_at,
        is_system_event=activity.activity_type
        in {CrmActivityType.SYSTEM_EVENT, CrmActivityType.AUTOMATION_EVENT},
        imported_historical_comment=imported,
        metadata=metadata,
    )


def purchase_history(db: Session, *, deal_id: str | None, contact_ids: set[UUID]) -> list[CrmContactTimelineEntry]:
    if not deal_id or not contact_ids:
        return []
    activities = list(
        db.scalars(
            select(CrmActivity).where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
                CrmActivity.archived_at.is_(None),
            )
        ).all()
    )
    entries = [
        _activity_entry(db, activity)
        for activity in activities
        if is_deal_owned_activity(
            activity.metadata_json if isinstance(activity.metadata_json, dict) else None,
            deal_id,
        )
    ]
    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries


def purchase_documents(db: Session, agreement_id: UUID, deal_id: str | None) -> list[CrmPurchaseDocument]:
    linked_ids = list(
        db.scalars(
            select(DocumentLink.document_id).where(
                DocumentLink.entity_type == "crm_agreement",
                DocumentLink.entity_id == agreement_id,
            )
        ).all()
    )
    documents: list[Document] = []
    if linked_ids:
        documents.extend(db.scalars(select(Document).where(Document.id.in_(linked_ids))).all())
    if deal_id:
        extras = list(
            db.scalars(
                select(Document).where(
                    Document.notes.is_not(None),
                    Document.notes.ilike(f"%bitrix_entity_id%"),
                    Document.notes.ilike(f"%{deal_id}%"),
                )
            ).all()
        )
        seen = {item.id for item in documents}
        for document in extras:
            notes = _document_notes(document)
            if (
                str(notes.get("bitrix_entity_type") or "").lower() == "deal"
                and str(notes.get("bitrix_entity_id") or "") == deal_id
                and document.id not in seen
            ):
                documents.append(document)
                seen.add(document.id)
    items: list[CrmPurchaseDocument] = []
    seen_docs: set[UUID] = set()
    for document in documents:
        if document.id in seen_docs:
            continue
        seen_docs.add(document.id)
        notes = _document_notes(document)
        if deal_id and not _is_deal_owned_document(notes, deal_id):
            continue
        filename = _display_filename(document.original_file_name, document.title) or document.original_file_name
        items.append(
            CrmPurchaseDocument(
                id=document.id,
                title=filename or document.title,
                original_file_name=filename,
                bitrix_file_id=str(notes.get("bitrix_file_id") or "") or None,
                bitrix_entity_type=str(notes.get("bitrix_entity_type") or "") or None,
                bitrix_entity_id=str(notes.get("bitrix_entity_id") or "") or None,
                document_type=_file_type_label(document.mime_type, filename),
                mime_type=document.mime_type,
                source=_document_source_label(notes),
                created_at=document.created_at,
            )
        )
    seen_files: set[str] = set()
    unique: list[CrmPurchaseDocument] = []
    for item in items:
        file_id = item.bitrix_file_id or str(item.id)
        if file_id in seen_files:
            continue
        seen_files.add(file_id)
        unique.append(item)
    unique.sort(
        key=lambda item: (
            0 if item.source == "Satış belgesi" else 1,
            str(item.created_at or ""),
            item.original_file_name or item.title,
        )
    )
    return unique


def _labeled_values(raw: Any) -> list[CrmLabeledValue]:
    items: list[CrmLabeledValue] = []
    if not isinstance(raw, list):
        return items
    for row in raw:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip()
        value = str(row.get("value") or "").strip()
        if label and value:
            items.append(CrmLabeledValue(label=label, value=value))
    return items


def get_purchase_card(
    db: Session,
    agreement_id: UUID,
    viewer_contact_id: UUID | None = None,
) -> CrmPurchaseCard | None:
    row = get_agreement(db, agreement_id)
    if row is None:
        return None
    contact = db.get(CrmContact, row.contact_id)
    participants = _load_participants_map(db, {row.id}).get(row.id, [])
    summary = serialize_purchase_summary(row, contact=contact, participants=participants)
    owner_rows = _participant_summaries(participants)
    contact_ids = {row.contact_id, *(item.contact_id for item in owner_rows)}
    if is_nedim_purchase_agreement(row.id):
        contact_ids.add(NEDIM_CANONICAL_ID)
        contact_ids.add(IZZET_CANONICAL_ID)
    history = purchase_history(db, deal_id=summary.bitrix_deal_id, contact_ids=contact_ids)
    documents = purchase_documents(db, row.id, summary.bitrix_deal_id)
    meta = _meta(row)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    related: list[CrmRelatedPurchase] = []
    if is_nedim_purchase_agreement(row.id):
        source_id = NEDIM_CANONICAL_ID
        if viewer_contact_id == IZZET_CANONICAL_ID:
            source_id = IZZET_CANONICAL_ID
        for item in list_contact_purchases(db, source_id):
            related.append(
                CrmRelatedPurchase(
                    agreement_id=item.agreement_id,
                    project_label=item.project_label,
                    unit_number=item.unit_number,
                    amount_label=item.amount_label,
                    owners_label=item.owners_label,
                    is_current=item.agreement_id == row.id,
                )
            )
        if len(related) <= 1:
            related = []
    payment = {
        "amount": summary.amount,
        "currency": summary.currency,
        "amount_label": summary.amount_label,
        "stage": summary.stage,
        "begin_date": summary.begin_date,
        "close_date": summary.close_date,
    }
    for key in ("payment_amount", "deposit", "kapora", "payment_plan", "odeme", "payment_notes"):
        if meta.get(key):
            payment[key] = meta.get(key)
        elif live.get(key):
            payment[key] = live.get(key)
    payment_fields = _labeled_values(live.get("payment_fields") or meta.get("payment_fields"))
    if payment.get("payment_notes") and not any(item.label == "Ödeme notu" for item in payment_fields):
        payment_fields.append(CrmLabeledValue(label="Ödeme notu", value=str(payment["payment_notes"])))
    return CrmPurchaseCard(
        agreement_id=row.id,
        bitrix_deal_id=summary.bitrix_deal_id,
        project_group=row.project_group,
        project_label=summary.project_label,
        unit_number=row.unit_number,
        amount=summary.amount,
        currency=summary.currency,
        amount_label=summary.amount_label,
        stage=summary.stage,
        begin_date=summary.begin_date,
        close_date=summary.close_date,
        status=row.status,
        primary_contact_id=row.contact_id,
        owners_label=summary.owners_label,
        participants=owner_rows,
        payment=payment,
        history=history,
        history_count=len(history),
        documents=documents,
        document_count=len(documents),
        responsible_name=str(live.get("assigned_name") or "").strip() or None,
        comments=_plain_text(live.get("comments") or meta.get("comments")),
        agreement_date=row.agreement_date,
        related_purchases=related,
        primary_contact_name=contact.display_name if contact else None,
        llc_name=str(live.get("llc_name") or "").strip() or None,
        payment_fields=payment_fields,
        llc_fields=_labeled_values(live.get("llc_fields") or meta.get("llc_fields")),
        extra_fields=_labeled_values(live.get("extra_fields") or meta.get("extra_fields")),
    )
