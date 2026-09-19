"""Live Bitrix search for Lale Şenyol 1812 B08 + REIT. Read-only."""
from __future__ import annotations

import json
import os
from pathlib import Path

from agreement_customers_final_model import BitrixClient, webhook_base

OUT = Path("/tmp/LALE_TWO_INVESTMENTS")


def dump(client: BitrixClient, method: str, payload: dict | None = None) -> dict:
    return client.call(method, payload or {})


def list_all(client: BitrixClient, method: str, payload: dict) -> list:
    start = 0
    rows: list = []
    while True:
        body = payload | {"start": start}
        parsed = dump(client, method, body)
        chunk = parsed.get("result")
        if isinstance(chunk, dict) and "items" in chunk:
            chunk = chunk.get("items")
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend(chunk)
        nxt = parsed.get("next")
        if nxt in (None, ""):
            break
        start = int(nxt)
        if start <= 0:
            break
    return rows


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    client = BitrixClient(webhook_base(raw))
    report: dict = {"calls": 0}

    contact = dump(client, "crm.contact.get", {"id": "362"}).get("result")
    report["contact_362"] = contact if isinstance(contact, dict) else {"error": contact}

    for lead_id in ("16400", "6178"):
        report[f"lead_{lead_id}"] = dump(client, "crm.lead.get", {"id": lead_id}).get("result")

    report["deals_contact_362"] = list_all(client, "crm.deal.list", {
        "filter": {"CONTACT_ID": 362},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "BEGINDATE", "CLOSEDATE", "CONTACT_ID", "LEAD_ID", "COMMENTS", "ASSIGNED_BY_ID", "COMPANY_ID"],
    })
    report["deals_lead_16400"] = list_all(client, "crm.deal.list", {
        "filter": {"LEAD_ID": 16400},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "LEAD_ID"],
    })
    report["deals_lead_6178"] = list_all(client, "crm.deal.list", {
        "filter": {"LEAD_ID": 6178},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "LEAD_ID"],
    })

    title_queries = [
        "Lale",
        "Şenyol",
        "Senyol",
        "Sahyol",
        "Şahyol",
        "B08",
        "B008",
        "1812",
        "1820 H PL B",
        "16400",
    ]
    found: dict[str, dict] = {}
    for query in title_queries:
        rows = list_all(client, "crm.deal.list", {
            "filter": {"%TITLE": query},
            "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "BEGINDATE", "CLOSEDATE", "CONTACT_ID", "LEAD_ID", "COMMENTS", "ASSIGNED_BY_ID"],
        })
        for row in rows:
            if isinstance(row, dict) and row.get("ID"):
                found[str(row["ID"])] = row
        report[f"title_{query}"] = [{"ID": r.get("ID"), "TITLE": r.get("TITLE")} for r in rows if isinstance(r, dict)]

    leads_name = list_all(client, "crm.lead.list", {
        "filter": {"%NAME": "Lale"},
        "select": ["ID", "TITLE", "NAME", "LAST_NAME", "STATUS_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID"],
    })
    report["leads_name_lale"] = leads_name
    contacts_name = list_all(client, "crm.contact.list", {
        "filter": {"%NAME": "Lale"},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL"],
    })
    report["contacts_name_lale"] = contacts_name
    contacts_last = list_all(client, "crm.contact.list", {
        "filter": {"%LAST_NAME": "Senyol"},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL"],
    })
    report["contacts_last_senyol"] = contacts_last
    contacts_last2 = list_all(client, "crm.contact.list", {
        "filter": {"%LAST_NAME": "Şenyol"},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL"],
    })
    report["contacts_last_senyol_tr"] = contacts_last2
    contacts_sahyol = list_all(client, "crm.contact.list", {
        "filter": {"%LAST_NAME": "Şahyol"},
        "select": ["ID", "NAME", "LAST_NAME", "PHONE", "EMAIL"],
    })
    report["contacts_last_sahyol"] = contacts_sahyol

    deal_206 = dump(client, "crm.deal.get", {"id": "206"}).get("result")
    report["deal_206"] = deal_206 if isinstance(deal_206, dict) else deal_206
    if isinstance(deal_206, dict):
        report["deal_206_items"] = dump(client, "crm.deal.contact.items.get", {"id": "206"}).get("result")

    # Fetch full any extra candidate deals
    extra_ids = [did for did in found if did not in {"206"}]
    report["candidate_deals"] = {}
    for did in sorted(found, key=lambda x: int(x) if x.isdigit() else 0):
        full = dump(client, "crm.deal.get", {"id": did}).get("result")
        items = dump(client, "crm.deal.contact.items.get", {"id": did}).get("result")
        report["candidate_deals"][did] = {"deal": full if isinstance(full, dict) else full, "items": items, "list_row": found[did]}

    report["calls"] = client.call_count
    (OUT / "SEARCH.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "calls": client.call_count,
        "deals_contact_362": [(d.get("ID"), d.get("TITLE"), d.get("OPPORTUNITY")) for d in report["deals_contact_362"] if isinstance(d, dict)],
        "deals_lead_6178": [(d.get("ID"), d.get("TITLE")) for d in report["deals_lead_6178"] if isinstance(d, dict)],
        "deals_lead_16400": [(d.get("ID"), d.get("TITLE")) for d in report["deals_lead_16400"] if isinstance(d, dict)],
        "candidate_ids": list(found),
        "contacts_lale": [(c.get("ID"), c.get("NAME"), c.get("LAST_NAME")) for c in contacts_name if isinstance(c, dict)],
        "contacts_senyol": [(c.get("ID"), c.get("NAME"), c.get("LAST_NAME")) for c in contacts_last + contacts_last2 if isinstance(c, dict)],
        "contacts_sahyol": [(c.get("ID"), c.get("NAME"), c.get("LAST_NAME")) for c in contacts_sahyol if isinstance(c, dict)],
        "deal_206_title": deal_206.get("TITLE") if isinstance(deal_206, dict) else None,
        "deal_206_opp": deal_206.get("OPPORTUNITY") if isinstance(deal_206, dict) else None,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
