"""Relink Nedim Ontario agreement onto the canonical Uniloft contact.

Does not create a new contact. Does not copy duplicate activities/documents.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.services.crm.nedim_project_card import NEDIM_CANONICAL_ID, NEDIM_ALIAS_IDS

ONTARIO_AGREEMENT = UUID("d30d258a-3b89-458a-bfa0-a2de4f9f0ba2")
UNILOFT_403 = UUID("444f6517-595a-4067-9c0c-3521708d2223")
UNILOFT_209 = UUID("bdfd5ca1-e491-4896-b5d4-4b401ef428ac")

TUTAR = {
    ONTARIO_AGREEMENT: ("800250.00", "USD", "198"),
    UNILOFT_403: ("470000.00", "USD", "720"),
    UNILOFT_209: ("330757.00", "USD", "656"),
}


def _apply_tutar(agreement: CrmAgreement, amount: str, currency: str, deal_id: str) -> None:
    meta = dict(agreement.metadata_json or {})
    if not meta.get("tutar_ve_para_birimi_amount"):
        meta["tutar_ve_para_birimi_amount"] = amount
        meta["tutar_ve_para_birimi_currency"] = currency
        meta["tutar_ve_para_birimi_label"] = "Tutar ve para birimi"
        meta["tutar_ve_para_birimi_field_id"] = "OPPORTUNITY+CURRENCY_ID"
        meta["tutar_ve_para_birimi_source"] = "bitrix_live"
    meta["bitrix_deal_id"] = deal_id
    agreement.metadata_json = meta
    flag_modified(agreement, "metadata_json")


def main() -> int:
    db = SessionLocal()
    try:
        survivor = db.get(CrmContact, NEDIM_CANONICAL_ID)
        if survivor is None:
            raise SystemExit("canonical Nedim missing")
        ontario = db.get(CrmAgreement, ONTARIO_AGREEMENT)
        if ontario is None:
            raise SystemExit("Ontario agreement missing")
        ontario.contact_id = NEDIM_CANONICAL_ID
        for agreement_id, payload in TUTAR.items():
            agreement = db.get(CrmAgreement, agreement_id)
            if agreement:
                _apply_tutar(agreement, *payload)
        for alias_id in NEDIM_ALIAS_IDS:
            alias = db.get(CrmContact, alias_id)
            if alias is None or alias.id == NEDIM_CANONICAL_ID:
                continue
            meta = dict(alias.metadata_json or {})
            meta["merged_into"] = str(NEDIM_CANONICAL_ID)
            meta["nedim_project_card_pilot"] = True
            alias.metadata_json = meta
            flag_modified(alias, "metadata_json")
            alias.status = CrmContactStatus.ARCHIVED
            alias.archived_at = datetime.now(UTC)
        live = dict((survivor.metadata_json or {}).get("bitrix_live") or {})
        ext = list(((survivor.metadata_json or {}).get("bitrix_import") or {}).get("external_ids") or [])
        if "Anlaşmalar 2319 ontario.xls:198" not in ext:
            bitrix_imp = dict((survivor.metadata_json or {}).get("bitrix_import") or {})
            ext.append("Anlaşmalar 2319 ontario.xls:198")
            files = list(bitrix_imp.get("source_files") or [])
            if "Anlaşmalar 2319 ontario.xls" not in files:
                files.append("Anlaşmalar 2319 ontario.xls")
            bitrix_imp["external_ids"] = ext
            bitrix_imp["source_files"] = files
            full = dict(survivor.metadata_json or {})
            full["bitrix_import"] = bitrix_imp
            full["nedim_project_card_pilot"] = True
            survivor.metadata_json = full
            flag_modified(survivor, "metadata_json")
        db.commit()
        print(
            json.dumps(
                {
                    "canonical": str(NEDIM_CANONICAL_ID),
                    "ontario_agreement_contact": str(ontario.contact_id),
                    "archived_alias": [str(x) for x in NEDIM_ALIAS_IDS],
                }
            )
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
