"""Read-only Albert Levi Bitrix history check. Does not write."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from sqlalchemy import text
from investhome_api.db.session import SessionLocal

ARCHIVE = Path("/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE")


def fold(value: str | None) -> str:
    table = str.maketrans({"ı": "i", "İ": "i", "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g", "ç": "c", "Ç": "c"})
    return re.sub(r"\s+", " ", (value or "").translate(table).casefold()).strip()


def main() -> None:
    db = SessionLocal()
    contacts = db.execute(
        text(
            """
            select id::text, display_name, primary_email, primary_phone, source,
                   metadata_json::text as meta
            from crm_contacts
            where lower(display_name) like '%albert%'
               or lower(display_name) like '%levi%'
               or lower(display_name) like '%levı%'
            order by display_name
            """
        )
    ).mappings().all()
    print("CONTACT_HITS", len(contacts))
    for row in contacts:
        print("CONTACT", json.dumps({k: row[k] for k in row if k != "meta"}, ensure_ascii=False))

    target = None
    for row in contacts:
        name = fold(row["display_name"])
        if "albert" in name and "levi" in name:
            target = row
            break
    if target is None:
        print("NO_ALBERT")
        return

    cid = target["id"]
    agreements = db.execute(
        text(
            """
            select id::text, project_group, status, unit_number, source, source_external_id,
                   investment_amount, agreement_date::text
            from crm_agreements
            where contact_id = cast(:cid as uuid)
            """
        ),
        {"cid": cid},
    ).mappings().all()
    print("AGREEMENTS", json.dumps([dict(r) for r in agreements], ensure_ascii=False, default=str))

    acts = db.execute(
        text(
            """
            select id::text,
                   activity_type,
                   activity_category,
                   title,
                   left(coalesce(summary,''), 180) as summary,
                   left(coalesce(description,''), 4000) as description,
                   start_date::text,
                   created_at::text,
                   metadata_json::text as meta
            from crm_activities
            where entity_type = 'contact'
              and entity_id = cast(:cid as uuid)
              and archived_at is null
            order by coalesce(start_date, created_at)
            """
        ),
        {"cid": cid},
    ).mappings().all()

    excel = []
    api = []
    other = []
    by_type = Counter()
    api_kind = Counter()
    api_by_type = Counter()
    for act in acts:
        meta = json.loads(act["meta"] or "{}") if act["meta"] else {}
        has_excel = isinstance(meta.get("bitrix_historical_comment"), dict)
        has_api = isinstance(meta.get("bitrix_history"), dict)
        history = meta.get("bitrix_history") if has_api else {}
        kind = (history or {}).get("kind") or ""
        rec = {
            "id": act["id"],
            "activity_type": act["activity_type"],
            "title": act["title"],
            "start_date": act["start_date"],
            "created_at": act["created_at"],
            "kind": kind,
            "bitrix_entity_type": (history or {}).get("bitrix_entity_type"),
            "bitrix_entity_id": (history or {}).get("bitrix_entity_id"),
            "bitrix_record_id": (history or {}).get("bitrix_record_id") or (meta.get("bitrix_historical_comment") or {}).get("source_row"),
            "text": (act["description"] or act["summary"] or "").strip(),
            "source": "excel" if has_excel else "api" if has_api else "other",
        }
        by_type[act["activity_type"]] += 1
        if has_excel:
            excel.append(rec)
        elif has_api:
            api.append(rec)
            api_kind[kind or act["activity_type"]] += 1
            api_by_type[act["activity_type"]] += 1
        else:
            other.append(rec)

    def norm(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "").strip()).casefold()

    excel_texts = {norm(r["text"]) for r in excel if r["text"]}
    api_comments = [r for r in api if r["kind"] == "comment" or r["activity_type"] in {"comment", "note"}]
    new_comments = [r for r in api_comments if norm(r["text"]) not in excel_texts]

    print(
        json.dumps(
            {
                "canonical_crm_contact_id": cid,
                "person_name": target["display_name"],
                "email": target["primary_email"],
                "phone": target["primary_phone"],
                "source": target["source"],
                "agreement_count": len(agreements),
                "activity_total": len(acts),
                "excel_imported_comments": len(excel),
                "api_history_total": len(api),
                "other_activities": len(other),
                "all_activity_types": dict(by_type),
                "api_by_activity_type": dict(api_by_type),
                "api_by_kind": dict(api_kind),
                "api_comments": len(api_comments),
                "api_comments_not_in_excel": len(new_comments),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print("\n===== EXCEL COMMENTS =====")
    for rec in excel:
        print(json.dumps({"date": rec["start_date"] or rec["created_at"], "title": rec["title"], "text": rec["text"][:800]}, ensure_ascii=False))
    print("\n===== API HISTORY BY TYPE =====")
    for rec in api:
        print(
            json.dumps(
                {
                    "date": rec["start_date"] or rec["created_at"],
                    "type": rec["activity_type"],
                    "kind": rec["kind"],
                    "title": rec["title"],
                    "entity": f"{rec['bitrix_entity_type']}:{rec['bitrix_entity_id']}",
                    "record": rec["bitrix_record_id"],
                    "text": rec["text"][:500],
                },
                ensure_ascii=False,
            )
        )
    print("\n===== API COMMENTS NOT IN EXCEL =====")
    for rec in new_comments:
        print(
            json.dumps(
                {
                    "date": rec["start_date"] or rec["created_at"],
                    "kind": rec["kind"],
                    "title": rec["title"],
                    "record": rec["bitrix_record_id"],
                    "text": rec["text"],
                },
                ensure_ascii=False,
            )
        )
    print("\n===== OTHER =====")
    for rec in other:
        print(json.dumps({"date": rec["start_date"] or rec["created_at"], "type": rec["activity_type"], "title": rec["title"], "text": rec["text"][:300]}, ensure_ascii=False))
    db.close()


if __name__ == "__main__":
    main()
