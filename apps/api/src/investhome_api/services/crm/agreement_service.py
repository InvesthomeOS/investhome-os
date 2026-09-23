"""CRM Agreement list and Nedim purchase-card service."""

from __future__ import annotations

import json
import re
import urllib.parse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType, CrmActivityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.document import Document, DocumentLink
from investhome_api.schemas.crm_agreements import (
    CrmAgreementActivityItem,
    CrmAgreementCalendarItem,
    CrmAgreementParticipantSummary,
    CrmAgreementSummary,
    CrmLabeledValue,
    CrmPurchaseCard,
    CrmPurchaseDocument,
    CrmRelatedPurchase,
    CrmUnitHistoryStep,
)
from investhome_api.schemas.crm_contacts import CrmContactTimelineEntry, CrmPurchaseParticipant, CrmPurchaseSummary
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.contact_service import paginate_total_pages
from investhome_api.services.crm.document_surface import (
    document_notes,
    person_surface_documents,
    purchase_linked_documents,
)
from investhome_api.services.crm.identity import displayable_phone, format_display_phone, is_agent_advisor_name
from investhome_api.services.crm.nedim_purchase_card import (
    IZZET_CANONICAL_ID,
    NEDIM_CANONICAL_ID,
    activity_deal_id,
    deal_id_for_agreement,
    is_deal_owned_activity,
    is_nedim_purchase_agreement,
)
from investhome_api.services.crm.unit_change import (
    historical_unit_change_clause,
    is_historical_unit_change,
    unit_history_steps,
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


def _project_label(project_group: str, meta: dict[str, Any] | None = None) -> str:
    payload = meta if isinstance(meta, dict) else {}
    override = str(payload.get("original_project_label") or payload.get("project_label") or "").strip()
    if override:
        return override
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


_LIFECYCLE_TR = {
    "new": "Yeni",
    "engaged": "Etkileşimde",
    "qualified": "Nitelikli",
    "active_relationship": "Aktif ilişki",
    "dormant": "Durgun",
    "churned": "Kaybedildi",
}

_DEAL_STATUS_TR = {
    "won": "Kazanıldı",
    "lost": "Kaybedildi",
    "active": "Aktif",
    "early": "Erken",
}


def _labeled_lookup(items: list[CrmLabeledValue], *labels: str) -> str | None:
    wanted = {label.casefold() for label in labels}
    for item in items:
        if item.label.casefold() in wanted:
            return item.value
    return None


def _optional_fields(meta: dict[str, Any], live: dict[str, Any]) -> dict[str, str | None]:
    labeled = [
        *_labeled_values(live.get("extra_fields") or meta.get("extra_fields")),
        *_labeled_values(live.get("payment_fields") or meta.get("payment_fields")),
        *_labeled_values(live.get("llc_fields") or meta.get("llc_fields")),
    ]
    status_raw = str(meta.get("bitrix_deal_status") or live.get("bitrix_deal_status") or "").strip().lower()
    deposit = (
        _labeled_lookup(labeled, "Ön Ödeme Tutarı", "Peşinat", "Kapora")
        or (str(meta.get("deposit") or live.get("deposit") or meta.get("kapora") or live.get("kapora") or "").strip() or None)
    )
    return {
        "payment_status": _DEAL_STATUS_TR.get(status_raw, status_raw or None),
        "payment_method": _labeled_lookup(labeled, "Ödeme Şekli"),
        "share_ratio": _labeled_lookup(labeled, "Ownership Percentage", "Sahiplik"),
        "company_details": str(live.get("llc_name") or "").strip() or _labeled_lookup(labeled, "Şirket / LLC", "LLC"),
        "payment_dates": _labeled_lookup(labeled, "Ödeme Tarihleri"),
        "floor": _labeled_lookup(labeled, "Kat"),
        "deposit_amount": deposit,
        "potential_status": _labeled_lookup(labeled, "Potansiyel Durumu"),
        "begin_date": str(meta.get("begin_date") or live.get("begin_date") or "").strip() or None,
        "close_date": str(meta.get("close_date") or live.get("close_date") or "").strip() or None,
        "responsible_name": (
            str(live.get("assigned_name") or meta.get("responsible_person") or "").strip() or None
        ),
    }


def _share_from_participants(participants: list[CrmAgreementParticipantSummary], fallback: str | None) -> str | None:
    parts = [f"{item.display_name} {item.ownership_pct}%" for item in participants if item.ownership_pct]
    if parts:
        return " · ".join(parts)
    return fallback


def _parse_iso_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


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
    line1 = str(contact.address_line1 or "").strip()
    parts: list[str] = [line1] if line1 else []
    for part in (
        contact.address_line2,
        contact.city,
        contact.state_province,
        contact.postal_code,
        contact.country,
    ):
        text = str(part).strip() if part else ""
        if not text:
            continue
        if line1 and text.casefold() in line1.casefold():
            continue
        parts.append(text)
    return ", ".join(parts) or None


def _contact_responsible(contact: CrmContact) -> str | None:
    live = _contact_live(contact)
    assigned = str(live.get("assigned_name") or "").strip()
    if assigned:
        return assigned
    meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    extras = bitrix.get("source_extras") if isinstance(bitrix.get("source_extras"), dict) else {}
    responsible = str(extras.get("responsible") or "").strip()
    return responsible or None


def _participant_summaries(
    participants: list[tuple[CrmAgreementParticipant, CrmContact]],
) -> list[CrmAgreementParticipantSummary]:
    ordered = sorted(participants, key=lambda item: (not item[0].is_primary, item[1].display_name.lower()))
    items: list[CrmAgreementParticipantSummary] = []
    for row, contact in ordered:
        items.append(
            CrmAgreementParticipantSummary(
                contact_id=contact.id,
                display_name=contact.display_name,
                role=row.role,
                ownership_pct=_pct_text(row.ownership_pct),
                is_primary=bool(row.is_primary),
                source=row.source,
                phone=format_display_phone(contact.primary_phone),
                email=contact.primary_email,
                address=_contact_address(contact),
                company=contact.organization_name,
                position=contact.job_title,
                responsible=_contact_responsible(contact),
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
    meta = _meta(row)
    label = _project_label(row.project_group, meta)
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
    change_status = str(meta.get("unit_change_status") or "").strip() or None
    stage_label = change_status or _display_stage(meta, live)
    extras = _optional_fields(meta, live)
    journey = None
    if contact is not None and getattr(contact, "lifecycle_stage", None) is not None:
        raw_stage = contact.lifecycle_stage.value if hasattr(contact.lifecycle_stage, "value") else str(contact.lifecycle_stage)
        journey = _LIFECYCLE_TR.get(raw_stage, raw_stage)
    share = _share_from_participants(participant_rows, extras.get("share_ratio"))
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
        hemen_kira=bool(getattr(row, "hemen_kira", False)),
        responsible_name=extras.get("responsible_name") or (participant_rows[0].responsible if participant_rows else None),
        payment_status=extras.get("payment_status"),
        payment_method=extras.get("payment_method"),
        share_ratio=share,
        company_details=extras.get("company_details"),
        payment_dates=extras.get("payment_dates"),
        floor=extras.get("floor"),
        deposit_amount=extras.get("deposit_amount"),
        customer_journey=journey,
        potential_status=extras.get("potential_status"),
        begin_date=extras.get("begin_date"),
        close_date=extras.get("close_date"),
        joint_owners=len(participant_rows) > 1,
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
    else:
        query = query.where(~historical_unit_change_clause())
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
    next_map = _next_activity_map(db, rows, participants_map)
    items = [
        serialize_agreement(
            row,
            contact=contacts.get(row.contact_id),
            contact_name=(contacts[row.contact_id].display_name if row.contact_id in contacts else None),
            participants=participants_map.get(row.id),
        )
        for row in rows
    ]
    for item in items:
        nxt = next_map.get(item.id)
        if nxt:
            item.next_activity_title = nxt[0]
            item.next_activity_at = nxt[1]
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
    if raw in {"manual_import", "sale_document"}:
        return "Manuel belge"
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
    historical = is_historical_unit_change(row)
    amount, currency = _purchase_amount(row)
    if not amount and not historical:
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
    change_status = str(meta.get("unit_change_status") or "").strip() or None
    return CrmPurchaseSummary(
        agreement_id=row.id,
        bitrix_deal_id=deal_id,
        project_group=row.project_group,
        project_label=_project_label(row.project_group, meta),
        unit_number=row.unit_number,
        amount=amount,
        currency=currency,
        amount_label=format_money(amount, currency),
        stage=change_status or stage_label,
        begin_date=str(meta.get("begin_date") or live.get("begin_date") or "") or None,
        close_date=str(meta.get("close_date") or live.get("close_date") or "") or None,
        owners_label=_owners_label(summaries, contact.display_name if contact else None),
        participants=purchase_participants,
        opens_purchase_card=True,
        status=change_status
        or stage_label
        or (row.status.value if hasattr(row.status, "value") else str(row.status)),
        hemen_kira=bool(getattr(row, "hemen_kira", False)),
        is_historical_unit_change=historical,
        unit_change_status=change_status,
        original_unit=str(meta.get("original_unit") or "").strip() or None,
        final_unit=str(meta.get("final_unit") or "").strip() or None,
        unit_history=[],
    )


def _serialize_unit_history(focus: CrmAgreement, siblings: list[CrmAgreement]) -> list[CrmUnitHistoryStep]:
    return [
        CrmUnitHistoryStep(
            agreement_id=step.agreement_id,
            unit_number=step.unit_number,
            is_current=step.is_current,
            is_historical_unit_change=step.is_historical_unit_change,
            contact_id=step.contact_id,
        )
        for step in unit_history_steps(focus, siblings)
    ]


def _contact_project_agreements(
    db: Session,
    contact_id: UUID,
    project_group: str,
) -> list[CrmAgreement]:
    owned_ids = set(db.scalars(select(CrmAgreement.id).where(CrmAgreement.contact_id == contact_id)).all())
    participant_ids = set(
        db.scalars(
            select(CrmAgreementParticipant.agreement_id).where(CrmAgreementParticipant.contact_id == contact_id)
        ).all()
    )
    agreement_ids = owned_ids | participant_ids
    if not agreement_ids:
        return []
    return list(
        db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.id.in_(agreement_ids),
                CrmAgreement.project_group == project_group,
            )
        ).all()
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
    rows_by_project: dict[str, list[CrmAgreement]] = defaultdict(list)
    for row in rows:
        rows_by_project[row.project_group].append(row)
    for summary, row in zip(summaries, rows, strict=True):
        summary.unit_history = _serialize_unit_history(row, rows_by_project.get(row.project_group, []))
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


def set_document_surface_hidden(
    db: Session,
    *,
    document_id: UUID,
    entity_type: str,
    entity_id: UUID,
    hidden: bool,
) -> DocumentLink:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("document_not_found")
    aliases = {
        "crm_contact": ("crm_contact", "contact"),
        "contact": ("crm_contact", "contact"),
    }
    surfaces = aliases.get(entity_type, (entity_type,))
    primary: DocumentLink | None = None
    for surface in surfaces:
        link = db.scalar(
            select(DocumentLink).where(
                DocumentLink.document_id == document_id,
                DocumentLink.entity_type == surface,
                DocumentLink.entity_id == entity_id,
            )
        )
        if link is None:
            link = DocumentLink(
                document_id=document_id,
                entity_type=surface,
                entity_id=entity_id,
                relationship_type="crm_view",
            )
            db.add(link)
            db.flush()
        link.hidden_from_view = hidden
        if surface == entity_type or primary is None:
            primary = link
    db.flush()
    if primary is None:
        raise ValueError("document_not_found")
    return primary


def _document_notes(document: Document) -> dict[str, Any]:
    return document_notes(document)


def _serialize_purchase_documents(
    db: Session,
    documents: list[Document],
    *,
    hidden_ids: set[UUID],
    include_hidden: bool,
) -> list[CrmPurchaseDocument]:
    items: list[CrmPurchaseDocument] = []
    seen_docs: set[UUID] = set()
    for document in documents:
        if document.id in seen_docs:
            continue
        seen_docs.add(document.id)
        notes = document_notes(document)
        filename = _display_filename(document.original_file_name, document.title) or document.original_file_name
        hidden = document.id in hidden_ids
        if hidden and not include_hidden:
            continue
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
                checksum=document.checksum or None,
                hidden_from_view=hidden,
                created_at=document.created_at,
            )
        )
    seen_files: set[str] = set()
    unique: list[CrmPurchaseDocument] = []
    items.sort(key=lambda item: 0 if item.source == "Satış belgesi" else 1)
    for item in items:
        keys = [key for key in (item.bitrix_file_id, item.checksum, str(item.id)) if key]
        if any(key in seen_files for key in keys):
            continue
        for key in keys:
            seen_files.add(key)
        unique.append(item)
    unique.sort(
        key=lambda item: (
            0 if item.source == "Satış belgesi" else 1,
            str(item.created_at or ""),
            item.original_file_name or item.title,
        )
    )
    return unique


def purchase_documents(
    db: Session,
    agreement_id: UUID,
    deal_id: str | None = None,
    *,
    include_hidden: bool = False,
) -> list[CrmPurchaseDocument]:
    del deal_id
    links = list(
        db.scalars(
            select(DocumentLink).where(
                DocumentLink.entity_type == "crm_agreement",
                DocumentLink.entity_id == agreement_id,
            )
        ).all()
    )
    hidden_ids = {link.document_id for link in links if link.hidden_from_view}
    documents = purchase_linked_documents(db, agreement_id, include_hidden=include_hidden)
    return _serialize_purchase_documents(db, documents, hidden_ids=hidden_ids, include_hidden=include_hidden)


def person_documents_for_purchase(
    db: Session,
    *,
    contact_ids: set[UUID],
    agreement_id: UUID,
    purchase_doc_ids: set[UUID],
    include_hidden: bool = False,
) -> list[CrmPurchaseDocument]:
    owner_agreement_ids = set(
        db.scalars(
            select(CrmAgreement.id).where(
                or_(
                    CrmAgreement.contact_id.in_(contact_ids),
                    CrmAgreement.id.in_(
                        select(CrmAgreementParticipant.agreement_id).where(
                            CrmAgreementParticipant.contact_id.in_(contact_ids)
                        )
                    ),
                )
            )
        ).all()
    )
    documents = person_surface_documents(
        db,
        contact_ids,
        exclude_ids=purchase_doc_ids,
        owner_agreement_ids=owner_agreement_ids,
    )
    hidden_ids: set[UUID] = set()
    if not include_hidden:
        hidden_ids = set(
            db.scalars(
                select(DocumentLink.document_id).where(
                    DocumentLink.entity_type.in_(("crm_contact", "contact")),
                    DocumentLink.entity_id.in_(contact_ids),
                    DocumentLink.hidden_from_view.is_(True),
                )
            ).all()
        )
    return _serialize_purchase_documents(db, documents, hidden_ids=hidden_ids, include_hidden=include_hidden)


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
    *,
    include_hidden_documents: bool = False,
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
    documents = purchase_documents(
        db,
        row.id,
        summary.bitrix_deal_id,
        include_hidden=include_hidden_documents,
    )
    person_docs = person_documents_for_purchase(
        db,
        contact_ids=contact_ids,
        agreement_id=row.id,
        purchase_doc_ids={item.id for item in documents},
        include_hidden=include_hidden_documents,
    )
    meta = _meta(row)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    related: list[CrmRelatedPurchase] = []
    change_related = bool(meta.get("unit_change_status") or meta.get("historical_unit_change"))
    if is_nedim_purchase_agreement(row.id) or change_related:
        source_id = row.contact_id
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
                    is_historical_unit_change=bool(item.is_historical_unit_change),
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
        document_count=len([item for item in documents if not item.hidden_from_view]),
        person_documents=person_docs,
        person_document_count=len([item for item in person_docs if not item.hidden_from_view]),
        responsible_name=str(live.get("assigned_name") or "").strip() or None,
        comments=_plain_text(live.get("comments") or meta.get("comments")),
        agreement_date=row.agreement_date,
        related_purchases=related,
        primary_contact_name=contact.display_name if contact else None,
        llc_name=str(live.get("llc_name") or "").strip() or None,
        payment_fields=payment_fields,
        llc_fields=_labeled_values(live.get("llc_fields") or meta.get("llc_fields")),
        extra_fields=_labeled_values(live.get("extra_fields") or meta.get("extra_fields")),
        hemen_kira=bool(getattr(row, "hemen_kira", False)),
        unit_history=_serialize_unit_history(row, _contact_project_agreements(db, row.contact_id, row.project_group)),
    )


def patch_agreement_hemen_kira(db: Session, agreement_id: UUID, hemen_kira: bool) -> CrmPurchaseCard | None:
    row = get_agreement(db, agreement_id)
    if row is None:
        return None
    row.hemen_kira = bool(hemen_kira)
    db.add(row)
    db.commit()
    db.refresh(row)
    return get_purchase_card(db, agreement_id)


def _agreement_index(
    db: Session,
    *,
    project_group: str | None = None,
    contact_id: UUID | None = None,
) -> list[CrmAgreement]:
    query = select(CrmAgreement).where(~historical_unit_change_clause())
    if project_group:
        query = query.where(CrmAgreement.project_group == project_group)
    if contact_id is not None:
        query = query.where(
            or_(
                CrmAgreement.contact_id == contact_id,
                CrmAgreement.id.in_(
                    select(CrmAgreementParticipant.agreement_id).where(
                        CrmAgreementParticipant.contact_id == contact_id
                    )
                ),
            )
        )
    return list(db.scalars(query).all())


def _deal_agreement_maps(
    rows: list[CrmAgreement],
    participants_map: dict[UUID, list[tuple[CrmAgreementParticipant, CrmContact]]],
) -> tuple[dict[str, CrmAgreement], dict[UUID, CrmAgreement], set[UUID]]:
    deal_map: dict[str, CrmAgreement] = {}
    id_map: dict[UUID, CrmAgreement] = {}
    contact_ids: set[UUID] = set()
    for row in rows:
        id_map[row.id] = row
        contact_ids.add(row.contact_id)
        for participant, _contact in participants_map.get(row.id, []):
            contact_ids.add(participant.contact_id)
        deal_id = deal_id_for_agreement(row.id, _meta(row))
        if deal_id:
            deal_map[deal_id] = row
    return deal_map, id_map, contact_ids


def _next_activity_map(
    db: Session,
    rows: list[CrmAgreement],
    participants_map: dict[UUID, list[tuple[CrmAgreementParticipant, CrmContact]]],
) -> dict[UUID, tuple[str, datetime | None]]:
    if not rows:
        return {}
    deal_map, _id_map, contact_ids = _deal_agreement_maps(rows, participants_map)
    if not contact_ids:
        return {}
    now = datetime.now(tz=UTC)
    activities = list(
        db.scalars(
            select(CrmActivity).where(
                CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                CrmActivity.entity_id.in_(contact_ids),
                CrmActivity.archived_at.is_(None),
                or_(CrmActivity.due_date >= now, CrmActivity.start_date >= now),
            ).order_by(CrmActivity.due_date.asc().nullslast(), CrmActivity.start_date.asc().nullslast())
        ).all()
    )
    result: dict[UUID, tuple[str, datetime | None]] = {}
    for activity in activities:
        deal_id = activity_deal_id(activity.metadata_json if isinstance(activity.metadata_json, dict) else None)
        row = deal_map.get(deal_id) if deal_id else None
        if row is None or row.id in result:
            continue
        result[row.id] = (activity.title, activity.due_date or activity.start_date)
    return result


def _activity_actor(db: Session, activity: CrmActivity) -> str | None:
    entry = _activity_entry(db, activity)
    return entry.actor_name


def list_purchase_activities(
    db: Session,
    *,
    project_group: str | None = None,
    contact_id: UUID | None = None,
    activity_type: str | None = None,
    responsible: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[CrmAgreementActivityItem], int]:
    rows = _agreement_index(db, project_group=project_group, contact_id=contact_id)
    if not rows:
        return [], 0
    participants_map = _load_participants_map(db, {row.id for row in rows})
    deal_map, _id_map, contact_ids = _deal_agreement_maps(rows, participants_map)
    contacts = {
        contact.id: contact
        for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
    }
    query = select(CrmActivity).where(
        CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
        CrmActivity.entity_id.in_(contact_ids),
        CrmActivity.archived_at.is_(None),
    )
    if activity_type:
        try:
            query = query.where(CrmActivity.activity_type == CrmActivityType(activity_type))
        except ValueError:
            return [], 0
    if date_from is not None:
        query = query.where(
            or_(CrmActivity.created_at >= date_from, CrmActivity.start_date >= date_from, CrmActivity.due_date >= date_from)
        )
    if date_to is not None:
        query = query.where(
            or_(CrmActivity.created_at <= date_to, CrmActivity.start_date <= date_to, CrmActivity.due_date <= date_to)
        )
    activities = list(db.scalars(query.order_by(CrmActivity.created_at.desc())).all())
    items: list[CrmAgreementActivityItem] = []
    responsible_filter = (responsible or "").strip().casefold()
    for activity in activities:
        deal_id = activity_deal_id(activity.metadata_json if isinstance(activity.metadata_json, dict) else None)
        row = deal_map.get(deal_id) if deal_id else None
        if row is None:
            continue
        actor = _activity_actor(db, activity)
        if responsible_filter and (actor or "").casefold() != responsible_filter:
            continue
        contact = contacts.get(activity.entity_id)
        items.append(
            CrmAgreementActivityItem(
                id=activity.id,
                agreement_id=row.id,
                contact_id=activity.entity_id,
                contact_name=contact.display_name if contact else None,
                project_group=row.project_group,
                project_label=_project_label(row.project_group, _meta(row)),
                activity_type=activity.activity_type.value,
                title=activity.title,
                summary=activity.summary or activity.description,
                actor_name=actor,
                responsible_name=actor,
                created_at=activity.created_at,
                start_date=activity.start_date,
                due_date=activity.due_date,
            )
        )
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def list_purchase_calendar(
    db: Session,
    *,
    start: date,
    end: date,
    project_group: str | None = None,
    contact_id: UUID | None = None,
) -> list[CrmAgreementCalendarItem]:
    rows = _agreement_index(db, project_group=project_group, contact_id=contact_id)
    participants_map = _load_participants_map(db, {row.id for row in rows})
    deal_map, _id_map, contact_ids = _deal_agreement_maps(rows, participants_map)
    contacts: dict[UUID, CrmContact] = {}
    if contact_ids:
        contacts = {
            contact.id: contact
            for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
        }
    items: list[CrmAgreementCalendarItem] = []
    for row in rows:
        meta = _meta(row)
        live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
        owners = row.contact_id
        contact = contacts.get(owners)
        name = contact.display_name if contact else None
        label = _project_label(row.project_group, _meta(row))
        for kind, raw in (
            ("purchase", row.agreement_date or meta.get("begin_date") or live.get("begin_date")),
            ("closing", meta.get("close_date") or live.get("close_date")),
        ):
            parsed = raw if isinstance(raw, date) else _parse_iso_date(raw)
            if parsed is None or parsed < start or parsed > end:
                continue
            title = "Satın alma tarihi" if kind == "purchase" else "Kapanış tarihi"
            items.append(
                CrmAgreementCalendarItem(
                    id=f"{row.id}:{kind}:{parsed.isoformat()}",
                    title=f"{title} · {name or label}",
                    date=parsed,
                    kind=kind,
                    agreement_id=row.id,
                    contact_name=name,
                    project_label=label,
                )
            )
    if contact_ids:
        start_dt = datetime(start.year, start.month, start.day, tzinfo=UTC)
        end_dt = datetime(end.year, end.month, end.day, 23, 59, 59, tzinfo=UTC)
        activities = list(
            db.scalars(
                select(CrmActivity).where(
                    CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                    CrmActivity.entity_id.in_(contact_ids),
                    CrmActivity.archived_at.is_(None),
                    or_(
                        CrmActivity.start_date.between(start_dt, end_dt),
                        CrmActivity.due_date.between(start_dt, end_dt),
                    ),
                    CrmActivity.activity_type.in_(
                        {
                            CrmActivityType.MEETING,
                            CrmActivityType.ZOOM_MEETING,
                            CrmActivityType.TEAMS_MEETING,
                            CrmActivityType.INVESTOR_MEETING,
                            CrmActivityType.CONSTRUCTION_MEETING,
                            CrmActivityType.SITE_VISIT,
                            CrmActivityType.PROPERTY_TOUR,
                            CrmActivityType.TASK,
                            CrmActivityType.FOLLOW_UP,
                            CrmActivityType.REMINDER,
                            CrmActivityType.PAYMENT,
                            CrmActivityType.CLOSING,
                            CrmActivityType.INSPECTION,
                        }
                    ),
                )
            ).all()
        )
        for activity in activities:
            deal_id = activity_deal_id(activity.metadata_json if isinstance(activity.metadata_json, dict) else None)
            row = deal_map.get(deal_id) if deal_id else None
            if row is None:
                continue
            when = activity.start_date or activity.due_date
            if when is None:
                continue
            day = when.date()
            if day < start or day > end:
                continue
            contact = contacts.get(activity.entity_id)
            kind = activity.activity_type.value
            if activity.activity_type in {
                CrmActivityType.MEETING,
                CrmActivityType.ZOOM_MEETING,
                CrmActivityType.TEAMS_MEETING,
                CrmActivityType.INVESTOR_MEETING,
                CrmActivityType.CONSTRUCTION_MEETING,
                CrmActivityType.SITE_VISIT,
                CrmActivityType.PROPERTY_TOUR,
            }:
                kind = "meeting"
            elif activity.activity_type in {CrmActivityType.TASK, CrmActivityType.REMINDER}:
                kind = "task"
            elif activity.activity_type == CrmActivityType.FOLLOW_UP:
                kind = "follow_up"
            elif activity.activity_type == CrmActivityType.PAYMENT:
                kind = "payment"
            elif activity.activity_type == CrmActivityType.CLOSING:
                kind = "closing"
            items.append(
                CrmAgreementCalendarItem(
                    id=str(activity.id),
                    title=activity.title,
                    date=day,
                    kind=kind,
                    agreement_id=row.id,
                    contact_name=contact.display_name if contact else None,
                    project_label=_project_label(row.project_group, _meta(row)),
                    activity_type=activity.activity_type.value,
                )
            )
    items.sort(key=lambda item: (item.date, item.title))
    return items
