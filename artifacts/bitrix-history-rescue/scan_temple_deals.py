"""Read-only full live Bitrix scan for The Temple deals.

Does not write CRM. Never prints webhook URLs.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from sqlalchemy import text

from investhome_api.db.session import SessionLocal
from investhome_api.services.crm.identity import normalize_valid_email, parse_phone

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

OUT = Path("/export/2026-09-final/BITRIX_THE_TEMPLE_FULL_SCAN")
TUTAR_LABEL = "Tutar ve para birimi"
TUTAR_FIELD_ID = "OPPORTUNITY+CURRENCY_ID"
TEMPLE_RE = re.compile(
    r"the\s*temple|\btemple\b|1610\s*columbia|columbia\s*rd|ih-?dc-?tmp|adams\s*morgan",
    re.I,
)
FALSE_POS_RE = re.compile(r"contemplat|temperature|template\b", re.I)
UNIT_RE = re.compile(
    r"(?:the\s*temple|temple)\s+([0-9]{1,4}(?:\s*[-/&]\s*[0-9]{1,4})?)|"
    r"\b(?:unit|daire|apt|apartment|#)\s*[:.]?\s*([0-9]{1,4}(?:\s*[-/&]\s*[0-9]{1,4})?)\b",
    re.I,
)
PAYMENT_LABEL_RE = re.compile(
    r"sat[iı][sş]|yat[iı]r[iı]m|öde|ode|tutar|bedel|deposit|kapora|pe[sş]inat|"
    r"kalan|toplam|closing|unit|daire|proje|project|opportunity|amount|paid|"
    r"payment|currency|anla[sş]|columbia|temple|adres|address",
    re.I,
)


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
    seen: set[int] = set()
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


def phone_keys(value: str | None) -> set[str]:
    keys: set[str] = set()
    parsed = parse_phone(value)
    if parsed:
        keys.update({parsed.match_key, parsed.digits, parsed.e164 or ""})
    digits = re.sub(r"\D+", "", value or "")
    if len(digits) >= 10:
        keys.add(digits[-10:])
    return {k for k in keys if k}


def blob_of(rec: dict) -> str:
    parts = [str(rec.get("TITLE") or ""), str(rec.get("COMMENTS") or "")]
    for key, value in rec.items():
        if str(key).startswith("UF_") and value not in (None, "", [], {}, "0", 0):
            parts.append(f"{key}={value}")
    return " ".join(parts)


def extract_unit(title: str, custom: dict) -> str:
    for value in custom.values():
        text = str(value or "").strip()
        if re.fullmatch(r"[0-9]{1,4}(?:\s*[-/&]\s*[0-9]{1,4})?", text):
            label_hit = True
            # keep; prefer dedicated unit-like values later
            _ = label_hit
    for key, value in custom.items():
        if re.search(r"unit|daire|apt", key, re.I) and value not in (None, "", [], {}):
            return re.sub(r"\s+", "", str(value)).strip()
    match = UNIT_RE.search(title or "")
    if match:
        return re.sub(r"\s+", "", (match.group(1) or match.group(2) or "").strip())
    return ""


def deal_status(stage_id: str, closed: str, semantic: str, stage_name: str) -> str:
    blob = f"{stage_id} {stage_name} {semantic} {closed}".upper()
    if semantic == "F" or any(tok in blob for tok in ("LOSE", "LOST", "FAIL", "CANCEL", "JUNK", "APTAL", "KAYIP")):
        return "lost"
    if semantic == "S" or "WON" in blob or "SUCCESS" in blob or "KAZAN" in blob:
        return "won"
    if closed == "Y" and semantic != "P":
        return "closed"
    return "active"


def classify(
    *,
    status: str,
    stage_name: str,
    opportunity: str,
    unit: str,
    already: bool,
    duplicate: bool,
    contact_ids: list[str],
    person_name: str,
) -> str:
    if duplicate:
        return "DUPLICATE"
    if already:
        return "ALREADY_IN_OS"
    if status == "lost":
        return "LOST/CANCELLED"
    stage_l = f"{stage_name} {status}".casefold()
    opp = 0.0
    try:
        opp = float(opportunity or 0)
    except ValueError:
        opp = 0.0
    early = any(
        tok in stage_l
        for tok in ("new", "yeni", "lead", "qualification", "nurture", "appointment", "randevu", "potential", "aday")
    )
    if status == "won" or "execut" in stage_l or "anla" in stage_l or (opp > 0 and unit):
        if not contact_ids:
            return "REVIEW_REQUIRED"
        return "NEW_REAL_AGREEMENT_CANDIDATE"
    if status in {"active", "closed"} and (opp > 0 or unit) and contact_ids and not early:
        return "NEW_REAL_AGREEMENT_CANDIDATE"
    if early or (opp == 0 and not unit) or not contact_ids:
        return "POTENTIAL/NOT_AN_AGREEMENT"
    if not person_name:
        return "REVIEW_REQUIRED"
    return "POTENTIAL/NOT_AN_AGREEMENT"


def load_os(db) -> dict[str, Any]:
    agreements = [dict(r) for r in db.execute(
        text(
            """
            select a.id::text, a.contact_id::text, c.display_name, a.project_group, a.unit_number,
                   a.status, a.investment_amount::text, a.source_external_id,
                   a.metadata_json, c.primary_phone, c.primary_email, c.secondary_phones,
                   c.secondary_emails, c.metadata_json as contact_meta
            from crm_agreements a
            join crm_contacts c on c.id = a.contact_id
            """
        )
    ).mappings().all()]
    contacts = [dict(r) for r in db.execute(
        text(
            """
            select id::text, display_name, primary_phone, primary_email, secondary_phones,
                   secondary_emails, metadata_json
            from crm_contacts
            """
        )
    ).mappings().all()]
    by_deal: dict[str, dict] = {}
    by_phone: dict[str, list[dict]] = defaultdict(list)
    by_email: dict[str, list[dict]] = defaultdict(list)
    for rec in contacts:
        meta = rec.get("metadata_json") if isinstance(rec.get("metadata_json"), dict) else {}
        live = meta.get("bitrix_live") if isinstance(meta, dict) else {}
        rec["bitrix_contact_ids"] = [str(x) for x in (live or {}).get("contact_ids") or []]
        rec["bitrix_deal_ids"] = [str(x) for x in (live or {}).get("deal_ids") or []]
        for phone in [rec.get("primary_phone"), *(rec.get("secondary_phones") or [])]:
            for key in phone_keys(phone):
                by_phone[key].append(rec)
        emails = [normalize_valid_email(rec.get("primary_email") or "") or ""]
        emails.extend(normalize_valid_email(e) or "" for e in (rec.get("secondary_emails") or []))
        for email in {e for e in emails if e}:
            by_email[email].append(rec)
    temple = [a for a in agreements if a.get("project_group") == "the_temple"]
    for ag in agreements:
        meta = ag.get("metadata_json") if isinstance(ag.get("metadata_json"), dict) else {}
        deal_id = str((meta or {}).get("bitrix_deal_id") or "")
        if deal_id:
            by_deal[deal_id] = ag
    return {
        "agreements": agreements,
        "contacts": contacts,
        "temple": temple,
        "by_deal": by_deal,
        "by_phone": by_phone,
        "by_email": by_email,
        "agreement_count": len(agreements),
    }


def match_os_contact(os_data: dict, contact_ids: list[str], phones: list[str], emails: list[str]) -> list[dict]:
    hits: dict[str, dict] = {}
    for rec in os_data["contacts"]:
        if set(contact_ids) & set(rec.get("bitrix_contact_ids") or []):
            hits[rec["id"]] = rec
    pkeys: set[str] = set()
    for phone in phones:
        pkeys |= phone_keys(phone)
    for key in pkeys:
        for rec in os_data["by_phone"].get(key) or []:
            hits[rec["id"]] = rec
    for email in emails:
        norm = normalize_valid_email(email) or email
        for rec in os_data["by_email"].get(norm) or []:
            hits[rec["id"]] = rec
    return list(hits.values())


def main() -> int:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)

    print("Loading OS baseline…", flush=True)
    db = SessionLocal()
    try:
        os_data = load_os(db)
    finally:
        db.close()

    print("Loading Bitrix categories, fields, users…", flush=True)
    cats_body = client.call("crm.dealcategory.list", {"select[]": ["ID", "NAME", "IS_LOCKED", "SORT"]})
    categories = cats_body.get("result") or []
    if isinstance(categories, dict):
        categories = categories.get("categories") or categories.get("items") or []
    cat_by_id = {str(c.get("ID")): c for c in categories if isinstance(c, dict)}
    cat_by_id["0"] = {"ID": "0", "NAME": "Default"}

    fields_body = client.call("crm.deal.fields", {})
    field_specs = fields_body.get("result") if isinstance(fields_body.get("result"), dict) else {}
    field_labels = {
        fid: str(spec.get("formLabel") or spec.get("listLabel") or spec.get("title") or fid)
        for fid, spec in field_specs.items()
        if isinstance(spec, dict)
    }

    statuses: dict[str, dict] = {}
    for entity in ["STATUS", "DEAL_STAGE"] + [f"DEAL_STAGE_{cid}" for cid in cat_by_id if cid != "0"]:
        body = client.call("crm.status.list", {"filter[ENTITY_ID]": entity})
        for row in body.get("result") or []:
            if isinstance(row, dict) and row.get("STATUS_ID"):
                statuses[str(row["STATUS_ID"])] = row
                if entity.startswith("DEAL_STAGE_") and ":" not in str(row["STATUS_ID"]):
                    cat = entity.split("_")[-1]
                    statuses[f"C{cat}:{row['STATUS_ID']}"] = row

    users: dict[str, str] = {}

    def user_name(uid: str) -> str:
        if not uid or uid in {"0", "None"}:
            return ""
        if uid not in users:
            body = client.call("user.get", {"ID": uid})
            recs = body.get("result") or []
            rec = recs[0] if isinstance(recs, list) and recs else (recs if isinstance(recs, dict) else {})
            users[uid] = " ".join(p for p in [rec.get("NAME"), rec.get("LAST_NAME")] if p).strip() or uid
        return users[uid]

    print("Listing all live deals by category…", flush=True)
    select_fields = [
        "ID", "TITLE", "STAGE_ID", "STAGE_SEMANTIC_ID", "CLOSED", "OPPORTUNITY", "CURRENCY_ID",
        "BEGINDATE", "CLOSEDATE", "ASSIGNED_BY_ID", "CONTACT_ID", "COMPANY_ID", "LEAD_ID",
        "CATEGORY_ID", "COMMENTS", "TYPE_ID", "UF_*",
    ]
    all_deals: dict[str, dict] = {}
    for cat_id in list(cat_by_id) + [None]:
        payload: dict[str, Any] = {"select": select_fields}
        if cat_id is not None:
            payload["filter"] = {"CATEGORY_ID": cat_id}
        rows = list_all(client, "crm.deal.list", payload)
        print(f"  category {cat_id}: {len(rows)}", flush=True)
        for rec in rows:
            did = str(rec.get("ID") or "")
            if did:
                all_deals[did] = rec

    temple_cat_ids = {
        cid
        for cid, rec in cat_by_id.items()
        if TEMPLE_RE.search(str(rec.get("NAME") or "")) and not FALSE_POS_RE.search(str(rec.get("NAME") or ""))
    }

    matches: list[dict] = []
    for rec in all_deals.values():
        cat_id = str(rec.get("CATEGORY_ID") or "0")
        title = str(rec.get("TITLE") or "")
        blob = blob_of(rec)
        cat_name = str((cat_by_id.get(cat_id) or {}).get("NAME") or "")
        why = []
        if cat_id in temple_cat_ids:
            why.append(f"category:{cat_name or cat_id}")
        if TEMPLE_RE.search(title) and not FALSE_POS_RE.search(title):
            why.append("title")
        if TEMPLE_RE.search(blob) and not FALSE_POS_RE.search(blob):
            if "title" not in why:
                why.append("fields")
        if TEMPLE_RE.search(cat_name) and not FALSE_POS_RE.search(cat_name) and f"category:{cat_name}" not in why:
            why.append(f"category:{cat_name}")
        if why:
            rec["_why"] = why
            rec["_category_name"] = cat_name
            matches.append(rec)

    print(f"Matched {len(matches)} Temple-related deals of {len(all_deals)} total", flush=True)

    contact_cache: dict[str, dict] = {}
    lead_cache: dict[str, dict] = {}
    rows_out = []
    for rec in sorted(matches, key=lambda r: int(r.get("ID") or 0)):
        did = str(rec.get("ID"))
        full = client.call("crm.deal.get", {"id": did})
        deal = full.get("result") if isinstance(full.get("result"), dict) else rec
        contact_ids: list[str] = []
        cid = str(deal.get("CONTACT_ID") or rec.get("CONTACT_ID") or "")
        if cid and cid != "0":
            contact_ids.append(cid)
        items = client.call("crm.deal.contact.items.get", {"id": did})
        item_rows = items.get("result") or []
        for item in item_rows if isinstance(item_rows, list) else []:
            if isinstance(item, dict) and item.get("CONTACT_ID"):
                token = str(item["CONTACT_ID"])
                if token not in contact_ids:
                    contact_ids.append(token)

        contacts = []
        for token in contact_ids:
            if token not in contact_cache:
                got = client.call("crm.contact.get", {"id": token})
                contact_cache[token] = got.get("result") if isinstance(got.get("result"), dict) else {}
            contacts.append(contact_cache[token])

        lead_ids = []
        lid = str(deal.get("LEAD_ID") or rec.get("LEAD_ID") or "")
        if lid and lid != "0":
            lead_ids.append(lid)
        for token in contact_ids:
            extra = list_all(client, "crm.lead.list", {"filter": {"CONTACT_ID": token}, "select": ["ID", "TITLE", "STATUS_ID", "NAME", "LAST_NAME"]})
            for lead in extra:
                token_l = str(lead.get("ID") or "")
                if token_l and token_l not in lead_ids:
                    lead_ids.append(token_l)
                    lead_cache[token_l] = lead

        names = []
        phones: list[str] = []
        emails: list[str] = []
        for contact in contacts:
            names.append(" ".join(p for p in [contact.get("NAME"), contact.get("LAST_NAME")] if p).strip())
            phones.extend(phones_of(contact))
            emails.extend(emails_of(contact))

        custom = {}
        for key, value in {**rec, **deal}.items():
            if not str(key).startswith("UF_"):
                continue
            if value in (None, "", [], {}, "0", 0, False):
                continue
            label = field_labels.get(key, key)
            custom[f"{key}|{label}"] = value

        payment_custom = {
            k: v
            for k, v in custom.items()
            if PAYMENT_LABEL_RE.search(k) or PAYMENT_LABEL_RE.search(str(v))
        }
        title = str(deal.get("TITLE") or rec.get("TITLE") or "")
        unit = extract_unit(title, {k.split("|", 1)[-1]: v for k, v in custom.items()})
        stage_id = str(deal.get("STAGE_ID") or rec.get("STAGE_ID") or "")
        stage_meta = statuses.get(stage_id) or {}
        stage_name = str(stage_meta.get("NAME") or stage_id)
        status = deal_status(
            stage_id,
            str(deal.get("CLOSED") or rec.get("CLOSED") or ""),
            str(deal.get("STAGE_SEMANTIC_ID") or rec.get("STAGE_SEMANTIC_ID") or stage_meta.get("SEMANTICS") or ""),
            stage_name,
        )
        opportunity = str(deal.get("OPPORTUNITY") if deal.get("OPPORTUNITY") not in (None, "") else rec.get("OPPORTUNITY") or "")
        currency = str(deal.get("CURRENCY_ID") or rec.get("CURRENCY_ID") or "")
        assigned = str(deal.get("ASSIGNED_BY_ID") or rec.get("ASSIGNED_BY_ID") or "")
        os_hits = match_os_contact(os_data, contact_ids, phones, emails)
        os_ag = os_data["by_deal"].get(did)
        temple_for_person = []
        for hit in os_hits:
            temple_for_person.extend(
                [
                    a
                    for a in os_data["temple"]
                    if a["contact_id"] == hit["id"]
                ]
            )
        unit_norm = re.sub(r"\s+", "", unit or "")
        already = bool(os_ag) or any(
            re.sub(r"\s+", "", str(a.get("unit_number") or "")) == unit_norm and unit_norm
            for a in temple_for_person
        )
        row = {
            "deal_id": did,
            "deal_title": title,
            "category_id": str(deal.get("CATEGORY_ID") or rec.get("CATEGORY_ID") or ""),
            "category_name": rec.get("_category_name") or "",
            "match_reason": ",".join(rec.get("_why") or []),
            "stage_id": stage_id,
            "stage": stage_name,
            "status": status,
            "contact_ids": ",".join(contact_ids),
            "lead_ids": ",".join(lead_ids),
            "person_name": " | ".join(n for n in names if n),
            "phone": " | ".join(dict.fromkeys(phones)),
            "email": " | ".join(dict.fromkeys(emails)),
            "unit": unit,
            "tutar_ve_para_birimi_label": TUTAR_LABEL,
            "tutar_ve_para_birimi_field_id": TUTAR_FIELD_ID,
            "tutar_ve_para_birimi": f"{opportunity} {currency}".strip(),
            "opportunity": opportunity,
            "currency": currency,
            "begin_date": str(deal.get("BEGINDATE") or rec.get("BEGINDATE") or ""),
            "responsible_person": user_name(assigned),
            "responsible_id": assigned,
            "os_contact_uuid": " | ".join(h["id"] for h in os_hits),
            "os_contact_name": " | ".join(h["display_name"] for h in os_hits),
            "os_temple_agreements": " | ".join(a["id"] for a in temple_for_person),
            "populated_custom_fields": json.dumps(custom, ensure_ascii=False, default=str),
            "project_unit_payment_custom_fields": json.dumps(payment_custom, ensure_ascii=False, default=str),
            "already_in_os": already,
        }
        rows_out.append(row)

    # duplicates: same contact+unit among matches, or same person with multiple temple deals
    seen_keys: dict[str, list[str]] = defaultdict(list)
    for row in rows_out:
        key = f"{row['contact_ids']}|{row['unit'] or row['deal_title']}"
        seen_keys[key].append(row["deal_id"])
    dup_ids = {did for ids in seen_keys.values() if len(ids) > 1 for did in ids[1:]}

    for row in rows_out:
        row["classification"] = classify(
            status=row["status"],
            stage_name=row["stage"],
            opportunity=row["opportunity"],
            unit=row["unit"],
            already=row["already_in_os"],
            duplicate=row["deal_id"] in dup_ids,
            contact_ids=[x for x in row["contact_ids"].split(",") if x],
            person_name=row["person_name"],
        )
        if row["already_in_os"] and row["classification"] != "DUPLICATE":
            row["classification"] = "ALREADY_IN_OS"
        if row["os_contact_uuid"] and row["os_contact_name"] and row["person_name"]:
            os_fold = re.sub(r"\s+", " ", row["os_contact_name"]).casefold()
            bx_fold = re.sub(r"\s+", " ", row["person_name"]).casefold()
            if os_fold and bx_fold and os_fold != bx_fold and row["classification"] == "NEW_REAL_AGREEMENT_CANDIDATE":
                row["classification"] = "REVIEW_REQUIRED"
                row["review_note"] = "os_name_mismatch"
        if not row.get("review_note"):
            row["review_note"] = ""

    counts = Counter(r["classification"] for r in rows_out)
    summary = {
        "generated_readonly": True,
        "bitrix_calls": client.call_count,
        "total_live_deals_scanned": len(all_deals),
        "categories": [{"id": k, "name": v.get("NAME")} for k, v in cat_by_id.items()],
        "temple_category_ids": sorted(temple_cat_ids),
        "os_agreements_total": os_data["agreement_count"],
        "os_temple_agreements": [
            {
                "id": a["id"],
                "contact": a["display_name"],
                "unit": a["unit_number"],
                "bitrix_deal_id": (a.get("metadata_json") or {}).get("bitrix_deal_id") if isinstance(a.get("metadata_json"), dict) else None,
            }
            for a in os_data["temple"]
        ],
        "total_temple_related_bitrix_deals": len(rows_out),
        "already_in_os": counts.get("ALREADY_IN_OS", 0),
        "new_real_agreement_candidates": counts.get("NEW_REAL_AGREEMENT_CANDIDATE", 0),
        "duplicates": counts.get("DUPLICATE", 0),
        "lost_cancelled": counts.get("LOST/CANCELLED", 0),
        "potential_not_agreement": counts.get("POTENTIAL/NOT_AN_AGREEMENT", 0),
        "review_required": counts.get("REVIEW_REQUIRED", 0),
        "classifications": dict(counts),
        "no_agreements_created": True,
    }
    fields = [
        "deal_id", "deal_title", "classification", "person_name", "unit", "tutar_ve_para_birimi",
        "opportunity", "currency", "status", "stage", "contact_ids", "lead_ids", "phone", "email",
        "begin_date", "responsible_person", "category_name", "match_reason", "os_contact_name",
        "os_contact_uuid", "os_temple_agreements", "review_note", "project_unit_payment_custom_fields",
    ]
    csv_path = OUT / "reports" / "THE_TEMPLE_FULL_BITRIX_DEALS.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows_out)
    json_path = OUT / "reports" / "THE_TEMPLE_FULL_BITRIX_SCAN.json"
    json_path.write_text(
        json.dumps({"summary": summary, "deals": rows_out}, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
