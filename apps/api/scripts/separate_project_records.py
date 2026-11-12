"""Split Campus or Temple into independent projects. Dry-run unless --apply.

Campus and Temple are separate targets. A Campus run does not read or write Temple.
"""

from __future__ import annotations

import argparse
import sys

from investhome_api.db.session import SessionLocal
from investhome_api.services.inventory.separate_project_records import (
    separate_campus_records,
    separate_temple_records,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Separate Campus or Temple project records.")
    parser.add_argument("--target", choices=("campus", "temple"), required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    db = SessionLocal()
    try:
        report = (
            separate_campus_records(db) if args.target == "campus" else separate_temple_records(db)
        )
        if args.apply:
            db.commit()
        else:
            db.rollback()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("DURUM", "APPLY" if args.apply else "DRY_RUN")
    print("TARGET", args.target)
    if args.target == "campus":
        print("CAMPUS_3220", report.campus_3220_id, "unite", report.units_3220)
        print("CAMPUS_3224", report.campus_3224_id, "unite", report.units_3224, "fiyat", report.prices_3224)
        print("USES_PHASES", str(report.uses_phases).lower())
    else:
        print("TEMPLE", report.temple_id)
        print("TEMPLE_HISTORIC", report.temple_historic_id)
        print("TEMPLE_ADDITION", report.temple_addition_id)
        print(
            "TEMPLE_KALAN",
            "unite",
            report.units_left,
            "anlasma",
            report.agreements_left,
            "finans",
            report.finance_left,
            "fonlama",
            report.funding_left,
            "belge",
            report.documents_left,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
