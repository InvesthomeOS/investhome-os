"""Build the 42-file manual recovery package. Read-only against Bitrix. No CRM writes."""
from __future__ import annotations

import csv
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from link_agreement_documents import (  # type: ignore
    BitrixClient,
    ENV_PATH,
    EXISTING_MANIFEST,
    load_env,
    log,
    redact,
    safe_filename,
    utc_now,
    webhook_base,
)

PACKAGE = Path("/export/2026-09-final/BITRIX_MANUAL_RECOVERY")
ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
PROGRESS = PACKAGE / "reports" / "package_build.log"
BB_RE = re.compile(r"\[/?[biu]\]", re.I)
PHONE_RE = re.compile(r"^\d{10,15}\s*")
PERSON_FOLDERS = [
    ("Berk Çimen", "Berk_Cimen"),
    ("Birol Toykan", "Birol_Toykan"),
    ("Eda Kestellioglu Yurttutan", "Eda_Kestellioglu_Yurttutan"),
    ("Gökhan Bülbül", "Gokhan_Bulbul"),
]
FOLDER_BY_PERSON = dict(PERSON_FOLDERS)
CSV_FIELDS = [
    "person_name",
    "canonical_crm_contact_id",
    "destination_folder",
    "suggested_save_as",
    "source_type",
    "datetime",
    "source_record_id",
    "bitrix_file_id",
    "original_filename",
    "subject_or_message",
    "direct_file_url",
    "source_record_url",
    "crm_card_url",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "link_coverage",
    "filename_known",
]


def origin_of(client: BitrixClient) -> str:
    return client.origin.rstrip("/")


def crm_card_url(origin: str, entity_type: str, entity_id: str) -> str:
    kind = "lead" if entity_type == "lead" else "contact"
    return f"{origin}/crm/{kind}/details/{entity_id}/"


def email_direct_url(origin: str, file_id: str, activity_id: str) -> str:
    qs = urlencode({"fileId": file_id, "ownerTypeId": "6", "ownerId": activity_id})
    return f"{origin}/bitrix/tools/crm_show_file.php?{qs}"


def email_activity_url(origin: str, entity_type: str, entity_id: str, activity_id: str) -> str:
    card = crm_card_url(origin, entity_type, entity_id)
    return f"{card}?open_view={quote(activity_id)}"


def im_message_url(origin: str, dialog_id: str, message_id: str) -> str:
    return f"{origin}/online/?IM_HISTORY={quote(dialog_id)}&IM_MESSAGE={quote(message_id)}"


def im_dialog_url(origin: str, dialog_id: str) -> str:
    return f"{origin}/online/?IM_DIALOG={quote(dialog_id)}"


def clean_wa_name(text: str) -> str:
    cleaned = BB_RE.sub("", text or "")
    lines = [PHONE_RE.sub("", ln.strip()).strip() for ln in cleaned.splitlines()]
    lines = [ln for ln in lines if ln]
    if not lines:
        return ""
    cand = lines[-1]
    return cand[:180]


def suggested_name(file_id: str, original: str) -> str:
    original = (original or "").strip()
    if original:
        safe = safe_filename(original, file_id)
        stem, dot, ext = safe.rpartition(".")
        if dot and ext and f"bitrix-{file_id}" not in safe:
            return f"{stem}__bitrix-{file_id}.{ext}"
        if f"bitrix-{file_id}" in safe:
            return safe
        return f"{safe}__bitrix-{file_id}"
    return f"bitrix-file-{file_id}"


def load_archive_entity(entity_type: str, entity_id: str) -> dict:
    for folder in ("contacts", "leads"):
        path = ARCHIVE / "raw" / folder / f"{entity_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
    return {}


def load_archive_chats(entity_type: str, entity_id: str) -> dict:
    path = ARCHIVE / "raw" / "chats" / "live" / f"{entity_type}_{entity_id}.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def find_wa_meta(chats: dict, message_id: str, file_id: str) -> dict:
    out = {"datetime": "", "filename": "", "subject": "", "dialog_id": "", "chat_id": ""}
    for chat in chats.get("chats") or []:
        if not isinstance(chat, dict):
            continue
        chat_id = str(chat.get("chat_id") or "")
        dialog_id = str(chat.get("dialog_id") or (f"chat{chat_id}" if chat_id else ""))
        for message in chat.get("messages") or []:
            if not isinstance(message, dict):
                continue
            raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
            mid = str(message.get("message_id") or raw.get("id") or "")
            params = raw.get("params") or raw.get("PARAMS") or {}
            file_ids = params.get("FILE_ID") or [] if isinstance(params, dict) else []
            if not isinstance(file_ids, list):
                file_ids = [file_ids] if file_ids else []
            hit = (message_id and mid == message_id) or (file_id and str(file_id) in {str(x) for x in file_ids})
            if not hit:
                continue
            text = str(message.get("message_text") or message.get("text") or raw.get("text") or "")
            out["datetime"] = str(message.get("date_time") or raw.get("date") or "")
            out["filename"] = clean_wa_name(text)
            out["subject"] = text.replace("\n", " ").strip()[:240]
            out["dialog_id"] = dialog_id
            out["chat_id"] = chat_id
            return out
    return out


def find_email_meta(entity: dict, activity_id: str, file_id: str) -> dict:
    out = {"datetime": "", "filename": "", "subject": ""}
    for activity in entity.get("crm_activities") or []:
        if not isinstance(activity, dict):
            continue
        if str(activity.get("ID") or "") != str(activity_id):
            continue
        out["datetime"] = str(activity.get("CREATED") or activity.get("START_TIME") or activity.get("LAST_UPDATED") or "")
        out["subject"] = str(activity.get("SUBJECT") or "")[:240]
        files = activity.get("FILES") or []
        if not isinstance(files, list):
            files = [files]
        for node in files:
            if not isinstance(node, dict):
                continue
            nid = str(node.get("id") or node.get("ID") or "")
            if nid == str(file_id):
                out["filename"] = str(node.get("name") or node.get("NAME") or "")
                break
        return out
    return out


def live_activity(client: BitrixClient, activity_id: str) -> dict:
    body = client.call("crm.activity.get", {"id": activity_id})
    result = body.get("result") if not body.get("error") else None
    return result if isinstance(result, dict) else {}


def filename_from_activity(activity: dict, file_id: str) -> str:
    files = activity.get("FILES") or []
    if not isinstance(files, list):
        files = [files]
    for node in files:
        if not isinstance(node, dict):
            continue
        if str(node.get("id") or node.get("ID") or "") == str(file_id):
            return str(node.get("name") or node.get("NAME") or node.get("fileName") or "")
    return ""


def build_rows(client: BitrixClient) -> list[dict]:
    origin = origin_of(client)
    with EXISTING_MANIFEST.open(encoding="utf-8", newline="") as handle:
        source_rows = [r for r in csv.DictReader(handle) if (r.get("downloaded") or "").lower() != "yes"]
    activity_cache: dict[str, dict] = {}
    entity_cache: dict[tuple[str, str], dict] = {}
    chat_cache: dict[tuple[str, str], dict] = {}
    out: list[dict] = []
    for src in source_rows:
        person = src.get("person_name") or ""
        folder = FOLDER_BY_PERSON.get(person)
        if not folder:
            raise SystemExit(f"unexpected person in remaining set: {person}")
        entity_type = src.get("bitrix_entity_type") or "contact"
        entity_id = str(src.get("bitrix_entity_id") or "")
        source_type = src.get("source_type") or ""
        source_id = str(src.get("source_record_id") or "")
        file_id = str(src.get("bitrix_file_id") or "")
        filename = (src.get("original_filename") or "").strip()
        datetime_val = ""
        subject = ""
        direct = ""
        source_url = ""
        card = crm_card_url(origin, entity_type, entity_id) if entity_id else ""
        key = (entity_type, entity_id)
        if key not in entity_cache:
            entity_cache[key] = load_archive_entity(entity_type, entity_id)
        if key not in chat_cache:
            chat_cache[key] = load_archive_chats(entity_type, entity_id)
        if source_type.lower() == "email":
            archived = find_email_meta(entity_cache[key], source_id, file_id)
            datetime_val = archived["datetime"]
            subject = archived["subject"]
            filename = filename or archived["filename"]
            if source_id and source_id not in activity_cache:
                activity_cache[source_id] = live_activity(client, source_id)
            live = activity_cache.get(source_id) or {}
            if live:
                datetime_val = datetime_val or str(live.get("CREATED") or live.get("START_TIME") or "")
                subject = subject or str(live.get("SUBJECT") or "")
                filename = filename or filename_from_activity(live, file_id)
            if file_id and source_id:
                direct = email_direct_url(origin, file_id, source_id)
            source_url = email_activity_url(origin, entity_type, entity_id, source_id) if source_id else card
        else:
            wa = find_wa_meta(chat_cache[key], source_id, file_id)
            datetime_val = wa["datetime"]
            filename = filename or wa["filename"]
            subject = wa["subject"] or filename
            dialog_id = wa["dialog_id"] or "chat13496"
            if source_id:
                source_url = im_message_url(origin, dialog_id, source_id)
            else:
                source_url = im_dialog_url(origin, dialog_id)
        coverage = "direct+source" if direct and source_url else ("direct" if direct else "source")
        row = {
            "person_name": person,
            "canonical_crm_contact_id": src.get("canonical_crm_contact_id") or "",
            "destination_folder": folder,
            "suggested_save_as": suggested_name(file_id, filename),
            "source_type": source_type,
            "datetime": datetime_val,
            "source_record_id": source_id,
            "bitrix_file_id": file_id,
            "original_filename": filename,
            "subject_or_message": subject,
            "direct_file_url": direct,
            "source_record_url": source_url,
            "crm_card_url": card,
            "bitrix_entity_type": entity_type,
            "bitrix_entity_id": entity_id,
            "link_coverage": coverage,
            "filename_known": "yes" if filename else "no",
            "agreement_id": src.get("agreement_id") or "",
            "project_group": src.get("project_group") or "",
        }
        out.append(row)
    return out


def write_save_lists(rows: list[dict]) -> None:
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_folder[row["destination_folder"]].append(row)
    for folder, items in by_folder.items():
        path = PACKAGE / folder / "SAVE_AS.txt"
        lines = [
            f"Person: {items[0]['person_name']}",
            f"Canonical CRM contact: {items[0]['canonical_crm_contact_id']}",
            "Save each Bitrix attachment using the suggested filename so import can match Bitrix file ID.",
            "Do not match or rename by person name.",
            "",
        ]
        for row in items:
            lines.append(f"- {row['suggested_save_as']}")
            lines.append(f"    source: {row['source_type']}  id={row['source_record_id']}  file={row['bitrix_file_id']}")
            if row["original_filename"]:
                lines.append(f"    original: {row['original_filename']}")
            if row["datetime"]:
                lines.append(f"    when: {row['datetime']}")
            if row["subject_or_message"]:
                lines.append(f"    context: {row['subject_or_message'][:180]}")
            link = row["direct_file_url"] or row["source_record_url"]
            lines.append(f"    open: {link}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")


def render_html(rows: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["person_name"]].append(row)
    known = sum(1 for r in rows if r["filename_known"] == "yes")
    linked = sum(1 for r in rows if r["direct_file_url"] or r["source_record_url"])
    parts = [
        "<!DOCTYPE html><html lang='tr'><head><meta charset='utf-8'>",
        "<title>Bitrix manual recovery — 42 files</title>",
        "<style>",
        "body{font:15px/1.45 system-ui,Segoe UI,sans-serif;margin:0;background:#f4f1ea;color:#1b1b1b}",
        "header{background:#13294b;color:#fff;padding:28px 32px}",
        "header p{max-width:860px;opacity:.92}",
        "main{padding:24px 32px 64px;max-width:1180px}",
        ".stats{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0 8px}",
        ".stat{background:#fff;border:1px solid #d9d3c7;border-radius:10px;padding:10px 14px;min-width:120px}",
        ".stat b{display:block;font-size:22px}",
        "section{background:#fff;border:1px solid #d9d3c7;border-radius:14px;margin:22px 0;overflow:hidden}",
        "h2{margin:0;padding:16px 20px;background:#efe8dc;font-size:18px}",
        "table{width:100%;border-collapse:collapse}",
        "th,td{text-align:left;vertical-align:top;padding:10px 12px;border-top:1px solid #eee;font-size:13px}",
        "th{background:#faf7f2;font-weight:600}",
        "a{color:#0b57d0}",
        ".mono{font-family:ui-monospace,Consolas,monospace;font-size:12px;word-break:break-all}",
        ".muted{color:#5c5852}",
        ".chip{display:inline-block;background:#e8f1ff;color:#0b3d91;border-radius:999px;padding:1px 8px;font-size:12px}",
        "ol{max-width:820px}",
        "</style></head><body>",
        "<header><h1>Manual recovery package — 42 remaining files</h1>",
        "<p>Download each attachment while logged into Bitrix, then save it into that person's folder using the suggested filename. The import helper matches Bitrix file ID / original filename / source metadata. It never assigns ownership by person name.</p></header>",
        "<main>",
        "<div class='stats'>",
        f"<div class='stat'><b>42</b> files</div>",
        f"<div class='stat'><b>4</b> people</div>",
        f"<div class='stat'><b>{known}</b> filenames known</div>",
        f"<div class='stat'><b>{linked}</b> with a Bitrix link</div>",
        "</div>",
        "<ol>",
        "<li>Open the <b>Download file</b> or <b>Open source</b> link while signed into Bitrix.</li>",
        "<li>Save the file into the destination folder using the exact <b>Save as</b> name.</li>",
        "<li>If the direct file link asks you to log in, use <b>Open source</b> and download the attachment from that activity or WhatsApp thread.</li>",
        "<li>After files are in the four folders, run the import helper in dry-run first.</li>",
        "</ol>",
    ]
    for person, folder in PERSON_FOLDERS:
        items = grouped.get(person) or []
        parts.append(f"<section id='{html.escape(folder)}'><h2>{html.escape(person)} <span class='chip'>{len(items)}</span> &nbsp; <span class='muted'>{html.escape(folder)}/</span></h2>")
        parts.append("<table><thead><tr>")
        for col in (
            "When",
            "Source",
            "File / activity",
            "Original name",
            "Context",
            "Open in Bitrix",
            "Save as / folder",
        ):
            parts.append(f"<th>{col}</th>")
        parts.append("</tr></thead><tbody>")
        for row in items:
            direct = row["direct_file_url"]
            source = row["source_record_url"]
            card = row["crm_card_url"]
            links = []
            if direct:
                links.append(f"<a href='{html.escape(direct)}' target='_blank' rel='noopener'>Download file</a>")
            if source:
                links.append(f"<a href='{html.escape(source)}' target='_blank' rel='noopener'>Open source</a>")
            if card:
                links.append(f"<a href='{html.escape(card)}' target='_blank' rel='noopener'>CRM card</a>")
            name = row["original_filename"] or "<span class='muted'>unknown — use Save as</span>"
            parts.append("<tr>")
            parts.append(f"<td>{html.escape(row['datetime'] or '—')}</td>")
            parts.append(f"<td>{html.escape(row['source_type'])}</td>")
            parts.append(
                f"<td>file <span class='mono'>{html.escape(row['bitrix_file_id'])}</span><br>"
                f"<span class='muted'>record {html.escape(row['source_record_id'])}</span></td>"
            )
            parts.append(f"<td>{name if name.startswith('<') else html.escape(name)}</td>")
            parts.append(f"<td>{html.escape(row['subject_or_message'] or '—')}</td>")
            parts.append(f"<td>{'<br>'.join(links) or '—'}</td>")
            parts.append(
                f"<td><span class='mono'>{html.escape(row['suggested_save_as'])}</span><br>"
                f"<span class='muted'>{html.escape(row['destination_folder'])}/</span></td>"
            )
            parts.append("</tr>")
        parts.append("</tbody></table></section>")
    parts.append(f"<p class='muted'>Generated {html.escape(utc_now())}. Canonical CRM contact IDs are preserved from the agreement document manifest.</p>")
    parts.append("</main></body></html>")
    return "\n".join(parts)


def main() -> None:
    env = load_env(ENV_PATH)
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    if not raw:
        print("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
        return
    client = BitrixClient(webhook_base(raw))
    (PACKAGE / "reports").mkdir(parents=True, exist_ok=True)
    for _, folder in PERSON_FOLDERS:
        (PACKAGE / folder).mkdir(parents=True, exist_ok=True)
    log(PROGRESS, "BUILD_START")
    rows = build_rows(client)
    reports = PACKAGE / "reports"
    csv_path = reports / "BITRIX_MANUAL_RECOVERY_42.csv"
    html_path = reports / "BITRIX_MANUAL_RECOVERY_42.html"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    html_path.write_text(render_html(rows), encoding="utf-8")
    write_save_lists(rows)
    catalog = PACKAGE / "expected_42.json"
    catalog.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    known = sum(1 for r in rows if r["filename_known"] == "yes")
    linked = sum(1 for r in rows if r["direct_file_url"] or r["source_record_url"])
    summary = {
        "rows": len(rows),
        "html": str(html_path),
        "csv": str(csv_path),
        "folders": [str(PACKAGE / folder) for _, folder in PERSON_FOLDERS],
        "all_have_direct_or_source_link": linked == len(rows),
        "filenames_known": known,
        "by_person": {person: sum(1 for r in rows if r["person_name"] == person) for person, _ in PERSON_FOLDERS},
        "generated_at": utc_now(),
        "bitrix_calls": client.call_count,
    }
    (reports / "BITRIX_MANUAL_RECOVERY_42_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    log(PROGRESS, f"BUILD_DONE rows={len(rows)} known_names={known} linked={linked}")
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
