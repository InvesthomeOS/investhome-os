"""Dry-run or apply Bitrix history import. No contact creation."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from investhome_api.db.session import SessionLocal
from investhome_api.services.crm.bitrix_history_import import (
    ARCHIVE_DEFAULT,
    apply_import,
    pick_actor,
    plan_import,
)


def focus_counts(plans) -> dict:
    payload = {}
    for label, cid in (
        ("kaan_kalyon", "f67fe899-6acd-4490-a727-78f8fd6b5340"),
        ("berk_cimen", "ca204ce5-945e-4e43-ae9b-0a375b93d44c"),
    ):
        subset = [plan for plan in plans if str(plan.contact_id) == cid]
        payload[label] = {
            "new_activities": len(subset),
            "by_type": dict(Counter(plan.activity_type.value for plan in subset)),
            "whatsapp_messages": sum(
                1
                for plan in subset
                if (plan.metadata.get("bitrix_history") or {}).get("kind") == "whatsapp_message"
            ),
        }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", default=str(ARCHIVE_DEFAULT))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--out",
        default="/export/2026-09-final/BITRIX_FINAL_HISTORY_ARCHIVE/reports/BITRIX_HISTORY_IMPORT_DRY_RUN.json",
    )
    args = parser.parse_args()
    archive = Path(args.archive)
    db = SessionLocal()
    try:
        plans, report = plan_import(db, archive)
        report.dry_run = not args.apply
        if args.apply:
            actor = pick_actor(db)
            created = apply_import(db, plans, actor)
            db.commit()
            report.created_by_type = dict(created)
            report.new_activities = sum(created.values())
        payload = report.to_dict()
        payload["planned_sample_keys"] = [plan.import_key for plan in plans[:15]]
        payload["focus"] = focus_counts(plans)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
