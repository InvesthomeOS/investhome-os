import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class InvestorType(str, enum.Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"
    FAMILY_OFFICE = "family_office"
    FUND = "fund"
    INSTITUTIONAL = "institutional"
    BROKER = "broker"
    REFERRAL_PARTNER = "referral_partner"


class InvestorStatus(str, enum.Enum):
    PROSPECT = "prospect"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    INVESTED = "invested"
    FOLLOW_UP = "follow_up"
    DORMANT = "dormant"
    REJECTED = "rejected"


class InvestmentModel(str, enum.Enum):
    DEVELOPMENT_EQUITY = "development_equity"
    RENTAL_INCOME = "rental_income"
    FIX_AND_FLIP = "fix_and_flip"
    DEBT_INVESTMENT = "debt_investment"
    BULK_PURCHASE = "bulk_purchase"
    JOINT_VENTURE = "joint_venture"
    OTHER = "other"


class AccreditationStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    SELF_CERTIFIED = "self_certified"
    VERIFIED = "verified"
    NOT_ACCREDITED = "not_accredited"


class RiskProfile(str, enum.Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    GROWTH = "growth"
    AGGRESSIVE = "aggressive"


class Investor(Base):
    __tablename__ = "investors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    investor_type: Mapped[InvestorType] = mapped_column(
        Enum(InvestorType, native_enum=False, length=50),
        nullable=False,
        default=InvestorType.INDIVIDUAL,
    )
    accreditation_status: Mapped[AccreditationStatus] = mapped_column(
        Enum(AccreditationStatus, native_enum=False, length=50),
        nullable=False,
        default=AccreditationStatus.UNKNOWN,
    )
    preferred_investment_model: Mapped[InvestmentModel | None] = mapped_column(
        Enum(InvestmentModel, native_enum=False, length=50),
        nullable=True,
    )
    investment_capacity: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    minimum_ticket: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    maximum_ticket: Mapped[Decimal | None] = mapped_column(Numeric(16, 2), nullable=True)
    preferred_markets: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_projects: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_profile: Mapped[RiskProfile | None] = mapped_column(
        Enum(RiskProfile, native_enum=False, length=50),
        nullable=True,
    )
    status: Mapped[InvestorStatus] = mapped_column(
        Enum(InvestorStatus, native_enum=False, length=50),
        nullable=False,
        default=InvestorStatus.PROSPECT,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_contact_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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
