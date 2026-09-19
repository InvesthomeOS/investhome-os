"""Recover remaining 66 inaccessible agreement-contact files via admin webhook.

Does not rescan contacts, does not redownload successes, does not modify Bitrix.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID
from urllib.parse import unquote, urlparse
import urllib.error
import urllib.parse
import urllib.request

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.config.documents_config import ALLOWED_EXTENSIONS, infer_file_kind
from investhome_api.db.session import SessionLocal
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
from investhome_api.services.document_service import create_document_analysis
from investhome_api.services.document_validation import compute_checksum, generate_storage_key
from investhome_api.services.storage.factory import get_storage_provider, provider_enum

from link_agreement_documents import (  # type: ignore
    BitrixClient,
    EXISTING_MANIFEST,
    HTML_HEAD,
    MANIFEST_FIELDS,
    OUT,
    ENV_PATH,
    existing_document,
    ext_of,
    import_document,
    import_tag,
    link_exists,
    load_agreement_contacts,
    load_env,
    log,
    mime_of,
    redact,
    safe_filename,
    unique_dest,
    utc_now,
    webhook_base,
)

PROGRESS = OUT / "reports" / "remaining66_progress.log"
OWNER_TYPE = {"lead": "1", "deal": "2", "contact": "3", "company": "4", "activity": "6"}
ENTITY_TYPE_ID = {"lead": 1, "deal": 2, "contact": 3}
ARCHIVE_CHATS = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE/raw/chats/live")
ITEM_CACHE: dict[tuple[str, str], dict | None] = {}
CHAT_CACHE: dict[str, dict] = {}


def with_auth(client: BitrixClient, url: str) -> str:
    if not url:
        return url
    token = [s for s in Path(client.base.replace("https://", "")).parts if s]
    # token is last path segment of webhook
    segs = [s for s in __import__("urllib.parse", fromlist=["urlparse"]).urlparse(client.base).path.split("/") if s]
    auth = segs[-1] if segs else ""
    from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

    if url.startswith("/"):
        url = client.origin + url
    parsed = urlparse(url)
    q = parse_qs(parsed.query, keep_blank_values=True)
    if auth and (not q.get("auth") or q.get("auth") == [""]):
        q["auth"] = [auth]
    return urlunparse(parsed._replace(query=urlencode(q, doseq=True)))


def walk_urls_and_ids(obj: Any, prefix: str = "") -> tuple[list[str], list[str], list[dict]]:
    urls: list[str] = []
    ids: list[str] = []
    files: list[dict] = []
    if obj is None:
        return urls, ids, files
    if isinstance(obj, dict):
        lower = {str(k).lower(): v for k, v in obj.items()}
        for key in (
            "url",
            "urlmachine",
            "urldownload",
            "download_url",
            "downloadurl",
            "showurl",
            "urlshow",
            "urlpreview",
            "src",
            "href",
        ):
            val = lower.get(key)
            if isinstance(val, str) and val.startswith(("http", "/")):
                urls.append(val)
        for key in ("id", "fileid", "file_id", "diskid", "disk_id", "objectid", "attachedid", "attached_id"):
            val = lower.get(key)
            if val not in (None, "", [], {}):
                ids.append(str(val))
        name = lower.get("name") or lower.get("filename") or lower.get("originalname")
        if name or ids:
            files.append(obj)
        for val in obj.values():
            u, i, f = walk_urls_and_ids(val)
            urls.extend(u)
            ids.extend(i)
            files.extend(f)
    elif isinstance(obj, list):
        for item in obj:
            u, i, f = walk_urls_and_ids(item)
            urls.extend(u)
            ids.extend(i)
            files.extend(f)
    elif isinstance(obj, (int, str)) and str(obj).isdigit() and len(str(obj)) >= 3:
        ids.append(str(obj))
    elif isinstance(obj, str) and obj.startswith(("http", "/bitrix/")):
        urls.append(obj)
    return urls, ids, files


def is_binary(data: bytes, ctype: str | None) -> bool:
    if not data or len(data) < 8:
        return False
    if HTML_HEAD.search(data[:200]) or "text/html" in (ctype or ""):
        return False
    if data.lstrip()[:1] == b"{" and b'"error"' in data[:400]:
        return False
    return True


def try_download(client: BitrixClient, url: str) -> tuple[bytes | None, str | None, str | None]:
    if not url:
        return None, None, "no_url"
    for candidate in (url, with_auth(client, url)):
        content, mime, err = client.download(candidate)
        if content and is_binary(content, mime):
            return content, mime, None
    return None, None, err or "download_failed"


def try_disk(client: BitrixClient, file_id: str) -> tuple[bytes | None, str | None, str | None, str | None]:
    if not file_id:
        return None, None, None, "missing_id"
    for method, payload in (
        ("disk.file.get", {"id": file_id}),
        ("disk.attachedObject.get", {"id": file_id}),
        ("im.disk.file.get", {"id": file_id}),
    ):
        body = client.call(method, payload)
        result = body.get("result") if not body.get("error") else None
        if not isinstance(result, dict):
            continue
        name = result.get("NAME") or result.get("name")
        inner = result.get("FILE") if isinstance(result.get("FILE"), dict) else {}
        urls = [
            result.get("DOWNLOAD_URL") or result.get("downloadUrl") or "",
            inner.get("DOWNLOAD_URL") or inner.get("downloadUrl") or "",
        ]
        for url in urls:
            content, mime, err = try_download(client, str(url))
            if content:
                return content, name, mime, None
    return None, None, None, "disk_methods_failed"


def show_file_urls(client: BitrixClient, file_id: str, owner_type: str, owner_id: str) -> list[str]:
    origin = client.origin
    type_id = OWNER_TYPE.get(owner_type, owner_type)
    return [
        f"{origin}/bitrix/tools/crm_show_file.php?fileId={file_id}&ownerTypeId={type_id}&ownerId={owner_id}",
        f"{origin}/bitrix/tools/crm_show_file.php?fileId={file_id}&ownerId={owner_id}&ownerType={owner_type.upper()}",
        f"{origin}/bitrix/tools/disk/uf.php?attachedId={file_id}",
        f"{origin}/bitrix/components/bitrix/crm.field.file/show_file.php?ownerId={owner_id}&ownerType={owner_type}&fileId={file_id}",
    ]


def activity_owner_ok(payload: dict, row: dict) -> str | None:
    owner_id = str(payload.get("OWNER_ID") or payload.get("ownerId") or "")
    owner_type = str(payload.get("OWNER_TYPE_ID") or payload.get("OWNER_TYPE") or payload.get("ownerTypeId") or "")
    expected_id = str(row.get("bitrix_entity_id") or "")
    expected_type = str(row.get("bitrix_entity_type") or "")
    expected_type_id = OWNER_TYPE.get(expected_type, expected_type)
    if owner_id and expected_id and owner_id != expected_id:
        return f"REVIEW_REQUIRED: activity OWNER_ID {owner_id} != bitrix_entity_id {expected_id}"
    if owner_type and expected_type_id and str(owner_type) not in {expected_type, expected_type_id, expected_type.upper()}:
        return f"REVIEW_REQUIRED: activity OWNER_TYPE {owner_type} != {expected_type}"
    return None


def recover_email(client: BitrixClient, row: dict) -> tuple[bytes | None, str | None, str | None, str | None]:
    file_id = str(row.get("bitrix_file_id") or "")
    source_id = str(row.get("source_record_id") or "")
    filename = (row.get("original_filename") or "").strip() or None
    reasons: list[str] = []
    if not source_id:
        return None, filename, None, "missing_activity_id"
    activity = client.call("crm.activity.get", {"id": source_id})
    payload = activity.get("result") if not activity.get("error") else None
    if not isinstance(payload, dict):
        return None, filename, None, f"crm.activity.get:{activity.get('error') or activity.get('error_description')}"
    conflict = activity_owner_ok(payload, row)
    if conflict:
        return None, filename, None, conflict
    configurable = client.call("crm.activity.configurable.get", {"id": source_id})
    extra = configurable.get("result") if not configurable.get("error") else None
    if configurable.get("error"):
        reasons.append(f"crm.activity.configurable.get:{configurable.get('error')}")
    mail_id = payload.get("ASSOCIATED_ENTITY_ID") or payload.get("UF_MAIL_MESSAGE")
    settings = payload.get("SETTINGS") if isinstance(payload.get("SETTINGS"), dict) else {}
    if not mail_id:
        mail_id = settings.get("MESSAGE_ID") or settings.get("MAIL_MESSAGE_ID")
    mail_payload = None
    if mail_id and str(mail_id) not in {"0", "None"}:
        mail = client.call("mail.message.get", {"id": mail_id})
        mail_payload = mail.get("result") if not mail.get("error") else None
        if mail.get("error"):
            reasons.append(f"mail.message.get:{mail.get('error')}")
    blob = {
        "FILES": payload.get("FILES"),
        "STORAGE_ELEMENT_IDS": payload.get("STORAGE_ELEMENT_IDS"),
        "WEBDAV_ELEMENTS": payload.get("WEBDAV_ELEMENTS"),
        "UF_CRM_FILES": payload.get("UF_CRM_FILES"),
        "configurable": extra,
        "mail_attachments": None,
    }
    if isinstance(mail_payload, dict):
        blob["mail_attachments"] = {
            k: mail_payload.get(k)
            for k in mail_payload
            if any(tok in str(k).upper() for tok in ("FILE", "ATTACH", "DISK"))
        } or mail_payload
    urls, ids, files = walk_urls_and_ids(blob)
    matched: list[dict] = []
    unmatched_live: list[dict] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        lower = {str(k).lower(): v for k, v in item.items()}
        ids_here = {str(lower.get(k) or "") for k in ("id", "fileid", "file_id")}
        if file_id and file_id in ids_here:
            matched.append(item)
        elif lower.get("url") or lower.get("urlmachine") or lower.get("urldownload") or lower.get("name"):
            unmatched_live.append(item)
    targets = matched or unmatched_live
    tried_urls: set[str] = set()
    tried_ids: set[str] = set()
    for item in targets:
        fname = item.get("name") or item.get("NAME") or item.get("fileName") or filename
        u, i, _ = walk_urls_and_ids(item)
        for url in u:
            if url in tried_urls:
                continue
            tried_urls.add(url)
            content, mime, fname2, err = download_silent(client, url)
            if content:
                return content, fname2 or fname, mime, None
            reasons.append(err or "live_activity_url_failed")
        for fid in i:
            if fid in tried_ids:
                continue
            tried_ids.add(fid)
            content, name, mime, err = try_disk(client, fid)
            if content:
                return content, name or fname, mime, None
            reasons.append(err or f"disk:{fid}")
    for url in urls:
        if url in tried_urls:
            continue
        tried_urls.add(url)
        content, mime, fname2, err = download_silent(client, url)
        if content:
            return content, fname2 or filename, mime, None
        reasons.append(err or "activity_url_failed")
    live_ids = []
    if file_id:
        live_ids.append(file_id)
    for fid in ids:
        if fid not in live_ids:
            live_ids.append(fid)
    for fid in live_ids[:8]:
        if fid in tried_ids:
            continue
        tried_ids.add(fid)
        content, name, mime, err = try_disk(client, fid)
        if content:
            return content, name or filename, mime, None
        reasons.append(err or f"disk:{fid}")
    if not reasons:
        reasons.append("email_live_descriptor_has_no_downloadable_binary")
    return None, filename, None, "; ".join(dict.fromkeys(reasons))[:400]


def download_silent(client: BitrixClient, url: str) -> tuple[bytes | None, str | None, str | None, str | None]:
    """GET a URL; return content, mime, filename, error. Never logs the URL."""
    if not url:
        return None, None, None, "no_url"
    if url.startswith("/"):
        url = client.origin + url
    last_err = "download_failed"
    candidates = [url]
    if "/rest/" not in url:
        auth_url = with_auth(client, url)
        if auth_url != url:
            candidates.append(auth_url)
    for candidate in candidates:
        client._wait()
        client.call_count += 1
        req = urllib.request.Request(candidate, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
                disp = resp.headers.get("Content-Disposition") or ""
                data = resp.read()
            client._last = time.time()
        except urllib.error.HTTPError as exc:
            client._last = time.time()
            last_err = f"HTTP {exc.code}"
            continue
        except Exception as exc:  # noqa: BLE001
            last_err = redact(str(exc), client.base)[:160]
            continue
        if not data or not is_binary(data, ctype):
            last_err = (
                "html_login_or_error_page"
                if data and (HTML_HEAD.search(data[:200]) or "text/html" in ctype)
                else "empty_or_invalid"
            )
            continue
        fname = None
        match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disp, re.I)
        if match:
            fname = unquote(match.group(1).strip())
        return data, ctype, fname, None
    return None, None, None, last_err


def item_field_key(uf_name: str) -> str:
    if uf_name.startswith("UF_CRM_"):
        return "ufCrm_" + uf_name[7:]
    return uf_name


def crm_item(client: BitrixClient, entity_type: str, entity_id: str) -> dict | None:
    key = (entity_type, entity_id)
    if key in ITEM_CACHE:
        return ITEM_CACHE[key]
    type_id = ENTITY_TYPE_ID.get(entity_type)
    if not type_id:
        ITEM_CACHE[key] = None
        return None
    body = client.call("crm.item.get", {"entityTypeId": type_id, "id": entity_id})
    item = (body.get("result") or {}).get("item") if not body.get("error") else None
    ITEM_CACHE[key] = item if isinstance(item, dict) else None
    return ITEM_CACHE[key]


def recover_entity_field(client: BitrixClient, row: dict) -> tuple[bytes | None, str | None, str | None, str | None, str | None]:
    file_id = str(row.get("bitrix_file_id") or "")
    entity_type = row.get("bitrix_entity_type") or "contact"
    entity_id = str(row.get("bitrix_entity_id") or "")
    field = str(row.get("source_record_id") or "")
    filename = (row.get("original_filename") or "").strip() or None
    item = crm_item(client, entity_type, entity_id)
    if not item:
        return None, filename, None, "crm.item.get_failed", file_id
    live_id = str(item.get("id") or "")
    if live_id and live_id != entity_id:
        return None, filename, None, "REVIEW_REQUIRED: live entity id mismatch", file_id
    def file_nodes(val: Any) -> list[dict]:
        if isinstance(val, dict) and (val.get("urlMachine") or val.get("url") or val.get("id")):
            return [val]
        if isinstance(val, list):
            out: list[dict] = []
            for item_val in val:
                out.extend(file_nodes(item_val))
            return out
        return []

    candidates: list[dict] = []
    wanted_key = item_field_key(field) if field.startswith("UF_") else ""
    for key, val in item.items():
        nodes = file_nodes(val)
        if not nodes:
            continue
        for node in nodes:
            if wanted_key and key == wanted_key:
                candidates.insert(0, node)
            elif file_id and str(node.get("id") or "") == file_id:
                candidates.append(node)
            elif not wanted_key and (str(key).startswith("ufCrm") or str(key).upper() == "PHOTO"):
                candidates.append(node)
    if not candidates:
        return None, filename, None, "live_uf_file_missing", file_id
    reasons: list[str] = []
    for node in candidates:
        live_file_id = str(node.get("id") or file_id)
        for url_key in ("urlMachine", "url"):
            content, mime, fname, err = download_silent(client, str(node.get(url_key) or ""))
            if content:
                if not filename:
                    if content.startswith(b"%PDF"):
                        filename = fname or "Identification.pdf"
                    elif content[:3] == b"\xff\xd8\xff":
                        filename = fname or "Identification.jpg"
                    elif content.startswith(b"\x89PNG"):
                        filename = fname or "Identification.png"
                    else:
                        filename = fname or f"Identification-{live_file_id}"
                return content, filename, mime, None, live_file_id
            reasons.append(f"{url_key}:{err}")
    return None, filename, None, "; ".join(dict.fromkeys(reasons))[:400], file_id


def load_archive_chats(entity_type: str, entity_id: str) -> dict:
    key = f"{entity_type}_{entity_id}"
    if key in CHAT_CACHE:
        return CHAT_CACHE[key]
    path = ARCHIVE_CHATS / f"{key}.json"
    data: dict = {}
    if path.exists():
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            data = loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            data = {}
    CHAT_CACHE[key] = data
    return data


def archive_dialog_for_file(archive: dict, message_id: str, file_id: str) -> tuple[str, str, dict | None]:
    for chat in archive.get("chats") or []:
        if not isinstance(chat, dict):
            continue
        chat_id = str(chat.get("chat_id") or "")
        dialog_id = str(chat.get("dialog_id") or "")
        if not dialog_id and chat_id:
            dialog_id = chat_id if str(chat_id).startswith("chat") else f"chat{chat_id}"
        files_map = chat.get("files") or {}
        node = None
        if isinstance(files_map, dict):
            node = files_map.get(file_id)
            if node is None and file_id.isdigit():
                node = files_map.get(int(file_id))
        hit = isinstance(node, dict)
        for message in chat.get("messages") or []:
            if not isinstance(message, dict):
                continue
            raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
            mid = str(message.get("message_id") or raw.get("id") or "")
            params = raw.get("params") or raw.get("PARAMS") or {}
            file_ids = params.get("FILE_ID") or [] if isinstance(params, dict) else []
            if not isinstance(file_ids, list):
                file_ids = [file_ids] if file_ids else []
            if (message_id and mid == message_id) or (file_id and str(file_id) in {str(x) for x in file_ids}):
                hit = True
                break
        if hit and dialog_id:
            return chat_id, dialog_id, node if isinstance(node, dict) else None
    return "", "", None


def recover_whatsapp(client: BitrixClient, row: dict) -> tuple[bytes | None, str | None, str | None, str | None, str | None]:
    file_id = str(row.get("bitrix_file_id") or "")
    source_id = str(row.get("source_record_id") or "")
    filename = (row.get("original_filename") or "").strip() or None
    entity_type = str(row.get("bitrix_entity_type") or "contact")
    entity_id = str(row.get("bitrix_entity_id") or "")
    archive = load_archive_chats(entity_type, entity_id)
    chat_id, dialog_id, archive_node = archive_dialog_for_file(archive, source_id, file_id)
    reasons: list[str] = []
    live_file_id = file_id
    if archive_node:
        fname = archive_node.get("name") or archive_node.get("NAME")
        if fname:
            filename = fname
    if not dialog_id:
        reasons.append("archive_chat_not_found_for_this_contact")
        content, name, mime, err = try_disk(client, file_id)
        if content:
            return content, name or filename, mime, None, file_id
        reasons.append(err or "disk_failed")
        return None, filename, None, "; ".join(dict.fromkeys(reasons))[:400], file_id
    params: dict[str, Any] = {"DIALOG_ID": dialog_id, "LIMIT": 20}
    if source_id.isdigit():
        params["LAST_ID"] = int(source_id) + 1
    body = client.call("im.dialog.messages.get", params)
    result = body.get("result") if not body.get("error") else None
    if not isinstance(result, dict):
        reasons.append(f"im.dialog.messages.get:{body.get('error') or body.get('error_description')}")
        content, name, mime, err = try_disk(client, file_id)
        if content:
            return content, name or filename, mime, None, file_id
        reasons.append(err or "disk_failed")
        return None, filename, None, "; ".join(dict.fromkeys(reasons))[:400], file_id
    messages = result.get("messages") or []
    files_map = result.get("files") or result.get("FILES") or {}
    live_ids: list[str] = []
    for message in messages if isinstance(messages, list) else []:
        mid = str(message.get("id") or message.get("ID") or "")
        if source_id and mid != source_id:
            continue
        live_chat = str(message.get("chat_id") or message.get("chatId") or "")
        if live_chat and chat_id and live_chat != chat_id and f"chat{live_chat}" != dialog_id:
            return None, filename, None, f"REVIEW_REQUIRED: live chat {live_chat} != archive chat {chat_id}", file_id
        msg_params = message.get("params") or message.get("PARAMS") or {}
        file_ids = msg_params.get("FILE_ID") or [] if isinstance(msg_params, dict) else []
        if not isinstance(file_ids, list):
            file_ids = [file_ids] if file_ids else []
        live_ids.extend(str(x) for x in file_ids if x not in (None, "", []))
        fname = (message.get("text") or "").strip()
        if fname and "." in fname and len(fname) < 180:
            filename = fname
    if file_id and file_id not in live_ids:
        live_ids.append(file_id)
    if live_ids:
        live_file_id = live_ids[0]
    nodes: list[Any] = []
    if isinstance(files_map, dict):
        for fid in live_ids:
            node = files_map.get(fid)
            if node is None and fid.isdigit():
                node = files_map.get(int(fid))
            if node:
                nodes.append(node)
    elif isinstance(files_map, list):
        nodes.extend(files_map)
    tried_ids: set[str] = set()
    for node in nodes:
        urls, ids, _ = walk_urls_and_ids(node)
        fname = None
        if isinstance(node, dict):
            fname = node.get("name") or node.get("NAME") or filename
        for url in urls:
            content, mime, fname2, err = download_silent(client, url)
            if content:
                return content, fname2 or fname or filename, mime, None, live_file_id
            reasons.append(err or "im_file_url_failed")
        for fid in ids or live_ids:
            if fid in tried_ids:
                continue
            tried_ids.add(fid)
            content, name, mime, err = try_disk(client, fid)
            if content:
                return content, name or fname or filename, mime, None, fid
            reasons.append(err or f"disk:{fid}")
    for fid in live_ids:
        if fid in tried_ids:
            continue
        tried_ids.add(fid)
        content, name, mime, err = try_disk(client, fid)
        if content:
            return content, name or filename, mime, None, fid
        reasons.append(err or f"disk:{fid}")
    if isinstance(files_map, list) and not files_map:
        reasons.append("im.dialog.files_empty")
    return None, filename, None, "; ".join(dict.fromkeys(reasons))[:400] or "whatsapp_binary_inaccessible", live_file_id


def recover_row(client: BitrixClient, row: dict) -> dict:
    source = (row.get("source_type") or "").strip()
    live_file_id = str(row.get("bitrix_file_id") or "")
    if source == "email":
        content, filename, mime, err = recover_email(client, row)
    elif source == "entity_field":
        content, filename, mime, err, live_file_id = recover_entity_field(client, row)
    elif source.lower() in {"whatsapp", "open_channel", "imopenlines"}:
        content, filename, mime, err, live_file_id = recover_whatsapp(client, row)
    else:
        content, filename, mime, err, live_file_id = recover_whatsapp(client, row)
        if not content:
            content, filename, mime, err = recover_email(client, row)
    return {
        "content": content,
        "filename": filename,
        "mime": mime,
        "error": err,
        "live_file_id": live_file_id,
    }


def main() -> None:
    env = load_env(ENV_PATH)
    raw = env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""
    if not raw:
        print("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
        return
    client = BitrixClient(webhook_base(raw))
    admin = client.call("user.admin", {})
    current = client.call("user.current", {})
    user = current.get("result") if isinstance(current.get("result"), dict) else {}
    log(PROGRESS, f"ADMIN_USER {user.get('NAME')} {user.get('LAST_NAME')} admin={admin.get('result')}")
    if admin.get("result") is not True:
        log(PROGRESS, "REFUSING_NON_ADMIN_WEBHOOK")
        return

    with EXISTING_MANIFEST.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    unresolved = [r for r in rows if (r.get("downloaded") or "").lower() != "yes"]
    source_order = {"entity_field": 0, "WhatsApp": 1, "whatsapp": 1, "open_channel": 1, "email": 2}
    unresolved.sort(key=lambda r: source_order.get(r.get("source_type") or "", 9))
    by_source = defaultdict(int)
    for r in unresolved:
        by_source[r.get("source_type") or "unknown"] += 1
    log(PROGRESS, f"UNRESOLVED {len(unresolved)} by_source={dict(by_source)}")

    db = SessionLocal()
    try:
        contacts = load_agreement_contacts(db)
        actor = db.scalars(select(User).limit(1)).first()
        recovered_by = defaultdict(int)
        newly_linked = 0
        skipped_dup = 0
        ownership_conflicts = 0
        remaining_detail = []

        for idx, row in enumerate(unresolved, start=1):
            cid = (row.get("canonical_crm_contact_id") or "").strip()
            if cid not in contacts:
                row["failure_reason"] = "REVIEW_REQUIRED: canonical_contact_not_in_agreement_set"
                ownership_conflicts += 1
                remaining_detail.append(row)
                continue
            source = row.get("source_type") or ""
            result = recover_row(client, row)
            content = result["content"]
            live_file_id = str(result.get("live_file_id") or row.get("bitrix_file_id") or "")
            if live_file_id and live_file_id != str(row.get("bitrix_file_id") or ""):
                other_owners = {
                    (r.get("canonical_crm_contact_id") or "").strip()
                    for r in rows
                    if r is not row
                    and str(r.get("bitrix_file_id") or "") == live_file_id
                    and (r.get("canonical_crm_contact_id") or "").strip()
                }
                other_owners.discard(cid)
                if other_owners:
                    row["downloaded"] = "no"
                    row["failure_reason"] = "REVIEW_REQUIRED: live file id owned by another canonical contact"
                    ownership_conflicts += 1
                    remaining_detail.append(row)
                    log(PROGRESS, f"{idx}/{len(unresolved)} CONFLICT {row.get('person_name')} {source} {live_file_id}")
                    continue
                row["bitrix_file_id"] = live_file_id
            if not content:
                row["downloaded"] = "no"
                row["failure_reason"] = result["error"] or "unresolved"
                remaining_detail.append(row)
                log(PROGRESS, f"{idx}/{len(unresolved)} FAIL {row.get('person_name')} {source} {row.get('bitrix_file_id')} {row['failure_reason'][:120]}")
                continue
            mime = mime_of(result["filename"], result["mime"], content)
            filename = result["filename"] or row.get("original_filename") or f"bitrix-file-{row['bitrix_file_id']}"
            folder = OUT / "by_contact" / cid
            folder.mkdir(parents=True, exist_ok=True)
            dest = unique_dest(folder, safe_filename(filename, str(row["bitrix_file_id"])), str(row["bitrix_file_id"]))
            dest.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            row["original_filename"] = filename
            row["mime_type"] = mime
            row["file_size"] = str(len(content))
            row["downloaded"] = "yes"
            row["local_archive_path"] = str(dest.relative_to(OUT)).replace("\\", "/")
            row["sha256"] = digest
            row["failure_reason"] = ""
            recovered_by[source] += 1
            if actor is None:
                row["crm_imported"] = "no"
                row["failure_reason"] = "no_actor_user"
            else:
                status, doc_id, reason = import_document(db, actor, row, content, row["local_archive_path"])
                row["crm_document_id"] = doc_id or ""
                if status == "yes":
                    row["crm_imported"] = "yes"
                    newly_linked += 1
                elif status == "skipped_duplicate":
                    row["crm_imported"] = "skipped_duplicate"
                    skipped_dup += 1
                else:
                    row["crm_imported"] = "no"
                    row["failure_reason"] = reason
            log(PROGRESS, f"{idx}/{len(unresolved)} OK {row.get('person_name')} {source} {filename} bytes={len(content)}")

        db.commit()

        still = [r for r in rows if (r.get("downloaded") or "").lower() != "yes"]
        downloaded = [r for r in rows if (r.get("downloaded") or "").lower() == "yes"]
        reports = OUT / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        with EXISTING_MANIFEST.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        crm_count = db.execute(
            text(
                """
                select count(distinct d.id)
                from documents d
                join document_links l on l.document_id = d.id
                where d.tags like 'bitrix:%'
                  and l.entity_type in ('crm_contact', 'contact')
                """
            )
        ).scalar()
        remaining_by = [
            {
                "person": r.get("person_name"),
                "source_type": r.get("source_type"),
                "bitrix_file_id": r.get("bitrix_file_id"),
                "source_record_id": r.get("source_record_id"),
                "reason": (r.get("failure_reason") or "")[:300],
            }
            for r in still
        ]
        summary = {
            "unresolved_attempted": len(unresolved),
            "email_newly_recovered": recovered_by.get("email", 0),
            "entity_field_newly_recovered": recovered_by.get("entity_field", 0),
            "whatsapp_newly_recovered": recovered_by.get("WhatsApp", 0) + recovered_by.get("whatsapp", 0),
            "recovered_by_source": dict(recovered_by),
            "total_newly_recovered": sum(recovered_by.values()),
            "still_inaccessible": len(still),
            "newly_linked_crm_documents": newly_linked,
            "duplicate_links_skipped": skipped_dup,
            "ownership_conflicts": ownership_conflicts,
            "final_recovered_out_of_191": len(downloaded),
            "final_crm_document_count": int(crm_count or 0),
            "remaining": remaining_by,
            "bitrix_calls": client.call_count,
            "generated_at": utc_now(),
        }
        (reports / "BITRIX_REMAINING_66_SUMMARY.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
