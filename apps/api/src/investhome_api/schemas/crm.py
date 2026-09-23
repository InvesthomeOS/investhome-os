"""CRM workspace Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.crm_contact import CrmContactType
from investhome_api.schemas.crm_contacts import CrmContactListResponse, CrmContactSummary


class CrmActivitySummary(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID
    description_key: str
    actor_name: str | None = None
    created_at: datetime


class CrmTaskSummary(BaseModel):
    id: UUID
    title: str
    status: str
    due_at: datetime | None = None
    priority: str | None = None


class CrmMeetingSummary(BaseModel):
    id: UUID
    title: str
    start_at: datetime | None = None
    status: str | None = None


class CrmRelationshipAlert(BaseModel):
    contact_id: UUID
    display_name: str
    alert_type: str
    message_key: str
    severity: str = "info"


class CrmPinnedCompanySummary(BaseModel):
    contact_id: UUID
    display_name: str
    organization_name: str | None = None
    contact_type: CrmContactType


class CrmCommunicationSummary(BaseModel):
    total_contacts: int = 0
    contacts_with_email: int = 0
    contacts_with_phone: int = 0
    favorites_count: int = 0
    recent_interactions_count: int = 0


class CrmDashboardCount(BaseModel):
    key: str
    label: str
    count: int
    href: str | None = None


class CrmDashboardKpis(BaseModel):
    current_purchases: int = 0
    investors: int = 0
    active_tasks: int = 0
    open_leads: int = 0
    documents_review: int = 0
    matches_pending: int = 0


class CrmDashboardPurchaseScope(BaseModel):
    current: int = 0
    historical: int = 0
    total: int = 0


class CrmDashboardCharts(BaseModel):
    purchases_by_project: list[CrmDashboardCount] = Field(default_factory=list)
    purchases_by_month: list[CrmDashboardCount] = Field(default_factory=list)
    task_status: list[CrmDashboardCount] = Field(default_factory=list)
    communication_channels: list[CrmDashboardCount] = Field(default_factory=list)
    lead_pipeline: list[CrmDashboardCount] = Field(default_factory=list)
    document_status: list[CrmDashboardCount] = Field(default_factory=list)


class CrmDashboardFeedItem(BaseModel):
    id: str
    title: str
    meta: str | None = None
    href: str
    occurred_at: datetime | None = None
    kind: str


class CrmDashboardPanels(BaseModel):
    recent_activities: list[CrmDashboardFeedItem] = Field(default_factory=list)
    upcoming_tasks: list[CrmDashboardFeedItem] = Field(default_factory=list)
    recent_documents: list[CrmDashboardFeedItem] = Field(default_factory=list)
    review_queue: list[CrmDashboardFeedItem] = Field(default_factory=list)
    recent_leads: list[CrmDashboardFeedItem] = Field(default_factory=list)


class CrmDashboardResponse(BaseModel):
    recent_contacts: list[CrmContactSummary] = Field(default_factory=list)
    recent_activities: list[CrmActivitySummary] = Field(default_factory=list)
    upcoming_tasks: list[CrmTaskSummary] = Field(default_factory=list)
    todays_meetings: list[CrmMeetingSummary] = Field(default_factory=list)
    recently_updated: list[CrmContactSummary] = Field(default_factory=list)
    relationship_alerts: list[CrmRelationshipAlert] = Field(default_factory=list)
    favorite_contacts: list[CrmContactSummary] = Field(default_factory=list)
    pinned_companies: list[CrmPinnedCompanySummary] = Field(default_factory=list)
    communication_summary: CrmCommunicationSummary = Field(default_factory=CrmCommunicationSummary)
    kpis: CrmDashboardKpis = Field(default_factory=CrmDashboardKpis)
    purchase_scope: CrmDashboardPurchaseScope = Field(default_factory=CrmDashboardPurchaseScope)
    charts: CrmDashboardCharts = Field(default_factory=CrmDashboardCharts)
    panels: CrmDashboardPanels = Field(default_factory=CrmDashboardPanels)


class CrmTagItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    status: str = "active"
    color: str | None = None
    usage_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CrmTagStats(BaseModel):
    total_tags: int = 0
    tagged_people: int = 0
    untagged_people: int = 0


class CrmTagListResponse(BaseModel):
    items: list[CrmTagItem] = Field(default_factory=list)
    stats: CrmTagStats = Field(default_factory=CrmTagStats)


class CrmTagContactRef(BaseModel):
    id: UUID
    display_name: str


class CrmTagDetail(CrmTagItem):
    people: list[CrmTagContactRef] = Field(default_factory=list)


class CrmTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None
    status: str = "active"


class CrmTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    status: str | None = None


class CrmTagAssignRequest(BaseModel):
    tag_id: UUID


class CrmTagStatusRequest(BaseModel):
    status: str
