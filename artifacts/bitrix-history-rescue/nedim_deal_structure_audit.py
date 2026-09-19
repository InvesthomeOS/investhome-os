"""Read-only Bitrix + OS audit of Nedim Kondu deals 198/656/720.

Does not write CRM, Bitrix, or documents. Never prints webhook URLs.
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
from collections import Counter
from pathlib import Path
from typing import Any

from sqlalchemy import text

from investhome_api.db.session import SessionLocal

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

OUT = Path("/export/2026-09-final/NEDIM_BITRIX_DEAL_STRUCTURE_AUDIT")
DEAL_IDS = ("198", "656", "720")
NEDIM_CONTACT = "588"
NEDIM_LEAD = "12512"
NEDIM_UUID = "811c6aed-5f58-4c89-a9b1-0eebed64b9cf"
NEDIM_ALIAS = "ee093070-b3a4-4fb3-b3ca-3aa92379a187"
OWNER = {"lead": 1, "deal": 2, "contact": 3, "company": 4}
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
PAYMENT_RE = re.compile(
    r"sat[iı][sş]|yat[iı]r[iı]m|öde|ode|tutar|bedel|deposit|kapora|pe[sş]inat|"
    r"kalan|toplam|closing|unit|daire|proje|project|opportunity|amount|paid|"
    r"payment|currency|anla[sş]|gelir|mortgage|llc",
    re.I,
)
FOLD = str.maketrans(
    {"ı": "i", "İ": "i", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c"}
)


def fold(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").translate(FOLD).casefold()).strip()


def redact(value: Any) -> Any:
    if isinstance(value, str):
        return WEBHOOK_RE.sub("[REDACTED_URL]", value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def flatten(payload: dict) -> dict:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            for inner_k, inner_v in value.items():
                out[f"{key}[{inner_k}]"] = inner_v
        elif isinstance(value, list) and key.endswith("[]"):
            out[key] = value
        else:
            out[key] = value
    return out


def list_all(client: BitrixClient, method: str, payload: dict) -> list[dict]:
    rows: list[dict] = []
    start = 0
    seen: set[int] = set()
    while start not in seen:
        seen.add(start)
        body = client.call(method, {**flatten(payload), "start": start})
        result = body.get("result")
        chunk = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else [])
        if body.get("error") and not rows:
            return [{"_error": body.get("error"), "_error_description": body.get("error_description")}]
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend([x for x in chunk if isinstance(x, dict)])
        nxt = body.get("next")
        if not isinstance(nxt, int):
            break
        start = nxt
    return rows


def get_result(client: BitrixClient, method: str, payload: dict) -> dict:
    body = client.call(method, payload)
    rec = body.get("result")
    if isinstance(rec, dict):
        return rec
    return {"_error": body.get("error"), "_error_description": body.get("error_description"), "_raw_type": type(rec).__name__}


def label_of(spec: dict) -> str:
    for key in ("formLabel", "listLabel", "filterLabel", "title", "editFormLabel"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip() and not val.startswith("UF_"):
            return val.strip()
        if isinstance(val, dict):
            for lang in ("tr", "en", "br"):
                if val.get(lang):
                    return str(val[lang]).strip()
            for item in val.values():
                if item:
                    return str(item).strip()
    return str(spec.get("title") or "")


def phones_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("PHONE") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]))
        elif isinstance(item, str) and item.strip():
            out.append(item)
    return out


def emails_of(rec: dict) -> list[str]:
    out = []
    for item in rec.get("EMAIL") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]).strip().lower())
        elif isinstance(item, str) and item.strip():
            out.append(item.strip().lower())
    return [e for e in out if e]


def display_name(rec: dict) -> str:
    parts = [rec.get("NAME"), rec.get("SECOND_NAME"), rec.get("LAST_NAME")]
    name = " ".join(str(p).strip() for p in parts if p)
    return name or str(rec.get("TITLE") or rec.get("COMPANY_TITLE") or rec.get("ID") or "")


def enum_label(spec: dict, value: Any) -> Any:
    items = spec.get("items")
    if not isinstance(items, list):
        return value
    wanted = str(value)
    for item in items:
        if not isinstance(item, dict):
            continue
        if str(item.get("ID") or item.get("id") or "") == wanted:
            return item.get("VALUE") or item.get("value") or value
    return value


def file_refs(value: Any) -> list[dict]:
    refs: list[dict] = []

    def walk(node: Any) -> None:
        if isinstance(node, list):
            for item in node:
                walk(item)
            return
        if isinstance(node, dict):
            fid = node.get("id") or node.get("ID") or node.get("FILE_ID") or node.get("fileId")
            name = node.get("name") or node.get("NAME") or node.get("fileName") or node.get("FILE_NAME")
            url = node.get("url") or node.get("downloadUrl") or node.get("showUrl") or node.get("downloadUrlMachine")
            if fid or name:
                refs.append({"id": str(fid) if fid else None, "name": name, "has_url": bool(url)})
            return
        if isinstance(node, (int, str)) and str(node).isdigit() and int(str(node)) > 0:
            refs.append({"id": str(node), "name": None, "has_url": False})

    walk(value)
    return refs


def classify_activity(item: dict) -> str:
    subject = str(item.get("SUBJECT") or "")
    low = subject.casefold()
    provider = str(item.get("PROVIDER_ID") or "").upper()
    provider_type = str(item.get("PROVIDER_TYPE_ID") or "").upper()
    if "IMOPENLINES" in provider or "whatsapp" in low or "open channel" in low or "whatcrm" in low or "WAZZUP" in provider:
        return "whatsapp_open_channel"
    if "EMAIL" in provider or "MAIL" in provider or provider_type == "EMAIL":
        return "email"
    if "TASK" in provider or provider_type == "TASK":
        return "task"
    if "CALL" in provider or "VOX" in provider:
        return "call"
    if "SMS" in provider:
        return "sms"
    type_id = str(item.get("TYPE_ID") or "")
    return {"1": "meeting", "2": "call", "4": "email", "6": "task"}.get(type_id, "other")


def slim_activity(item: dict) -> dict:
    bindings = item.get("BINDINGS") or item.get("bindings") or []
    files = file_refs(item.get("FILES") or item.get("STORAGE_ELEMENT_IDS") or item.get("UF_CRM_TASK"))
    return {
        "id": item.get("ID"),
        "type": classify_activity(item),
        "type_id": item.get("TYPE_ID"),
        "provider_id": item.get("PROVIDER_ID"),
        "provider_type_id": item.get("PROVIDER_TYPE_ID"),
        "subject": item.get("SUBJECT"),
        "completed": item.get("COMPLETED"),
        "direction": item.get("DIRECTION"),
        "owner_type_id": item.get("OWNER_TYPE_ID"),
        "owner_id": item.get("OWNER_ID"),
        "responsible_id": item.get("RESPONSIBLE_ID"),
        "created": item.get("CREATED") or item.get("CREATED_TIME"),
        "start_time": item.get("START_TIME"),
        "description_len": len(str(item.get("DESCRIPTION") or "")),
        "bindings": bindings if isinstance(bindings, list) else [bindings],
        "files": files,
        "associated_entity_id": item.get("ASSOCIATED_ENTITY_ID"),
        "settings_keys": sorted((item.get("SETTINGS") or {}).keys()) if isinstance(item.get("SETTINGS"), dict) else [],
    }


def slim_comment(item: dict) -> dict:
    return {
        "id": item.get("ID"),
        "created": item.get("CREATED") or item.get("CREATED_TIME"),
        "author_id": item.get("AUTHOR_ID"),
        "text": str(item.get("COMMENT") or item.get("TEXT") or "")[:400],
        "files": file_refs(item.get("FILES") or item.get("ATTACHMENTS")),
        "entity_type": item.get("ENTITY_TYPE") or item.get("ENTITYTYPEID"),
        "entity_id": item.get("ENTITY_ID") or item.get("ENTITYID"),
    }


def history(client: BitrixClient, etype: str, eid: str) -> dict:
    owner = OWNER[etype]
    comments = list_all(client, "crm.timeline.comment.list", {"filter": {"ENTITY_TYPE": etype, "ENTITY_ID": eid}})
    activities = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": owner, "OWNER_ID": eid}})
    if comments and comments[0].get("_error"):
        comments_err = comments[0]
        comments = []
    else:
        comments_err = None
    if activities and activities[0].get("_error"):
        activities_err = activities[0]
        activities = []
    else:
        activities_err = None
    types = Counter(classify_activity(a) for a in activities)
    files = []
    for act in activities:
        for ref in file_refs(act.get("FILES") or act.get("STORAGE_ELEMENT_IDS")):
            files.append({"source": "activity", "activity_id": act.get("ID"), **ref})
    for comment in comments:
        for ref in file_refs(comment.get("FILES") or comment.get("ATTACHMENTS")):
            files.append({"source": "timeline_comment", "comment_id": comment.get("ID"), **ref})
    return {
        "comments_count": len(comments),
        "activities_count": len(activities),
        "activity_types": dict(types),
        "comments_error": comments_err,
        "activities_error": activities_err,
        "comments": [slim_comment(c) for c in comments],
        "activities": [slim_activity(a) for a in activities],
        "file_refs": files,
    }


def tasks_for_crm(client: BitrixClient, crm_code: str) -> list[dict]:
    rows = list_all(client, "tasks.task.list", {"filter": {"UF_CRM_TASK": crm_code}, "select[]": ["ID", "TITLE", "STATUS", "RESPONSIBLE_ID", "CREATED_DATE", "UF_CRM_TASK"]})
    if rows and rows[0].get("_error"):
        return rows[:1]
    slim = []
    for row in rows:
        task = row.get("task") if isinstance(row.get("task"), dict) else row
        slim.append(
            {
                "id": task.get("id") or task.get("ID"),
                "title": task.get("title") or task.get("TITLE"),
                "status": task.get("status") or task.get("STATUS"),
                "responsible_id": task.get("responsibleId") or task.get("RESPONSIBLE_ID"),
                "created": task.get("createdDate") or task.get("CREATED_DATE"),
                "uf_crm_task": task.get("ufCrmTask") or task.get("UF_CRM_TASK"),
            }
        )
    return slim


def decode_deal(deal: dict, fields: dict, users: dict, stages: dict, categories: dict) -> dict:
    custom = []
    payment = []
    files = []
    for key, value in deal.items():
        if not str(key).startswith("UF_"):
            continue
        if value in (None, "", [], {}, "0", 0, False):
            continue
        spec = fields.get(key) if isinstance(fields.get(key), dict) else {}
        label = label_of(spec) or key
        ftype = spec.get("type")
        decoded = enum_label(spec, value) if ftype in {"enumeration", "crm_status"} else value
        row = {"id": key, "label": label, "type": ftype, "value": redact(decoded)}
        custom.append(row)
        if ftype == "file" or file_refs(value):
            for ref in file_refs(value):
                files.append({"source": f"deal_field:{key}", "label": label, **ref})
        if PAYMENT_RE.search(f"{label} {key}") or ftype in {"money", "double", "integer"}:
            payment.append(row)
    assigned = str(deal.get("ASSIGNED_BY_ID") or "")
    category = str(deal.get("CATEGORY_ID") or "0")
    stage = str(deal.get("STAGE_ID") or "")
    return {
        "id": str(deal.get("ID") or ""),
        "title": deal.get("TITLE"),
        "category_id": category,
        "category_name": categories.get(category) or categories.get(int(category) if category.isdigit() else category),
        "stage_id": stage,
        "stage_name": stages.get(stage),
        "opportunity": deal.get("OPPORTUNITY"),
        "currency_id": deal.get("CURRENCY_ID"),
        "opportunity_account": deal.get("OPPORTUNITY_ACCOUNT"),
        "account_currency_id": deal.get("ACCOUNT_CURRENCY_ID"),
        "is_manual_opportunity": deal.get("IS_MANUAL_OPPORTUNITY"),
        "probability": deal.get("PROBABILITY"),
        "begin_date": deal.get("BEGINDATE"),
        "close_date": deal.get("CLOSEDATE"),
        "date_create": deal.get("DATE_CREATE"),
        "date_modify": deal.get("DATE_MODIFY"),
        "closed": deal.get("CLOSED"),
        "opened": deal.get("OPENED"),
        "type_id": deal.get("TYPE_ID"),
        "source_id": deal.get("SOURCE_ID"),
        "source_description": deal.get("SOURCE_DESCRIPTION"),
        "comments": deal.get("COMMENTS"),
        "additional_info": deal.get("ADDITIONAL_INFO"),
        "assigned_by_id": assigned,
        "assigned_by_name": users.get(assigned),
        "contact_id": deal.get("CONTACT_ID"),
        "company_id": deal.get("COMPANY_ID"),
        "lead_id": deal.get("LEAD_ID"),
        "originator_id": deal.get("ORIGINATOR_ID"),
        "origin_id": deal.get("ORIGIN_ID"),
        "parent_id_deal": deal.get("PARENT_ID_2") or deal.get("PARENT_ID_DEAL"),
        "custom_fields": custom,
        "payment_like_fields": payment,
        "file_fields": files,
        "raw_standard_keys": sorted(k for k in deal.keys() if not str(k).startswith("UF_")),
    }


def os_contacts_for_bitrix(db, contact_id: str | None = None, lead_id: str | None = None, deal_id: str | None = None) -> list[dict]:
    needles = []
    if contact_id:
        needles.append(f"%bitrix_contact:{contact_id}%")
        needles.append(f"%:{contact_id}%")
    if lead_id:
        needles.append(f"%bitrix_lead:{lead_id}%")
    if deal_id:
        needles.append(f"%:{deal_id}%")
        needles.append(f"%bitrix_deal:{deal_id}%")
    if not needles:
        return []
    clauses = " OR ".join([f"metadata_json::text ilike :n{i}" for i in range(len(needles))])
    params = {f"n{i}": v for i, v in enumerate(needles)}
    rows = db.execute(
        text(
            f"""
            select id::text, display_name, primary_phone, primary_email, status,
                   metadata_json->'bitrix_import'->'external_ids' as external_ids
            from crm_contacts
            where {clauses}
            order by created_at
            """
        ),
        params,
    ).mappings().all()
    out = []
    for row in rows:
        ext = row["external_ids"] if isinstance(row["external_ids"], list) else []
        ext_s = [str(x) for x in ext]
        keep = False
        if contact_id and any(x.endswith(f":{contact_id}") or x == f"bitrix_contact:{contact_id}" for x in ext_s):
            keep = True
        if lead_id and any(x.endswith(f"bitrix_lead:{lead_id}") or x.endswith(f":{lead_id}") and "lead" in x.lower() for x in ext_s):
            keep = True
        if deal_id and any(x.endswith(f":{deal_id}") for x in ext_s):
            keep = True
        if keep:
            out.append(
                {
                    "id": row["id"],
                    "display_name": row["display_name"],
                    "phone": row["primary_phone"],
                    "email": row["primary_email"],
                    "status": row["status"],
                    "external_ids": ext_s,
                }
            )
    return out


def main() -> int:
    env = dict(os.environ)
    if not (env.get("BITRIX_ADMIN_WEBHOOK_URL") or env.get("BITRIX_WEBHOOK_URL")):
        env.update(load_env(ENV_PATH) if ENV_PATH.exists() else {})
    webhook = webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or env.get("BITRIX_WEBHOOK_URL") or "")
    if not webhook:
        print("MISSING_WEBHOOK")
        return 1
    client = BitrixClient(webhook)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)

    fields = get_result(client, "crm.deal.fields", {})
    field_map = fields if all(isinstance(v, dict) for v in fields.values() if v) else {}

    users: dict[str, str] = {}

    def load_user(uid: str) -> str:
        if not uid or uid in {"0", "None"}:
            return ""
        if uid in users:
            return users[uid]
        body = client.call("user.get", {"ID": uid})
        rec = body.get("result")
        if isinstance(rec, list) and rec:
            rec = rec[0]
        if not isinstance(rec, dict):
            users[uid] = uid
            return uid
        name = " ".join(p for p in [rec.get("NAME"), rec.get("LAST_NAME")] if p) or uid
        users[uid] = name
        return name

    categories: dict[str, str] = {"0": "General CRM"}
    cat_rows = list_all(client, "crm.dealcategory.list", {})
    for row in cat_rows:
        categories[str(row.get("ID") or row.get("id") or "")] = str(row.get("NAME") or row.get("name") or "")

    stages: dict[str, str] = {}
    for cat_id in sorted({*(categories.keys()), "0", "1", "2", "3", "4", "5"}):
        body = client.call("crm.dealcategory.stage.list", {"id": cat_id})
        result = body.get("result") or []
        if isinstance(result, dict):
            result = list(result.values())
        for row in result if isinstance(result, list) else []:
            if isinstance(row, dict):
                stages[str(row.get("STATUS_ID") or row.get("STATUSID") or row.get("id") or "")] = str(
                    row.get("NAME") or row.get("name") or ""
                )

    report: dict[str, Any] = {
        "read_only": True,
        "deals": {},
        "nedim_contact": {},
        "nedim_lead": {},
        "izzet": {},
        "os": {},
        "model_notes": {},
    }

    contact_cache: dict[str, dict] = {}
    company_cache: dict[str, dict] = {}

    def load_contact(cid: str) -> dict:
        if cid in contact_cache:
            return contact_cache[cid]
        rec = get_result(client, "crm.contact.get", {"id": cid})
        contact_cache[cid] = rec
        return rec

    def load_company(cid: str) -> dict:
        if cid in company_cache:
            return company_cache[cid]
        rec = get_result(client, "crm.company.get", {"id": cid})
        company_cache[cid] = rec
        return rec

    for did in DEAL_IDS:
        deal = get_result(client, "crm.deal.get", {"id": did})
        load_user(str(deal.get("ASSIGNED_BY_ID") or ""))
        decoded = decode_deal(deal, field_map, users, stages, categories)
        items = client.call("crm.deal.contact.items.get", {"id": did}).get("result") or []
        if not isinstance(items, list):
            items = []
        linked = []
        seen_cids = set()
        primary = str(deal.get("CONTACT_ID") or "")
        if primary not in {"", "0"}:
            rec = load_contact(primary)
            linked.append(
                {
                    "source": "deal.CONTACT_ID",
                    "is_primary": True,
                    "contact_id": primary,
                    "name": display_name(rec),
                    "phones": phones_of(rec),
                    "emails": emails_of(rec),
                    "company_id": rec.get("COMPANY_ID"),
                    "lead_id": rec.get("LEAD_ID") or rec.get("ORIGIN_ID"),
                    "role_id": None,
                }
            )
            seen_cids.add(primary)
        for item in items:
            if not isinstance(item, dict):
                continue
            cid = str(item.get("CONTACT_ID") or "")
            if not cid or cid in seen_cids:
                if cid in seen_cids:
                    for row in linked:
                        if row["contact_id"] == cid:
                            row["role_id"] = item.get("ROLE_ID")
                            row["sort"] = item.get("SORT")
                            row["is_primary_item"] = item.get("IS_PRIMARY")
                continue
            rec = load_contact(cid)
            linked.append(
                {
                    "source": "crm.deal.contact.items.get",
                    "is_primary": str(item.get("IS_PRIMARY") or "").upper() in {"Y", "1", "TRUE"},
                    "contact_id": cid,
                    "name": display_name(rec),
                    "phones": phones_of(rec),
                    "emails": emails_of(rec),
                    "company_id": rec.get("COMPANY_ID"),
                    "lead_id": rec.get("LEAD_ID") or rec.get("ORIGIN_ID"),
                    "role_id": item.get("ROLE_ID"),
                    "sort": item.get("SORT"),
                    "is_primary_item": item.get("IS_PRIMARY"),
                }
            )
            seen_cids.add(cid)

        company = None
        company_id = str(deal.get("COMPANY_ID") or "")
        if company_id not in {"", "0"}:
            crec = load_company(company_id)
            company = {
                "id": company_id,
                "title": crec.get("TITLE"),
                "phones": phones_of(crec),
                "emails": emails_of(crec),
            }

        products = client.call("crm.deal.productrows.get", {"id": did}).get("result")
        hist = history(client, "deal", did)
        tasks = tasks_for_crm(client, f"D_{did}") + tasks_for_crm(client, f"D{did}")

        report["deals"][did] = {
            "deal": decoded,
            "linked_contacts": linked,
            "company": company,
            "product_rows": products if isinstance(products, list) else products,
            "history": hist,
            "tasks": tasks,
        }

    nedim_contact = load_contact(NEDIM_CONTACT)
    nedim_lead = get_result(client, "crm.lead.get", {"id": NEDIM_LEAD})
    nedim_deals = list_all(client, "crm.deal.list", {"filter": {"CONTACT_ID": NEDIM_CONTACT}, "select[]": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "COMPANY_ID", "BEGINDATE"]})
    report["nedim_contact"] = {
        "id": NEDIM_CONTACT,
        "name": display_name(nedim_contact),
        "phones": phones_of(nedim_contact),
        "emails": emails_of(nedim_contact),
        "company_id": nedim_contact.get("COMPANY_ID"),
        "assigned_by_id": nedim_contact.get("ASSIGNED_BY_ID"),
        "assigned_by_name": load_user(str(nedim_contact.get("ASSIGNED_BY_ID") or "")),
        "comments": nedim_contact.get("COMMENTS"),
        "history": history(client, "contact", NEDIM_CONTACT),
        "tasks": tasks_for_crm(client, f"C_{NEDIM_CONTACT}"),
        "deals_listed_by_contact_id": [
            {"id": r.get("ID"), "title": r.get("TITLE"), "stage": r.get("STAGE_ID"), "amount": r.get("OPPORTUNITY"), "currency": r.get("CURRENCY_ID")}
            for r in nedim_deals
            if not r.get("_error")
        ],
    }
    report["nedim_lead"] = {
        "id": NEDIM_LEAD,
        "title": nedim_lead.get("TITLE"),
        "name": display_name(nedim_lead),
        "status_id": nedim_lead.get("STATUS_ID"),
        "phones": phones_of(nedim_lead),
        "emails": emails_of(nedim_lead),
        "contact_id": nedim_lead.get("CONTACT_ID"),
        "opportunity": nedim_lead.get("OPPORTUNITY"),
        "currency_id": nedim_lead.get("CURRENCY_ID"),
        "history": history(client, "lead", NEDIM_LEAD),
        "tasks": tasks_for_crm(client, f"L_{NEDIM_LEAD}"),
    }

    izzet_hits = []
    for did, payload in report["deals"].items():
        for row in payload["linked_contacts"]:
            n = fold(row.get("name"))
            if "izzet" in n or "izzet" in n.replace("i", "i"):
                izzet_hits.append({"deal": did, **row})
            if "dincer" in n or "dinçer" in fold(row.get("name")):
                izzet_hits.append({"deal": did, **row})
    # unique by contact_id
    seen = set()
    unique_izzet = []
    for row in izzet_hits:
        cid = row.get("contact_id")
        if cid in seen:
            continue
        seen.add(cid)
        unique_izzet.append(row)

    report["izzet"]["from_deal_links_only"] = unique_izzet
    report["izzet"]["name_search_not_used_for_ownership"] = True

    db = SessionLocal()
    os_nedim = db.execute(
        text(
            """
            select id::text, display_name, primary_phone, primary_email, status,
                   metadata_json->'bitrix_import'->'external_ids' as external_ids,
                   metadata_json->'bitrix_live'->'tutar_ve_para_birimi' as live_tutar
            from crm_contacts
            where id in (:a, :b)
            """
        ),
        {"a": NEDIM_UUID, "b": NEDIM_ALIAS},
    ).mappings().all()
    os_agreements = db.execute(
        text(
            """
            select a.id::text, a.contact_id::text, c.display_name, a.project_group, a.unit_number,
                   a.status::text, a.agreement_date::text,
                   a.metadata_json->>'bitrix_deal_id' as bitrix_deal_id,
                   a.metadata_json->>'tutar_ve_para_birimi_amount' as tutar,
                   a.metadata_json->>'tutar_ve_para_birimi_currency' as currency
            from crm_agreements a
            join crm_contacts c on c.id = a.contact_id
            where a.contact_id in (:a, :b)
               or a.metadata_json->>'bitrix_deal_id' in ('198','656','720')
               or (a.project_group in ('uniloft','2319_ontario') and a.unit_number in ('209','403'))
            order by a.project_group, a.unit_number, c.display_name
            """
        ),
        {"a": NEDIM_UUID, "b": NEDIM_ALIAS},
    ).mappings().all()
    os_acts = db.execute(
        text(
            """
            select entity_id::text, count(*) as n,
                   count(*) filter (where metadata_json->'bitrix_history'->>'bitrix_entity_type'='deal'
                     and metadata_json->'bitrix_history'->>'bitrix_entity_id'='198') as deal_198,
                   count(*) filter (where metadata_json->'bitrix_history'->>'bitrix_entity_type'='deal'
                     and metadata_json->'bitrix_history'->>'bitrix_entity_id'='656') as deal_656,
                   count(*) filter (where metadata_json->'bitrix_history'->>'bitrix_entity_type'='deal'
                     and metadata_json->'bitrix_history'->>'bitrix_entity_id'='720') as deal_720,
                   count(*) filter (where metadata_json->'bitrix_history'->>'bitrix_entity_type'='contact') as contact_owner,
                   count(*) filter (where metadata_json->'bitrix_history'->>'bitrix_entity_type'='lead') as lead_owner
            from crm_activities
            where entity_type='CONTACT' and entity_id in (:a, :b) and archived_at is null
            group by entity_id
            """
        ),
        {"a": NEDIM_UUID, "b": NEDIM_ALIAS},
    ).mappings().all()

    izzet_os = []
    for row in unique_izzet:
        izzet_os.extend(os_contacts_for_bitrix(db, contact_id=str(row.get("contact_id"))))
        rec = contact_cache.get(str(row.get("contact_id")) or "") or {}
        if rec.get("LEAD_ID"):
            izzet_os.extend(os_contacts_for_bitrix(db, lead_id=str(rec.get("LEAD_ID"))))
        phone = (phones_of(rec) or row.get("phones") or [None])[0]
        email = (emails_of(rec) or row.get("emails") or [None])[0]
        extra = db.execute(
            text(
                """
                select id::text, display_name, primary_phone, primary_email, status,
                       metadata_json->'bitrix_import'->'external_ids' as external_ids
                from crm_contacts
                where (:email <> '' and lower(coalesce(primary_email,'')) = :email)
                   or (:phone <> '' and right(regexp_replace(coalesce(primary_phone,''), '[^0-9]', '', 'g'), 10)
                        = right(regexp_replace(:phone, '[^0-9]', '', 'g'), 10))
                """
            ),
            {"email": (email or "").lower(), "phone": phone or ""},
        ).mappings().all()
        for item in extra:
            izzet_os.append(
                {
                    "id": item["id"],
                    "display_name": item["display_name"],
                    "phone": item["primary_phone"],
                    "email": item["primary_email"],
                    "status": item["status"],
                    "external_ids": item["external_ids"] if isinstance(item["external_ids"], list) else [],
                    "match": "phone_or_email_after_bitrix_link",
                }
            )

    # Also OS agreements on uniloft 403 besides Nedim — possible co-buyer representation
    uniloft_403 = db.execute(
        text(
            """
            select a.id::text, a.contact_id::text, c.display_name, c.status::text,
                   a.project_group, a.unit_number,
                   a.metadata_json->>'bitrix_deal_id' as bitrix_deal_id,
                   a.metadata_json->>'tutar_ve_para_birimi_amount' as tutar,
                   c.metadata_json->'bitrix_import'->'external_ids' as external_ids
            from crm_agreements a
            join crm_contacts c on c.id=a.contact_id
            where a.project_group='uniloft' and a.unit_number='403'
            """
        )
    ).mappings().all()
    db.close()

    report["os"] = {
        "nedim_contacts": [dict(r) for r in os_nedim],
        "agreements": [dict(r) for r in os_agreements],
        "activity_owner_counts": [dict(r) for r in os_acts],
        "uniloft_403_all_contacts": [dict(r) for r in uniloft_403],
        "izzet_os_contacts": izzet_os,
    }

    # linkage summary
    linkage = {}
    for did in DEAL_IDS:
        hist = report["deals"][did]["history"]
        linkage[did] = {
            "deal_activities": hist["activities_count"],
            "deal_comments": hist["comments_count"],
            "deal_activity_types": hist["activity_types"],
            "deal_files": len(hist["file_refs"]) + len(report["deals"][did]["deal"]["file_fields"]),
        }
    linkage["contact_588"] = {
        "activities": report["nedim_contact"]["history"]["activities_count"],
        "comments": report["nedim_contact"]["history"]["comments_count"],
        "types": report["nedim_contact"]["history"]["activity_types"],
    }
    linkage["lead_12512"] = {
        "activities": report["nedim_lead"]["history"]["activities_count"],
        "comments": report["nedim_lead"]["history"]["comments_count"],
        "types": report["nedim_lead"]["history"]["activity_types"],
    }
    report["linkage_summary"] = linkage
    report["bitrix_call_count"] = client.call_count

    out_path = OUT / "reports" / "NEDIM_BITRIX_DEAL_STRUCTURE.json"
    out_path.write_text(json.dumps(redact(report), ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("WROTE", str(out_path))
    print("CALLS", client.call_count)
    for did in DEAL_IDS:
        d = report["deals"][did]
        print(
            f"DEAL {did} title={d['deal']['title']!r} amount={d['deal']['opportunity']} {d['deal']['currency_id']} "
            f"stage={d['deal']['stage_id']}/{d['deal']['stage_name']} contacts={[c['contact_id']+':'+c['name'] for c in d['linked_contacts']]} "
            f"acts={d['history']['activities_count']} comments={d['history']['comments_count']}"
        )
    print("NEDIM_CONTACT", display_name(nedim_contact), phones_of(nedim_contact), emails_of(nedim_contact))
    print("IZZET_FROM_DEAL_LINKS", json.dumps(unique_izzet, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
