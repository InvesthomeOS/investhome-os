"""Match remaining unmatched Active people whose source Excel ID exists as a live Bitrix lead."""
from __future__ import annotations

import json
from pathlib import Path

from investhome_api.db.session import SessionLocal
from investhome_api.models.user_auth import User

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore
from active_master_audit import apply_person, extra_safe_adds, load_people, slim_entity  # type: ignore
from active_exceptions_cleanup import fetch_history_extended, import_keys_for, mapping_from_live  # type: ignore

OUT = Path("/export/2026-09-final/BITRIX_ACTIVE_MASTER_AUDIT/reports")
TARGETS = {
    "99d7643b-ca18-4423-beb9-1472a18b2aa5": "32744",
    "0d1bd0ed-df71-4c41-9831-363e0b9dee19": "34826",
    "61d15990-0623-4e26-b8eb-22127a64730f": "34818",
    "2f9609b6-d32c-4938-9fda-9b3e64f8a55b": "37084",
    "1d8cc791-6ab1-49c8-8abb-684b22f5add9": "34824",
    "b50bb241-20ae-4a39-81b9-b01fbeaf79e3": "27968",
}


def main() -> int:
    env = load_env(ENV_PATH)
    client = BitrixClient(webhook_base(env.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    db = SessionLocal()
    actor = db.query(User).order_by(User.created_at.asc()).first()
    people = {p["cid"]: p for p in load_people(db)}
    matched = []
    try:
        for uid, lead_id in TARGETS.items():
            person = people[uid]
            got = client.call("crm.lead.get", {"id": lead_id})
            rec = got.get("result") if isinstance(got.get("result"), dict) else {}
            if not rec or str(rec.get("ID")) != str(lead_id):
                print("SKIP", person["display_name"], "lead_missing", lead_id)
                continue
            rec["_how"] = "source_external_id+live_lead_get"
            mapping = {
                "contacts": {},
                "leads": {lead_id: slim_entity(rec) | {"_how": rec["_how"]}},
                "raw_contacts": {},
                "raw_leads": {lead_id: rec},
                "deals": {},
                "company_title": None,
                "assigned_name": None,
                "assigned_by_id": rec.get("ASSIGNED_BY_ID"),
            }
            linked = str(rec.get("CONTACT_ID") or "")
            if linked and linked not in {"0", ""}:
                gotc = client.call("crm.contact.get", {"id": linked})
                crec = gotc.get("result") if isinstance(gotc.get("result"), dict) else {}
                if crec:
                    crec["_how"] = "lead_linked_contact"
                    mapping["contacts"][linked] = slim_entity(crec) | {"_how": "lead_linked_contact"}
                    mapping["raw_contacts"][linked] = crec
            person["import_keys"] = import_keys_for(db, uid)
            hist = fetch_history_extended(client, mapping)
            primary = rec
            adds, conflicts, _notes = extra_safe_adds(person, primary, None, None)
            # ID match is allowed here; do not block on name formatting.
            conflicts = [c for c in conflicts if not str(c).startswith("display_name OS=")]
            apply_person(db, actor, person, mapping_from_live(mapping), hist, adds, conflicts)
            db.commit()
            matched.append(
                {
                    "name": person["display_name"],
                    "uuid": uid,
                    "lead_id": lead_id,
                    "contact_ids": sorted(mapping["contacts"]),
                    "imported": len(hist.get("comments") or []) + len(hist.get("activities") or []),
                    "live_history": hist.get("live_history_count") or 0,
                }
            )
            print("MATCHED", person["display_name"], "lead", lead_id)
        path = OUT / "ACTIVE_EXCEPTIONS_CLEANUP.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        report["source_id_followup_matched"] = matched
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps({"followup_matched": matched, "calls": client.call_count}, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
