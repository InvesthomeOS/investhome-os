"""Revert non-deterministic Berk 304<-305 pairing and junk job_title '.'."""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact

BERK_304 = UUID("4836482a-559a-428d-910f-cf08a09ab544")
CAGLAR = UUID("4ef08204-60bf-490b-b8fb-9b4b4804775e")


def main() -> None:
    with SessionLocal() as db:
        ag = db.get(CrmAgreement, BERK_304)
        before = {
            "unit": ag.unit_number if ag else None,
            "date": str(ag.agreement_date) if ag and ag.agreement_date else None,
            "has_recon": bool(ag and (ag.metadata_json or {}).get("bitrix_reconciliation")),
        }
        if ag:
            ag.agreement_date = None
            meta = dict(ag.metadata_json or {})
            meta.pop("bitrix_reconciliation", None)
            ag.metadata_json = meta
        caglar = db.get(CrmContact, CAGLAR)
        caglar_before = {
            "job_title": caglar.job_title if caglar else None,
            "has_recon": bool(caglar and (caglar.metadata_json or {}).get("bitrix_reconciliation")),
        }
        if caglar and caglar.job_title == ".":
            caglar.job_title = None
            meta = dict(caglar.metadata_json or {})
            recon = dict(meta.get("bitrix_reconciliation") or {})
            if recon:
                meta.pop("bitrix_reconciliation", None)
                caglar.metadata_json = meta
        db.commit()
        counts = db.execute(
            text("select (select count(*) from crm_agreements) a, (select count(distinct contact_id) from crm_agreements) c")
        ).one()
        ag2 = db.get(CrmAgreement, BERK_304)
        caglar2 = db.get(CrmContact, CAGLAR)
        print(
            json.dumps(
                {
                    "berk_304_before": before,
                    "berk_304_after": {
                        "unit": ag2.unit_number,
                        "date": str(ag2.agreement_date) if ag2.agreement_date else None,
                        "has_recon": bool((ag2.metadata_json or {}).get("bitrix_reconciliation")),
                    },
                    "caglar_before": caglar_before,
                    "caglar_after": {
                        "job_title": caglar2.job_title,
                        "has_recon": bool((caglar2.metadata_json or {}).get("bitrix_reconciliation")),
                    },
                    "agreements": counts[0],
                    "contacts": counts[1],
                },
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
