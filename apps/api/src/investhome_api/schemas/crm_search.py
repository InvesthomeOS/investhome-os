"""CRM search API schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class CrmSearchEntityType(str, Enum):
    CONTACT = "crm_contact"
    COMPANY = "crm_company"
    RELATIONSHIP = "crm_relationship"
    ACTIVITY = "crm_activity"
    COMMUNICATION = "crm_communication"
    TASK = "crm_task"
    OPPORTUNITY = "sales_opportunity"
    INVESTOR = "investor"
    PROJECT = "project"
    PROPERTY = "inventory_asset"
    TRANSACTION = "financial_transaction"
    DOCUMENT = "document"
    FILE = "file"
    ACTION = "action"


class CrmSearchSortField(str, Enum):
    RELEVANCE = "relevance"
    RECENCY = "recency"
    TITLE = "title"
    UPDATED_AT = "updated_at"
    CREATED_AT = "created_at"


class CrmSearchFilterGroup(BaseModel):
    logic: str = "and"
    conditions: list[CrmSearchFilterCondition] = Field(default_factory=list)
    groups: list[CrmSearchFilterGroup] = Field(default_factory=list)


class CrmSearchFilterCondition(BaseModel):
    field: str
    operator: str
    value: str | int | float | bool | list[str] | None = None


CrmSearchFilterGroup.model_rebuild()


class CrmSearchDateRange(BaseModel):
    from_date: datetime | None = None
    to_date: datetime | None = None
    relative: str | None = None


class CrmSearchQueryRequest(BaseModel):
    query: str = ""
    entity_types: list[str] | None = None
    filters: CrmSearchFilterGroup | None = None
    sort: CrmSearchSortField = CrmSearchSortField.RELEVANCE
    sort_dir: str = "desc"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    cursor: str | None = None
    include_archived: bool = False
    include_restricted: bool = False
    exact_match: bool = False
    fuzzy_match: bool = True
    semantic_search: bool = False
    date_range: CrmSearchDateRange | None = None
    owner_ids: list[UUID] | None = None
    team_ids: list[UUID] | None = None
    tags: list[str] | None = None
    statuses: list[str] | None = None
    locations: list[str] | None = None
    related_entity_ids: list[UUID] | None = None
    saved_search_id: UUID | None = None
    grouping: str | None = None


class CrmSearchHighlightField(BaseModel):
    field: str
    snippet: str
    highlighted_html: str | None = None


class CrmSearchResultItem(BaseModel):
    id: UUID
    entity_type: str
    entity_id: UUID
    title: str
    subtitle: str | None = None
    description: str | None = None
    preview: str | None = None
    highlighted_fields: list[CrmSearchHighlightField] = Field(default_factory=list)
    matched_fields: list[str] = Field(default_factory=list)
    score: float = 0.0
    relevance_score: float = 0.0
    recency_score: float = 0.0
    relationship_score: float = 0.0
    entity_status: str | None = None
    owner_id: UUID | None = None
    owner_name: str | None = None
    tags: list[str] = Field(default_factory=list)
    url: str
    icon: str | None = None
    thumbnail: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_activity_at: datetime | None = None
    permission_level: str = "read"
    metadata: dict = Field(default_factory=dict)


class CrmSearchResultGroup(BaseModel):
    entity_type: str
    label_key: str
    items: list[CrmSearchResultItem]
    total: int


class CrmSearchResponse(BaseModel):
    query: str
    parsed_query: dict | None = None
    groups: list[CrmSearchResultGroup] = Field(default_factory=list)
    items: list[CrmSearchResultItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 25
    has_more: bool = False
    next_cursor: str | None = None
    took_ms: int = 0
    suggestions: list[str] = Field(default_factory=list)
    did_you_mean: str | None = None
    explanation: str | None = None
    active_filters: list[str] = Field(default_factory=list)


class CrmSearchSuggestionItem(BaseModel):
    text: str
    type: str
    entity_type: str | None = None


class CrmSearchSuggestionsResponse(BaseModel):
    query: str
    suggestions: list[CrmSearchSuggestionItem] = Field(default_factory=list)


class CrmParseQueryRequest(BaseModel):
    query: str


class CrmParseQueryResponse(BaseModel):
    query: str
    parsed: dict
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CrmNaturalLanguageRequest(BaseModel):
    query: str


class CrmNaturalLanguageResponse(BaseModel):
    query: str
    interpreted_filters: dict | None = None
    available: bool = False
    message: str | None = None


class CrmRecentSearchResponse(BaseModel):
    id: UUID
    query: str
    filters: dict | None = None
    entity_types: list[str] | None = None
    result_count: int
    opened_result_id: UUID | None = None
    opened_entity_type: str | None = None
    searched_at: datetime


class CrmRecentSearchCreate(BaseModel):
    query: str
    filters: dict | None = None
    entity_types: list[str] | None = None
    result_count: int = 0
    opened_result_id: UUID | None = None
    opened_entity_type: str | None = None


class CrmSavedSearchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    query: str | None = None
    filters: dict | None = None
    entity_types: list[str] | None = None
    sort: dict | None = None
    grouping: str | None = None
    visible_fields: list[str] | None = None
    view_mode: str = "list"
    visibility: str = "private"
    shared_with: list[UUID] | None = None
    notification_settings: dict | None = None


class CrmSavedSearchUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    query: str | None = None
    filters: dict | None = None
    entity_types: list[str] | None = None
    sort: dict | None = None
    grouping: str | None = None
    visible_fields: list[str] | None = None
    view_mode: str | None = None
    visibility: str | None = None
    shared_with: list[UUID] | None = None
    notification_settings: dict | None = None


class CrmSavedSearchResponse(BaseModel):
    id: UUID
    owner_id: UUID
    name: str
    description: str | None = None
    query: str | None = None
    filters: dict | None = None
    entity_types: list[str] | None = None
    sort: dict | None = None
    grouping: str | None = None
    visible_fields: list[str] | None = None
    view_mode: str
    visibility: str
    shared_with: list[UUID] | None = None
    notification_settings: dict | None = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime


class CrmSearchExportRequest(BaseModel):
    format: str = "csv"
    result_ids: list[UUID] | None = None
    visible_fields: list[str] | None = None
    query: str | None = None
    filters: dict | None = None


class CrmSearchExportResponse(BaseModel):
    download_url: str | None = None
    content: str | None = None
    format: str
    row_count: int = 0


class CrmEntityPickerRequest(BaseModel):
    query: str = ""
    entity_types: list[str] | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=50)
    exclude_ids: list[UUID] | None = None


class CrmEntityPickerResponse(BaseModel):
    items: list[CrmSearchResultItem]
    total: int
    page: int
    page_size: int
    has_more: bool


class CrmDuplicateDiscoveryRequest(BaseModel):
    entity_type: str
    entity_id: UUID | None = None
    display_name: str | None = None
    email: str | None = None
    phone: str | None = None


class CrmDuplicateDiscoveryMatch(BaseModel):
    entity_type: str
    entity_id: UUID
    title: str
    match_reason: str
    score: float


class CrmDuplicateDiscoveryResponse(BaseModel):
    matches: list[CrmDuplicateDiscoveryMatch] = Field(default_factory=list)


class CrmSearchAnalyticsSummary(BaseModel):
    total_searches: int = 0
    zero_result_searches: int = 0
    avg_latency_ms: float = 0.0
    top_queries: list[str] = Field(default_factory=list)
    filter_usage: dict[str, int] = Field(default_factory=dict)
