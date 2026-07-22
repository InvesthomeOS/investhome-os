"""Financial and document reconciliation for G12 (read-only checks)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session


@dataclass
class ReconCheck:
    name: str
    status: str  # PASS | FAIL | SKIP | N/A
    expected: str | None = None
    actual: str | None = None
    diff: str | None = None
    notes: str = ""


@dataclass
class ReconReport:
    scope: str
    checks: list[ReconCheck] = field(default_factory=list)
    open_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "checks": [asdict(c) for c in self.checks],
            "open_issues": self.open_issues,
            "summary": {
                "pass": sum(1 for c in self.checks if c.status == "PASS"),
                "fail": sum(1 for c in self.checks if c.status == "FAIL"),
                "skip": sum(1 for c in self.checks if c.status in {"SKIP", "N/A"}),
            },
        }


def reconcile_demo_integrity(db: Session) -> ReconReport:
    """Integrity checks against whatever is in the connected DB (typically demo)."""
    from investhome_api.models.finance import FinancialAccount, FinanceTransaction
    from investhome_api.models.inventory import InventoryAsset, InventoryReservation

    report = ReconReport(scope="connected_db_integrity")

    orphan_txn = int(
        db.scalar(
            select(func.count())
            .select_from(FinanceTransaction)
            .outerjoin(FinancialAccount, FinanceTransaction.account_id == FinancialAccount.id)
            .where(FinancialAccount.id.is_(None))
        )
        or 0
    )
    report.checks.append(
        ReconCheck(
            "finance_transactions.account_fk",
            "PASS" if orphan_txn == 0 else "FAIL",
            expected="0 orphans",
            actual=str(orphan_txn),
            diff=None if orphan_txn == 0 else str(orphan_txn),
            notes="Transactions must reference an existing financial account",
        )
    )

    orphan_res = int(
        db.scalar(
            select(func.count())
            .select_from(InventoryReservation)
            .outerjoin(InventoryAsset, InventoryReservation.inventory_asset_id == InventoryAsset.id)
            .where(InventoryAsset.id.is_(None))
        )
        or 0
    )
    report.checks.append(
        ReconCheck(
            "inventory_reservations.asset_fk",
            "PASS" if orphan_res == 0 else "FAIL",
            expected="0 orphans",
            actual=str(orphan_res),
            notes="Reservations must reference an existing inventory asset",
        )
    )

    bal = db.scalar(select(func.coalesce(func.sum(FinancialAccount.current_balance), 0)))
    report.checks.append(
        ReconCheck(
            "financial_accounts.balance_sum",
            "N/A",
            expected="bank statement total (not provided)",
            actual=str(bal if bal is not None else "0"),
            notes=(
                "Cannot certify bank reconciliation without source bank exports. "
                "Current DB balance sum is informational only."
            ),
        )
    )

    txn_count = int(db.scalar(select(func.count()).select_from(FinanceTransaction)) or 0)
    report.checks.append(
        ReconCheck(
            "finance_transactions.count_vs_source",
            "N/A",
            expected="QuickBooks/bank export count (not provided)",
            actual=str(txn_count),
            notes="No source ledger file available for count reconciliation",
        )
    )

    for name in (
        "invoices_vs_vendor_bills",
        "reservations_deposits_vs_bank",
        "contracts_vs_documents",
        "investor_payments_vs_commitments",
        "vendor_payments_vs_bills",
        "budgets_vs_workbook_totals",
        "cash_position_vs_bank",
    ):
        report.checks.append(
            ReconCheck(
                name,
                "SKIP",
                expected="source extract",
                actual=None,
                notes="Blocked — real source files not provided",
            )
        )
        report.open_issues.append(f"Missing source for {name}")

    return report


def reconcile_against_source_balances(
    db: Session,
    *,
    expected_balances: dict[str, Decimal],
) -> ReconReport:
    """Compare FinancialAccount.current_balance to operator-provided expected map.

    expected_balances keys = account_name (case-insensitive).
    Never auto-adjust balances — report diffs only.
    """
    from investhome_api.models.finance import FinancialAccount

    report = ReconReport(scope="account_balance_recon")
    if not expected_balances:
        report.checks.append(
            ReconCheck(
                "expected_balances",
                "SKIP",
                notes="No expected balance map provided",
            )
        )
        report.open_issues.append("Provide bank statement balances keyed by account_name")
        return report

    accounts = list(db.scalars(select(FinancialAccount)).all())
    by_name = {(a.account_name or "").strip().lower(): a for a in accounts}

    for name, expected in expected_balances.items():
        key = name.strip().lower()
        acct = by_name.get(key)
        if acct is None:
            report.checks.append(
                ReconCheck(
                    f"balance:{name}",
                    "FAIL",
                    expected=str(expected),
                    actual=None,
                    notes="Account not found in DB",
                )
            )
            report.open_issues.append(f"Missing account for expected balance: {name}")
            continue
        actual = acct.current_balance if acct.current_balance is not None else Decimal("0")
        diff = actual - expected
        ok = diff == 0
        report.checks.append(
            ReconCheck(
                f"balance:{name}",
                "PASS" if ok else "FAIL",
                expected=str(expected),
                actual=str(actual),
                diff=str(diff),
                notes="" if ok else "Unexplained balance difference — do not go live",
            )
        )
        if not ok:
            report.open_issues.append(f"Balance mismatch for {name}: diff={diff}")

    return report
