"""Ensure finance demo rows link to projects/investors; fill gaps idempotently."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    FinanceTransaction,
    FinancialAccount,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentObligation,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project

GAP_TRANSACTIONS: list[dict[str, object]] = [
    {
        "ref": "DEMO-TXN-1307-ACQ",
        "project_code": "PRJ-1307-008",
        "type": TransactionType.ACQUISITION,
        "category": "Land Purchase",
        "amount": Decimal("3100000.00"),
        "description": "Demo acquisition — 1307 Rhode Island Ave NE",
        "txn_date": date(2026, 5, 1),
    },
    {
        "ref": "DEMO-TXN-1313-CON",
        "project_code": "PRJ-1313-009",
        "type": TransactionType.CONSTRUCTION_COST,
        "category": "Hard Costs",
        "amount": Decimal("850000.00"),
        "description": "Demo construction draw — 1313 H St NE",
        "txn_date": date(2025, 8, 15),
    },
    {
        "ref": "DEMO-TXN-1627-EQ",
        "project_code": "PRJ-1627-011",
        "investor_name": "James Whitfield",
        "type": TransactionType.INVESTMENT_INFLOW,
        "category": "Investor Capital",
        "amount": Decimal("500000.00"),
        "description": "Demo equity contribution — 1627 16th St NW",
        "txn_date": date(2024, 6, 1),
    },
]


def seed_finance_links(session: Session | None = None) -> dict[str, int]:
    own_session = session is None
    session = session or SessionLocal()
    counts = {"transactions": 0, "obligations": 0, "accounts": 0}
    try:
        account = session.scalar(
            select(FinancialAccount).where(
                FinancialAccount.account_reference == "DEMO-GAP-OP"
            )
        )
        if account is None:
            # Prefer existing demo operating account
            account = session.scalar(
                select(FinancialAccount).where(
                    FinancialAccount.is_demo.is_(True),
                    FinancialAccount.account_type == AccountType.OPERATING,
                )
            )
        if account is None:
            account = FinancialAccount(
                account_name="Demo Gap Operating Account",
                account_type=AccountType.OPERATING,
                institution_name="First National Bank",
                ownership_entity="Investhome Holdings LLC",
                currency="USD",
                current_balance=Decimal("500000.00"),
                available_balance=Decimal("450000.00"),
                account_reference="DEMO-GAP-OP",
                status=AccountStatus.ACTIVE,
                notes="Demo account for integrated finance gap fill.",
                is_demo=True,
            )
            session.add(account)
            session.flush()
            counts["accounts"] += 1

        projects = {p.project_code: p for p in session.scalars(select(Project)).all()}
        investors = {i.full_name: i for i in session.scalars(select(Investor)).all()}

        for spec in GAP_TRANSACTIONS:
            ref = str(spec["ref"])
            existing = session.scalar(
                select(FinanceTransaction).where(FinanceTransaction.reference_number == ref)
            )
            if existing is not None:
                if not existing.is_demo:
                    existing.is_demo = True
                continue
            project = projects.get(str(spec["project_code"]))
            investor = None
            inv_name = spec.get("investor_name")
            if inv_name:
                investor = investors.get(str(inv_name))
            txn = FinanceTransaction(
                transaction_date=spec["txn_date"],  # type: ignore[arg-type]
                transaction_type=spec["type"],  # type: ignore[arg-type]
                category=str(spec["category"]),
                amount=spec["amount"],  # type: ignore[arg-type]
                currency="USD",
                description=str(spec["description"]),
                project_id=project.id if project else None,
                investor_id=investor.id if investor else None,
                account_id=account.id,
                reference_number=ref,
                status=TransactionStatus.COMPLETED,
                notes="Integrated demo finance link.",
                is_demo=True,
            )
            session.add(txn)
            counts["transactions"] += 1

            # Matching payment schedule / obligation with same amount
            obl_desc = f"Schedule for {ref}"
            obl_existing = session.scalar(
                select(PaymentObligation).where(PaymentObligation.description == obl_desc)
            )
            if obl_existing is None and project is not None:
                session.add(
                    PaymentObligation(
                        obligation_type=ObligationType.VENDOR_PAYMENT,
                        payee="Demo Vendor",
                        description=obl_desc,
                        amount=spec["amount"],  # type: ignore[arg-type]
                        currency="USD",
                        due_date=date(2026, 12, 31),
                        project_id=project.id,
                        investor_id=investor.id if investor else None,
                        status=ObligationStatus.UPCOMING,
                        priority=ObligationPriority.NORMAL,
                        notes="Integrated demo payment schedule.",
                        is_demo=True,
                    )
                )
                counts["obligations"] += 1

        # Touch existing demo finance rows to ensure project links where missing
        unlinked = session.scalars(
            select(FinanceTransaction).where(
                FinanceTransaction.is_demo.is_(True),
                FinanceTransaction.project_id.is_(None),
            )
        ).all()
        temple = projects.get("PRJ-TEMP-001")
        if temple is not None:
            for txn in unlinked[:5]:
                txn.project_id = temple.id

        if own_session:
            session.commit()
        else:
            session.flush()
        return counts
    finally:
        if own_session:
            session.close()
