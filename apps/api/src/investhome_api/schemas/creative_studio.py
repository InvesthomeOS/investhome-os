"""Creative Studio API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.creative_studio import (
    CreativeStudioDocumentStatus,
    CreativeStudioDocumentType,
    CreativeStudioProjectStatus,
)


# --- Projects ---


class CreativeStudioProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: CreativeStudioProjectStatus = CreativeStudioProjectStatus.ACTIVE
    company_id: UUID | None = None
    linked_project_id: UUID | None = None


class CreativeStudioProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    status: CreativeStudioProjectStatus
    company_id: UUID | None
    linked_project_id: UUID | None
    owner_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    document_count: int = 0


class CreativeStudioProjectListResponse(BaseModel):
    items: list[CreativeStudioProjectResponse]
    total: int


# --- Documents ---


class CreativeStudioDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    document_type: CreativeStudioDocumentType
    status: CreativeStudioDocumentStatus = CreativeStudioDocumentStatus.DRAFT
    language: str | None = Field(default=None, max_length=10)
    thumbnail_url: str | None = Field(default=None, max_length=1000)
    draft_body_json: dict[str, Any] | None = None


class CreativeStudioDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    document_type: CreativeStudioDocumentType
    status: CreativeStudioDocumentStatus
    language: str | None
    thumbnail_url: str | None
    draft_body_json: dict[str, Any] | None = None
    draft_updated_at: datetime | None
    draft_updated_by_user_id: UUID | None
    current_version_id: UUID | None
    created_by_user_id: UUID | None
    updated_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None
    version_count: int = 0


class CreativeStudioDocumentListResponse(BaseModel):
    items: list[CreativeStudioDocumentResponse]
    total: int


class CreativeStudioDraftUpdate(BaseModel):
    draft_body_json: dict[str, Any]


# --- Versions ---


class CreativeStudioVersionCreate(BaseModel):
    body_json: dict[str, Any] | None = None
    label: str | None = Field(default=None, max_length=120)
    summary: str | None = None


class CreativeStudioVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    version_number: int
    label: str | None
    summary: str | None
    body_json: dict[str, Any] | None = None
    created_by_user_id: UUID | None
    created_at: datetime


class CreativeStudioVersionListResponse(BaseModel):
    items: list[CreativeStudioVersionResponse]
    total: int


class CreativeStudioRestoreRequest(BaseModel):
    create_version: bool = True
    label: str | None = Field(default=None, max_length=120)
    summary: str | None = None


class CreativeStudioRestoreResponse(BaseModel):
    document: CreativeStudioDocumentResponse
    new_version: CreativeStudioVersionResponse | None = None
