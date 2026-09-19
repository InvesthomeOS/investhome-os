"""Live Bitrix reconciliation for canonical Junk CRM contacts (~8336).

Default: fetch + dry-run (no CRM writes).
--apply: write verified IDs, blank fields, blank Junk reasons, Tutar ve para birimi, missing history.
No document recovery. Never name-only match. Never treat Excel row IDs as Bitrix IDs
unless live Bitrix confirms them. Do not change Active/Junk status.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityVisibility,
    CrmTaskStatus,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

from agreement_master_audit import (  # type: ignore
    ARCHIVE,
    HISTORY_KEY,
    OWNER_TYPE,
    TUTAR_FIELD_ID,
    TUTAR_LABEL,
    TYPE_MAP,
    attach_tutar,
    collapse_ws,
    deal_tutar,
    emails_of,
    flatten,
    import_key_aliases,
    list_all,
    match_deals_to_agreements,
    normalize_valid_email,
    parse_dt,
    person_safe_adds,
    phone_keys,
    phones_of,
    planned_history,
    slim_entity,
    utc_now,
)

from active_master_audit import (  # type: ignore
    collect_tutars,
    extra_safe_adds,
    lead_tutar,
    web_of,
    whatsapp_of,
)

OUT = Path("/export/2026-09-final/BITRIX_JUNK_MASTER_AUDIT")
BACKUP_PATH = (
    "data/Bitrix_Export/2026-09-final/BITRIX_JUNK_MASTER_AUDIT/backups/"
    "investhome-pre-junk-master-audit-20260918.dump"
)
HASH_PREFIX = re.compile(r"^#\d+\s+")
HONORIFIC = re.compile(r"\b(bey|han[ıi]m|mr|mrs|ms)\b", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9ğüşöçıİ]+", re.I)
BATCH_SIZE = 45


def fold_tr(value: str) -> str:
    table = str.maketrans("ğüşöçıĞÜŞÖÇİIı", "gusociGUSOCIii")
    return (value or "").translate(table).casefold()


def name_tokens(value: str) -> list[str]:
    text = HASH_PREFIX.sub("", collapse_ws(value))
    text = HONORIFIC.sub(" ", text)
    parts = [fold_tr(p) for p in NON_ALNUM.split(text) if p]
    out: list[str] = []
    for part in parts:
        if not out or out[-1] != part:
            out.append(part)
    return out


def harmless_display_name(os_name: str, bitrix_name: str) -> bool:
    a, b = name_tokens(os_name), name_tokens(bitrix_name)
    if not a or not b:
        return False
    if a == b:
        return True
    sa, sb = set(a), set(b)
    if sa <= sb or sb <= sa:
        return True
    if "".join(a) == "".join(b):
        return True
    return False


def source_excel_id(person: dict) -> str | None:
    meta = person.get("metadata_json") if isinstance(person.get("metadata_json"), dict) else {}
    bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    for ext in bitrix.get("external_ids") or []:
        text = str(ext)
        if ":" in text:
            tail = text.rsplit(":", 1)[-1].strip()
            if tail.isdigit():
                return tail
        if str(ext).isdigit():
            return str(ext)
    return None


def stored_source_ids(person: dict) -> dict[str, list[str]]:
    meta = person.get("metadata_json") if isinstance(person.get("metadata_json"), dict) else {}
    bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    contacts: list[str] = []
    leads: list[str] = []
    deals: list[str] = []
    for ext in bitrix.get("external_ids") or []:
        text = str(ext)
        if text.startswith("bitrix_contact:"):
            eid = text.split(":", 1)[-1]
            if eid.isdigit():
                contacts.append(eid)
        elif text.startswith("bitrix_lead:"):
            eid = text.split(":", 1)[-1]
            if eid.isdigit():
                leads.append(eid)
        elif text.startswith("bitrix_deal:"):
            eid = text.split(":", 1)[-1]
            if eid.isdigit():
                deals.append(eid)
    excel = source_excel_id(person)
    if excel:
        leads.append(excel)
    return {
        "contacts": list(dict.fromkeys(contacts + person.get("existing_contact_ids") or [])),
        "leads": list(dict.fromkeys(leads + person.get("existing_lead_ids") or [])),
        "deals": list(dict.fromkeys(deals + person.get("existing_deal_ids") or [])),
    }


def batch_call(client: BitrixClient, commands: dict[str, tuple[str, dict]]) -> dict:
    if not commands:
        return {"result": {}, "result_error": {}, "result_next": {}, "result_total": {}}
    payload: dict[str, Any] = {"halt": 0}
    for key, (method, params) in commands.items():
        payload[f"cmd[{key}]"] = f"{method}?{urllib.parse.urlencode(params, doseq=True)}"
    body = client.call("batch", payload)
    result = body.get("result") or {}
    if isinstance(result, dict) and "result" in result:
        return {
            "result": result.get("result") or {},
            "result_error": result.get("result_error") or {},
            "result_next": result.get("result_next") or {},
            "result_total": result.get("result_total") or {},
        }
    return {
        "result": result if isinstance(result, dict) else {},
        "result_error": body.get("result_error") or {},
        "result_next": body.get("result_next") or {},
        "result_total": body.get("result_total") or {},
    }


def chunks(items: list, size: int = BATCH_SIZE):
    for index in range(0, len(items), size):
        yield items[index : index + size]


def entity_ok(rec: dict | None, eid: str) -> bool:
    if not isinstance(rec, dict) or not rec:
        return False
    return str(rec.get("ID") or "") == str(eid)


def load_people(db: Session, limit: int | None = None, offset: int = 0) -> list[dict]:
    sql = """
        select c.id::text as cid, c.display_name, c.first_name, c.last_name, c.primary_phone,
               c.secondary_phones, c.primary_email, c.secondary_emails, c.organization_name,
               c.job_title, c.address_line1, c.address_line2, c.city, c.state_province,
               c.postal_code, c.country, c.source, c.junk_reason, c.notes, c.metadata_json,
               c.status, c.website, c.whatsapp, c.owner_user_id::text as owner_user_id,
               u.full_name as owner_name
        from crm_contacts c
        left join users u on u.id = c.owner_user_id
        where c.status = 'ARCHIVED'
          and c.metadata_json::jsonb->'bitrix_import'->'source_roles' ? 'junk'
        order by c.display_name, c.id
    """
    if limit:
        sql += " offset :offset limit :limit"
        rows = db.execute(text(sql), {"offset": offset, "limit": limit}).mappings().all()
    else:
        rows = db.execute(text(sql)).mappings().all()
    counts = {
        str(row[0]): int(row[1] or 0)
        for row in db.execute(
            text(
                """
                select entity_id::text, count(*)
                from crm_activities
                where archived_at is null and entity_type in ('contact', 'CONTACT')
                group by 1
                """
            )
        ).all()
    }
    people = []
    for row in rows:
        rec = dict(row)
        meta = rec.get("metadata_json") if isinstance(rec.get("metadata_json"), dict) else {}
        live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
        rec["existing_contact_ids"] = [str(x) for x in (live.get("contact_ids") or []) if str(x).isdigit()]
        rec["existing_lead_ids"] = [str(x) for x in (live.get("lead_ids") or []) if str(x).isdigit()]
        rec["existing_deal_ids"] = [str(x) for x in (live.get("deal_ids") or []) if str(x).isdigit()]
        rec["crm_history"] = counts.get(rec["cid"], 0)
        rec["import_keys"] = set()
        rec["source_ids"] = stored_source_ids(rec)
        people.append(rec)
    return people


def load_import_keys(db: Session, cid: str) -> set[str]:
    keys: set[str] = set()
    for key_row in db.execute(
        text("select metadata_json from crm_activities where entity_id=cast(:cid as uuid)"),
        {"cid": cid},
    ).all():
        meta_act = key_row[0] if key_row else {}
        if not isinstance(meta_act, dict):
            continue
        for bucket in (HISTORY_KEY, "bitrix_historical_comment"):
            hist = meta_act.get(bucket)
            if isinstance(hist, dict) and hist.get("import_key"):
                keys |= import_key_aliases(str(hist["import_key"]))
            if isinstance(hist, dict) and hist.get("bitrix_record_id"):
                kind = str(hist.get("kind") or bucket)
                keys |= import_key_aliases(f"bitrix:{kind}:{hist['bitrix_record_id']}")
                if hist.get("chat_id") and hist.get("bitrix_record_id"):
                    keys |= import_key_aliases(f"bitrix:wa:{hist['chat_id']}:{hist['bitrix_record_id']}")
    return keys


def discover_junk_reason_fields(client: BitrixClient) -> tuple[list[str], dict[str, dict[str, str]]]:
    found: list[str] = []
    enum_maps: dict[str, dict[str, str]] = {}
    for method in ("crm.lead.fields", "crm.contact.fields"):
        body = client.call(method, {})
        fields = body.get("result") if isinstance(body.get("result"), dict) else {}
        for key, spec in fields.items():
            if not isinstance(spec, dict):
                continue
            labels = " ".join(
                str(spec.get(item) or "")
                for item in ("formLabel", "listLabel", "filterLabel", "title", "upperName")
            ).casefold()
            items = spec.get("items") if isinstance(spec.get("items"), list) else []
            if items:
                enum_maps.setdefault(str(key), {})
                for item in items:
                    if isinstance(item, dict) and item.get("ID") is not None:
                        enum_maps[str(key)][str(item.get("ID"))] = str(item.get("VALUE") or "").strip()
            if any(token in labels for token in ("junk", "sebep", "reason")) and str(key).startswith("UF_"):
                found.append(str(key))
    return list(dict.fromkeys(found)), enum_maps


def reason_value(value: Any) -> str:
    if value in (None, "", [], {}, 0, "0"):
        return ""
    if isinstance(value, list):
        parts = [reason_value(item) for item in value]
        return "; ".join(p for p in parts if p)
    if isinstance(value, dict):
        for key in ("VALUE", "value", "LABEL", "label"):
            if value.get(key):
                return str(value[key]).strip()
        return collapse_ws(json.dumps(value, ensure_ascii=False))
    return collapse_ws(str(value))


def map_enum_reason(text: str, uf_key: str | None, enum_maps: dict[str, dict[str, str]] | None) -> str:
    if not text:
        return ""
    maps = enum_maps or {}
    if uf_key and text in maps.get(uf_key, {}):
        return maps[uf_key][text]
    for mapping in maps.values():
        if text in mapping:
            return mapping[text]
    if text.isdigit():
        return ""
    return text


def bitrix_junk_reason(
    rec: dict | None,
    uf_fields: list[str],
    enum_maps: dict[str, dict[str, str]] | None = None,
) -> str:
    if not rec:
        return ""
    extras = rec.get("source_extras") if isinstance(rec.get("source_extras"), dict) else {}
    for key in uf_fields + ["UF_CRM_JUNK_REASON", "UF_CRM_JUNK", "REASON"]:
        text = map_enum_reason(reason_value(rec.get(key)), key, enum_maps)
        if text:
            return text
    for key in ("junk_reason", "junk sebebi"):
        text = reason_value(extras.get(key))
        if text:
            return text
    return ""


def bitrix_stage(rec: dict | None) -> str:
    if not rec:
        return ""
    return str(rec.get("STATUS_ID") or rec.get("STAGE_ID") or "").strip()


def reasons_conflict(os_reason: str, bx_reason: str) -> bool:
    a = fold_tr(collapse_ws(os_reason or ""))
    b = fold_tr(collapse_ws(bx_reason or ""))
    if not a or not b:
        return False
    if a == b:
        return False
    if a in b or b in a:
        return False
    return True


def filter_harmless_conflicts(person: dict, conflicts: list[str]) -> list[str]:
    out = []
    os_name = str(person.get("display_name") or "")
    for item in conflicts:
        if item.startswith("display_name OS="):
            bitrix_name = item.split(" Bitrix=", 1)[-1] if " Bitrix=" in item else ""
            if harmless_display_name(os_name, bitrix_name):
                continue
        out.append(item)
    return out


def person_phones(person: dict) -> set[str]:
    keys: set[str] = set()
    keys |= phone_keys(person.get("primary_phone"))
    for phone in person.get("secondary_phones") or []:
        keys |= phone_keys(phone)
    return keys


def person_emails(person: dict) -> set[str]:
    emails = [normalize_valid_email(person.get("primary_email") or "") or ""]
    emails.extend(normalize_valid_email(e) or "" for e in (person.get("secondary_emails") or []))
    return {e for e in emails if e}


def comms_overlap(person: dict, rec: dict) -> tuple[bool, bool]:
    rec_phones: set[str] = set()
    for value in phones_of(rec):
        rec_phones |= phone_keys(value)
    rec_emails = set(emails_of(rec))
    return bool(person_phones(person) and rec_phones and (person_phones(person) & rec_phones)), bool(
        person_emails(person) and rec_emails and (person_emails(person) & rec_emails)
    )


def batch_get(client: BitrixClient, method: str, ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    unique = [i for i in dict.fromkeys(ids) if str(i).isdigit()]
    for group in chunks(unique):
        commands = {f"e{i}": (method, {"id": eid}) for i, eid in enumerate(group)}
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, eid in enumerate(group):
            rec = result.get(f"e{i}")
            if entity_ok(rec, eid):
                out[eid] = rec
    return out


def archive_file(etype: str, eid: str) -> Path:
    return ARCHIVE / "raw" / f"{etype}s" / f"{eid}.json"


def archive_chat_file(etype: str, eid: str) -> Path:
    return ARCHIVE / "raw" / "chats" / "live" / f"{etype}_{eid}.json"


def load_archive_rec(etype: str, eid: str) -> dict:
    path = archive_file(etype, eid)
    if not path.exists():
        return {}
    try:
        rec = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return rec if isinstance(rec, dict) else {}


def merge_archive_history(hist: dict, mapping: dict) -> dict:
    comments = {str(x.get("ID") or ""): x for x in hist.get("comments") or [] if x.get("ID")}
    activities = {str(x.get("ID") or ""): x for x in hist.get("activities") or [] if x.get("ID")}
    messages = list(hist.get("messages") or [])
    msg_keys = {f"{m.get('chat_id')}:{m.get('id')}" for m in messages if m.get("id") is not None}
    archive_extra = 0
    entities = (
        [("contact", eid) for eid in mapping.get("contacts") or []]
        + [("lead", eid) for eid in mapping.get("leads") or []]
        + [("deal", eid) for eid in mapping.get("deals") or []]
    )
    for etype, eid in entities:
        rec = load_archive_rec(etype, eid)
        for row in rec.get("timeline_comments") or []:
            cid = str(row.get("ID") or "")
            if cid and cid not in comments:
                comments[cid] = {**row, "_entity_type": etype, "_entity_id": eid, "_from_archive": True}
                archive_extra += 1
        for row in rec.get("crm_activities") or []:
            aid = str(row.get("ID") or "")
            if aid and aid not in activities:
                activities[aid] = {**row, "_entity_type": etype, "_entity_id": eid, "_from_archive": True}
                archive_extra += 1
        for msg in rec.get("retrieved_chat_messages") or []:
            if not isinstance(msg, dict):
                continue
            mid = str(msg.get("id") or msg.get("message_id") or "")
            chat_id = str(msg.get("chat_id") or "")
            key = f"{chat_id}:{mid}"
            if mid and key not in msg_keys:
                messages.append(
                    {**msg, "id": mid, "chat_id": chat_id, "_entity_type": etype, "_entity_id": eid, "_from_archive": True}
                )
                msg_keys.add(key)
                archive_extra += 1
        chat_path = archive_chat_file(etype, eid)
        if chat_path.exists():
            try:
                chat_rec = json.loads(chat_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                chat_rec = {}
            chat_messages = chat_rec.get("messages") if isinstance(chat_rec, dict) else []
            if isinstance(chat_rec, dict) and not chat_messages:
                chat_messages = chat_rec.get("retrieved_chat_messages") or chat_rec.get("result") or []
            if isinstance(chat_messages, dict):
                chat_messages = chat_messages.get("messages") or []
            for msg in chat_messages or []:
                if not isinstance(msg, dict):
                    continue
                mid = str(msg.get("id") or msg.get("message_id") or "")
                chat_id = str(msg.get("chat_id") or msg.get("CHAT_ID") or "")
                key = f"{chat_id}:{mid}"
                if mid and key not in msg_keys:
                    messages.append(
                        {
                            **msg,
                            "id": mid,
                            "chat_id": chat_id,
                            "_entity_type": etype,
                            "_entity_id": eid,
                            "_from_archive": True,
                        }
                    )
                    msg_keys.add(key)
                    archive_extra += 1
    hist = dict(hist)
    hist["comments"] = list(comments.values())
    hist["activities"] = list(activities.values())
    hist["messages"] = messages
    hist["archive_extra_count"] = archive_extra
    hist["archive_history_count"] = archive_extra
    return hist


def paginate_batch_lists(
    client: BitrixClient,
    method: str,
    specs: list[tuple[str, dict, str, str]],
) -> dict[str, list[dict]]:
    collected: dict[str, list[dict]] = {key: [] for key, *_ in specs}
    pending = {key: dict(params) for key, params, *_ in specs}
    meta = {key: (etype, eid) for key, _params, etype, eid in specs}
    start_vals = {key: 0 for key in pending}
    while pending:
        commands = {}
        keys = list(pending.keys())
        for key in keys[:BATCH_SIZE]:
            params = dict(pending[key])
            params["start"] = start_vals[key]
            commands[key] = (method, params)
        body = batch_call(client, commands)
        result = body.get("result") or {}
        nxt = body.get("result_next") or {}
        still: dict[str, dict] = {}
        for key in commands:
            chunk = result.get(key) or []
            if isinstance(chunk, dict):
                chunk = chunk.get("items") or chunk.get("result") or []
            etype, eid = meta[key]
            for row in chunk or []:
                if isinstance(row, dict):
                    collected[key].append({**row, "_entity_type": etype, "_entity_id": eid})
            next_start = nxt.get(key)
            if next_start not in (None, "", 0, "0") and chunk:
                start_vals[key] = int(next_start)
                still[key] = pending[key]
        pending = still
    return collected


def fetch_messages(client: BitrixClient, chat_id: str, etype: str, eid: str) -> list[dict]:
    messages: list[dict] = []
    last = None
    for _ in range(40):
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
        nxt = min((i for i in ids if i), default=None)
        if not nxt or nxt == last:
            break
        last = nxt
    return messages


def fetch_history(client: BitrixClient, mapping: dict) -> dict:
    comments: dict[str, dict] = {}
    activities: dict[str, dict] = {}
    chats: list[dict] = []
    messages: list[dict] = []
    entities = (
        [("contact", eid) for eid in mapping.get("contacts") or []]
        + [("lead", eid) for eid in mapping.get("leads") or []]
        + [("deal", eid) for eid in mapping.get("deals") or []]
    )
    if not entities:
        return {
            "comments": [],
            "activities": [],
            "chats": [],
            "messages": [],
            "live_history_count": 0,
        }
    comment_specs = [
        (
            f"c{i}",
            flatten({"filter": {"ENTITY_TYPE": etype, "ENTITY_ID": eid}}),
            etype,
            eid,
        )
        for i, (etype, eid) in enumerate(entities)
    ]
    activity_specs = [
        (
            f"a{i}",
            flatten({"filter": {"OWNER_TYPE_ID": OWNER_TYPE[etype], "OWNER_ID": eid}}),
            etype,
            eid,
        )
        for i, (etype, eid) in enumerate(entities)
    ]
    for spec_group in chunks(comment_specs, BATCH_SIZE):
        for rows in paginate_batch_lists(client, "crm.timeline.comment.list", spec_group).values():
            for row in rows:
                cid = str(row.get("ID") or "")
                if cid:
                    comments.setdefault(cid, row)
    for spec_group in chunks(activity_specs, BATCH_SIZE):
        for rows in paginate_batch_lists(client, "crm.activity.list", spec_group).values():
            for row in rows:
                aid = str(row.get("ID") or "")
                if aid:
                    activities.setdefault(aid, row)
    oc_entities = [(etype, eid) for etype, eid in entities if etype in {"contact", "lead"}]
    for group in chunks(oc_entities, BATCH_SIZE):
        commands = {
            f"o{i}": (
                "imopenlines.crm.chat.get",
                {"CRM_ENTITY_TYPE": etype.upper(), "CRM_ENTITY": eid, "ACTIVE_ONLY": "N"},
            )
            for i, (etype, eid) in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, (etype, eid) in enumerate(group):
            oc_list = result.get(f"o{i}")
            if not isinstance(oc_list, list):
                continue
            for item in oc_list:
                if not isinstance(item, dict):
                    continue
                chat_id = str(item.get("CHAT_ID") or "")
                if not chat_id:
                    continue
                chats.append({**item, "_entity_type": etype, "_entity_id": eid})
                messages.extend(fetch_messages(client, chat_id, etype, eid))
    return {
        "comments": list(comments.values()),
        "activities": list(activities.values()),
        "chats": chats,
        "messages": messages,
        "live_history_count": len(comments) + len(activities) + len(messages),
    }


def slim_plus(rec: dict) -> dict:
    out = slim_entity(rec)
    for key in ("WEB", "IM", "COMPANY_ID", "PHONE", "EMAIL"):
        if key in rec:
            out[key] = rec.get(key)
    out["_how"] = rec.get("_how")
    return out


def enrich_related(
    client: BitrixClient,
    contacts: dict[str, dict],
    leads: dict[str, dict],
    deals: dict[str, dict],
    person: dict,
) -> None:
    contact_ids = list(contacts)
    lead_ids = list(leads)
    extra_leads = []
    extra_contacts = []
    extra_deals = []
    for group in chunks(contact_ids, BATCH_SIZE):
        commands = {
            f"l{i}": ("crm.lead.list", flatten({"filter": {"CONTACT_ID": eid}, "select": ["ID", "CONTACT_ID"]}))
            for i, eid in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, _eid in enumerate(group):
            for item in result.get(f"l{i}") or []:
                if isinstance(item, dict) and item.get("ID"):
                    extra_leads.append(str(item["ID"]))
        commands = {
            f"d{i}": ("crm.deal.list", flatten({"filter": {"CONTACT_ID": eid}, "select": ["ID", "CONTACT_ID", "LEAD_ID"]}))
            for i, eid in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, _eid in enumerate(group):
            for item in result.get(f"d{i}") or []:
                if isinstance(item, dict) and item.get("ID"):
                    extra_deals.append(str(item["ID"]))
    for group in chunks(lead_ids, BATCH_SIZE):
        commands = {
            f"d{i}": ("crm.deal.list", flatten({"filter": {"LEAD_ID": eid}, "select": ["ID", "CONTACT_ID", "LEAD_ID"]}))
            for i, eid in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, _eid in enumerate(group):
            for item in result.get(f"d{i}") or []:
                if isinstance(item, dict) and item.get("ID"):
                    extra_deals.append(str(item["ID"]))
    missing_leads = [eid for eid in dict.fromkeys(extra_leads) if eid not in leads]
    if missing_leads:
        fetched = batch_get(client, "crm.lead.get", missing_leads)
        for eid, rec in fetched.items():
            rec["_how"] = "lead_contact_id"
            leads[eid] = rec
            linked = str(rec.get("CONTACT_ID") or "")
            if linked and linked not in {"0", ""}:
                extra_contacts.append(linked)
    missing_contacts = [eid for eid in dict.fromkeys(extra_contacts) if eid not in contacts]
    linked_from_leads = []
    for rec in leads.values():
        linked = str(rec.get("CONTACT_ID") or "")
        if linked and linked not in {"0", ""} and linked not in contacts:
            linked_from_leads.append(linked)
    missing_contacts = [eid for eid in dict.fromkeys(missing_contacts + linked_from_leads) if eid not in contacts]
    if missing_contacts:
        fetched = batch_get(client, "crm.contact.get", missing_contacts)
        for eid, rec in fetched.items():
            phone_ok, email_ok = comms_overlap(person, rec)
            existing = eid in (person.get("existing_contact_ids") or [])
            if phone_ok or email_ok or existing or str(rec.get("ID")) in extra_contacts or eid in linked_from_leads:
                rec["_how"] = "lead_linked_contact" if eid in linked_from_leads else "lead_contact_id"
                contacts[eid] = rec
    missing_deals = [eid for eid in dict.fromkeys(extra_deals) if eid not in deals]
    if missing_deals:
        fetched = batch_get(client, "crm.deal.get", missing_deals)
        for eid, rec in fetched.items():
            linked_c = str(rec.get("CONTACT_ID") or "")
            linked_l = str(rec.get("LEAD_ID") or "")
            if linked_c in contacts or linked_l in leads:
                rec["_how"] = "deal_contact_id" if linked_c in contacts else "deal_lead_id"
                deals[eid] = rec


def hist_for_mapping(full_hist: dict, mapping: dict) -> dict:
    contacts = set(mapping.get("contacts") or [])
    leads = set(mapping.get("leads") or [])
    deals = set(mapping.get("deals") or [])

    def keep(row: dict) -> bool:
        etype = row.get("_entity_type")
        eid = str(row.get("_entity_id") or "")
        return (
            (etype == "contact" and eid in contacts)
            or (etype == "lead" and eid in leads)
            or (etype == "deal" and eid in deals)
        )

    comments = [x for x in full_hist.get("comments") or [] if keep(x)]
    activities = [x for x in full_hist.get("activities") or [] if keep(x)]
    messages = [x for x in full_hist.get("messages") or [] if keep(x)]
    chats = [x for x in full_hist.get("chats") or [] if keep(x)]
    live_count = sum(1 for x in comments + activities + messages if not x.get("_from_archive"))
    return {
        "comments": comments,
        "activities": activities,
        "messages": messages,
        "chats": chats,
        "live_history_count": live_count,
    }


def attach_deals_global(client: BitrixClient, people: list[dict]) -> None:
    lead_ids: list[str] = []
    contact_ids: list[str] = []
    for person in people:
        mapping = person.get("_mapping") or {}
        lead_ids.extend(mapping.get("leads") or [])
        contact_ids.extend(mapping.get("contacts") or [])
    deals: dict[str, dict] = {}
    for group in chunks(list(dict.fromkeys(lead_ids))):
        commands = {
            f"d{i}": (
                "crm.deal.list",
                flatten(
                    {
                        "filter": {"LEAD_ID": eid},
                        "select": ["ID", "CONTACT_ID", "LEAD_ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID", "STAGE_ID"],
                    }
                ),
            )
            for i, eid in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, _eid in enumerate(group):
            for item in result.get(f"d{i}") or []:
                if isinstance(item, dict) and item.get("ID"):
                    rec = dict(item)
                    rec["_how"] = "deal_lead_id"
                    deals[str(item["ID"])] = rec
    for group in chunks(list(dict.fromkeys(contact_ids))):
        commands = {
            f"d{i}": (
                "crm.deal.list",
                flatten(
                    {
                        "filter": {"CONTACT_ID": eid},
                        "select": ["ID", "CONTACT_ID", "LEAD_ID", "TITLE", "OPPORTUNITY", "CURRENCY_ID", "STAGE_ID"],
                    }
                ),
            )
            for i, eid in enumerate(group)
        }
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, _eid in enumerate(group):
            for item in result.get(f"d{i}") or []:
                if isinstance(item, dict) and item.get("ID"):
                    rec = dict(item)
                    rec.setdefault("_how", "deal_contact_id")
                    deals[str(item["ID"])] = rec
    for person in people:
        mapping = person["_mapping"]
        lids = set(mapping.get("leads") or [])
        cids = set(mapping.get("contacts") or [])
        raw = {}
        for did, rec in deals.items():
            if str(rec.get("LEAD_ID") or "") in lids or str(rec.get("CONTACT_ID") or "") in cids:
                raw[did] = rec
        mapping["raw_deals"] = raw
        mapping["deals"] = {
            k: slim_entity(v) | {"_how": v.get("_how"), "_title": v.get("TITLE")} for k, v in raw.items()
        }


def resolve_from_live_records(
    person: dict,
    live_leads: dict[str, dict],
    live_contacts: dict[str, dict],
    live_deals: dict[str, dict],
    uf_fields: list[str],
    enum_maps: dict[str, dict[str, str]] | None = None,
) -> dict:
    review: list[str] = []
    contacts: dict[str, dict] = {}
    leads: dict[str, dict] = {}
    deals: dict[str, dict] = {}
    methods: list[str] = []
    source = stored_source_ids(person)
    pkeys = person_phones(person)
    emails = person_emails(person)

    def accept(etype: str, rec: dict, how: str, require_comms: bool) -> bool:
        eid = str(rec.get("ID") or "")
        if not eid:
            return False
        phone_ok, email_ok = comms_overlap(person, rec)
        existing = eid in (
            (person.get("existing_contact_ids") or []) if etype == "contact" else (person.get("existing_lead_ids") or [])
        )
        if require_comms and not (phone_ok or email_ok or existing):
            return False
        rec = dict(rec)
        rec["_how"] = how if not existing else f"{how}+existing_live_id"
        if etype == "contact":
            contacts[eid] = rec
        else:
            leads[eid] = rec
        methods.append(rec["_how"])
        if (pkeys or emails) and not phone_ok and not email_ok and how.startswith("source_"):
            rec_phones: set[str] = set()
            for value in phones_of(rec):
                rec_phones |= phone_keys(value)
            rec_emails = set(emails_of(rec))
            if (pkeys and rec_phones and not (pkeys & rec_phones)) or (emails and rec_emails and not (emails & rec_emails)):
                review.append("source_id_live_confirmed_identity_differs")
        return True

    for eid in source["leads"]:
        rec = live_leads.get(eid)
        if rec:
            accept("lead", rec, "source_external_id+live_lead_get", require_comms=False)
    for eid in source["contacts"]:
        rec = live_contacts.get(eid)
        if rec:
            accept("contact", rec, "source_external_id+live_contact_get", require_comms=False)
    if not contacts and not leads:
        review.append("no_verified_bitrix_contact")
        if not pkeys and not emails and not source["leads"] and not source["contacts"]:
            review.append("no_phone_or_email_for_live_match")
        elif source["leads"] or source["contacts"]:
            review.append("source_id_not_live")
    primary = next(iter(contacts.values()), None) or next(iter(leads.values()), None)
    bx_reason = bitrix_junk_reason(primary, uf_fields, enum_maps)
    if not bx_reason:
        for rec in list(leads.values()) + list(contacts.values()):
            bx_reason = bitrix_junk_reason(rec, uf_fields, enum_maps)
            if bx_reason:
                break
    stages = []
    for rec in list(leads.values()) + list(deals.values()) + list(contacts.values()):
        stage = bitrix_stage(rec)
        if stage:
            stages.append(stage)
    return {
        "contacts": {k: slim_plus(v) for k, v in contacts.items()},
        "leads": {k: slim_plus(v) for k, v in leads.items()},
        "deals": {k: slim_entity(v) | {"_how": v.get("_how"), "_title": v.get("TITLE")} for k, v in deals.items()},
        "raw_contacts": contacts,
        "raw_leads": leads,
        "raw_deals": deals,
        "review": review,
        "match_methods": sorted(set(methods)),
        "company_title": None,
        "assigned_name": None,
        "assigned_by_id": str((primary or {}).get("ASSIGNED_BY_ID") or "") or None,
        "junk_reason_bitrix": bx_reason,
        "junk_stage_or_status": list(dict.fromkeys(stages)),
        "unresolved_reason": "; ".join(review) if not contacts and not leads else "",
    }


def search_unmatched_live(
    client: BitrixClient,
    people: list[dict],
    uf_fields: list[str],
    enum_maps: dict[str, dict[str, str]] | None = None,
) -> None:
    for person in people:
        mapping = person.get("_mapping") or {}
        if mapping.get("contacts") or mapping.get("leads"):
            continue
        pkeys = list(person_phones(person))[:4]
        emails = list(person_emails(person))[:3]
        review = list(mapping.get("review") or [])
        contacts: dict[str, dict] = {}
        leads: dict[str, dict] = {}
        select = ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "CONTACT_ID", "COMPANY_ID", "POST", "WEB", "IM"]
        seen: set[tuple] = set()

        def consider(etype: str, rec: dict, how: str) -> None:
            if not isinstance(rec, dict):
                return
            eid = str(rec.get("ID") or "")
            if not eid:
                return
            phone_ok, email_ok = comms_overlap(person, rec)
            existing = eid in (
                (person.get("existing_contact_ids") or []) if etype == "contact" else (person.get("existing_lead_ids") or [])
            )
            if not (phone_ok or email_ok or existing):
                return
            rec = dict(rec)
            rec["_how"] = how
            if etype == "contact":
                contacts[eid] = rec
            else:
                leads[eid] = rec

        for phone in pkeys:
            key = ("dup", phone)
            if key not in seen:
                seen.add(key)
                body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "PHONE", "values[]": [phone]})
                ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
                fetched = batch_get(client, "crm.contact.get", [str(x) for x in (ids or [])])
                for rec in fetched.values():
                    consider("contact", rec, "duplicate_phone")
            body = client.call("crm.contact.list", {"filter[PHONE]": phone, "select[]": select, "start": 0})
            for rec in body.get("result") or []:
                consider("contact", rec, "list_phone")
            body = client.call("crm.lead.list", {"filter[PHONE]": phone, "select[]": select, "start": 0})
            for rec in body.get("result") or []:
                consider("lead", rec, "list_phone")
        for email in emails:
            body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "EMAIL", "values[]": [email]})
            ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
            fetched = batch_get(client, "crm.contact.get", [str(x) for x in (ids or [])])
            for rec in fetched.values():
                consider("contact", rec, "duplicate_email")
            body = client.call("crm.contact.list", {"filter[EMAIL]": email, "select[]": select, "start": 0})
            for rec in body.get("result") or []:
                consider("contact", rec, "list_email")
            body = client.call("crm.lead.list", {"filter[EMAIL]": email, "select[]": select, "start": 0})
            for rec in body.get("result") or []:
                consider("lead", rec, "list_email")
        if contacts or leads:
            person["_mapping"] = {
                "contacts": {k: slim_plus(v) for k, v in contacts.items()},
                "leads": {k: slim_plus(v) for k, v in leads.items()},
                "deals": {},
                "raw_contacts": contacts,
                "raw_leads": leads,
                "raw_deals": {},
                "review": [],
                "match_methods": sorted({v.get("_how") for v in list(contacts.values()) + list(leads.values()) if v.get("_how")}),
                "company_title": None,
                "assigned_name": None,
                "assigned_by_id": None,
                "junk_reason_bitrix": bitrix_junk_reason(
                    next(iter(contacts.values()), None) or next(iter(leads.values()), None),
                    uf_fields,
                    enum_maps,
                ),
                "junk_stage_or_status": list(
                    dict.fromkeys(bitrix_stage(r) for r in list(contacts.values()) + list(leads.values()) if bitrix_stage(r))
                ),
                "unresolved_reason": "",
            }
        else:
            if pkeys or emails:
                if "phone_email_not_found" not in review:
                    review.append("phone_email_not_found")
            mapping["review"] = review
            mapping["unresolved_reason"] = "; ".join(dict.fromkeys(review))
            person["_mapping"] = mapping


def format_tutar(tutars: list[dict]) -> tuple[str, str]:
    amounts = [t["amount"] for t in tutars if t.get("amount")]
    currencies = list(dict.fromkeys(t["currency"] for t in tutars if t.get("currency")))
    return " | ".join(amounts), " | ".join(currencies)


def apply_person(
    db: Session,
    actor: User | None,
    person: dict,
    mapping: dict,
    hist: dict,
    adds: dict,
    conflicts: list[str],
    junk_meta: dict,
) -> dict:
    result = {"ids": False, "fields": 0, "history": 0, "tutar": 0, "ids_changed": False, "junk_reason": 0, "errors": []}
    contact = db.get(CrmContact, UUID(person["cid"]))
    if contact is None:
        result["errors"].append("contact_missing")
        return result
    meta = dict(contact.metadata_json or {})
    live = dict(meta.get("bitrix_live") or {})
    old_contact_ids = [str(x) for x in (live.get("contact_ids") or [])]
    old_lead_ids = [str(x) for x in (live.get("lead_ids") or [])]
    old_deal_ids = [str(x) for x in (live.get("deal_ids") or [])]
    tutars = collect_tutars(mapping.get("deals") or {}, mapping.get("leads") or {})
    live.update(
        {
            "contact_ids": sorted(mapping.get("contacts") or {}),
            "lead_ids": sorted(mapping.get("leads") or {}),
            "deal_ids": sorted(mapping.get("deals") or {}),
            "how": {
                "contacts": {k: v.get("_how") for k, v in (mapping.get("contacts") or {}).items()},
                "leads": {k: v.get("_how") for k, v in (mapping.get("leads") or {}).items()},
                "deals": {k: v.get("_how") for k, v in (mapping.get("deals") or {}).items()},
            },
            "company_title": mapping.get("company_title"),
            "assigned_by_id": mapping.get("assigned_by_id"),
            "assigned_name": mapping.get("assigned_name"),
            "live_stage_or_status": junk_meta.get("junk_stage_or_status") or [],
            "junk_reason_os": person.get("junk_reason") or "",
            "junk_reason_bitrix": junk_meta.get("junk_reason_bitrix") or "",
            "tutar_ve_para_birimi": tutars,
            "updated_at": utc_now(),
            "source": "bitrix_live",
            "documents_skipped": True,
        }
    )
    if junk_meta.get("reason_conflict"):
        live["junk_reason_conflict"] = {
            "os": person.get("junk_reason") or "",
            "bitrix": junk_meta.get("junk_reason_bitrix") or "",
        }
    bitrix_imp = dict(meta.get("bitrix_import") or {})
    ext = list(bitrix_imp.get("external_ids") or [])
    for eid in mapping.get("contacts") or []:
        token = f"bitrix_contact:{eid}"
        if token not in ext:
            ext.append(token)
    for eid in mapping.get("leads") or []:
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
        old_contact_ids != sorted(mapping.get("contacts") or {})
        or old_lead_ids != sorted(mapping.get("leads") or {})
        or old_deal_ids != sorted(mapping.get("deals") or {})
        or not old_contact_ids
    )
    field_map = {
        "first_name": ("first_name", 120),
        "last_name": ("last_name", 120),
        "job_title": ("job_title", 120),
        "address_line1": ("address_line1", 255),
        "address_line2": ("address_line2", 255),
        "city": ("city", 120),
        "state_province": ("state_province", 120),
        "postal_code": ("postal_code", 30),
        "country": ("country", 100),
        "notes": ("notes", 8000),
        "organization_name": ("organization_name", 255),
        "website": ("website", 500),
        "whatsapp": ("whatsapp", 50),
        "junk_reason": ("junk_reason", 255),
    }
    for add_key, (attr, limit) in field_map.items():
        value = adds.get(add_key)
        if value:
            setattr(contact, attr, str(value)[:limit])
            result["fields"] += 1
            if add_key == "junk_reason":
                result["junk_reason"] = 1
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
    if conflicts:
        contact.review_required = True
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
    if tutars:
        result["tutar"] = len(tutars)
    agreements = db.query(CrmAgreement).filter(CrmAgreement.contact_id == UUID(person["cid"])).all()
    if agreements and mapping.get("deals"):
        paired = match_deals_to_agreements(agreements, mapping["deals"])
        paired_ags = {str(ag.id) for ag, _, _ in paired}
        for ag, deal_id, deal in paired:
            attach_tutar(ag, deal_id, deal, deal_tutar({**deal, "ID": deal_id}))
        if len(tutars) == 1 and tutars[0].get("related_entity_type") == "deal":
            for ag in agreements:
                if str(ag.id) in paired_ags:
                    continue
                ag_meta = dict(ag.metadata_json or {})
                if ag_meta.get("tutar_ve_para_birimi_amount"):
                    continue
                did = tutars[0]["related_entity_id"]
                attach_tutar(ag, did, mapping["deals"][did], tutars[0])
    return result


def write_progress(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    args = parser.parse_args()
    apply = args.apply
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    db = SessionLocal()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    people = load_people(db, limit=args.limit or None, offset=args.offset)
    actor = db.query(User).order_by(User.created_at.asc()).first()
    uf_fields, enum_maps = discover_junk_reason_fields(client)
    print(f"junk_reason_uf_fields={uf_fields} people={len(people)}", flush=True)

    lead_ids: list[str] = []
    contact_ids: list[str] = []
    deal_ids: list[str] = []
    for person in people:
        ids = person["source_ids"]
        lead_ids.extend(ids["leads"])
        contact_ids.extend(ids["contacts"])
        deal_ids.extend(ids["deals"])
    print(f"batch lead.get {len(set(lead_ids))} ids", flush=True)
    live_leads = batch_get(client, "crm.lead.get", lead_ids)
    print(f"live leads confirmed {len(live_leads)}", flush=True)
    extra_contacts = []
    for rec in live_leads.values():
        linked = str(rec.get("CONTACT_ID") or "")
        if linked and linked not in {"0", ""}:
            extra_contacts.append(linked)
    print(f"batch contact.get {len(set(contact_ids + extra_contacts))} ids", flush=True)
    live_contacts = batch_get(client, "crm.contact.get", contact_ids + extra_contacts)
    print(f"live contacts confirmed {len(live_contacts)}", flush=True)
    live_deals = batch_get(client, "crm.deal.get", deal_ids) if deal_ids else {}

    matched_source = 0
    for person in people:
        mapping = resolve_from_live_records(person, live_leads, live_contacts, live_deals, uf_fields, enum_maps)
        person["_mapping"] = mapping
        if mapping.get("contacts") or mapping.get("leads"):
            matched_source += 1
    print(f"source-id live matches {matched_source}/{len(people)}", flush=True)

    unmatched = [p for p in people if not (p["_mapping"].get("contacts") or p["_mapping"].get("leads"))]
    print(f"phone/email search unmatched {len(unmatched)}", flush=True)
    search_unmatched_live(client, unmatched, uf_fields, enum_maps)

    print("attach deals", flush=True)
    attach_deals_global(client, people)
    global_entities = {"contacts": {}, "leads": {}, "deals": {}}
    for person in people:
        mapping = person["_mapping"]
        global_entities["contacts"].update(mapping.get("contacts") or {})
        global_entities["leads"].update(mapping.get("leads") or {})
        global_entities["deals"].update(mapping.get("deals") or {})
    print(
        f"fetch live history contacts={len(global_entities['contacts'])} "
        f"leads={len(global_entities['leads'])} deals={len(global_entities['deals'])}",
        flush=True,
    )
    global_hist = fetch_history(client, global_entities)
    print(
        f"live history comments={len(global_hist['comments'])} "
        f"activities={len(global_hist['activities'])} messages={len(global_hist['messages'])} "
        f"calls={client.call_count}",
        flush=True,
    )

    company_ids: list[str] = []
    user_ids: list[str] = []
    for person in people:
        primary = next(iter((person["_mapping"].get("raw_contacts") or {}).values()), None) or next(
            iter((person["_mapping"].get("raw_leads") or {}).values()), None
        )
        if not primary:
            continue
        cid = str(primary.get("COMPANY_ID") or "")
        uid = str(primary.get("ASSIGNED_BY_ID") or "")
        if cid and cid not in {"0", ""}:
            company_ids.append(cid)
        if uid and uid not in {"0", ""}:
            user_ids.append(uid)
    company_cache = batch_get(client, "crm.company.get", company_ids)
    user_cache: dict[str, str] = {}
    for group in chunks(list(dict.fromkeys(user_ids))):
        commands = {f"u{i}": ("user.get", {"ID": uid}) for i, uid in enumerate(group)}
        body = batch_call(client, commands)
        result = body.get("result") or {}
        for i, uid in enumerate(group):
            rows_u = result.get(f"u{i}")
            urec: dict = {}
            if isinstance(rows_u, list) and rows_u and isinstance(rows_u[0], dict):
                urec = rows_u[0]
            elif isinstance(rows_u, dict):
                urec = rows_u
            user_cache[uid] = " ".join(p for p in [urec.get("NAME"), urec.get("LAST_NAME")] if p).strip()

    rows = []
    totals = Counter()
    conflicts_out = []
    history_yes = history_na = history_no = 0
    try:
        for index, person in enumerate(people, start=1):
            if index % 250 == 0 or index == 1:
                print(f"[{index}/{len(people)}] {person['display_name']} calls={client.call_count}", flush=True)
            snap_path = OUT / "raw" / f"{person['cid']}.json"
            mapping = person["_mapping"]
            if snap_path.exists() and not args.refresh:
                snap = json.loads(snap_path.read_text(encoding="utf-8"))
                mapping = snap.get("mapping") or mapping
            else:
                hist = hist_for_mapping(global_hist, mapping)
                live_count = hist.get("live_history_count") or 0
                hist = merge_archive_history(hist, mapping)
                hist["live_history_count"] = live_count
                primary_contact: dict = {}
                contacts_map = mapping.get("raw_contacts") or mapping.get("contacts") or {}
                leads_map = mapping.get("raw_leads") or mapping.get("leads") or {}
                if len(contacts_map) == 1:
                    primary_contact = next(iter(contacts_map.values()))
                elif contacts_map:
                    primary_contact = next(iter(contacts_map.values()))
                    review = list(mapping.get("review") or [])
                    if "multiple_or_first_contact_used" not in review:
                        review.append("multiple_or_first_contact_used")
                    mapping["review"] = review
                elif leads_map:
                    primary_contact = next(iter(leads_map.values()))
                assigned_id = str((primary_contact or {}).get("ASSIGNED_BY_ID") or "") or None
                company_id = str((primary_contact or {}).get("COMPANY_ID") or "")
                company_title = None
                if company_id and company_id not in {"0", ""}:
                    company_title = str((company_cache.get(company_id) or {}).get("TITLE") or "") or None
                assigned_name = user_cache.get(assigned_id or "") or None
                mapping["company_title"] = company_title
                mapping["assigned_name"] = assigned_name
                mapping["assigned_by_id"] = assigned_id
                if not mapping.get("junk_reason_bitrix"):
                    mapping["junk_reason_bitrix"] = bitrix_junk_reason(primary_contact, uf_fields, enum_maps)
                snap = {
                    "person": {
                        k: person[k]
                        for k in ("cid", "display_name", "primary_phone", "primary_email", "organization_name", "owner_name", "junk_reason")
                        if k in person
                    },
                    "mapping": {
                        "contacts": mapping.get("contacts") or {},
                        "leads": mapping.get("leads") or {},
                        "deals": mapping.get("deals") or {},
                        "review": mapping.get("review") or [],
                        "company_title": company_title,
                        "assigned_name": assigned_name,
                        "assigned_by_id": assigned_id,
                        "match_methods": mapping.get("match_methods") or [],
                        "junk_reason_bitrix": mapping.get("junk_reason_bitrix") or "",
                        "junk_stage_or_status": mapping.get("junk_stage_or_status") or [],
                        "unresolved_reason": mapping.get("unresolved_reason") or "",
                        "raw_contacts": {
                            k: slim_plus(v)
                            | {
                                "NAME": v.get("NAME"),
                                "LAST_NAME": v.get("LAST_NAME"),
                                "POST": v.get("POST"),
                                "PHONE": v.get("PHONE"),
                                "EMAIL": v.get("EMAIL"),
                                "COMMENTS": v.get("COMMENTS"),
                                "OPPORTUNITY": v.get("OPPORTUNITY"),
                                "CURRENCY_ID": v.get("CURRENCY_ID"),
                                "STATUS_ID": v.get("STATUS_ID"),
                                "STAGE_ID": v.get("STAGE_ID"),
                            }
                            for k, v in (mapping.get("raw_contacts") or mapping.get("contacts") or {}).items()
                        },
                    },
                    "history": {
                        "comments": hist["comments"],
                        "activities": hist["activities"],
                        "chats": hist.get("chats") or [],
                        "messages": hist["messages"],
                        "live_history_count": hist.get("live_history_count") or 0,
                        "archive_extra_count": hist.get("archive_extra_count") or 0,
                    },
                    "primary_contact": {
                        k: primary_contact.get(k)
                        for k in (
                            "ID", "NAME", "LAST_NAME", "POST", "PHONE", "EMAIL", "WEB", "IM",
                            "ADDRESS", "ADDRESS_2", "ADDRESS_CITY", "ADDRESS_REGION", "ADDRESS_PROVINCE",
                            "ADDRESS_POSTAL_CODE", "ADDRESS_COUNTRY", "COMMENTS", "COMPANY_ID", "_how",
                            "OPPORTUNITY", "CURRENCY_ID", "STATUS_ID", "STAGE_ID",
                        )
                        if k in primary_contact
                    },
                }
                for uf in uf_fields:
                    if primary_contact.get(uf) not in (None, "", [], {}):
                        snap["primary_contact"][uf] = primary_contact.get(uf)
                snap_path.write_text(json.dumps(snap, ensure_ascii=False, default=str), encoding="utf-8")
            contacts_map = snap["mapping"].get("raw_contacts") or snap["mapping"].get("contacts") or {}
            primary_contact = snap.get("primary_contact") or {}
            if not primary_contact and contacts_map:
                primary_contact = next(iter(contacts_map.values()))
            elif not primary_contact and snap["mapping"].get("leads"):
                primary_contact = next(iter(snap["mapping"]["leads"].values()))
            adds, person_conflicts, _notes = extra_safe_adds(
                person,
                primary_contact,
                snap["mapping"].get("company_title"),
                snap["mapping"].get("assigned_name"),
            )
            person_conflicts = filter_harmless_conflicts(person, person_conflicts)
            bx_reason = str(snap["mapping"].get("junk_reason_bitrix") or bitrix_junk_reason(primary_contact, uf_fields, enum_maps) or "")
            os_reason = str(person.get("junk_reason") or "").strip()
            reason_conflict = False
            if not os_reason and bx_reason:
                adds["junk_reason"] = bx_reason
            elif reasons_conflict(os_reason, bx_reason):
                reason_conflict = True
                person_conflicts.append(f"junk_reason OS={os_reason} Bitrix={bx_reason}")
            if len(contacts_map) > 1:
                for key in ("first_name", "last_name", "notes", "organization_name"):
                    adds.pop(key, None)
            person["import_keys"] = load_import_keys(db, person["cid"]) if apply or (snap["history"].get("live_history_count") or 0) or (snap["history"].get("archive_extra_count") or 0) else set()
            plans = planned_history(person, snap["history"])
            tutars = collect_tutars(snap["mapping"].get("deals") or {}, snap["mapping"].get("leads") or {})
            amount, currency = format_tutar(tutars)
            apply_result: dict[str, Any] = {}
            matched = bool(snap["mapping"].get("contacts") or snap["mapping"].get("leads"))
            apply_contacts = dict(snap["mapping"].get("contacts") or {})
            apply_leads = snap["mapping"].get("leads") or {}
            for lead in apply_leads.values():
                if not isinstance(lead, dict):
                    continue
                linked = str(lead.get("CONTACT_ID") or "")
                if linked and linked not in {"0", ""} and linked not in apply_contacts:
                    apply_contacts[linked] = {"ID": linked, "_how": "lead_linked_contact"}
            if apply and matched:
                apply_result = apply_person(
                    db,
                    actor,
                    person,
                    {
                        "contacts": apply_contacts,
                        "leads": apply_leads,
                        "deals": snap["mapping"].get("deals") or {},
                        "company_title": snap["mapping"].get("company_title"),
                        "assigned_name": snap["mapping"].get("assigned_name"),
                        "assigned_by_id": snap["mapping"].get("assigned_by_id"),
                    },
                    snap["history"],
                    adds,
                    person_conflicts,
                    {
                        "junk_reason_bitrix": bx_reason,
                        "junk_stage_or_status": snap["mapping"].get("junk_stage_or_status") or [],
                        "reason_conflict": reason_conflict,
                    },
                )
                db.commit()
            crm_history_after = person["crm_history"] + (apply_result.get("history") or 0 if apply else 0)
            if apply and matched:
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
            live_h = snap["history"].get("live_history_count") or 0
            archive_extra = snap["history"].get("archive_extra_count") or 0
            if live_h == 0:
                hist_complete = "NA"
                history_na += 1
            elif crm_history_after >= live_h:
                hist_complete = "YES"
                history_yes += 1
            else:
                hist_complete = "NO"
                history_no += 1
            review_bits = list(snap["mapping"].get("review") or []) + person_conflicts
            methods = snap["mapping"].get("match_methods") or []
            if not methods:
                methods = sorted(
                    {
                        str(v.get("_how"))
                        for v in list((snap["mapping"].get("contacts") or {}).values())
                        + list((snap["mapping"].get("leads") or {}).values())
                        if isinstance(v, dict) and v.get("_how")
                    }
                )
            row = {
                "canonical_uuid": person["cid"],
                "name": person["display_name"],
                "bitrix_contact_ids": ",".join(sorted(apply_contacts)),
                "lead_ids": ",".join(sorted(apply_leads)),
                "deal_ids": ",".join(sorted(snap["mapping"].get("deals") or {})),
                "match_method": ",".join(methods),
                "junk_reason_os": os_reason,
                "junk_reason_bitrix": bx_reason,
                "junk_stage_or_status": ",".join(snap["mapping"].get("junk_stage_or_status") or []),
                "tutar_ve_para_birimi": amount,
                "currency": currency,
                "live_history_count": live_h,
                "crm_history_count": crm_history_after,
                "crm_history_count_before": person["crm_history"],
                "history_imported": apply_result.get("history") if apply else len(plans),
                "history_status": hist_complete,
                "history_complete": hist_complete,
                "conflicts": "; ".join(person_conflicts),
                "review_required": "; ".join(review_bits),
                "unresolved_reason": "" if matched else (snap["mapping"].get("unresolved_reason") or "; ".join(review_bits)),
                "notes": (
                    f"safe_adds={list(adds)}; comments={len(snap['history'].get('comments') or [])}; "
                    f"activities={len(snap['history'].get('activities') or [])}; "
                    f"wa={len(snap['history'].get('messages') or [])}; "
                    f"archive_extra={archive_extra}; ids_changed={apply_result.get('ids_changed')}; "
                    f"reason_conflict={reason_conflict}"
                ),
            }
            rows.append(row)
            totals["checked"] += 1
            if matched:
                totals["matched"] += 1
            else:
                totals["unmatched"] += 1
            totals["history_plans"] += len(plans)
            totals["history_imported"] += int(apply_result.get("history") or 0)
            totals["safe_field_adds"] += len([k for k in adds if k != "junk_reason"])
            totals["fields_written"] += int(apply_result.get("fields") or 0)
            if amount:
                totals["tutar"] += 1
            totals["tutar_written"] += int(1 if apply and apply_result.get("tutar") else 0)
            if apply_result.get("ids_changed"):
                totals["ids_corrected"] += 1
            if adds.get("junk_reason"):
                totals["junk_reason_plans"] += 1
            totals["junk_reason_written"] += int(apply_result.get("junk_reason") or 0)
            if reason_conflict:
                totals["junk_reason_conflicts"] += 1
            if person_conflicts:
                totals["real_conflicts"] += 1
            if review_bits:
                totals["review_required"] += 1
                conflicts_out.append({"person": person["display_name"], "uuid": person["cid"], "issues": review_bits})
            if index % 50 == 0:
                write_progress(
                    OUT / "reports" / "progress.json",
                    {
                        "index": index,
                        "total": len(people),
                        "matched": totals["matched"],
                        "unmatched": totals["unmatched"],
                        "calls": client.call_count,
                        "apply": apply,
                    },
                )
                csv_fields_tmp = [
                    "canonical_uuid", "name", "bitrix_contact_ids", "lead_ids", "deal_ids", "match_method",
                    "junk_reason_os", "junk_reason_bitrix", "tutar_ve_para_birimi", "currency",
                    "live_history_count", "crm_history_count", "history_status", "conflicts",
                    "review_required", "unresolved_reason",
                ]
                with (OUT / "reports" / "JUNK_CONTACT_COMPLETENESS.csv").open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=csv_fields_tmp, extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(rows)
        if apply:
            db.commit()
        junk_count = db.execute(
            text(
                """
                select count(*) from crm_contacts
                where status='ARCHIVED'
                  and metadata_json::jsonb->'bitrix_import'->'source_roles' ? 'junk'
                """
            )
        ).scalar() or 0
        contact_total = db.execute(text("select count(*) from crm_contacts")).scalar() or 0
        unmatched_rows = [r for r in rows if not r.get("bitrix_contact_ids") and not r.get("lead_ids")]
        summary = {
            "generated_at": utc_now(),
            "apply": apply,
            "backup_path": BACKUP_PATH,
            "junk_reason_uf_fields": uf_fields,
            "junk_contacts_checked": len(rows),
            "matched": totals["matched"],
            "unmatched": totals["unmatched"],
            "corrected_bitrix_ids": totals["ids_corrected"],
            "missing_person_fields_recovered": totals["fields_written"] if apply else totals["safe_field_adds"],
            "junk_reasons_recovered": totals["junk_reason_written"] if apply else totals["junk_reason_plans"],
            "tutar_ve_para_birimi_recovered": totals["tutar_written"] if apply else totals["tutar"],
            "missing_history_imported": totals["history_imported"] if apply else totals["history_plans"],
            "history_yes": history_yes,
            "history_na": history_na,
            "history_no": history_no,
            "real_conflicts": totals["real_conflicts"],
            "junk_reason_conflicts": totals["junk_reason_conflicts"],
            "unresolved_contacts": [
                {
                    "uuid": r["canonical_uuid"],
                    "name": r["name"],
                    "reason": r.get("unresolved_reason") or "no_verified_bitrix_contact",
                }
                for r in unmatched_rows
            ],
            "unresolved_count": len(unmatched_rows),
            "final_junk_count": junk_count,
            "crm_contacts_unchanged_total": contact_total,
            "documents_recovered": 0,
            "bitrix_calls": client.call_count,
            "totals": dict(totals),
            "conflicts": conflicts_out[:500],
            "report_paths": {
                "csv": "data/Bitrix_Export/2026-09-final/BITRIX_JUNK_MASTER_AUDIT/reports/JUNK_CONTACT_COMPLETENESS.csv",
                "summary": "data/Bitrix_Export/2026-09-final/BITRIX_JUNK_MASTER_AUDIT/reports/JUNK_CONTACT_COMPLETENESS_SUMMARY.json",
                "backup": BACKUP_PATH,
            },
        }
        csv_fields = [
            "canonical_uuid", "name", "bitrix_contact_ids", "lead_ids", "deal_ids", "match_method",
            "junk_reason_os", "junk_reason_bitrix", "junk_stage_or_status", "tutar_ve_para_birimi",
            "currency", "live_history_count", "crm_history_count", "history_status", "history_complete",
            "conflicts", "review_required", "unresolved_reason", "crm_history_count_before",
            "history_imported", "notes",
        ]
        with (OUT / "reports" / "JUNK_CONTACT_COMPLETENESS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        (OUT / "reports" / "JUNK_CONTACT_COMPLETENESS_SUMMARY.json").write_text(
            json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(json.dumps({k: v for k, v in summary.items() if k != "unresolved_contacts"}, ensure_ascii=False, indent=2, default=str))
        print("unresolved_count", summary["unresolved_count"], flush=True)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
