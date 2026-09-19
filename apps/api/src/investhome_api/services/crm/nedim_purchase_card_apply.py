"""Apply Nedim purchase-card pilot data. Does not delete records."""
from __future__ import annotations

import json
import os
import urllib.parse
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.document import Document, DocumentLink
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.crm.nedim_purchase_card import (
    AGREEMENT_198,
    AGREEMENT_656,
    AGREEMENT_720,
    DEAL_198,
    DEAL_656,
    DEAL_720,
    DEAL_UF_FILES,
    NEDIM_CANONICAL_ID,
    DEAL_TO_AGREEMENT,
)

IZZET_CONTACT_ID = "1160"
NEDIM_BITRIX_CONTACT = "588"

DEAL_META = {
    DEAL_198: {
        "bitrix_deal_id": DEAL_198,
        "stage_id": "C8:WON",
        "stage_label": "WON",
        "begin_date": "2024-07-31",
        "close_date": "2025-02-27",
        "opportunity": "800250.00",
        "currency": "USD",
        "source": "bitrix_live",
    },
    DEAL_656: {
        "bitrix_deal_id": DEAL_656,
        "stage_id": "C26:FINAL_INVOICE",
        "stage_label": "FINAL_INVOICE",
        "begin_date": "2025-11-14",
        "close_date": None,
        "opportunity": "330757.00",
        "currency": "USD",
        "source": "bitrix_live",
    },
    DEAL_720: {
        "bitrix_deal_id": DEAL_720,
        "stage_id": "C26:FINAL_INVOICE",
        "stage_label": "FINAL_INVOICE",
        "begin_date": "2026-03-17",
        "close_date": None,
        "opportunity": "470000.00",
        "currency": "USD",
        "source": "bitrix_live",
    },
}


def _notes(document: Document) -> dict[str, Any]:
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


def _find_izzet(db: Session) -> CrmContact | None:
    for contact in db.scalars(select(CrmContact)).all():
        blob = json.dumps(contact.metadata_json or {}, ensure_ascii=False)
        if f"bitrix_contact:{IZZET_CONTACT_ID}" in blob:
            return contact
        live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
        if isinstance(live, dict) and str(live.get("contact_id") or "") == IZZET_CONTACT_ID:
            return contact
        if (contact.primary_email or "").strip().lower() == "izzetk@gmail.com":
            return contact
    return None


def ensure_izzet(db: Session) -> CrmContact:
    existing = _find_izzet(db)
    if existing is not None:
        meta = dict(existing.metadata_json or {})
        bitrix = dict(meta.get("bitrix_import") or {}) if isinstance(meta.get("bitrix_import"), dict) else {}
        ids = [str(item) for item in (bitrix.get("external_ids") or [])]
        token = f"bitrix_contact:{IZZET_CONTACT_ID}"
        if token not in ids:
            ids.append(token)
            bitrix["external_ids"] = ids
            bitrix.setdefault("source_files", ["bitrix_live"])
            bitrix.setdefault("source_roles", ["contact"])
            meta["bitrix_import"] = bitrix
        live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
        live.setdefault("contact_id", IZZET_CONTACT_ID)
        live.setdefault("assigned_by_name", "Beyza Karakuş")
        live.setdefault("lead_id", None)
        meta["bitrix_live"] = live
        existing.metadata_json = meta
        if existing.source != "bitrix_live":
            existing.source = "bitrix_live"
        db.flush()
        return existing

    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.BUYER,
            record_kind=CrmRecordKind.PERSON,
            display_name="İzzet Kondu Levi Dinçer",
            first_name="İzzet",
            last_name="Kondu Levi Dinçer",
            primary_phone="+41795969733",
            primary_email="izzetk@gmail.com",
            source="bitrix_live",
            status=CrmContactStatus.ACTIVE,
        ),
    )
    contact.metadata_json = {
        "bitrix_import": {
            "external_ids": [f"bitrix_contact:{IZZET_CONTACT_ID}"],
            "source_files": ["bitrix_live"],
            "source_roles": ["contact"],
        },
        "bitrix_live": {
            "contact_id": IZZET_CONTACT_ID,
            "assigned_by_name": "Beyza Karakuş",
            "lead_id": None,
        },
    }
    db.flush()
    return contact


def _merge_meta(row: CrmAgreement, extra: dict[str, Any]) -> None:
    meta = dict(row.metadata_json or {})
    live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
    for key, value in extra.items():
        if value is None:
            continue
        meta[key] = value
        live[key] = value
    meta["bitrix_live"] = live
    row.metadata_json = meta


def ensure_deal_metadata(db: Session) -> None:
    for deal_id, agreement_id in DEAL_TO_AGREEMENT.items():
        row = db.get(CrmAgreement, agreement_id)
        if row is None:
            continue
        _merge_meta(row, DEAL_META[deal_id])
        if not row.investment_amount:
            row.investment_amount = DEAL_META[deal_id]["opportunity"]
    db.flush()


def _upsert_participant(
    db: Session,
    *,
    agreement_id: UUID,
    contact_id: UUID,
    ownership_pct: str,
    is_primary: bool,
    role: str,
    deal_id: str,
) -> CrmAgreementParticipant:
    existing = db.scalar(
        select(CrmAgreementParticipant).where(
            CrmAgreementParticipant.agreement_id == agreement_id,
            CrmAgreementParticipant.contact_id == contact_id,
        )
    )
    if existing is None:
        existing = CrmAgreementParticipant(
            id=uuid4(),
            agreement_id=agreement_id,
            contact_id=contact_id,
            role=role,
            ownership_pct=Decimal(ownership_pct),
            is_primary=is_primary,
            source="bitrix_live",
            metadata_json={"bitrix_deal_id": deal_id, "source": "bitrix_live"},
        )
        db.add(existing)
    else:
        existing.role = role
        existing.ownership_pct = Decimal(ownership_pct)
        existing.is_primary = is_primary
        existing.source = "bitrix_live"
        meta = dict(existing.metadata_json or {})
        meta["bitrix_deal_id"] = deal_id
        meta["source"] = "bitrix_live"
        existing.metadata_json = meta
    db.flush()
    return existing


def ensure_participants(db: Session, izzet_id: UUID) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {}
    _upsert_participant(
        db,
        agreement_id=AGREEMENT_198,
        contact_id=NEDIM_CANONICAL_ID,
        ownership_pct="100.00",
        is_primary=True,
        role="owner",
        deal_id=DEAL_198,
    )
    created[DEAL_198] = [str(NEDIM_CANONICAL_ID)]
    _upsert_participant(
        db,
        agreement_id=AGREEMENT_656,
        contact_id=NEDIM_CANONICAL_ID,
        ownership_pct="100.00",
        is_primary=True,
        role="owner",
        deal_id=DEAL_656,
    )
    created[DEAL_656] = [str(NEDIM_CANONICAL_ID)]
    _upsert_participant(
        db,
        agreement_id=AGREEMENT_720,
        contact_id=NEDIM_CANONICAL_ID,
        ownership_pct="50.00",
        is_primary=True,
        role="owner",
        deal_id=DEAL_720,
    )
    _upsert_participant(
        db,
        agreement_id=AGREEMENT_720,
        contact_id=izzet_id,
        ownership_pct="50.00",
        is_primary=False,
        role="owner",
        deal_id=DEAL_720,
    )
    created[DEAL_720] = [str(NEDIM_CANONICAL_ID), str(izzet_id)]
    return created


def _link_agreement_doc(db: Session, document_id: UUID, agreement_id: UUID) -> bool:
    exists = db.scalar(
        select(DocumentLink.id).where(
            DocumentLink.document_id == document_id,
            DocumentLink.entity_type == "crm_agreement",
            DocumentLink.entity_id == agreement_id,
        )
    )
    if exists:
        return False
    db.add(
        DocumentLink(
            document_id=document_id,
            entity_type="crm_agreement",
            entity_id=agreement_id,
            relationship_type="bitrix_deal_file",
        )
    )
    return True


def link_existing_deal_documents(db: Session) -> dict[str, list[str]]:
    linked: dict[str, list[str]] = {DEAL_198: [], DEAL_656: [], DEAL_720: []}
    wanted_files = {file_id: deal_id for deal_id, files in DEAL_UF_FILES.items() for file_id in files}
    candidates: list[Document] = []
    for deal_id, files in DEAL_UF_FILES.items():
        clause_hits = list(
            db.scalars(
                select(Document).where(
                    Document.notes.is_not(None),
                    Document.notes.ilike(f"%{deal_id}%"),
                )
            ).all()
        )
        candidates.extend(clause_hits)
        for file_id in files:
            candidates.extend(
                db.scalars(
                    select(Document).where(
                        Document.notes.is_not(None),
                        Document.notes.ilike(f"%{file_id}%"),
                    )
                ).all()
            )
    seen: set[UUID] = set()
    for document in candidates:
        if document.id in seen:
            continue
        seen.add(document.id)
        notes = _notes(document)
        file_id = str(notes.get("bitrix_file_id") or "").strip()
        entity_type = str(notes.get("bitrix_entity_type") or "").lower()
        entity_id = str(notes.get("bitrix_entity_id") or "").strip()
        deal_id = None
        if entity_type == "deal" and entity_id in DEAL_TO_AGREEMENT:
            deal_id = entity_id
        elif file_id in wanted_files:
            deal_id = wanted_files[file_id]
        if not deal_id:
            continue
        agreement_id = DEAL_TO_AGREEMENT[deal_id]
        if _link_agreement_doc(db, document.id, agreement_id):
            linked[deal_id].append(str(document.id))
        elif str(document.id) not in linked[deal_id]:
            linked[deal_id].append(str(document.id))
    db.flush()
    return linked


def cleanup_false_agreement_links(db: Session) -> dict[str, Any]:
    removed: dict[str, int] = {DEAL_198: 0, DEAL_656: 0, DEAL_720: 0}
    kept: dict[str, int] = {DEAL_198: 0, DEAL_656: 0, DEAL_720: 0}
    wanted_files = {file_id: deal_id for deal_id, files in DEAL_UF_FILES.items() for file_id in files}
    for deal_id, agreement_id in DEAL_TO_AGREEMENT.items():
        links = list(
            db.scalars(
                select(DocumentLink).where(
                    DocumentLink.entity_type == "crm_agreement",
                    DocumentLink.entity_id == agreement_id,
                )
            ).all()
        )
        for link in links:
            document = db.get(Document, link.document_id)
            notes = _notes(document) if document is not None else {}
            file_id = str(notes.get("bitrix_file_id") or "").strip()
            entity_type = str(notes.get("bitrix_entity_type") or "").lower()
            entity_id = str(notes.get("bitrix_entity_id") or "").strip()
            ok = (entity_type == "deal" and entity_id == deal_id) or (
                file_id in wanted_files and wanted_files[file_id] == deal_id
            )
            if ok:
                kept[deal_id] += 1
            else:
                db.delete(link)
                removed[deal_id] += 1
    db.flush()
    return {"removed": removed, "kept": kept}


def _webhook_base() -> str:
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip().strip('"').strip("'")
    marker = "BURAYA_BITRIX_URL="
    if marker in raw:
        raw = raw.split(marker, 1)[1].strip()
    parsed = urllib.parse.urlparse(raw)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(segs) + "/", "", "", ""))


def _import_uf_files(db: Session) -> dict[str, Any]:
    webhook = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    if not webhook:
        return {"imported": {}, "skipped": "no_webhook"}
    try:
        from investhome_api.models.document import (
            ConfidentialityLevel,
            DocumentStatus,
            DocumentType,
            DocumentVisibility,
            DocumentWorkspaceFolder,
            ProcessingStatus,
        )
        from investhome_api.models.user_auth import User
        from investhome_api.config.documents_config import infer_file_kind
        from investhome_api.services.document_validation import compute_checksum, generate_storage_key
        from investhome_api.services.storage.factory import get_storage_provider, provider_enum
        from io import BytesIO
        import urllib.parse
        import urllib.request
        import time
    except Exception as exc:  # noqa: BLE001
        return {"imported": {}, "skipped": str(exc)[:200]}

    base = _webhook_base()
    imported: dict[str, list[str]] = {DEAL_198: [], DEAL_656: [], DEAL_720: []}
    failed: dict[str, list[str]] = {DEAL_198: [], DEAL_656: [], DEAL_720: []}
    actor = db.scalar(select(User).order_by(User.created_at.asc()))
    storage = get_storage_provider()

    def call(method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = urllib.parse.urljoin(base, method + ".json")
        data = urllib.parse.urlencode(payload, doseq=True).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def download(url: str) -> tuple[bytes | None, str | None, str | None]:
        if not url:
            return None, None, None
        parsed_base = urllib.parse.urlparse(base)
        origin = f"{parsed_base.scheme}://{parsed_base.netloc}"
        absolute = urllib.parse.urljoin(origin + "/", url)
        req = urllib.request.Request(absolute, method="GET")
        with urllib.request.urlopen(req, timeout=90) as resp:
            content = resp.read()
            if not content or content[:1] == b"<":
                return None, None, None
            mime = resp.headers.get("Content-Type")
            disposition = resp.headers.get("Content-Disposition") or ""
            fname = None
            if "filename=" in disposition:
                fname = disposition.split("filename=", 1)[1].strip().strip('"').strip("'")
            return content, fname, mime

    def already_for_file(file_id: str) -> Document | None:
        rows = list(
            db.scalars(select(Document).where(Document.notes.is_not(None), Document.notes.ilike(f"%{file_id}%"))).all()
        )
        for document in rows:
            notes = _notes(document)
            if str(notes.get("bitrix_file_id") or "") == file_id:
                return document
        return None

    for deal_id, wanted in DEAL_UF_FILES.items():
        time.sleep(0.3)
        try:
            body = call("crm.item.get", {"entityTypeId": 2, "id": deal_id})
        except Exception as exc:  # noqa: BLE001
            failed[deal_id].append(type(exc).__name__)
            continue
        item = (body.get("result") or {}).get("item") if isinstance(body.get("result"), dict) else None
        if not isinstance(item, dict):
            failed[deal_id].append(str(body.get("error") or "item_empty")[:80])
            continue
        file_nodes: dict[str, dict[str, Any]] = {}
        def collect(value: Any) -> None:
            if isinstance(value, dict) and str(value.get("id") or "") in wanted:
                file_nodes[str(value.get("id"))] = value
            elif isinstance(value, list):
                for nested in value:
                    collect(nested)

        for value in item.values():
            collect(value)
        for file_id in wanted:
            existing = already_for_file(file_id)
            if existing is not None:
                _link_agreement_doc(db, existing.id, DEAL_TO_AGREEMENT[deal_id])
                imported[deal_id].append(str(existing.id))
                continue
            node = file_nodes.get(file_id) or {}
            try:
                content, downloaded_name, downloaded_mime = download(
                    str(
                        node.get("urlMachine")
                        or node.get("downloadUrl")
                        or node.get("url")
                        or node.get("DOWNLOAD_URL")
                        or ""
                    )
                )
            except Exception as exc:  # noqa: BLE001
                failed[deal_id].append(f"{file_id}:{type(exc).__name__}")
                continue
            if not content:
                failed[deal_id].append(file_id)
                continue
            filename = str(downloaded_name or node.get("name") or node.get("fileName") or f"bitrix-file-{file_id}")
            mime = downloaded_mime or "application/octet-stream"
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
            stored_name, storage_key = generate_storage_key(ext)
            checksum = compute_checksum(content)
            storage.save(storage_key, BytesIO(content), content_length=len(content))
            notes = json.dumps(
                {
                    "source": "bitrix_live",
                    "bitrix_file_id": file_id,
                    "bitrix_entity_type": "deal",
                    "bitrix_entity_id": deal_id,
                    "source_type": "deal_uf",
                    "import_key": f"bitrix_deal:{deal_id}:file:{file_id}",
                },
                ensure_ascii=False,
            )
            document = Document(
                title=(filename.rsplit(".", 1)[0] if "." in filename else filename)[:500],
                original_file_name=filename[:500],
                stored_file_name=stored_name,
                file_extension=ext[:20],
                mime_type=mime[:120],
                file_size=len(content),
                storage_provider=provider_enum(),
                storage_key=storage_key,
                checksum=checksum,
                document_type=DocumentType.OTHER,
                category="bitrix",
                folder=DocumentWorkspaceFolder.CONTRACTS,
                file_kind=infer_file_kind(ext),
                status=DocumentStatus.ACTIVE,
                visibility=DocumentVisibility.ORGANIZATION,
                confidentiality_level=ConfidentialityLevel.INTERNAL,
                version_number=1,
                uploaded_by_user_id=actor.id if actor else None,
                owner_user_id=actor.id if actor else None,
                description=f"Bitrix deal {deal_id} UF file {file_id}",
                notes=notes,
                tags=f"bitrix_file:{file_id}"[:1000],
                is_latest_version=True,
                processing_status=ProcessingStatus.UPLOADED,
            )
            db.add(document)
            db.flush()
            _link_agreement_doc(db, document.id, DEAL_TO_AGREEMENT[deal_id])
            imported[deal_id].append(str(document.id))
    db.flush()
    return {"imported": imported, "failed": failed, "present_checked": True}


def apply_nedim_purchase_card_pilot(db: Session) -> dict[str, Any]:
    izzet = ensure_izzet(db)
    ensure_deal_metadata(db)
    participants = ensure_participants(db, izzet.id)
    cleanup = cleanup_false_agreement_links(db)
    linked = link_existing_deal_documents(db)
    uf = _import_uf_files(db)
    cleanup_after = cleanup_false_agreement_links(db)
    linked = link_existing_deal_documents(db)
    db.commit()
    return {
        "izzet_contact_id": str(izzet.id),
        "izzet_source": izzet.source,
        "participants": participants,
        "documents_linked": linked,
        "cleanup": cleanup,
        "cleanup_after": cleanup_after,
        "uf_import": uf,
        "uf_expected": DEAL_UF_FILES,
        "webhook_used": bool(os.environ.get("BITRIX_ADMIN_WEBHOOK_URL")),
    }


def main() -> None:
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        print(json.dumps(apply_nedim_purchase_card_pilot(db), ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
