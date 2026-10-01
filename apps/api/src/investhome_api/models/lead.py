import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class LeadStatus(str, enum.Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    FOLLOW_UP = "Follow Up"
    QUALIFIED = "Qualified"
    MEETING_SCHEDULED = "Meeting Scheduled"
    PROPOSAL_SENT = "Proposal Sent"
    NEGOTIATION = "Negotiation"
    WON = "Won"
    LOST = "Lost"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=50),
        nullable=False,
        default=LeadStatus.NEW,
    )
    assigned_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    assigned_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    preferred_market: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cached_lead_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    interested_project: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ingest_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ok")
    converted_contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("crm_contacts.id", ondelete="SET NULL", use_alter=True, name="fk_leads_converted_contact_id"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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
