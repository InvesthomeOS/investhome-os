"""Prepare The Campus on the existing 3220 project.

Dry-run unless --apply is passed. One transaction: any failed check rolls
the whole change back. Does not import 3224 units and does not update the
demo Campus project.
"""

from __future__ import annotations

import argparse
import sys

from investhome_api.db.session import SessionLocal
from investhome_api.services.inventory.campus_phase_migration import (
    CampusMigrationReport,
    migrate_campus_phases,
)


def run(apply: bool) -> CampusMigrationReport:
    db = SessionLocal()
    try:
        report = migrate_campus_phases(db)
        if apply:
            db.commit()
        else:
            db.rollback()
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Link 3220 units to Campus phase 1.")
    parser.add_argument("--apply", action="store_true", help="Commit. Without this flag the transaction rolls back.")
    args = parser.parse_args(argv)
    report = run(apply=args.apply)
    print("DURUM", "APPLY" if args.apply else "DRY_RUN")
    print("PROJE", report.project_id, report.project_name, report.project_code)
    print("FAZ1", report.phase_1_id, "unite", report.units_on_phase_1, "yeni_bag", report.units_linked)
    print("FAZ2", report.phase_2_id, "unite", report.units_on_phase_2)
    print("BINA", report.building_3220_id, report.building_3224_id, "yeni_bina", report.buildings_created)
    print("FAZ_YENI", report.phases_created)
    print("USES_PHASES", str(report.uses_phases).lower())
    print("TOTAL_UNITS", report.total_units)
    print("DEMO", "PRJ-CAMP-004 degismedi")
    return 0


if __name__ == "__main__":
    sys.exit(main())
