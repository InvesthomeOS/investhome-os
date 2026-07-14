import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class AccountType(str, enum.Enum):
    OPERATING = "operating"
    PROJECT = "project"
    ESCROW = "escrow"
    INVESTOR_FUNDS = "investor_funds"
    RESERVE = "reserve"
    DEBT = "debt"
    PERSONAL = "personal"
    OTHER = "other"


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    CLOSED = "closed"


class TransactionType(str, enum.Enum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    INVESTMENT_INFLOW = "investment_inflow"
    INVESTOR_DISTRIBUTION = "investor_distribution"
    LOAN_DRAW = "loan_draw"
    LOAN_PAYMENT = "loan_payment"
    ACQUISITION = "acquisition"
    CONSTRUCTION_COST = "construction_cost"
    OPERATING_COST = "operating_cost"
    SALE_PROCEEDS = "sale_proceeds"
    RENTAL_INCOME = "rental_income"
    REFUND = "refund"
    OTHER = "other"


class TransactionStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentMethod(str, enum.Enum):
    WIRE = "wire"
    ACH = "ach"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    CASH = "cash"
    INTERNAL_TRANSFER = "internal_transfer"
    OTHER = "other"


class BudgetCategory(str, enum.Enum):
    ACQUISITION = "acquisition"
    DESIGN = "design"
    ARCHITECTURE = "architecture"
    ENGINEERING = "engineering"
    PERMITTING = "permitting"
    LEGAL = "legal"
    FINANCING = "financing"
    CONSTRUCTION = "construction"
    MARKETING = "marketing"
    SALES = "sales"
    LEASING = "leasing"
    OPERATIONS = "operations"
    CONTINGENCY = "contingency"
    TAXES = "taxes"
    INSURANCE = "insurance"
    OTHER = "other"


class CommitmentType(str, enum.Enum):
    EQUITY = "equity"
    PREFERRED_EQUITY = "preferred_equity"
    DEBT = "debt"
    BRIDGE_LOAN = "bridge_loan"
    CONSTRUCTION_LOAN = "construction_loan"
    MEZZANINE = "mezzanine"
    SPONSOR_EQUITY = "sponsor_equity"
    OTHER = "other"


class CommitmentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    COMMITTED = "committed"
    PARTIALLY_FUNDED = "partially_funded"
    FULLY_FUNDED = "fully_funded"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class ObligationType(str, enum.Enum):
    VENDOR_PAYMENT = "vendor_payment"
    LOAN_PAYMENT = "loan_payment"
    INVESTOR_DISTRIBUTION = "investor_distribution"
    TAX = "tax"
    INSURANCE = "insurance"
    PAYROLL = "payroll"
    UTILITY = "utility"
    PROFESSIONAL_FEE = "professional_fee"
    ACQUISITION_PAYMENT = "acquisition_payment"
    OTHER = "other"


class ObligationStatus(str, enum.Enum):
    UPCOMING = "upcoming"
    DUE = "due"
    OVERDUE = "overdue"
    PAID = "paid"
    CANCELLED = "cancelled"


class ObligationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


INCOME_TRANSACTION_TYPES = frozenset(
    {
        TransactionType.INCOME,
        TransactionType.INVESTMENT_INFLOW,
        TransactionType.LOAN_DRAW,
        TransactionType.SALE_PROCEEDS,
        TransactionType.RENTAL_INCOME,
        TransactionType.REFUND,
    }
)


class FinancialAccount(Base):
    __tablename__ = "financial_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False, length=50),
        nullable=False,
        default=AccountType.OPERATING,
    )
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ownership_entity: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    current_balance: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    available_balance: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    account_reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False, length=50),
        nullable=False,
        default=AccountStatus.ACTIVE,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    transactions: Mapped[list["FinanceTransaction"]] = relationship(back_populates="account")


class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, length=50),
        nullable=False,
    )
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("financial_accounts.id"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
    )
    investor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investors.id"),
        nullable=True,
    )
    counterparty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, native_enum=False, length=50),
        nullable=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, native_enum=False, length=50),
        nullable=False,
        default=TransactionStatus.PENDING,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    account: Mapped[FinancialAccount] = relationship(back_populates="transactions")


class ProjectBudget(Base):
    __tablename__ = "project_budgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    budget_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[BudgetCategory] = mapped_column(
        Enum(BudgetCategory, native_enum=False, length=50),
        nullable=False,
    )
    original_budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    revised_budget: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    paid_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    forecast_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class FundingCommitment(Base):
    __tablename__ = "funding_commitments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    investor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investors.id"), nullable=False)
    commitment_type: Mapped[CommitmentType] = mapped_column(
        Enum(CommitmentType, native_enum=False, length=50),
        nullable=False,
    )
    committed_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    funded_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    remaining_amount: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    commitment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_funding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_funding_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CommitmentStatus] = mapped_column(
        Enum(CommitmentStatus, native_enum=False, length=50),
        nullable=False,
        default=CommitmentStatus.PROPOSED,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PaymentObligation(Base):
    __tablename__ = "payment_obligations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("projects.id"),
        nullable=True,
    )
    investor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investors.id"),
        nullable=True,
    )
    obligation_type: Mapped[ObligationType] = mapped_column(
        Enum(ObligationType, native_enum=False, length=50),
        nullable=False,
    )
    payee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ObligationStatus] = mapped_column(
        Enum(ObligationStatus, native_enum=False, length=50),
        nullable=False,
        default=ObligationStatus.UPCOMING,
    )
    priority: Mapped[ObligationPriority] = mapped_column(
        Enum(ObligationPriority, native_enum=False, length=50),
        nullable=False,
        default=ObligationPriority.NORMAL,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
