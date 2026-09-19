"""Read-only rescue of Bitrix files for CRM agreement contacts. No Bitrix/CRM writes."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import text
from investhome_api.db.session import SessionLocal

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS")
ENV_PATH = Path("/tmp/.env")
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
NON_DIGIT = re.compile(r"\D+")
OWNER_TYPE = {"contact": 3, "lead": 1}
ENTITY_TYPE_ID = {"contact": 3, "lead": 1}
IDENTITY_RE = re.compile(
    r"passport|pasaport|passaport|kimlik|n[uü]fus|ehliyet|identity|\bid\b|id[_\-\s]?card|"
    r"national\s*id|driver.?s?\s*licen[cs]e|vesikal[iı]k",
    re.I,
)
CONTRACT_RE = re.compile(
    r"contract|agreement|s[oö]zle[sş]me|reservation|rezervasyon|purchase\s*agreement|"
    r"sat[iı][sş]|imza|signed|daire teklifi",
    re.I,
)
CLOSING_RE = re.compile(
    r"closing|settlement|title\s*deed|tapu|kapan[iı][sş]|closing\s*statement",
    re.I,
)
PAYMENT_RE = re.compile(
    r"dekont|receipt|payment|swift|wire|deposit|pe[sş]inat|kapora|fatura|invoice|"
    r"havale|eft|transfer|mortgage|ipotek",
    re.I,
)
HTML_HEAD = re.compile(br"^\s*<(!doctype|html|head|script|body)\b", re.I)
MANIFEST_FIELDS = [
    "canonical_contact_id",
    "person_name",
    "agreement_id",
    "project_group",
    "bitrix_entity_type",
    "bitrix_entity_id",
    "source_type",
    "source_record_id",
    "bitrix_file_id",
    "original_filename",
    "file_type",
    "document_category",
    "datetime",
    "recovered",
    "local_archive_path",
    "failure_reason",
    "sha256",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def webhook_base(raw: str) -> str:
    value = (raw or "").strip()
    marker = "BURAYA_BITRIX_URL="
    if marker in value:
        value = value.split(marker, 1)[1].strip()
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    path = "/" + "/".join(segs) + "/"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def webhook_token(base: str) -> str:
    segs = [s for s in urllib.parse.urlparse(base).path.split("/") if s]
    return segs[-1] if segs else ""


def redact(text: str, webhook: str) -> str:
    cleaned = (text or "").replace(webhook, "[REDACTED]")
    token = webhook_token(webhook)
    if token:
        cleaned = cleaned.replace(token, "[REDACTED]")
    return WEBHOOK_RE.sub("[REDACTED_URL]", cleaned)


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def digits(value: str | None) -> str:
    return NON_DIGIT.sub("", value or "")


def phone_keys(value: str | None) -> set[str]:
    raw = digits(value)
    keys: set[str] = set()
    if len(raw) >= 10:
        keys.add(raw)
        keys.add(raw[-10:])
        if raw.startswith("90") and len(raw) >= 12:
            keys.add(raw[-10:])
        if raw.startswith("0") and len(raw) >= 11:
            keys.add(raw[-10:])
    return {k for k in keys if len(k) >= 10}


def emails_of(item: dict) -> list[str]:
    values = []
    field = item.get("EMAIL") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        if isinstance(row, dict):
            val = (row.get("VALUE") or "").strip().lower()
        else:
            val = str(row or "").strip().lower()
        if val and "@" in val:
            values.append(val)
    return values


def phones_of(item: dict) -> list[str]:
    values = []
    field = item.get("PHONE") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        if isinstance(row, dict):
            val = row.get("VALUE") or ""
        else:
            val = str(row or "")
        if digits(val):
            values.append(val)
    return values


def person_phone_keys(phones: list[str]) -> set[str]:
    keys: set[str] = set()
    for phone in phones:
        keys |= phone_keys(phone)
    return keys


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or item.get("DESCRIPTION") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or item.get("PROVIDER_TYPE_ID") or "").upper()
    if (
        "whatsapp" in low
        or "open channel" in low
        or "imopenlines" in low
        or "wazzup" in low
        or "whatcrm" in low
        or "IMOPENLINES" in provider
        or "IMOL" in provider
    ):
        return "WhatsApp"
    if "sms" in low or "SMS" in provider:
        return "other"
    type_id = str(item.get("TYPE_ID") or "")
    mapping = {"1": "meeting", "2": "call", "4": "email", "6": "task"}
    if type_id in mapping:
        return mapping[type_id]
    if "CALL" in provider or "VOX" in provider:
        return "call"
    if "EMAIL" in provider or "MAIL" in provider:
        return "email"
    if "MEETING" in provider or "VISIT" in provider:
        return "meeting"
    if "TASK" in provider:
        return "task"
    return "other"


def classify_document(filename: str | None, context: str | None) -> str:
    blob = f"{filename or ''} {context or ''}"
    if IDENTITY_RE.search(blob):
        return "IDENTITY"
    if CLOSING_RE.search(blob):
        return "CLOSING"
    if PAYMENT_RE.search(blob):
        return "PAYMENT"
    if CONTRACT_RE.search(blob):
        return "CONTRACT"
    return "OTHER"


def category_folder(category: str) -> str:
    return {
        "IDENTITY": "identity",
        "CONTRACT": "contracts",
        "CLOSING": "closing",
        "PAYMENT": "payments",
        "OTHER": "other",
    }.get(category, "other")


def file_type_of(filename: str | None, mime: str | None, image_flag: Any) -> str:
    name = (filename or "").lower()
    mime_l = (mime or "").lower()
    if image_flag is True or mime_l.startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".heic", ".tif", ".tiff")):
        return "image"
    if name.endswith(".pdf") or mime_l == "application/pdf":
        return "pdf"
    if name.endswith((".doc", ".docx", ".rtf", ".odt")):
        return "word"
    if name.endswith((".xls", ".xlsx", ".xlsm", ".csv")):
        return "excel"
    if name.endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
        return "video"
    if name.endswith((".mp3", ".wav", ".ogg", ".m4a", ".aac")):
        return "audio"
    if filename:
        if "." in name:
            return name.rsplit(".", 1)[-1]
        return "named"
    return "unknown"


def safe_filename(name: str | None, file_id: str) -> str:
    raw = (name or "").strip() or f"bitrix-file-{file_id}"
    raw = raw.replace("\\", "_").replace("/", "_").replace("\x00", "")
    raw = re.sub(r"[<>:\"|?*]", "_", raw)
    raw = raw.strip(" .")
    if not raw:
        raw = f"bitrix-file-{file_id}"
    if len(raw) > 180:
        stem, dot, ext = raw.rpartition(".")
        if dot and len(ext) <= 8:
            raw = stem[: 180 - len(ext) - 1] + "." + ext
        else:
            raw = raw[:180]
    return raw


def unique_dest(folder: Path, filename: str, file_id: str) -> Path:
    dest = folder / filename
    if not dest.exists():
        return dest
    stem, dot, ext = filename.rpartition(".")
    if not dot:
        stem, ext = filename, ""
        suffix = f"__{file_id}"
        return folder / f"{stem}{suffix}"
    return folder / f"{stem}__{file_id}.{ext}"


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


def node_urls(node: dict) -> list[str]:
    urls = []
    for key in (
        "urlDownload",
        "urlShow",
        "DOWNLOAD_URL",
        "downloadUrl",
        "url",
        "URL",
        "showUrl",
        "urlPreview",
    ):
        val = node.get(key)
        if isinstance(val, str) and val.strip():
            urls.append(val.strip())
    return urls


def node_meta(node: dict) -> dict[str, Any]:
    file_id = node.get("id") or node.get("ID") or node.get("FILE_ID") or node.get("fileId") or node.get("file_id")
    filename = node.get("name") or node.get("NAME") or node.get("fileName") or node.get("FILE_NAME")
    mime = node.get("CONTENT_TYPE") or node.get("contentType") or node.get("MIME_TYPE") or node.get("mime")
    raw_type = node.get("type") or node.get("FILE_TYPE")
    if raw_type and "/" in str(raw_type) and not mime:
        mime = raw_type
    return {
        "file_id": str(file_id) if file_id not in (None, "") else "",
        "filename": filename if isinstance(filename, str) and filename.strip() else None,
        "size": node.get("size") or node.get("SIZE") or node.get("FILE_SIZE"),
        "mime": mime if isinstance(mime, str) and mime.strip() and mime != "file" else None,
        "datetime": node.get("date") or node.get("DATE") or node.get("CREATED"),
        "image_flag": node.get("image"),
        "urls": node_urls(node),
        "raw": node,
    }


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.origin = urllib.parse.urlunparse(urllib.parse.urlparse(self.base)[:2] + ("", "", "", ""))
        self.token = webhook_token(self.base)
        self.min_interval = 0.35
        self._last = 0.0
        self.call_count = 0
        self.retry_count = 0
        self.known_denied: set[str] = set()
        self.permission_failures: list[dict] = []

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def call(self, method: str, payload: dict | None = None) -> dict:
        if method in self.known_denied:
            return {
                "error": "insufficient_scope",
                "error_description": "cached: webhook scope does not allow this method",
                "cached": True,
            }
        url = urllib.parse.urljoin(self.base, method + ".json")
        last_error = None
        for attempt in range(6):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "error_description": redact(raw, self.base)[:500]}
            except Exception as exc:  # noqa: BLE001
                last_error = redact(str(exc), self.base)
                self.retry_count += 1
                time.sleep(min(30, 2 ** attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            desc = redact(str(parsed.get("error_description") or ""), self.base)
            parsed["error_description"] = desc
            low = f"{err} {desc}".lower()
            if err == "insufficient_scope" or "higher privileges" in low:
                self.known_denied.add(method)
                self.permission_failures.append({"method": method, "error": err or "permission", "detail": desc})
                return parsed
            if err in {"ACCESS_DENIED", "denied"} or "access denied" in low:
                self.permission_failures.append({"method": method, "error": err or "permission", "detail": desc})
                return parsed
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                self.retry_count += 1
                time.sleep(min(45, 2 ** (attempt + 1)))
                last_error = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last_error or "unknown"}

    def list_entity(self, method: str, filt: dict) -> list[dict]:
        items: list[dict] = []
        start = 0
        seen = set()
        while start not in seen:
            seen.add(start)
            payload = {f"filter[{key}]": value for key, value in filt.items()}
            payload["start"] = start
            body = self.call(method, payload)
            if body.get("error"):
                return items
            chunk = body.get("result") or []
            if isinstance(chunk, dict):
                chunk = chunk.get("items") or chunk.get("result") or []
            items.extend(chunk)
            nxt = body.get("next")
            if nxt is None or not chunk:
                break
            start = int(nxt)
        return items

    def with_auth(self, url: str) -> str:
        if not url or not self.token:
            return url
        parsed = urllib.parse.urlparse(url)
        q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        if not q.get("auth") or q.get("auth") == [""]:
            q["auth"] = [self.token]
        return urllib.parse.urlunparse(parsed._replace(query=urllib.parse.urlencode(q, doseq=True)))

    def absolute(self, url: str) -> str:
        if not url:
            return url
        if url.startswith("/"):
            return self.origin + url
        return url

    def download(self, url: str, dest: Path) -> tuple[str, str | None]:
        if not url:
            return "failed", "no_url"
        url = self.absolute(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        self._wait()
        self.call_count += 1
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=90) as resp, tmp.open("wb") as handle:
                content_type = (resp.headers.get("Content-Type") or "").lower()
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
            data = tmp.read_bytes()
            if not data:
                tmp.unlink(missing_ok=True)
                return "inaccessible", "empty_body"
            if HTML_HEAD.search(data[:200]) or "text/html" in content_type:
                tmp.unlink(missing_ok=True)
                return "inaccessible", "html_login_or_error_page"
            if data.lstrip()[:1] == b"{" and b'"error"' in data[:300]:
                tmp.unlink(missing_ok=True)
                return "inaccessible", "json_error_body"
            tmp.replace(dest)
            self._last = time.time()
            return "downloaded", None
        except urllib.error.HTTPError as exc:
            self._last = time.time()
            tmp.unlink(missing_ok=True)
            if exc.code in {401, 403}:
                return "inaccessible", f"HTTP {exc.code}"
            if exc.code == 404:
                return "missing", "HTTP 404"
            return "failed", f"HTTP {exc.code}"
        except Exception as exc:  # noqa: BLE001
            tmp.unlink(missing_ok=True)
            return "failed", redact(str(exc), self.base)[:300]


def log(path: Path, message: str) -> None:
    line = f"{utc_now()} {message}"
    print(line, flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_agreement_contacts(db) -> dict[str, dict]:
    rows = db.execute(
        text(
            """
            select a.id::text as agreement_id,
                   coalesce(a.project_group, '') as project_group,
                   a.contact_id::text as cid,
                   c.display_name,
                   c.primary_email,
                   c.primary_phone,
                   c.whatsapp,
                   c.secondary_emails,
                   c.secondary_phones
            from crm_agreements a
            join crm_contacts c on c.id = a.contact_id
            order by c.display_name, a.project_group
            """
        )
    ).mappings().all()
    contacts: dict[str, dict] = {}
    for row in rows:
        rec = contacts.setdefault(
            row["cid"],
            {
                "cid": row["cid"],
                "name": row["display_name"],
                "emails": set(),
                "phones": [],
                "agreements": [],
                "entities": [],
            },
        )
        rec["agreements"].append({"id": row["agreement_id"], "project_group": row["project_group"]})
        if row["primary_email"]:
            rec["emails"].add(row["primary_email"].strip().lower())
        secondary = row["secondary_emails"] or []
        if isinstance(secondary, list):
            rec["emails"].update(str(x).strip().lower() for x in secondary if x)
        for phone in [row["primary_phone"], row["whatsapp"], *(row["secondary_phones"] or [] if isinstance(row["secondary_phones"], list) else [])]:
            if phone:
                rec["phones"].append(str(phone))
    for rec in contacts.values():
        rec["emails"] = sorted(rec["emails"])
        rec["phone_keys"] = person_phone_keys(rec["phones"])
        rec["agreement_id"] = " | ".join(item["id"] for item in rec["agreements"])
        rec["project_group"] = " | ".join(item["project_group"] or "" for item in rec["agreements"])
    return contacts


def add_entity(contact: dict, entity_type: str, entity_id: str, how: str) -> None:
    key = (entity_type, str(entity_id))
    existing = {(item["type"], item["id"]) for item in contact["entities"]}
    if key in existing or not entity_type or not entity_id:
        return
    contact["entities"].append({"type": entity_type, "id": str(entity_id), "how": how})


def index_archive() -> dict[str, Any]:
    files: dict[tuple[str, str], dict] = {}
    by_canon: dict[str, list[tuple[str, str]]] = defaultdict(list)
    by_phone: dict[str, list[tuple[str, str]]] = defaultdict(list)
    by_email: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for folder, etype in ((ARCHIVE / "raw" / "leads", "lead"), (ARCHIVE / "raw" / "contacts", "contact")):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            et = str(data.get("bitrix_entity_type") or etype)
            eid = str(data.get("bitrix_entity_id") or path.stem)
            files[(et, eid)] = data
            canon = str(data.get("canonical_crm_contact_id") or "")
            if canon:
                by_canon[canon].append((et, eid))
            live = data.get("live_entity") if isinstance(data.get("live_entity"), dict) else {}
            for phone in phones_of(live):
                for key in phone_keys(phone):
                    by_phone[key].append((et, eid))
            for email in emails_of(live):
                by_email[email].append((et, eid))
    live_chats: dict[tuple[str, str], dict] = {}
    live_dir = ARCHIVE / "raw" / "chats" / "live"
    if live_dir.exists():
        for path in live_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            et = str(data.get("bitrix_entity_type") or "")
            eid = str(data.get("bitrix_entity_id") or "")
            if et and eid:
                live_chats[(et, eid)] = data
    return {"files": files, "by_canon": by_canon, "by_phone": by_phone, "by_email": by_email, "live_chats": live_chats}


def live_lookup(client: BitrixClient, contact: dict) -> None:
    select = ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "TITLE", "PHONE", "EMAIL", "IM", "HAS_IMOL"]
    seen_phone = set()
    for phone in contact["phones"]:
        variants = [phone]
        d = digits(phone)
        if d:
            variants.extend([d, "+" + d])
            if len(d) >= 10:
                variants.append(d[-10:])
            if d.startswith("90") and len(d) >= 12:
                variants.append("0" + d[-10:])
        for variant in variants:
            if not variant or variant in seen_phone:
                continue
            seen_phone.add(variant)
            for method, entity_type in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
                body = client.call(method, {"filter[PHONE]": variant, "select[]": select, "start": 0})
                for item in body.get("result") or []:
                    rec_keys: set[str] = set()
                    for value in phones_of(item):
                        rec_keys |= phone_keys(value)
                    if contact["phone_keys"] and rec_keys and not (contact["phone_keys"] & rec_keys):
                        continue
                    add_entity(contact, entity_type, str(item.get("ID")), "live_phone")
            if contact["entities"]:
                return
    for email in contact["emails"]:
        for method, entity_type in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            body = client.call(method, {"filter[EMAIL]": email, "select[]": select, "start": 0})
            for item in body.get("result") or []:
                rec_emails = set(emails_of(item))
                if email not in rec_emails:
                    continue
                add_entity(contact, entity_type, str(item.get("ID")), "live_email")
    for email in contact["emails"]:
        for entity_type in ("LEAD", "CONTACT"):
            body = client.call(
                "crm.duplicate.findbycomm",
                {"entity_type": entity_type, "type": "EMAIL", "values": [email]},
            )
            result = body.get("result") or {}
            collect_duplicate_ids(contact, result, "live_duplicate_email")
    for phone in list(contact["phone_keys"])[:4]:
        for entity_type in ("LEAD", "CONTACT"):
            body = client.call(
                "crm.duplicate.findbycomm",
                {"entity_type": entity_type, "type": "PHONE", "values": [phone]},
            )
            collect_duplicate_ids(contact, body.get("result") or {}, "live_duplicate_phone")


def collect_duplicate_ids(contact: dict, result: Any, how: str) -> None:
    mapping = {"CONTACT": "contact", "LEAD": "lead", "COMPANY": None}
    if isinstance(result, dict):
        for key, ids in result.items():
            etype = mapping.get(str(key).upper())
            if not etype:
                continue
            if not isinstance(ids, list):
                ids = [ids]
            for eid in ids:
                add_entity(contact, etype, str(eid), how)
    elif isinstance(result, list):
        for eid in result:
            add_entity(contact, "lead", str(eid), how)


def file_fields(client: BitrixClient) -> dict[str, set[str]]:
    out = {"lead": set(), "contact": set()}
    for entity, method in (("lead", "crm.lead.fields"), ("contact", "crm.contact.fields")):
        body = client.call(method, {})
        fields = body.get("result") or {}
        if not isinstance(fields, dict):
            continue
        for name, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            ftype = str(spec.get("type") or "").lower()
            if ftype == "file" or "file" in str(name).lower() or name in {"PHOTO"}:
                out[entity].add(name)
        out[entity].add("PHOTO")
    return out


def add_ref(refs: list[dict], seen: dict[tuple, dict], row: dict) -> None:
    key = (
        row.get("bitrix_entity_type"),
        row.get("bitrix_entity_id"),
        row.get("source_type"),
        row.get("source_record_id"),
        row.get("bitrix_file_id"),
        row.get("original_filename"),
    )
    existing = seen.get(key)
    if existing:
        urls = list(dict.fromkeys([*(existing.get("urls") or []), *(row.get("urls") or [])]))
        existing["urls"] = urls
        if not existing.get("original_filename") and row.get("original_filename"):
            existing["original_filename"] = row["original_filename"]
        if not existing.get("datetime") and row.get("datetime"):
            existing["datetime"] = row["datetime"]
        if (existing.get("file_type") in {None, "", "unknown"}) and row.get("file_type"):
            existing["file_type"] = row["file_type"]
        return
    seen[key] = row
    refs.append(row)


def refs_from_nodes(
    nodes: list[dict],
    contact: dict,
    entity_type: str,
    entity_id: str,
    source_type: str,
    source_id: str,
    context: str,
    when: Any,
) -> list[dict]:
    rows = []
    for node in nodes:
        meta = node_meta(node)
        if not meta["file_id"] and not meta["filename"] and not meta["urls"]:
            continue
        filename = meta["filename"]
        category = classify_document(filename, context)
        rows.append(
            {
                "canonical_contact_id": contact["cid"],
                "person_name": contact["name"],
                "agreement_id": contact["agreement_id"],
                "project_group": contact["project_group"],
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
                "source_type": source_type,
                "source_record_id": str(source_id or ""),
                "bitrix_file_id": meta["file_id"],
                "original_filename": filename,
                "file_type": file_type_of(filename, meta["mime"], meta["image_flag"]),
                "document_category": category,
                "datetime": meta["datetime"] or when,
                "urls": meta["urls"],
                "context": (context or "")[:500],
            }
        )
    return rows


def collect_from_archive(contact: dict, data: dict, live_chat: dict | None, seen: dict[tuple, dict]) -> list[dict]:
    refs: list[dict] = []
    entity_type = str(data.get("bitrix_entity_type") or "")
    entity_id = str(data.get("bitrix_entity_id") or "")
    for comment in data.get("timeline_comments") or []:
        cid = str(comment.get("ID") or "")
        text = str(comment.get("COMMENT") or comment.get("TEXT") or "")
        created = comment.get("CREATED") or comment.get("DATE_CREATE")
        for row in refs_from_nodes(iter_file_nodes(comment.get("FILES")), contact, entity_type, entity_id, "comment", cid, text, created):
            add_ref(refs, seen, row)
    for activity in data.get("crm_activities") or []:
        source = classify_activity(activity)
        aid = str(activity.get("ID") or "")
        context = " ".join(str(x) for x in [activity.get("SUBJECT"), activity.get("DESCRIPTION")] if x)
        when = activity.get("CREATED") or activity.get("START_TIME") or activity.get("LAST_UPDATED")
        nodes = iter_file_nodes(activity.get("FILES"))
        for extra in (activity.get("STORAGE_ELEMENT_IDS"), activity.get("WEBDAV_ELEMENTS"), activity.get("UF_CRM_FILES")):
            nodes.extend(iter_file_nodes(extra))
        for row in refs_from_nodes(nodes, contact, entity_type, entity_id, source, aid, context, when):
            add_ref(refs, seen, row)
    live = data.get("live_entity") if isinstance(data.get("live_entity"), dict) else {}
    for key, value in live.items():
        if not value:
            continue
        upper = str(key).upper()
        if upper == "PHOTO" or "FILE" in upper or upper.startswith("UF"):
            nodes = iter_file_nodes(value)
            if not nodes and str(value).isdigit():
                nodes = [{"id": value}]
            for row in refs_from_nodes(nodes, contact, entity_type, entity_id, "entity_field", key, key, live.get("DATE_MODIFY")):
                add_ref(refs, seen, row)
    for item in data.get("attachment_references") or []:
        if isinstance(item, dict):
            for row in refs_from_nodes([item], contact, entity_type, entity_id, str(item.get("source") or "attachment_reference"), str(item.get("source_record_id") or ""), str(item.get("filename") or ""), item.get("datetime")):
                add_ref(refs, seen, row)
    if live_chat:
        for chat in live_chat.get("chats") or []:
            chat_id = str(chat.get("chat_id") or "")
            files_map = chat.get("files") or {}
            if isinstance(files_map, dict):
                for fid, node in files_map.items():
                    payload = node if isinstance(node, dict) else {"id": fid}
                    if "id" not in payload and "ID" not in payload:
                        payload = {**payload, "id": fid}
                    for row in refs_from_nodes([payload], contact, entity_type, entity_id, "WhatsApp", chat_id, "", None):
                        add_ref(refs, seen, row)
            for message in chat.get("messages") or []:
                raw = message.get("raw") if isinstance(message.get("raw"), dict) else {}
                params = raw.get("params") or raw.get("PARAMS") or {}
                text = str(message.get("message_text") or message.get("text") or raw.get("text") or "")
                when = message.get("date_time") or raw.get("date")
                mid = str(message.get("message_id") or raw.get("id") or "")
                file_ids = []
                if isinstance(params, dict):
                    file_ids = params.get("FILE_ID") or []
                    if not isinstance(file_ids, list):
                        file_ids = [file_ids] if file_ids else []
                    extra_nodes = iter_file_nodes(params.get("FILES") or params.get("FILE"))
                    for row in refs_from_nodes(extra_nodes, contact, entity_type, entity_id, "WhatsApp", mid, text, when):
                        add_ref(refs, seen, row)
                for fid in file_ids:
                    if not str(fid) or str(fid) == "None":
                        continue
                    node = files_map.get(str(fid)) if isinstance(files_map, dict) else None
                    payload = node if isinstance(node, dict) else {"id": fid}
                    if isinstance(payload, dict) and "id" not in payload and "ID" not in payload:
                        payload = {**payload, "id": fid}
                    for row in refs_from_nodes([payload], contact, entity_type, entity_id, "WhatsApp", mid, text, when):
                        add_ref(refs, seen, row)
    return refs


def collect_live_entity_files(contact: dict, entity_type: str, entity_id: str, record: dict, uf_names: set[str], seen: dict[tuple, dict]) -> list[dict]:
    refs: list[dict] = []
    for key in sorted(uf_names | {k for k in record if str(k).upper() in {"PHOTO"} or "FILE" in str(k).upper()}):
        value = record.get(key)
        if not value:
            continue
        nodes = iter_file_nodes(value)
        if not nodes and str(value).isdigit():
            nodes = [{"id": value}]
        for row in refs_from_nodes(nodes, contact, entity_type, entity_id, "entity_field", key, key, record.get("DATE_MODIFY")):
            add_ref(refs, seen, row)
    return refs


def collect_live_comments_activities(client: BitrixClient, contact: dict, entity_type: str, entity_id: str, seen: dict[tuple, dict]) -> list[dict]:
    refs: list[dict] = []
    comments = client.list_entity("crm.timeline.comment.list", {"ENTITY_TYPE": entity_type, "ENTITY_ID": entity_id})
    for comment in comments:
        cid = str(comment.get("ID") or "")
        text = str(comment.get("COMMENT") or comment.get("TEXT") or "")
        created = comment.get("CREATED") or comment.get("DATE_CREATE")
        for row in refs_from_nodes(iter_file_nodes(comment.get("FILES")), contact, entity_type, entity_id, "comment", cid, text, created):
            add_ref(refs, seen, row)
    activities = client.list_entity(
        "crm.activity.list",
        {"OWNER_TYPE_ID": OWNER_TYPE.get(entity_type, 1), "OWNER_ID": entity_id},
    )
    for activity in activities:
        source = classify_activity(activity)
        aid = str(activity.get("ID") or "")
        context = " ".join(str(x) for x in [activity.get("SUBJECT"), activity.get("DESCRIPTION")] if x)
        when = activity.get("CREATED") or activity.get("START_TIME")
        nodes = iter_file_nodes(activity.get("FILES"))
        for extra in (activity.get("STORAGE_ELEMENT_IDS"), activity.get("WEBDAV_ELEMENTS")):
            nodes.extend(iter_file_nodes(extra))
        for row in refs_from_nodes(nodes, contact, entity_type, entity_id, source, aid, context, when):
            add_ref(refs, seen, row)
    return refs


def recover_file(client: BitrixClient, ref: dict, dest: Path) -> tuple[str, str | None]:
    reasons: list[str] = []
    tried_urls: set[str] = set()
    urls = list(ref.get("urls") or [])
    file_id = str(ref.get("bitrix_file_id") or "")
    source = ref.get("source_type")
    source_id = ref.get("source_record_id")

    def try_urls(candidates: list[str]) -> tuple[str, str | None] | None:
        for url in candidates:
            if not url or url in tried_urls:
                continue
            tried_urls.add(url)
            status, reason = client.download(url, dest)
            if status == "downloaded":
                return status, None
            reasons.append(reason or status)
            authed = client.with_auth(url)
            if authed != url and authed not in tried_urls:
                tried_urls.add(authed)
                status, reason = client.download(authed, dest)
                if status == "downloaded":
                    return status, None
                reasons.append(reason or status)
        return None

    if file_id:
        disk = client.call("disk.file.get", {"id": file_id})
        result = disk.get("result") if not disk.get("error") else None
        if isinstance(result, dict):
            if result.get("NAME") and not ref.get("original_filename"):
                ref["original_filename"] = result.get("NAME")
            hit = try_urls([result.get("DOWNLOAD_URL") or result.get("downloadUrl") or ""])
            if hit:
                return hit
        else:
            reasons.append(redact(str(disk.get("error") or disk.get("error_description") or "disk.file.get"), client.base))
        attached = client.call("disk.attachedObject.get", {"id": file_id})
        result = attached.get("result") if not attached.get("error") else None
        if isinstance(result, dict):
            inner = result.get("FILE") if isinstance(result.get("FILE"), dict) else {}
            hit = try_urls(
                [
                    result.get("DOWNLOAD_URL") or result.get("downloadUrl") or "",
                    inner.get("DOWNLOAD_URL") or inner.get("downloadUrl") or "",
                ]
            )
            if hit:
                return hit
        else:
            reasons.append(redact(str(attached.get("error") or attached.get("error_description") or "disk.attachedObject.get"), client.base))

    hit = try_urls(urls)
    if hit:
        return hit

    if source in {"email", "task", "meeting", "call", "other"} and source_id and file_id:
        show = (
            f"{client.origin}/bitrix/tools/crm_show_file.php"
            f"?fileId={file_id}&ownerTypeId=6&ownerId={source_id}"
        )
        hit = try_urls([show])
        if hit:
            return hit
        body = client.call("crm.activity.get", {"id": source_id})
        result = body.get("result") or {}
        if isinstance(result, dict):
            nodes = iter_file_nodes(result.get("FILES"))
            nodes.extend(iter_file_nodes(result.get("STORAGE_ELEMENT_IDS")))
            for node in nodes:
                meta = node_meta(node)
                if file_id and meta["file_id"] and meta["file_id"] != file_id:
                    continue
                hit = try_urls(meta["urls"])
                if hit:
                    return hit

    uniq = []
    for reason in reasons:
        if reason and reason not in uniq:
            uniq.append(reason)
    return "inaccessible", "; ".join(uniq[:8]) or "no_download_method"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    progress = OUT / "reports" / "progress.log"
    env = load_env(ENV_PATH)
    raw_url = env.get("BITRIX_WEBHOOK_URL") or ""
    if not raw_url:
        print("MISSING_BITRIX_WEBHOOK_URL")
        return
    client = BitrixClient(webhook_base(raw_url))
    db = SessionLocal()
    try:
        contacts = load_agreement_contacts(db)
    finally:
        db.close()
    log(progress, f"AGREEMENT_CONTACTS {len(contacts)}")
    index = index_archive()
    log(progress, f"ARCHIVE_INDEX entities={len(index['files'])} live_chats={len(index['live_chats'])}")

    for contact in contacts.values():
        for et, eid in index["by_canon"].get(contact["cid"], []):
            add_entity(contact, et, eid, "canonical")
        for key in contact["phone_keys"]:
            for et, eid in index["by_phone"].get(key, []):
                add_entity(contact, et, eid, "archive_phone")
        for email in contact["emails"]:
            for et, eid in index["by_email"].get(email, []):
                add_entity(contact, et, eid, "archive_email")
        if not contact["entities"]:
            live_lookup(client, contact)
        log(
            progress,
            f"MATCH {contact['name']} entities={len(contact['entities'])} how={[item['how'] for item in contact['entities']]}",
        )

    uf = file_fields(client)
    log(progress, f"UF_FILE_FIELDS lead={len(uf['lead'])} contact={len(uf['contact'])}")
    scope = client.call("scope", {})
    log(progress, f"SCOPE {scope.get('result')}")

    all_refs: list[dict] = []
    seen: dict[tuple, dict] = {}
    for contact in contacts.values():
        if not contact["entities"]:
            log(progress, f"NO_ENTITY {contact['name']}")
            continue
        for ent in contact["entities"]:
            et, eid = ent["type"], ent["id"]
            data = index["files"].get((et, eid))
            live_chat = index["live_chats"].get((et, eid))
            if data:
                all_refs.extend(collect_from_archive(contact, data, live_chat, seen))
            getter = "crm.contact.get" if et == "contact" else "crm.lead.get"
            body = client.call(getter, {"id": eid})
            record = body.get("result") if not body.get("error") else None
            if isinstance(record, dict):
                all_refs.extend(collect_live_entity_files(contact, et, eid, record, uf.get(et) or set(), seen))
            all_refs.extend(collect_live_comments_activities(client, contact, et, eid, seen))

    log(progress, f"FILE_REFS {len(all_refs)}")

    downloaded = 0
    inaccessible = 0
    rows: list[dict] = []
    for idx, ref in enumerate(all_refs, start=1):
        category = ref["document_category"]
        folder = (
            OUT
            / "by_contact"
            / ref["canonical_contact_id"]
            / category_folder(category)
        )
        filename = safe_filename(ref.get("original_filename"), ref.get("bitrix_file_id") or f"idx{idx}")
        dest = unique_dest(folder, filename, ref.get("bitrix_file_id") or str(idx))
        status, reason = recover_file(client, ref, dest)
        recovered = "yes" if status == "downloaded" and dest.exists() and dest.stat().st_size > 0 else "no"
        digest = ""
        local = ""
        if recovered == "yes":
            downloaded += 1
            digest = sha256_file(dest)
            local = str(dest.relative_to(OUT)).replace("\\", "/")
            if ref.get("original_filename") and dest.name != safe_filename(ref.get("original_filename"), ref.get("bitrix_file_id") or ""):
                # keep dest; filename already collision-suffixed
                pass
        else:
            inaccessible += 1
            if dest.exists():
                dest.unlink()
        rows.append(
            {
                "canonical_contact_id": ref["canonical_contact_id"],
                "person_name": ref["person_name"],
                "agreement_id": ref["agreement_id"],
                "project_group": ref["project_group"],
                "bitrix_entity_type": ref["bitrix_entity_type"],
                "bitrix_entity_id": ref["bitrix_entity_id"],
                "source_type": ref["source_type"],
                "source_record_id": ref["source_record_id"],
                "bitrix_file_id": ref["bitrix_file_id"],
                "original_filename": ref.get("original_filename") or "",
                "file_type": file_type_of(ref.get("original_filename"), None, None) if ref.get("original_filename") else ref.get("file_type") or "",
                "document_category": category,
                "datetime": ref.get("datetime") or "",
                "recovered": recovered,
                "local_archive_path": local,
                "failure_reason": "" if recovered == "yes" else (reason or status),
                "sha256": digest,
            }
        )
        if idx % 10 == 0 or recovered == "yes":
            log(progress, f"FILE {idx}/{len(all_refs)} recovered={recovered} cat={category} src={ref['source_type']}")

    reports = OUT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    manifest_path = reports / "BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    by_contact_refs = defaultdict(int)
    by_contact_down = defaultdict(int)
    cats = defaultdict(int)
    identity = contract = closing = payment = 0
    for row in rows:
        by_contact_refs[row["canonical_contact_id"]] += 1
        if row["recovered"] == "yes":
            by_contact_down[row["canonical_contact_id"]] += 1
        cats[row["document_category"]] += 1
        if row["document_category"] == "IDENTITY":
            identity += 1
        elif row["document_category"] == "CONTRACT":
            contract += 1
        elif row["document_category"] == "CLOSING":
            closing += 1
        elif row["document_category"] == "PAYMENT":
            payment += 1

    zero = [cid for cid in contacts if by_contact_refs[cid] == 0]
    with_refs = [cid for cid in contacts if by_contact_refs[cid] > 0]
    inaccessible_contacts = [
        cid for cid in contacts if by_contact_refs[cid] > 0 and by_contact_down[cid] < by_contact_refs[cid]
    ]
    denied = sorted({item["method"] for item in client.permission_failures} | client.known_denied)
    summary = {
        "agreement_contacts_checked": len(contacts),
        "contacts_with_file_references": len(with_refs),
        "total_file_references": len(rows),
        "files_downloaded": downloaded,
        "files_inaccessible": inaccessible,
        "likely_passport_id_documents": identity,
        "contracts": contract,
        "closing_documents": closing,
        "payment_swift_dekont_documents": payment,
        "contacts_with_zero_documents": len(zero),
        "contacts_with_inaccessible_files": len(inaccessible_contacts),
        "contacts_with_zero_names": [contacts[cid]["name"] for cid in sorted(zero, key=lambda x: contacts[x]["name"])],
        "archive_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/",
        "manifest_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS/reports/BITRIX_AGREEMENT_DOCUMENT_MANIFEST.csv",
        "remaining_permission_problem": (
            "Inbound webhook is CRM-scoped; disk.file.get / disk.attachedObject.get / IM Open Channel file APIs return ACCESS_DENIED or insufficient_scope. "
            "Comment urlDownload and crm_show_file.php URLs require a logged-in session or disk scope, so most binaries remain unrecovered."
            if denied or inaccessible
            else "none"
        ),
        "denied_methods": denied,
        "bitrix_calls": client.call_count,
        "category_counts": dict(cats),
        "entities_matched": sum(1 for rec in contacts.values() if rec["entities"]),
        "entities_unmatched": sum(1 for rec in contacts.values() if not rec["entities"]),
        "unmatched_names": [rec["name"] for rec in contacts.values() if not rec["entities"]],
        "generated_at": utc_now(),
    }
    atomic_write_json(reports / "BITRIX_AGREEMENT_DOCUMENT_SUMMARY.json", summary)
    log(progress, json.dumps({k: summary[k] for k in list(summary)[:12]}, ensure_ascii=False))
    print("SUMMARY", json.dumps(summary, ensure_ascii=False, indent=2, default=str), flush=True)


if __name__ == "__main__":
    main()
