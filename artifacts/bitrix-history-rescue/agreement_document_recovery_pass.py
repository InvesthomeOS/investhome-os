"""Recover missing live Bitrix deal UF files for 31 closeout purchases. Bitrix read-only."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.documents_config import ALLOWED_EXTENSIONS, infer_file_kind
from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import (
    ConfidentialityLevel,
    Document,
    DocumentLink,
    DocumentStatus,
    DocumentType,
    DocumentVisibility,
    DocumentWorkspaceFolder,
    ProcessingStatus,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.agreement_service import _document_notes, get_purchase_card
from investhome_api.services.crm.nedim_purchase_card import deal_id_for_agreement
from investhome_api.services.document_service import create_document_analysis
from investhome_api.services.document_validation import compute_checksum, generate_storage_key
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

from lale_b08_document_recovery import (
    BitrixClient,
    TYPE_MAP,
    collect_file_nodes,
    ext_of,
    existing_for_file,
    link_agreement,
    link_contact,
    mime_of,
    notes_of,
    redact,
    safe_filename,
    try_disk,
    user_label,
    webhook_base,
)

OUT = Path("/tmp/AGREEMENT_DOCUMENT_RECOVERY")
COPY_SUFFIX = re.compile(r"\s*\(\d+\)(?=\.[^.]+$)", re.I)
CLOSEOUT = Path("/tmp/AGREEMENTS_PHASE_CLOSEOUT/reports/CLOSEOUT.json")


def load_targets() -> list[dict[str, Any]]:
    raw = json.loads(CLOSEOUT.read_text(encoding="utf-8"))
    targets: list[dict[str, Any]] = []
    for row in raw.get("document_gaps") or []:
        if row.get("problem") != "deal_uf_files_missing_from_os":
            continue
        fids = [str(item) for item in (row.get("file_ids") or []) if str(item).isdigit() and len(str(item)) >= 5]
        if not fids:
            continue
        targets.append({"name": row.get("name"), "deal_id": str(row.get("deal_id")), "file_ids": fids})
    return targets


def recover_one(
    client: BitrixClient,
    file_id: str,
    field: str,
    node: dict[str, Any],
    assigned_id: str | None,
    deal_id: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "bitrix_file_id": file_id,
        "deal_id": deal_id,
        "source_field": field,
        "original_filename": node.get("name"),
        "type": node.get("mime") or node.get("type"),
        "size": node.get("size"),
        "download_url_status": None,
        "access_status": "pending",
        "required_bitrix_user": None,
        "reason": None,
        "sha256": None,
        "local_archive_path": None,
        "crm_document_id": None,
        "reused_existing": False,
        "newly_created": False,
        "newly_linked": False,
        "recovered": False,
    }
    reasons: list[str] = []
    content = None
    mime = None
    fname = node.get("name")
    live_node = node.get("node") if isinstance(node.get("node"), dict) else {}
    for url_key in ("urlMachine", "urlDownload", "DOWNLOAD_URL", "downloadUrl", "url"):
        url = str(live_node.get(url_key) or "")
        if not url:
            continue
        data, detected, downloaded_name, err = client.download(url)
        row["download_url_status"] = "ok" if data else redact(err or f"{url_key}_failed", client.base)
        if data:
            content, mime, fname = data, detected, downloaded_name or fname
            row["access_status"] = f"downloaded_via_crm.item.{url_key}"
            break
        reasons.append(f"{url_key}:{err}")
    disk = try_disk(client, file_id)
    row["original_filename"] = fname or disk.get("name") or row["original_filename"]
    row["type"] = mime or disk.get("type") or row["type"]
    row["size"] = disk.get("size") or row["size"]
    if not content and disk.get("content"):
        content = disk["content"]
        mime = disk.get("mime") or mime
        fname = disk.get("name") or fname
        row["access_status"] = f"downloaded_via_{disk.get('download_via')}"
        row["download_url_status"] = "ok"
    else:
        for method, payload in (disk.get("methods") or {}).items():
            if payload.get("error"):
                reasons.append(f"{method}:{payload.get('error')}:{payload.get('error_description') or ''}".strip(":"))
            elif payload.get("download_error"):
                reasons.append(f"{method}:{payload.get('download_error')}")
    if not content:
        for url in (
            f"{client.origin}/bitrix/tools/crm_show_file.php?fileId={file_id}&ownerTypeId=2&ownerId={deal_id}",
            f"{client.origin}/bitrix/components/bitrix/crm.field.file/show_file.php?ownerId={deal_id}&ownerType=DEAL&fileId={file_id}",
            f"{client.origin}/bitrix/tools/disk/uf.php?attachedId={file_id}",
        ):
            data, detected, downloaded_name, err = client.download(url)
            if data:
                content, mime, fname = data, detected, downloaded_name or fname
                row["access_status"] = "downloaded_via_crm_show_file"
                row["download_url_status"] = "ok"
                break
            reasons.append(f"show_file:{err}")
    if content:
        row["original_filename"] = fname or row["original_filename"] or f"bitrix-file-{file_id}"
        row["type"] = mime_of(row["original_filename"], mime, content)
        row["size"] = len(content)
        row["content"] = content
        row["recovered"] = True
        return row
    row["access_status"] = "inaccessible"
    row["required_bitrix_user"] = user_label(client, disk.get("created_by")) or user_label(client, assigned_id)
    row["reason"] = "; ".join(dict.fromkeys(r for r in reasons if r))[:500] or "authorized_webhook_cannot_read_file"
    if not row["download_url_status"]:
        row["download_url_status"] = "no_usable_url"
    return row


def existing_for_checksum_deal(db: Session, checksum: str, deal_id: str) -> Document | None:
    rows = list(db.scalars(select(Document).where(Document.checksum == checksum)).all())
    for document in rows:
        notes = notes_of(document)
        if str(notes.get("bitrix_entity_type") or "").lower() == "deal" and str(notes.get("bitrix_entity_id") or "") == deal_id:
            return document
    return None


def import_or_reuse(
    db: Session,
    actor: User,
    deal_id: str,
    file_id: str,
    filename: str,
    mime: str,
    content: bytes,
    field: str,
    archive_path: str,
    checksum: str,
) -> tuple[Document, bool, bool]:
    existing = existing_for_file(db, file_id) or existing_for_checksum_deal(db, checksum, deal_id)
    reused_storage = False
    if existing is not None:
        notes = notes_of(existing)
        notes.update(
            {
                "source": "bitrix_live",
                "bitrix_file_id": file_id,
                "bitrix_entity_type": "deal",
                "bitrix_entity_id": deal_id,
                "source_type": "deal_uf",
                "source_record_id": field,
                "archive_path": archive_path,
                "sha256": checksum,
                "import_key": f"bitrix_deal:{deal_id}:file:{file_id}",
            }
        )
        existing.notes = json.dumps(notes, ensure_ascii=False)
        return existing, True, False

    ext = ext_of(filename, mime)
    if not ext:
        if content.startswith(b"%PDF"):
            ext, mime = "pdf", "application/pdf"
            filename = filename if filename.lower().endswith(".pdf") else f"{filename}.pdf"
        elif content[:3] == b"\xff\xd8\xff":
            ext, mime = "jpg", "image/jpeg"
            filename = filename if filename.lower().endswith((".jpg", ".jpeg")) else f"{filename}.jpg"
        elif content.startswith(b"\x89PNG"):
            ext, mime = "png", "image/png"
            filename = filename if filename.lower().endswith(".png") else f"{filename}.png"
        else:
            raise ValueError(f"unsupported_type:{mime}:{filename}")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"unsupported_extension:{ext}")

    twin = db.scalar(select(Document).where(Document.checksum == checksum).limit(1))
    storage = get_storage_provider()
    if twin is not None:
        stored_name, storage_key = twin.stored_file_name, twin.storage_key
        reused_storage = True
    else:
        stored_name, storage_key = generate_storage_key(ext)
        storage.save(storage_key, BytesIO(content), content_length=len(content))
    notes = json.dumps(
        {
            "source": "bitrix_live",
            "bitrix_file_id": file_id,
            "bitrix_entity_type": "deal",
            "bitrix_entity_id": deal_id,
            "source_type": "deal_uf",
            "source_record_id": field,
            "archive_path": archive_path,
            "sha256": checksum,
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
        document_type=TYPE_MAP.get(ext, DocumentType.OTHER),
        category="bitrix",
        folder=DocumentWorkspaceFolder.CONTRACTS,
        file_kind=infer_file_kind(ext),
        status=DocumentStatus.ACTIVE,
        visibility=DocumentVisibility.ORGANIZATION,
        confidentiality_level=ConfidentialityLevel.INTERNAL,
        version_number=1,
        uploaded_by_user_id=actor.id,
        owner_user_id=actor.id,
        description=f"Bitrix deal {deal_id} UF file {file_id}",
        notes=notes,
        tags=f"bitrix_file:{file_id}"[:1000],
        is_latest_version=True,
        processing_status=ProcessingStatus.UPLOADED,
    )
    db.add(document)
    db.flush()
    create_document_analysis(db, document.id)
    return document, False, not reused_storage


def prefer_visible(document: Document, live_ids: set[str]) -> tuple[int, int, int, str]:
    notes = notes_of(document)
    name = document.original_file_name or document.title or ""
    uf = 0 if str(notes.get("source_type") or "") == "deal_uf" else 1
    live = 0 if str(notes.get("bitrix_file_id") or "") in live_ids else 1
    copy = 1 if COPY_SUFFIX.search(name) else 0
    return (uf, live, copy, name.casefold())


def dedupe_agreement(db: Session, agreement_id: UUID, live_ids: set[str]) -> int:
    links = list(
        db.scalars(
            select(DocumentLink).where(
                DocumentLink.entity_type == "crm_agreement",
                DocumentLink.entity_id == agreement_id,
            )
        ).all()
    )
    by_checksum: dict[str, list[tuple[DocumentLink, Document]]] = defaultdict(list)
    for link in links:
        document = db.get(Document, link.document_id)
        if document is None or not document.checksum:
            continue
        by_checksum[document.checksum].append((link, document))
    removed = 0
    for rows in by_checksum.values():
        if len(rows) < 2:
            continue
        winner = sorted(rows, key=lambda item: prefer_visible(item[1], live_ids))[0]
        for link, document in rows:
            if link.id == winner[0].id:
                continue
            db.delete(link)
            removed += 1
    return removed


def visible_file_ids(card) -> set[str]:
    return {str(doc.bitrix_file_id) for doc in (card.documents if card else []) if doc.bitrix_file_id}


def visible_checksums(db: Session, card) -> set[str]:
    found: set[str] = set()
    for doc in card.documents if card else []:
        document = db.get(Document, doc.id)
        if document and document.checksum:
            found.add(document.checksum)
    return found


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    (OUT / "binaries").mkdir(parents=True, exist_ok=True)
    targets = load_targets()
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    if not raw:
        raise SystemExit("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
    client = BitrixClient(webhook_base(raw))
    admin = client.call("user.admin", {})
    current = client.call("user.current", {})
    user = current.get("result") if isinstance(current.get("result"), dict) else {}
    webhook_user = " ".join(str(part) for part in (user.get("NAME"), user.get("LAST_NAME")) if part).strip()
    db = SessionLocal()
    report: dict[str, Any] = {
        "bitrix_modified": False,
        "webhook_user": webhook_user,
        "webhook_admin": admin.get("result"),
        "purchases_processed": 0,
        "files": [],
        "still_missing": [],
        "purchases_still_incomplete": [],
    }
    try:
        actor = db.scalar(select(User).order_by(User.created_at.asc()))
        if actor is None:
            raise RuntimeError("no actor user")
        agreements = list(db.scalars(select(CrmAgreement)).all())
        deal_to_agreement: dict[str, CrmAgreement] = {}
        for row in agreements:
            did = deal_id_for_agreement(row.id, row.metadata_json if isinstance(row.metadata_json, dict) else {})
            if did:
                deal_to_agreement[did] = row
        deal_fields = client.call("crm.deal.fields", {}).get("result") or {}
        file_fields = {
            key
            for key, spec in (deal_fields.items() if isinstance(deal_fields, dict) else [])
            if isinstance(spec, dict) and str(spec.get("type") or "").lower() == "file"
        }
        downloaded = reused = created = linked = 0
        checksum_by_file: dict[tuple[str, str], str] = {}
        for index, target in enumerate(targets, start=1):
            deal_id = target["deal_id"]
            wanted = set(target["file_ids"])
            agreement = deal_to_agreement.get(deal_id)
            print(f"DEAL {index}/{len(targets)} {deal_id} {target.get('name')} files={len(wanted)}", flush=True)
            if agreement is None:
                for fid in wanted:
                    report["still_missing"].append(
                        {"deal_id": deal_id, "bitrix_file_id": fid, "reason": "os_agreement_not_found_for_deal"}
                    )
                continue
            person = db.get(CrmContact, agreement.contact_id)
            deal = client.call("crm.deal.get", {"id": deal_id}).get("result") or {}
            item_body = client.call("crm.item.get", {"entityTypeId": 2, "id": deal_id})
            item = (item_body.get("result") or {}).get("item") if isinstance(item_body.get("result"), dict) else {}
            assigned_id = str(deal.get("ASSIGNED_BY_ID") or item.get("assignedById") or "")
            collected: dict[str, dict[str, Any]] = {}
            for key, value in (deal.items() if isinstance(deal, dict) else []):
                if key in file_fields or str(key).startswith("UF_"):
                    collect_file_nodes(value, key, collected)
            for key, value in (item.items() if isinstance(item, dict) else []):
                collect_file_nodes(value, key, collected)
            live_ids = set(wanted)
            for fid in collected:
                if fid in wanted:
                    live_ids.add(fid)
            for file_id in sorted(wanted):
                node = collected.get(file_id) or {"id": file_id, "fields": []}
                field = (node.get("fields") or [""])[0]
                rec = recover_one(client, file_id, field, node, assigned_id, deal_id)
                rec["person"] = person.display_name if person else target.get("name")
                rec["agreement_id"] = str(agreement.id)
                rec["source_field_label"] = field
                content = rec.pop("content", None)
                if not content:
                    rec["recovered"] = False
                    report["files"].append(rec)
                    report["still_missing"].append(
                        {
                            "deal_id": deal_id,
                            "bitrix_file_id": file_id,
                            "person": rec["person"],
                            "reason": rec.get("reason"),
                            "access_status": rec.get("access_status"),
                            "required_bitrix_user": rec.get("required_bitrix_user"),
                        }
                    )
                    continue
                filename = safe_filename(rec.get("original_filename"), file_id)
                checksum = hashlib.sha256(content).hexdigest()
                dest = OUT / "binaries" / f"{deal_id}_{file_id}__{filename}"
                dest.write_bytes(content)
                document, was_existing, wrote_binary = import_or_reuse(
                    db,
                    actor,
                    deal_id,
                    file_id,
                    filename,
                    rec.get("type") or "application/octet-stream",
                    content,
                    field,
                    str(dest),
                    checksum,
                )
                newly_linked = link_agreement(db, document.id, agreement.id)
                if person is not None:
                    link_contact(db, document.id, person.id)
                rec["sha256"] = checksum
                rec["local_archive_path"] = str(dest)
                rec["crm_document_id"] = str(document.id)
                rec["reused_existing"] = was_existing
                rec["newly_created"] = not was_existing
                rec["newly_linked"] = newly_linked
                rec["original_filename"] = document.original_file_name
                rec["type"] = document.mime_type
                rec["size"] = document.file_size
                rec["recovered"] = True
                report["files"].append(rec)
                downloaded += 1
                checksum_by_file[(deal_id, file_id)] = checksum
                if was_existing:
                    reused += 1
                elif wrote_binary:
                    created += 1
                else:
                    reused += 1
                if newly_linked:
                    linked += 1
            db.commit()
            report["purchases_processed"] += 1

        cleaned = 0
        for row in agreements:
            did = deal_id_for_agreement(row.id, row.metadata_json if isinstance(row.metadata_json, dict) else {})
            live_ids = set()
            target = next((item for item in targets if item["deal_id"] == did), None)
            if target:
                live_ids = set(target["file_ids"])
            cleaned += dedupe_agreement(db, row.id, live_ids)
        db.commit()

        incomplete = []
        lale_87264 = None
        for target in targets:
            agreement = deal_to_agreement.get(target["deal_id"])
            if agreement is None:
                incomplete.append({"deal_id": target["deal_id"], "name": target["name"], "missing": target["file_ids"]})
                continue
            card = get_purchase_card(db, agreement.id, viewer_contact_id=agreement.contact_id)
            ids = visible_file_ids(card)
            sums = visible_checksums(db, card)
            missing = []
            for fid in target["file_ids"]:
                digest = checksum_by_file.get((target["deal_id"], fid))
                if fid in ids or (digest and digest in sums):
                    continue
                missing.append(fid)
            if target["deal_id"] == "206" and "87264" in target["file_ids"]:
                hit = next((item for item in report["files"] if item.get("bitrix_file_id") == "87264"), None)
                lale_87264 = {
                    "recovered": bool(hit and hit.get("recovered") and "87264" not in missing),
                    "file": hit,
                    "visible": "87264" not in missing,
                }
            if missing:
                incomplete.append(
                    {
                        "deal_id": target["deal_id"],
                        "name": target["name"],
                        "agreement_id": str(agreement.id),
                        "missing": missing,
                        "visible_count": card.document_count if card else 0,
                    }
                )
        denom = max(1, len(targets))
        report.update(
            {
                "missing_file_ids_attempted": sum(len(item["file_ids"]) for item in targets),
                "downloaded": downloaded,
                "reused_existing_files": reused,
                "newly_created_documents": created,
                "newly_linked_documents": linked,
                "duplicate_visible_files_cleaned": cleaned,
                "still_missing_count": len(report["still_missing"]),
                "purchases_still_incomplete": incomplete,
                "lale_reit_87264": lale_87264,
                "final_document_completeness_percentage": round(100 * (1 - len(incomplete) / denom), 1),
                "bitrix_calls": client.call_count,
                "backup_path": "data/Bitrix_Export/2026-09-final/AGREEMENT_DOCUMENT_RECOVERY/backups/investhome-pre-agreement-doc-recovery-20260919.dump",
                "report_path": "data/Bitrix_Export/2026-09-final/AGREEMENT_DOCUMENT_RECOVERY/INDEX.md",
            }
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    (OUT / "reports" / "RECOVERY.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "purchases": report.get("purchases_processed"),
                "attempted": report.get("missing_file_ids_attempted"),
                "downloaded": report.get("downloaded"),
                "reused": report.get("reused_existing_files"),
                "created": report.get("newly_created_documents"),
                "linked": report.get("newly_linked_documents"),
                "deduped": report.get("duplicate_visible_files_cleaned"),
                "still_missing": report.get("still_missing_count"),
                "incomplete": len(report.get("purchases_still_incomplete") or []),
                "lale_87264": report.get("lale_reit_87264"),
                "completeness": report.get("final_document_completeness_percentage"),
                "calls": report.get("bitrix_calls"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
