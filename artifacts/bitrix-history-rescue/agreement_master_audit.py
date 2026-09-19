"""Live Bitrix master audit for the 55 canonical agreement contacts.

Default: fetch + dry-run (no CRM writes).
--apply: write verified IDs, blank fields, missing history, deal metadata, recoverable files.
Never name-only match. Never treat Excel row IDs as Bitrix IDs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User
from investhome_api.services.crm.identity import normalize_valid_email, parse_phone

from investhome_api.models.document import DocumentLink

from link_agreement_documents import (  # type: ignore
    BitrixClient,
    ENV_PATH,
    existing_document,
    import_document,
    import_tag,
    link_exists,
    load_env,
    mime_of,
    unique_dest,
    webhook_base,
)

OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_MASTER_AUDIT")
ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")
DOCS_OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_CONTACT_DOCUMENTS")
HISTORY_KEY = "bitrix_history"
TUTAR_LABEL = "Tutar ve para birimi"
TUTAR_FIELD_ID = "OPPORTUNITY+CURRENCY_ID"
DISK_FILE_RE = re.compile(r"DISK FILE ID=n?(\d+)", re.I)
BB_RE = re.compile(r"\[/?[^\]]+\]")
NON_DIGIT = re.compile(r"\D+")
TEMPLE_RE = re.compile(r"the\s*temple|\btemple\b", re.I)
EDA_UUID = "2b2c8330-541d-4100-95ea-fb0c036d4e0d"
SEED_IDS = {
    EDA_UUID: {"contact": ["1128"], "lead": ["29102"]},
}
OWNER_TYPE = {"contact": 3, "lead": 1, "deal": 2}
TYPE_MAP = {
    "comment": (CrmActivityType.COMMENT, CrmActivityCategory.NOTE),
    "whatsapp_message": (CrmActivityType.WHATSAPP, CrmActivityCategory.COMMUNICATION),
    "whatsapp_session": (CrmActivityType.WHATSAPP, CrmActivityCategory.COMMUNICATION),
    "sms": (CrmActivityType.SMS, CrmActivityCategory.COMMUNICATION),
    "call": (CrmActivityType.PHONE_CALL, CrmActivityCategory.COMMUNICATION),
    "email": (CrmActivityType.EMAIL, CrmActivityCategory.COMMUNICATION),
    "meeting": (CrmActivityType.MEETING, CrmActivityCategory.MEETING),
    "task": (CrmActivityType.TASK, CrmActivityCategory.TASK),
    "other": (CrmActivityType.OTHER, CrmActivityCategory.OTHER),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def collapse_ws(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def import_key_aliases(key: str) -> set[str]:
    keys = {key}
    if key.startswith("bitrix:whatsapp:"):
        keys.add("bitrix:wa:" + key[len("bitrix:whatsapp:") :])
    if key.startswith("bitrix:wa:"):
        keys.add("bitrix:whatsapp:" + key[len("bitrix:wa:") :])
    parts = key.split(":")
    if len(parts) >= 3 and parts[0] == "bitrix":
        keys.add(f"bitrix:{parts[1]}:{parts[-1]}")
        if len(parts) >= 4:
            keys.add(":".join(parts[:2] + parts[-2:]))
    return {k for k in keys if k}


def digits(value: str | None) -> str:
    return NON_DIGIT.sub("", value or "")


def phone_keys(value: str | None) -> set[str]:
    parsed = parse_phone(value)
    keys: set[str] = set()
    if parsed:
        keys.update({parsed.match_key, parsed.digits, parsed.e164 or ""})
    d = digits(value)
    if len(d) >= 10:
        keys.add(d[-10:])
    return {k for k in keys if k}


def phones_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("PHONE") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]))
        elif isinstance(item, str):
            out.append(item)
    return out


def emails_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("EMAIL") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]).strip().lower())
        elif isinstance(item, str):
            out.append(item.strip().lower())
    return [e for e in out if e]


def flatten(payload: dict) -> dict:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            for inner_k, inner_v in value.items():
                out[f"{key}[{inner_k}]"] = inner_v
        else:
            out[key] = value
    return out


def list_all(client: BitrixClient, method: str, payload: dict) -> list[dict]:
    rows: list[dict] = []
    start = 0
    seen = set()
    while start not in seen:
        seen.add(start)
        body = client.call(method, {**flatten(payload), "start": start})
        result = body.get("result")
        chunk = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else [])
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend([x for x in chunk if isinstance(x, dict)])
        nxt = body.get("next")
        if not isinstance(nxt, int):
            break
        start = nxt
    return rows


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or item.get("DESCRIPTION") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or "").upper()
    provider_type = str(item.get("PROVIDER_TYPE_ID") or "").upper()
    if "whatsapp" in low or "open channel" in low or "whatcrm" in low or "IMOPENLINES" in provider or "IMOL" in provider:
        return "whatsapp_session"
    if "SMS" in provider or provider_type == "SMS" or "sms" in low:
        return "sms"
    if "EMAIL" in provider or "MAIL" in provider or "EMAIL" in provider_type:
        return "email"
    if "VOX" in provider or "CALL" in provider or provider_type == "CALL":
        return "call"
    if "MEETING" in provider or "VISIT" in provider or provider_type == "MEETING":
        return "meeting"
    if provider == "CRM_TODO" or provider_type == "TODO":
        return "meeting"
    if "TASK" in provider or "TASK" in provider_type:
        return "task"
    if "WEBFORM" in provider:
        return "other"
    return {"1": "meeting", "2": "call", "4": "email"}.get(str(item.get("TYPE_ID") or ""), "other")


def plain(text: str | None, limit: int = 80) -> str:
    cleaned = BB_RE.sub("", text or "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:limit] if cleaned else ""


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def title_for(kind: str, text: str | None, fallback: str) -> str:
    labels = {
        "comment": "Yorum",
        "whatsapp_message": "WhatsApp",
        "whatsapp_session": "WhatsApp / Open Channel",
        "sms": "SMS",
        "call": "Arama",
        "email": "E-posta",
        "meeting": "Toplantı",
        "task": "Görev",
        "other": "CRM aktivitesi",
    }
    snippet = plain(text, 72)
    base = labels.get(kind, fallback)
    if snippet and kind in {"whatsapp_message", "comment", "sms", "email"}:
        return f"{base}: {snippet}"[:500]
    return (snippet or base)[:500]


def extract_file_ids(obj: Any, found: set[str] | None = None) -> set[str]:
    found = found if found is not None else set()
    if isinstance(obj, dict):
        for key in ("id", "ID", "FILE_ID", "fileId"):
            val = obj.get(key)
            if val not in (None, "", [], {}, 0, "0") and str(val).lstrip("n").isdigit():
                found.add(str(val).lstrip("n"))
        if obj.get("url") or obj.get("DOWNLOAD_URL"):
            fid = obj.get("id") or obj.get("ID")
            if fid:
                found.add(str(fid).lstrip("n"))
        for value in obj.values():
            extract_file_ids(value, found)
    elif isinstance(obj, list):
        for item in obj:
            extract_file_ids(item, found)
    elif isinstance(obj, str):
        for match in DISK_FILE_RE.findall(obj):
            found.add(match)
    return found


def slim_entity(rec: dict) -> dict:
    keep = {
        "ID", "TITLE", "NAME", "LAST_NAME", "SECOND_NAME", "POST", "COMMENTS", "STAGE_ID",
        "STATUS_ID", "OPPORTUNITY", "CURRENCY_ID", "BEGINDATE", "CLOSEDATE", "ASSIGNED_BY_ID",
        "CONTACT_ID", "COMPANY_ID", "SOURCE_ID", "TYPE_ID", "CLOSED", "CATEGORY_ID",
        "ADDRESS", "ADDRESS_2", "ADDRESS_CITY", "ADDRESS_POSTAL_CODE", "ADDRESS_REGION",
        "ADDRESS_PROVINCE", "ADDRESS_COUNTRY", "PHONE", "EMAIL", "HAS_IMOL", "BIRTHDATE",
    }
    out = {k: rec.get(k) for k in keep if k in rec}
    for key, value in rec.items():
        if str(key).startswith("UF_") and value not in (None, "", [], {}):
            out[key] = value
    return out


def load_people(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            select c.id::text as cid, c.display_name, c.first_name, c.last_name, c.primary_phone,
                   c.secondary_phones, c.primary_email, c.secondary_emails, c.organization_name,
                   c.job_title, c.address_line1, c.city, c.postal_code, c.country, c.source,
                   c.junk_reason, c.notes, c.metadata_json, c.status
            from crm_contacts c
            where c.id in (select distinct contact_id from crm_agreements)
            order by c.display_name
            """
        )
    ).mappings().all()
    people = []
    for row in rows:
        rec = dict(row)
        rec["agreements"] = [dict(a) for a in db.execute(
            text(
                """
                select id::text, project_group, status, unit_number, investment_amount,
                       agreement_date::text, source_external_id, review_required, metadata_json
                from crm_agreements where contact_id = cast(:cid as uuid)
                """
            ),
            {"cid": rec["cid"]},
        ).mappings().all()]
        rec["crm_history"] = db.execute(
            text(
                """
                select count(*) from crm_activities
                where entity_id=cast(:cid as uuid) and archived_at is null
                  and entity_type in ('contact', 'CONTACT')
                """
            ),
            {"cid": rec["cid"]},
        ).scalar() or 0
        rec["crm_docs"] = db.execute(
            text(
                """
                select count(distinct d.id)
                from document_links l join documents d on d.id=l.document_id
                where l.entity_id=cast(:cid as uuid) and d.archived_at is null
                """
            ),
            {"cid": rec["cid"]},
        ).scalar() or 0
        rec["import_keys"] = set()
        for key_row in db.execute(
            text("select metadata_json from crm_activities where entity_id=cast(:cid as uuid)"),
            {"cid": rec["cid"]},
        ).all():
            meta = key_row[0] if key_row else {}
            if not isinstance(meta, dict):
                continue
            for bucket in (HISTORY_KEY, "bitrix_historical_comment"):
                hist = meta.get(bucket)
                if isinstance(hist, dict) and hist.get("import_key"):
                    rec["import_keys"] |= import_key_aliases(str(hist["import_key"]))
                if isinstance(hist, dict) and hist.get("bitrix_record_id"):
                    kind = str(hist.get("kind") or bucket)
                    rec["import_keys"] |= import_key_aliases(f"bitrix:{kind}:{hist['bitrix_record_id']}")
                    if hist.get("chat_id") and hist.get("bitrix_record_id"):
                        rec["import_keys"] |= import_key_aliases(
                            f"bitrix:wa:{hist['chat_id']}:{hist['bitrix_record_id']}"
                        )
        people.append(rec)
    return people


def resolve_live(client: BitrixClient, person: dict) -> dict:
    cid = person["cid"]
    review: list[str] = []
    phones = [person.get("primary_phone") or ""]
    phones.extend(person.get("secondary_phones") or [])
    emails = [normalize_valid_email(person.get("primary_email") or "") or ""]
    emails.extend(normalize_valid_email(e) or "" for e in (person.get("secondary_emails") or []))
    pkeys = set()
    for phone in phones:
        pkeys |= phone_keys(phone)
    emails = [e for e in emails if e]
    seed = SEED_IDS.get(cid, {})
    contact_ids: dict[str, str] = {}
    lead_ids: dict[str, str] = {}

    def consider(etype: str, rec: dict, how: str) -> None:
        eid = str(rec.get("ID") or "")
        if not eid:
            return
        rec_phones = set()
        for value in phones_of(rec):
            rec_phones |= phone_keys(value)
        rec_emails = set(emails_of(rec))
        phone_ok = bool(pkeys and rec_phones and (pkeys & rec_phones))
        email_ok = bool(emails and rec_emails and (set(emails) & rec_emails))
        seeded = eid in (seed.get(etype) or [])
        if not (phone_ok or email_ok or seeded):
            return
        target = contact_ids if etype == "contact" else lead_ids
        if eid not in target:
            target[eid] = how if not seeded else f"{how}+seed"

    select = ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "CONTACT_ID"]
    seen = set()
    for phone in list(pkeys)[:6]:
        for etype, method in (("CONTACT", "crm.duplicate.findbycomm"),):
            key = ("dup", etype, phone)
            if key in seen:
                continue
            seen.add(key)
            body = client.call("crm.duplicate.findbycomm", {"entity_type": etype, "type": "PHONE", "values[]": [phone]})
            ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
            for item_id in ids or []:
                got = client.call("crm.contact.get", {"id": item_id})
                rec = got.get("result") if isinstance(got.get("result"), dict) else {}
                consider("contact", rec, "duplicate_phone")
        body = client.call("crm.contact.list", {"filter[PHONE]": phone, "select[]": select, "start": 0})
        for rec in body.get("result") or []:
            if isinstance(rec, dict):
                consider("contact", rec, "list_phone")
        body = client.call("crm.lead.list", {"filter[PHONE]": phone, "select[]": select, "start": 0})
        for rec in body.get("result") or []:
            if isinstance(rec, dict):
                consider("lead", rec, "list_phone")
    for email in emails[:4]:
        body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "EMAIL", "values[]": [email]})
        ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
        for item_id in ids or []:
            got = client.call("crm.contact.get", {"id": item_id})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider("contact", rec, "duplicate_email")
        body = client.call("crm.contact.list", {"filter[EMAIL]": email, "select[]": select, "start": 0})
        for rec in body.get("result") or []:
            if isinstance(rec, dict):
                consider("contact", rec, "list_email")
        body = client.call("crm.lead.list", {"filter[EMAIL]": email, "select[]": select, "start": 0})
        for rec in body.get("result") or []:
            if isinstance(rec, dict):
                consider("lead", rec, "list_email")
    for eid in seed.get("contact") or []:
        if eid not in contact_ids:
            got = client.call("crm.contact.get", {"id": eid})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider("contact", rec, "seed")
    for eid in seed.get("lead") or []:
        if eid not in lead_ids:
            got = client.call("crm.lead.get", {"id": eid})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider("lead", rec, "seed")

    if len(contact_ids) > 1:
        review.append("multiple_live_contacts:" + ",".join(sorted(contact_ids)))
    contacts: dict[str, dict] = {}
    for eid, how in contact_ids.items():
        got = client.call("crm.contact.get", {"id": eid})
        rec = got.get("result") if isinstance(got.get("result"), dict) else {}
        if rec:
            rec["_how"] = how
            contacts[eid] = rec
            extra = client.call("crm.lead.list", flatten({"filter": {"CONTACT_ID": eid}, "select": select}))
            for item in extra.get("result") or []:
                if isinstance(item, dict):
                    consider("lead", item, "lead_contact_id")
                    lead_ids[str(item.get("ID"))] = "lead_contact_id"
    leads: dict[str, dict] = {}
    for eid, how in lead_ids.items():
        got = client.call("crm.lead.get", {"id": eid})
        rec = got.get("result") if isinstance(got.get("result"), dict) else {}
        if rec:
            rec["_how"] = how
            leads[eid] = rec
            linked = str(rec.get("CONTACT_ID") or "")
            if linked and linked not in contacts:
                gotc = client.call("crm.contact.get", {"id": linked})
                crec = gotc.get("result") if isinstance(gotc.get("result"), dict) else {}
                if crec:
                    consider("contact", crec, "lead_linked_contact")
                    if str(crec.get("ID")) in contact_ids or (pkeys & set().union(*[phone_keys(p) for p in phones_of(crec)])) or (set(emails) & set(emails_of(crec))):
                        crec["_how"] = "lead_linked_contact"
                        contacts[str(crec.get("ID"))] = crec
    deals: dict[str, dict] = {}
    for eid in list(contacts):
        rows = list_all(client, "crm.deal.list", {"filter": {"CONTACT_ID": eid}})
        for rec in rows:
            did = str(rec.get("ID") or "")
            if not did:
                continue
            full = client.call("crm.deal.get", {"id": did})
            payload = full.get("result") if isinstance(full.get("result"), dict) else rec
            payload["_how"] = "deal_contact_id"
            deals[did] = payload
    if not contacts:
        review.append("no_verified_bitrix_contact")
    return {
        "contacts": {k: slim_entity(v) | {"_how": v.get("_how")} for k, v in contacts.items()},
        "leads": {k: slim_entity(v) | {"_how": v.get("_how")} for k, v in leads.items()},
        "deals": {k: slim_entity(v) | {"_how": v.get("_how"), "_title": v.get("TITLE")} for k, v in deals.items()},
        "review": review,
        "raw_contacts": contacts,
        "raw_leads": leads,
        "raw_deals": deals,
    }


def fetch_history(client: BitrixClient, mapping: dict) -> dict:
    comments: dict[str, dict] = {}
    activities: dict[str, dict] = {}
    chats: list[dict] = []
    messages: list[dict] = []
    files: dict[str, dict] = {}

    def add_files(source_type: str, source_id: str, entity_type: str, entity_id: str, blob: Any, name: str = "") -> None:
        for fid in extract_file_ids(blob):
            files.setdefault(
                fid,
                {
                    "bitrix_file_id": fid,
                    "source_type": source_type,
                    "source_record_id": source_id,
                    "bitrix_entity_type": entity_type,
                    "bitrix_entity_id": entity_id,
                    "original_filename": name,
                },
            )

    entities = [("contact", eid) for eid in mapping["contacts"]] + [("lead", eid) for eid in mapping["leads"]] + [("deal", eid) for eid in mapping["deals"]]
    for etype, eid in entities:
        rows = list_all(client, "crm.timeline.comment.list", {"filter": {"ENTITY_TYPE": etype, "ENTITY_ID": eid}})
        for row in rows:
            cid = str(row.get("ID") or "")
            if cid:
                comments.setdefault(cid, {**row, "_entity_type": etype, "_entity_id": eid})
                add_files("comment", cid, etype, eid, row)
        owner = OWNER_TYPE[etype]
        acts = list_all(
            client,
            "crm.activity.list",
            {"filter": {"OWNER_TYPE_ID": owner, "OWNER_ID": eid}},
        )
        for row in acts:
            aid = str(row.get("ID") or "")
            if aid:
                activities.setdefault(aid, {**row, "_entity_type": etype, "_entity_id": eid})
                add_files("activity", aid, etype, eid, row.get("FILES") or row, str(row.get("SUBJECT") or ""))
        if etype in {"contact", "lead"}:
            oc = client.call(
                "imopenlines.crm.chat.get",
                {"CRM_ENTITY_TYPE": etype.upper(), "CRM_ENTITY": eid, "ACTIVE_ONLY": "N"},
            )
            oc_list = oc.get("result") if isinstance(oc.get("result"), list) else []
            for item in oc_list:
                if not isinstance(item, dict):
                    continue
                chat_id = str(item.get("CHAT_ID") or "")
                if not chat_id:
                    continue
                chats.append({**item, "_entity_type": etype, "_entity_id": eid})
                last = None
                for _ in range(80):
                    params: dict[str, Any] = {"DIALOG_ID": f"chat{chat_id}", "LIMIT": 50}
                    if last:
                        params["LAST_ID"] = last
                    body = client.call("im.dialog.messages.get", params)
                    result = body.get("result") if isinstance(body.get("result"), dict) else {}
                    batch = result.get("messages") or []
                    if not batch:
                        break
                    ids = []
                    for msg in batch:
                        mid = str(msg.get("id") or "")
                        ids.append(int(mid) if mid.isdigit() else 0)
                        messages.append({**msg, "chat_id": chat_id, "_entity_type": etype, "_entity_id": eid})
                        add_files("whatsapp", mid, etype, eid, msg)
                    nxt = min(i for i in ids if i) if any(ids) else None
                    if not nxt or nxt == last:
                        break
                    last = nxt
    return {
        "comments": list(comments.values()),
        "activities": list(activities.values()),
        "chats": chats,
        "messages": messages,
        "files": list(files.values()),
        "live_history_count": len(comments) + len(activities) + len(messages),
    }


def person_safe_adds(os_row: dict, contact: dict) -> tuple[dict, list[str], list[str]]:
    adds: dict[str, Any] = {}
    conflicts: list[str] = []
    notes: list[str] = []
    bitrix_name = " ".join(p for p in [contact.get("NAME"), contact.get("LAST_NAME")] if p).strip()
    if bitrix_name and os_row.get("display_name") and collapse_ws(bitrix_name).casefold() != collapse_ws(os_row["display_name"]).casefold():
        conflicts.append(f"display_name OS={os_row['display_name']} Bitrix={bitrix_name}")
    if not os_row.get("first_name") and contact.get("NAME"):
        adds["first_name"] = str(contact["NAME"]).strip()
    if not os_row.get("last_name") and contact.get("LAST_NAME"):
        adds["last_name"] = str(contact["LAST_NAME"]).strip()
    if not os_row.get("job_title") and contact.get("POST"):
        adds["job_title"] = str(contact["POST"]).strip()
    if not os_row.get("address_line1") and contact.get("ADDRESS"):
        adds["address_line1"] = str(contact["ADDRESS"]).strip()
    if not os_row.get("city") and contact.get("ADDRESS_CITY"):
        adds["city"] = str(contact["ADDRESS_CITY"]).strip()
    if not os_row.get("postal_code") and contact.get("ADDRESS_POSTAL_CODE"):
        adds["postal_code"] = str(contact["ADDRESS_POSTAL_CODE"]).strip()
    if not os_row.get("country") and contact.get("ADDRESS_COUNTRY"):
        adds["country"] = str(contact["ADDRESS_COUNTRY"]).strip()
    if not os_row.get("notes") and contact.get("COMMENTS"):
        adds["notes"] = str(contact["COMMENTS"]).strip()[:8000]
    if not os_row.get("junk_reason"):
        pass
    extra_phones = []
    os_keys = phone_keys(os_row.get("primary_phone"))
    for p in os_row.get("secondary_phones") or []:
        os_keys |= phone_keys(p)
    for phone in phones_of(contact):
        if phone_keys(phone) and not (phone_keys(phone) & os_keys):
            extra_phones.append(phone)
    if extra_phones:
        adds["secondary_phones_add"] = extra_phones
    extra_emails = []
    os_emails = {normalize_valid_email(os_row.get("primary_email") or "") or ""}
    os_emails.update(normalize_valid_email(e) or "" for e in (os_row.get("secondary_emails") or []))
    os_emails.discard("")
    for email in emails_of(contact):
        if email not in os_emails:
            extra_emails.append(email)
    if extra_emails:
        adds["secondary_emails_add"] = extra_emails
    if adds:
        notes.append("safe_add_blank_or_extra_identity_fields")
    return adds, conflicts, notes


def deal_tutar(deal: dict) -> dict:
    amount = deal.get("OPPORTUNITY")
    currency = deal.get("CURRENCY_ID")
    return {
        "bitrix_field_id": TUTAR_FIELD_ID,
        "bitrix_field_ids": ["OPPORTUNITY", "CURRENCY_ID"],
        "bitrix_field_label": TUTAR_LABEL,
        "bitrix_api_labels": {"OPPORTUNITY": "Total", "CURRENCY_ID": "Currency"},
        "amount": str(amount) if amount not in (None, "") else "",
        "currency": str(currency or ""),
        "deal_id": str(deal.get("ID") or ""),
        "not_amount_paid": True,
    }


def planned_history(person: dict, hist: dict) -> list[dict]:
    plans = []
    seen = set(person.get("import_keys") or set())
    cid = person["cid"]

    def add(import_key: str, kind: str, title: str, description: str, occurred: Any, extra: dict) -> None:
        aliases = import_key_aliases(import_key)
        if seen & aliases:
            return
        seen.update(aliases)
        plans.append(
            {
                "import_key": import_key,
                "kind": kind,
                "title": title,
                "description": description,
                "occurred": occurred,
                "metadata": {HISTORY_KEY: {"import_key": import_key, "source": "bitrix_live", "kind": kind, **extra}},
                "contact_id": cid,
            }
        )

    for comment in hist.get("comments") or []:
        cid_b = str(comment.get("ID") or "")
        text = str(comment.get("COMMENT") or comment.get("TEXT") or "")
        add(
            f"bitrix:comment:{cid_b}",
            "comment",
            title_for("comment", text, "Yorum"),
            text,
            comment.get("CREATED") or comment.get("DATE_CREATE"),
            {
                "bitrix_entity_type": comment.get("_entity_type"),
                "bitrix_entity_id": comment.get("_entity_id"),
                "bitrix_record_id": cid_b,
                "author_id": str(comment.get("AUTHOR_ID") or ""),
            },
        )
    for act in hist.get("activities") or []:
        aid = str(act.get("ID") or "")
        kind = classify_activity(act)
        add(
            f"bitrix:activity:{aid}",
            kind,
            title_for(kind, str(act.get("SUBJECT") or act.get("DESCRIPTION") or ""), "CRM aktivitesi"),
            str(act.get("DESCRIPTION") or act.get("SUBJECT") or ""),
            act.get("CREATED") or act.get("START_TIME") or act.get("LAST_UPDATED"),
            {
                "bitrix_entity_type": act.get("_entity_type"),
                "bitrix_entity_id": act.get("_entity_id"),
                "bitrix_record_id": aid,
                "provider": act.get("PROVIDER_ID"),
            },
        )
    for msg in hist.get("messages") or []:
        mid = str(msg.get("id") or "")
        chat_id = str(msg.get("chat_id") or "")
        text = str(msg.get("text") or "")
        add(
            f"bitrix:whatsapp:{chat_id}:{mid}",
            "whatsapp_message",
            title_for("whatsapp_message", text, "WhatsApp"),
            text,
            msg.get("date"),
            {
                "bitrix_entity_type": msg.get("_entity_type"),
                "bitrix_entity_id": msg.get("_entity_id"),
                "bitrix_record_id": mid,
                "chat_id": chat_id,
                "author_id": str(msg.get("author_id") or ""),
            },
        )
    return plans


def deal_snapshot(deal_id: str, deal: dict) -> dict:
    snap = {
        "ID": deal_id,
        "TITLE": deal.get("TITLE") or deal.get("_title"),
        "STAGE_ID": deal.get("STAGE_ID"),
        "STATUS_ID": deal.get("STATUS_ID"),
        "OPPORTUNITY": deal.get("OPPORTUNITY"),
        "CURRENCY_ID": deal.get("CURRENCY_ID"),
        "BEGINDATE": deal.get("BEGINDATE"),
        "ASSIGNED_BY_ID": deal.get("ASSIGNED_BY_ID"),
        "CLOSED": deal.get("CLOSED"),
    }
    for key, value in deal.items():
        if str(key).startswith("UF_") and value not in (None, "", [], {}):
            snap[key] = value
    return snap


def attach_tutar(ag, deal_id: str, deal: dict, tutar: dict) -> None:
    ag_meta = dict(ag.metadata_json or {})
    ag_meta["bitrix_deal_id"] = deal_id
    ag_meta["bitrix_deal_title"] = deal.get("TITLE") or deal.get("_title")
    ag_meta["bitrix_deal_stage"] = deal.get("STAGE_ID")
    ag_meta["tutar_ve_para_birimi_label"] = TUTAR_LABEL
    ag_meta["tutar_ve_para_birimi_field_id"] = TUTAR_FIELD_ID
    ag_meta["tutar_ve_para_birimi_amount"] = tutar.get("amount")
    ag_meta["tutar_ve_para_birimi_currency"] = tutar.get("currency")
    ag_meta["bitrix_deal_snapshot"] = deal_snapshot(deal_id, deal)
    ag.metadata_json = ag_meta
    flag_modified(ag, "metadata_json")


def match_deals_to_agreements(agreements: list, deals: dict) -> list[tuple]:
    matched = []
    used_deals: set[str] = set()
    used_ags: set[str] = set()
    if len(deals) == 1 and len(agreements) == 1:
        did = next(iter(deals))
        return [(agreements[0], did, deals[did])]
    for ag in agreements:
        unit = collapse_ws(str(ag.unit_number or ""))
        if not unit:
            continue
        hits = []
        for did, deal in deals.items():
            title = collapse_ws(str(deal.get("TITLE") or deal.get("_title") or ""))
            if unit and unit in title:
                hits.append(did)
        if len(hits) == 1 and hits[0] not in used_deals:
            used_deals.add(hits[0])
            used_ags.add(str(ag.id))
            matched.append((ag, hits[0], deals[hits[0]]))
    return matched


def fetch_disk_file(client: BitrixClient, file_id: str, cache: dict) -> tuple[bytes | None, str | None, str | None, str | None]:
    if file_id in cache:
        return cache[file_id]
    disk = client.call("disk.file.get", {"id": file_id})
    payload = disk.get("result") if isinstance(disk.get("result"), dict) else {}
    url = payload.get("DOWNLOAD_URL") or payload.get("downloadUrl") if payload else None
    content = filename = mime = err = None
    if url:
        content, mime, err = client.download(str(url))
        filename = payload.get("NAME") or payload.get("name")
    if not content:
        err = err or disk.get("error") or disk.get("error_description") or "download_failed"
    cache[file_id] = (content, filename, mime, str(err) if err else None)
    return cache[file_id]


def apply_person(
    db: Session,
    actor: User | None,
    person: dict,
    mapping: dict,
    hist: dict,
    adds: dict,
    apply_docs: bool,
    client: BitrixClient,
    disk_cache: dict | None = None,
) -> dict:
    result = {"ids": False, "fields": 0, "history": 0, "docs": 0, "docs_skipped": 0, "tutar": 0, "errors": [], "inaccessible": []}
    contact = db.get(CrmContact, UUID(person["cid"]))
    if contact is None:
        result["errors"].append("contact_missing")
        return result
    meta = dict(contact.metadata_json or {})
    live = dict(meta.get("bitrix_live") or {})
    old_contact_ids = [str(x) for x in (live.get("contact_ids") or [])]
    old_lead_ids = [str(x) for x in (live.get("lead_ids") or [])]
    old_deal_ids = [str(x) for x in (live.get("deal_ids") or [])]
    live.update(
        {
            "contact_ids": sorted(mapping["contacts"]),
            "lead_ids": sorted(mapping["leads"]),
            "deal_ids": sorted(mapping["deals"]),
            "how": {
                "contacts": {k: v.get("_how") for k, v in mapping["contacts"].items()},
                "leads": {k: v.get("_how") for k, v in mapping["leads"].items()},
                "deals": {k: v.get("_how") for k, v in mapping["deals"].items()},
            },
            "updated_at": utc_now(),
        }
    )
    bitrix_imp = dict(meta.get("bitrix_import") or {})
    ext = list(bitrix_imp.get("external_ids") or [])
    for eid in mapping["contacts"]:
        token = f"bitrix_contact:{eid}"
        if token not in ext:
            ext.append(token)
    for eid in mapping["leads"]:
        token = f"bitrix_lead:{eid}"
        if token not in ext:
            ext.append(token)
    bitrix_imp["external_ids"] = ext
    meta["bitrix_import"] = bitrix_imp
    meta["bitrix_live"] = live
    contact.metadata_json = meta
    flag_modified(contact, "metadata_json")
    result["ids"] = True
    result["ids_changed"] = (
        old_contact_ids != sorted(mapping["contacts"])
        or old_lead_ids != sorted(mapping["leads"])
        or old_deal_ids != sorted(mapping["deals"])
        or not old_contact_ids
    )
    if adds.get("first_name"):
        contact.first_name = adds["first_name"]
        result["fields"] += 1
    if adds.get("last_name"):
        contact.last_name = adds["last_name"]
        result["fields"] += 1
    if adds.get("job_title"):
        contact.job_title = adds["job_title"]
        result["fields"] += 1
    if adds.get("address_line1"):
        contact.address_line1 = adds["address_line1"]
        result["fields"] += 1
    if adds.get("city"):
        contact.city = adds["city"]
        result["fields"] += 1
    if adds.get("postal_code"):
        contact.postal_code = adds["postal_code"]
        result["fields"] += 1
    if adds.get("country"):
        contact.country = adds["country"]
        result["fields"] += 1
    if adds.get("notes"):
        contact.notes = adds["notes"]
        result["fields"] += 1
    if adds.get("secondary_phones_add"):
        current = list(contact.secondary_phones or [])
        current.extend(adds["secondary_phones_add"])
        contact.secondary_phones = current
        result["fields"] += 1
    if adds.get("secondary_emails_add"):
        current = list(contact.secondary_emails or [])
        current.extend(adds["secondary_emails_add"])
        contact.secondary_emails = current
        result["fields"] += 1
    actor_id = actor.id if actor else None
    for plan in planned_history(person, hist):
        kind = plan["kind"]
        activity_type, category = TYPE_MAP.get(kind, TYPE_MAP["other"])
        occurred = parse_dt(plan["occurred"])
        db.add(
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=UUID(person["cid"]),
                activity_type=activity_type,
                activity_category=category,
                title=plan["title"][:500],
                summary=(plan["description"] or "")[:1000] if plan["description"] else None,
                description=plan["description"],
                status=CrmActivityStatus.COMPLETED,
                task_status=CrmTaskStatus.COMPLETED if kind == "task" else None,
                priority=CrmActivityPriority.MEDIUM,
                visibility=CrmActivityVisibility.ORGANIZATION,
                start_date=occurred,
                completed_at=occurred,
                created_at=occurred or datetime.now(timezone.utc),
                updated_at=occurred or datetime.now(timezone.utc),
                created_by=actor_id,
                updated_by=actor_id,
                metadata_json=plan["metadata"],
            )
        )
        result["history"] += 1
        person["import_keys"] |= import_key_aliases(plan["import_key"])
    deals = mapping["deals"]
    tutars = [deal_tutar({**d, "ID": did}) for did, d in deals.items()]
    live["tutar_ve_para_birimi"] = tutars
    meta["bitrix_live"] = live
    contact.metadata_json = meta
    flag_modified(contact, "metadata_json")
    agreements = db.query(CrmAgreement).filter(CrmAgreement.contact_id == UUID(person["cid"])).all()
    paired = match_deals_to_agreements(agreements, deals)
    paired_ags = {str(ag.id) for ag, _, _ in paired}
    for ag, deal_id, deal in paired:
        attach_tutar(ag, deal_id, deal, deal_tutar({**deal, "ID": deal_id}))
        result["tutar"] += 1
    if len(tutars) == 1:
        for ag in agreements:
            if str(ag.id) in paired_ags:
                continue
            ag_meta = dict(ag.metadata_json or {})
            if ag_meta.get("tutar_ve_para_birimi_amount"):
                continue
            did = next(iter(deals))
            attach_tutar(ag, did, deals[did], tutars[0])
            result["tutar"] += 1
    inaccessible: list[dict] = []
    result["docs_skipped"] = 0
    if apply_docs:
        folder = DOCS_OUT / "by_contact" / person["cid"]
        folder.mkdir(parents=True, exist_ok=True)
        cache = disk_cache if disk_cache is not None else {}
        seen_files: set[str] = set()
        actor_row = actor or db.query(User).first()
        for src in hist.get("files") or []:
            src = dict(src)
            src["canonical_crm_contact_id"] = person["cid"]
            file_id = str(src.get("bitrix_file_id") or "")
            if not file_id or file_id in seen_files:
                continue
            seen_files.add(file_id)
            tag = import_tag(person["cid"], file_id)
            existing = existing_document(db, tag)
            if existing:
                uid = UUID(person["cid"])
                created = 0
                for entity_type in ("crm_contact", "contact"):
                    if not link_exists(db, existing.id, entity_type, uid):
                        db.add(
                            DocumentLink(
                                document_id=existing.id,
                                entity_type=entity_type,
                                entity_id=uid,
                                relationship_type="bitrix_source",
                            )
                        )
                        created += 1
                if created:
                    result["docs"] += 1
                else:
                    result["docs_skipped"] += 1
                continue
            content, filename, mime, err = fetch_disk_file(client, file_id, cache)
            if not content:
                inaccessible.append(
                    {
                        "person": person.get("display_name"),
                        "canonical_uuid": person["cid"],
                        "bitrix_file_id": file_id,
                        "source_type": src.get("source_type"),
                        "source_record_id": src.get("source_record_id"),
                        "bitrix_entity_type": src.get("bitrix_entity_type"),
                        "bitrix_entity_id": src.get("bitrix_entity_id"),
                        "reason": err or "download_failed",
                    }
                )
                continue
            src["original_filename"] = filename or src.get("original_filename") or f"bitrix-file-{file_id}"
            src["mime_type"] = mime_of(src.get("original_filename"), mime, content)
            dest = unique_dest(folder, src["original_filename"], file_id)
            dest.write_bytes(content)
            imported, _doc_id, reason = import_document(db, actor_row, src, content, str(dest))
            if imported == "yes":
                result["docs"] += 1
            elif imported == "skipped_duplicate":
                result["docs_skipped"] += 1
            elif imported == "no" and reason:
                inaccessible.append(
                    {
                        "person": person.get("display_name"),
                        "canonical_uuid": person["cid"],
                        "bitrix_file_id": file_id,
                        "source_type": src.get("source_type"),
                        "source_record_id": src.get("source_record_id"),
                        "bitrix_entity_type": src.get("bitrix_entity_type"),
                        "bitrix_entity_id": src.get("bitrix_entity_id"),
                        "reason": reason,
                    }
                )
    result["inaccessible"] = inaccessible
    return result


def temple_summary(all_deals: list[dict], os_temple: list[dict]) -> dict:
    live = []
    for deal in all_deals:
        title = str(deal.get("TITLE") or deal.get("_title") or "")
        blob = " ".join([title, str(deal.get("STAGE_ID") or ""), json.dumps(deal, ensure_ascii=False, default=str)[:2000]])
        if TEMPLE_RE.search(blob):
            stage = str(deal.get("STAGE_ID") or "")
            closed = str(deal.get("CLOSED") or "")
            status = "lost" if "LOSE" in stage.upper() or stage.upper().endswith(":LOSE") else ("won" if "WON" in stage.upper() or closed == "Y" else "active")
            live.append(
                {
                    "deal_id": str(deal.get("ID") or ""),
                    "title": title,
                    "stage": stage,
                    "status": status,
                    "opportunity": deal.get("OPPORTUNITY"),
                    "currency": deal.get("CURRENCY_ID"),
                    "contact_id": deal.get("CONTACT_ID"),
                }
            )
    os_ids = {str((a.get("metadata_json") or {}).get("bitrix_deal_id") or "") for a in os_temple}
    os_ids.discard("")
    missing = [d for d in live if d["deal_id"] not in os_ids]
    counts = Counter(d["deal_id"] for d in live)
    duplicate = [d for d in live if counts[d["deal_id"]] > 1]
    review = []
    if missing:
        review.append("bitrix_temple_deals_not_in_os")
    if duplicate:
        review.append("duplicate_live_temple_deals")
    if len(os_temple) != len({d["deal_id"] for d in live}):
        review.append("os_live_temple_count_mismatch")
    return {
        "existing_os_agreements": [
            {"id": a.get("id"), "contact": a.get("display_name"), "source_external_id": a.get("source_external_id"), "unit": a.get("unit_number")}
            for a in os_temple
        ],
        "live_temple_deals": live,
        "bitrix_deals_missing_from_os": missing,
        "won_or_active": [d for d in live if d["status"] in {"won", "active"}],
        "lost": [d for d in live if d["status"] == "lost"],
        "duplicate": duplicate,
        "review_required": review,
        "note": "No new OS agreements created. Excel row IDs were not treated as Bitrix deal IDs.",
    }


def fetch_live_temple_deals(client: BitrixClient) -> list[dict]:
    found: dict[str, dict] = {}
    for term in ("%Temple%", "%The Temple%"):
        start = 0
        while True:
            body = client.call(
                "crm.deal.list",
                {
                    "filter[TITLE]": term,
                    "select[]": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "CLOSED", "BEGINDATE"],
                    "start": start,
                },
            )
            rows = body.get("result") or []
            for rec in rows:
                if isinstance(rec, dict) and rec.get("ID"):
                    found[str(rec["ID"])] = rec
            nxt = body.get("next")
            if nxt is None or not rows:
                break
            start = int(nxt)
    return list(found.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    apply = args.apply
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    db = SessionLocal()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    people = load_people(db)
    actor = db.query(User).order_by(User.created_at.asc()).first()
    rows = []
    totals = Counter()
    all_deals = []
    inaccessible = []
    conflicts = []
    eda = {}
    disk_cache: dict[str, tuple] = {}
    try:
        for index, person in enumerate(people, start=1):
            print(f"[{index}/{len(people)}] {person['display_name']}", flush=True)
            snap_path = OUT / "raw" / f"{person['cid']}.json"
            if snap_path.exists() and apply:
                snap = json.loads(snap_path.read_text(encoding="utf-8"))
                mapping = snap["mapping"]
                hist = snap["history"]
            else:
                mapping = resolve_live(client, person)
                hist = fetch_history(client, mapping) if mapping["contacts"] or mapping["leads"] else {
                    "comments": [], "activities": [], "chats": [], "messages": [], "files": [], "live_history_count": 0
                }
                snap = {
                    "person": {k: person[k] for k in ("cid", "display_name", "primary_phone", "primary_email") if k in person},
                    "mapping": {
                        "contacts": mapping["contacts"],
                        "leads": mapping["leads"],
                        "deals": mapping["deals"],
                        "review": mapping["review"],
                    },
                    "history": {
                        "comments": hist["comments"],
                        "activities": hist["activities"],
                        "chats": hist["chats"],
                        "messages": hist["messages"],
                        "files": hist["files"],
                        "live_history_count": hist["live_history_count"],
                    },
                }
                # keep raw for apply tutar/safe-add
                snap["mapping"]["raw_contacts"] = {k: slim_entity(v) | {"_how": v.get("_how"), "NAME": v.get("NAME"), "LAST_NAME": v.get("LAST_NAME"), "POST": v.get("POST"), "PHONE": v.get("PHONE"), "EMAIL": v.get("EMAIL"), "ADDRESS": v.get("ADDRESS"), "ADDRESS_CITY": v.get("ADDRESS_CITY"), "ADDRESS_POSTAL_CODE": v.get("ADDRESS_POSTAL_CODE"), "ADDRESS_COUNTRY": v.get("ADDRESS_COUNTRY"), "COMMENTS": v.get("COMMENTS")} for k, v in mapping.get("raw_contacts", {}).items()}
                snap_path.write_text(json.dumps(snap, ensure_ascii=False, default=str), encoding="utf-8")
            primary_contact = {}
            contacts_map = snap["mapping"].get("raw_contacts") or snap["mapping"]["contacts"]
            if len(contacts_map) == 1:
                primary_contact = next(iter(contacts_map.values()))
            elif EDA_UUID == person["cid"] and "1128" in contacts_map:
                primary_contact = contacts_map["1128"]
            elif contacts_map:
                primary_contact = next(iter(contacts_map.values()))
                review = list(snap["mapping"].get("review") or [])
                if "multiple_or_first_contact_used" not in review:
                    review.append("multiple_or_first_contact_used")
                snap["mapping"]["review"] = review
            adds, person_conflicts, _notes = person_safe_adds(person, primary_contact)
            if len(contacts_map) > 1 or person_conflicts:
                for key in ("first_name", "last_name", "notes"):
                    adds.pop(key, None)
            plans = planned_history(person, snap["history"])
            tutars = [deal_tutar(d) for d in snap["mapping"]["deals"].values()]
            for deal in snap["mapping"]["deals"].values():
                all_deals.append(deal)
            live_files = snap["history"].get("files") or []
            apply_result = {}
            if apply and (snap["mapping"]["contacts"] or snap["mapping"]["leads"]):
                mapping_apply = {
                    "contacts": snap["mapping"]["contacts"],
                    "leads": snap["mapping"]["leads"],
                    "deals": snap["mapping"]["deals"],
                    "raw_deals": snap["mapping"]["deals"],
                    "review": snap["mapping"].get("review") or [],
                }
                apply_result = apply_person(
                    db, actor, person, mapping_apply, snap["history"], adds, True, client, disk_cache
                )
                db.commit()
            elif apply:
                db.commit()
            person_inacc = apply_result.get("inaccessible") or []
            inaccessible.extend(person_inacc)
            crm_history_after = person["crm_history"] + (apply_result.get("history") or 0 if apply else 0)
            crm_docs_after = person["crm_docs"]
            if apply:
                crm_history_after = db.execute(
                    text(
                        """
                        select count(*) from crm_activities
                        where entity_id=cast(:cid as uuid) and archived_at is null
                          and entity_type in ('contact', 'CONTACT')
                        """
                    ),
                    {"cid": person["cid"]},
                ).scalar() or 0
                crm_docs_after = db.execute(
                    text(
                        """
                        select count(distinct d.id)
                        from document_links l join documents d on d.id=l.document_id
                        where l.entity_id=cast(:cid as uuid) and d.archived_at is null
                        """
                    ),
                    {"cid": person["cid"]},
                ).scalar() or 0
            live_h = snap["history"].get("live_history_count") or 0
            if live_h == 0:
                hist_complete = "NA"
            elif crm_history_after >= live_h:
                hist_complete = "YES"
            else:
                hist_complete = "NO"
            inacc_txt = "; ".join(f"{x['bitrix_file_id']}:{x['reason']}" for x in person_inacc[:25])
            if len(person_inacc) > 25:
                inacc_txt += f"; +{len(person_inacc) - 25} more"
            row = {
                "person_name": person["display_name"],
                "canonical_uuid": person["cid"],
                "bitrix_contact_id": ",".join(sorted(snap["mapping"]["contacts"])),
                "lead_ids": ",".join(sorted(snap["mapping"]["leads"])),
                "deal_ids": ",".join(sorted(snap["mapping"]["deals"])),
                "person_info_complete": "YES" if primary_contact and not person_conflicts else "NO",
                "tutar_ve_para_birimi": " | ".join(t["amount"] for t in tutars if t.get("amount")) or "",
                "currency": " | ".join(sorted({t["currency"] for t in tutars if t.get("currency")})),
                "live_history_count": live_h,
                "crm_history_count": crm_history_after,
                "crm_history_count_before": person["crm_history"],
                "history_imported": apply_result.get("history") if apply else len(plans),
                "history_complete": hist_complete,
                "live_document_refs": len({str(f.get("bitrix_file_id")) for f in live_files if f.get("bitrix_file_id")}),
                "crm_linked_documents": crm_docs_after,
                "inaccessible_documents": inacc_txt,
                "agreement_data_complete": "YES" if snap["mapping"]["deals"] else "NO",
                "review_required": "; ".join((snap["mapping"].get("review") or []) + person_conflicts),
                "notes": (
                    f"safe_adds={list(adds)}; files={len(live_files)}; "
                    f"comments={len(snap['history'].get('comments') or [])}; "
                    f"activities={len(snap['history'].get('activities') or [])}; "
                    f"wa={len(snap['history'].get('messages') or [])}; "
                    f"docs_new={apply_result.get('docs') or 0}; "
                    f"docs_skipped={apply_result.get('docs_skipped') or 0}; "
                    f"inaccessible={len(person_inacc)}; "
                    f"ids_changed={apply_result.get('ids_changed')}"
                ),
            }
            if person["cid"] == EDA_UUID:
                eda = {
                    "canonical_uuid": person["cid"],
                    "bitrix_contact_id": row["bitrix_contact_id"],
                    "lead_ids": row["lead_ids"],
                    "deal_ids": row["deal_ids"],
                    "live_history_count": row["live_history_count"],
                    "history_imported": row["history_imported"],
                    "crm_history_count": row["crm_history_count"],
                    "history_complete": row["history_complete"],
                    "crm_docs": crm_docs_after,
                    "documents_visible_via_dual_links": crm_docs_after > 0,
                    "review": row["review_required"],
                    "inaccessible_docs": len(person_inacc),
                }
            rows.append(row)
            totals["checked"] += 1
            if snap["mapping"]["contacts"]:
                totals["mapped_contacts"] += 1
            totals["history_plans"] += len(plans)
            totals["history_imported"] += int(apply_result.get("history") or 0)
            totals["safe_field_adds"] += len(adds)
            totals["fields_written"] += int(apply_result.get("fields") or 0)
            totals["docs_new"] += int(apply_result.get("docs") or 0)
            totals["docs_skipped"] += int(apply_result.get("docs_skipped") or 0)
            totals["inaccessible_docs"] += len(person_inacc)
            if tutars:
                totals["tutar"] += 1
            totals["tutar_written"] += int(apply_result.get("tutar") or 0)
            if apply_result.get("ids_changed"):
                totals["ids_corrected"] += 1
            if person_conflicts or snap["mapping"].get("review"):
                conflicts.append({"person": person["display_name"], "issues": (snap["mapping"].get("review") or []) + person_conflicts})
        os_temple = [dict(r) for r in db.execute(
            text(
                """
                select a.id::text, a.contact_id::text, c.display_name, a.source_external_id,
                       a.unit_number, a.metadata_json
                from crm_agreements a join crm_contacts c on c.id=a.contact_id
                where a.project_group='the_temple'
                """
            )
        ).mappings().all()]
        temple = temple_summary(all_deals, os_temple)
        live_extra = fetch_live_temple_deals(client)
        for rec in live_extra:
            if not any(str(d.get("ID") or d.get("deal_id") or "") == str(rec.get("ID")) for d in all_deals):
                all_deals.append(rec)
        temple = temple_summary(all_deals, os_temple)
        temple["live_bitrix_title_search_count"] = len(live_extra)
        if apply:
            db.commit()
        (OUT / "reports" / "INACCESSIBLE_DOCUMENTS.json").write_text(
            json.dumps(inaccessible, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        summary = {
            "generated_at": utc_now(),
            "apply": apply,
            "backup_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_MASTER_AUDIT/backups/investhome-pre-agreement-master-audit-20260918.dump",
            "contacts_checked": len(rows),
            "totals": dict(totals),
            "eda": eda,
            "temple": {
                "existing_os": len(temple["existing_os_agreements"]),
                "live_deals": len(temple["live_temple_deals"]),
                "missing_from_os": len(temple["bitrix_deals_missing_from_os"]),
                "won_or_active": len(temple["won_or_active"]),
                "lost": len(temple["lost"]),
            },
            "bitrix_calls": client.call_count,
            "conflicts": conflicts,
        }
        csv_fields = list(rows[0].keys()) if rows else []
        with (OUT / "reports" / "AGREEMENT_CONTACT_COMPLETENESS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_fields)
            writer.writeheader()
            writer.writerows(rows)
        (OUT / "reports" / "AGREEMENT_CONTACT_COMPLETENESS_SUMMARY.json").write_text(
            json.dumps({"summary": summary, "temple": temple, "rows": rows}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        (OUT / "reports" / "THE_TEMPLE_EXTRA_DEALS.json").write_text(json.dumps(temple, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
