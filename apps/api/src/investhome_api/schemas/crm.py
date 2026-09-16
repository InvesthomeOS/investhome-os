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


class CrmTagItem(BaseModel):
    id: UUID
    name: str
    color: str | None = None
    usage_count: int = 0


class CrmTagListResponse(BaseModel):
    items: list[CrmTagItem] = Field(default_factory=list)
