"""CLI: investhome-migrate — inventory | templates | dry-run | validate | reconcile | duplicates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from investhome_api.migration.mapping_registry import (
    entities_as_dicts,
    mappings_as_dicts,
    mappings_by_entity,
)
from investhome_api.migration.validators import run_dry_run, write_template_csvs


def _repo_root() -> Path:
    # .../apps/api/src/investhome_api/migration/cli.py → repo root = parents[5]
    return Path(__file__).resolve().parents[5]


def _default_artifacts() -> Path:
    return _repo_root() / "artifacts" / "g12-migration"


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    print(f"Wrote {path}")


def cmd_inventory(args: argparse.Namespace) -> int:
    from investhome_api.migration.inventory import build_inventory_document, scan_filesystem_sources

    root = _repo_root()
    fs_scan = scan_filesystem_sources(
        [
            root / "data",
            root / "docs",
            root / "artifacts",
            Path(args.sources) if args.sources else root / "data" / "migration-sources",
        ]
    )
    db_snapshot = None
    if args.with_db:
        from investhome_api.db.session import SessionLocal
        from investhome_api.migration.inventory import collect_db_snapshot

        with SessionLocal() as db:
            db_snapshot = collect_db_snapshot(db)

    doc = build_inventory_document(fs_scan=fs_scan, db_snapshot=db_snapshot)
    out = Path(args.output) if args.output else _default_artifacts() / "01-data-inventory.json"
    _write_json(out, doc)
    print(doc["verdict"])
    return 0


def cmd_templates(args: argparse.Namespace) -> int:
    out_dir = Path(args.output) if args.output else _default_artifacts() / "templates"
    written = write_template_csvs(out_dir)
    mapping_json = _default_artifacts() / "03-field-mapping.json"
    _write_json(
        mapping_json,
        {
            "entities": entities_as_dicts(),
            "mappings": mappings_as_dicts(),
            "by_entity": mappings_by_entity(),
        },
    )
    print(f"Wrote {len(written)} CSV templates to {out_dir}")
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    source_dir = Path(args.sources) if args.sources else None
    report = run_dry_run(source_dir)
    out = Path(args.output) if args.output else _default_artifacts() / "dry-run" / "import-dry-run.json"
    _write_json(out, report.to_dict())
    if report.real_sources_present and report.to_dict()["totals"]["rejected"] == 0:
        print("Dry-run: sources validated (no DB writes).")
        return 0
    if not report.real_sources_present:
        print("Dry-run: NO real sources — templates/tooling only.")
        return 0
    print("Dry-run: REJECTS present — see report.")
    return 1


def cmd_reconcile(args: argparse.Namespace) -> int:
    from investhome_api.db.session import SessionLocal
    from investhome_api.migration.reconcile import reconcile_demo_integrity

    with SessionLocal() as db:
        report = reconcile_demo_integrity(db)
    out = Path(args.output) if args.output else _default_artifacts() / "dry-run" / "reconcile.json"
    _write_json(out, report.to_dict())
    fails = report.to_dict()["summary"]["fail"]
    if fails:
        print(f"Reconcile: {fails} FAIL checks")
        return 1
    print(
        "Reconcile: integrity checks done. Bank/source recon remains SKIP without real extracts."
    )
    return 0


def cmd_duplicates(args: argparse.Namespace) -> int:
    from investhome_api.db.session import SessionLocal
    from investhome_api.migration.duplicates import collect_duplicate_report

    with SessionLocal() as db:
        report = collect_duplicate_report(db)
    out = Path(args.output) if args.output else _default_artifacts() / "dry-run" / "duplicates.json"
    _write_json(out, report)
    print(
        f"Duplicates: {report['counts']['total_groups']} groups "
        f"(suggest_merge={report['counts']['suggest_merge']}, "
        f"never_auto_merge={report['counts']['never_auto_merge']})"
    )
    return 0


def cmd_export_mapping_md(args: argparse.Namespace) -> int:
    by_entity = mappings_by_entity()
    lines = [
        "# G12 Field Mapping",
        "",
        "Machine-readable twin: `03-field-mapping.json`.",
        "",
        "Columns: Source → Destination → Transformation → Validation → Required → Default → Relationship → Rejected if",
        "",
    ]
    for entity, rows in by_entity.items():
        lines.append(f"## `{entity}`")
        lines.append("")
        lines.append(
            "| Source | Destination | Transformation | Validation | Required | Default | Relationship | Rejected if |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in rows:
            lines.append(
                "| {source_field} | `{destination_field}` | {transformation} | {validation} | "
                "{required} | {default} | {relationship} | {rejected_if} |".format(
                    source_field=r["source_field"],
                    destination_field=r["destination_field"],
                    transformation=r["transformation"],
                    validation=r["validation"],
                    required="yes" if r["required"] else "no",
                    default=r["default"] if r["default"] is not None else "—",
                    relationship=r["relationship"] or "—",
                    rejected_if=r["rejected_if"],
                )
            )
        lines.append("")
    out = Path(args.output) if args.output else _default_artifacts() / "03-field-mapping.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="investhome-migrate",
        description=(
            "G12 controlled migration tooling — dry-run, validate, reconcile. "
            "Never invents production data. Never auto-merges financials."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_inv = sub.add_parser("inventory", help="Scan sources + optional DB snapshot")
    p_inv.add_argument("--sources", default=None, help="Extra sources directory")
    p_inv.add_argument("--with-db", action="store_true", help="Include connected DB counts")
    p_inv.add_argument("--output", default=None)
    p_inv.set_defaults(func=cmd_inventory)

    p_tpl = sub.add_parser("templates", help="Write empty CSV templates + mapping JSON")
    p_tpl.add_argument("--output", default=None, help="Template directory")
    p_tpl.set_defaults(func=cmd_templates)

    p_map = sub.add_parser("mapping-md", help="Export field mapping markdown")
    p_map.add_argument("--output", default=None)
    p_map.set_defaults(func=cmd_export_mapping_md)

    p_dry = sub.add_parser("dry-run", help="Validate source CSVs without DB writes")
    p_dry.add_argument(
        "--sources",
        default=None,
        help="Directory of entity CSV extracts (e.g. data/migration-sources)",
    )
    p_dry.add_argument("--output", default=None)
    p_dry.set_defaults(func=cmd_dry_run)

    p_rec = sub.add_parser("reconcile", help="Read-only financial/relationship integrity")
    p_rec.add_argument("--output", default=None)
    p_rec.set_defaults(func=cmd_reconcile)

    p_dup = sub.add_parser("duplicates", help="Duplicate suggestions (no auto-merge)")
    p_dup.add_argument("--output", default=None)
    p_dup.set_defaults(func=cmd_duplicates)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


def console_main() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    raise SystemExit(main())
