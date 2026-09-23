"""Person vs purchase document classification. No writes. No unit-history changes."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.document import Document, DocumentLink

IDENTITY_RE = re.compile(
    r"pasaport|passport|kimlik|n[uü]fus|ehliyet|green.?card|\bvisa\b|id[_\- ]?(?:card|copy|fot)",
    re.I,
)
UNIT_RE = re.compile(
    r"(?:H[\s_-]*PL[\s_-]*)(B?0*\d{1,3})"
    r"|(?:unit|daire|(?<![A-Za-z])d)[\s_-]*(\d{3}|B0\d)"
    r"|(?<![A-Za-z0-9])(B0*\d{1,2}|\d{3})(?![A-Za-z0-9])",
    re.I,
)
SKIP_UNITS = {
    "1812",
    "1820",
    "1307",
    "2319",
    "2617",
    "3380",
    "3346",
    "3348",
    "3088",
}
PROJECT_MARKERS: dict[str, tuple[str, ...]] = {
    "1812_h_pl": ("1812", "1820 h", "h place", "h pl ", "h-pl", "1812h"),
    "uniloft": ("uniloft",),
    "1307_k_st": ("1307", "k street", "k-st"),
    "2319_ontario": ("2319", "ontario"),
    "the_temple": ("temple",),
    "2617_penn": ("2617", "penn"),
}


def document_notes(document: Document) -> dict[str, Any]:
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


def document_filename(document: Document) -> str:
    return str(document.original_file_name or document.title or "").strip()


def is_identity_document(document: Document) -> bool:
    notes = document_notes(document)
    hay = " ".join(
        [
            document_filename(document),
            str(notes.get("source_type") or ""),
            str(notes.get("bitrix_field_label") or notes.get("field_label") or ""),
            str(notes.get("class") or notes.get("kind") or ""),
        ]
    )
    if IDENTITY_RE.search(hay):
        return True
    label = str(notes.get("bitrix_field_label") or notes.get("field_label") or "").casefold()
    return any(token in label for token in ("pasaport", "passport", "kimlik", "identification"))


def fold(value: str | None) -> str:
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


def norm_unit(token: str | None) -> str | None:
    raw = re.sub(r"\s+", "", str(token or "").strip().upper())
    raw = re.sub(r"^(UNIT|DAIRE|D)", "", raw)
    if not raw:
        return None
    if raw.startswith("B"):
        digits = re.sub(r"\D", "", raw).lstrip("0") or "0"
        if digits.isdigit() and int(digits) <= 20:
            return f"B{digits.zfill(2)}"
        return None
    digits = re.sub(r"\D", "", raw)
    if not digits or digits in SKIP_UNITS:
        return None
    if re.fullmatch(r"20\d{2}|19\d{2}", digits):
        return None
    if len(digits) == 3:
        return digits
    if len(digits) == 2 and digits.startswith("0"):
        return None
    return None


def extract_units(text: str | None) -> set[str]:
    found: set[str] = set()
    for match in UNIT_RE.finditer(text or ""):
        token = next((group for group in match.groups() if group), "")
        unit = norm_unit(token)
        if unit:
            found.add(unit)
    compact = fold(text).replace(" ", "").replace("_", "").replace("-", "")
    for extra in re.findall(r"b00*(\d{1,2})", compact):
        unit = norm_unit(f"B{extra}")
        if unit:
            found.add(unit)
    return found


def agreement_units(agreement: CrmAgreement) -> set[str]:
    raw = str(agreement.unit_number or "").strip()
    if not raw:
        return set()
    parts = re.split(r"[,+/]| and ", raw, flags=re.I)
    units: set[str] = set()
    for part in parts:
        unit = norm_unit(part)
        if unit:
            units.add(unit)
        units |= extract_units(part)
    return units


def filename_projects(text: str | None) -> set[str]:
    hay = fold(text)
    hits: set[str] = set()
    for project, markers in PROJECT_MARKERS.items():
        if any(marker in hay for marker in markers):
            hits.add(project)
    return hits


def linked_documents(
    db: Session,
    *,
    entity_type: str,
    entity_id: UUID,
) -> list[tuple[DocumentLink, Document]]:
    types = ("crm_contact", "contact") if entity_type in {"crm_contact", "contact"} else (entity_type,)
    return list(
        db.execute(
            select(DocumentLink, Document)
            .join(Document, Document.id == DocumentLink.document_id)
            .where(DocumentLink.entity_type.in_(types), DocumentLink.entity_id == entity_id)
        ).all()
    )


def purchase_linked_documents(
    db: Session,
    agreement_id: UUID,
    *,
    include_hidden: bool = False,
) -> list[Document]:
    rows = linked_documents(db, entity_type="crm_agreement", entity_id=agreement_id)
    documents: list[Document] = []
    seen: set[UUID] = set()
    for link, document in rows:
        if document.id in seen:
            continue
        if link.hidden_from_view and not include_hidden:
            continue
        if is_identity_document(document):
            continue
        seen.add(document.id)
        documents.append(document)
    return documents


def person_surface_documents(
    db: Session,
    contact_ids: set[UUID],
    *,
    exclude_ids: set[UUID],
    owner_agreement_ids: set[UUID],
) -> list[Document]:
    documents: list[Document] = []
    seen: set[UUID] = set(exclude_ids)
    purchase_linked: set[UUID] = set()
    if owner_agreement_ids:
        purchase_linked = set(
            db.scalars(
                select(DocumentLink.document_id).where(
                    DocumentLink.entity_type == "crm_agreement",
                    DocumentLink.entity_id.in_(owner_agreement_ids),
                )
            ).all()
        )
    for contact_id in contact_ids:
        for _link, document in linked_documents(db, entity_type="crm_contact", entity_id=contact_id):
            if document.id in seen:
                continue
            identity = is_identity_document(document)
            if not identity:
                if document.id in purchase_linked:
                    continue
                if extract_units(document_filename(document)):
                    continue
            seen.add(document.id)
            documents.append(document)
    return documents
