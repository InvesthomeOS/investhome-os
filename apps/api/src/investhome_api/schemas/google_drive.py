"""Schemas for Google Drive project mapping and sync."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectDriveMappingUpsert(BaseModel):
    drive_folder_id: str = Field(min_length=1, max_length=128)
    drive_sync_enabled: bool = True


class ProjectDriveMappingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    drive_folder_id: str
    drive_sync_enabled: bool
    last_drive_sync_at: datetime | None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class DriveSyncDuplicateItem(BaseModel):
    drive_file_id: str
    existing_asset_id: str
    checksum: str
    filename: str


class DriveSyncErrorItem(BaseModel):
    path: str
    code: str
    message: str


class DriveSyncResponse(BaseModel):
    scanned: int
    created: int
    updated: int
    unchanged: int
    missing: int
    skipped: int = 0
    possible_duplicates: list[DriveSyncDuplicateItem] = Field(default_factory=list)
    errors: list[DriveSyncErrorItem] = Field(default_factory=list)
    dry_run: bool
    warnings: list[str] = Field(default_factory=list)
