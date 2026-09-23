"""CRM document hub — live documents, checksum/source-file dedupe, no link moves."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document, DocumentLink
from investhome_api.schemas.crm_documents import CrmDocumentFeedItem, CrmDocumentFeedResponse, CrmDocumentFeedStats
from investhome_api.services.crm.agreement_service import _display_filename, _document_source_label
from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup
from investhome_api.services.crm.document_surface import (
    agreement_units,
    document_filename,
    document_notes,
    extract_units,
    is_identity_document,
)

CRM_LINK_TYPES = ("crm_contact", "contact", "crm_agreement")
PURCHASE_SOURCES = {
    "deal_uf",
    "uf",
    "sale_document",
    "crm.deal.get",
    "entity_field",
    "manual_import",
    "manual_import_1812",
    "manual_import_final_agreements",
}
CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("passport", ("pasaport", "passport", "kimlik", "nufus", "ehliyet", "green card", "id card")),
    ("reservation", ("on rezervasyon", "ön rezervasyon", "reservation", "rezervasyon sozles")),
    ("operating_agreement", ("operating agreement", "isletme sozlesmesi")),
    ("llc", ("llc", "certificate of", "sertifika", "articles of organiz")),
    ("payment", ("swift", "dekont", "wire", "havale", "odeme", "payment")),
    ("closing", ("closing", "title", "tapu", "settlement")),
    ("offer", ("teklif", "offer", "proposal")),
    ("warranty", ("warranty", "garanti", "teslim tutanak", "delivery")),
    ("correspondence", ("correspondence", "yazisma", "email", "e-posta")),
)
CATEGORY_LABELS = {
    "passport": "Pasaport / Kimlik",
    "reservation": "Ön Rezervasyon",
    "operating_agreement": "Operating Agreement",
    "llc": "LLC / Certificate",
    "payment": "SWIFT / Dekont",
    "closing": "Closing / Title",
    "offer": "Teklif",
    "warranty": "Warranty / Teslim",
    "correspondence": "Correspondence",
    "other": "Diğer",
}
TYPE_CATEGORIES = {
    "operating_agreement": "operating_agreement",
    "subscription_agreement": "operating_agreement",
    "title_document": "closing",
    "closing_document": "closing",
    "correspondence": "correspondence",
    "invoice": "payment",
    "receipt": "payment",
    "bank_statement": "payment",
}
SOURCE_LABELS = {
    "comment": "Yorum eki",
    "manual_import_1812": "1812 içe aktarma",
    "manual_import_final_agreements": "Manuel belge",
    "entity_field": "Satış belgesi",
    "crm.deal.get": "Satın alma belgesi",
}


def _fold(value: str | None) -> str:
    return (
        (value or "")
        .casefold()
        .replace("ı", "i")
        .replace("ş", "s")
        .replace("ç", "c")
        .replace("ö", "o")
        .replace("ü", "u")
        .replace("ğ", "g")
    )


def _notes(document: Document) -> dict:
    return document_notes(document)


def _project_label(group: str | None) -> str | None:
    if not group:
        return None
    try:
        return BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup(group)]
    except ValueError:
        return group


def _deal_id(agreement: CrmAgreement) -> str | None:
    source = str(agreement.source_external_id or "")
    if source.startswith("bitrix_deal:"):
        return source.split(":", 1)[-1] or None
    if source.startswith("bitrix:"):
        tail = source.rsplit(":", 1)[-1].strip()
        return tail or None
    meta = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    for raw in (meta.get("bitrix_deal_id"), live.get("bitrix_deal_id"), source):
        value = str(raw or "").strip()
        if value.isdigit():
            return value
    return None


def _source_type(notes: dict) -> str:
    return str(notes.get("source_type") or notes.get("source") or "").strip().lower()


def _is_purchase_source(notes: dict) -> bool:
    if _source_type(notes) in PURCHASE_SOURCES:
        return True
    return str(notes.get("bitrix_entity_type") or "").strip().lower() == "deal"


def _deal_owned(notes: dict, deal_id: str | None) -> bool:
    if not deal_id:
        return False
    return (
        str(notes.get("bitrix_entity_type") or "").strip().lower() == "deal"
        and str(notes.get("bitrix_entity_id") or "").strip() == str(deal_id)
    )


def _source_label(notes: dict) -> str | None:
    raw = _source_type(notes)
    if raw in SOURCE_LABELS:
        return SOURCE_LABELS[raw]
    return _document_source_label(notes)


def _category(document: Document, notes: dict) -> str:
    type_key = document.document_type.value if hasattr(document.document_type, "value") else str(document.document_type or "")
    mapped = TYPE_CATEGORIES.get(type_key.lower())
    if mapped:
        return mapped
    hay = _fold(
        " ".join(
            [
                document_filename(document),
                str(document.category or ""),
                str(notes.get("bitrix_field_label") or notes.get("field_label") or ""),
                str(notes.get("class") or notes.get("kind") or ""),
            ]
        )
    )
    for key, tokens in CATEGORY_RULES:
        if any(token in hay for token in tokens):
            return key
    return "other"


def _binary_keys(document: Document, notes: dict) -> list[str]:
    keys: list[str] = []
    file_id = str(notes.get("bitrix_file_id") or "").strip()
    if file_id:
        keys.append(f"bx:{file_id}")
    checksum = str(document.checksum or "").strip()
    if checksum:
        keys.append(f"sum:{checksum}")
    keys.append(f"id:{document.id}")
    return keys


def _rank(document: Document, notes: dict) -> tuple[int, int, str]:
    source = _source_type(notes)
    preferred = 0 if source in PURCHASE_SOURCES or source in {"deal_uf", "uf"} else 1
    return (preferred, -int(document.file_size or 0), str(document.created_at or ""))


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _occurred(document: Document) -> datetime | None:
    if document.document_date:
        return datetime.combine(document.document_date, datetime.min.time(), tzinfo=timezone.utc)
    return _as_utc(document.created_at or document.updated_at)


def set_document_hub_hidden(db: Session, document_id: UUID, hidden: bool) -> tuple[Document, int]:
    document = db.get(Document, document_id)
    if document is None:
        raise ValueError("document_not_found")
    links = list(
        db.scalars(
            select(DocumentLink).where(
                DocumentLink.document_id == document_id,
                DocumentLink.entity_type.in_(CRM_LINK_TYPES),
            )
        ).all()
    )
    if not links:
        raise ValueError("document_not_found")
    for link in links:
        link.hidden_from_view = hidden
    db.flush()
    return document, len(links)


def _classify(
    document: Document,
    *,
    notes: dict,
    agreements: list[CrmAgreement],
) -> tuple[str, CrmAgreement | None]:
    if is_identity_document(document):
        return "person", None
    file_units = extract_units(document_filename(document))
    if len(agreements) == 1:
        return "purchase", agreements[0]
    if len(agreements) > 1:
        deal_hits = [row for row in agreements if _deal_owned(notes, _deal_id(row))]
        unit_hits = [row for row in agreements if file_units and file_units & agreement_units(row)]
        if len(deal_hits) == 1:
            return "purchase", deal_hits[0]
        if len(unit_hits) == 1:
            return "purchase", unit_hits[0]
        return "unresolved", None
    if _is_purchase_source(notes) or file_units:
        return "unresolved", None
    return "person", None


def _serialize(
    document: Document,
    *,
    notes: dict,
    contacts: list[CrmContact],
    agreement: CrmAgreement | None,
    scope: str,
    hidden: bool,
) -> CrmDocumentFeedItem:
    filename = _display_filename(document.original_file_name, document.title) or document_filename(document) or document.title
    category = _category(document, notes)
    contact = contacts[0] if contacts else None
    file_units = extract_units(filename)
    filename_unit = next(iter(sorted(file_units)), None)
    current_unit = str(agreement.unit_number or "").strip() or None if agreement else None
    historical_unit = None
    if filename_unit and current_unit:
        current_set = agreement_units(agreement) if agreement else set()
        if filename_unit not in current_set:
            historical_unit = filename_unit
    display_unit = historical_unit or filename_unit or current_unit
    project_group = agreement.project_group if agreement else None
    project_label = _project_label(project_group)
    project_unit = " · ".join([item for item in [project_label, display_unit] if item]) or None
    if scope == "unresolved":
        status = "inceleme"
    elif hidden:
        status = "gizli"
    else:
        status = "gorunur"
    previewable = str(document.mime_type or "").lower().startswith("image/") or "pdf" in str(document.mime_type or "").lower() or str(filename).lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".gif", ".webp"))
    return CrmDocumentFeedItem(
        id=document.id,
        source_key=_binary_keys(document, notes)[0],
        filename=filename,
        category=category,
        category_label=CATEGORY_LABELS.get(category, CATEGORY_LABELS["other"]),
        mime_type=document.mime_type,
        file_size=int(document.file_size or 0),
        file_kind=document.file_kind.value if hasattr(document.file_kind, "value") else str(document.file_kind or "") or None,
        source=_source_label(notes),
        source_type=_source_type(notes) or None,
        occurred_at=_occurred(document),
        hidden=hidden,
        scope=scope,
        status=status,
        contact_id=contact.id if contact else None,
        contact_name=contact.display_name if contact else None,
        agreement_id=agreement.id if agreement and scope == "purchase" else None,
        project_group=project_group if scope == "purchase" else None,
        project_label=project_label if scope == "purchase" else None,
        unit_number=display_unit,
        current_unit=current_unit if scope == "purchase" else None,
        historical_unit=historical_unit if scope == "purchase" else None,
        project_unit=project_unit if scope == "purchase" else (display_unit if scope == "unresolved" else None),
        checksum=str(document.checksum or "") or None,
        bitrix_file_id=str(notes.get("bitrix_file_id") or "") or None,
        previewable=previewable,
        extra_contact_count=max(0, len(contacts) - 1),
    )


def list_document_feed(
    db: Session,
    *,
    search: str | None = None,
    person: str | None = None,
    project_group: str | None = None,
    unit: str | None = None,
    category: str | None = None,
    source: str | None = None,
    visibility: str | None = None,
    scope: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    page_size: int = 25,
) -> CrmDocumentFeedResponse:
    link_rows = list(
        db.execute(
            select(Document, DocumentLink)
            .join(DocumentLink, DocumentLink.document_id == Document.id)
            .where(
                Document.archived_at.is_(None),
                Document.is_demo.is_(False),
                DocumentLink.entity_type.in_(CRM_LINK_TYPES),
            )
        ).all()
    )
    by_doc: dict[UUID, dict] = {}
    contact_ids: set[UUID] = set()
    agreement_ids: set[UUID] = set()
    for document, link in link_rows:
        bucket = by_doc.setdefault(
            document.id,
            {"document": document, "links": [], "contact_ids": set(), "agreement_ids": set()},
        )
        bucket["links"].append(link)
        if link.entity_type in {"crm_contact", "contact"}:
            bucket["contact_ids"].add(link.entity_id)
            contact_ids.add(link.entity_id)
        elif link.entity_type == "crm_agreement":
            bucket["agreement_ids"].add(link.entity_id)
            agreement_ids.add(link.entity_id)

    contacts = {item.id: item for item in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()} if contact_ids else {}
    agreements = {item.id: item for item in db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(agreement_ids))).all()} if agreement_ids else {}

    ranked: list[tuple[tuple, Document, dict, list[CrmContact], list[CrmAgreement], bool]] = []
    for bucket in by_doc.values():
        document: Document = bucket["document"]
        notes = _notes(document)
        doc_contacts = [contacts[item] for item in sorted(bucket["contact_ids"]) if item in contacts]
        doc_agreements = [agreements[item] for item in bucket["agreement_ids"] if item in agreements]
        hidden = any(bool(link.hidden_from_view) for link in bucket["links"])
        ranked.append((_rank(document, notes), document, notes, doc_contacts, doc_agreements, hidden))
    ranked.sort(key=lambda item: item[0])

    chosen: dict[str, CrmDocumentFeedItem] = {}
    order: list[str] = []
    for _rank_key, document, notes, doc_contacts, doc_agreements, hidden in ranked:
        keys = _binary_keys(document, notes)
        if any(key in chosen for key in keys):
            continue
        scope_value, agreement = _classify(document, notes=notes, agreements=doc_agreements)
        if agreement and agreement.contact_id and agreement.contact_id in {item.id for item in doc_contacts}:
            doc_contacts = sorted(doc_contacts, key=lambda item: 0 if item.id == agreement.contact_id else 1)
        item = _serialize(
            document,
            notes=notes,
            contacts=doc_contacts,
            agreement=agreement,
            scope=scope_value,
            hidden=hidden,
        )
        for key in keys:
            chosen[key] = item
        order.append(keys[0])

    unique = [chosen[key] for key in order]
    stats = CrmDocumentFeedStats(
        total=len(unique),
        person=sum(1 for item in unique if item.scope == "person"),
        purchase=sum(1 for item in unique if item.scope == "purchase"),
        hidden=sum(1 for item in unique if item.hidden),
        unresolved=sum(1 for item in unique if item.scope == "unresolved"),
    )

    visibility_mode = (visibility or "visible").strip().lower()
    filtered = unique
    if visibility_mode == "hidden":
        filtered = [item for item in filtered if item.hidden]
    elif visibility_mode != "all":
        filtered = [item for item in filtered if not item.hidden]
    if scope in {"person", "purchase", "unresolved"}:
        filtered = [item for item in filtered if item.scope == scope]
    if search:
        needle = search.strip().casefold()
        filtered = [
            item
            for item in filtered
            if needle in (item.filename or "").casefold()
            or needle in (item.contact_name or "").casefold()
            or needle in (item.project_unit or "").casefold()
        ]
    if person:
        needle = person.strip().casefold()
        filtered = [item for item in filtered if needle in (item.contact_name or "").casefold()]
    if project_group:
        filtered = [item for item in filtered if item.project_group == project_group]
    if unit:
        needle = unit.strip().casefold()
        filtered = [
            item
            for item in filtered
            if needle in (item.unit_number or "").casefold()
            or needle in (item.current_unit or "").casefold()
            or needle in (item.historical_unit or "").casefold()
        ]
    if category:
        filtered = [item for item in filtered if item.category == category]
    if source:
        needle = source.strip().casefold()
        filtered = [
            item
            for item in filtered
            if needle in (item.source or "").casefold() or needle == (item.source_type or "")
        ]
    start_at = _as_utc(date_from)
    end_at = _as_utc(date_to)
    if start_at is not None:
        filtered = [item for item in filtered if item.occurred_at and _as_utc(item.occurred_at) >= start_at]
    if end_at is not None:
        filtered = [item for item in filtered if item.occurred_at and _as_utc(item.occurred_at) <= end_at]

    filtered.sort(key=lambda item: _as_utc(item.occurred_at) or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    total = len(filtered)
    start = max(page - 1, 0) * page_size
    page_items = filtered[start : start + page_size]
    return CrmDocumentFeedResponse(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size) if total else 1,
        stats=stats,
    )
