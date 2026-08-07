"""Construction project ↔ Google Drive folder mapping.

Kept as a dedicated table (not columns on ``projects``) so Drive sync concerns
stay out of the core construction Project model while still linking by
``projects.id`` — the same FK Media Library already uses via ``linked_project_id``.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class DriveSyncStatus(str, enum.Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ProjectDriveMapping(Base):
    __tablename__ = "project_drive_mappings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    drive_folder_id: Mapped[str] = mapped_column(String(128), nullable=False)
    drive_sync_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_drive_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DriveSyncStatus.IDLE.value
    )
    last_sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sync_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    force_full_sync: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Folder id observed at last successful sync — detects mapping changes.
    mapped_folder_id_at_sync: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_project_drive_mappings_drive_folder_id", "drive_folder_id"),
        Index("ix_project_drive_mappings_last_sync_status", "last_sync_status"),
    )


class GoogleDriveSyncCursor(Base):
    """Global Google Drive Changes API page token (one row per credential scope)."""

    __tablename__ = "google_drive_sync_cursors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    cursor_key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    start_page_token: Mapped[str | None] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


# Canonical key for the OAuth user / Drive.readonly scope used by this app.
GLOBAL_DRIVE_CURSOR_KEY = "default"
