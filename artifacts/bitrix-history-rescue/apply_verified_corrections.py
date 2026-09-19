"""Apply only verified agreement unit + Ümit phone corrections. Abort if current values differ."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.identity import normalize_phone

NOW = datetime.now(timezone.utc).isoformat()

UNIT_FIXES = [
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:68",
        "person": "Berk Çimen",
        "expect_unit": "304",
        "new_unit": "305",
        "bitrix_deal_id": "68",
        "bitrix_deal_title": "1812 H PL 305 LLC Berk Cimen",
        "bitrix_field_id": "TITLE",
        "bitrix_field_label": "Name",
        "bitrix_value": "1812 H PL 305 LLC Berk Cimen",
        "excel_field": "Anlaşma Adı / parsed unit",
    },
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:66",
        "person": "Ilgaz Uzunca",
        "expect_unit": "201",
        "new_unit": "307",
        "bitrix_deal_id": "66",
        "bitrix_deal_title": "1812 H PL 307 LLC Ilgaz Uzunca",
        "bitrix_field_id": "TITLE",
        "bitrix_field_label": "Name",
        "bitrix_value": "1812 H PL 307 LLC Ilgaz Uzunca",
        "excel_field": "Anlaşma Adı / parsed unit",
    },
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:52",
        "person": "Ümit Çimen",
        "expect_unit": "301",
        "new_unit": "205",
        "bitrix_deal_id": "52",
        "bitrix_deal_title": "1820 H PL 205 LLC Ayse-Umit Cimen",
        "bitrix_field_id": "TITLE",
        "bitrix_field_label": "Name",
        "bitrix_value": "1820 H PL 205 LLC Ayse-Umit Cimen",
        "excel_field": "Anlaşma Adı / parsed unit",
    },
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:48",
        "person": "Ayşe Çimen",
        "expect_unit": "204",
        "new_unit": "106",
        "bitrix_deal_id": "48",
        "bitrix_deal_title": "1820 H PL 106 LLC Ayse-Umit Cimen",
        "bitrix_field_id": "TITLE",
        "bitrix_field_label": "Name",
        "bitrix_value": "1820 H PL 106 LLC Ayse-Umit Cimen",
        "excel_field": "Anlaşma Adı / parsed unit",
    },
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:76",
        "person": "Ayşe Çimen",
        "expect_unit": "204",
        "new_unit": "405",
        "bitrix_deal_id": "76",
        "bitrix_deal_title": "1812 H PL 405 LLC Ayse-Umit Cimen",
        "bitrix_field_id": "TITLE",
        "bitrix_field_label": "Name",
        "bitrix_value": "1812 H PL 405 LLC Ayse-Umit Cimen",
        "excel_field": "Anlaşma Adı / parsed unit",
    },
    {
        "source_external_id": "Anlaşmalar 1812 H Pl.xls:58",
        "person": "Semih Sönmez",
        "expect_unit": "208",
        "new_unit": "302",
        "bitrix_deal_id": "58",
        "bitrix_deal_title": "1812 H PL 302 LLC Semih Sonmez",
        "bitrix_field_id": "UF_CRM_1690887880212",
        "bitrix_field_label": "Daire No",
        "bitrix_value": "302",
        "excel_field": "Daire No",
    },
]

KEEP = [
    ("Anlaşmalar 1812 H Pl.xls:54", "105"),
    ("Anlaşmalar 1812 H Pl.xls:56", "207"),
    ("Anlaşmalar 1812 H Pl.xls:116", "B08"),
    ("Anlaşmalar 1307 k st.xls:126", "102"),
    ("Anlaşmalar 2319 ontario.xls:198", "403"),
    ("Anlaşmalar Uniloft.xls:656", "209"),
    ("Anlaşmalar Uniloft.xls:720", "403"),
    ("Anlaşmalar Reıt.xls:434", None),  # unit blank; investment 50000
]

UMIT_ID = UUID("9011557a-b96a-4d66-8d6a-6baeb481d017")
BERK_ID = UUID("ca204ce5-945e-4e43-ae9b-0a375b93d44c")
SEMIH_SRC = "Anlaşmalar 1812 H Pl.xls:58"


def provenance(fix: dict, previous: str) -> dict:
    return {
        "source": "bitrix+excel",
        "event": "verified_unit_correction",
        "previous_value": previous,
        "new_value": fix["new_unit"],
        "bitrix_entity_type": "deal",
        "bitrix_entity_id": fix["bitrix_deal_id"],
        "bitrix_deal_id": fix["bitrix_deal_id"],
        "bitrix_deal_title": fix["bitrix_deal_title"],
        "bitrix_field_id": fix["bitrix_field_id"],
        "bitrix_field_label": fix["bitrix_field_label"],
        "bitrix_value": fix["bitrix_value"],
        "excel_source_external_id": fix["source_external_id"],
        "excel_field": fix["excel_field"],
        "retrieved_at": NOW,
        "applied_at": NOW,
    }


def append_activity(db, contact: CrmContact, title: str, description: str, metadata: dict) -> None:
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.SYSTEM_EVENT,
            activity_category=CrmActivityCategory.SYSTEM,
            title=title,
            description=description,
            status=CrmActivityStatus.COMPLETED,
            priority=CrmActivityPriority.MEDIUM,
            visibility=CrmActivityVisibility.ORGANIZATION,
            owner_id=contact.owner_user_id,
            metadata_json=metadata,
            completed_at=datetime.now(timezone.utc),
        )
    )


def main() -> None:
    errors: list[str] = []
    applied: list[dict] = []
    with SessionLocal() as db:
        pre = db.execute(
            text(
                """
                select
                  (select count(*) from crm_agreements) agreements,
                  (select count(distinct contact_id) from crm_agreements) contacts
                """
            )
        ).one()
        ownership_before = {
            str(r.id): str(r.contact_id)
            for r in db.execute(text("select id, contact_id from crm_agreements")).all()
        }

        for fix in UNIT_FIXES:
            ag = db.execute(
                text(
                    """
                    select a.id, a.unit_number, a.contact_id, a.investment_amount,
                           a.source_external_id, a.metadata_json, c.display_name
                    from crm_agreements a
                    join crm_contacts c on c.id = a.contact_id
                    where a.source_external_id = :src
                    """
                ),
                {"src": fix["source_external_id"]},
            ).mappings().one_or_none()
            if ag is None:
                errors.append(f"missing agreement {fix['source_external_id']}")
                continue
            if ag["display_name"] != fix["person"]:
                errors.append(f"ownership name mismatch {fix['source_external_id']}: {ag['display_name']} != {fix['person']}")
                continue
            if (ag["unit_number"] or "") != fix["expect_unit"]:
                errors.append(
                    f"unit guard failed {fix['source_external_id']}: have {ag['unit_number']!r} expected {fix['expect_unit']!r}"
                )
                continue
            if ag["investment_amount"] not in (None, ""):
                # none of these six currently hold investment; refuse surprise overwrites
                errors.append(f"unexpected investment_amount on {fix['source_external_id']}")
                continue

            row = db.get(CrmAgreement, ag["id"])
            contact = db.get(CrmContact, ag["contact_id"])
            previous = row.unit_number
            row.unit_number = fix["new_unit"]
            meta = dict(row.metadata_json or {})
            audit = list(meta.get("verified_corrections") or [])
            prov = provenance(fix, previous)
            audit.append(prov)
            meta["verified_corrections"] = audit
            fields = dict(meta.get("agreement_fields") or {})
            if fields.get("unit_number") in {previous, None, ""}:
                fields["unit_number"] = fix["new_unit"]
                meta["agreement_fields"] = fields
            if meta.get("unit_number") == previous:
                meta["unit_number"] = fix["new_unit"]
            if fix["source_external_id"] == SEMIH_SRC:
                meta["amount_review"] = {
                    "status": "REVIEW_REQUIRED",
                    "excel_gelir": "325500",
                    "bitrix_opportunity": "325000",
                    "bitrix_deal_id": "58",
                    "bitrix_field_id": "OPPORTUNITY",
                    "bitrix_field_label": "Total",
                    "action": "kept_unchanged",
                    "retrieved_at": NOW,
                }
            row.metadata_json = meta
            flag_modified(row, "metadata_json")
            append_activity(
                db,
                contact,
                title="Anlaşma birimi düzeltildi",
                description=f"Birim: {previous} → {fix['new_unit']}\nKaynak: {fix['source_external_id']}\nBitrix deal #{fix['bitrix_deal_id']} {fix['bitrix_deal_title']}",
                metadata=prov,
            )
            applied.append(
                {
                    "person": fix["person"],
                    "agreement_id": str(row.id),
                    "source_external_id": fix["source_external_id"],
                    "previous_unit": previous,
                    "new_unit": row.unit_number,
                    "contact_id": str(contact.id),
                    "bitrix_deal_id": fix["bitrix_deal_id"],
                }
            )

        umit = db.get(CrmContact, UMIT_ID)
        berk = db.get(CrmContact, BERK_ID)
        phone_result = None
        if umit is None or berk is None:
            errors.append("Ümit or Berk contact missing")
        else:
            berk_phone_before = berk.primary_phone
            old = umit.primary_phone
            if old != "+905304150866":
                errors.append(f"Ümit phone guard failed: have {old!r}")
            else:
                new_phone = normalize_phone("+905357252349") or "+905357252349"
                umit.primary_phone = new_phone
                secondary = [p for p in (umit.secondary_phones or []) if p not in {"+905304150866", "905304150866"}]
                umit.secondary_phones = secondary or None
                meta = dict(umit.metadata_json or {})
                audit = list(meta.get("verified_corrections") or [])
                phone_prov = {
                    "source": "bitrix+excel",
                    "event": "verified_phone_correction",
                    "previous_value": old,
                    "new_value": new_phone,
                    "bitrix_entity_type": "contact",
                    "bitrix_entity_id": "178",
                    "bitrix_deal_id": None,
                    "bitrix_field_id": "PHONE",
                    "bitrix_field_label": "Phone",
                    "bitrix_value": "+905357252349",
                    "excel_source_external_id": "Anlaşmalar 1812 H Pl.xls:52",
                    "excel_field": "notes/phone 05357252349",
                    "retrieved_at": NOW,
                    "applied_at": NOW,
                }
                audit.append(phone_prov)
                meta["verified_corrections"] = audit
                umit.metadata_json = meta
                flag_modified(umit, "metadata_json")
                append_activity(
                    db,
                    umit,
                    title="Telefon düzeltildi",
                    description=f"Telefon: {old} → {new_phone}\nBitrix contact 178; Excel Anlaşmalar 1812 H Pl.xls:52\nBerk Çimen telefonu değiştirilmedi.",
                    metadata=phone_prov,
                )
                if berk.primary_phone != berk_phone_before:
                    errors.append("Berk phone changed unexpectedly")
                phone_result = {
                    "umit_previous": old,
                    "umit_new": umit.primary_phone,
                    "berk_phone_unchanged": berk.primary_phone,
                }

        if errors:
            db.rollback()
            print(json.dumps({"ok": False, "errors": errors}, ensure_ascii=False, indent=2))
            return

        db.commit()

        # re-load after commit
        post = db.execute(
            text(
                """
                select
                  (select count(*) from crm_agreements) agreements,
                  (select count(distinct contact_id) from crm_agreements) contacts,
                  (select count(*) from crm_contacts) all_contacts
                """
            )
        ).one()
        ownership_after = {
            str(r.id): str(r.contact_id)
            for r in db.execute(text("select id, contact_id from crm_agreements")).all()
        }
        moved = [aid for aid, cid in ownership_after.items() if ownership_before.get(aid) != cid]
        dup_pairs = db.execute(
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

        keep_state = []
        for src, unit in KEEP:
            row = db.execute(
                text(
                    """
                    select c.display_name, a.project_group, a.unit_number, a.investment_amount
                    from crm_agreements a join crm_contacts c on c.id=a.contact_id
                    where a.source_external_id = :src
                    """
                ),
                {"src": src},
            ).mappings().one()
            keep_state.append(dict(row) | {"source_external_id": src, "expected_unit": unit})

        corrected = []
        for fix in UNIT_FIXES:
            row = db.execute(
                text(
                    """
                    select c.display_name, a.unit_number, a.contact_id::text, a.id::text
                    from crm_agreements a join crm_contacts c on c.id=a.contact_id
                    where a.source_external_id = :src
                    """
                ),
                {"src": fix["source_external_id"]},
            ).mappings().one()
            corrected.append(dict(row) | {"source_external_id": fix["source_external_id"], "expected": fix["new_unit"]})

        umit = db.get(CrmContact, UMIT_ID)
        berk = db.get(CrmContact, BERK_ID)
        eyyub = db.execute(
            text("select investment_amount from crm_agreements where source_external_id = 'Anlaşmalar Reıt.xls:434'")
        ).scalar()
        caglar_count = db.execute(
            text("select count(*) from crm_agreements where contact_id = '4ef08204-60bf-490b-b8fb-9b4b4804775e'")
        ).scalar()
        nedim_contacts = db.execute(
            text("select count(*) from crm_contacts where display_name = 'Nedim Kondu'")
        ).scalar()

        out = {
            "ok": True,
            "backup_path": "data/Bitrix_Export/2026-09-final/BITRIX_AGREEMENT_RECONCILIATION/backups/investhome-pre-verified-agreement-corrections-20260917.dump",
            "pre_counts": {"agreements": pre[0], "contacts": pre[1]},
            "corrections_applied": applied,
            "umit_phone": phone_result,
            "keep_state": keep_state,
            "corrected_units": corrected,
            "final_agreements": post[0],
            "final_agreement_contacts": post[1],
            "all_contacts": post[2],
            "ownership_moved": moved,
            "dup_agreement_unit_pairs": dup_pairs,
            "eyyub_investment": eyyub,
            "caglar_agreement_count": caglar_count,
            "nedim_contact_count": nedim_contacts,
            "berk_phone": berk.primary_phone if berk else None,
            "umit_phone_now": umit.primary_phone if umit else None,
            "errors": errors,
        }
        print(json.dumps(out, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
