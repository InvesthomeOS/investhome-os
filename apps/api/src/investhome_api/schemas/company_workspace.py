"""Company workspace dashboard, activity, and search schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivitySource,
)
from investhome_api.schemas.search import SearchResponse


class CompanyDashboardKpisResponse(BaseModel):
    total_companies: int
    active_companies: int
    branches: int
    employees: int
    departments: int
    teams: int
    pending_tasks: int


class CompanyActivityItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    action: ActivityAction
    entity_type: ActivityEntityType
    entity_id: UUID
    actor_type: ActivityActorType
    actor_user_id: UUID | None
    actor_name: str | None
    source: ActivitySource
    description_key: str
    metadata: dict[str, object] | None = Field(default=None, validation_alias="metadata_json")
    created_at: datetime
    entity_label: str | None = None
    link_module: str | None = None


class CompanyRecentActivityResponse(BaseModel):
    items: list[CompanyActivityItemResponse]
    total: int


class CompanySearchResponse(SearchResponse):
    """Permission-aware company workspace search results."""
