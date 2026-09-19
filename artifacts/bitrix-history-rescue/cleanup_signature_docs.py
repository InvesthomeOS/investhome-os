"""Classify and hide high-confidence email signature/logo junk in CRM Documents.

Does not delete Bitrix archive binaries. Does not invent contact history.
Default is dry-run. Pass --apply to archive high-confidence junk only.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
from collections import defaultdict
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.document import Document, DocumentLink, DocumentStatus
from investhome_api.services.storage.factory import get_storage_provider

OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports")
PROTECTED_RE = re.compile(
    r"passport|pasaport|kimlik|identit|id[\s_-]?card|closing|teklif|dekont|s[oö]zle[sş]me|"
    r"contract|tapu|swift|fatura|invoice|vekalet|notary|title.?deed|llc|imza\s*sirk|nüfus",
    re.I,
)
JUNK_NAME_RE = re.compile(
    r"logo|signature|imza|icon|favicon|facebook|twitter|instagram|linkedin|youtube|"
    r"spacer|pixel|tracking|banner|footer|header[-_ ]?logo|company[-_ ]?logo|"
    r"email[-_ ]?sig|social|whatsapp[-_ ]?icon|image00\d|untitled",
    re.I,
)
OUTLOOK_INLINE_RE = re.compile(r"^image00\d(?:\s*\(\d+\))?\.(gif|png|jpe?g|bmp)$", re.I)


def parse_notes(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def image_size(data: bytes) -> tuple[int | None, int | None]:
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                break
            marker = data[i + 1]
            if marker in {0xC0, 0xC1, 0xC2}:
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            length = struct.unpack(">H", data[i + 2 : i + 4])[0]
            i += 2 + length
        return None, None
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:6] in {b"GIF87a", b"GIF89a"} and len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w, h
    return None, None


def classify(row: dict, sha_contacts: dict[str, set[str]]) -> tuple[str, str]:
    source = (row.get("source_type") or "").lower()
    name = row.get("original_file_name") or row.get("title") or ""
    mime = (row.get("mime_type") or "").lower()
    ext = (row.get("file_extension") or "").lower()
    is_image = mime.startswith("image/") or ext in {"jpg", "jpeg", "png", "gif", "bmp", "webp", "tif", "tiff"}
    protected = bool(PROTECTED_RE.search(name) or PROTECTED_RE.search(row.get("title") or ""))
    if source == "entity_field" or protected:
        return "keep", "protected_customer_document"
    if not is_image:
        return "keep", "not_image"
    sha = row.get("checksum") or ""
    contacts = sha_contacts.get(sha) or set()
    repeated = len(contacts) >= 2
    inline = bool(row.get("inline_or_cid"))
    junk_name = bool(JUNK_NAME_RE.search(name) or OUTLOOK_INLINE_RE.match(Path(name).name))
    w, h = row.get("width"), row.get("height")
    tiny_icon = w is not None and h is not None and w <= 96 and h <= 96
    outlook_inline = bool(OUTLOOK_INLINE_RE.match(Path(name).name))
    tracking_pixel = name.lower().startswith("outlook-") and int(row.get("file_size") or 0) <= 2048
    logo_name = bool(re.search(r"logo", name, re.I))
    size = int(row.get("file_size") or 0)
    email = source == "email"
    reasons = []
    if email:
        reasons.append("source=email")
    if junk_name:
        reasons.append("signature_or_logo_filename")
    if inline:
        reasons.append("inline_or_cid")
    if repeated and email:
        reasons.append(f"repeated_sha_across_{len(contacts)}_contacts")
    if tiny_icon and email:
        reasons.append(f"tiny_graphic_{w}x{h}")
    if tracking_pixel:
        reasons.append("outlook_tracking_or_spacer")
    if not email:
        pass
    elif tracking_pixel:
        return "junk", "; ".join(reasons)
    elif logo_name and (repeated or size <= 120_000):
        return "junk", "; ".join(reasons)
    elif outlook_inline and repeated:
        return "junk", "; ".join(reasons)
    elif outlook_inline and ext in {"png", "gif"} and size <= 80_000:
        return "junk", "; ".join(reasons)
    elif repeated and is_image and (outlook_inline or logo_name or name.lower().startswith("image1")):
        return "junk", "; ".join(reasons)
    elif outlook_inline and not repeated and (ext in {"jpg", "jpeg"} or size > 80_000):
        return "ambiguous", "; ".join(reasons + ["unique_outlook_named_image_may_be_photo"])
    elif email and (junk_name or inline or repeated or tiny_icon):
        return "ambiguous", "; ".join(reasons) or "email_image_without_strong_junk_signal"
    if is_image and repeated and source in {"email", "comment", "whatsapp"}:
        if tiny_icon or junk_name:
            return "junk", "; ".join(reasons + ["repeated_decorative"])
        return "ambiguous", f"repeated_image_source={source or 'unknown'}"
    if email and is_image:
        return "ambiguous", "email_image_without_strong_junk_signal"
    return "keep", "not_email_signature"


def load_rows(db: Session) -> list[dict]:
    storage = get_storage_provider()
    sql = text(
        """
        select d.id::text as document_id,
               d.title,
               d.original_file_name,
               d.file_extension,
               d.mime_type,
               d.file_size,
               d.checksum,
               d.tags,
               d.notes,
               d.status,
               d.archived_at,
               d.storage_key,
               l.entity_id::text as contact_id,
               c.display_name
        from documents d
        join document_links l on l.document_id = d.id
        left join crm_contacts c on c.id = l.entity_id
        where d.tags like 'bitrix:%'
          and l.entity_type in ('crm_contact', 'contact')
        """
    )
    grouped: dict[str, dict] = {}
    for rec in db.execute(sql).mappings():
        doc_id = rec["document_id"]
        row = grouped.get(doc_id)
        if row is None:
            notes = parse_notes(rec["notes"])
            disp = str(notes.get("content_disposition") or notes.get("contentDisposition") or "")
            cid = str(notes.get("content_id") or notes.get("contentId") or notes.get("cid") or "")
            row = {
                "document_id": doc_id,
                "title": rec["title"],
                "original_file_name": rec["original_file_name"],
                "file_extension": rec["file_extension"],
                "mime_type": rec["mime_type"],
                "file_size": rec["file_size"],
                "checksum": rec["checksum"],
                "tags": rec["tags"],
                "status": str(rec["status"]),
                "archived": rec["archived_at"] is not None,
                "storage_key": rec["storage_key"],
                "source_type": notes.get("source_type") or "",
                "bitrix_file_id": str(notes.get("bitrix_file_id") or ""),
                "archive_path": notes.get("archive_path") or "",
                "inline_or_cid": "inline" in disp.lower() or bool(cid),
                "width": None,
                "height": None,
                "contacts": [],
            }
            grouped[doc_id] = row
        if rec["contact_id"]:
            row["contacts"].append(
                {"contact_id": rec["contact_id"], "display_name": rec["display_name"]}
            )
    for row in grouped.values():
        mime = (row.get("mime_type") or "").lower()
        if not mime.startswith("image/"):
            continue
        try:
            stream = storage.open(row["storage_key"])
            data = stream.read(256 * 1024)
            stream.close()
        except FileNotFoundError:
            continue
        w, h = image_size(data)
        row["width"] = w
        row["height"] = h
    return list(grouped.values())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        rows = load_rows(db)
        sha_contacts: dict[str, set[str]] = defaultdict(set)
        for row in rows:
            sha = row.get("checksum") or ""
            for contact in row["contacts"]:
                if sha and contact.get("contact_id"):
                    sha_contacts[sha].add(contact["contact_id"])
        classified = {"junk": [], "ambiguous": [], "keep": []}
        for row in rows:
            bucket, reason = classify(row, sha_contacts)
            item = {
                **{k: v for k, v in row.items() if k != "storage_key"},
                "decision": bucket,
                "reason": reason,
                "contact_names": sorted({c["display_name"] for c in row["contacts"] if c.get("display_name")}),
                "contact_ids": sorted({c["contact_id"] for c in row["contacts"] if c.get("contact_id")}),
                "sha_contact_count": len(sha_contacts.get(row.get("checksum") or "", set())),
            }
            classified[bucket].append(item)

        before = db.execute(
            text(
                """
                select count(distinct d.id)
                from documents d
                join document_links l on l.document_id = d.id
                where d.tags like 'bitrix:%'
                  and l.entity_type in ('crm_contact', 'contact')
                  and d.archived_at is null
                """
            )
        ).scalar()
        repeated = [
            {
                "checksum": sha,
                "contacts": len(cids),
                "filenames": sorted(
                    {
                        r["original_file_name"]
                        for r in rows
                        if r.get("checksum") == sha
                    }
                ),
            }
            for sha, cids in sha_contacts.items()
            if len(cids) >= 2
        ]
        dry = {
            "mode": "apply" if args.apply else "dry-run",
            "total_crm_bitrix_documents_active": int(before or 0),
            "inspected": len(rows),
            "likely_signature_logo_junk": len(classified["junk"]),
            "repeated_identical_files": repeated,
            "contacts_affected": sorted(
                {name for item in classified["junk"] for name in item["contact_names"]}
            ),
            "files_safe_to_hide": [
                {
                    "document_id": i["document_id"],
                    "filename": i["original_file_name"],
                    "person": i["contact_names"],
                    "reason": i["reason"],
                    "size": i["file_size"],
                    "dims": f"{i['width']}x{i['height']}" if i["width"] else "",
                    "checksum": (i.get("checksum") or "")[:16],
                }
                for i in classified["junk"]
            ],
            "ambiguous_left_untouched": [
                {
                    "document_id": i["document_id"],
                    "filename": i["original_file_name"],
                    "person": i["contact_names"],
                    "reason": i["reason"],
                    "source_type": i["source_type"],
                    "size": i["file_size"],
                }
                for i in classified["ambiguous"]
            ],
            "keep": len(classified["keep"]),
        }
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "CRM_DOCUMENT_CLEANUP_DRY_RUN.json").write_text(
            json.dumps(dry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(dry, ensure_ascii=False, indent=2))
        if not args.apply:
            print("DRY_RUN_NO_CHANGES")
            return

        hidden = []
        for item in classified["junk"]:
            doc = db.get(Document, UUID(item["document_id"]))
            if doc is None or doc.archived_at is not None:
                continue
            notes = parse_notes(doc.notes)
            notes["cleanup"] = {
                "action": "hidden_from_crm",
                "reason": item["reason"],
                "at": datetime.now(UTC).isoformat(),
                "binary_preserved": True,
                "bitrix_archive_untouched": True,
            }
            doc.notes = json.dumps(notes, ensure_ascii=False)
            doc.archived_at = datetime.now(UTC)
            doc.status = DocumentStatus.ARCHIVED
            hidden.append(item["document_id"])
        db.commit()
        after = db.execute(
            text(
                """
                select count(distinct d.id)
                from documents d
                join document_links l on l.document_id = d.id
                where d.tags like 'bitrix:%'
                  and l.entity_type in ('crm_contact', 'contact')
                  and d.archived_at is null
                """
            )
        ).scalar()
        applied = {
            "hidden_count": len(hidden),
            "hidden_ids": hidden,
            "final_crm_bitrix_document_count": int(after or 0),
            "ambiguous_untouched": len(classified["ambiguous"]),
        }
        (OUT / "CRM_DOCUMENT_CLEANUP_APPLIED.json").write_text(
            json.dumps(applied, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("APPLIED", json.dumps(applied, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
