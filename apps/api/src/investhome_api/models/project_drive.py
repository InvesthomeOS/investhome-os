"""Construction project ↔ Google Drive folder mapping.

Kept as a dedicated table (not columns on ``projects``) so Drive sync concerns
stay out of the core construction Project model while still linking by
``projects.id`` — the same FK Media Library already uses via ``linked_project_id``.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


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
    )
