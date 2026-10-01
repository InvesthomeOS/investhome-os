"""CRM document hub feed — live Bitrix/CRM documents only."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CrmDocumentFeedStats(BaseModel):
    total: int = 0
    person: int = 0
    purchase: int = 0
    hidden: int = 0
    unresolved: int = 0


class CrmDocumentFeedItem(BaseModel):
    id: UUID
    source_key: str
    filename: str
    category: str
    category_label: str
    mime_type: str | None = None
    file_size: int = 0
    file_kind: str | None = None
    source: str | None = None
    source_type: str | None = None
    occurred_at: datetime | None = None
    hidden: bool = False
    scope: str
    status: str
    contact_id: UUID | None = None
    contact_name: str | None = None
    agreement_id: UUID | None = None
    project_group: str | None = None
    project_label: str | None = None
    unit_number: str | None = None
    current_unit: str | None = None
    historical_unit: str | None = None
    project_unit: str | None = None
    checksum: str | None = None
    bitrix_file_id: str | None = None
    previewable: bool = False
    extra_contact_count: int = 0


class CrmDocumentFeedResponse(BaseModel):
    items: list[CrmDocumentFeedItem]
    total: int
    page: int
    page_size: int
    pages: int
    stats: CrmDocumentFeedStats
    request_id: str = ""


class CrmDocumentHubVisibilityRequest(BaseModel):
    hidden: bool


class CrmDocumentHubVisibilityResponse(BaseModel):
    id: UUID
    hidden: bool
    updated_links: int = 0
    request_id: str = Field(default="")
