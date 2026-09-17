"""Read-only Bitrix final history archive. Never writes to CRM or Bitrix. Never prints webhook URLs."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_contact import CrmContact

ARCHIVE_REL = Path("2026-09-final") / "BITRIX_FINAL_HISTORY_ARCHIVE"
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
NON_DIGIT = re.compile(r"\D+")
WA_HEADER_RE = re.compile(r"chat with whatsapp|open channel|\[whatcrm\]|imopenlines", re.I)
WA_SEGMENT_RE = re.compile(
    r"\[B\](.*?)\[/B\]\s*(?:(\d{1,2}\.\d{1,2}\.\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?)\s*)?(.*?)(?=\[B\]|$)",
    re.I | re.S,
)
OWNER_TYPE = {"contact": 3, "lead": 1}
FORCE_NAMES = ("berk cimen", "kaan kalyon")
INDEX_SELECT = [
    "ID",
    "NAME",
    "LAST_NAME",
    "SECOND_NAME",
    "TITLE",
    "PHONE",
    "EMAIL",
    "IM",
    "ASSIGNED_BY_ID",
    "HAS_IMOL",
    "HAS_PHONE",
    "HAS_EMAIL",
    "STATUS_ID",
    "DATE_MODIFY",
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
    if value.startswith("BITRIX_WEBHOOK_URL="):
        value = value.split("=", 1)[1].strip()
    value = value.strip().strip('"').strip("'")
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    path = "/" + "/".join(segs) + "/"
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def redact(text: str, webhook: str) -> str:
    cleaned = (text or "").replace(webhook, "[REDACTED]")
    return WEBHOOK_RE.sub("[REDACTED_URL]", cleaned)


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


def display_of(item: dict) -> str:
    parts = [item.get("NAME"), item.get("SECOND_NAME"), item.get("LAST_NAME"), item.get("TITLE")]
    return " ".join(str(p) for p in parts if p).strip()


def fold_name(value: str | None) -> str:
    table = str.maketrans({"ı": "i", "İ": "i", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c", "â": "a"})
    return re.sub(r"\s+", " ", (value or "").translate(table).casefold()).strip()


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.retry_count = 0
        self.call_count = 0
        self.failures: list[dict] = []
        self.permission_failures: list[dict] = []
        self.known_denied: set[str] = set()
        self.min_interval = 0.35
        self._last = 0.0

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)

    def call(self, method: str, payload: dict | None = None, *, allow_denied: bool = False) -> dict:
        method_name = method[:-5] if method.endswith(".json") else method
        if method_name in self.known_denied and not allow_denied:
            return {
                "error": "insufficient_scope",
                "error_description": "cached: webhook scope does not allow this method",
                "cached": True,
            }
        url = urllib.parse.urljoin(self.base, method_name + ".json")
        body = payload or {}
        last_error = None
        for attempt in range(6):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(body, doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "error_description": redact(raw, self.base)[:1000]}
            except Exception as exc:  # noqa: BLE001
                last_error = redact(str(exc), self.base)
                self.retry_count += 1
                time.sleep(min(30, 2 ** attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            desc = redact(str(parsed.get("error_description") or ""), self.base)
            parsed["error_description"] = desc
            if err in {"insufficient_scope", "ACCESS_DENIED", "denied"} or "higher privileges" in desc.lower():
                self.known_denied.add(method_name)
                self.permission_failures.append({"method": method_name, "error": err or "permission", "detail": desc})
                return parsed
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"} or "operating" in desc.lower():
                self.retry_count += 1
                time.sleep(min(45, 2 ** (attempt + 1)))
                last_error = err or desc
                continue
            if err:
                self.failures.append({"method": method_name, "error": err, "detail": desc})
                return parsed
            return parsed
        return {"error": "retry_exhausted", "error_description": last_error or "unknown"}

    def list_all(self, method: str, payload: dict | None = None, progress=None) -> list[dict]:
        items: list[dict] = []
        start = 0
        seen_starts = set()
        params = dict(payload or {})
        while True:
            if start in seen_starts:
                break
            seen_starts.add(start)
            params["start"] = start
            body = self.call(method, params)
            if body.get("error"):
                break
            chunk = body.get("result") or []
            if isinstance(chunk, dict):
                chunk = chunk.get("items") or chunk.get("result") or []
            items.extend(chunk)
            if progress and len(seen_starts) % 20 == 0:
                progress(len(items), body.get("total"))
            nxt = body.get("next")
            if nxt is None or not chunk:
                break
            nxt_i = int(nxt)
            if nxt_i <= start:
                break
            start = nxt_i
        return items

    def batch(self, commands: dict[str, tuple[str, dict]]) -> dict:
        payload: dict[str, Any] = {"halt": 0}
        for key, (method, params) in commands.items():
            payload[f"cmd[{key}]"] = f"{method}?{urllib.parse.urlencode(params, doseq=True)}"
        body = self.call("batch", payload)
        result = body.get("result") or {}
        if isinstance(result, dict) and "result" in result:
            return result
        return {"result": result, "result_error": body.get("result_error") or {}, "result_next": body.get("result_next") or {}, "result_total": body.get("result_total") or {}}

    def list_entity(self, method: str, filt: dict) -> tuple[list[dict], list[str]]:
        items: list[dict] = []
        methods_used = [method]
        start = 0
        while True:
            payload = {f"filter[{key}]": value for key, value in filt.items()}
            payload["start"] = start
            body = self.call(method, payload)
            if body.get("error"):
                return items, methods_used
            chunk = body.get("result") or []
            items.extend(chunk)
            nxt = body.get("next")
            if nxt is None or not chunk:
                break
            start = int(nxt)
        return items, methods_used

    def list_continue(self, method: str, filt: dict, start: int) -> list[dict]:
        items: list[dict] = []
        current: int | None = int(start)
        seen = set()
        while current is not None:
            if current in seen:
                break
            seen.add(current)
            payload = {f"filter[{key}]": value for key, value in filt.items()}
            payload["start"] = current
            body = self.call(method, payload)
            if body.get("error"):
                break
            chunk = body.get("result") or []
            items.extend(chunk)
            nxt = body.get("next")
            current = int(nxt) if nxt is not None and chunk else None
        return items


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
        return "whatsapp"
    if "sms" in low or "SMS" in provider:
        return "sms"
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


def extract_attachments(obj: Any) -> list[dict]:
    found: list[dict] = []

    def walk(node: Any, trail: str) -> None:
        if isinstance(node, dict):
            keys = {k.upper() for k in node.keys()}
            if {"ID", "NAME"} <= keys or "FILE_ID" in node or "DOWNLOAD_URL" in {k.upper() for k in node.keys()}:
                file_id = node.get("id") or node.get("ID") or node.get("FILE_ID") or node.get("fileId")
                name = node.get("name") or node.get("NAME") or node.get("fileName") or node.get("FILE_NAME")
                if file_id or name or node.get("DOWNLOAD_URL") or node.get("url"):
                    found.append(
                        {
                            "file_id": file_id,
                            "filename": name,
                            "size": node.get("size") or node.get("SIZE") or node.get("FILE_SIZE"),
                            "type": node.get("type") or node.get("CONTENT_TYPE") or node.get("FILE_TYPE"),
                            "url": node.get("DOWNLOAD_URL") or node.get("url") or node.get("URL"),
                            "source": trail,
                            "raw": node,
                        }
                    )
            for key, val in node.items():
                upper = str(key).upper()
                if upper in {"FILES", "STORAGE_ELEMENT_IDS", "WEBDAV_ELEMENTS", "UF_CRM_FILES"}:
                    walk(val, f"{trail}.{key}")
                elif isinstance(val, (dict, list)) and upper not in {"SETTINGS", "PROVIDER_PARAMS"}:
                    walk(val, f"{trail}.{key}")
        elif isinstance(node, list):
            for idx, val in enumerate(node):
                if isinstance(val, (dict, list)):
                    walk(val, f"{trail}[{idx}]")
                elif str(val).isdigit():
                    found.append({"file_id": val, "filename": None, "size": None, "type": None, "url": None, "source": trail, "raw": val})

    walk(obj, "root")
    uniq = []
    seen = set()
    for item in found:
        key = (str(item.get("file_id")), str(item.get("filename")), str(item.get("source")))
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    return uniq


def parse_whatsapp_comment(comment: str) -> list[dict]:
    text = comment or ""
    if not WA_HEADER_RE.search(text) and "[B]" not in text:
        return []
    messages = []
    for match in WA_SEGMENT_RE.finditer(text):
        header, stamp, body = match.group(1), match.group(2), match.group(3)
        body = re.sub(r"\[/?[^\]]+\]", "", body or "").strip()
        header_clean = re.sub(r"\[/?[^\]]+\]", "", header or "").strip()
        if not header_clean and not body:
            continue
        direction = ""
        sender = header_clean
        if "->" in header_clean:
            left, right = header_clean.split("->", 1)
            if re.search(r"\d{7,}", left):
                direction = "inbound"
                sender = left.strip()
            elif re.search(r"\d{7,}", right):
                direction = "outbound"
                sender = left.strip()
            else:
                sender = left.strip()
        messages.append(
            {
                "sender_name": sender,
                "date_time": stamp,
                "message_text": body,
                "direction": direction,
                "source": "timeline_comment_parse",
            }
        )
    if messages and not any("whatsapp" in (comment or "").casefold() for _ in [0]):
        if not WA_HEADER_RE.search(comment or ""):
            return []
    return messages if WA_HEADER_RE.search(comment or "") else []


def openchannel_refs(activity: dict, lead_or_contact: dict | None = None) -> dict:
    params = activity.get("PROVIDER_PARAMS") or {}
    if not isinstance(params, dict):
        params = {}
    user_code = params.get("USER_CODE") or params.get("user_code")
    session_id = activity.get("ASSOCIATED_ENTITY_ID") or (str(activity.get("ORIGIN_ID") or "").replace("IMOL_", "") or None)
    chat_id = None
    if isinstance(user_code, str) and "|" in user_code:
        parts = user_code.split("|")
        if parts:
            chat_id = parts[-1]
    im_values = []
    if lead_or_contact:
        for row in lead_or_contact.get("IM") or []:
            if isinstance(row, dict):
                im_values.append(row.get("VALUE"))
    return {
        "session_id": str(session_id) if session_id else None,
        "origin_id": activity.get("ORIGIN_ID"),
        "user_code": user_code,
        "chat_id": chat_id,
        "dialog_id": f"chat{chat_id}" if chat_id else None,
        "provider": activity.get("RESULT_SOURCE_ID") or activity.get("PROVIDER_ID"),
        "connector_id": activity.get("PROVIDER_TYPE_ID"),
        "im_values": im_values,
        "activity_id": activity.get("ID"),
    }


def load_people(db: Session, smoke: bool) -> list[dict]:
    people = []
    seen = set()
    for contact in db.query(CrmContact).all():
        meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
        bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
        roles = [str(x) for x in (bitrix.get("source_roles") or [])]
        role_set = set(roles)
        external_ids = [str(x) for x in (bitrix.get("external_ids") or [])]
        source_files = [str(x) for x in (bitrix.get("source_files") or [])]
        ids = []
        for ext in external_ids:
            part = ext.rsplit(":", 1)[-1].strip()
            if part.isdigit():
                ids.append(part)
        folded = fold_name(contact.display_name)
        is_force = any(name in folded for name in FORCE_NAMES) and "kalyoncu" not in folded and "tursucu" not in folded
        is_active_or_junk = bool(role_set & {"active_customers", "junk"})
        is_agent = "agents" in role_set and bool(ids)
        if not (is_active_or_junk or is_agent or is_force):
            continue
        group = "active" if "active_customers" in role_set else "junk" if "junk" in role_set else "agent" if "agents" in role_set else "validation"
        if is_force and group == "validation":
            group = "validation"
        rec = {
            "canonical_crm_contact_id": str(contact.id),
            "person_name": contact.display_name,
            "status": getattr(contact.status, "value", str(contact.status)),
            "primary_phone": contact.primary_phone,
            "primary_email": (contact.primary_email or "").strip().lower() or None,
            "source_roles": roles,
            "source_files": source_files,
            "external_ids": external_ids,
            "source_bitrix_ids": ids,
            "group": group,
            "force_include": is_force,
        }
        if rec["canonical_crm_contact_id"] in seen:
            continue
        seen.add(rec["canonical_crm_contact_id"])
        people.append(rec)
    if smoke:
        wanted = []
        for rec in people:
            folded = fold_name(rec["person_name"])
            if rec["force_include"] or rec["group"] == "validation":
                wanted.append(rec)
            elif rec["group"] == "active" and len([x for x in wanted if x["group"] == "active"]) < 1:
                wanted.append(rec)
            elif rec["group"] == "junk" and len([x for x in wanted if x["group"] == "junk"]) < 1:
                wanted.append(rec)
        people = wanted
    people.sort(key=lambda rec: (0 if rec["force_include"] else 1, rec["group"], rec["person_name"] or ""))
    return people


def index_entities(rows: list[dict], entity_type: str) -> dict:
    by_id = {}
    by_phone: dict[str, set[str]] = {}
    by_email: dict[str, set[str]] = {}
    for item in rows:
        eid = str(item.get("ID") or "")
        if not eid:
            continue
        by_id[eid] = item
        for phone in phones_of(item):
            for key in phone_keys(phone):
                by_phone.setdefault(key, set()).add(eid)
        for email in emails_of(item):
            by_email.setdefault(email, set()).add(eid)
    return {"entity_type": entity_type, "by_id": by_id, "by_phone": {k: sorted(v) for k, v in by_phone.items()}, "by_email": {k: sorted(v) for k, v in by_email.items()}}


def records_compatible(person: dict, record: dict) -> bool:
    person_phones = phone_keys(person.get("primary_phone"))
    rec_phones: set[str] = set()
    for phone in phones_of(record):
        rec_phones |= phone_keys(phone)
    if person_phones and rec_phones:
        return bool(person_phones & rec_phones)
    person_email = (person.get("primary_email") or "").strip().lower()
    rec_emails = set(emails_of(record))
    if person_email and person_email in rec_emails:
        return True
    person_fold = fold_name(person.get("person_name"))
    rec_fold = fold_name(display_of(record))
    if person_fold and rec_fold and (person_fold in rec_fold or rec_fold in person_fold):
        return True
    if not person_phones and not person_email:
        return True
    if not rec_phones and not rec_emails:
        return True
    return False


def live_lookup(client: BitrixClient, person: dict) -> list[dict]:
    matches = []
    phones = []
    raw = person.get("primary_phone") or ""
    if raw:
        phones.append(raw)
        d = digits(raw)
        if d:
            phones.append(d)
            phones.append("+" + d)
            if len(d) >= 10:
                phones.append(d[-10:])
    seen = set()
    select = ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "TITLE", "PHONE", "EMAIL", "IM", "HAS_IMOL", "ASSIGNED_BY_ID"]
    for phone in phones:
        if not phone or phone in seen:
            continue
        seen.add(phone)
        for method, entity_type in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            body = client.call(method, {"filter[PHONE]": phone, "select[]": select, "start": 0})
            for item in body.get("result") or []:
                if records_compatible(person, item) or not phones_of(item):
                    matches.append({"entity_type": entity_type, "entity_id": str(item.get("ID")), "how": "live_phone", "record": item})
    email = person.get("primary_email")
    if email and not matches:
        for method, entity_type in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            body = client.call(method, {"filter[EMAIL]": email, "select[]": select, "start": 0})
            for item in body.get("result") or []:
                matches.append({"entity_type": entity_type, "entity_id": str(item.get("ID")), "how": "live_email", "record": item})
    unique = []
    have = set()
    for match in matches:
        key = (match["entity_type"], match["entity_id"])
        if key in have:
            continue
        have.add(key)
        unique.append(match)
    return unique


def resolve_person(person: dict, contact_idx: dict, lead_idx: dict, client: BitrixClient | None = None) -> dict:
    warnings = []
    matches = []
    for sid in person["source_bitrix_ids"]:
        if sid in contact_idx["by_id"]:
            rec = contact_idx["by_id"][sid]
            if records_compatible(person, rec):
                matches.append({"entity_type": "contact", "entity_id": sid, "how": "source_id", "record": rec})
            else:
                warnings.append(f"source_id_contact_mismatch:{sid}")
        if sid in lead_idx["by_id"]:
            rec = lead_idx["by_id"][sid]
            if records_compatible(person, rec):
                matches.append({"entity_type": "lead", "entity_id": sid, "how": "source_id", "record": rec})
            else:
                warnings.append(f"source_id_lead_mismatch:{sid}")
    if not matches:
        phone_hits = set()
        for key in phone_keys(person.get("primary_phone")):
            phone_hits.update(contact_idx["by_phone"].get(key) or [])
        if len(phone_hits) == 1:
            eid = next(iter(phone_hits))
            matches.append({"entity_type": "contact", "entity_id": eid, "how": "phone", "record": contact_idx["by_id"][eid]})
        elif len(phone_hits) > 1:
            warnings.append(f"ambiguous_contact_phone:{sorted(phone_hits)[:8]}")
        phone_leads = set()
        for key in phone_keys(person.get("primary_phone")):
            phone_leads.update(lead_idx["by_phone"].get(key) or [])
        if not matches and len(phone_leads) == 1:
            eid = next(iter(phone_leads))
            matches.append({"entity_type": "lead", "entity_id": eid, "how": "phone", "record": lead_idx["by_id"][eid]})
        elif not matches and len(phone_leads) > 1:
            warnings.append(f"ambiguous_lead_phone:{sorted(phone_leads)[:8]}")
    if not matches and person.get("primary_email"):
        email = person["primary_email"]
        hits = contact_idx["by_email"].get(email) or []
        if len(hits) == 1:
            eid = hits[0]
            matches.append({"entity_type": "contact", "entity_id": eid, "how": "email", "record": contact_idx["by_id"][eid]})
        elif len(hits) > 1:
            warnings.append(f"ambiguous_contact_email:{hits[:8]}")
        lead_hits = lead_idx["by_email"].get(email) or []
        if not matches and len(lead_hits) == 1:
            eid = lead_hits[0]
            matches.append({"entity_type": "lead", "entity_id": eid, "how": "email", "record": lead_idx["by_id"][eid]})
        elif not matches and len(lead_hits) > 1:
            warnings.append(f"ambiguous_lead_email:{lead_hits[:8]}")
    if not matches and client is not None:
        live = live_lookup(client, person)
        matches.extend(live)
        if not live:
            warnings.append("live_lookup_empty")
    unique = []
    seen = set()
    for match in matches:
        key = (match["entity_type"], match["entity_id"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(match)
    return {"matches": unique, "warnings": warnings}


def history_rows_for_entity(
    person: dict,
    entity_type: str,
    entity_id: str,
    comments: list[dict],
    activities: list[dict],
    author_names: dict[str, str | None],
    chat_messages: list[dict],
) -> list[dict]:
    rows = []
    for item in comments:
        author_id = str(item.get("AUTHOR_ID") or item.get("CREATED_BY") or "")
        files = extract_attachments(item)
        text = str(item.get("COMMENT") or item.get("TEXT") or "")
        rows.append(
            {
                "canonical_crm_contact_id": person["canonical_crm_contact_id"],
                "person_name": person["person_name"],
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
                "history_type": "comment",
                "bitrix_record_id": item.get("ID"),
                "chat_id": "",
                "message_id": "",
                "date_time": item.get("CREATED") or item.get("DATE_CREATE"),
                "author_id": author_id,
                "author_name": author_names.get(author_id) or "",
                "direction": "",
                "title": "timeline comment",
                "full_text": text,
                "attachment_count": len(files),
                "source_api_method": "crm.timeline.comment.list",
            }
        )
    for item in activities:
        kind = classify_activity(item)
        author_id = str(item.get("AUTHOR_ID") or item.get("RESPONSIBLE_ID") or "")
        files = extract_attachments(item)
        refs = openchannel_refs(item)
        text = str(item.get("DESCRIPTION") or item.get("SUBJECT") or "")
        rows.append(
            {
                "canonical_crm_contact_id": person["canonical_crm_contact_id"],
                "person_name": person["person_name"],
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
                "history_type": kind,
                "bitrix_record_id": item.get("ID"),
                "chat_id": refs.get("chat_id") or refs.get("session_id") or "",
                "message_id": "",
                "date_time": item.get("CREATED") or item.get("START_TIME"),
                "author_id": author_id,
                "author_name": author_names.get(author_id) or "",
                "direction": str(item.get("DIRECTION") or ""),
                "title": item.get("SUBJECT") or "",
                "full_text": text,
                "attachment_count": len(files),
                "source_api_method": "crm.activity.list",
            }
        )
    for msg in chat_messages:
        rows.append(
            {
                "canonical_crm_contact_id": person["canonical_crm_contact_id"],
                "person_name": person["person_name"],
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
                "history_type": "whatsapp_message",
                "bitrix_record_id": msg.get("activity_id") or msg.get("comment_id") or "",
                "chat_id": msg.get("chat_id") or "",
                "message_id": msg.get("message_id") or "",
                "date_time": msg.get("date_time") or "",
                "author_id": msg.get("sender_id") or "",
                "author_name": msg.get("sender_name") or "",
                "direction": msg.get("direction") or "",
                "title": "open channel message",
                "full_text": msg.get("message_text") or "",
                "attachment_count": msg.get("attachment_count") or 0,
                "source_api_method": msg.get("source_api_method") or "",
            }
        )
    return rows


def build_report(stats: dict, archive: Path, kaan: dict, berk: dict, client: BitrixClient) -> dict:
    return {
        "generated_at": utc_now(),
        "archive_path": str(archive),
        "total_source_people_checked": stats["people_checked"],
        "active_checked": stats["active_checked"],
        "junk_checked": stats["junk_checked"],
        "agents_checked": stats["agents_checked"],
        "contacts_found": stats["contacts_found"],
        "leads_found": stats["leads_found"],
        "unresolved_source_ids": stats["unresolved"],
        "people_with_history": stats["people_with_history"],
        "people_with_zero_history": stats["people_with_zero_history"],
        "history_counts": {
            "timeline_comments": stats["comments"],
            "whatsapp_open_channel_activities": stats["whatsapp_activities"],
            "actual_recovered_whatsapp_open_channel_messages": stats["whatsapp_messages"],
            "sms": stats["sms"],
            "calls": stats["calls"],
            "emails": stats["emails"],
            "meetings": stats["meetings"],
            "tasks": stats["tasks"],
            "notes": stats["notes"],
            "other_activities": stats["other"],
        },
        "chats_discovered": stats["chats_discovered"],
        "chats_with_full_messages_recovered": stats["chats_full"],
        "chats_summary_only_or_inaccessible": stats["chats_summary"],
        "attachment_references_found": stats["attachment_refs"],
        "attachments_downloaded": stats["attachments_downloaded"],
        "api_failures": client.failures[-200:],
        "permission_failures": client.permission_failures[:50] + [{"note": "duplicates collapsed", "unique_methods": sorted(client.known_denied)}],
        "unresolved_chat_ids": stats["unresolved_chat_ids"],
        "retry_count": client.retry_count,
        "bitrix_calls": client.call_count,
        "webhook_scope": stats.get("scope"),
        "open_channel_api_status": stats.get("open_channel_api_status"),
        "kaan_kalyon_validation": kaan,
        "berk_cimen_validation": berk,
        "crm_write_confirmation": "NO Investhome OS CRM data was modified",
        "checkpoint": stats.get("checkpoint"),
    }


def empty_stats() -> dict:
    return {
        "people_checked": 0,
        "active_checked": 0,
        "junk_checked": 0,
        "agents_checked": 0,
        "contacts_found": 0,
        "leads_found": 0,
        "unresolved": 0,
        "people_with_history": 0,
        "people_with_zero_history": 0,
        "comments": 0,
        "whatsapp_activities": 0,
        "whatsapp_messages": 0,
        "sms": 0,
        "calls": 0,
        "emails": 0,
        "meetings": 0,
        "tasks": 0,
        "notes": 0,
        "other": 0,
        "chats_discovered": 0,
        "chats_full": 0,
        "chats_summary": 0,
        "attachment_refs": 0,
        "attachments_downloaded": 0,
        "unresolved_chat_ids": [],
        "total_history_rows": 0,
    }


def add_counts(stats: dict, comments: list[dict], activities: list[dict], messages: list[dict], attachments: int) -> tuple[int, int, int]:
    stats["comments"] += len(comments)
    wa_acts = 0
    chats_disc = set()
    for act in activities:
        kind = classify_activity(act)
        if kind == "whatsapp":
            stats["whatsapp_activities"] += 1
            wa_acts += 1
            refs = openchannel_refs(act)
            chats_disc.add(str(refs.get("session_id") or refs.get("user_code") or act.get("ID")))
        elif kind == "call":
            stats["calls"] += 1
        elif kind == "email":
            stats["emails"] += 1
        elif kind == "meeting":
            stats["meetings"] += 1
        elif kind == "task":
            stats["tasks"] += 1
        elif kind == "sms":
            stats["sms"] += 1
        else:
            stats["other"] += 1
    stats["whatsapp_messages"] += len(messages)
    stats["attachment_refs"] += attachments
    return wa_acts, len(chats_disc), len(messages)


class ArchiveRun:
    def __init__(self, root: Path, client: BitrixClient, smoke: bool) -> None:
        self.root = root
        self.client = client
        self.smoke = smoke
        self.raw = root / "raw"
        self.attachments = root / "attachments"
        self.reports = root / "reports"
        self.checkpoints = root / "checkpoints"
        for path in (self.raw / "contacts", self.raw / "leads", self.raw / "chats", self.raw / "users", self.attachments, self.reports, self.checkpoints):
            path.mkdir(parents=True, exist_ok=True)
        self.state_path = self.checkpoints / "state.json"
        self.state = self._load_state()
        self.author_names: dict[str, str | None] = dict(self.state.get("author_names") or {})
        self.stats = self.state.get("stats") or empty_stats()
        self.open_channel_status = self.state.get("open_channel_api_status")

    def _load_state(self) -> dict:
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        return {"completed": {}, "unresolved": {}, "author_names": {}, "stats": empty_stats()}

    def save_state(self) -> None:
        self.state["stats"] = self.stats
        self.state["author_names"] = self.author_names
        self.state["open_channel_api_status"] = self.open_channel_status
        self.state["updated_at"] = utc_now()
        atomic_write_json(self.state_path, self.state)

    def log(self, message: str) -> None:
        line = f"{utc_now()} {message}"
        print(line, flush=True)
        with (self.checkpoints / "progress.log").open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")

    def probe_open_channel(self) -> None:
        if self.open_channel_status:
            return
        methods = [
            ("imopenlines.crm.chat.get", {"CRM_ENTITY_TYPE": "lead", "CRM_ENTITY": 34456, "ACTIVE_ONLY": "N"}),
            ("imopenlines.session.history.get", {"SESSION_ID": 10542}),
            ("im.dialog.messages.get", {"DIALOG_ID": "chat10706"}),
            ("user.get", {"ID": 92}),
            ("disk.file.get", {"id": 1}),
        ]
        results = {}
        for method, payload in methods:
            body = self.client.call(method, payload)
            results[method] = {
                "error": body.get("error"),
                "error_description": body.get("error_description"),
            }
        scope = self.client.call("scope", {})
        self.open_channel_status = {
            "webhook_scope": scope.get("result"),
            "probes": results,
            "reason": "permission denied: webhook scope is crm only; Open Channel/IM/user/disk methods returned insufficient_scope",
        }
        self.stats["scope"] = scope.get("result")
        self.stats["open_channel_api_status"] = self.open_channel_status
        profile = self.client.call("profile", {})
        result = profile.get("result") or {}
        if result.get("ID"):
            name = " ".join(p for p in [result.get("NAME"), result.get("LAST_NAME")] if p).strip()
            self.author_names[str(result.get("ID"))] = name or None
        self.save_state()

    def entity_path(self, entity_type: str, entity_id: str) -> Path:
        folder = "contacts" if entity_type == "contact" else "leads"
        return self.raw / folder / f"{entity_id}.json"

    def fetch_entity(self, person: dict, entity_type: str, entity_id: str, live_record: dict, how: str) -> dict:
        comments, c_methods = self.client.list_entity(
            "crm.timeline.comment.list",
            {"ENTITY_TYPE": entity_type, "ENTITY_ID": entity_id},
        )
        activities, a_methods = self.client.list_entity(
            "crm.activity.list",
            {"OWNER_TYPE_ID": OWNER_TYPE[entity_type], "OWNER_ID": entity_id},
        )
        return self.save_fetched(person, entity_type, entity_id, live_record, how, comments, activities, c_methods + a_methods)

    def save_fetched(
        self,
        person: dict,
        entity_type: str,
        entity_id: str,
        live_record: dict,
        how: str,
        comments: list[dict],
        activities: list[dict],
        methods: list[str],
        errors: list | None = None,
    ) -> dict:
        errors = list(errors or [])
        chat_messages: list[dict] = []
        chats_meta = []
        wa_acts = [a for a in activities if classify_activity(a) == "whatsapp"]
        for act in wa_acts:
            refs = openchannel_refs(act, live_record)
            reason = self.open_channel_status["reason"] if self.open_channel_status else "Open Channel APIs not available"
            chat_rec = {
                **refs,
                "person_name": person["person_name"],
                "canonical_crm_contact_id": person["canonical_crm_contact_id"],
                "bitrix_entity_type": entity_type,
                "bitrix_entity_id": entity_id,
                "recovery_status": "summary_only",
                "recovery_reason": reason,
                "messages": [],
                "activity_subject": act.get("SUBJECT"),
                "retrieved_at": utc_now(),
            }
            chats_meta.append(chat_rec)
            key = refs.get("session_id") or refs.get("chat_id") or act.get("ID")
            atomic_write_json(self.raw / "chats" / f"{entity_type}_{entity_id}_{key}.json", chat_rec)
            self.stats["unresolved_chat_ids"] = list(set(self.stats.get("unresolved_chat_ids") or []) | {str(key)})
        for comment in comments:
            parsed = parse_whatsapp_comment(str(comment.get("COMMENT") or ""))
            if not parsed:
                continue
            for idx, msg in enumerate(parsed):
                msg.update(
                    {
                        "comment_id": comment.get("ID"),
                        "message_id": f"{comment.get('ID')}:{idx}",
                        "chat_id": None,
                        "session_id": None,
                        "provider": "whatsapp_timeline_comment",
                        "source_api_method": "crm.timeline.comment.list",
                        "attachment_count": len(extract_attachments(comment)),
                    }
                )
                chat_messages.append(msg)
        attachments = []
        for item in comments + activities:
            attachments.extend(extract_attachments(item))
        payload = {
            "canonical_crm_contact_id": person["canonical_crm_contact_id"],
            "person_name": person["person_name"],
            "source_group": person["group"],
            "source_roles": person["source_roles"],
            "source_external_ids": person["external_ids"],
            "resolution_method": how,
            "bitrix_entity_type": entity_type,
            "bitrix_entity_id": entity_id,
            "live_entity": live_record,
            "timeline_comments": comments,
            "crm_activities": activities,
            "linked_chat_references": chats_meta,
            "retrieved_chat_messages": chat_messages,
            "attachment_references": attachments,
            "api_methods_used": methods,
            "retrieval_timestamp": utc_now(),
            "errors_warnings": errors,
            "open_channel_recovery": self.open_channel_status,
        }
        atomic_write_json(self.entity_path(entity_type, entity_id), payload)
        return payload

    def fetch_jobs(self, jobs: list[tuple[dict, dict]]) -> list[tuple[dict, dict, dict]]:
        if not jobs:
            return []
        if len(jobs) == 1:
            person, match = jobs[0]
            payload = self.fetch_entity(person, match["entity_type"], match["entity_id"], match["record"], match["how"])
            return [(person, match, payload)]
        commands: dict[str, tuple[str, dict]] = {}
        for index, (_person, match) in enumerate(jobs):
            entity_type = match["entity_type"]
            entity_id = match["entity_id"]
            commands[f"c{index}"] = (
                "crm.timeline.comment.list",
                {"filter[ENTITY_TYPE]": entity_type, "filter[ENTITY_ID]": entity_id, "start": 0},
            )
            commands[f"a{index}"] = (
                "crm.activity.list",
                {"filter[OWNER_TYPE_ID]": OWNER_TYPE[entity_type], "filter[OWNER_ID]": entity_id, "start": 0},
            )
        body = self.client.batch(commands)
        results = body.get("result") or {}
        result_error = body.get("result_error") or {}
        result_next = body.get("result_next") or {}
        out: list[tuple[dict, dict, dict]] = []
        for index, (person, match) in enumerate(jobs):
            entity_type = match["entity_type"]
            entity_id = match["entity_id"]
            if result_error.get(f"c{index}") or result_error.get(f"a{index}"):
                payload = self.fetch_entity(person, entity_type, entity_id, match["record"], match["how"])
                out.append((person, match, payload))
                continue
            comments = results.get(f"c{index}") or []
            activities = results.get(f"a{index}") or []
            if not isinstance(comments, list):
                comments = []
            if not isinstance(activities, list):
                activities = []
            methods = ["crm.timeline.comment.list", "crm.activity.list", "batch"]
            nxt_c = result_next.get(f"c{index}")
            nxt_a = result_next.get(f"a{index}")
            if nxt_c is not None:
                comments = comments + self.client.list_continue(
                    "crm.timeline.comment.list",
                    {"ENTITY_TYPE": entity_type, "ENTITY_ID": entity_id},
                    int(nxt_c),
                )
            if nxt_a is not None:
                activities = activities + self.client.list_continue(
                    "crm.activity.list",
                    {"OWNER_TYPE_ID": OWNER_TYPE[entity_type], "OWNER_ID": entity_id},
                    int(nxt_a),
                )
            payload = self.save_fetched(person, entity_type, entity_id, match["record"], match["how"], comments, activities, methods)
            out.append((person, match, payload))
        return out

    def mark_completed(self, key: str, info: dict) -> None:
        self.state.setdefault("completed", {})[key] = info
        self.save_state()


def validate_person(archive: Path, name_fold: str, expect: dict) -> dict:
    found = None
    for folder in ("contacts", "leads"):
        directory = archive / "raw" / folder
        if not directory.exists():
            continue
        for path in directory.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if fold_name(data.get("person_name")) == name_fold or name_fold in fold_name(data.get("person_name") or ""):
                found = data
                break
        if found:
            break
    if not found:
        return {"found": False, "error": "archive file not found"}
    comments = found.get("timeline_comments") or []
    activities = found.get("crm_activities") or []
    wa_acts = [a for a in activities if classify_activity(a) == "whatsapp"]
    sms = [a for a in activities if classify_activity(a) == "sms"]
    tasks = [a for a in activities if classify_activity(a) == "task"]
    messages = found.get("retrieved_chat_messages") or []
    return {
        "found": True,
        "person_name": found.get("person_name"),
        "bitrix_entity_type": found.get("bitrix_entity_type"),
        "bitrix_entity_id": str(found.get("bitrix_entity_id")),
        "resolution_method": found.get("resolution_method"),
        "comment_count": len(comments),
        "activity_count": len(activities),
        "whatsapp_activity_count": len(wa_acts),
        "sms_count": len(sms),
        "task_count": len(tasks),
        "crm_history_record_count": len(comments) + len(activities),
        "recovered_whatsapp_messages": len(messages),
        "expected": expect,
        "matches_expected_entity": (
            found.get("bitrix_entity_type") == expect.get("entity_type")
            and str(found.get("bitrix_entity_id")) == str(expect.get("entity_id"))
        ),
        "matches_expected_history_count": (len(comments) + len(activities)) == expect.get("history_records"),
        "whatsapp_beyond_activity_rows": len(messages) > 0,
        "open_channel_status": (found.get("open_channel_recovery") or {}).get("reason"),
    }


def rebuild_masters(archive: Path, author_names: dict[str, str | None]) -> dict:
    history_path = archive / "BITRIX_HISTORY_MASTER.csv"
    chat_path = archive / "BITRIX_CHAT_MESSAGES_MASTER.csv"
    hist_fields = [
        "canonical_crm_contact_id",
        "person_name",
        "bitrix_entity_type",
        "bitrix_entity_id",
        "history_type",
        "bitrix_record_id",
        "chat_id",
        "message_id",
        "date_time",
        "author_id",
        "author_name",
        "direction",
        "title",
        "full_text",
        "attachment_count",
        "source_api_method",
    ]
    chat_fields = [
        "canonical_crm_contact_id",
        "person_name",
        "bitrix_entity_type",
        "bitrix_entity_id",
        "provider",
        "chat_id",
        "dialog_id",
        "session_id",
        "message_id",
        "date_time",
        "sender_id",
        "sender_name",
        "direction",
        "message_text",
        "attachment_count",
        "source_api_method",
    ]
    stats = empty_stats()
    seen_people_history = set()
    with history_path.open("w", encoding="utf-8", newline="") as hist_f, chat_path.open("w", encoding="utf-8", newline="") as chat_f:
        hist_w = csv.DictWriter(hist_f, fieldnames=hist_fields, extrasaction="ignore")
        chat_w = csv.DictWriter(chat_f, fieldnames=chat_fields, extrasaction="ignore")
        hist_w.writeheader()
        chat_w.writeheader()
        for folder, entity_type in (("contacts", "contact"), ("leads", "lead")):
            directory = archive / "raw" / folder
            if not directory.exists():
                continue
            for path in sorted(directory.glob("*.json")):
                if path.name.startswith("_"):
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                person = {
                    "canonical_crm_contact_id": data.get("canonical_crm_contact_id"),
                    "person_name": data.get("person_name"),
                    "group": data.get("source_group"),
                }
                comments = data.get("timeline_comments") or []
                activities = data.get("crm_activities") or []
                messages = data.get("retrieved_chat_messages") or []
                rows = history_rows_for_entity(
                    person,
                    data.get("bitrix_entity_type") or entity_type,
                    str(data.get("bitrix_entity_id")),
                    comments,
                    activities,
                    author_names,
                    [],
                )
                for row in rows:
                    hist_w.writerow(row)
                for msg in messages:
                    chat_w.writerow(
                        {
                            "canonical_crm_contact_id": data.get("canonical_crm_contact_id"),
                            "person_name": data.get("person_name"),
                            "bitrix_entity_type": data.get("bitrix_entity_type"),
                            "bitrix_entity_id": data.get("bitrix_entity_id"),
                            "provider": msg.get("provider"),
                            "chat_id": msg.get("chat_id") or "",
                            "dialog_id": msg.get("dialog_id") or "",
                            "session_id": msg.get("session_id") or "",
                            "message_id": msg.get("message_id") or "",
                            "date_time": msg.get("date_time") or "",
                            "sender_id": msg.get("sender_id") or "",
                            "sender_name": msg.get("sender_name") or "",
                            "direction": msg.get("direction") or "",
                            "message_text": msg.get("message_text") or "",
                            "attachment_count": msg.get("attachment_count") or 0,
                            "source_api_method": msg.get("source_api_method") or "",
                        }
                    )
                crm_count = len(comments) + len(activities)
                stats["total_history_rows"] += crm_count
                if crm_count:
                    seen_people_history.add(data.get("canonical_crm_contact_id"))
                add_counts(stats, comments, activities, messages, len(data.get("attachment_references") or []))
                chats = data.get("linked_chat_references") or []
                stats["chats_discovered"] += len(chats)
                if messages:
                    stats["chats_full"] += 1
                stats["chats_summary"] += len(chats)
                if entity_type == "contact":
                    stats["contacts_found"] += 1
                else:
                    stats["leads_found"] += 1
    stats["people_with_history"] = len(seen_people_history)
    return {"history_csv": str(history_path), "chat_csv": str(chat_path), "rebuild_stats": stats}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive-root", default="/export")
    parser.add_argument("--env-file", default="/tmp/.env")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    archive = Path(args.archive_root) / ARCHIVE_REL
    archive.mkdir(parents=True, exist_ok=True)
    env = load_env(Path(args.env_file))
    raw_url = env.get("BITRIX_WEBHOOK_URL") or ""
    if not raw_url:
        print("MISSING_BITRIX_WEBHOOK_URL")
        return 2
    client = BitrixClient(webhook_base(raw_url))
    run = ArchiveRun(archive, client, args.smoke)
    run.log(f"START smoke={args.smoke}")
    run.probe_open_channel()
    run.log(f"SCOPE={run.open_channel_status}")

    def _index_stale(rows: list) -> bool:
        if not rows:
            return True
        sample = rows[0]
        return sample.get("PHONE") is None and sample.get("EMAIL") is None

    contacts_path = run.raw / "contacts" / "_index.json"
    leads_path = run.raw / "leads" / "_index.json"
    contacts = json.loads(contacts_path.read_text(encoding="utf-8")) if contacts_path.exists() else []
    leads = json.loads(leads_path.read_text(encoding="utf-8")) if leads_path.exists() else []
    if _index_stale(contacts):
        run.log("INDEX contacts refresh with PHONE/EMAIL")
        contacts = client.list_all(
            "crm.contact.list",
            {"select[]": INDEX_SELECT},
            progress=lambda n, total: run.log(f"INDEX contacts n={n} total={total}"),
        )
        atomic_write_json(contacts_path, contacts)
        run.log(f"INDEX contacts done n={len(contacts)}")
    else:
        run.log(f"INDEX contacts loaded n={len(contacts)}")
    if _index_stale(leads):
        run.log("INDEX leads refresh with PHONE/EMAIL")
        leads = client.list_all(
            "crm.lead.list",
            {"select[]": INDEX_SELECT},
            progress=lambda n, total: run.log(f"INDEX leads n={n} total={total}"),
        )
        atomic_write_json(leads_path, leads)
        run.log(f"INDEX leads done n={len(leads)}")
    else:
        run.log(f"INDEX leads loaded n={len(leads)}")

    contact_idx = index_entities(contacts, "contact")
    lead_idx = index_entities(leads, "lead")
    atomic_write_json(run.raw / "users" / "users.json", {"author_names": run.author_names, "open_channel": run.open_channel_status, "scope": (run.open_channel_status or {}).get("webhook_scope")})

    db = SessionLocal()
    try:
        people = load_people(db, args.smoke)
    finally:
        db.close()
    atomic_write_json(run.checkpoints / "people_index.json", {"count": len(people), "people": people})
    run.log(f"PEOPLE n={len(people)}")

    pending_jobs: list[tuple[dict, dict]] = []
    person_job_counts: dict[str, int] = {}

    def flush_jobs() -> None:
        if not pending_jobs:
            return
        batch = list(pending_jobs)
        pending_jobs.clear()
        try:
            fetched = run.fetch_jobs(batch)
        except Exception as exc:  # noqa: BLE001
            run.log(f"BATCH_FAIL {redact(str(exc), client.base)}")
            fetched = []
            for person, match in batch:
                try:
                    payload = run.fetch_entity(person, match["entity_type"], match["entity_id"], match["record"], match["how"])
                    fetched.append((person, match, payload))
                except Exception as inner:  # noqa: BLE001
                    append_jsonl(
                        run.checkpoints / "failures.jsonl",
                        {"entity": f"{match['entity_type']}:{match['entity_id']}", "person": person["person_name"], "error": redact(str(inner), client.base)},
                    )
        for person, match, payload in fetched:
            entity_key = f"{match['entity_type']}:{match['entity_id']}"
            comments = payload.get("timeline_comments") or []
            activities = payload.get("crm_activities") or []
            messages = payload.get("retrieved_chat_messages") or []
            crm_count = len(comments) + len(activities)
            if match["entity_type"] == "contact":
                run.stats["contacts_found"] += 1
            else:
                run.stats["leads_found"] += 1
            add_counts(run.stats, comments, activities, messages, len(payload.get("attachment_references") or []))
            chats = payload.get("linked_chat_references") or []
            run.stats["chats_discovered"] += len(chats)
            if messages:
                run.stats["chats_full"] += 1
            run.stats["chats_summary"] += len(chats)
            run.stats["total_history_rows"] = run.stats.get("total_history_rows", 0) + crm_count
            run.mark_completed(
                entity_key,
                {
                    "canonical_crm_contact_id": person["canonical_crm_contact_id"],
                    "person_name": person["person_name"],
                    "group": person["group"],
                    "how": match["how"],
                    "comments": len(comments),
                    "activities": len(activities),
                    "messages": len(messages),
                    "at": utc_now(),
                },
            )
            run.log(f"OK {entity_key} {person['person_name']} comments={len(comments)} activities={len(activities)} msgs={len(messages)}")

    for person in people:
        key_person = person["canonical_crm_contact_id"]
        resolved = resolve_person(person, contact_idx, lead_idx, client)
        if person["group"] == "active":
            run.stats["active_checked"] += 1
        elif person["group"] == "junk":
            run.stats["junk_checked"] += 1
        elif person["group"] == "agent":
            run.stats["agents_checked"] += 1
        run.stats["people_checked"] += 1
        if not resolved["matches"]:
            run.state.setdefault("unresolved", {})[key_person] = {
                "person_name": person["person_name"],
                "source_bitrix_ids": person["source_bitrix_ids"],
                "warnings": resolved["warnings"],
                "group": person["group"],
                "at": utc_now(),
            }
            run.stats["unresolved"] = len(run.state.get("unresolved") or {})
            continue
        run.state.get("unresolved", {}).pop(key_person, None)
        had_history = False
        for match in resolved["matches"]:
            entity_key = f"{match['entity_type']}:{match['entity_id']}"
            completed = run.state.get("completed") or {}
            existing_path = run.entity_path(match["entity_type"], match["entity_id"])
            if entity_key in completed and existing_path.exists():
                existing = json.loads(existing_path.read_text(encoding="utf-8"))
                if len(existing.get("timeline_comments") or []) + len(existing.get("crm_activities") or []):
                    had_history = True
                continue
            pending_jobs.append((person, match))
            person_job_counts[key_person] = person_job_counts.get(key_person, 0) + 1
            if len(pending_jobs) >= 20:
                flush_jobs()
        if had_history:
            run.stats["people_with_history"] += 1
        elif person_job_counts.get(key_person):
            pass
        else:
            run.stats["people_with_zero_history"] += 1
        if run.stats["people_checked"] % 50 == 0:
            flush_jobs()
            run.save_state()
            run.log(f"PROGRESS people={run.stats['people_checked']} contacts={run.stats['contacts_found']} leads={run.stats['leads_found']} unresolved={len(run.state.get('unresolved') or {})}")
    flush_jobs()

    # recount groups accurately from people_index vs completed/unresolved
    run.stats["unresolved"] = len(run.state.get("unresolved") or {})
    run.save_state()
    masters = rebuild_masters(archive, run.author_names)
    rebuilt = masters["rebuild_stats"]
    run.stats["people_checked"] = len(people)
    run.stats["active_checked"] = sum(1 for item in people if item["group"] == "active")
    run.stats["junk_checked"] = sum(1 for item in people if item["group"] == "junk")
    run.stats["agents_checked"] = sum(1 for item in people if item["group"] == "agent")
    run.stats["unresolved"] = len(run.state.get("unresolved") or {})
    for key in (
        "comments",
        "whatsapp_activities",
        "whatsapp_messages",
        "sms",
        "calls",
        "emails",
        "meetings",
        "tasks",
        "other",
        "chats_discovered",
        "chats_full",
        "chats_summary",
        "attachment_refs",
        "contacts_found",
        "leads_found",
        "people_with_history",
        "total_history_rows",
    ):
        run.stats[key] = rebuilt.get(key, run.stats.get(key, 0))
    run.stats["people_with_zero_history"] = max(
        0,
        run.stats["people_checked"] - run.stats["unresolved"] - run.stats["people_with_history"],
    )
    run.save_state()
    kaan = validate_person(
        archive,
        "kaan kalyon",
        {"entity_type": "lead", "entity_id": "34456", "history_records": 13},
    )
    berk = validate_person(
        archive,
        "berk cimen",
        {"entity_type": "contact", "entity_id": "180", "history_records": 5},
    )
    report = build_report(run.stats, archive, kaan, berk, client)
    report["masters"] = masters
    report["checkpoint"] = {"path": str(run.state_path), "completed": len(run.state.get("completed") or {}), "unresolved": len(run.state.get("unresolved") or {})}
    atomic_write_json(run.reports / "BITRIX_HISTORY_RESCUE_REPORT.json", report)
    summary = {
        "1_total_source_people_checked": run.stats["people_checked"],
        "2_contacts_found": run.stats["contacts_found"],
        "3_leads_found": run.stats["leads_found"],
        "4_unresolved_people": run.stats["unresolved"],
        "5_people_with_history": run.stats["people_with_history"],
        "6_total_crm_history_records": run.stats.get("total_history_rows", 0),
        "7_timeline_comments": run.stats["comments"],
        "8_whatsapp_open_channel_activities": run.stats["whatsapp_activities"],
        "9_actual_recovered_whatsapp_messages": run.stats["whatsapp_messages"],
        "10_sms_calls_emails_meetings_tasks": {
            "sms": run.stats["sms"],
            "calls": run.stats["calls"],
            "emails": run.stats["emails"],
            "meetings": run.stats["meetings"],
            "tasks": run.stats["tasks"],
        },
        "11_chats_discovered": run.stats["chats_discovered"],
        "12_chats_fully_recovered": run.stats["chats_full"],
        "13_chats_summary_only": run.stats["chats_summary"],
        "14_attachment_count": run.stats["attachment_refs"],
        "15_failures_permission_problems": {
            "api_failures": len(client.failures),
            "permission_denied_methods": sorted(client.known_denied),
            "retry_count": client.retry_count,
        },
        "16_archive_path": str(archive),
        "17_kaan_kalyon_validation": kaan,
        "18_berk_cimen_validation": berk,
        "19_resume_checkpoint": report["checkpoint"],
        "20_crm_modified": "NO",
    }
    atomic_write_json(run.reports / "BITRIX_HISTORY_RESCUE_SUMMARY.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    run.log("DONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
