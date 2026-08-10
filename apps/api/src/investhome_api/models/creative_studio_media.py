"""Creative Studio Media Library models — folders and media assets."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class MediaAssetSourceType(str, enum.Enum):
    UPLOAD = "upload"
    GOOGLE_DRIVE = "google_drive"


class MediaAssetSyncStatus(str, enum.Enum):
    ACTIVE = "active"
    CHANGED = "changed"
    MISSING = "missing"
    ERROR = "error"


class CreativeStudioMediaFolder(Base):
    __tablename__ = "creative_studio_media_folders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("creative_studio_media_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    # Google Drive hierarchy (nullable — manual upload folders omit these)
    external_folder_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    linked_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent: Mapped["CreativeStudioMediaFolder | None"] = relationship(
        "CreativeStudioMediaFolder",
        remote_side="CreativeStudioMediaFolder.id",
        back_populates="children",
    )
    children: Mapped[list["CreativeStudioMediaFolder"]] = relationship(
        "CreativeStudioMediaFolder",
        back_populates="parent",
    )
    assets: Mapped[list["CreativeStudioMediaAsset"]] = relationship(
        "CreativeStudioMediaAsset",
        back_populates="folder",
    )

    __table_args__ = (
        Index("ix_cs_media_folders_parent_id", "parent_id"),
        Index("ix_cs_media_folders_company_id", "company_id"),
        Index("ix_cs_media_folders_archived_at", "archived_at"),
        Index("ix_cs_media_folders_external_folder_id", "external_folder_id", unique=True),
        Index("ix_cs_media_folders_external_parent_id", "external_parent_id"),
        Index("ix_cs_media_folders_linked_project_id", "linked_project_id"),
    )


class CreativeStudioMediaAsset(Base):
    __tablename__ = "creative_studio_media_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(20), nullable=False, default="local")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("creative_studio_media_folders.id", ondelete="SET NULL"),
        nullable=True,
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
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

    # Google Drive sync fields (nullable — existing uploads untouched)
    source_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    external_file_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_parent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    external_modified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sync_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    folder_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    possible_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    web_view_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    external_thumbnail_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    drive_meta_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    folder: Mapped["CreativeStudioMediaFolder | None"] = relationship(
        "CreativeStudioMediaFolder",
        back_populates="assets",
    )

    __table_args__ = (
        Index("ix_cs_media_assets_folder_id", "folder_id"),
        Index("ix_cs_media_assets_company_id", "company_id"),
        Index("ix_cs_media_assets_linked_project_id", "linked_project_id"),
        Index("ix_cs_media_assets_uploaded_by_user_id", "uploaded_by_user_id"),
        Index("ix_cs_media_assets_archived_at", "archived_at"),
        Index("ix_cs_media_assets_filename", "filename"),
        Index("ix_cs_media_assets_storage_key", "storage_key"),
        Index("ix_cs_media_assets_source_type", "source_type"),
        Index("ix_cs_media_assets_external_file_id", "external_file_id"),
        Index("ix_cs_media_assets_sync_status", "sync_status"),
    )
