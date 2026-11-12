"""Move the current REIT agreements to Ev Teslim Süreci.

Dry-run unless --apply is passed. Matches the authoritative member list to
existing contacts and their one non-cancelled REIT agreement. Does not create
contacts, agreements, or inventory, and does not rewrite Bitrix metadata.
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.agreement_service import _display_stage, _meta, set_agreement_stage
from investhome_api.services.crm.bitrix_project_aliases import fold_alias
from investhome_api.services.crm.unit_change import is_historical_unit_change, is_relationship_detached

TARGET_STAGE = "Ev Teslim Süreci"
REIT_GROUP = "reit"
AUTHORITATIVE_MEMBERS = (
    "Göksel Canlılar",
    "Eyyub Canlılar",
    "Nuri Oraj Özgövde",
    "Ebru Kaya",
    "Emin KAYA",
    "Selim Levi Beceren",
    "Lale Şenyol",
    "Birol Toykan",
    "Alper Levi",
    "Hande Erin Suner",
)
ACTIONS = (
    "READY_FOR_STAGE",
    "ALREADY_AT_TARGET",
    "PERSON_NOT_FOUND",
    "AMBIGUOUS_PERSON",
    "AGREEMENT_NOT_UNIQUE",
    "CANCELLED",
    "SKIPPED",
)


def _shown_stage(row: CrmAgreement) -> str:
    meta = _meta(row)
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    return _display_stage(meta, live) or "—"


def _current_reit_agreements(rows: list[CrmAgreement], contact_id: UUID) -> list[CrmAgreement]:
    return [
        row
        for row in rows
        if row.contact_id == contact_id
        and row.project_group == REIT_GROUP
        and row.status != CrmAgreementStatus.CANCELLED
        and not is_historical_unit_change(row)
        and not is_relationship_detached(row)
    ]


def plan_reit_delivery(db: Session) -> list[dict[str, object]]:
    contacts = list(db.scalars(select(CrmContact)).all())
    agreements = list(
        db.scalars(select(CrmAgreement).where(CrmAgreement.project_group == REIT_GROUP)).all()
    )
    by_name: dict[str, list[CrmContact]] = defaultdict(list)
    for contact in contacts:
        key = fold_alias(contact.display_name or "")
        if key:
            by_name[key].append(contact)
    planned: list[dict[str, object]] = []
    for name in AUTHORITATIVE_MEMBERS:
        key = fold_alias(name)
        named = by_name.get(key, [])
        current: list[CrmAgreement] = []
        for contact in named:
            current.extend(_current_reit_agreements(agreements, contact.id))
        cancelled = [
            row
            for contact in named
            for row in agreements
            if row.contact_id == contact.id and row.status == CrmAgreementStatus.CANCELLED
        ]
        if len(named) == 0:
            action = "PERSON_NOT_FOUND"
            row = None
        elif len(current) == 1:
            row = current[0]
            action = "ALREADY_AT_TARGET" if _shown_stage(row) == TARGET_STAGE else "READY_FOR_STAGE"
        elif len(current) > 1:
            action = "AGREEMENT_NOT_UNIQUE"
            row = None
        elif cancelled:
            action = "CANCELLED"
            row = None
        elif len(named) > 1:
            action = "AMBIGUOUS_PERSON"
            row = None
        else:
            action = "SKIPPED"
            row = None
        planned.append(
            {
                "person": name,
                "action": action,
                "agreement_id": None if row is None else str(row.id),
                "agreement": row,
                "current_stage": None if row is None else _shown_stage(row),
                "target_stage": TARGET_STAGE,
            }
        )
    return planned


def apply_reit_delivery(db: Session, planned: list[dict[str, object]]) -> int:
    written = 0
    for item in planned:
        if item["action"] != "READY_FOR_STAGE":
            continue
        row = item["agreement"]
        if not isinstance(row, CrmAgreement):
            continue
        before = dict(_meta(row))
        set_agreement_stage(row, TARGET_STAGE)
        after = _meta(row)
        for key, value in before.items():
            if key == "stage_label":
                continue
            if after.get(key) != value:
                raise RuntimeError("reit stage move rewrote historical metadata")
        written += 1
    return written


def run(apply: bool) -> list[dict[str, object]]:
    db = SessionLocal()
    try:
        planned = plan_reit_delivery(db)
        if apply:
            apply_reit_delivery(db, planned)
            db.commit()
        else:
            db.rollback()
        return planned
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write. Without this flag the run stays a dry run.")
    args = parser.parse_args(argv)
    planned = run(apply=args.apply)
    counts: dict[str, int] = defaultdict(int)
    for item in planned:
        counts[str(item["action"])] += 1
        print(
            f"{item['action']}\t{item['person']}\t{item['agreement_id'] or '—'}"
            f"\t{item['current_stage'] or '—'}\t{item['target_stage']}"
        )
    print("TOTAL", len(planned))
    for key in ACTIONS:
        print(f"{key} {counts.get(key, 0)}")
    print("APPLY" if args.apply else "DRY_RUN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
