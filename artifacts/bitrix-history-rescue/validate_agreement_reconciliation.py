"""Post-reconciliation validation. Read-only."""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

from sqlalchemy import text
from investhome_api.db.session import SessionLocal

CSV = Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/reports/BITRIX_AGREEMENT_RECONCILIATION.csv")
BACKUP = Path("/export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/backups/investhome-pre-agreement-reconciliation-20260917.dump")


def main() -> None:
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    status = Counter(r["status"] for r in rows)
    fields_add = Counter(r["field"] for r in rows if r["status"] == "ADD")
    payment_roles = Counter(r["field"] for r in rows if r["field"].startswith("payment.") and r["bitrix_value"])
    conflicts = [r for r in rows if r["status"] == "CONFLICT_REVIEW"]
    match = Counter(r["match_status"] for r in rows)
    people = {r["canonical_crm_contact_id"]: r["person_name"] for r in rows}
    amb_people = sorted({r["person_name"] for r in rows if r["match_status"] == "REVIEW_REQUIRED"})
    unmatched = sorted({r["person_name"] for r in rows if r["match_status"] not in {"matched", "REVIEW_REQUIRED"}})
    deal_ids = {r["bitrix_deal_id"] for r in rows if r["bitrix_deal_id"]}

    with SessionLocal() as db:
        counts = db.execute(
            text(
                """
                select
                  (select count(*) from crm_agreements) agreements,
                  (select count(distinct contact_id) from crm_agreements) contacts,
                  (select count(*) from crm_contacts) all_contacts
                """
            )
        ).one()
        dup_contacts = db.execute(
            text(
                """
                select count(*) from (
                  select contact_id, project_group, coalesce(unit_number,''), count(*) c
                  from crm_agreements
                  group by 1,2,3 having count(*) > 1
                ) x
                """
            )
        ).scalar()
        dup_agreements = db.execute(text("select count(*) from (select id from crm_agreements group by id having count(*)>1) x")).scalar()
        completeness = db.execute(
            text(
                """
                select
                  count(*) filter (where unit_number is not null and btrim(unit_number) <> '') units,
                  count(*) filter (where investment_amount is not null and btrim(investment_amount) <> '') investment,
                  count(*) filter (where agreement_date is not null) dates,
                  count(*) filter (where metadata_json::jsonb ? 'bitrix_reconciliation') recon
                from crm_agreements
                """
            )
        ).one()
        groups = db.execute(
            text("select project_group, count(*) from crm_agreements group by 1 order by 1")
        ).all()
        contact_enrich = db.execute(
            text(
                """
                select count(*) from crm_contacts
                where id in (select distinct contact_id from crm_agreements)
                  and metadata_json::jsonb ? 'bitrix_reconciliation'
                """
            )
        ).scalar()
        samples = db.execute(
            text(
                """
                select c.display_name, a.project_group, a.unit_number, a.investment_amount,
                       a.agreement_date::text,
                       a.metadata_json::jsonb->'bitrix_reconciliation' as recon
                from crm_agreements a
                join crm_contacts c on c.id = a.contact_id
                where c.display_name ilike '%albert%lev%'
                   or c.display_name ilike '%berk%cimen%'
                   or c.display_name ilike '%berk%çimen%'
                   or a.project_group = 'reit'
                order by c.display_name, a.project_group, a.unit_number
                """
            )
        ).mappings().all()
        uniloft = db.execute(
            text(
                """
                select c.display_name, a.unit_number, a.investment_amount, a.agreement_date::text
                from crm_agreements a join crm_contacts c on c.id=a.contact_id
                where a.project_group='uniloft'
                order by c.display_name limit 8
                """
            )
        ).mappings().all()
        hpl = db.execute(
            text(
                """
                select c.display_name, a.unit_number, a.investment_amount, a.agreement_date::text
                from crm_agreements a join crm_contacts c on c.id=a.contact_id
                where a.project_group='1812_h_pl'
                order by c.display_name limit 8
                """
            )
        ).mappings().all()
        albert_meta = db.execute(
            text(
                """
                select c.display_name, c.primary_phone, c.primary_email, c.organization_name, c.job_title,
                       a.unit_number, a.investment_amount, a.agreement_date::text,
                       a.metadata_json::jsonb->'bitrix_reconciliation' as recon
                from crm_agreements a
                join crm_contacts c on c.id=a.contact_id
                where c.id = 'c20db712-3636-4f4a-81d2-4255b855cd0e'
                """
            )
        ).mappings().all()
        moved = db.execute(
            text(
                """
                select count(*) from crm_agreements
                where contact_id is null
                """
            )
        ).scalar()

    out = {
        "csv_status": dict(status),
        "add_fields": dict(fields_add),
        "payment_roles_with_values": dict(payment_roles),
        "conflicts": [
            {
                "person": r["person_name"],
                "field": r["field"],
                "investhome": r["investhome_value"],
                "bitrix": r["bitrix_value"],
                "bitrix_field": r["bitrix_field_label"],
                "bitrix_field_id": r["bitrix_field_id"],
                "deal": r["bitrix_deal_title"],
            }
            for r in conflicts
        ],
        "match_status_rows": dict(match),
        "people_in_csv": len(people),
        "ambiguous_people": amb_people,
        "unmatched_in_csv": unmatched,
        "distinct_deal_ids_in_csv": len(deal_ids),
        "db": {
            "agreements": counts[0],
            "agreement_contacts": counts[1],
            "all_contacts": counts[2],
            "dup_agreement_unit_pairs": dup_contacts,
            "dup_agreement_ids": dup_agreements,
            "null_contact_agreements": moved,
            "units": completeness[0],
            "investment": completeness[1],
            "dates": completeness[2],
            "agreements_with_recon": completeness[3],
            "contacts_with_recon": contact_enrich,
            "groups": {g[0]: g[1] for g in groups},
        },
        "backup_exists": BACKUP.exists(),
        "backup_bytes": BACKUP.stat().st_size if BACKUP.exists() else 0,
        "samples": [dict(r) for r in samples],
        "uniloft_sample": [dict(r) for r in uniloft],
        "hpl_sample": [dict(r) for r in hpl],
        "albert": [dict(r) for r in albert_meta],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
