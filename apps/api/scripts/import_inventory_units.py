"""Dry-run an inventory workbook. Pass --apply only for a database you intend to change.

Default mode reads the workbook and writes nothing. This script does not create
projects, buildings, phases, agreements, or ownership rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from investhome_api.db.session import SessionLocal
from investhome_api.services.inventory.excel_import import run_inventory_import


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import inventory units from an Excel workbook.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write inventory rows. Omit this flag for a dry run.",
    )
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        report = run_inventory_import(db, str(args.workbook), apply=args.apply)
        if args.apply and not report.blocked:
            db.commit()
        else:
            db.rollback()
    finally:
        db.close()
    print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
    print("DRY_RUN" if report.dry_run else "APPLIED")
    return 2 if report.blocked else 0


if __name__ == "__main__":
    sys.exit(main())
