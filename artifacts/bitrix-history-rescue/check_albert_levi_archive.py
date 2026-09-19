"""Read-only: locate Albert Levi Bitrix archive history by phone/email, not name."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from investhome_api.db.session import SessionLocal

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
NON_DIGIT = re.compile(r"\D+")


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
    return {k for k in keys if len(k) >= 10}


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
            from crm_contacts
            where id = 'c20db712-3636-4f4a-81d2-4255b855cd0e'
            """
        )
    ).mappings().first()
    excel_comments = db.execute(
        text(
            """
            select left(coalesce(description, summary, ''), 4000) as text,
                   coalesce(start_date, created_at)::text as dt
            from crm_activities
            where entity_type='contact'
              and entity_id='c20db712-3636-4f4a-81d2-4255b855cd0e'
              and metadata_json::text like '%bitrix_historical_comment%'
            """
        )
    ).mappings().all()
    db.close()
    want_phones = phone_keys(contact["primary_phone"])
    want_email = (contact["primary_email"] or "").strip().lower()
    matches = []
    for folder, etype in ((ARCHIVE / "raw" / "leads", "lead"), (ARCHIVE / "raw" / "contacts", "contact")):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            live = data.get("live_entity") if isinstance(data.get("live_entity"), dict) else {}
            rec_phones: set[str] = set()
            for phone in phones_of(live):
                rec_phones |= phone_keys(phone)
            rec_emails = set(emails_of(live))
            how = []
            if want_phones and rec_phones and (want_phones & rec_phones):
                how.append("phone")
            if want_email and want_email in rec_emails:
                how.append("email")
            if not how:
                continue
            et = str(data.get("bitrix_entity_type") or etype)
            eid = str(data.get("bitrix_entity_id") or path.stem)
            comments = data.get("timeline_comments") or []
            activities = data.get("crm_activities") or []
            live_chat = ARCHIVE / "raw" / "chats" / "live"
            wa = 0
            if live_chat.exists():
                for chat_path in live_chat.glob("*.json"):
                    chat = json.loads(chat_path.read_text(encoding="utf-8"))
                    if str(chat.get("bitrix_entity_type")) == et and str(chat.get("bitrix_entity_id")) == eid:
                        for c in chat.get("chats") or []:
                            wa += len(c.get("messages") or [])
            act_types = Counter(classify_activity(a) for a in activities)
            matches.append(
                {
                    "how": how,
                    "entity": f"{et}:{eid}",
                    "person_name_in_archive": data.get("person_name"),
                    "canonical_in_archive": data.get("canonical_crm_contact_id"),
                    "comments": len(comments),
                    "activities": dict(act_types),
                    "whatsapp_live_messages": wa,
                    "comment_rows": [
                        {
                            "id": c.get("ID"),
                            "date": c.get("CREATED") or c.get("DATE_CREATE"),
                            "author": c.get("AUTHOR_NAME") or c.get("AUTHOR_ID"),
                            "text": str(c.get("COMMENT") or c.get("TEXT") or ""),
                        }
                        for c in comments
                    ],
                    "activity_rows": [
                        {
                            "id": a.get("ID"),
                            "type": classify_activity(a),
                            "provider": a.get("PROVIDER_ID"),
                            "date": a.get("CREATED") or a.get("START_TIME"),
                            "subject": a.get("SUBJECT"),
                            "description": str(a.get("DESCRIPTION") or "")[:300],
                        }
                        for a in activities
                    ],
                }
            )
    print("CRM_EXCEL_COMMENTS", len(excel_comments))
    print("ARCHIVE_MATCHES", len(matches))
    print(json.dumps(matches, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
