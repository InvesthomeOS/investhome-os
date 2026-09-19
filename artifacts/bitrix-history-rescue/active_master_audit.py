"""Live Bitrix reconciliation for the 121 Active CRM customers.

Default: fetch + dry-run (no CRM writes).
--apply: write verified IDs, blank fields, Tutar ve para birimi, missing history.
No document recovery. Never name-only match. Never treat Excel row IDs as Bitrix IDs.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
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

OUT = Path("/export/2026-09-final/BITRIX_ACTIVE_MASTER_AUDIT")
BACKUP_PATH = (
    "data/Bitrix_Export/2026-09-final/BITRIX_ACTIVE_MASTER_AUDIT/backups/"
    "investhome-pre-active-master-audit-20260918.dump"
)


def load_people(db: Session) -> list[dict]:
    rows = db.execute(
        text(
            """
            select c.id::text as cid, c.display_name, c.first_name, c.last_name, c.primary_phone,
                   c.secondary_phones, c.primary_email, c.secondary_emails, c.organization_name,
                   c.job_title, c.address_line1, c.address_line2, c.city, c.state_province,
                   c.postal_code, c.country, c.source, c.junk_reason, c.notes, c.metadata_json,
                   c.status, c.website, c.whatsapp, c.owner_user_id::text as owner_user_id,
                   u.full_name as owner_name
            from crm_contacts c
            left join users u on u.id = c.owner_user_id
            where c.status = 'ACTIVE'
              and c.archived_at is null
              and c.metadata_json::jsonb->'bitrix_import'->'source_roles' ? 'active_customers'
            order by c.display_name
            """
        )
    ).mappings().all()
    people = []
    for row in rows:
        rec = dict(row)
        meta = rec.get("metadata_json") if isinstance(rec.get("metadata_json"), dict) else {}
        live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
        rec["existing_contact_ids"] = [str(x) for x in (live.get("contact_ids") or []) if str(x).isdigit()]
        rec["existing_lead_ids"] = [str(x) for x in (live.get("lead_ids") or []) if str(x).isdigit()]
        rec["existing_deal_ids"] = [str(x) for x in (live.get("deal_ids") or []) if str(x).isdigit()]
        rec["agreements"] = [
            dict(a)
            for a in db.execute(
                text(
                    """
                    select id::text, project_group, status, unit_number, investment_amount,
                           agreement_date::text, source_external_id, review_required, metadata_json
                    from crm_agreements where contact_id = cast(:cid as uuid)
                    """
                ),
                {"cid": rec["cid"]},
            ).mappings().all()
        ]
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
        rec["import_keys"] = set()
        for key_row in db.execute(
            text("select metadata_json from crm_activities where entity_id=cast(:cid as uuid)"),
            {"cid": rec["cid"]},
        ).all():
            meta_act = key_row[0] if key_row else {}
            if not isinstance(meta_act, dict):
                continue
            for bucket in (HISTORY_KEY, "bitrix_historical_comment"):
                hist = meta_act.get(bucket)
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


def load_archive_index() -> dict[tuple[str, str], dict]:
    index: dict[tuple[str, str], dict] = {}
    if not ARCHIVE.exists():
        return index
    for folder, etype in ((ARCHIVE / "raw" / "contacts", "contact"), (ARCHIVE / "raw" / "leads", "lead")):
        if not folder.exists():
            continue
        for path in folder.glob("*.json"):
            if path.name.startswith("_"):
                continue
            try:
                rec = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(rec, dict):
                continue
            eid = str(rec.get("bitrix_entity_id") or path.stem)
            index[(etype, eid)] = rec
    return index


def web_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("WEB") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]).strip())
        elif isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def whatsapp_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("IM") or []:
        if not isinstance(item, dict):
            continue
        value_type = str(item.get("VALUE_TYPE") or item.get("TYPE") or "").upper()
        value = str(item.get("VALUE") or "").strip()
        if not value or len(value) > 50:
            continue
        if "WHATSAPP" in value_type or value.startswith("+") or phone_keys(value):
            if value.lower().startswith("imol|") or "bitrix_whatcrm" in value.lower():
                continue
            out.append(value)
    return out


def extra_safe_adds(os_row: dict, contact: dict, company_title: str | None, assigned_name: str | None) -> tuple[dict, list[str], list[str]]:
    adds, conflicts, notes = person_safe_adds(os_row, contact)
    if company_title:
        if not os_row.get("organization_name"):
            adds["organization_name"] = company_title.strip()
        elif collapse_ws(company_title).casefold() != collapse_ws(str(os_row.get("organization_name") or "")).casefold():
            conflicts.append(f"organization OS={os_row.get('organization_name')} Bitrix={company_title}")
    if not os_row.get("address_line2") and contact.get("ADDRESS_2"):
        adds["address_line2"] = str(contact["ADDRESS_2"]).strip()
    if not os_row.get("state_province") and (contact.get("ADDRESS_REGION") or contact.get("ADDRESS_PROVINCE")):
        adds["state_province"] = str(contact.get("ADDRESS_REGION") or contact.get("ADDRESS_PROVINCE")).strip()
    if not os_row.get("website"):
        sites = web_of(contact)
        if sites:
            adds["website"] = sites[0]
    if not os_row.get("whatsapp"):
        wa = whatsapp_of(contact)
        if wa:
            adds["whatsapp"] = wa[0]
    if assigned_name and os_row.get("owner_name"):
        if collapse_ws(assigned_name).casefold() != collapse_ws(str(os_row["owner_name"])).casefold():
            conflicts.append(f"responsible OS={os_row.get('owner_name')} Bitrix={assigned_name}")
            notes.append("responsible_not_overwritten")
    elif assigned_name:
        notes.append(f"bitrix_responsible={assigned_name}")
    return adds, conflicts, notes


def lead_tutar(lead: dict) -> dict:
    amount = lead.get("OPPORTUNITY")
    currency = lead.get("CURRENCY_ID")
    return {
        "bitrix_field_id": TUTAR_FIELD_ID,
        "bitrix_field_ids": ["OPPORTUNITY", "CURRENCY_ID"],
        "bitrix_field_label": TUTAR_LABEL,
        "bitrix_api_labels": {"OPPORTUNITY": "Total", "CURRENCY_ID": "Currency"},
        "amount": str(amount) if amount not in (None, "") else "",
        "currency": str(currency or ""),
        "lead_id": str(lead.get("ID") or ""),
        "related_entity_type": "lead",
        "related_entity_id": str(lead.get("ID") or ""),
        "source": "bitrix_live",
        "not_amount_paid": True,
    }


def collect_tutars(deals: dict, leads: dict) -> list[dict]:
    items = []
    for did, deal in deals.items():
        row = deal_tutar({**deal, "ID": did})
        row["related_entity_type"] = "deal"
        row["related_entity_id"] = did
        row["source"] = "bitrix_live"
        if row.get("amount"):
            items.append(row)
    if items:
        return items
    for lid, lead in leads.items():
        row = lead_tutar({**lead, "ID": lid})
        if row.get("amount"):
            items.append(row)
    return items


def fetch_history(client: BitrixClient, mapping: dict) -> dict:
    comments: dict[str, dict] = {}
    activities: dict[str, dict] = {}
    chats: list[dict] = []
    messages: list[dict] = []

    entities = (
        [("contact", eid) for eid in mapping["contacts"]]
        + [("lead", eid) for eid in mapping["leads"]]
        + [("deal", eid) for eid in mapping["deals"]]
    )
    for etype, eid in entities:
        rows = list_all(client, "crm.timeline.comment.list", {"filter": {"ENTITY_TYPE": etype, "ENTITY_ID": eid}})
        for row in rows:
            cid = str(row.get("ID") or "")
            if cid:
                comments.setdefault(cid, {**row, "_entity_type": etype, "_entity_id": eid})
        owner = OWNER_TYPE[etype]
        acts = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": owner, "OWNER_ID": eid}})
        for row in acts:
            aid = str(row.get("ID") or "")
            if aid:
                activities.setdefault(aid, {**row, "_entity_type": etype, "_entity_id": eid})
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
                    nxt = min(i for i in ids if i) if any(ids) else None
                    if not nxt or nxt == last:
                        break
                    last = nxt
    return {
        "comments": list(comments.values()),
        "activities": list(activities.values()),
        "chats": chats,
        "messages": messages,
        "live_history_count": len(comments) + len(activities) + len(messages),
    }


def merge_archive_history(hist: dict, mapping: dict, archive_index: dict[tuple[str, str], dict]) -> dict:
    comments = {str(x.get("ID") or ""): x for x in hist.get("comments") or [] if x.get("ID")}
    activities = {str(x.get("ID") or ""): x for x in hist.get("activities") or [] if x.get("ID")}
    messages = list(hist.get("messages") or [])
    msg_keys = {
        f"{m.get('chat_id')}:{m.get('id')}"
        for m in messages
        if m.get("id") is not None
    }
    archive_extra = 0
    entities = (
        [("contact", eid) for eid in mapping["contacts"]]
        + [("lead", eid) for eid in mapping["leads"]]
        + [("deal", eid) for eid in mapping["deals"]]
    )
    for etype, eid in entities:
        rec = archive_index.get((etype, eid))
        if not rec:
            continue
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
                messages.append({**msg, "id": mid, "chat_id": chat_id, "_entity_type": etype, "_entity_id": eid, "_from_archive": True})
                msg_keys.add(key)
                archive_extra += 1
    hist = dict(hist)
    hist["comments"] = list(comments.values())
    hist["activities"] = list(activities.values())
    hist["messages"] = messages
    hist["archive_extra_count"] = archive_extra
    hist["archive_history_count"] = archive_extra
    return hist


def resolve_live(client: BitrixClient, person: dict, company_cache: dict, user_cache: dict) -> dict:
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
        existing = eid in (person.get("existing_contact_ids") if etype == "contact" else person.get("existing_lead_ids") or [])
        if not (phone_ok or email_ok or existing):
            return
        target = contact_ids if etype == "contact" else lead_ids
        if eid not in target:
            target[eid] = how if not existing else f"{how}+existing_live_id"

    select = ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "CONTACT_ID", "COMPANY_ID", "POST", "WEB", "IM"]
    seen: set[tuple] = set()
    for phone in list(pkeys)[:6]:
        key = ("dup", "CONTACT", phone)
        if key not in seen:
            seen.add(key)
            body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "PHONE", "values[]": [phone]})
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
    for eid in person.get("existing_contact_ids") or []:
        if eid not in contact_ids:
            got = client.call("crm.contact.get", {"id": eid})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider("contact", rec, "existing_live_id")
    for eid in person.get("existing_lead_ids") or []:
        if eid not in lead_ids:
            got = client.call("crm.lead.get", {"id": eid})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider("lead", rec, "existing_live_id")

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
    for eid, how in list(lead_ids.items()):
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
                    live_phones = set()
                    for value in phones_of(crec):
                        live_phones |= phone_keys(value)
                    if str(crec.get("ID")) in contact_ids or (pkeys & live_phones) or (set(emails) & set(emails_of(crec))):
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
    for eid in list(leads):
        rows = list_all(client, "crm.deal.list", {"filter": {"LEAD_ID": eid}})
        for rec in rows:
            did = str(rec.get("ID") or "")
            if not did or did in deals:
                continue
            full = client.call("crm.deal.get", {"id": did})
            payload = full.get("result") if isinstance(full.get("result"), dict) else rec
            payload["_how"] = "deal_lead_id"
            deals[did] = payload
    for did in person.get("existing_deal_ids") or []:
        if did in deals:
            continue
        full = client.call("crm.deal.get", {"id": did})
        payload = full.get("result") if isinstance(full.get("result"), dict) else {}
        linked_contact = str(payload.get("CONTACT_ID") or "")
        linked_lead = str(payload.get("LEAD_ID") or "")
        if payload and (linked_contact in contacts or linked_lead in leads):
            payload["_how"] = "existing_live_id"
            deals[did] = payload
    company_title = None
    assigned_name = None
    assigned_id = None
    primary = next(iter(contacts.values()), None) or next(iter(leads.values()), None)
    if primary:
        company_id = str(primary.get("COMPANY_ID") or "")
        if company_id and company_id not in {"0", ""}:
            if company_id not in company_cache:
                got = client.call("crm.company.get", {"id": company_id})
                company_cache[company_id] = (got.get("result") or {}) if isinstance(got.get("result"), dict) else {}
            company_title = str((company_cache.get(company_id) or {}).get("TITLE") or "") or None
        assigned_id = str(primary.get("ASSIGNED_BY_ID") or "")
        if assigned_id and assigned_id not in {"0", ""}:
            if assigned_id not in user_cache:
                got = client.call("user.get", {"ID": assigned_id})
                rows = got.get("result") if isinstance(got.get("result"), list) else []
                urec = rows[0] if rows and isinstance(rows[0], dict) else {}
                user_cache[assigned_id] = " ".join(p for p in [urec.get("NAME"), urec.get("LAST_NAME")] if p).strip()
            assigned_name = user_cache.get(assigned_id) or None
    if not contacts and not leads:
        if not pkeys and not emails and not (person.get("existing_contact_ids") or person.get("existing_lead_ids")):
            review.append("no_verified_bitrix_contact")
            review.append("no_phone_or_email_for_live_match")
        else:
            review.append("no_verified_bitrix_contact")
    slim_keep_extra = {"WEB", "IM", "COMPANY_ID"}
    def slim_plus(rec: dict) -> dict:
        out = slim_entity(rec)
        for key in slim_keep_extra:
            if key in rec:
                out[key] = rec.get(key)
        return out
    return {
        "contacts": {k: slim_plus(v) | {"_how": v.get("_how")} for k, v in contacts.items()},
        "leads": {k: slim_plus(v) | {"_how": v.get("_how")} for k, v in leads.items()},
        "deals": {k: slim_entity(v) | {"_how": v.get("_how"), "_title": v.get("TITLE")} for k, v in deals.items()},
        "review": review,
        "raw_contacts": contacts,
        "raw_leads": leads,
        "raw_deals": deals,
        "company_title": company_title,
        "assigned_name": assigned_name,
        "assigned_by_id": assigned_id,
        "match_methods": sorted({v.get("_how") for v in list(contacts.values()) + list(leads.values()) if v.get("_how")}),
    }


def apply_person(
    db: Session,
    actor: User | None,
    person: dict,
    mapping: dict,
    hist: dict,
    adds: dict,
    conflicts: list[str],
) -> dict:
    result = {"ids": False, "fields": 0, "history": 0, "tutar": 0, "ids_changed": False, "errors": []}
    contact = db.get(CrmContact, UUID(person["cid"]))
    if contact is None:
        result["errors"].append("contact_missing")
        return result
    meta = dict(contact.metadata_json or {})
    live = dict(meta.get("bitrix_live") or {})
    old_contact_ids = [str(x) for x in (live.get("contact_ids") or [])]
    old_lead_ids = [str(x) for x in (live.get("lead_ids") or [])]
    old_deal_ids = [str(x) for x in (live.get("deal_ids") or [])]
    stages = []
    for rec in list(mapping["leads"].values()) + list(mapping["deals"].values()):
        stage = rec.get("STAGE_ID") or rec.get("STATUS_ID")
        if stage:
            stages.append(str(stage))
    tutars = collect_tutars(mapping["deals"], mapping["leads"])
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
            "company_title": mapping.get("company_title"),
            "assigned_by_id": mapping.get("assigned_by_id"),
            "assigned_name": mapping.get("assigned_name"),
            "live_stage_or_status": stages,
            "tutar_ve_para_birimi": tutars,
            "updated_at": utc_now(),
            "source": "bitrix_live",
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
    }
    for add_key, (attr, limit) in field_map.items():
        value = adds.get(add_key)
        if value:
            setattr(contact, attr, str(value)[:limit])
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


def format_tutar(tutars: list[dict]) -> tuple[str, str]:
    amounts = [t["amount"] for t in tutars if t.get("amount")]
    currencies = list(dict.fromkeys(t["currency"] for t in tutars if t.get("currency")))
    return " | ".join(amounts), " | ".join(currencies)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--refresh", action="store_true")
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
    archive_index = load_archive_index()
    company_cache: dict[str, dict] = {}
    user_cache: dict[str, str] = {}
    rows = []
    totals = Counter()
    conflicts_out = []
    try:
        for index, person in enumerate(people, start=1):
            print(f"[{index}/{len(people)}] {person['display_name']}", flush=True)
            snap_path = OUT / "raw" / f"{person['cid']}.json"
            if snap_path.exists() and not args.refresh:
                snap = json.loads(snap_path.read_text(encoding="utf-8"))
            else:
                mapping = resolve_live(client, person, company_cache, user_cache)
                hist = (
                    fetch_history(client, mapping)
                    if mapping["contacts"] or mapping["leads"] or mapping["deals"]
                    else {"comments": [], "activities": [], "chats": [], "messages": [], "live_history_count": 0}
                )
                hist = merge_archive_history(hist, mapping, archive_index)
                primary_contact = {}
                contacts_map = mapping.get("raw_contacts") or mapping["contacts"]
                if len(contacts_map) == 1:
                    primary_contact = next(iter(contacts_map.values()))
                elif contacts_map:
                    primary_contact = next(iter(contacts_map.values()))
                    review = list(mapping.get("review") or [])
                    if "multiple_or_first_contact_used" not in review:
                        review.append("multiple_or_first_contact_used")
                    mapping["review"] = review
                elif mapping.get("raw_leads") or mapping["leads"]:
                    primary_contact = next(iter((mapping.get("raw_leads") or mapping["leads"]).values()))
                snap = {
                    "person": {
                        k: person[k]
                        for k in ("cid", "display_name", "primary_phone", "primary_email", "organization_name", "owner_name")
                        if k in person
                    },
                    "mapping": {
                        "contacts": mapping["contacts"],
                        "leads": mapping["leads"],
                        "deals": mapping["deals"],
                        "review": mapping["review"],
                        "company_title": mapping.get("company_title"),
                        "assigned_name": mapping.get("assigned_name"),
                        "assigned_by_id": mapping.get("assigned_by_id"),
                        "match_methods": mapping.get("match_methods") or [],
                        "raw_contacts": {
                            k: slim_entity(v)
                            | {
                                "_how": v.get("_how"),
                                "NAME": v.get("NAME"),
                                "LAST_NAME": v.get("LAST_NAME"),
                                "POST": v.get("POST"),
                                "PHONE": v.get("PHONE"),
                                "EMAIL": v.get("EMAIL"),
                                "WEB": v.get("WEB"),
                                "IM": v.get("IM"),
                                "ADDRESS": v.get("ADDRESS"),
                                "ADDRESS_2": v.get("ADDRESS_2"),
                                "ADDRESS_CITY": v.get("ADDRESS_CITY"),
                                "ADDRESS_REGION": v.get("ADDRESS_REGION"),
                                "ADDRESS_PROVINCE": v.get("ADDRESS_PROVINCE"),
                                "ADDRESS_POSTAL_CODE": v.get("ADDRESS_POSTAL_CODE"),
                                "ADDRESS_COUNTRY": v.get("ADDRESS_COUNTRY"),
                                "COMMENTS": v.get("COMMENTS"),
                                "COMPANY_ID": v.get("COMPANY_ID"),
                            }
                            for k, v in (mapping.get("raw_contacts") or mapping["contacts"]).items()
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
                snap_path.write_text(json.dumps(snap, ensure_ascii=False, default=str), encoding="utf-8")
            contacts_map = snap["mapping"].get("raw_contacts") or snap["mapping"]["contacts"]
            primary_contact = snap.get("primary_contact") or {}
            if not primary_contact and contacts_map:
                primary_contact = next(iter(contacts_map.values()))
            elif not primary_contact and snap["mapping"]["leads"]:
                primary_contact = next(iter(snap["mapping"]["leads"].values()))
            adds, person_conflicts, _notes = extra_safe_adds(
                person,
                primary_contact,
                snap["mapping"].get("company_title"),
                snap["mapping"].get("assigned_name"),
            )
            if len(contacts_map) > 1 or person_conflicts:
                for key in ("first_name", "last_name", "notes", "organization_name"):
                    adds.pop(key, None)
            plans = planned_history(person, snap["history"])
            tutars = collect_tutars(snap["mapping"]["deals"], snap["mapping"]["leads"])
            amount, currency = format_tutar(tutars)
            apply_result: dict[str, Any] = {}
            if apply and (snap["mapping"]["contacts"] or snap["mapping"]["leads"] or snap["mapping"]["deals"]):
                apply_result = apply_person(
                    db,
                    actor,
                    person,
                    {
                        "contacts": snap["mapping"]["contacts"],
                        "leads": snap["mapping"]["leads"],
                        "deals": snap["mapping"]["deals"],
                        "company_title": snap["mapping"].get("company_title"),
                        "assigned_name": snap["mapping"].get("assigned_name"),
                        "assigned_by_id": snap["mapping"].get("assigned_by_id"),
                    },
                    snap["history"],
                    adds,
                    person_conflicts,
                )
                db.commit()
            crm_history_after = person["crm_history"] + (apply_result.get("history") or 0 if apply else 0)
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
            live_h = snap["history"].get("live_history_count") or 0
            archive_extra = snap["history"].get("archive_extra_count") or 0
            compare_h = live_h if live_h else archive_extra
            if compare_h == 0:
                hist_complete = "NA"
            elif crm_history_after >= compare_h:
                hist_complete = "YES"
            else:
                hist_complete = "NO"
            matched = bool(snap["mapping"]["contacts"] or snap["mapping"]["leads"])
            info_complete = "YES" if matched and primary_contact and not person_conflicts else "NO"
            review_bits = list(snap["mapping"].get("review") or []) + person_conflicts
            methods = snap["mapping"].get("match_methods") or []
            if not methods:
                methods = sorted(
                    {
                        str(v.get("_how"))
                        for v in list(snap["mapping"]["contacts"].values()) + list(snap["mapping"]["leads"].values())
                        if isinstance(v, dict) and v.get("_how")
                    }
                )
            row = {
                "canonical_uuid": person["cid"],
                "name": person["display_name"],
                "bitrix_contact_ids": ",".join(sorted(snap["mapping"]["contacts"])),
                "lead_ids": ",".join(sorted(snap["mapping"]["leads"])),
                "deal_ids": ",".join(sorted(snap["mapping"]["deals"])),
                "match_method": ",".join(methods),
                "info_complete": info_complete,
                "tutar_ve_para_birimi": amount,
                "currency": currency,
                "live_history_count": live_h,
                "crm_history_count": crm_history_after,
                "crm_history_count_before": person["crm_history"],
                "history_imported": apply_result.get("history") if apply else len(plans),
                "history_complete": hist_complete,
                "conflicts": "; ".join(person_conflicts),
                "review_required": "; ".join(review_bits),
                "notes": (
                    f"safe_adds={list(adds)}; comments={len(snap['history'].get('comments') or [])}; "
                    f"activities={len(snap['history'].get('activities') or [])}; "
                    f"wa={len(snap['history'].get('messages') or [])}; "
                    f"archive_extra={archive_extra}; ids_changed={apply_result.get('ids_changed')}"
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
            totals["safe_field_adds"] += len(adds)
            totals["fields_written"] += int(apply_result.get("fields") or 0)
            if amount:
                totals["tutar"] += 1
            totals["tutar_written"] += int(1 if apply and apply_result.get("tutar") else 0)
            if apply_result.get("ids_changed"):
                totals["ids_corrected"] += 1
            if hist_complete == "YES":
                totals["history_complete"] += 1
            if review_bits:
                totals["review_required"] += 1
                conflicts_out.append({"person": person["display_name"], "uuid": person["cid"], "issues": review_bits})
        if apply:
            db.commit()
        active_count = db.execute(
            text(
                """
                select count(*) from crm_contacts
                where status='ACTIVE' and archived_at is null
                  and metadata_json::jsonb->'bitrix_import'->'source_roles' ? 'active_customers'
                """
            )
        ).scalar() or 0
        contact_total = db.execute(text("select count(*) from crm_contacts")).scalar() or 0
        summary = {
            "generated_at": utc_now(),
            "apply": apply,
            "backup_path": BACKUP_PATH,
            "active_customers_checked": len(rows),
            "matched": totals["matched"],
            "unmatched": totals["unmatched"],
            "corrected_bitrix_ids": totals["ids_corrected"],
            "missing_contact_fields_recovered": totals["fields_written"] if apply else totals["safe_field_adds"],
            "tutar_ve_para_birimi_values_recovered": totals["tutar_written"] if apply else totals["tutar"],
            "missing_history_imported": totals["history_imported"] if apply else totals["history_plans"],
            "history_complete_count": totals["history_complete"],
            "conflicts_review_required": totals["review_required"],
            "final_active_count": active_count,
            "crm_contacts_unchanged_total": contact_total,
            "documents_recovered": 0,
            "bitrix_calls": client.call_count,
            "totals": dict(totals),
            "conflicts": conflicts_out,
        }
        csv_fields = [
            "canonical_uuid", "name", "bitrix_contact_ids", "lead_ids", "deal_ids", "match_method",
            "info_complete", "tutar_ve_para_birimi", "currency", "live_history_count",
            "crm_history_count", "history_complete", "conflicts", "review_required",
            "crm_history_count_before", "history_imported", "notes",
        ]
        with (OUT / "reports" / "ACTIVE_CONTACT_COMPLETENESS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        (OUT / "reports" / "ACTIVE_CONTACT_COMPLETENESS_SUMMARY.json").write_text(
            json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
