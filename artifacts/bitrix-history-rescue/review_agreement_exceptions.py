"""Read-only manual review of remaining agreement reconciliation exceptions."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, "/work")
from reconcile_agreements import (  # type: ignore
    BitrixClient,
    emails_of,
    label_of,
    load_env,
    phones_of,
    scalar,
    webhook_base,
)

from investhome_api.db.session import SessionLocal

ENV_PATH = Path("/tmp/.env")
OUT = Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_AGREEMENT_FINAL_REVIEW.json")

TARGET_AGREEMENTS = {
    "56e993e2-23be-474d-9784-1ed2ecb6a3c1",  # Berk 105
    "4836482a-559a-428d-910f-cf08a09ab544",  # Berk 304
    "6b58a9e0-a219-404b-8b06-a71c6d6fbdd6",  # Ilgaz 207
    "d30d258a-3b89-458a-bfa0-a2de4f9f0ba2",  # Nedim Ontario 403
    "bdfd5ca1-e491-4896-b5d4-4b401ef428ac",  # Nedim Uniloft 209
    "56e9755b-c944-4a29-a654-49c9db55cf8e",  # Caglar 102
    "32021a1a-6366-4eb8-831f-29643635863a",  # Umit 301
    "43e762d6-9409-425d-b96b-c38c8d240324",  # Ayse second 204
    "fadfc360-2900-4673-80d0-ffdc88b6763a",  # Lale B08
    "89017632-0b24-4d80-aed1-78e6e746ede7",  # Eyyub REIT
    "584cd34b-3830-4505-9c41-3c47ad41d2e8",  # Semih
}

# Also include any other agreements owned by these people so leftover deals can be shown.
TARGET_NAMES = [
    "Berk Çimen",
    "Ilgaz Uzunca",
    "Nedim Kondu",
    "Çağlar Çağ",
    "Ümit Çimen",
    "Ayşe Çimen",
    "Lale Şenyol",
    "Eyyub Canlılar",
    "Semih Sönmez",
]

PAYMENT_KEYS = (
    "OPPORTUNITY",
    "CURRENCY_ID",
    "TITLE",
    "STAGE_ID",
    "CATEGORY_ID",
    "BEGINDATE",
    "CLOSEDATE",
    "COMMENTS",
    "CONTACT_ID",
    "LEAD_ID",
    "ASSIGNED_BY_ID",
    "SOURCE_ID",
    "UF_CRM_1690887880212",  # Daire No
    "UF_CRM_1690533085532",  # Alınan Ev Proje Adresi
    "UF_CRM_1690530042617",  # Ödeme Şekli
    "UF_CRM_1690534081328",  # Ödeme Tarihleri
    "UF_CRM_668E2D3B0863D",  # Yatırım Tutarı (R)
    "UF_CRM_1690532500123",
)

EXCEL_KEEP = (
    "0:ID",
    "1:Satış kanalı",
    "4:Aşama",
    "12:Anlaşma Adı",
    "16:Gelir",
    "17:Para birimi",
    "19:İletişim",
    "26:Başlama ​​tarihi",
    "27:Varsayılan kapanış tarihi",
    "31:Yorum",
    "10:Sorumlu",
)


def compact_excel(meta: dict) -> dict:
    src = ((meta or {}).get("source_data") or {}).get("source_fields") or (meta or {}).get("source_fields") or {}
    out = {}
    for key, val in src.items():
        label = str(key)
        keep = any(label.startswith(k.split(":")[0] + ":") or k in label for k in EXCEL_KEEP)
        interesting = any(
            tok in label.casefold()
            for tok in (
                "daire",
                "unit",
                "yatırım",
                "yatirim",
                "ödeme",
                "odeme",
                "peşinat",
                "pesinat",
                "gelir",
                "anlaşma",
                "anlasma",
                "kanal",
                "yorum",
                "id",
                "iletişim",
                "iletisim",
                "para",
            )
        )
        if keep or interesting:
            if val not in (None, "", [], {}):
                out[label] = val
    agr = (meta or {}).get("agreement_fields") or {}
    if agr:
        out["_agreement_fields"] = {
            k: agr.get(k)
            for k in ("customer_name", "phone", "email", "closing_date", "payment_amount", "notes", "deal_name", "unit_number")
            if agr.get(k) not in (None, "", [])
        }
    return {
        "source_file": (meta or {}).get("source_file"),
        "source_row_identifier": (meta or {}).get("source_row_identifier"),
        "project_label": (meta or {}).get("project_label"),
        "fields": out,
    }


def deal_compact(deal: dict, labels: dict[str, str]) -> dict:
    if not deal:
        return {}
    interesting = {}
    for fid, val in deal.items():
        if val in (None, "", [], {}):
            continue
        label = labels.get(fid, fid)
        low = (label or fid).casefold()
        if fid in PAYMENT_KEYS or fid in {"ID", "TITLE", "STAGE_ID", "CATEGORY_ID", "CURRENCY_ID", "OPPORTUNITY", "BEGINDATE", "CLOSEDATE", "COMMENTS", "CONTACT_ID", "LEAD_ID"}:
            interesting[f"{fid}|{label}"] = val
        elif any(tok in low for tok in ("daire", "ödeme", "odeme", "peşinat", "pesinat", "yatırım", "yatirim", "kapora", "proje", "unit", "ön ödeme", "teslim")):
            interesting[f"{fid}|{label}"] = val
    return {
        "id": deal.get("ID"),
        "title": deal.get("TITLE"),
        "stage": deal.get("STAGE_ID"),
        "category": deal.get("CATEGORY_ID"),
        "opportunity": deal.get("OPPORTUNITY"),
        "currency": deal.get("CURRENCY_ID"),
        "contact_id": deal.get("CONTACT_ID"),
        "lead_id": deal.get("LEAD_ID"),
        "begindate": deal.get("BEGINDATE"),
        "closedate": deal.get("CLOSEDATE"),
        "assigned_by": deal.get("ASSIGNED_BY_ID"),
        "comments": (scalar(deal.get("COMMENTS")) or "")[:400],
        "fields": interesting,
    }


def entity_compact(kind: str, rec: dict) -> dict:
    return {
        "type": kind,
        "id": rec.get("ID"),
        "name": " ".join(x for x in [rec.get("NAME"), rec.get("LAST_NAME")] if x).strip() or rec.get("TITLE"),
        "phones": phones_of(rec),
        "emails": emails_of(rec),
        "company": rec.get("COMPANY_TITLE") or rec.get("POST"),
        "post": rec.get("POST"),
        "address": rec.get("ADDRESS"),
        "assigned_by": rec.get("ASSIGNED_BY_ID"),
    }


def main() -> None:
    env = load_env(ENV_PATH)
    webhook = webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or "")
    if not webhook:
        raise SystemExit("MISSING_ADMIN_WEBHOOK")
    client = BitrixClient(webhook)

    fields = client.call("crm.deal.fields", {})
    labels: dict[str, str] = {}
    for fid, spec in (fields.get("result") or {}).items():
        if isinstance(spec, dict):
            labels[fid] = label_of(spec) or fid

    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                select c.id::text as cid, c.display_name, c.primary_phone, c.secondary_phones,
                       c.primary_email, c.secondary_emails, c.whatsapp, c.organization_name, c.job_title,
                       c.address_line1, c.metadata_json as contact_meta,
                       a.id::text as aid, a.project_group, a.unit_number, a.investment_amount,
                       a.agreement_date::text, a.source_external_id, a.status::text,
                       a.metadata_json as agreement_meta
                from crm_agreements a
                join crm_contacts c on c.id = a.contact_id
                where c.display_name = any(:names)
                order by c.display_name, a.project_group, a.unit_number
                """
            ),
            {"names": TARGET_NAMES},
        ).mappings().all()

    people: dict[str, dict] = {}
    for row in rows:
        person = people.setdefault(
            row["cid"],
            {
                "cid": row["cid"],
                "name": row["display_name"],
                "os_phone": row["primary_phone"],
                "os_secondary_phones": row["secondary_phones"],
                "os_email": row["primary_email"],
                "os_secondary_emails": row["secondary_emails"],
                "whatsapp": row["whatsapp"],
                "org": row["organization_name"],
                "job_title": row["job_title"],
                "address": row["address_line1"],
                "agreements": [],
                "bitrix_entities": [],
                "bitrix_deals": [],
            },
        )
        person["agreements"].append(
            {
                "id": row["aid"],
                "project_group": row["project_group"],
                "unit_number": row["unit_number"],
                "investment_amount": row["investment_amount"],
                "agreement_date": row["agreement_date"],
                "source_external_id": row["source_external_id"],
                "status": row["status"],
                "excel": compact_excel(row["agreement_meta"] or {}),
                "is_exception": row["aid"] in TARGET_AGREEMENTS,
            }
        )

    # Match people on Bitrix by phone/email using same methods as reconciliation.
    from reconcile_agreements import digits, phone_keys

    for person in people.values():
        phones = [person["os_phone"], person["whatsapp"], *(person["os_secondary_phones"] or [])]
        emails = [person["os_email"], *((person["os_secondary_emails"] or []))]
        entities = []
        how = []
        seen = set()
        for phone in phones:
            for key in phone_keys(phone):
                payload = {"FILTER[PHONE]": key, "SELECT[]": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST", "ADDRESS", "ASSIGNED_BY_ID"]}
                for rec in client.list_all("crm.contact.list", payload):
                    mark = ("contact", rec.get("ID"))
                    if mark not in seen:
                        seen.add(mark)
                        entities.append(entity_compact("contact", rec))
                        how.append({"entity": f"contact:{rec.get('ID')}", "via": "phone", "value": phone})
                for rec in client.list_all("crm.lead.list", {**payload, "SELECT[]": ["ID", "NAME", "LAST_NAME", "TITLE", "PHONE", "EMAIL", "POST", "ADDRESS", "ASSIGNED_BY_ID", "COMPANY_TITLE"]}):
                    mark = ("lead", rec.get("ID"))
                    if mark not in seen:
                        seen.add(mark)
                        entities.append(entity_compact("lead", rec))
                        how.append({"entity": f"lead:{rec.get('ID')}", "via": "phone", "value": phone})
        for email in emails:
            em = (email or "").strip().lower()
            if "@" not in em:
                continue
            payload = {"FILTER[EMAIL]": em, "SELECT[]": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL", "POST", "ADDRESS", "ASSIGNED_BY_ID"]}
            for rec in client.list_all("crm.contact.list", payload):
                mark = ("contact", rec.get("ID"))
                if mark not in seen:
                    seen.add(mark)
                    entities.append(entity_compact("contact", rec))
                    how.append({"entity": f"contact:{rec.get('ID')}", "via": "email", "value": em})
            for rec in client.list_all("crm.lead.list", {**payload, "SELECT[]": ["ID", "NAME", "LAST_NAME", "TITLE", "PHONE", "EMAIL", "POST", "ADDRESS", "ASSIGNED_BY_ID", "COMPANY_TITLE"]}):
                mark = ("lead", rec.get("ID"))
                if mark not in seen:
                    seen.add(mark)
                    entities.append(entity_compact("lead", rec))
                    how.append({"entity": f"lead:{rec.get('ID')}", "via": "email", "value": em})
        person["match_how"] = how
        person["bitrix_entities"] = entities

        deals = []
        deal_ids = set()
        for ent in entities:
            filt_key = "FILTER[CONTACT_ID]" if ent["type"] == "contact" else "FILTER[LEAD_ID]"
            payload = {filt_key: ent["id"], "SELECT[]": ["*", *list(labels)]}
            for deal in client.list_all("crm.deal.list", payload):
                did = str(deal.get("ID"))
                if did not in deal_ids:
                    deal_ids.add(did)
                    deals.append(deal_compact(deal, labels))
        # also fetch source_external_id deal ids
        for ag in person["agreements"]:
            ext = ag.get("source_external_id") or ""
            if ":" in ext:
                did = ext.rsplit(":", 1)[-1]
                if did.isdigit() and did not in deal_ids:
                    parsed = client.call("crm.deal.get", {"id": did})
                    rec = parsed.get("result") or {}
                    if rec:
                        deal_ids.add(did)
                        deals.append(deal_compact(rec, labels))
        person["bitrix_deals"] = deals

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"people": list(people.values()), "bitrix_calls": client.call_count}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("WROTE", OUT, "people", len(people), "calls", client.call_count, flush=True)


if __name__ == "__main__":
    main()
