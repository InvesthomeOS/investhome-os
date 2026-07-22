"""Cross-workspace contracts for Marketing — typed interfaces, no direct imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CrmContactRef:
    """Reference to a CRM contact."""

    contact_id: UUID
    display_name: str
    primary_email: str | None = None


@dataclass(frozen=True)
class CrmCompanyRef:
    """Reference to a CRM/company entity."""

    company_id: UUID
    name: str


@dataclass(frozen=True)
class SalesLeadRef:
    """Reference to canonical Sales lead — no duplicate identity."""

    lead_id: UUID
    status: str
    source: str | None = None


@dataclass(frozen=True)
class SalesOpportunityRef:
    """Reference to Sales opportunity."""

    opportunity_id: UUID
    stage: str
    lead_id: UUID | None = None


@dataclass(frozen=True)
class InvestorProfileRef:
    """Reference to Investor workspace profile."""

    investor_id: UUID
    display_name: str
    kyc_status: str | None = None


@dataclass(frozen=True)
class ProjectRef:
    """Reference to Projects workspace."""

    project_id: UUID
    name: str
    status: str | None = None


@dataclass(frozen=True)
class PropertyRef:
    """Reference to Properties/Inventory."""

    property_id: UUID
    name: str
    availability_status: str | None = None


@dataclass(frozen=True)
class DocumentRef:
    """Reference to Documents workspace — no duplicate storage."""

    document_id: UUID
    title: str
    document_type: str | None = None


@dataclass(frozen=True)
class FinanceBudgetRef:
    """Finance budget/spend contract — architecture placeholder."""

    budget_id: UUID
    planned_amount: float | None
    spent_amount: float | None
    currency: str


@dataclass(frozen=True)
class MarketingTimelineEvent:
    """Event published to CRM activity timeline."""

    event_type: str
    entity_type: str
    entity_id: UUID
    description_key: str
    actor_user_id: UUID | None
    metadata: dict | None = None
    occurred_at: datetime | None = None


@dataclass(frozen=True)
class MarketingNotificationContract:
    """Notification contract for marketing events."""

    notification_type: str
    title_key: str
    body_key: str
    entity_type: str
    entity_id: UUID
    priority: str = "normal"
    metadata: dict | None = None
