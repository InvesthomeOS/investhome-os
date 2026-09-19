"""Build a visual review gallery for the 18 ambiguous CRM images. Read-only."""
from __future__ import annotations

import base64
import csv
import html
import io
import json
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from investhome_api.db.session import SessionLocal
from investhome_api.models.document import Document
from investhome_api.services.storage.factory import get_storage_provider

REPORTS = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports")
DRY = REPORTS / "CRM_DOCUMENT_CLEANUP_DRY_RUN.json"
MANIFEST = REPORTS / "BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
OUT_HTML = REPORTS / "AMBIGUOUS_IMAGE_REVIEW.html"
OUT_CSV = REPORTS / "AMBIGUOUS_IMAGE_REVIEW.csv"
MAX_EDGE = 900


def parse_notes(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def thumbnail(data: bytes, mime: str) -> tuple[str, bool]:
    try:
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        image = image.convert("RGB") if image.mode not in {"RGB", "L"} else image
        image.thumbnail((MAX_EDGE, MAX_EDGE))
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=82)
        b64 = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}", True
    except Exception:
        kind = "image/jpeg" if "jpeg" in (mime or "") or "jpg" in (mime or "") else (mime or "image/png")
        if not data:
            return "", False
        b64 = base64.b64encode(data).decode("ascii")
        return f"data:{kind};base64,{b64}", bool(data)


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    with MANIFEST.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def context_from_archive(entity_type: str, entity_id: str, source_id: str, file_id: str) -> tuple[str, str]:
    if not entity_id:
        return "", ""
    path = ARCHIVE / "raw" / ("contacts" if entity_type == "contact" else "leads") / f"{entity_id}.json"
    if not path.exists():
        alt = ARCHIVE / "raw" / "contacts" / f"{entity_id}.json"
        path = alt if alt.exists() else path
    if not path.exists():
        return "", ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "", ""
    for activity in data.get("crm_activities") or []:
        if str(activity.get("ID") or "") != str(source_id):
            continue
        when = str(activity.get("CREATED") or activity.get("START_TIME") or "")
        subject = str(activity.get("SUBJECT") or "")
        body = str(activity.get("DESCRIPTION") or "")[:400]
        return when, " — ".join(x for x in (subject, body) if x)
    return "", ""


def main() -> None:
    dry = json.loads(DRY.read_text(encoding="utf-8"))
    wanted = [item["document_id"] for item in dry.get("ambiguous_left_untouched") or []]
    if len(wanted) != 18:
        print(f"UNEXPECTED_AMBIGUOUS_COUNT {len(wanted)}")
    manifest = load_manifest()
    storage = get_storage_provider()
    db = SessionLocal()
    rows = []
    try:
        for doc_id in wanted:
            doc = db.get(Document, UUID(doc_id))
            if doc is None:
                rows.append(
                    {
                        "document_id": doc_id,
                        "person_name": "",
                        "canonical_crm_contact_id": "",
                        "original_filename": "",
                        "file_size": "",
                        "source_type": "",
                        "source_date": "",
                        "context": "",
                        "rendered": False,
                        "thumb": "",
                    }
                )
                continue
            notes = parse_notes(doc.notes)
            contact_id = str(notes.get("canonical_contact_id") or "")
            person = ""
            if contact_id:
                person = db.execute(
                    text("select display_name from crm_contacts where id = :id"),
                    {"id": contact_id},
                ).scalar() or ""
            if not person:
                link = db.execute(
                    text(
                        """
                        select c.display_name, l.entity_id::text
                        from document_links l
                        join crm_contacts c on c.id = l.entity_id
                        where l.document_id = :id
                          and l.entity_type in ('crm_contact', 'contact')
                        limit 1
                        """
                    ),
                    {"id": doc_id},
                ).mappings().first()
                if link:
                    person = link["display_name"]
                    contact_id = contact_id or link["entity_id"]
            file_id = str(notes.get("bitrix_file_id") or "")
            source_id = str(notes.get("source_record_id") or "")
            source_type = str(notes.get("source_type") or "")
            entity_type = str(notes.get("bitrix_entity_type") or "")
            entity_id = str(notes.get("bitrix_entity_id") or "")
            source_date = str(doc.document_date or "")
            context = ""
            for item in manifest:
                if contact_id and item.get("canonical_crm_contact_id") == contact_id and str(item.get("bitrix_file_id") or "") == file_id:
                    source_date = source_date or item.get("datetime") or ""
                    context = context or (item.get("surrounding_text") or item.get("original_filename") or "")
                    source_type = source_type or item.get("source_type") or ""
                    break
            when, archive_ctx = context_from_archive(entity_type, entity_id, source_id, file_id)
            source_date = source_date or when
            context = context or archive_ctx
            data = b""
            archive_path = notes.get("archive_path") or ""
            local = REPORTS.parent / archive_path if archive_path else None
            if local and local.exists():
                data = local.read_bytes()
            if not data:
                try:
                    stream = storage.open(doc.storage_key)
                    data = stream.read()
                    stream.close()
                except FileNotFoundError:
                    data = b""
            thumb, rendered = thumbnail(data, doc.mime_type or "")
            rows.append(
                {
                    "document_id": doc_id,
                    "person_name": person,
                    "canonical_crm_contact_id": contact_id,
                    "original_filename": doc.original_file_name or "",
                    "file_size": str(doc.file_size or len(data) or ""),
                    "mime_type": doc.mime_type or "",
                    "source_type": source_type,
                    "source_record_id": source_id,
                    "bitrix_file_id": file_id,
                    "source_date": source_date or "",
                    "context": context,
                    "rendered": rendered,
                    "thumb": thumb,
                }
            )
    finally:
        db.close()

    fields = [
        "person_name",
        "canonical_crm_contact_id",
        "document_id",
        "original_filename",
        "file_size",
        "source_type",
        "source_date",
        "source_record_id",
        "bitrix_file_id",
        "context",
        "rendered",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["person_name"] or "Unknown"].append(row)
    rendered_ok = sum(1 for r in rows if r["rendered"])
    parts = [
        "<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'>",
        "<title>Ambiguous CRM image review (18)</title>",
        "<style>",
        "body{font:15px/1.4 system-ui,Segoe UI,sans-serif;margin:0;background:#f3efe6;color:#1b1b1b}",
        "header{background:#1e2a3a;color:#fff;padding:24px 28px}",
        "main{padding:20px 28px 64px;max-width:1280px}",
        "section{margin:28px 0}",
        "h2{margin:0 0 12px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(380px,1fr));gap:18px}",
        "figure{margin:0;background:#fff;border:1px solid #d8d1c4;border-radius:14px;overflow:hidden}",
        "figure img{width:100%;height:420px;object-fit:contain;background:#111;display:block}",
        "figcaption{padding:12px 14px}",
        ".meta{font-size:13px;color:#444}",
        ".mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all}",
        ".missing{height:420px;display:flex;align-items:center;justify-content:center;background:#eee;color:#666}",
        "</style></head><body>",
        "<header><h1>Ambiguous CRM images — visual review</h1>",
        f"<p>{len(rows)} files left untouched. No classification. No CRM changes.</p></header><main>",
    ]
    for person in sorted(grouped):
        items = grouped[person]
        parts.append(f"<section><h2>{html.escape(person)} <small>({len(items)})</small></h2><div class='grid'>")
        for row in items:
            parts.append("<figure>")
            if row["thumb"]:
                parts.append(
                    f"<img src='{row['thumb']}' alt='{html.escape(row['original_filename'])}'>"
                )
            else:
                parts.append("<div class='missing'>Image did not render</div>")
            parts.append("<figcaption>")
            parts.append(f"<strong>{html.escape(row['original_filename'] or 'unnamed')}</strong>")
            parts.append(
                f"<div class='meta'>{html.escape(row['source_type'] or '—')} · "
                f"{html.escape(row['source_date'] or 'date unknown')} · "
                f"{html.escape(row['file_size'] or '?')} bytes</div>"
            )
            if row["context"]:
                parts.append(f"<p>{html.escape(row['context'][:400])}</p>")
            parts.append(f"<div class='mono'>contact {html.escape(row['canonical_crm_contact_id'])}</div>")
            parts.append(f"<div class='mono'>document {html.escape(row['document_id'])}</div>")
            parts.append("</figcaption></figure>")
        parts.append("</div></section>")
    parts.append("</main></body></html>")
    OUT_HTML.write_text("\n".join(parts), encoding="utf-8")
    print(
        json.dumps(
            {
                "html": str(OUT_HTML),
                "csv": str(OUT_CSV),
                "images": len(rows),
                "rendered": rendered_ok,
                "all_rendered": rendered_ok == len(rows),
                "contacts": sorted({r["person_name"] for r in rows if r["person_name"]}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
