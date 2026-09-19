"""Read-only live Bitrix lookup for Albert Levi by CRM phone/email."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from investhome_api.db.session import SessionLocal

NON_DIGIT = re.compile(r"\D+")
OWNER_TYPE = {"contact": 3, "lead": 1}


def digits(value: str | None) -> str:
    return NON_DIGIT.sub("", value or "")


def phone_keys(value: str | None) -> set[str]:
    raw = digits(value)
    keys = set()
    if len(raw) >= 10:
        keys.add(raw)
        keys.add(raw[-10:])
        if raw.startswith("90") and len(raw) >= 12:
            keys.add(raw[-10:])
    return {k for k in keys if len(k) >= 10}


def phones_of(item: dict) -> list[str]:
    values = []
    field = item.get("PHONE") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        val = row.get("VALUE") if isinstance(row, dict) else str(row or "")
        if digits(val):
            values.append(val)
    return values


def emails_of(item: dict) -> list[str]:
    values = []
    field = item.get("EMAIL") or []
    if isinstance(field, str):
        field = [{"VALUE": field}]
    for row in field:
        val = (row.get("VALUE") if isinstance(row, dict) else str(row or "")).strip().lower()
        if val and "@" in val:
            values.append(val)
    return values


def load_env(path: Path) -> dict[str, str]:
    values = {}
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
    parsed = urllib.parse.urlparse(value.strip().strip('"').strip("'"))
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(segs) + "/", "", "", ""))


def call(base: str, method: str, payload: dict | None = None) -> dict:
    url = urllib.parse.urljoin(base, method + ".json")
    data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": f"HTTP {exc.code}"}


def list_entity(base: str, method: str, filt: dict) -> list[dict]:
    items = []
    start = 0
    seen = set()
    while start not in seen:
        seen.add(start)
        payload = {f"filter[{k}]": v for k, v in filt.items()}
        payload["start"] = start
        body = call(base, method, payload)
        if body.get("error"):
            return items
        chunk = body.get("result") or []
        items.extend(chunk)
        nxt = body.get("next")
        if nxt is None or not chunk:
            break
        start = int(nxt)
    return items


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or "").upper()
    if "IMOPENLINES" in provider or "whatsapp" in low or "open channel" in low or "whatcrm" in low:
        return "WhatsApp"
    if "EMAIL" in provider or "MAIL" in provider:
        return "email"
    if "TASK" in provider:
        return "task"
    if "MEETING" in provider or provider == "CRM_TODO":
        return "meeting"
    if "SMS" in provider:
        return "sms"
    if "CALL" in provider or "VOX" in provider:
        return "call"
    type_id = str(item.get("TYPE_ID") or "")
    return {"1": "meeting", "2": "call", "4": "email", "6": "task"}.get(type_id, "other")


def main() -> None:
    db = SessionLocal()
    contact = db.execute(
        text(
            """
            select id::text, display_name, primary_email, primary_phone
            from crm_contacts where id='c20db712-3636-4f4a-81d2-4255b855cd0e'
            """
        )
    ).mappings().one()
    db.close()
    env = load_env(Path("/tmp/.env"))
    base = webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or env.get("BITRIX_WEBHOOK_URL") or "")
    want_phones = phone_keys(contact["primary_phone"])
    want_email = (contact["primary_email"] or "").strip().lower()
    select = ["ID", "NAME", "LAST_NAME", "SECOND_NAME", "TITLE", "PHONE", "EMAIL"]
    found = []
    variants = []
    d = digits(contact["primary_phone"])
    if d:
        variants.extend([contact["primary_phone"], d, "+" + d, d[-10:] if len(d) >= 10 else d])
    seen_v = set()
    for variant in variants:
        if not variant or variant in seen_v:
            continue
        seen_v.add(variant)
        for method, etype in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            body = call(base, method, {"filter[PHONE]": variant, "select[]": select, "start": 0})
            for item in body.get("result") or []:
                rec_keys: set[str] = set()
                for phone in phones_of(item):
                    rec_keys |= phone_keys(phone)
                if want_phones and rec_keys and not (want_phones & rec_keys):
                    continue
                key = (etype, str(item.get("ID")))
                if key not in {(e["type"], e["id"]) for e in found}:
                    found.append({"type": etype, "id": str(item.get("ID")), "how": "phone", "record": item})
        if found:
            break
    if not found and want_email:
        for method, etype in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            body = call(base, method, {"filter[EMAIL]": want_email, "select[]": select, "start": 0})
            for item in body.get("result") or []:
                if want_email not in set(emails_of(item)):
                    continue
                found.append({"type": etype, "id": str(item.get("ID")), "how": "email", "record": item})

    entities = []
    all_comments = []
    all_acts = Counter()
    for ent in found:
        et, eid = ent["type"], ent["id"]
        comments = list_entity(base, "crm.timeline.comment.list", {"ENTITY_TYPE": et, "ENTITY_ID": eid})
        activities = list_entity(base, "crm.activity.list", {"OWNER_TYPE_ID": OWNER_TYPE[et], "OWNER_ID": eid})
        types = Counter(classify_activity(a) for a in activities)
        all_acts.update(types)
        for c in comments:
            all_comments.append(
                {
                    "entity": f"{et}:{eid}",
                    "id": c.get("ID"),
                    "date": c.get("CREATED") or c.get("DATE_CREATE"),
                    "author_id": c.get("AUTHOR_ID"),
                    "text": str(c.get("COMMENT") or c.get("TEXT") or ""),
                    "has_files": bool(c.get("FILES")),
                }
            )
        rec = ent["record"]
        name = " ".join(p for p in [rec.get("NAME"), rec.get("LAST_NAME"), rec.get("TITLE")] if p)
        entities.append(
            {
                "type": et,
                "id": eid,
                "how": ent["how"],
                "bitrix_name": name,
                "comments": len(comments),
                "activities": dict(types),
                "activity_total": len(activities),
            }
        )
    print(
        json.dumps(
            {
                "crm_id": contact["id"],
                "crm_name": contact["display_name"],
                "live_entities": entities,
                "live_comments_total": len(all_comments),
                "live_activity_counts": dict(all_acts),
                "comments": all_comments,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
