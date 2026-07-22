"""CSV template validation and dry-run import checks (no DB writes)."""

from __future__ import annotations

import csv
import io
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from investhome_api.migration.mapping_registry import (
    CANONICAL_ENTITIES,
    TEMPLATE_HEADERS,
)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CURRENCY_RE = re.compile(r"^[A-Z]{3}$")
DEMO_EMAIL_SUFFIX = "@investhome.demo"

FINANCIAL_ENTITIES = {
    e.key for e in CANONICAL_ENTITIES if e.financial_class == "financial"
}


@dataclass
class RowIssue:
    row: int
    field: str
    severity: str  # error | warning
    message: str


@dataclass
class EntityDryRunResult:
    entity: str
    source_path: str | None
    rows_read: int = 0
    accepted: int = 0
    rejected: int = 0
    warnings: int = 0
    issues: list[RowIssue] = field(default_factory=list)
    duplicate_keys: list[str] = field(default_factory=list)
    financial: bool = False
    merge_policy: str = "suggest_only"
    status: str = "no_source"  # no_source | dry_run_ok | dry_run_failed


@dataclass
class DryRunReport:
    mode: str
    real_sources_present: bool
    results: list[EntityDryRunResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "real_sources_present": self.real_sources_present,
            "notes": self.notes,
            "results": [
                {
                    **{k: v for k, v in asdict(r).items() if k != "issues"},
                    "issues": [asdict(i) for i in r.issues[:200]],
                    "issues_truncated": len(r.issues) > 200,
                }
                for r in self.results
            ],
            "totals": {
                "entities_with_source": sum(1 for r in self.results if r.source_path),
                "rows_read": sum(r.rows_read for r in self.results),
                "accepted": sum(r.accepted for r in self.results),
                "rejected": sum(r.rejected for r in self.results),
            },
        }


def _parse_decimal(value: str) -> Decimal | None:
    try:
        return Decimal(value.replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _entity_meta(entity: str) -> tuple[bool, str]:
    for e in CANONICAL_ENTITIES:
        if e.key == entity:
            return e.financial_class == "financial", e.merge_policy
    return entity in FINANCIAL_ENTITIES, "suggest_only"


def validate_headers(entity: str, headers: list[str]) -> list[str]:
    expected = TEMPLATE_HEADERS.get(entity, [])
    missing = [h for h in expected if h not in headers]
    return missing


def validate_row(entity: str, row_num: int, row: dict[str, str]) -> list[RowIssue]:
    issues: list[RowIssue] = []

    def req(name: str) -> str:
        return (row.get(name) or "").strip()

    def err(fld: str, msg: str) -> None:
        issues.append(RowIssue(row_num, fld, "error", msg))

    def warn(fld: str, msg: str) -> None:
        issues.append(RowIssue(row_num, fld, "warning", msg))

    if entity == "crm_contacts":
        if not req("display_name"):
            err("display_name", "required")
        email = req("primary_email").lower()
        if not email:
            err("primary_email", "required")
        elif not EMAIL_RE.match(email):
            err("primary_email", "invalid email")
        elif email.endswith(DEMO_EMAIL_SUFFIX):
            err("primary_email", "demo domain not allowed for production import")

    elif entity == "crm_companies":
        if not req("display_name"):
            err("display_name", "required")

    elif entity == "leads":
        if not req("full_name"):
            err("full_name", "required")
        email = req("email").lower()
        if email and not EMAIL_RE.match(email):
            err("email", "invalid email")
        if email.endswith(DEMO_EMAIL_SUFFIX):
            err("email", "demo domain not allowed for production import")
        budget = req("estimated_budget")
        if budget and _parse_decimal(budget) is None:
            err("estimated_budget", "non-numeric")
        elif budget and _parse_decimal(budget) is not None and _parse_decimal(budget) < 0:  # type: ignore[operator]
            err("estimated_budget", "negative not allowed")

    elif entity == "investors":
        if not req("full_name"):
            err("full_name", "required")
        email = req("email").lower()
        if email and not EMAIL_RE.match(email):
            err("email", "invalid email")

    elif entity == "projects":
        if not req("project_code"):
            err("project_code", "required")
        if not req("project_name"):
            err("project_name", "required")

    elif entity == "inventory_assets":
        for fld in ("asset_code", "project_code", "building_code", "asset_type"):
            if not req(fld):
                err(fld, "required")
        price = req("list_price")
        if price and _parse_decimal(price) is None:
            err("list_price", "non-numeric")
        cur = req("currency")
        if cur and not CURRENCY_RE.match(cur.upper()):
            err("currency", "must be ISO-4217")

    elif entity == "inventory_reservations":
        for fld in ("external_ref", "asset_code", "party_email", "status"):
            if not req(fld):
                err(fld, "required")
        dep = req("deposit_amount")
        if dep and _parse_decimal(dep) is None:
            err("deposit_amount", "non-numeric")
        warn(
            "deposit_amount",
            "financial field — never auto-merge; manual reconcile required",
        )

    elif entity == "financial_accounts":
        for fld in ("account_name", "account_type", "currency", "current_balance"):
            if not req(fld):
                err(fld, "required")
        bal = req("current_balance")
        if bal and _parse_decimal(bal) is None:
            err("current_balance", "non-numeric")
        cur = req("currency")
        if cur and not CURRENCY_RE.match(cur.upper()):
            err("currency", "must be ISO-4217")
        warn("current_balance", "must match bank statement before commit")

    elif entity == "finance_transactions":
        for fld in ("transaction_date", "transaction_type", "amount", "account_name"):
            if not req(fld):
                err(fld, "required")
        if req("transaction_date") and _parse_date(req("transaction_date")) is None:
            err("transaction_date", "unparseable date")
        amt = _parse_decimal(req("amount"))
        if req("amount") and amt is None:
            err("amount", "non-numeric")
        elif amt == 0:
            err("amount", "zero amount rejected")
        warn("amount", "financial — never auto-merge duplicates")

    elif entity == "funding_commitments":
        for fld in ("investor_email", "project_code", "commitment_type", "committed_amount", "currency"):
            if not req(fld):
                err(fld, "required")
        amt = _parse_decimal(req("committed_amount"))
        if req("committed_amount") and (amt is None or amt <= 0):
            err("committed_amount", "must be > 0")
        funded = req("funded_amount")
        if funded:
            f = _parse_decimal(funded)
            if f is None:
                err("funded_amount", "non-numeric")
            elif amt is not None and f > amt:
                err("funded_amount", "cannot exceed committed_amount")

    elif entity == "payment_obligations":
        for fld in ("title", "obligation_type", "amount", "due_date", "currency"):
            if not req(fld):
                err(fld, "required")
        if req("due_date") and _parse_date(req("due_date")) is None:
            err("due_date", "unparseable date")
        amt = _parse_decimal(req("amount"))
        if req("amount") and (amt is None or amt <= 0):
            err("amount", "must be > 0")

    elif entity == "vendor_bills":
        for fld in ("external_ref", "vendor_code", "invoice_number", "amount", "currency"):
            if not req(fld):
                err(fld, "required")
        warn("amount", "AP financial — never auto-merge")

    elif entity == "documents_manifest":
        for fld in ("source_path", "original_filename", "checksum_sha256"):
            if not req(fld):
                err(fld, "required")
        checksum = req("checksum_sha256")
        if checksum and len(checksum) != 64:
            warn("checksum_sha256", "expected 64-char sha256 hex")

    elif entity == "users":
        email = req("email").lower()
        if not email:
            err("email", "required")
        elif not EMAIL_RE.match(email):
            err("email", "invalid email")
        elif email.endswith(DEMO_EMAIL_SUFFIX):
            err("email", "demo users cannot be imported as production")
        if not req("full_name"):
            err("full_name", "required")
        if not req("role_codes"):
            err("role_codes", "required")

    elif entity in TEMPLATE_HEADERS:
        # Generic: first header treated as soft-required when present in template
        first = TEMPLATE_HEADERS[entity][0]
        if not req(first):
            err(first, "required")

    return issues


def _dedupe_key(entity: str, row: dict[str, str]) -> str | None:
    getters = {
        "crm_contacts": lambda r: (r.get("primary_email") or "").strip().lower(),
        "crm_companies": lambda r: (r.get("display_name") or "").strip().lower(),
        "leads": lambda r: (r.get("email") or r.get("full_name") or "").strip().lower(),
        "investors": lambda r: (r.get("email") or r.get("full_name") or "").strip().lower(),
        "projects": lambda r: (r.get("project_code") or "").strip().upper(),
        "inventory_assets": lambda r: (
            f"{(r.get('project_code') or '').strip().upper()}:"
            f"{(r.get('asset_code') or '').strip()}"
        ),
        "inventory_reservations": lambda r: (r.get("external_ref") or "").strip(),
        "financial_accounts": lambda r: (r.get("account_name") or "").strip().lower(),
        "finance_transactions": lambda r: (r.get("external_ref") or "").strip(),
        "funding_commitments": lambda r: (
            f"{(r.get('investor_email') or '').strip().lower()}:"
            f"{(r.get('project_code') or '').strip().upper()}"
        ),
        "vendor_bills": lambda r: (r.get("external_ref") or "").strip(),
        "documents_manifest": lambda r: (r.get("checksum_sha256") or "").strip().lower(),
        "users": lambda r: (r.get("email") or "").strip().lower(),
    }
    fn = getters.get(entity)
    if not fn:
        return None
    key = fn(row)
    return key or None


def dry_run_csv(entity: str, content: str, *, source_path: str | None = None) -> EntityDryRunResult:
    financial, merge_policy = _entity_meta(entity)
    result = EntityDryRunResult(
        entity=entity,
        source_path=source_path,
        financial=financial,
        merge_policy=merge_policy,
    )
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None:
        result.status = "dry_run_failed"
        result.issues.append(RowIssue(0, "_header", "error", "empty CSV"))
        return result

    headers = list(reader.fieldnames)
    missing = validate_headers(entity, headers)
    for m in missing:
        result.issues.append(RowIssue(0, m, "error", f"missing required column: {m}"))
    if missing:
        result.status = "dry_run_failed"
        return result

    seen: dict[str, int] = {}
    for idx, row in enumerate(reader, start=2):
        result.rows_read += 1
        clean = {k: (v or "").strip() if isinstance(v, str) else "" for k, v in row.items()}
        issues = validate_row(entity, idx, clean)
        result.issues.extend(issues)
        errors = [i for i in issues if i.severity == "error"]
        warns = [i for i in issues if i.severity == "warning"]
        result.warnings += len(warns)

        key = _dedupe_key(entity, clean)
        if key:
            if key in seen:
                result.duplicate_keys.append(key)
                result.issues.append(
                    RowIssue(
                        idx,
                        "_duplicate",
                        "error" if financial else "warning",
                        f"duplicate key '{key}' also on row {seen[key]}"
                        + (
                            " — financial duplicates never auto-merged"
                            if financial
                            else " — suggest merge only"
                        ),
                    )
                )
                if financial:
                    errors.append(result.issues[-1])
            else:
                seen[key] = idx

        if errors:
            result.rejected += 1
        else:
            result.accepted += 1

    result.status = "dry_run_ok" if result.rejected == 0 else "dry_run_failed"
    return result


def discover_source_csvs(source_dir: Path) -> dict[str, Path]:
    """Map entity key → CSV path when filename matches `{entity}.csv` or template name."""
    found: dict[str, Path] = {}
    if not source_dir.exists():
        return found
    aliases = {k: k for k in TEMPLATE_HEADERS}
    aliases.update(
        {
            "contacts": "crm_contacts",
            "companies": "crm_companies",
            "accounts": "financial_accounts",
            "transactions": "finance_transactions",
            "commitments": "funding_commitments",
            "obligations": "payment_obligations",
            "reservations": "inventory_reservations",
            "units": "inventory_assets",
            "documents": "documents_manifest",
        }
    )
    for path in sorted(source_dir.glob("*.csv")):
        stem = path.stem.lower()
        entity = aliases.get(stem)
        if entity:
            found[entity] = path
    return found


def run_dry_run(source_dir: Path | None) -> DryRunReport:
    report = DryRunReport(mode="dry-run", real_sources_present=False)
    if source_dir is None or not source_dir.exists():
        report.notes.append(
            "No source directory provided or directory missing. "
            "Place validated extracts under the sources path and re-run."
        )
        for entity in TEMPLATE_HEADERS:
            financial, merge_policy = _entity_meta(entity)
            report.results.append(
                EntityDryRunResult(
                    entity=entity,
                    source_path=None,
                    financial=financial,
                    merge_policy=merge_policy,
                    status="no_source",
                )
            )
        return report

    found = discover_source_csvs(source_dir)
    report.real_sources_present = bool(found)
    if not found:
        report.notes.append(
            f"No recognizable entity CSV files in {source_dir}. "
            f"Expected names like: {', '.join(sorted(TEMPLATE_HEADERS)[:8])}…"
        )

    for entity in TEMPLATE_HEADERS:
        path = found.get(entity)
        if path is None:
            financial, merge_policy = _entity_meta(entity)
            report.results.append(
                EntityDryRunResult(
                    entity=entity,
                    source_path=None,
                    financial=financial,
                    merge_policy=merge_policy,
                    status="no_source",
                )
            )
            continue
        content = path.read_text(encoding="utf-8-sig")
        # Heuristic: reject files that still look like empty header-only templates
        # with only the EXAMPLE row marker — still validate them as dry-run.
        result = dry_run_csv(entity, content, source_path=str(path))
        report.results.append(result)

    if report.real_sources_present:
        report.notes.append(
            "Sources found — dry-run validation only. No DB writes performed. "
            "Financial entities require separate reconciliation before commit."
        )
    return report


def write_template_csvs(output_dir: Path) -> list[str]:
    """Write empty header-only CSV templates (no fake business rows)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for entity, headers in TEMPLATE_HEADERS.items():
        path = output_dir / f"{entity}.csv"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(headers)
        written.append(str(path))
    return written
