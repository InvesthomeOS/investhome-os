"""Creative Studio Media Library API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# --- Folders ---


class CreativeStudioMediaFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    parent_id: UUID | None = None
    company_id: UUID | None = None


class CreativeStudioMediaFolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    parent_id: UUID | None
    company_id: UUID | None
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class CreativeStudioMediaFolderListResponse(BaseModel):
    items: list[CreativeStudioMediaFolderResponse]
    total: int


# --- Assets ---


class CreativeStudioMediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    content_type: str
    file_size: int
    width: int | None
    height: int | None
    storage_provider: str
    storage_key: str
    thumbnail_storage_key: str | None
    # Auth-gated content path (mirrors Document Center download pattern — no public CDN URL)
    url: str
    thumbnail_url: str | None = None
    folder_id: UUID | None
    tags: list[str] | None = None
    company_id: UUID | None
    linked_project_id: UUID | None
    uploaded_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    # Thumbnail pipeline stub — null key means not generated yet
    thumbnail_pending: bool = True


class CreativeStudioMediaAssetListResponse(BaseModel):
    items: list[CreativeStudioMediaAssetResponse]
    total: int
    page: int = 1
    page_size: int = 50


class CreativeStudioMediaAssetTagsUpdate(BaseModel):
    tags: list[str] = Field(default_factory=list)
