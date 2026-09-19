"""Read-only fetch of Bitrix contact 1160 and any lead by email/phone."""
from __future__ import annotations

import json
import os
from pathlib import Path

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore


def get(client, method, payload):
    body = client.call(method, payload)
    return body.get("result")


def main() -> None:
    env = dict(os.environ)
    if not env.get("BITRIX_ADMIN_WEBHOOK_URL"):
        env.update(load_env(ENV_PATH) if ENV_PATH.exists() else {})
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    contact = get(client, "crm.contact.get", {"id": "1160"}) or {}
    keys = [
        "ID", "NAME", "SECOND_NAME", "LAST_NAME", "PHONE", "EMAIL", "COMPANY_ID",
        "LEAD_ID", "ORIGIN_ID", "ORIGINATOR_ID", "ASSIGNED_BY_ID", "DATE_CREATE",
        "COMMENTS", "TYPE_ID", "SOURCE_ID",
    ]
    slim = {k: contact.get(k) for k in keys}
    leads_email = get(client, "crm.lead.list", {"filter[EMAIL]": "izzetk@gmail.com", "select[]": ["ID", "TITLE", "NAME", "LAST_NAME", "STATUS_ID", "CONTACT_ID", "PHONE", "EMAIL"]}) or []
    leads_phone = get(client, "crm.lead.list", {"filter[PHONE]": "+41795969733", "select[]": ["ID", "TITLE", "NAME", "LAST_NAME", "STATUS_ID", "CONTACT_ID"]}) or []
    deals = get(client, "crm.deal.list", {"filter[CONTACT_ID]": "1160", "select[]": ["ID", "TITLE", "STAGE_ID", "OPPORTUNITY", "CURRENCY_ID", "CONTACT_ID"]}) or []
    print(json.dumps({
        "contact_1160": slim,
        "leads_by_email": leads_email,
        "leads_by_phone": leads_phone,
        "deals_by_contact_1160": deals,
    }, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
