"""Read-only populated-field extract for Nedim/Izzet person+purchase UX. Never prints webhook."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

OUT = Path("/tmp/nedim_izzet_fields.json")
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)
EMPTY = (None, "", [], {}, 0, "0", "false", "False", "N")


def redact(value: Any) -> Any:
    if isinstance(value, str):
        if "urlMachine" in value or "/rest/" in value:
            return "[REDACTED]"
        return WEBHOOK_RE.sub("[REDACTED_URL]", value)
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items() if k not in {"urlMachine", "downloadUrl", "url"}}
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def populated(value: Any) -> bool:
    if isinstance(value, (list, dict, tuple, set)):
        if not value:
            return False
        if isinstance(value, dict):
            return any(populated(v) for k, v in value.items() if k not in {"urlMachine", "downloadUrl", "url", "showUrl"})
        return any(populated(v) for v in value)
    if value in EMPTY:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def label_of(spec: dict) -> str:
    for key in ("formLabel", "listLabel", "filterLabel", "title", "editFormLabel"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip() and not val.startswith("UF_"):
            return val.strip()
        if isinstance(val, dict):
            for lang in ("tr", "en"):
                if val.get(lang):
                    return str(val[lang]).strip()
            for item in val.values():
                if item:
                    return str(item).strip()
    return str(spec.get("title") or spec.get("listLabel") or "")


def enum_label(spec: dict, value: Any) -> Any:
    items = spec.get("items")
    if not isinstance(items, list):
        return value
    wanted = str(value)
    for item in items:
        if isinstance(item, dict) and str(item.get("ID") or item.get("id") or "") == wanted:
            return item.get("VALUE") or item.get("value") or value
    return value


def file_ids(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, list):
        for item in value:
            found.extend(file_ids(item))
        return found
    if isinstance(value, dict):
        for key in ("id", "ID", "fileId", "FILE_ID"):
            if value.get(key):
                found.append(str(value.get(key)))
        return found
    if str(value).isdigit():
        found.append(str(value))
    return found


def phones(row: dict) -> list[str]:
    out = []
    for item in row.get("PHONE") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]))
    return out


def emails(row: dict) -> list[str]:
    out = []
    for item in row.get("EMAIL") or []:
        if isinstance(item, dict) and item.get("VALUE"):
            out.append(str(item["VALUE"]))
    return out


def decode_fields(row: dict, specs: dict[str, dict]) -> list[dict]:
    items = []
    for key, value in row.items():
        if key in {"urlMachine", "downloadUrl"} or not populated(value):
            continue
        spec = specs.get(key) or {}
        label = label_of(spec) if spec else key
        decoded = enum_label(spec, value) if spec else value
        if isinstance(decoded, dict) and file_ids(decoded):
            decoded = {"file_ids": file_ids(decoded)}
        elif isinstance(decoded, list) and file_ids(decoded):
            decoded = {"file_ids": file_ids(decoded)}
        items.append({"key": key, "label": label or key, "value": redact(decoded)})
    return items


def get_result(client: BitrixClient, method: str, payload: dict) -> Any:
    body = client.call(method, payload)
    return body.get("result")


def main() -> None:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    deal_fields = get_result(client, "crm.deal.fields", {}) or {}
    contact_fields = get_result(client, "crm.contact.fields", {}) or {}
    lead_fields = get_result(client, "crm.lead.fields", {}) or {}
    if not isinstance(deal_fields, dict):
        deal_fields = {}
    if not isinstance(contact_fields, dict):
        contact_fields = {}
    if not isinstance(lead_fields, dict):
        lead_fields = {}

    statuses = get_result(client, "crm.status.list", {}) or []
    stage_names = {}
    source_names = {}
    if isinstance(statuses, list):
        for row in statuses:
            if not isinstance(row, dict):
                continue
            sid = str(row.get("STATUS_ID") or "")
            name = row.get("NAME")
            entity = str(row.get("ENTITY_ID") or "")
            if "DEAL_STAGE" in entity or entity.startswith("DEAL_STAGE"):
                stage_names[sid] = name
            if entity == "SOURCE":
                source_names[sid] = name
            stage_names.setdefault(sid, name)

    def user_name(uid: str) -> str | None:
        if not uid or uid in {"0"}:
            return None
        result = get_result(client, "user.get", {"ID": uid})
        row = result[0] if isinstance(result, list) and result else result
        if isinstance(row, dict):
            return " ".join(str(row.get(k) or "") for k in ("NAME", "LAST_NAME")).strip() or None
        return None

    def pack_entity(row: dict, specs: dict, kind: str) -> dict:
        assigned = str(row.get("ASSIGNED_BY_ID") or "")
        return {
            "id": row.get("ID"),
            "name": " ".join(str(row.get(k) or "") for k in ("NAME", "SECOND_NAME", "LAST_NAME")).strip() or row.get("TITLE"),
            "phones": phones(row),
            "emails": emails(row),
            "company_id": row.get("COMPANY_ID") or row.get("COMPANY_TITLE"),
            "post": row.get("POST"),
            "source_id": row.get("SOURCE_ID"),
            "source_name": source_names.get(str(row.get("SOURCE_ID") or "")),
            "assigned_id": assigned,
            "assigned_name": user_name(assigned),
            "comments": row.get("COMMENTS"),
            "address": row.get("ADDRESS"),
            "address_city": row.get("ADDRESS_CITY"),
            "address_postal": row.get("ADDRESS_POSTAL_CODE"),
            "address_country": row.get("ADDRESS_COUNTRY"),
            "populated": decode_fields(row, specs),
        }

    def requisites(entity_type: str, entity_id: str) -> list[dict]:
        rows = get_result(
            client,
            "crm.requisite.list",
            {"filter[ENTITY_TYPE_ID]": entity_type, "filter[ENTITY_ID]": entity_id},
        )
        out = []
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                packed = {k: redact(v) for k, v in row.items() if populated(v)}
                addrs = get_result(client, "crm.address.list", {"filter[ENTITY_ID]": row.get("ID")})
                packed["addresses"] = [
                    {k: redact(v) for k, v in addr.items() if populated(v)}
                    for addr in (addrs if isinstance(addrs, list) else [])
                    if isinstance(addr, dict)
                ]
                out.append(packed)
        return out

    def deal_pack(deal_id: str) -> dict:
        deal = get_result(client, "crm.deal.get", {"id": deal_id}) or {}
        if not isinstance(deal, dict):
            deal = {}
        items = get_result(client, "crm.deal.contact.items.get", {"id": deal_id})
        comments = get_result(
            client,
            "crm.timeline.comment.list",
            {"filter[ENTITY_ID]": deal_id, "filter[ENTITY_TYPE]": "deal"},
        )
        activities = get_result(
            client,
            "crm.activity.list",
            {
                "filter[OWNER_TYPE_ID]": 2,
                "filter[OWNER_ID]": deal_id,
                "select[]": ["ID", "TYPE_ID", "PROVIDER_ID", "SUBJECT", "DESCRIPTION", "CREATED"],
            },
        )
        assigned = str(deal.get("ASSIGNED_BY_ID") or "")
        stage_id = str(deal.get("STAGE_ID") or "")
        populated_fields = decode_fields(deal, deal_fields)
        payment = [
            item
            for item in populated_fields
            if re.search(
                r"öde|ode|tutar|bedel|deposit|kapora|pe[sş]inat|kalan|paid|payment|mortgage|ipotek|taksit|makbuz",
                f"{item['label']} {item['key']}",
                re.I,
            )
        ]
        llc = [
            item
            for item in populated_fields
            if re.search(r"llc|şirket|sirket|company|ünvan|unvan|title|ein|tax|vergi|kimlik", f"{item['label']} {item['key']}", re.I)
            and not str(item["key"]).startswith("UF_") is False
        ]
        llc = [
            item
            for item in populated_fields
            if re.search(r"llc|şirket|sirket|company|ünvan|unvan|ein|tax|vergi", f"{item['label']} {item['key']}", re.I)
        ]
        files = []
        for item in populated_fields:
            val = item["value"]
            if isinstance(val, dict) and val.get("file_ids"):
                files.extend(val["file_ids"])
        company_id = str(deal.get("COMPANY_ID") or "")
        company = None
        if company_id not in {"", "0"}:
            crec = get_result(client, "crm.company.get", {"id": company_id}) or {}
            if isinstance(crec, dict):
                company = {"id": company_id, "title": crec.get("TITLE"), "populated": decode_fields(crec, {})}
        return {
            "title": deal.get("TITLE"),
            "opportunity": deal.get("OPPORTUNITY"),
            "currency": deal.get("CURRENCY_ID"),
            "stage_id": stage_id,
            "stage_name": stage_names.get(stage_id),
            "begin": deal.get("BEGINDATE"),
            "close": deal.get("CLOSEDATE"),
            "assigned_id": assigned,
            "assigned_name": user_name(assigned),
            "comments": deal.get("COMMENTS"),
            "contact_id": deal.get("CONTACT_ID"),
            "company_id": deal.get("COMPANY_ID"),
            "company": company,
            "participants": items,
            "activity_count": len(activities) if isinstance(activities, list) else activities,
            "comment_count": len(comments) if isinstance(comments, list) else comments,
            "activities": redact(activities) if isinstance(activities, list) else activities,
            "timeline_comments": redact(comments) if isinstance(comments, list) else comments,
            "payment_fields": payment,
            "llc_fields": llc,
            "file_ids": files,
            "populated_fields": populated_fields,
            "requisites": requisites("2", deal_id),
        }

    contact_588 = get_result(client, "crm.contact.get", {"id": 588}) or {}
    contact_1160 = get_result(client, "crm.contact.get", {"id": 1160}) or {}
    lead_12512 = get_result(client, "crm.lead.get", {"id": 12512}) or {}
    payload = {
        "contact_588": pack_entity(contact_588 if isinstance(contact_588, dict) else {}, contact_fields, "contact"),
        "contact_588_requisites": requisites("3", "588"),
        "contact_1160": pack_entity(contact_1160 if isinstance(contact_1160, dict) else {}, contact_fields, "contact"),
        "contact_1160_requisites": requisites("3", "1160"),
        "lead_12512": pack_entity(lead_12512 if isinstance(lead_12512, dict) else {}, lead_fields, "lead"),
        "lead_12512_requisites": requisites("1", "12512"),
        "deal_198": deal_pack("198"),
        "deal_656": deal_pack("656"),
        "deal_720": deal_pack("720"),
        "calls": client.call_count,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    print(f"wrote {OUT} calls={client.call_count}")


if __name__ == "__main__":
    main()
