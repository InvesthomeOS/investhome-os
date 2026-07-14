"""Demo finance seed data."""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.finance import (
    AccountStatus,
    AccountType,
    BudgetCategory,
    CommitmentStatus,
    CommitmentType,
    FinanceTransaction,
    FinancialAccount,
    FundingCommitment,
    ObligationPriority,
    ObligationStatus,
    ObligationType,
    PaymentMethod,
    PaymentObligation,
    ProjectBudget,
    TransactionStatus,
    TransactionType,
)
from investhome_api.models.investor import Investor
from investhome_api.models.project import Project

PROJECT_CODES = [
    "PRJ-TEMP-001",
    "PRJ-UNIL-002",
    "PRJ-309H-003",
    "PRJ-CAMP-004",
    "PRJ-1812H-005",
]

INVESTOR_NAMES = [
    "James Whitfield",
    "Marmara Capital Partners",
    "Al-Rashid Family Office",
    "Nordic Growth Fund II",
]


def _lookup_projects(session: Session) -> dict[str, Project]:
    projects = session.scalars(
        select(Project).where(Project.project_code.in_(PROJECT_CODES))
    ).all()
    return {p.project_code: p for p in projects}


def _lookup_investors(session: Session) -> dict[str, Investor]:
    investors = session.scalars(
        select(Investor).where(Investor.full_name.in_(INVESTOR_NAMES))
    ).all()
    return {i.full_name: i for i in investors}


def seed_demo_finance() -> int:
    """Insert demo finance data when financial_accounts is empty. Returns rows inserted."""
    from investhome_api.db.session import SessionLocal

    with SessionLocal() as session:
        existing = session.scalar(select(FinancialAccount.id).limit(1))
        if existing is not None:
            return 0

        projects = _lookup_projects(session)
        investors = _lookup_investors(session)
        if not projects:
            return 0

        temple = projects.get("PRJ-TEMP-001")
        uniloft = projects.get("PRJ-UNIL-002")
        h309 = projects.get("PRJ-309H-003")
        camp = projects.get("PRJ-CAMP-004")
        h1812 = projects.get("PRJ-1812H-005")

        whitfield = investors.get("James Whitfield")
        marmara = investors.get("Marmara Capital Partners")
        rashid = investors.get("Al-Rashid Family Office")
        nordic = investors.get("Nordic Growth Fund II")

        operating = FinancialAccount(
            account_name="Investhome Operating Account",
            account_type=AccountType.OPERATING,
            institution_name="First National Bank",
            ownership_entity="Investhome Holdings LLC",
            currency="USD",
            current_balance=Decimal("2450000.00"),
            available_balance=Decimal("2180000.00"),
            account_reference="FNB-OP-001",
            status=AccountStatus.ACTIVE,
            notes="Demo — primary operating account for corporate expenses.",
            is_demo=True,
        )
        project_account = FinancialAccount(
            account_name="Temple Construction Escrow",
            account_type=AccountType.PROJECT,
            institution_name="City Trust Bank",
            ownership_entity="Investhome Temple LLC",
            currency="USD",
            current_balance=Decimal("8750000.00"),
            available_balance=Decimal("6200000.00"),
            account_reference="CTB-PRJ-TEMP",
            status=AccountStatus.ACTIVE,
            notes="Demo — project-specific account for The Temple drawdowns.",
            is_demo=True,
        )
        escrow = FinancialAccount(
            account_name="Investor Capital Escrow",
            account_type=AccountType.ESCROW,
            institution_name="Metro Escrow Services",
            ownership_entity="Investhome Capital LLC",
            currency="USD",
            current_balance=Decimal("4200000.00"),
            available_balance=Decimal("4200000.00"),
            account_reference="MES-ESC-001",
            status=AccountStatus.ACTIVE,
            notes="Demo — holds pending investor capital until funding events.",
            is_demo=True,
        )
        investor_funds = FinancialAccount(
            account_name="LP Distribution Account",
            account_type=AccountType.INVESTOR_FUNDS,
            institution_name="First National Bank",
            ownership_entity="Investhome Fund I GP LLC",
            currency="USD",
            current_balance=Decimal("1850000.00"),
            available_balance=Decimal("1650000.00"),
            account_reference="FNB-LP-001",
            status=AccountStatus.ACTIVE,
            notes="Demo — investor distributions and capital call receipts.",
            is_demo=True,
        )
        session.add_all([operating, project_account, escrow, investor_funds])
        session.flush()

        transactions: list[FinanceTransaction] = []

        if temple:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2024, 4, 15),
                    transaction_type=TransactionType.ACQUISITION,
                    category="Land Purchase",
                    amount=Decimal("8200000.00"),
                    currency="USD",
                    description="Acquisition of 1610 Columbia Rd NW parcel",
                    account_id=project_account.id,
                    project_id=temple.id,
                    counterparty="Columbia Road Holdings LLC",
                    reference_number="ACQ-TEMP-001",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2024, 4, 15),
                    is_demo=True,
                )
            )
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2025, 11, 20),
                    transaction_type=TransactionType.CONSTRUCTION_COST,
                    category="General Contractor",
                    amount=Decimal("1250000.00"),
                    currency="USD",
                    description="GC progress payment — structural steel package",
                    account_id=project_account.id,
                    project_id=temple.id,
                    counterparty="Capitol Build Group",
                    reference_number="CON-TEMP-042",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2025, 11, 22),
                    is_demo=True,
                )
            )

        if uniloft:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2026, 4, 1),
                    transaction_type=TransactionType.RENTAL_INCOME,
                    category="Residential Rent",
                    amount=Decimal("87500.00"),
                    currency="USD",
                    description="April 2026 rental collections — UniLoft",
                    account_id=operating.id,
                    project_id=uniloft.id,
                    counterparty="Tenant Collections",
                    reference_number="RENT-UNIL-202604",
                    payment_method=PaymentMethod.ACH,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2026, 4, 3),
                    is_demo=True,
                )
            )

        if h309 and whitfield:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2025, 9, 10),
                    transaction_type=TransactionType.INVESTMENT_INFLOW,
                    category="Equity Contribution",
                    amount=Decimal("1500000.00"),
                    currency="USD",
                    description="Series A equity contribution — 309 H St NE",
                    account_id=investor_funds.id,
                    project_id=h309.id,
                    investor_id=whitfield.id,
                    counterparty=whitfield.full_name,
                    reference_number="EQ-309H-WF-001",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2025, 9, 10),
                    is_demo=True,
                )
            )

        if camp:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2025, 6, 1),
                    transaction_type=TransactionType.LOAN_DRAW,
                    category="Construction Loan",
                    amount=Decimal("3500000.00"),
                    currency="USD",
                    description="Initial construction loan draw — Camp Springs",
                    account_id=project_account.id,
                    project_id=camp.id,
                    counterparty="Atlantic Commercial Lending",
                    reference_number="DRAW-CAMP-001",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2025, 6, 3),
                    is_demo=True,
                )
            )
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2026, 5, 1),
                    transaction_type=TransactionType.LOAN_PAYMENT,
                    category="Debt Service",
                    amount=Decimal("42500.00"),
                    currency="USD",
                    description="Monthly loan payment — Camp Springs construction loan",
                    account_id=operating.id,
                    project_id=camp.id,
                    counterparty="Atlantic Commercial Lending",
                    reference_number="PAY-CAMP-202605",
                    payment_method=PaymentMethod.ACH,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2026, 5, 1),
                    is_demo=True,
                )
            )

        if h1812:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2026, 3, 15),
                    transaction_type=TransactionType.SALE_PROCEEDS,
                    category="Unit Sales",
                    amount=Decimal("980000.00"),
                    currency="USD",
                    description="Phase 1 condo closings — 1812 H Street",
                    account_id=escrow.id,
                    project_id=h1812.id,
                    counterparty="Settlement Services Inc.",
                    reference_number="SALE-1812H-Q1",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.COMPLETED,
                    paid_date=date(2026, 3, 18),
                    is_demo=True,
                )
            )

        if marmara and temple:
            transactions.append(
                FinanceTransaction(
                    transaction_date=date(2026, 7, 20),
                    transaction_type=TransactionType.INVESTMENT_INFLOW,
                    category="Equity Contribution",
                    amount=Decimal("2500000.00"),
                    currency="USD",
                    description="Pending capital call — The Temple Phase 2",
                    account_id=escrow.id,
                    project_id=temple.id,
                    investor_id=marmara.id,
                    counterparty=marmara.full_name,
                    reference_number="EQ-TEMP-MCP-002",
                    payment_method=PaymentMethod.WIRE,
                    status=TransactionStatus.SCHEDULED,
                    due_date=date(2026, 7, 20),
                    is_demo=True,
                )
            )

        session.add_all(transactions)

        budgets: list[ProjectBudget] = []
        budget_specs: list[tuple[Project | None, str, BudgetCategory, Decimal, Decimal, Decimal]] = [
            (temple, "Land & Acquisition", BudgetCategory.ACQUISITION, Decimal("8500000.00"), Decimal("8200000.00"), Decimal("8200000.00")),
            (temple, "Hard Construction", BudgetCategory.CONSTRUCTION, Decimal("32000000.00"), Decimal("33500000.00"), Decimal("14200000.00")),
            (temple, "Design & Architecture", BudgetCategory.ARCHITECTURE, Decimal("1800000.00"), Decimal("1950000.00"), Decimal("1750000.00")),
            (uniloft, "Renovation Costs", BudgetCategory.CONSTRUCTION, Decimal("9800000.00"), Decimal("10200000.00"), Decimal("9800000.00")),
            (uniloft, "Leasing & Marketing", BudgetCategory.LEASING, Decimal("450000.00"), Decimal("420000.00"), Decimal("380000.00")),
            (h309, "Acquisition Budget", BudgetCategory.ACQUISITION, Decimal("5200000.00"), Decimal("5100000.00"), Decimal("5100000.00")),
            (h309, "Construction Budget", BudgetCategory.CONSTRUCTION, Decimal("12000000.00"), Decimal("11800000.00"), Decimal("4200000.00")),
            (camp, "Site Work & Utilities", BudgetCategory.CONSTRUCTION, Decimal("6500000.00"), Decimal("6800000.00"), Decimal("3100000.00")),
            (camp, "Financing Costs", BudgetCategory.FINANCING, Decimal("850000.00"), Decimal("900000.00"), Decimal("425000.00")),
            (h1812, "Sales & Marketing", BudgetCategory.SALES, Decimal("750000.00"), Decimal("720000.00"), Decimal("680000.00")),
            (h1812, "Contingency Reserve", BudgetCategory.CONTINGENCY, Decimal("500000.00"), Decimal("500000.00"), Decimal("125000.00")),
        ]
        for project, name, category, original, revised, paid in budget_specs:
            if project is None:
                continue
            budgets.append(
                ProjectBudget(
                    project_id=project.id,
                    budget_name=name,
                    category=category,
                    original_budget=original,
                    revised_budget=revised,
                    committed_amount=revised,
                    paid_amount=paid,
                    forecast_amount=revised + Decimal("150000.00"),
                    currency="USD",
                    notes=f"Demo budget — {name} for {project.project_name}.",
                    is_demo=True,
                )
            )
        session.add_all(budgets)

        commitments: list[FundingCommitment] = []
        if temple and whitfield:
            commitments.append(
                FundingCommitment(
                    project_id=temple.id,
                    investor_id=whitfield.id,
                    commitment_type=CommitmentType.EQUITY,
                    committed_amount=Decimal("3000000.00"),
                    funded_amount=Decimal("2500000.00"),
                    remaining_amount=Decimal("500000.00"),
                    currency="USD",
                    commitment_date=date(2024, 6, 1),
                    target_funding_date=date(2026, 9, 30),
                    status=CommitmentStatus.PARTIALLY_FUNDED,
                    notes="Demo — JV equity commitment for The Temple.",
                    is_demo=True,
                )
            )
        if temple and marmara:
            commitments.append(
                FundingCommitment(
                    project_id=temple.id,
                    investor_id=marmara.id,
                    commitment_type=CommitmentType.PREFERRED_EQUITY,
                    committed_amount=Decimal("5000000.00"),
                    funded_amount=Decimal("2500000.00"),
                    remaining_amount=Decimal("2500000.00"),
                    currency="USD",
                    commitment_date=date(2025, 1, 15),
                    target_funding_date=date(2026, 12, 31),
                    status=CommitmentStatus.PARTIALLY_FUNDED,
                    notes="Demo — preferred equity tranche for The Temple.",
                    is_demo=True,
                )
            )
        if h309 and rashid:
            commitments.append(
                FundingCommitment(
                    project_id=h309.id,
                    investor_id=rashid.id,
                    commitment_type=CommitmentType.EQUITY,
                    committed_amount=Decimal("2000000.00"),
                    funded_amount=Decimal("2000000.00"),
                    remaining_amount=Decimal("0.00"),
                    currency="USD",
                    commitment_date=date(2025, 3, 1),
                    actual_funding_date=date(2025, 9, 10),
                    status=CommitmentStatus.FULLY_FUNDED,
                    notes="Demo — fully funded equity for 309 H St NE.",
                    is_demo=True,
                )
            )
        if camp and nordic:
            commitments.append(
                FundingCommitment(
                    project_id=camp.id,
                    investor_id=nordic.id,
                    commitment_type=CommitmentType.CONSTRUCTION_LOAN,
                    committed_amount=Decimal("8000000.00"),
                    funded_amount=Decimal("3500000.00"),
                    remaining_amount=Decimal("4500000.00"),
                    currency="USD",
                    commitment_date=date(2025, 4, 1),
                    target_funding_date=date(2027, 6, 30),
                    status=CommitmentStatus.COMMITTED,
                    notes="Demo — construction loan facility for Camp Springs.",
                    is_demo=True,
                )
            )
        if uniloft and marmara:
            commitments.append(
                FundingCommitment(
                    project_id=uniloft.id,
                    investor_id=marmara.id,
                    commitment_type=CommitmentType.SPONSOR_EQUITY,
                    committed_amount=Decimal("1500000.00"),
                    funded_amount=Decimal("1500000.00"),
                    remaining_amount=Decimal("0.00"),
                    currency="USD",
                    commitment_date=date(2023, 7, 1),
                    actual_funding_date=date(2023, 8, 1),
                    status=CommitmentStatus.FULLY_FUNDED,
                    notes="Demo — sponsor equity for UniLoft renovation.",
                    is_demo=True,
                )
            )
        session.add_all(commitments)

        obligations: list[PaymentObligation] = []
        if temple:
            obligations.append(
                PaymentObligation(
                    project_id=temple.id,
                    obligation_type=ObligationType.VENDOR_PAYMENT,
                    payee="Capitol Build Group",
                    description="GC invoice #1042 — structural steel",
                    amount=Decimal("875000.00"),
                    currency="USD",
                    due_date=date(2026, 7, 25),
                    status=ObligationStatus.UPCOMING,
                    priority=ObligationPriority.HIGH,
                    notes="Demo — upcoming vendor payment.",
                    is_demo=True,
                )
            )
            obligations.append(
                PaymentObligation(
                    project_id=temple.id,
                    obligation_type=ObligationType.PROFESSIONAL_FEE,
                    payee="Harrison & Associates",
                    description="Architectural services — Q2 2026",
                    amount=Decimal("125000.00"),
                    currency="USD",
                    due_date=date(2026, 6, 30),
                    status=ObligationStatus.OVERDUE,
                    priority=ObligationPriority.CRITICAL,
                    notes="Demo — overdue professional fee.",
                    is_demo=True,
                )
            )
        if uniloft:
            obligations.append(
                PaymentObligation(
                    project_id=uniloft.id,
                    obligation_type=ObligationType.UTILITY,
                    payee="Pepco",
                    description="Common area electricity — June 2026",
                    amount=Decimal("4200.00"),
                    currency="USD",
                    due_date=date(2026, 7, 15),
                    status=ObligationStatus.DUE,
                    priority=ObligationPriority.NORMAL,
                    notes="Demo — utility payment due this week.",
                    is_demo=True,
                )
            )
        if camp:
            obligations.append(
                PaymentObligation(
                    project_id=camp.id,
                    obligation_type=ObligationType.LOAN_PAYMENT,
                    payee="Atlantic Commercial Lending",
                    description="Construction loan interest — July 2026",
                    amount=Decimal("42500.00"),
                    currency="USD",
                    due_date=date(2026, 7, 1),
                    paid_date=date(2026, 7, 1),
                    status=ObligationStatus.PAID,
                    priority=ObligationPriority.NORMAL,
                    notes="Demo — paid loan payment.",
                    is_demo=True,
                )
            )
        if h1812 and whitfield:
            obligations.append(
                PaymentObligation(
                    project_id=h1812.id,
                    investor_id=whitfield.id,
                    obligation_type=ObligationType.INVESTOR_DISTRIBUTION,
                    payee=whitfield.full_name,
                    description="Q1 2026 profit distribution — 1812 H Street",
                    amount=Decimal("185000.00"),
                    currency="USD",
                    due_date=date(2026, 4, 15),
                    paid_date=date(2026, 4, 16),
                    status=ObligationStatus.PAID,
                    priority=ObligationPriority.HIGH,
                    notes="Demo — completed investor distribution.",
                    is_demo=True,
                )
            )
        if h309:
            obligations.append(
                PaymentObligation(
                    project_id=h309.id,
                    obligation_type=ObligationType.INSURANCE,
                    payee="Liberty Mutual",
                    description="Builder's risk policy renewal",
                    amount=Decimal("68000.00"),
                    currency="USD",
                    due_date=date(2026, 8, 1),
                    status=ObligationStatus.UPCOMING,
                    priority=ObligationPriority.CRITICAL,
                    notes="Demo — critical insurance renewal.",
                    is_demo=True,
                )
            )
        session.add_all(obligations)

        session.commit()
        return (
            4
            + len(transactions)
            + len(budgets)
            + len(commitments)
            + len(obligations)
        )
