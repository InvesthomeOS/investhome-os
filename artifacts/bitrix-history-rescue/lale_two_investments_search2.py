"""Follow-up live Bitrix search for Lale B08 via lead 6178 / amounts / activities."""
from __future__ import annotations

import json
import os
from pathlib import Path

from agreement_customers_final_model import BitrixClient, webhook_base

OUT = Path("/tmp/LALE_TWO_INVESTMENTS")


def call(client, method, payload=None):
    return client.call(method, payload or {})


def list_all(client, method, payload):
    start = 0
    rows = []
    while True:
        parsed = call(client, method, payload | {"start": start})
        chunk = parsed.get("result")
        if isinstance(chunk, dict) and "items" in chunk:
            chunk = chunk.get("items")
        if not isinstance(chunk, list) or not chunk:
            if start == 0:
                rows.append({"_raw": parsed})
            break
        rows.extend(chunk)
        nxt = parsed.get("next")
        if nxt in (None, ""):
            break
        start = int(nxt)
    return rows


def main() -> None:
    client = BitrixClient(webhook_base(os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    report = {}

    report["deals_contact_str"] = list_all(client, "crm.deal.list", {
        "filter": {"CONTACT_ID": "362"},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "LEAD_ID", "CATEGORY_ID"],
    })
    report["deals_opp_232687"] = list_all(client, "crm.deal.list", {
        "filter": {"OPPORTUNITY": "232687"},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "LEAD_ID"],
    })
    report["deals_opp_232687_00"] = list_all(client, "crm.deal.list", {
        "filter": {"OPPORTUNITY": "232687.00"},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CONTACT_ID", "LEAD_ID"],
    })
    report["deals_title_6178"] = list_all(client, "crm.deal.list", {
        "filter": {"TITLE": "#6178 Lale Şenyol"},
        "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CONTACT_ID", "LEAD_ID"],
    })
    report["lead_6178_products"] = call(client, "crm.lead.productrows.get", {"id": "6178"})
    report["lead_16400_products"] = call(client, "crm.lead.productrows.get", {"id": "16400"})
    report["deal_206_products"] = call(client, "crm.deal.productrows.get", {"id": "206"})

    report["act_lead_6178"] = list_all(client, "crm.activity.list", {
        "filter": {"OWNER_TYPE_ID": 1, "OWNER_ID": 6178},
        "select": ["ID", "TYPE_ID", "SUBJECT", "DESCRIPTION", "ASSOCIATED_ENTITY_ID", "OWNER_ID", "OWNER_TYPE_ID", "FILES", "SETTINGS"],
        "order": {"ID": "DESC"},
    })
    report["act_contact_362"] = list_all(client, "crm.activity.list", {
        "filter": {"OWNER_TYPE_ID": 3, "OWNER_ID": 362},
        "select": ["ID", "TYPE_ID", "SUBJECT", "OWNER_ID", "OWNER_TYPE_ID", "ASSOCIATED_ENTITY_ID"],
        "order": {"ID": "DESC"},
    })
    report["act_deal_206"] = list_all(client, "crm.activity.list", {
        "filter": {"OWNER_TYPE_ID": 2, "OWNER_ID": 206},
        "select": ["ID", "TYPE_ID", "SUBJECT", "DESCRIPTION", "OWNER_ID", "FILES"],
        "order": {"ID": "DESC"},
    })

    # timeline bindings
    report["timeline_lead_6178"] = call(client, "crm.timeline.bindings.list", {"filter": {"ENTITY_ID": 6178, "ENTITY_TYPE": "lead"}})
    report["timeline_contact_362"] = call(client, "crm.timeline.bindings.list", {"filter": {"ENTITY_ID": 362, "ENTITY_TYPE": "contact"}})
    report["company_search"] = list_all(client, "crm.company.list", {
        "filter": {"%TITLE": "Lale"},
        "select": ["ID", "TITLE"],
    })
    report["company_b08"] = list_all(client, "crm.company.list", {
        "filter": {"%TITLE": "B08"},
        "select": ["ID", "TITLE"],
    })
    report["company_b008"] = list_all(client, "crm.company.list", {
        "filter": {"%TITLE": "B008"},
        "select": ["ID", "TITLE"],
    })
    report["company_1812"] = list_all(client, "crm.company.list", {
        "filter": {"%TITLE": "1812"},
        "select": ["ID", "TITLE"],
    })

    fields = call(client, "crm.deal.fields", {})
    result = fields.get("result") if isinstance(fields.get("result"), dict) else {}
    interesting = {}
    for key, spec in result.items():
        if not str(key).startswith("UF_"):
            continue
        label = ""
        if isinstance(spec, dict):
            for k in ("formLabel", "listLabel", "editLabel", "title"):
                val = spec.get(k)
                if isinstance(val, dict):
                    label = str(val.get("tr") or val.get("en") or next(iter(val.values()), "") or "")
                elif val:
                    label = str(val)
                if label:
                    break
        blob = f"{key} {label}".lower()
        if any(token in blob for token in ("unit", "daire", "b08", "proje", "llc", "şirket", "sirket", "tutar", "kapora", "peşinat", "pesinat", "reit", "yatırım", "yatirim")):
            interesting[key] = label or key
    report["deal_field_labels"] = interesting

    # Pull deal 206 labeled UFs using fields
    deal = call(client, "crm.deal.get", {"id": "206"}).get("result") or {}
    labeled = []
    if isinstance(deal, dict):
        for key, spec in result.items():
            if not str(key).startswith("UF_"):
                continue
            val = deal.get(key)
            if val in (None, "", [], {}, "0"):
                continue
            label = interesting.get(key)
            if not label and isinstance(spec, dict):
                for k in ("formLabel", "listLabel", "title"):
                    raw = spec.get(k)
                    if isinstance(raw, dict):
                        label = str(raw.get("tr") or raw.get("en") or "")
                    elif raw:
                        label = str(raw)
                    if label:
                        break
            labeled.append({"key": key, "label": label or key, "value": val if not isinstance(val, dict) else val})
    report["deal_206_labeled"] = labeled

    # contact deals via crm.item? try category loop 0-10
    cats = []
    for cat in range(0, 12):
        rows = list_all(client, "crm.deal.list", {
            "filter": {"CONTACT_ID": 362, "CATEGORY_ID": cat},
            "select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CATEGORY_ID", "LEAD_ID"],
        })
        real = [r for r in rows if isinstance(r, dict) and r.get("ID")]
        if real:
            cats.append({"category": cat, "deals": real})
    report["deals_by_category"] = cats

    report["calls"] = client.call_count
    (OUT / "SEARCH2.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "calls": client.call_count,
        "deals_contact_str": [r.get("ID") for r in report["deals_contact_str"] if isinstance(r, dict) and r.get("ID")],
        "deals_opp": [(r.get("ID"), r.get("TITLE")) for r in report["deals_opp_232687"] + report["deals_opp_232687_00"] if isinstance(r, dict) and r.get("ID")],
        "deals_title_6178": [(r.get("ID"), r.get("TITLE")) for r in report["deals_title_6178"] if isinstance(r, dict) and r.get("ID")],
        "cats": report["deals_by_category"],
        "act_lead": len([r for r in report["act_lead_6178"] if isinstance(r, dict) and r.get("ID")]),
        "act_contact": len([r for r in report["act_contact_362"] if isinstance(r, dict) and r.get("ID")]),
        "act_deal206": len([r for r in report["act_deal_206"] if isinstance(r, dict) and r.get("ID")]),
        "companies_b08": report["company_b08"],
        "companies_b008": report["company_b008"],
        "lead_6178_products": report["lead_6178_products"].get("result") if isinstance(report["lead_6178_products"], dict) else None,
    }, ensure_ascii=False, default=str)[:4000])


if __name__ == "__main__":
    main()
