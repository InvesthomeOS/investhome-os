"""Import manually recovered Bitrix files into existing CRM Documents.

Default is dry-run. Does not modify Bitrix. Ownership comes only from the
42-row package catalog (canonical CRM UUID + Bitrix file ID). Never assigns
a file to a contact by person name.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.user_auth import User

from link_agreement_documents import (  # type: ignore
    EXISTING_MANIFEST,
    HTML_HEAD,
    MANIFEST_FIELDS,
    OUT,
    import_document,
    mime_of,
    safe_filename,
    unique_dest,
    utc_now,
)

PACKAGE = Path("/export/2026-09-final/BITRIX_MANUAL_RECOVERY")
CATALOG_JSON = PACKAGE / "expected_42.json"
CATALOG_CSV = PACKAGE / "reports" / "BITRIX_MANUAL_RECOVERY_42.csv"
FILE_ID_RE = re.compile(r"(?:__)?bitrix[-_](\d+)\b", re.I)
SKIP_NAMES = {"save_as.txt", "expected_42.json"}


def load_catalog() -> list[dict]:
    if CATALOG_JSON.exists():
        rows = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
        if isinstance(rows, list):
            return [r for r in rows if isinstance(r, dict)]
    with CATALOG_CSV.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def is_binary(data: bytes) -> bool:
    if not data or len(data) < 8:
        return False
    if HTML_HEAD.search(data[:200]):
        return False
    return True


def candidate_files(folder: Path) -> list[Path]:
    files = []
    for path in folder.iterdir():
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.name.lower() in SKIP_NAMES:
            continue
        if path.suffix.lower() in {".txt", ".json", ".html", ".csv", ".md"}:
            continue
        files.append(path)
    return files


def match_file(path: Path, folder_rows: list[dict], all_rows: list[dict]) -> tuple[dict | None, str]:
    name = path.name
    ids = FILE_ID_RE.findall(name)
    if ids:
        file_id = ids[-1]
        hits = [r for r in folder_rows if str(r.get("bitrix_file_id") or "") == file_id]
        catalog_hits = [r for r in all_rows if str(r.get("bitrix_file_id") or "") == file_id]
        owners = {(r.get("canonical_crm_contact_id") or "") for r in catalog_hits}
        folder_owner = {(r.get("canonical_crm_contact_id") or "") for r in folder_rows}
        if len(hits) == 1 and owners <= folder_owner and len(owners) == 1:
            return hits[0], "matched_bitrix_file_id"
        if len(catalog_hits) == 1 and catalog_hits[0] not in folder_rows:
            return None, f"REJECT file_id_belongs_to_another_person file_id={file_id}"
        if len(hits) > 1 or len(owners) > 1:
            return None, f"REJECT ambiguous_file_id={file_id}"
        return None, f"REJECT unknown_bitrix_file_id={file_id}"

    stem = name
    exact = []
    for row in folder_rows:
        original = (row.get("original_filename") or "").strip()
        suggested = (row.get("suggested_save_as") or "").strip()
        if original and original.casefold() == name.casefold():
            exact.append(row)
        elif suggested and suggested.casefold() == name.casefold():
            exact.append(row)
    # unique original filename among this person's catalog rows only
    if not exact:
        orig_hits = [
            r
            for r in folder_rows
            if (r.get("original_filename") or "").strip()
            and Path((r.get("original_filename") or "").strip()).name.casefold() == name.casefold()
        ]
        exact = orig_hits
    if len(exact) == 1:
        original = (exact[0].get("original_filename") or "").strip()
        same_name = [
            r
            for r in all_rows
            if (r.get("original_filename") or "").strip().casefold() == original.casefold()
        ]
        if original and len(same_name) > 1:
            return None, f"REJECT ambiguous_original_filename={name}"
        return exact[0], "matched_original_or_suggested_filename"
    if len(exact) > 1:
        return None, f"REJECT ambiguous_filename={name}"
    return None, f"REJECT unmatched_filename={name}"


def apply_to_manifest(manifest_rows: list[dict], catalog_row: dict, dest: Path, digest: str, doc_id: str, imported: str) -> None:
    cid = catalog_row.get("canonical_crm_contact_id") or ""
    file_id = str(catalog_row.get("bitrix_file_id") or "")
    for row in manifest_rows:
        if (row.get("canonical_crm_contact_id") or "") == cid and str(row.get("bitrix_file_id") or "") == file_id:
            row["downloaded"] = "yes"
            row["local_archive_path"] = str(dest.relative_to(OUT)).replace("\\", "/")
            row["sha256"] = digest
            row["original_filename"] = catalog_row.get("original_filename") or dest.name
            row["file_size"] = str(dest.stat().st_size)
            row["crm_imported"] = imported
            row["crm_document_id"] = doc_id
            row["failure_reason"] = ""
            return


def main() -> None:
    parser = argparse.ArgumentParser(description="Match and import the 42 manually recovered Bitrix files.")
    parser.add_argument("--apply", action="store_true", help="Write files into CRM. Default is dry-run.")
    args = parser.parse_args()
    catalog = load_catalog()
    if len(catalog) != 42:
        print(f"CATALOG_COUNT_UNEXPECTED {len(catalog)}")
        return
    by_folder: dict[str, list[dict]] = defaultdict(list)
    for row in catalog:
        by_folder[row["destination_folder"]].append(row)

    results = []
    matched_ids: set[tuple[str, str]] = set()
    for folder_name, folder_rows in by_folder.items():
        folder = PACKAGE / folder_name
        if not folder.exists():
            results.append({"folder": folder_name, "status": "missing_folder"})
            continue
        for path in candidate_files(folder):
            row, reason = match_file(path, folder_rows, catalog)
            item = {
                "folder": folder_name,
                "local_file": path.name,
                "status": "matched" if row else "rejected",
                "reason": reason,
                "bitrix_file_id": (row or {}).get("bitrix_file_id") or "",
                "canonical_crm_contact_id": (row or {}).get("canonical_crm_contact_id") or "",
                "person_name": (row or {}).get("person_name") or "",
            }
            if not row:
                results.append(item)
                continue
            key = (row["canonical_crm_contact_id"], str(row["bitrix_file_id"]))
            if key in matched_ids:
                item["status"] = "rejected"
                item["reason"] = "REJECT duplicate_match_for_same_file_id"
                results.append(item)
                continue
            matched_ids.add(key)
            content = path.read_bytes()
            if not is_binary(content):
                item["status"] = "rejected"
                item["reason"] = "REJECT empty_or_html"
                results.append(item)
                continue
            item["bytes"] = len(content)
            item["sha256"] = hashlib.sha256(content).hexdigest()
            results.append(item)

    matched = [r for r in results if r["status"] == "matched"]
    rejected = [r for r in results if r["status"] == "rejected"]
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "catalog_rows": len(catalog),
                "matched": len(matched),
                "rejected": len(rejected),
                "unmatched_catalog": [
                    {
                        "person_name": r["person_name"],
                        "bitrix_file_id": r["bitrix_file_id"],
                        "suggested_save_as": r.get("suggested_save_as"),
                    }
                    for r in catalog
                    if (r["canonical_crm_contact_id"], str(r["bitrix_file_id"])) not in matched_ids
                ],
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if not args.apply:
        print("DRY_RUN_NO_CRM_WRITES")
        return

    db = SessionLocal()
    try:
        actor = db.scalars(select(User).limit(1)).first()
        if actor is None:
            print("NO_ACTOR_USER")
            return
        with EXISTING_MANIFEST.open(encoding="utf-8", newline="") as handle:
            manifest_rows = list(csv.DictReader(handle))
        catalog_by_key = {(r["canonical_crm_contact_id"], str(r["bitrix_file_id"])): r for r in catalog}
        for item in matched:
            key = (item["canonical_crm_contact_id"], str(item["bitrix_file_id"]))
            catalog_row = catalog_by_key[key]
            path = PACKAGE / item["folder"] / item["local_file"]
            content = path.read_bytes()
            filename = catalog_row.get("original_filename") or path.name
            mime = mime_of(filename, None, content)
            dest_folder = OUT / "by_contact" / catalog_row["canonical_crm_contact_id"]
            dest_folder.mkdir(parents=True, exist_ok=True)
            dest = unique_dest(
                dest_folder,
                safe_filename(filename, str(catalog_row["bitrix_file_id"])),
                str(catalog_row["bitrix_file_id"]),
            )
            dest.write_bytes(content)
            digest = hashlib.sha256(content).hexdigest()
            local = str(dest.relative_to(OUT)).replace("\\", "/")
            import_row = {
                "canonical_crm_contact_id": catalog_row["canonical_crm_contact_id"],
                "bitrix_file_id": catalog_row["bitrix_file_id"],
                "original_filename": filename,
                "mime_type": mime,
                "bitrix_entity_type": catalog_row.get("bitrix_entity_type"),
                "bitrix_entity_id": catalog_row.get("bitrix_entity_id"),
                "source_type": catalog_row.get("source_type"),
                "source_record_id": catalog_row.get("source_record_id"),
            }
            status, doc_id, reason = import_document(db, actor, import_row, content, local)
            apply_to_manifest(
                manifest_rows,
                catalog_row,
                dest,
                digest,
                doc_id or "",
                "yes" if status == "yes" else status,
            )
            item["crm_status"] = status
            item["crm_document_id"] = doc_id
            item["crm_reason"] = reason
            item["archive_path"] = local
        db.commit()
        with EXISTING_MANIFEST.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(manifest_rows)
        print(json.dumps({"applied_at": utc_now(), "imported": matched}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
