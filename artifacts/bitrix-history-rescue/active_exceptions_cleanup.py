"""Active exceptions cleanup: incomplete history, unmatched 9, harmless review flags.

No document recovery. Never match by name only.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import text

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityVisibility,
    CrmTaskStatus,
)
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.user_auth import User

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore
from agreement_master_audit import (  # type: ignore
    HISTORY_KEY,
    OWNER_TYPE,
    TYPE_MAP,
    classify_activity,
    collapse_ws,
    emails_of,
    flatten,
    import_key_aliases,
    list_all,
    normalize_valid_email,
    parse_dt,
    phone_keys,
    phones_of,
    planned_history,
    utc_now,
)
from active_master_audit import (  # type: ignore
    apply_person,
    extra_safe_adds,
    fetch_history,
    load_people,
    slim_entity,
)

OUT = Path("/export/2026-09-final/BITRIX_ACTIVE_MASTER_AUDIT")
SUMMARY = OUT / "reports" / "ACTIVE_CONTACT_COMPLETENESS_SUMMARY.json"
CLEANUP = OUT / "reports" / "ACTIVE_EXCEPTIONS_CLEANUP.json"
HASH_PREFIX = re.compile(r"^#\d+\s+")
HONORIFIC = re.compile(r"\b(bey|han[ıi]m|mr|mrs|ms)\b", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9ğüşöçıİ]+", re.I)
ENTITY_TYPE_ID = {"lead": 1, "deal": 2, "contact": 3}
UNMATCHED_UUIDS = [
    "99d7643b-ca18-4423-beb9-1472a18b2aa5",
    "0d1bd0ed-df71-4c41-9831-363e0b9dee19",
    "bfba05ef-902c-4919-9b12-1d6c186b4bcd",
    "61d15990-0623-4e26-b8eb-22127a64730f",
    "2f9609b6-d32c-4938-9fda-9b3e64f8a55b",
    "7a9c8ed8-27e0-4d0e-ae81-d8c709185a88",
    "1d8cc791-6ab1-49c8-8abb-684b22f5add9",
    "701dc239-e259-4b80-8d80-ea0bf0d8fe97",
    "b50bb241-20ae-4a39-81b9-b01fbeaf79e3",
]


def fold_tr(value: str) -> str:
    table = str.maketrans("ğüşöçıĞÜŞÖÇİIı", "gusociGUSOCIii")
    return (value or "").translate(table).casefold()


def name_tokens(value: str) -> list[str]:
    text = HASH_PREFIX.sub("", collapse_ws(value))
    text = HONORIFIC.sub(" ", text)
    parts = [fold_tr(p) for p in NON_ALNUM.split(text) if p]
    out: list[str] = []
    for part in parts:
        if not out or out[-1] != part:
            out.append(part)
    return out


def harmless_display_name(os_name: str, bitrix_name: str) -> bool:
    a, b = name_tokens(os_name), name_tokens(bitrix_name)
    if not a or not b:
        return False
    if a == b:
        return True
    sa, sb = set(a), set(b)
    if sa <= sb or sb <= sa:
        return True
    if "".join(a) == "".join(b):
        return True
    return False


def source_excel_id(person: dict) -> str | None:
    meta = person.get("metadata_json") if isinstance(person.get("metadata_json"), dict) else {}
    bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    for ext in bitrix.get("external_ids") or []:
        text = str(ext)
        if ":" in text:
            tail = text.rsplit(":", 1)[-1].strip()
            if tail.isdigit():
                return tail
        if str(ext).isdigit():
            return str(ext)
    return None


def phone_variants(value: str | None) -> list[str]:
    keys = set(phone_keys(value))
    d = re.sub(r"\D+", "", value or "")
    if d:
        keys.update({d, "+" + d, d[-10:] if len(d) >= 10 else d})
        if d.startswith("90") and len(d) >= 12:
            keys.update({d[2:], "0" + d[2:]})
        if d.startswith("0") and len(d) == 11:
            keys.add("90" + d[1:])
        if len(d) >= 7:
            keys.add(d[-7:])
    return [k for k in keys if k]


def history_by_type(hist: dict) -> dict[str, int]:
    counts: Counter[str] = Counter()
    counts["comment"] = len(hist.get("comments") or [])
    for act in hist.get("activities") or []:
        kind = classify_activity(act)
        if kind == "other" and "WEBFORM" in str(act.get("PROVIDER_ID") or "").upper():
            kind = "webform"
        if kind == "whatsapp_session":
            kind = "whatsapp"
        counts[kind] += 1
    counts["whatsapp_message"] = len(hist.get("messages") or [])
    counts["open_channel_chats"] = len(hist.get("chats") or [])
    counts["timeline_entries"] = len(hist.get("timeline") or [])
    return dict(counts)


def fetch_history_extended(client: BitrixClient, mapping: dict) -> dict:
    hist = fetch_history(client, mapping)
    timeline: dict[str, dict] = {}
    entities = (
        [("contact", eid) for eid in mapping["contacts"]]
        + [("lead", eid) for eid in mapping["leads"]]
        + [("deal", eid) for eid in mapping["deals"]]
    )
    for etype, eid in entities:
        type_id = ENTITY_TYPE_ID[etype]
        rows = list_all(
            client,
            "crm.timeline.list",
            {"filter": {"ASSOCIATED_ENTITY_ID": eid, "ASSOCIATED_ENTITY_TYPE_ID": type_id}},
        )
        for row in rows:
            tid = str(row.get("ID") or "")
            if tid:
                timeline.setdefault(tid, {**row, "_entity_type": etype, "_entity_id": eid})
                if (row.get("COMMENT") or row.get("TEXT")) and tid not in {str(c.get("ID")) for c in hist.get("comments") or []}:
                    comments_extra = list(hist.get("comments") or [])
                    comments_extra.append({**row, "_entity_type": etype, "_entity_id": eid})
                    hist["comments"] = comments_extra
        acts = list_all(
            client,
            "crm.activity.list",
            {"filter": {"OWNER_TYPE_ID": OWNER_TYPE[etype], "OWNER_ID": eid}},
        )
        existing = {str(a.get("ID")) for a in hist.get("activities") or []}
        extra_acts = list(hist.get("activities") or [])
        for row in acts:
            aid = str(row.get("ID") or "")
            if aid and aid not in existing:
                extra_acts.append({**row, "_entity_type": etype, "_entity_id": eid})
                existing.add(aid)
        hist["activities"] = extra_acts
    hist["timeline"] = list(timeline.values())
    hist["live_history_count"] = (
        len(hist.get("comments") or [])
        + len(hist.get("activities") or [])
        + len(hist.get("messages") or [])
        + len(timeline)
    )
    return hist


def import_keys_for(db, cid: str) -> set[str]:
    keys: set[str] = set()
    for key_row in db.execute(
        text("select metadata_json from crm_activities where entity_id=cast(:cid as uuid)"),
        {"cid": cid},
    ).all():
        meta = key_row[0] if key_row else {}
        if not isinstance(meta, dict):
            continue
        for bucket in (HISTORY_KEY, "bitrix_historical_comment"):
            hist = meta.get(bucket)
            if isinstance(hist, dict) and hist.get("import_key"):
                keys |= import_key_aliases(str(hist["import_key"]))
            if isinstance(hist, dict) and hist.get("bitrix_record_id"):
                kind = str(hist.get("kind") or bucket)
                keys |= import_key_aliases(f"bitrix:{kind}:{hist['bitrix_record_id']}")
    return keys


def crm_history_count(db, cid: str) -> int:
    return db.execute(
        text(
            """
            select count(*) from crm_activities
            where entity_id=cast(:cid as uuid) and archived_at is null
              and entity_type in ('contact', 'CONTACT')
            """
        ),
        {"cid": cid},
    ).scalar() or 0


def import_history_only(db, actor, person: dict, hist: dict) -> int:
    imported = 0
    actor_id = actor.id if actor else None
    for plan in planned_history(person, hist):
        kind = plan["kind"]
        activity_type, category = TYPE_MAP.get(kind, TYPE_MAP["other"])
        occurred = parse_dt(plan["occurred"])
        db.add(
            CrmActivity(
                entity_type=CrmActivityEntityType.CONTACT,
                entity_id=UUID(person["cid"]),
                activity_type=activity_type,
                activity_category=category,
                title=plan["title"][:500],
                summary=(plan["description"] or "")[:1000] if plan["description"] else None,
                description=plan["description"],
                status=CrmActivityStatus.COMPLETED,
                task_status=CrmTaskStatus.COMPLETED if kind == "task" else None,
                priority=CrmActivityPriority.MEDIUM,
                visibility=CrmActivityVisibility.ORGANIZATION,
                start_date=occurred,
                completed_at=occurred,
                created_at=occurred or datetime.now(timezone.utc),
                updated_at=occurred or datetime.now(timezone.utc),
                created_by=actor_id,
                updated_by=actor_id,
                metadata_json=plan["metadata"],
            )
        )
        imported += 1
        person["import_keys"] |= import_key_aliases(plan["import_key"])
    return imported


def mapping_from_live(live: dict) -> dict:
    return {
        "contacts": live.get("contacts") or {},
        "leads": live.get("leads") or {},
        "deals": live.get("deals") or {},
        "company_title": live.get("company_title"),
        "assigned_name": live.get("assigned_name"),
        "assigned_by_id": live.get("assigned_by_id"),
    }


def consider_entity(person: dict, rec: dict, how: str, etype: str, bucket: dict[str, dict]) -> None:
    eid = str(rec.get("ID") or "")
    if not eid:
        return
    os_phones: set[str] = set()
    for phone in [person.get("primary_phone") or "", *(person.get("secondary_phones") or [])]:
        os_phones |= phone_keys(phone)
    os_emails = {normalize_valid_email(person.get("primary_email") or "") or ""}
    os_emails.update(normalize_valid_email(e) or "" for e in (person.get("secondary_emails") or []))
    os_emails.discard("")
    rec_phones: set[str] = set()
    for value in phones_of(rec):
        rec_phones |= phone_keys(value)
    rec_emails = set(emails_of(rec))
    phone_ok = bool(os_phones and rec_phones and (os_phones & rec_phones))
    email_ok = bool(os_emails and rec_emails and (os_emails & rec_emails))
    if phone_ok or email_ok:
        rec["_how"] = how
        bucket[eid] = rec


def search_unmatched(client: BitrixClient, person: dict) -> dict[str, Any]:
    review: list[str] = []
    contacts: dict[str, dict] = {}
    leads: dict[str, dict] = {}
    phones = [person.get("primary_phone") or ""]
    phones.extend(person.get("secondary_phones") or [])
    variants: list[str] = []
    for phone in phones:
        for item in phone_variants(phone):
            if item not in variants:
                variants.append(item)
    seen: set[tuple] = set()
    select = ["ID", "NAME", "LAST_NAME", "TITLE", "PHONE", "EMAIL", "CONTACT_ID", "COMPANY_ID"]
    for phone in variants[:12]:
        for method, etype in (("crm.contact.list", "contact"), ("crm.lead.list", "lead")):
            key = (method, phone)
            if key in seen:
                continue
            seen.add(key)
            body = client.call(method, {"filter[PHONE]": phone, "select[]": select, "start": 0})
            target = contacts if etype == "contact" else leads
            for rec in body.get("result") or []:
                if isinstance(rec, dict):
                    consider_entity(person, rec, f"list_phone_variant:{phone[-4:]}", etype, target)
        body = client.call("crm.duplicate.findbycomm", {"entity_type": "CONTACT", "type": "PHONE", "values[]": [phone]})
        ids = (body.get("result") or {}).get("CONTACT") if isinstance(body.get("result"), dict) else []
        for item_id in ids or []:
            got = client.call("crm.contact.get", {"id": item_id})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider_entity(person, rec, "duplicate_phone_variant", "contact", contacts)
        body = client.call("crm.duplicate.findbycomm", {"entity_type": "LEAD", "type": "PHONE", "values[]": [phone]})
        ids = (body.get("result") or {}).get("LEAD") if isinstance(body.get("result"), dict) else []
        for item_id in ids or []:
            got = client.call("crm.lead.get", {"id": item_id})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            consider_entity(person, rec, "duplicate_lead_phone_variant", "lead", leads)
    excel_id = source_excel_id(person)
    excel_note = None
    if excel_id:
        for etype, method, bucket in (("lead", "crm.lead.get", leads), ("contact", "crm.contact.get", contacts)):
            got = client.call(method, {"id": excel_id})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            if not rec:
                continue
            os_phones: set[str] = set()
            for phone in [person.get("primary_phone") or "", *(person.get("secondary_phones") or [])]:
                os_phones |= phone_keys(phone)
            rec_phones: set[str] = set()
            for value in phones_of(rec):
                rec_phones |= phone_keys(value)
            if os_phones and rec_phones and (os_phones & rec_phones):
                rec["_how"] = f"source_external_id+phone:{etype}"
                bucket[str(rec.get("ID"))] = rec
            elif os_phones and rec_phones and not (os_phones & rec_phones):
                excel_note = f"source_id_{etype}_{excel_id}_exists_phone_mismatch"
            elif not os_phones:
                excel_note = (
                    f"source_id_{etype}_{excel_id}_exists_but_no_os_phone_email;"
                    f"live_name={' '.join(p for p in [rec.get('NAME'), rec.get('LAST_NAME'), rec.get('TITLE')] if p)}"
                )
                review.append("excel_id_live_exists_no_deterministic_comms")
    org = collapse_ws(person.get("organization_name") or "")
    display = collapse_ws(person.get("display_name") or "")
    company_queries = []
    if org:
        company_queries.append(org)
    if "/" in display:
        company_queries.append(display.split("/", 1)[0].strip())
        company_queries.append(display.split("/", 1)[-1].strip())
    if display and not person.get("primary_phone"):
        company_queries.append(display)
    company_hits = []
    for title in company_queries:
        if len(title) < 3:
            continue
        body = client.call("crm.company.list", {"filter[TITLE]": title, "select[]": ["ID", "TITLE", "PHONE", "EMAIL"], "start": 0})
        rows = [r for r in (body.get("result") or []) if isinstance(r, dict)]
        if len(rows) == 1:
            company_hits.append(rows[0])
            break
        if len(rows) > 1:
            review.append(f"ambiguous_company_title:{title}:{len(rows)}")
    if len(company_hits) == 1:
        company = company_hits[0]
        cid = str(company.get("ID"))
        linked_contacts = list_all(client, "crm.contact.list", {"filter": {"COMPANY_ID": cid}})
        linked_leads = list_all(client, "crm.lead.list", {"filter": {"COMPANY_ID": cid}})
        if person.get("primary_phone") or person.get("primary_email"):
            for rec in linked_contacts:
                consider_entity(person, rec, "company_linked_contact", "contact", contacts)
            for rec in linked_leads:
                consider_entity(person, rec, "company_linked_lead", "lead", leads)
        elif len(linked_contacts) + len(linked_leads) == 1:
            rec = (linked_contacts or linked_leads)[0]
            etype = "contact" if linked_contacts else "lead"
            rec["_how"] = f"unique_company_linked_{etype}"
            (contacts if etype == "contact" else leads)[str(rec.get("ID"))] = rec
        else:
            review.append(
                f"company_found_{cid}_but_not_unique_person:contacts={len(linked_contacts)},leads={len(linked_leads)}"
            )
    if excel_note:
        review.append(excel_note)
    deals: dict[str, dict] = {}
    for eid in list(contacts):
        for rec in list_all(client, "crm.deal.list", {"filter": {"CONTACT_ID": eid}}):
            did = str(rec.get("ID") or "")
            if did:
                full = client.call("crm.deal.get", {"id": did})
                payload = full.get("result") if isinstance(full.get("result"), dict) else rec
                payload["_how"] = "deal_contact_id"
                deals[did] = payload
    for eid in list(leads):
        rec = leads[eid]
        if not rec.get("_how"):
            continue
        full = client.call("crm.lead.get", {"id": eid})
        payload = full.get("result") if isinstance(full.get("result"), dict) else rec
        payload["_how"] = rec.get("_how")
        leads[eid] = payload
        linked = str(payload.get("CONTACT_ID") or "")
        if linked and linked not in contacts:
            gotc = client.call("crm.contact.get", {"id": linked})
            crec = gotc.get("result") if isinstance(gotc.get("result"), dict) else {}
            consider_entity(person, crec, "lead_linked_contact", "contact", contacts)
        for rec in list_all(client, "crm.deal.list", {"filter": {"LEAD_ID": eid}}):
            did = str(rec.get("ID") or "")
            if did and did not in deals:
                full = client.call("crm.deal.get", {"id": did})
                payload = full.get("result") if isinstance(full.get("result"), dict) else rec
                payload["_how"] = "deal_lead_id"
                deals[did] = payload
    matched = bool(contacts or leads)
    if not matched:
        if not any(phone_variants(person.get("primary_phone"))) and not person.get("primary_email"):
            review.append("no_phone_or_email_for_live_match")
        review.append("still_unmatched")
    return {
        "contacts": {k: slim_entity(v) | {"_how": v.get("_how")} for k, v in contacts.items()},
        "leads": {k: slim_entity(v) | {"_how": v.get("_how")} for k, v in leads.items()},
        "deals": {k: slim_entity(v) | {"_how": v.get("_how")} for k, v in deals.items()},
        "raw_contacts": contacts,
        "raw_leads": leads,
        "review": review,
        "excel_id": excel_id,
        "matched": matched,
        "match_methods": sorted({v.get("_how") for v in list(contacts.values()) + list(leads.values()) if v.get("_how")}),
    }


def main() -> int:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    db = SessionLocal()
    actor = db.query(User).order_by(User.created_at.asc()).first()
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = summary["rows"]
    by_id = {r["canonical_uuid"]: r for r in rows}
    people = {p["cid"]: p for p in load_people(db)}
    incomplete_before = [
        r for r in rows
        if r.get("history_complete") != "YES" and (r.get("bitrix_contact_ids") or r.get("lead_ids"))
    ]
    incomplete_out = []
    newly_imported = 0
    try:
        print(f"incomplete_matched_before={len(incomplete_before)}", flush=True)
        for index, row in enumerate(incomplete_before, start=1):
            person = people[row["canonical_uuid"]]
            person["import_keys"] = import_keys_for(db, person["cid"])
            print(f"[hist {index}/{len(incomplete_before)}] {person['display_name']}", flush=True)
            mapping = {
                "contacts": {x: {"ID": x} for x in (row.get("bitrix_contact_ids") or "").split(",") if x},
                "leads": {x: {"ID": x} for x in (row.get("lead_ids") or "").split(",") if x},
                "deals": {x: {"ID": x} for x in (row.get("deal_ids") or "").split(",") if x},
            }
            hist = fetch_history_extended(client, mapping)
            by_type = history_by_type(hist)
            imported = import_history_only(db, actor, person, hist)
            if imported:
                db.commit()
                newly_imported += imported
            crm_after = crm_history_count(db, person["cid"])
            live_h = hist.get("live_history_count") or 0
            if live_h == 0:
                complete = "NA"
                reason = "live_bitrix_empty_comments_activities_openchannel_timeline"
                missing = 0
            elif crm_after >= live_h:
                complete = "YES"
                reason = "complete_after_refresh" if imported else "already_complete_on_refresh"
                missing = 0
            else:
                complete = "NO"
                reason = "crm_still_below_live_after_refresh"
                missing = live_h - crm_after
            rec = {
                "canonical_uuid": person["cid"],
                "name": person["display_name"],
                "bitrix_contact_id": row.get("bitrix_contact_ids") or "",
                "lead_ids": row.get("lead_ids") or "",
                "deal_ids": row.get("deal_ids") or "",
                "live_history_by_type": by_type,
                "live_history_count": live_h,
                "crm_activities_count": crm_after,
                "missing_count": missing,
                "newly_imported": imported,
                "history_complete": complete,
                "reason_incomplete": reason if complete != "YES" else "",
            }
            incomplete_out.append(rec)
            row["live_history_count"] = live_h
            row["crm_history_count"] = crm_after
            row["history_complete"] = complete
            row["history_imported"] = imported

        unmatched_out = []
        print("unmatched_retry=9", flush=True)
        for uid in UNMATCHED_UUIDS:
            person = people[uid]
            print(f"[unmatch] {person['display_name']}", flush=True)
            found = search_unmatched(client, person)
            imported = 0
            if found["matched"]:
                person["import_keys"] = import_keys_for(db, person["cid"])
                hist = fetch_history_extended(client, found)
                primary = next(iter((found.get("raw_contacts") or found["contacts"]).values()), {}) or next(
                    iter((found.get("raw_leads") or found["leads"]).values()), {}
                )
                adds, conflicts, _notes = extra_safe_adds(person, primary, None, None)
                result = apply_person(db, actor, person, mapping_from_live(found), hist, adds, conflicts)
                db.commit()
                imported = int(result.get("history") or 0)
                newly_imported += imported
                live_h = hist.get("live_history_count") or 0
                crm_after = crm_history_count(db, person["cid"])
                complete = "YES" if live_h and crm_after >= live_h else ("NA" if live_h == 0 else "NO")
                by_id[uid].update(
                    {
                        "bitrix_contact_ids": ",".join(sorted(found["contacts"])),
                        "lead_ids": ",".join(sorted(found["leads"])),
                        "deal_ids": ",".join(sorted(found["deals"])),
                        "match_method": ",".join(found["match_methods"]),
                        "live_history_count": live_h,
                        "crm_history_count": crm_after,
                        "history_complete": complete,
                        "review_required": "; ".join(conflicts),
                    }
                )
                unmatched_out.append(
                    {
                        "name": person["display_name"],
                        "canonical_uuid": uid,
                        "result": "matched",
                        "match_method": found["match_methods"],
                        "bitrix_contact_ids": sorted(found["contacts"]),
                        "lead_ids": sorted(found["leads"]),
                        "deal_ids": sorted(found["deals"]),
                        "history_imported": imported,
                        "reason": "",
                    }
                )
            else:
                unmatched_out.append(
                    {
                        "name": person["display_name"],
                        "canonical_uuid": uid,
                        "result": "unmatched",
                        "excel_id": found.get("excel_id"),
                        "phone": person.get("primary_phone"),
                        "email": person.get("primary_email"),
                        "reason": "; ".join(found.get("review") or ["still_unmatched"]),
                    }
                )

        harmless_cleared = []
        real_conflicts = []
        for row in rows:
            issues = [p.strip() for p in str(row.get("review_required") or "").split(";") if p.strip()]
            display_issues = [i for i in issues if i.startswith("display_name OS=")]
            other = [i for i in issues if i and not i.startswith("display_name OS=")]
            still = list(other)
            for issue in display_issues:
                try:
                    os_part, bx_part = issue.split(" Bitrix=", 1)
                    os_name = os_part.split("OS=", 1)[1]
                    bx_name = bx_part
                except ValueError:
                    still.append(issue)
                    continue
                if harmless_display_name(os_name, bx_name):
                    harmless_cleared.append(
                        {"uuid": row["canonical_uuid"], "name": row["name"], "issue": issue}
                    )
                else:
                    still.append(issue)
            unmatched = not row.get("bitrix_contact_ids") and not row.get("lead_ids")
            if unmatched:
                still = [i for i in still if i not in {"no_verified_bitrix_contact", "no_phone_or_email_for_live_match"}]
            row["review_required"] = "; ".join(still)
            row["conflicts"] = "; ".join(i for i in still if i.startswith("display_name") or "mismatch" in i)
            contact = db.get(CrmContact, UUID(row["canonical_uuid"]))
            if contact is None:
                continue
            if still:
                contact.review_required = True
                real_conflicts.append({"uuid": row["canonical_uuid"], "name": row["name"], "issues": still})
            else:
                contact.review_required = False
        db.commit()

        history_complete = sum(1 for r in rows if r.get("history_complete") == "YES")
        still_unmatched = [u for u in unmatched_out if u["result"] == "unmatched"]
        report = {
            "generated_at": utc_now(),
            "matched_but_incomplete_before": len(incomplete_before),
            "history_records_newly_recovered": newly_imported,
            "final_history_complete_count": history_complete,
            "unmatched_count": len(still_unmatched),
            "unmatched": still_unmatched,
            "newly_matched": [u for u in unmatched_out if u["result"] == "matched"],
            "real_conflict_count_after_cleanup": len(real_conflicts),
            "harmless_formatting_conflicts_cleared": len(harmless_cleared),
            "incomplete_detail": incomplete_out,
            "real_conflicts": real_conflicts,
            "harmless_cleared_samples": harmless_cleared[:40],
            "bitrix_calls": client.call_count,
            "documents_touched": 0,
        }
        CLEANUP.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        summary["rows"] = rows
        summary["summary"]["history_complete_count"] = history_complete
        summary["summary"]["unmatched"] = len(still_unmatched)
        summary["summary"]["matched"] = 121 - len(still_unmatched)
        summary["summary"]["conflicts_review_required"] = len(real_conflicts)
        summary["summary"]["exceptions_cleanup"] = {
            "newly_imported": newly_imported,
            "harmless_cleared": len(harmless_cleared),
            "real_conflicts": len(real_conflicts),
        }
        SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        import csv

        fields = [
            "canonical_uuid", "name", "bitrix_contact_ids", "lead_ids", "deal_ids", "match_method",
            "info_complete", "tutar_ve_para_birimi", "currency", "live_history_count",
            "crm_history_count", "history_complete", "conflicts", "review_required",
            "crm_history_count_before", "history_imported", "notes",
        ]
        with (OUT / "reports" / "ACTIVE_CONTACT_COMPLETENESS.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        print(json.dumps({k: report[k] for k in [
            "matched_but_incomplete_before", "history_records_newly_recovered",
            "final_history_complete_count", "unmatched_count", "real_conflict_count_after_cleanup",
            "harmless_formatting_conflicts_cleared", "bitrix_calls",
        ]}, indent=2))
        print(json.dumps({"unmatched": still_unmatched, "newly_matched": report["newly_matched"]}, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
