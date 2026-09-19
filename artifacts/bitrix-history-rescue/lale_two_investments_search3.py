"""Flattened Bitrix list search for Lale B08. Read-only."""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

from agreement_customers_final_model import BitrixClient, webhook_base

OUT = Path("/tmp/LALE_TWO_INVESTMENTS")


def flatten(value, prefix=""):
    items = []
    if isinstance(value, dict):
        for key, inner in value.items():
            path = f"{prefix}[{key}]" if prefix else str(key)
            items.extend(flatten(inner, path))
    elif isinstance(value, list):
        for inner in value:
            path = f"{prefix}[]" if prefix else ""
            items.extend(flatten(inner, path))
    else:
        items.append((prefix, value))
    return items


class NestedClient(BitrixClient):
    def call(self, method: str, payload: dict | None = None) -> dict:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last = "unknown"
        for attempt in range(5):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(flatten(payload or {}), doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                last = type(exc).__name__
                continue
            self._last = __import__("time").time()
            err = str(parsed.get("error") or "")
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                last = err
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last}


def list_all(client, method, payload):
    start = 0
    rows = []
    while True:
        body = dict(payload)
        if start:
            body["start"] = start
        parsed = client.call(method, body)
        chunk = parsed.get("result")
        if isinstance(chunk, dict) and "items" in chunk:
            chunk = chunk.get("items")
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend([item for item in chunk if isinstance(item, dict)])
        nxt = parsed.get("next")
        if nxt in (None, ""):
            break
        start = int(nxt)
    return rows


def main() -> None:
    client = NestedClient(webhook_base(os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    select = ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "BEGINDATE", "CLOSEDATE", "CONTACT_ID", "LEAD_ID", "CATEGORY_ID", "COMMENTS", "ASSIGNED_BY_ID", "COMPANY_ID"]

    deals_362 = list_all(client, "crm.deal.list", {"filter": {"CONTACT_ID": 362}, "select": select})
    deals_lead_6178 = list_all(client, "crm.deal.list", {"filter": {"LEAD_ID": 6178}, "select": select})
    deals_lead_16400 = list_all(client, "crm.deal.list", {"filter": {"LEAD_ID": 16400}, "select": select})

    # paginate all deals and match locally
    all_deals = list_all(client, "crm.deal.list", {"select": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID", "LEAD_ID", "CATEGORY_ID"]})
    needles = ("lale", "şenyol", "senyol", "sahyol", "şahyol", "b08", "b008", "6178", "16400", "1812")
    matched = []
    for row in all_deals:
        blob = f"{row.get('ID')} {row.get('TITLE')} {row.get('CONTACT_ID')} {row.get('LEAD_ID')} {row.get('OPPORTUNITY')}".casefold()
        if any(n in blob for n in needles):
            matched.append(row)

    companies = list_all(client, "crm.company.list", {"select": ["ID", "TITLE"]})
    co_match = [c for c in companies if any(n in f"{c.get('TITLE')}".casefold() for n in ("lale", "b08", "b008", "1812", "senyol", "şenyol"))]

    leads = list_all(client, "crm.lead.list", {"filter": {"CONTACT_ID": 362}, "select": ["ID", "TITLE", "STATUS_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID"]})

    act_lead = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 1, "OWNER_ID": 6178}, "order": {"ID": "DESC"}})
    act_contact = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 3, "OWNER_ID": 362}, "order": {"ID": "DESC"}})
    act_deal = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 2, "OWNER_ID": 206}, "order": {"ID": "DESC"}})

    extra = {}
    for row in matched:
        did = str(row.get("ID"))
        full = client.call("crm.deal.get", {"id": did}).get("result")
        items = client.call("crm.deal.contact.items.get", {"id": did}).get("result")
        extra[did] = {"list": row, "deal": full if isinstance(full, dict) else full, "items": items}

    report = {
        "deals_contact_362": deals_362,
        "deals_lead_6178": deals_lead_6178,
        "deals_lead_16400": deals_lead_16400,
        "all_deal_count": len(all_deals),
        "matched_deals": matched,
        "matched_full": extra,
        "companies_matched": co_match,
        "leads_contact_362": leads,
        "act_lead_6178_n": len(act_lead),
        "act_contact_362_n": len(act_contact),
        "act_deal_206_n": len(act_deal),
        "act_lead_subjects": [(a.get("ID"), a.get("TYPE_ID"), a.get("SUBJECT")) for a in act_lead[:30]],
        "act_contact_subjects": [(a.get("ID"), a.get("TYPE_ID"), a.get("SUBJECT")) for a in act_contact[:30]],
        "act_deal_subjects": [(a.get("ID"), a.get("TYPE_ID"), a.get("SUBJECT")) for a in act_deal[:30]],
        "calls": client.call_count,
    }
    (OUT / "SEARCH3.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "calls": client.call_count,
        "all_deals": len(all_deals),
        "deals_362": [(d.get("ID"), d.get("TITLE"), d.get("OPPORTUNITY")) for d in deals_362],
        "deals_6178": [(d.get("ID"), d.get("TITLE"), d.get("OPPORTUNITY")) for d in deals_lead_6178],
        "deals_16400": [(d.get("ID"), d.get("TITLE"), d.get("OPPORTUNITY")) for d in deals_lead_16400],
        "matched": [(d.get("ID"), d.get("TITLE"), d.get("OPPORTUNITY"), d.get("CONTACT_ID"), d.get("LEAD_ID")) for d in matched],
        "companies": [(c.get("ID"), c.get("TITLE")) for c in co_match],
        "leads": [(l.get("ID"), l.get("TITLE"), l.get("OPPORTUNITY"), l.get("STATUS_ID")) for l in leads],
        "acts": {"lead": len(act_lead), "contact": len(act_contact), "deal206": len(act_deal)},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
