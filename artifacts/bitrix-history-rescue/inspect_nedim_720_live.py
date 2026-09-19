"""Read-only live Bitrix inspection for Uniloft 403 / deal 720. Never prints webhook."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

from sqlalchemy import select, text
from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document, DocumentLink

SCALAR_EMPTY = {None, "", 0, "0", "false", "False"}
FILE_IDS = ["96546", "96552", "96548", "96748", "96750", "96752", "96754", "96554"]
NEDIM_OS = "811c6aed-5f58-4c89-a9b1-0eebed64b9cf"
IZZET_OS = "339559ed-0d11-4e7c-a021-a07b388a817b"
AGREEMENT_720 = "444f6517-595a-4067-9c0c-3521708d2223"
OUT = Path("/tmp/nedim_720_live.json")


def populated(value: Any) -> bool:
    if isinstance(value, (list, dict, set, tuple)):
        if not value:
            return False
        if isinstance(value, dict):
            return any(populated(item) for item in value.values())
        return any(populated(item) for item in value)
    if value in SCALAR_EMPTY:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def compact(row: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    return {key: value for key, value in row.items() if populated(value) and key not in {"error", "error_description"}}


def phones(row: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for key in ("PHONE", "phone", "FM"):
        value = row.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and populated(item.get("VALUE")):
                    found.append(str(item.get("VALUE")))
                elif populated(item) and not isinstance(item, dict):
                    found.append(str(item))
        elif isinstance(value, dict) and populated(value.get("VALUE")):
            found.append(str(value.get("VALUE")))
    return found


def emails(row: dict[str, Any]) -> list[str]:
    found: list[str] = []
    value = row.get("EMAIL") or row.get("email")
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and populated(item.get("VALUE")):
                found.append(str(item.get("VALUE")))
            elif populated(item) and not isinstance(item, dict):
                found.append(str(item))
    elif isinstance(value, dict) and populated(value.get("VALUE")):
        found.append(str(value.get("VALUE")))
    return found


def main() -> None:
    env = load_env(ENV_PATH)
    webhook = webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or "")
    if not webhook:
        raise SystemExit("missing webhook")
    client = BitrixClient(webhook)

    contact_588 = compact(client.call("crm.contact.get", {"id": 588}).get("result"))
    contact_1160 = compact(client.call("crm.contact.get", {"id": 1160}).get("result"))
    deal = compact(client.call("crm.deal.get", {"id": 720}).get("result"))
    items = client.call("crm.deal.contact.items.get", {"id": 720}).get("result")
    item = compact(client.call("crm.item.get", {"entityTypeId": 2, "id": 720}).get("result"))
    comments = client.call("crm.timeline.comment.list", {"filter[ENTITY_ID]": 720, "filter[ENTITY_TYPE]": "deal"}).get("result")
    activities = client.call(
        "crm.activity.list",
        {"filter[OWNER_TYPE_ID]": 2, "filter[OWNER_ID]": 720, "select[]": ["ID", "TYPE_ID", "SUBJECT", "DESCRIPTION"]},
    ).get("result")
    statuses = client.call("crm.status.list", {"filter[ENTITY_ID]": "DEAL_STAGE"}).get("result")
    assigned_id = str(deal.get("ASSIGNED_BY_ID") or "")
    assigned = compact(client.call("user.get", {"ID": assigned_id}).get("result")[0] if assigned_id else None) if assigned_id else {}
    if assigned_id and not assigned:
        users = client.call("user.get", {"ID": assigned_id}).get("result")
        if isinstance(users, list) and users:
            assigned = compact(users[0] if isinstance(users[0], dict) else {})
        elif isinstance(users, dict):
            assigned = compact(users)

    stage_id = str(deal.get("STAGE_ID") or "")
    stage_name = None
    if isinstance(statuses, list):
        for row in statuses:
            if isinstance(row, dict) and str(row.get("STATUS_ID")) == stage_id:
                stage_name = row.get("NAME")
                break
    extra_statuses = client.call("crm.status.list", {}).get("result")
    if not stage_name and isinstance(extra_statuses, list):
        for row in extra_statuses:
            if isinstance(row, dict) and str(row.get("STATUS_ID")) == stage_id:
                stage_name = row.get("NAME")
                break

    db = SessionLocal()
    try:
        nedim = db.get(CrmContact, NEDIM_OS)
        izzet = db.get(CrmContact, IZZET_OS)
        docs = list(
            db.execute(
                text(
                    """
                    SELECT d.id::text, d.title, d.original_file_name, d.document_type, d.mime_type,
                           d.created_at::text, d.notes
                    FROM documents d
                    LEFT JOIN document_links l ON l.document_id = d.id
                    WHERE l.entity_type = 'crm_agreement' AND l.entity_id = :aid
                       OR d.notes ILIKE '%96546%'
                       OR d.notes ILIKE '%96552%'
                       OR d.notes ILIKE '%96548%'
                       OR d.notes ILIKE '%96748%'
                       OR d.notes ILIKE '%96750%'
                       OR d.notes ILIKE '%96752%'
                       OR d.notes ILIKE '%96754%'
                       OR d.notes ILIKE '%96554%'
                    """
                ),
                {"aid": AGREEMENT_720},
            ).mappings()
        )
    finally:
        db.close()

    def contact_os(row: CrmContact | None) -> dict[str, Any]:
        if row is None:
            return {}
        return {
            "id": str(row.id),
            "display_name": row.display_name,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "phone": row.primary_phone,
            "email": row.primary_email,
            "secondary_phones": row.secondary_phones,
            "secondary_emails": row.secondary_emails,
            "address_line1": row.address_line1,
            "address_line2": row.address_line2,
            "city": row.city,
            "postal_code": row.postal_code,
            "country": row.country,
            "organization_name": row.organization_name,
            "job_title": row.job_title,
            "source": row.source,
            "notes": (row.notes or "")[:500] if row.notes else None,
            "owner_user_id": str(row.owner_user_id) if row.owner_user_id else None,
        }

    payload = {
        "contact_588": {
            "name": " ".join(str(contact_588.get(k) or "") for k in ("NAME", "SECOND_NAME", "LAST_NAME")).strip(),
            "phones": phones(contact_588),
            "emails": emails(contact_588),
            "address": contact_588.get("ADDRESS"),
            "address_city": contact_588.get("ADDRESS_CITY"),
            "address_postal": contact_588.get("ADDRESS_POSTAL_CODE") or contact_588.get("ADDRESS_PROVINCE"),
            "address_country": contact_588.get("ADDRESS_COUNTRY"),
            "company": contact_588.get("COMPANY_ID") or contact_588.get("COMPANY_TITLE"),
            "post": contact_588.get("POST"),
            "source": contact_588.get("SOURCE_ID"),
            "source_desc": contact_588.get("SOURCE_DESCRIPTION"),
            "assigned": contact_588.get("ASSIGNED_BY_ID"),
            "comments": contact_588.get("COMMENTS"),
            "populated_keys": sorted(contact_588.keys()),
            "raw": contact_588,
        },
        "contact_1160": {
            "name": " ".join(str(contact_1160.get(k) or "") for k in ("NAME", "SECOND_NAME", "LAST_NAME")).strip(),
            "phones": phones(contact_1160),
            "emails": emails(contact_1160),
            "address": contact_1160.get("ADDRESS"),
            "address_city": contact_1160.get("ADDRESS_CITY"),
            "address_postal": contact_1160.get("ADDRESS_POSTAL_CODE") or contact_1160.get("ADDRESS_PROVINCE"),
            "address_country": contact_1160.get("ADDRESS_COUNTRY"),
            "company": contact_1160.get("COMPANY_ID") or contact_1160.get("COMPANY_TITLE"),
            "post": contact_1160.get("POST"),
            "source": contact_1160.get("SOURCE_ID"),
            "source_desc": contact_1160.get("SOURCE_DESCRIPTION"),
            "assigned": contact_1160.get("ASSIGNED_BY_ID"),
            "comments": contact_1160.get("COMMENTS"),
            "populated_keys": sorted(contact_1160.keys()),
            "raw": contact_1160,
        },
        "deal_720": {
            "title": deal.get("TITLE"),
            "opportunity": deal.get("OPPORTUNITY"),
            "currency": deal.get("CURRENCY_ID"),
            "stage_id": stage_id,
            "stage_name": stage_name,
            "begin": deal.get("BEGINDATE"),
            "close": deal.get("CLOSEDATE"),
            "assigned": deal.get("ASSIGNED_BY_ID"),
            "assigned_name": " ".join(
                str(assigned.get(k) or "") for k in ("NAME", "LAST_NAME", "EMAIL")
            ).strip()
            or assigned.get("NAME"),
            "comments": deal.get("COMMENTS"),
            "contact_id": deal.get("CONTACT_ID"),
            "company_id": deal.get("COMPANY_ID"),
            "participants": items,
            "activity_count": len(activities) if isinstance(activities, list) else activities,
            "comment_count": len(comments) if isinstance(comments, list) else comments,
            "uf_keys": sorted(k for k in deal.keys() if str(k).startswith("UF_")),
            "populated_keys": sorted(deal.keys()),
            "raw": deal,
            "item": item,
        },
        "os_nedim": contact_os(nedim),
        "os_izzet": contact_os(izzet),
        "os_docs": [dict(row) for row in docs],
        "calls": client.call_count,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, default=str, indent=2), encoding="utf-8")
    print(f"wrote {OUT} calls={client.call_count}")


if __name__ == "__main__":
    main()
