"""Pydantic schemas for AI Index read APIs."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AiDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID | None = None
    project_id: UUID
    drive_file_id: str | None = None
    document_type: str
    category: str | None = None
    language: str | None = None
    title: str
    extracted_text: str | None = None
    summary: str | None = None
    keywords: list[str] | None = None
    builders: list[str] | None = None
    last_indexed_at: datetime | None = None
    checksum: str | None = None
    version: int
    metadata_json: dict | None = None
    is_active: bool
    index_status: str
    skip_reason: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class AiDocumentListResponse(BaseModel):
    items: list[AiDocumentResponse]
    total: int
    project_id: UUID


class AiIndexReindexResponse(BaseModel):
    project_id: UUID
    queued: bool = True
    mode: str = Field(description="sync or async")
    stats: dict[str, int] | None = None
