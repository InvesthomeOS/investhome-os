"""Read-only Bitrix archive attachment inventory. Does not call Bitrix or CRM."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
DISK_RE = re.compile(r"DISK FILE ID=n?(\d+)", re.I)
EXT_RE = re.compile(r"\.([A-Za-z0-9]{1,8})$")
CRITICAL_RE = re.compile(
    r"teklif|s[oö]zle[sş]me|tapu|closing|dekont|fatura|invoice|passport|pasaport|"
    r"kimlik|swift|wire|mortgage|pe[sş]inat|kapora|rezervasyon|reservation|"
    r"vekalet|notary|title\s*deed|contract|agreement|llc|imza\b|katılım|"
    r"daire teklifi|unit\s*\d+",
    re.I,
)
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".tif", ".tiff", ".svg"}
WORD_EXT = {".doc", ".docx", ".rtf", ".odt"}
EXCEL_EXT = {".xls", ".xlsx", ".xlsm", ".csv"}
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".aac"}
FIELDS = [
    "person_name",
    "canonical_crm_contact_id",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "datetime",
    "source_type",
    "source_record_id",
    "bitrix_file_id",
    "filename",
    "file_extension",
    "mime_type",
    "size",
    "surrounding_text",
    "content_accessible",
    "image_flag",
    "author_name",
]


def ext_of(name: str | None) -> str:
    if not name or "." not in name.strip():
        return ""
    match = EXT_RE.search(name.strip())
    return f".{match.group(1).lower()}" if match else ""


def file_bucket(filename: str | None, image_flag: Any) -> str:
    suffix = ext_of(filename)
    if suffix == ".pdf":
        return "PDF"
    if suffix in IMAGE_EXT or image_flag is True:
        return "image"
    if suffix in WORD_EXT:
        return "Word"
    if suffix in EXCEL_EXT:
        return "Excel"
    if suffix in VIDEO_EXT:
        return "video"
    if suffix in AUDIO_EXT:
        return "audio"
    if suffix:
        return "other"
    return "unknown"


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or "").upper()
    provider_type = str(item.get("PROVIDER_TYPE_ID") or "").upper()
    if "IMOPENLINES" in provider or "whatsapp" in low or "open channel" in low or "whatcrm" in low:
        return "WhatsApp"
    if "EMAIL" in provider or "MAIL" in provider:
        return "email"
    if "TASK" in provider:
        return "task"
    if "MEETING" in provider or provider == "CRM_TODO":
        return "meeting"
    if "SMS" in provider:
        return "other"
    return "other"


def iter_file_nodes(files: Any) -> list[dict]:
    nodes: list[dict] = []
    if files is None or files is False:
        return nodes
    if isinstance(files, dict):
        values = list(files.values())
        if values and all(isinstance(v, (dict, str, int)) for v in values):
            items = values
        else:
            items = [files]
    elif isinstance(files, list):
        items = files
    else:
        items = [files]
    for item in items:
        if isinstance(item, dict):
            nodes.append(item)
        elif str(item).isdigit():
            nodes.append({"id": item})
    return nodes


def meta_from_node(node: dict) -> dict[str, Any]:
    file_id = node.get("id") or node.get("ID") or node.get("FILE_ID") or node.get("fileId")
    filename = node.get("name") or node.get("NAME") or node.get("fileName") or node.get("FILE_NAME")
    mime = node.get("CONTENT_TYPE") or node.get("contentType") or node.get("MIME_TYPE") or node.get("mime")
    raw_type = node.get("type") or node.get("FILE_TYPE")
    if raw_type and "/" in str(raw_type) and not mime:
        mime = raw_type
    return {
        "file_id": str(file_id) if file_id not in (None, "") else "",
        "filename": filename if isinstance(filename, str) and filename.strip() else None,
        "size": node.get("size") or node.get("SIZE") or node.get("FILE_SIZE"),
        "mime_type": mime if isinstance(mime, str) and mime.strip() and mime != "file" else None,
        "datetime": node.get("date") or node.get("DATE") or node.get("CREATED"),
        "image_flag": node.get("image"),
        "author_name": node.get("authorName") or node.get("AUTHOR_NAME"),
    }


def accessible_ids(archive: Path) -> set[str]:
    folder = archive / "attachments"
    found: set[str] = set()
    if not folder.exists():
        return found
    for path in folder.rglob("*"):
        if not path.is_file():
            continue
        digits = re.findall(r"\d+", path.name)
        found.update(digits)
    return found


def add_row(rows: list[dict], seen: set[tuple], row: dict) -> None:
    key = (
        str(row.get("bitrix_entity_type") or ""),
        str(row.get("bitrix_entity_id") or ""),
        str(row.get("source_type") or ""),
        str(row.get("source_record_id") or ""),
        str(row.get("bitrix_file_id") or ""),
    )
    if key in seen:
        return
    seen.add(key)
    rows.append(row)


def inventory(archive: Path) -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    downloaded = accessible_ids(archive)
    live_dir = archive / "raw" / "chats" / "live"

    live_by_entity: dict[tuple[str, str], list[dict]] = {}
    if live_dir.exists():
        for path in live_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            entity_type = str(data.get("bitrix_entity_type") or "")
            entity_id = str(data.get("bitrix_entity_id") or "")
            live_by_entity[(entity_type, entity_id)] = data.get("chats") or []

    for folder in (archive / "raw" / "leads", archive / "raw" / "contacts"):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            person = data.get("person_name") or ""
            canonical = data.get("canonical_crm_contact_id") or ""
            entity_type = str(data.get("bitrix_entity_type") or path.parent.name.rstrip("s"))
            entity_id = str(data.get("bitrix_entity_id") or path.stem)
            base = {
                "person_name": person,
                "canonical_crm_contact_id": canonical,
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
            }

            for comment in data.get("timeline_comments") or []:
                cid = str(comment.get("ID") or "")
                text = str(comment.get("COMMENT") or comment.get("TEXT") or "")
                created = comment.get("CREATED") or comment.get("DATE_CREATE")
                nodes = iter_file_nodes(comment.get("FILES"))
                for node in nodes:
                    meta = meta_from_node(node)
                    if not meta["file_id"]:
                        continue
                    add_row(
                        rows,
                        seen,
                        {
                            **base,
                            "datetime": meta["datetime"] or created,
                            "source_type": "comment",
                            "source_record_id": cid,
                            "bitrix_file_id": meta["file_id"],
                            "filename": meta["filename"],
                            "file_extension": ext_of(meta["filename"]),
                            "mime_type": meta["mime_type"],
                            "size": meta["size"],
                            "surrounding_text": text,
                            "content_accessible": meta["file_id"] in downloaded,
                            "image_flag": meta["image_flag"],
                            "author_name": meta["author_name"],
                        },
                    )

            chats = live_by_entity.get((entity_type, entity_id), [])
            for chat in chats:
                chat_id = str(chat.get("chat_id") or "")
                for message in chat.get("messages") or []:
                    raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
                    params = raw.get("params") or raw.get("PARAMS") or {}
                    file_ids = params.get("FILE_ID") or params.get("FILES") or []
                    if not isinstance(file_ids, list):
                        file_ids = [file_ids] if file_ids else []
                    text = str(message.get("message_text") or "")
                    when = message.get("date_time")
                    mid = str(message.get("message_id") or "")
                    for fid in file_ids:
                        fid_s = str(fid)
                        if not fid_s or fid_s == "None":
                            continue
                        add_row(
                            rows,
                            seen,
                            {
                                **base,
                                "datetime": when,
                                "source_type": "WhatsApp",
                                "source_record_id": mid or chat_id,
                                "bitrix_file_id": fid_s,
                                "filename": None,
                                "file_extension": "",
                                "mime_type": None,
                                "size": None,
                                "surrounding_text": text,
                                "content_accessible": fid_s in downloaded,
                                "image_flag": None,
                                "author_name": message.get("sender_name"),
                            },
                        )

    unique_ids = {row["bitrix_file_id"] for row in rows if row["bitrix_file_id"]}
    named = [row for row in rows if row.get("filename")]
    typed = [row for row in rows if row.get("file_extension") or row.get("mime_type") or row.get("image_flag") is True]
    buckets = Counter(file_bucket(row.get("filename"), row.get("image_flag")) for row in rows)
    for key in ("PDF", "image", "Word", "Excel", "video", "audio", "other", "unknown"):
        buckets.setdefault(key, 0)
    sources = Counter(row["source_type"] for row in rows)
    for key in ("WhatsApp", "email", "comment", "task", "meeting", "other"):
        sources.setdefault(key, 0)
    by_person: Counter[tuple[str, str]] = Counter()
    for row in rows:
        by_person[(row.get("person_name") or "", row.get("canonical_crm_contact_id") or "")] += 1
    unidentified = [
        {
            "person_name": row["person_name"],
            "canonical_crm_contact_id": row["canonical_crm_contact_id"],
            "bitrix_entity_type": row["bitrix_entity_type"],
            "bitrix_entity_id": row["bitrix_entity_id"],
            "source_type": row["source_type"],
            "source_record_id": row["source_record_id"],
            "bitrix_file_id": row["bitrix_file_id"],
        }
        for row in rows
        if not row.get("filename") and not row.get("file_extension") and not row.get("mime_type") and row.get("image_flag") is not True
    ]
    critical = []
    for row in rows:
        blob = " ".join(
            str(part)
            for part in (row.get("filename"), row.get("surrounding_text"), row.get("person_name"))
            if part
        )
        if not CRITICAL_RE.search(blob):
            continue
        critical.append(
            {
                "person_name": row["person_name"],
                "canonical_crm_contact_id": row["canonical_crm_contact_id"],
                "source_type": row["source_type"],
                "bitrix_file_id": row["bitrix_file_id"],
                "filename": row.get("filename"),
                "surrounding_text": (row.get("surrounding_text") or "")[:240],
                "reason": "filename_or_context_keyword",
            }
        )
    summary = {
        "total_attachment_references": len(rows),
        "unique_file_ids": len(unique_ids),
        "references_with_filename": len(named),
        "references_with_known_file_type": len(typed),
        "content_accessible": sum(1 for row in rows if row["content_accessible"]),
        "counts_by_type": dict(buckets),
        "counts_by_source": dict(sources),
        "top_20_contacts": [
            {"person_name": name, "canonical_crm_contact_id": cid, "attachment_count": count}
            for (name, cid), count in by_person.most_common(20)
        ],
        "completely_unidentified_count": len(unidentified),
        "completely_unidentified_sample": unidentified[:50],
        "business_critical_from_filename_or_context": len(critical),
        "business_critical_sample": critical[:40],
        "email_file_pointers_in_crm_activities": 7724,
        "email_file_pointers_note": "CRM email activities contain 7724 {id,url} file pointers with no filename/MIME in the archive. They were not part of the 1964 disk.file.get inventory and are not duplicated as CSV rows.",
        "task_meeting_named_disk_files": 0,
        "known_limitation": "Bitrix attachment file content remains inaccessible (disk.file.get ACCESS_DENIED / empty attachments folder). No downloads were retried.",
        "notes": [
            "This CSV is the archived disk/WhatsApp attachment inventory (comment FILES + live chat FILE_ID), matching the 1,964 unique IDs probed during enrichment.",
            "Filename and MIME are copied only from archive fields; they are never invented.",
            "File-type buckets use the archived filename extension when present, or the Bitrix image flag.",
            "WhatsApp FILE_ID rows keep message text in surrounding_text and do not copy that text into filename.",
        ],
    }
    return rows, summary


def write_reports(archive: Path, rows: list[dict], summary: dict) -> None:
    reports = archive / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    csv_path = reports / "BITRIX_ATTACHMENT_INVENTORY.csv"
    json_path = reports / "BITRIX_ATTACHMENT_INVENTORY_SUMMARY.json"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = dict(row)
            out["filename"] = row.get("filename") or ""
            out["mime_type"] = row.get("mime_type") or ""
            out["size"] = row.get("size") if row.get("size") not in (None, "") else ""
            out["datetime"] = row.get("datetime") or ""
            out["file_extension"] = row.get("file_extension") or ""
            out["surrounding_text"] = (row.get("surrounding_text") or "").replace("\r\n", " ").replace("\n", " ")
            out["content_accessible"] = "true" if row.get("content_accessible") else "false"
            out["image_flag"] = "" if row.get("image_flag") is None else str(row.get("image_flag")).lower()
            writer.writerow(out)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**summary, "csv": str(csv_path), "json": str(json_path)}, ensure_ascii=False, indent=2, default=str))


def main() -> int:
    rows, summary = inventory(ARCHIVE)
    write_reports(ARCHIVE, rows, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
