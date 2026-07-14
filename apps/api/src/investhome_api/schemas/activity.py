"""Activity log API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivitySource,
)


class ActivityLogResponse(BaseModel):
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
    changed_fields: list[str] | None = None
    previous_values: dict[str, object] | None = None
    new_values: dict[str, object] | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    is_demo: bool
    created_at: datetime
    entity_label: str | None = None
    link_module: str | None = None


class ActivityListResponse(BaseModel):
    items: list[ActivityLogResponse]
    total: int
    page: int
    page_size: int
    pages: int
