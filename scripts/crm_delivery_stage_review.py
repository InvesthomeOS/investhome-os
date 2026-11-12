"""Dry-run review of agreements that should move to Ev Teslim Süreci.

Default is report only. Pass --apply to write the CRM stage label.
Historical Bitrix metadata, including bitrix_live, is left unchanged.

Targets: 1812, 1313, 2319, 1307, Uniloft.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api" / "src"
if str(API) not in sys.path:
    sys.path.insert(0, str(API))

from sqlalchemy import select  # noqa: E402

from investhome_api.db.session import SessionLocal  # noqa: E402
from investhome_api.models.crm_agreement import CrmAgreement  # noqa: E402
from investhome_api.models.crm_contact import CrmContact  # noqa: E402
from investhome_api.services.crm.agreement_service import (  # noqa: E402
    _display_stage,
    _meta,
    _project_label,
    normalize_agreement_stage,
    set_agreement_stage,
)

TARGET_GROUPS = {
    "1812_h_pl",
    "1313_penn",
    "2319_ontario",
    "1307_k_st",
    "uniloft",
}
NEEDLES = ("1812", "1313", "2319", "1307", "uniloft", "uni loft", "uni-loft")
DELIVERY_STAGE = "Ev Teslim Süreci"


def _blob(row: CrmAgreement) -> str:
    meta = _meta(row)
    parts = [
        row.project_group or "",
        str(meta.get("project_label") or ""),
        str(meta.get("original_project_label") or ""),
        str(meta.get("llc_name") or ""),
        str(meta.get("bitrix_deal_stage_label") or ""),
        str(meta.get("bitrix_deal_stage") or ""),
    ]
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    parts.append(str(live.get("stage_label") or ""))
    parts.append(str(live.get("stage_id") or ""))
    parts.append(str(live.get("project") or ""))
    return " ".join(parts).casefold()


def matches(row: CrmAgreement) -> bool:
    if row.project_group in TARGET_GROUPS:
        return True
    blob = _blob(row)
    return any(needle in blob for needle in NEEDLES)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write Ev Teslim Süreci. Default is dry-run.")
    args = parser.parse_args()
    with SessionLocal() as db:
        rows = list(db.scalars(select(CrmAgreement)).all())
        hits = [row for row in rows if matches(row)]
        contact_ids = {row.contact_id for row in hits}
        contacts = {
            contact.id: contact
            for contact in db.scalars(select(CrmContact).where(CrmContact.id.in_(contact_ids))).all()
        } if contact_ids else {}
        print(f"matches={len(hits)} mode={'apply' if args.apply else 'dry-run'}")
        print("agreement_id\tcontact\tproject_id\tproject\tunit\tcrm_stage\tlegacy_stage")
        for row in hits:
            meta = _meta(row)
            live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
            label = _display_stage(meta, live) or ""
            stage = normalize_agreement_stage(label, str(meta.get("stage_id") or live.get("stage_id") or ""))
            legacy = str(
                live.get("stage_label")
                or meta.get("bitrix_deal_stage_label")
                or live.get("stage_id")
                or meta.get("bitrix_deal_stage")
                or ""
            )
            contact = contacts.get(row.contact_id)
            print(
                "\t".join(
                    [
                        str(row.id),
                        contact.display_name if contact else "",
                        str(row.project_id or ""),
                        _project_label(row.project_group, meta),
                        row.unit_number or "",
                        stage,
                        legacy,
                    ]
                )
            )
            if args.apply and stage != DELIVERY_STAGE:
                set_agreement_stage(row, DELIVERY_STAGE)
        if args.apply:
            db.commit()
            print("applied=yes")
        else:
            db.rollback()
            print("applied=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
