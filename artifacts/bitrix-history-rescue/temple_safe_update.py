"""Create Can Mergen Temple agreement from verified live Bitrix. Probe Selçuk/Harun read-only."""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.identity import normalize_valid_email, parse_phone

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

OUT = Path("/export/2026-09-final/BITRIX_THE_TEMPLE_FULL_SCAN")
CAN_UUID = UUID("e488dac2-22f7-45a7-847d-fefd3bec945d")
TEMPLE_PROJECT_ID = UUID("d50708cb-60b3-465a-8b16-6d30f802af8d")
TUTAR_LABEL = "Tutar ve para birimi"
TUTAR_FIELD_ID = "OPPORTUNITY+CURRENCY_ID"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def flatten(payload: dict) -> dict:
    out = {}
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
        keys.update({k for k in {parsed.match_key, parsed.digits, parsed.e164 or ""} if k})
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if len(digits) >= 10:
        keys.add(digits[-10:])
    return keys


def get_result(client: BitrixClient, method: str, payload: dict) -> dict:
    body = client.call(method, payload)
    rec = body.get("result")
    return rec if isinstance(rec, dict) else {}


def entity_history(client: BitrixClient, etype: str, eid: str) -> dict:
    owner = {"contact": 3, "lead": 1, "deal": 2}[etype]
    comments = list_all(client, "crm.timeline.comment.list", {"filter": {"ENTITY_TYPE": etype, "ENTITY_ID": eid}})
    activities = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": owner, "OWNER_ID": eid}})
    return {"comments": comments, "activities": activities}


def populate(value: dict) -> dict:
    return {k: v for k, v in value.items() if v not in (None, "", [], {}, "0", 0, False)}


def main() -> int:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)

    print("Fetching live Bitrix 748/750/752…", flush=True)
    deal_748 = get_result(client, "crm.deal.get", {"id": "748"})
    deal_750 = get_result(client, "crm.deal.get", {"id": "750"})
    deal_752 = get_result(client, "crm.deal.get", {"id": "752"})
    contact_1242 = get_result(client, "crm.contact.get", {"id": "1242"})
    lead_38510 = get_result(client, "crm.lead.get", {"id": "38510"})
    items_748 = client.call("crm.deal.contact.items.get", {"id": "748"}).get("result") or []
    items_750 = client.call("crm.deal.contact.items.get", {"id": "750"}).get("result") or []
    items_752 = client.call("crm.deal.contact.items.get", {"id": "752"}).get("result") or []

    hist_748 = entity_history(client, "deal", "748")
    hist_750 = entity_history(client, "deal", "750")
    hist_752 = entity_history(client, "deal", "752")
    hist_1242 = entity_history(client, "contact", "1242")
    hist_38510 = entity_history(client, "lead", "38510")

    # Selçuk: only deterministic comms, not surname
    selcuk_phones = phones_of(deal_750) 
    selcuk_emails = emails_of(deal_750)
    selcuk_contacts = []
    selcuk_leads = []
    for item in items_750 if isinstance(items_750, list) else []:
        if isinstance(item, dict) and item.get("CONTACT_ID"):
            rec = get_result(client, "crm.contact.get", {"id": item["CONTACT_ID"]})
            if rec:
                selcuk_contacts.append(rec)
                selcuk_phones.extend(phones_of(rec))
                selcuk_emails.extend(emails_of(rec))
    cid_750 = str(deal_750.get("CONTACT_ID") or "")
    if cid_750 not in {"", "0"}:
        rec = get_result(client, "crm.contact.get", {"id": cid_750})
        if rec:
            selcuk_contacts.append(rec)
            selcuk_phones.extend(phones_of(rec))
            selcuk_emails.extend(emails_of(rec))
    lid_750 = str(deal_750.get("LEAD_ID") or "")
    if lid_750 not in {"", "0"}:
        rec = get_result(client, "crm.lead.get", {"id": lid_750})
        if rec:
            selcuk_leads.append(rec)
            selcuk_phones.extend(phones_of(rec))
            selcuk_emails.extend(emails_of(rec))

    # pull phones/emails from comments/activities text? only explicit tel:/mailto: would be deterministic.
    # Also duplicate.findbycomm for any found numbers.
    found_contacts_by_comm = []
    for phone in dict.fromkeys(selcuk_phones):
        body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "PHONE", "values[]": [phone]})
        ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
        for item_id in ids or []:
            found_contacts_by_comm.append(get_result(client, "crm.contact.get", {"id": item_id}))
    for email in dict.fromkeys(selcuk_emails):
        body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "EMAIL", "values[]": [email]})
        ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
        for item_id in ids or []:
            found_contacts_by_comm.append(get_result(client, "crm.contact.get", {"id": item_id}))

    harun_items = items_752 if isinstance(items_752, list) else []
    harun_contact = str(deal_752.get("CONTACT_ID") or "")
    harun_lead = str(deal_752.get("LEAD_ID") or "")
    harun_company = str(deal_752.get("COMPANY_ID") or "")
    harun_uf = {k: v for k, v in deal_752.items() if str(k).startswith("UF_") and v not in (None, "", [], {}, "0", 0)}
    selcuk_uf = {k: v for k, v in deal_750.items() if str(k).startswith("UF_") and v not in (None, "", [], {}, "0", 0)}
    can_uf = {k: v for k, v in deal_748.items() if str(k).startswith("UF_") and v not in (None, "", [], {}, "0", 0)}

    live = {
        "deal_748": {
            "ID": deal_748.get("ID"),
            "TITLE": deal_748.get("TITLE"),
            "STAGE_ID": deal_748.get("STAGE_ID"),
            "CLOSED": deal_748.get("CLOSED"),
            "OPPORTUNITY": deal_748.get("OPPORTUNITY"),
            "CURRENCY_ID": deal_748.get("CURRENCY_ID"),
            "BEGINDATE": deal_748.get("BEGINDATE"),
            "ASSIGNED_BY_ID": deal_748.get("ASSIGNED_BY_ID"),
            "CONTACT_ID": deal_748.get("CONTACT_ID"),
            "LEAD_ID": deal_748.get("LEAD_ID"),
            "COMMENTS": deal_748.get("COMMENTS"),
            "TYPE_ID": deal_748.get("TYPE_ID"),
            "contact_items": items_748,
            "uf_populated": can_uf,
            "history": {"comments": len(hist_748["comments"]), "activities": len(hist_748["activities"])},
        },
        "contact_1242": {
            "ID": contact_1242.get("ID"),
            "NAME": contact_1242.get("NAME"),
            "LAST_NAME": contact_1242.get("LAST_NAME"),
            "PHONE": phones_of(contact_1242),
            "EMAIL": emails_of(contact_1242),
            "ASSIGNED_BY_ID": contact_1242.get("ASSIGNED_BY_ID"),
        },
        "lead_38510": {
            "ID": lead_38510.get("ID"),
            "TITLE": lead_38510.get("TITLE"),
            "NAME": lead_38510.get("NAME"),
            "LAST_NAME": lead_38510.get("LAST_NAME"),
            "STATUS_ID": lead_38510.get("STATUS_ID"),
            "CONTACT_ID": lead_38510.get("CONTACT_ID"),
            "PHONE": phones_of(lead_38510),
            "EMAIL": emails_of(lead_38510),
        },
        "deal_750": {
            "ID": deal_750.get("ID"),
            "TITLE": deal_750.get("TITLE"),
            "STAGE_ID": deal_750.get("STAGE_ID"),
            "CLOSED": deal_750.get("CLOSED"),
            "OPPORTUNITY": deal_750.get("OPPORTUNITY"),
            "CURRENCY_ID": deal_750.get("CURRENCY_ID"),
            "CONTACT_ID": deal_750.get("CONTACT_ID"),
            "LEAD_ID": deal_750.get("LEAD_ID"),
            "COMPANY_ID": deal_750.get("COMPANY_ID"),
            "COMMENTS": deal_750.get("COMMENTS"),
            "TYPE_ID": deal_750.get("TYPE_ID"),
            "ASSIGNED_BY_ID": deal_750.get("ASSIGNED_BY_ID"),
            "BEGINDATE": deal_750.get("BEGINDATE"),
            "contact_items": items_750,
            "uf_populated": selcuk_uf,
            "history": {
                "comments": hist_750["comments"],
                "activities": [
                    {"ID": a.get("ID"), "SUBJECT": a.get("SUBJECT"), "PROVIDER_ID": a.get("PROVIDER_ID"), "TYPE_ID": a.get("TYPE_ID")}
                    for a in hist_750["activities"]
                ],
            },
            "linked_contacts": [
                {"ID": c.get("ID"), "NAME": c.get("NAME"), "LAST_NAME": c.get("LAST_NAME"), "PHONE": phones_of(c), "EMAIL": emails_of(c)}
                for c in selcuk_contacts
            ],
            "linked_leads": [
                {"ID": c.get("ID"), "TITLE": c.get("TITLE"), "NAME": c.get("NAME"), "LAST_NAME": c.get("LAST_NAME"), "PHONE": phones_of(c), "EMAIL": emails_of(c)}
                for c in selcuk_leads
            ],
            "phones_found": list(dict.fromkeys(selcuk_phones)),
            "emails_found": list(dict.fromkeys(selcuk_emails)),
            "contacts_by_comm": [
                {"ID": c.get("ID"), "NAME": c.get("NAME"), "LAST_NAME": c.get("LAST_NAME")}
                for c in found_contacts_by_comm
                if c
            ],
        },
        "deal_752": {
            "ID": deal_752.get("ID"),
            "TITLE": deal_752.get("TITLE"),
            "STAGE_ID": deal_752.get("STAGE_ID"),
            "CLOSED": deal_752.get("CLOSED"),
            "OPPORTUNITY": deal_752.get("OPPORTUNITY"),
            "CURRENCY_ID": deal_752.get("CURRENCY_ID"),
            "CONTACT_ID": deal_752.get("CONTACT_ID"),
            "LEAD_ID": deal_752.get("LEAD_ID"),
            "COMPANY_ID": deal_752.get("COMPANY_ID"),
            "COMMENTS": deal_752.get("COMMENTS"),
            "TYPE_ID": deal_752.get("TYPE_ID"),
            "BEGINDATE": deal_752.get("BEGINDATE"),
            "ASSIGNED_BY_ID": deal_752.get("ASSIGNED_BY_ID"),
            "contact_items": harun_items,
            "uf_populated": harun_uf,
            "history": {
                "comments": hist_752["comments"],
                "activities": [
                    {"ID": a.get("ID"), "SUBJECT": a.get("SUBJECT"), "PROVIDER_ID": a.get("PROVIDER_ID"), "TYPE_ID": a.get("TYPE_ID")}
                    for a in hist_752["activities"]
                ],
            },
        },
        "history_counts": {
            "contact_1242": {"comments": len(hist_1242["comments"]), "activities": len(hist_1242["activities"])},
            "lead_38510": {"comments": len(hist_38510["comments"]), "activities": len(hist_38510["activities"])},
        },
    }

    db = SessionLocal()
    blockers: list[str] = []
    created = None
    try:
        before_agreements = db.execute(text("select count(*) from crm_agreements")).scalar() or 0
        before_temple = db.execute(text("select count(*) from crm_agreements where project_group='the_temple'")).scalar() or 0
        before_contacts = db.execute(text("select count(*) from crm_contacts")).scalar() or 0
        can = db.get(CrmContact, CAN_UUID)
        if can is None:
            blockers.append("canonical_can_mergen_missing")
        existing = db.execute(
            text(
                """
                select id::text from crm_agreements
                where contact_id = :cid or source_external_id = 'bitrix_deal:748'
                   or metadata_json->>'bitrix_deal_id' = '748'
                """
            ),
            {"cid": str(CAN_UUID)},
        ).scalars().all()
        if existing:
            blockers.append(f"can_already_has_or_deal_748_exists:{existing}")

        live_phones = set().union(*[phone_keys(p) for p in phones_of(contact_1242)]) if contact_1242 else set()
        os_phones = phone_keys(can.primary_phone if can else None)
        live_emails = set(emails_of(contact_1242))
        os_email = (normalize_valid_email(can.primary_email or "") or "") if can else ""
        phone_ok = bool(live_phones and os_phones and (live_phones & os_phones))
        email_ok = bool(os_email and os_email in live_emails)
        contact_id_ok = str(contact_1242.get("ID") or "") == "1242"
        lead_link_ok = str(lead_38510.get("CONTACT_ID") or "") in {"1242", ""} or str(deal_748.get("CONTACT_ID") or "") == "1242"
        deal_contact_ok = str(deal_748.get("CONTACT_ID") or "") == "1242"
        deal_id_ok = str(deal_748.get("ID") or "") == "748"
        if not (phone_ok or email_ok):
            blockers.append("can_live_contact_1242_phone_email_do_not_match_os")
        if not contact_id_ok or not deal_id_ok or not deal_contact_ok:
            blockers.append("live_ids_mismatch_verified_748_1242")
        if str(deal_748.get("OPPORTUNITY") or "") not in {"238008.00", "238008", "238008.0000"}:
            blockers.append(f"tutar_mismatch:{deal_748.get('OPPORTUNITY')}")
        if "203" not in str(deal_748.get("TITLE") or ""):
            blockers.append("unit_203_not_in_live_title")

        identity = {
            "phone_ok": phone_ok,
            "email_ok": email_ok,
            "deal_contact_ok": deal_contact_ok,
            "lead_id": lead_38510.get("ID"),
            "lead_contact_id": lead_38510.get("CONTACT_ID"),
            "os_phone": can.primary_phone if can else None,
            "live_phones": phones_of(contact_1242),
            "os_email": can.primary_email if can else None,
            "live_emails": emails_of(contact_1242),
            "lead_link_ok": lead_link_ok,
        }

        if not blockers:
            begin = str(deal_748.get("BEGINDATE") or "")[:10]
            agreement_date = date.fromisoformat(begin) if begin else date(2026, 9, 15)
            meta = {
                "source": "bitrix_live",
                "imported_historical_agreement": False,
                "project_group": "the_temple",
                "project_label": "The Temple",
                "bitrix_deal_id": "748",
                "bitrix_contact_id": "1242",
                "bitrix_lead_id": "38510",
                "bitrix_deal_title": deal_748.get("TITLE"),
                "bitrix_deal_stage": deal_748.get("STAGE_ID"),
                "bitrix_deal_stage_label": "Kimlik Bilgiler Süreci / Client Documents",
                "bitrix_deal_status": "active",
                "bitrix_assigned_by_id": str(deal_748.get("ASSIGNED_BY_ID") or "92"),
                "responsible_person": "Beyza Karakuş",
                "tutar_ve_para_birimi_label": TUTAR_LABEL,
                "tutar_ve_para_birimi_field_id": TUTAR_FIELD_ID,
                "tutar_ve_para_birimi_amount": "238008.00",
                "tutar_ve_para_birimi_currency": "USD",
                "tutar_not_amount_paid": True,
                "unit_number": "203",
                "bitrix_deal_snapshot": {
                    "ID": "748",
                    "TITLE": deal_748.get("TITLE"),
                    "STAGE_ID": deal_748.get("STAGE_ID"),
                    "OPPORTUNITY": deal_748.get("OPPORTUNITY"),
                    "CURRENCY_ID": deal_748.get("CURRENCY_ID"),
                    "BEGINDATE": deal_748.get("BEGINDATE"),
                    "ASSIGNED_BY_ID": deal_748.get("ASSIGNED_BY_ID"),
                    "CLOSED": deal_748.get("CLOSED"),
                    "CONTACT_ID": deal_748.get("CONTACT_ID"),
                    "LEAD_ID": deal_748.get("LEAD_ID") or "38510",
                },
                "retrieved_at": utc_now(),
            }
            agreement = CrmAgreement(
                contact_id=CAN_UUID,
                project_id=TEMPLE_PROJECT_ID,
                project_group="the_temple",
                source="bitrix_live",
                source_external_id="bitrix_deal:748",
                status=CrmAgreementStatus.ACTIVE,
                agreement_date=agreement_date,
                unit_number="203",
                investment_amount=None,
                review_required=False,
                metadata_json=meta,
            )
            db.add(agreement)
            db.flush()
            contact_meta = dict(can.metadata_json or {})
            live_meta = dict(contact_meta.get("bitrix_live") or {})
            live_meta.update(
                {
                    "contact_ids": ["1242"],
                    "lead_ids": ["38510"],
                    "deal_ids": ["748"],
                    "tutar_ve_para_birimi": [
                        {
                            "bitrix_field_id": TUTAR_FIELD_ID,
                            "bitrix_field_label": TUTAR_LABEL,
                            "amount": "238008.00",
                            "currency": "USD",
                            "deal_id": "748",
                            "not_amount_paid": True,
                        }
                    ],
                    "updated_at": utc_now(),
                }
            )
            bitrix_imp = dict(contact_meta.get("bitrix_import") or {})
            ext = list(bitrix_imp.get("external_ids") or [])
            for token in ("bitrix_contact:1242", "bitrix_lead:38510"):
                if token not in ext:
                    ext.append(token)
            bitrix_imp["external_ids"] = ext
            contact_meta["bitrix_import"] = bitrix_imp
            contact_meta["bitrix_live"] = live_meta
            can.metadata_json = contact_meta
            flag_modified(can, "metadata_json")
            db.commit()
            created = str(agreement.id)
        else:
            db.rollback()

        after_agreements = db.execute(text("select count(*) from crm_agreements")).scalar() or 0
        after_temple = db.execute(text("select count(*) from crm_agreements where project_group='the_temple'")).scalar() or 0
        after_contacts = db.execute(text("select count(*) from crm_contacts")).scalar() or 0
        can_agreements = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    select id::text, project_group, unit_number, status::text, source, source_external_id,
                           metadata_json->>'bitrix_deal_id' as deal_id,
                           metadata_json->>'tutar_ve_para_birimi_amount' as tutar
                    from crm_agreements where contact_id = :cid
                    """
                ),
                {"cid": str(CAN_UUID)},
            ).mappings().all()
        ]
        temple_rows = [
            dict(r)
            for r in db.execute(
                text(
                    """
                    select a.id::text, c.display_name, a.unit_number, a.source,
                           a.metadata_json->>'bitrix_deal_id' as deal_id
                    from crm_agreements a join crm_contacts c on c.id=a.contact_id
                    where a.project_group='the_temple' order by c.display_name
                    """
                )
            ).mappings().all()
        ]
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    selcuk_can_match = False
    # Deterministic only: if Selçuk deal shares phone/email with Can 1242, report related-not-same-person unless IDs equal
    can_phone_keys = set().union(*[phone_keys(p) for p in phones_of(contact_1242)]) if contact_1242 else set()
    selcuk_phone_keys = set().union(*[phone_keys(p) for p in selcuk_phones]) if selcuk_phones else set()
    if can_phone_keys and selcuk_phone_keys and (can_phone_keys & selcuk_phone_keys):
        selcuk_can_match = True

    selcuk = {
        "deal_id": "750",
        "title": deal_750.get("TITLE"),
        "unit": "103",
        "tutar": f"{deal_750.get('OPPORTUNITY')} {deal_750.get('CURRENCY_ID')}",
        "stage": deal_750.get("STAGE_ID"),
        "contact_id": deal_750.get("CONTACT_ID"),
        "lead_id": deal_750.get("LEAD_ID"),
        "company_id": deal_750.get("COMPANY_ID"),
        "contact_items": items_750,
        "phones_found": live["deal_750"]["phones_found"],
        "emails_found": live["deal_750"]["emails_found"],
        "linked_contacts": live["deal_750"]["linked_contacts"],
        "linked_leads": live["deal_750"]["linked_leads"],
        "contacts_by_comm": live["deal_750"]["contacts_by_comm"],
        "timeline_comments": len(hist_750["comments"]),
        "activities": len(hist_750["activities"]),
        "comments_preview": [str(c.get("COMMENT") or c.get("TEXT") or "")[:240] for c in hist_750["comments"][:8]],
        "shares_phone_with_can_1242": selcuk_can_match,
        "os_canonical_match": None,
        "can_create_new_person": False,
        "reason": "",
    }
    if selcuk["contact_id"] in (None, "", "0") and not selcuk["phones_found"] and not selcuk["emails_found"] and not selcuk["linked_contacts"] and not selcuk["linked_leads"]:
        selcuk["os_canonical_match"] = "NONE"
        selcuk["can_create_new_person"] = False
        selcuk["reason"] = (
            "Deal 750 has no Bitrix CONTACT_ID, no contact items, no LEAD_ID, no phone, no email, "
            "and no comm-duplicate hits. Title contains 'Selçuk Mergen' but surname-only/name-only matching is forbidden. "
            "Cannot attach to Can Mergen or create a new canonical person until a phone, email, or linked CRM entity exists."
        )
    elif selcuk_can_match:
        selcuk["os_canonical_match"] = "REVIEW_SHARED_COMM_WITH_CAN"
        selcuk["reason"] = "Deterministic comm overlap with Can contact 1242; not sufficient to merge or reuse without explicit person identity on deal 750."
    else:
        selcuk["os_canonical_match"] = "UNMATCHED"
        selcuk["reason"] = "No deterministic OS match."

    harun_files = any(isinstance(v, (dict, list)) for v in harun_uf.values())
    harun = {
        "deal_id": "752",
        "title": deal_752.get("TITLE"),
        "stage": deal_752.get("STAGE_ID"),
        "closed": deal_752.get("CLOSED"),
        "opportunity": deal_752.get("OPPORTUNITY"),
        "currency": deal_752.get("CURRENCY_ID"),
        "contact_id": harun_contact,
        "lead_id": harun_lead,
        "company_id": harun_company,
        "contact_items": harun_items,
        "comments": deal_752.get("COMMENTS"),
        "type_id": deal_752.get("TYPE_ID"),
        "uf_populated_count": len(harun_uf),
        "has_document_uf": harun_files,
        "timeline_comments": len(hist_752["comments"]),
        "activities": len(hist_752["activities"]),
        "units_in_title": "106-201-202-301-401-402",
        "classification": "multi-unit placeholder / potential deal — not a real agreement",
        "evidence": [
            "Pipeline The Temple, stage C30:NEW (Kimlik Bilgiler Süreci) — earliest stage, not executing/won",
            f"Tutar ve para birimi / OPPORTUNITY = {deal_752.get('OPPORTUNITY')} {deal_752.get('CURRENCY_ID')} (zero)",
            "No CONTACT_ID, no deal.contact.items, no LEAD_ID, no COMPANY_ID",
            "Title lists six units (106, 201, 202, 301, 401, 402), including 301 which overlaps Albert 301-302",
            f"Populated non-zero UF fields: {len(harun_uf)}; document-like UF present: {harun_files}",
            f"Timeline comments={len(hist_752['comments'])} activities={len(hist_752['activities'])}",
            "No reservation-form / passport / LLC docs like Albert deal 728",
            "CLOSED=N so still open, but commercially empty — treat as potential/multi-unit placeholder, not a signed agreement",
        ],
    }

    report = {
        "generated_at": utc_now(),
        "can_agreement_created": created,
        "blockers": blockers,
        "identity_748_1242": identity,
        "counts": {
            "agreements_before": before_agreements,
            "agreements_after": after_agreements,
            "temple_before": before_temple,
            "temple_after": after_temple,
            "contacts_before": before_contacts,
            "contacts_after": after_contacts,
            "can_agreements": can_agreements,
            "temple_agreements": temple_rows,
        },
        "selcuk": selcuk,
        "harun": harun,
        "live_snapshot": live,
        "bitrix_calls": client.call_count,
        "no_selcuk_agreement_created": True,
        "no_harun_agreement_created": True,
        "no_duplicate_contact": after_contacts == before_contacts,
    }
    (OUT / "reports" / "THE_TEMPLE_SAFE_UPDATE.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps({k: report[k] for k in ("can_agreement_created", "blockers", "counts", "selcuk", "harun") if k != "live_snapshot"}, ensure_ascii=False, indent=2, default=str)[:8000])
    return 0 if not blockers else 2


if __name__ == "__main__":
    sys.exit(main())
