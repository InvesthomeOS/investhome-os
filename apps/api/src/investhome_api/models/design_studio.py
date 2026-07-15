"""Visual Design Studio models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class DesignType(str, enum.Enum):
    COLORED_FLOOR_PLAN = "colored_floor_plan"
    MARKETING_FLOOR_PLAN = "marketing_floor_plan"
    FURNITURE_LAYOUT = "furniture_layout"
    MATERIAL_PLAN = "material_plan"
    INTERIOR_CONCEPT = "interior_concept"
    EXTERIOR_CONCEPT = "exterior_concept"
    OTHER = "other"


class DesignStatus(str, enum.Enum):
    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    REVISION_REQUESTED = "revision_requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    ARCHIVED = "archived"


class FurnitureType(str, enum.Enum):
    SOFA = "sofa"
    ARMCHAIR = "armchair"
    COFFEE_TABLE = "coffee_table"
    DINING_TABLE = "dining_table"
    DINING_CHAIR = "dining_chair"
    BED = "bed"
    BEDSIDE_TABLE = "bedside_table"
    WARDROBE = "wardrobe"
    DESK = "desk"
    MEDIA_UNIT = "media_unit"
    RUG = "rug"
    KITCHEN_ISLAND = "kitchen_island"
    STOOL = "stool"
    VANITY = "vanity"
    BATHTUB = "bathtub"
    SHOWER = "shower"
    TOILET = "toilet"
    OTHER = "other"


class RoomType(str, enum.Enum):
    LIVING_ROOM = "living_room"
    BEDROOM = "bedroom"
    KITCHEN = "kitchen"
    DINING_ROOM = "dining_room"
    BATHROOM = "bathroom"
    OFFICE = "office"
    HALLWAY = "hallway"
    OTHER = "other"


class StylePreset(Base):
    __tablename__ = "style_presets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color_palette: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    material_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    furniture_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_system_preset: Mapped[bool] = mapped_column(nullable=False, default=False)
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

    __table_args__ = (
        Index("ix_style_presets_code", "code"),
        Index("ix_style_presets_is_system", "is_system_preset"),
    )


class MaterialPackage(Base):
    __tablename__ = "material_packages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    flooring: Mapped[str | None] = mapped_column(String(120), nullable=True)
    wall_finish: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ceiling_finish: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cabinetry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    countertop: Mapped[str | None] = mapped_column(String(120), nullable=True)
    backsplash: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bathroom_finish: Mapped[str | None] = mapped_column(String(120), nullable=True)
    metal_finish: Mapped[str | None] = mapped_column(String(120), nullable=True)
    door_finish: Mapped[str | None] = mapped_column(String(120), nullable=True)
    color_palette: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reference_document_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
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

    __table_args__ = (Index("ix_material_packages_name", "name"),)


class FurnitureItem(Base):
    __tablename__ = "furniture_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    room_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    furniture_type: Mapped[str] = mapped_column(String(40), nullable=False)
    width: Mapped[float | None] = mapped_column(nullable=True)
    depth: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    measurement_unit: Mapped[str] = mapped_column(String(10), nullable=False, default="cm")
    default_rotation: Mapped[float] = mapped_column(nullable=False, default=0.0)
    icon_or_preview: Mapped[str | None] = mapped_column(String(500), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    is_system_item: Mapped[bool] = mapped_column(nullable=False, default=True)
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
        Index("ix_furniture_items_code", "code"),
        Index("ix_furniture_items_furniture_type", "furniture_type"),
    )


class DesignProject(Base):
    __tablename__ = "design_projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    drawing_analysis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("drawing_analyses.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    design_type: Mapped[DesignType] = mapped_column(
        Enum(DesignType, native_enum=False, length=40),
        nullable=False,
        default=DesignType.COLORED_FLOOR_PLAN,
    )
    status: Mapped[DesignStatus] = mapped_column(
        Enum(DesignStatus, native_enum=False, length=30),
        nullable=False,
        default=DesignStatus.DRAFT,
    )
    source_geometry_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
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
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    versions: Mapped[list["DesignVersion"]] = relationship(
        "DesignVersion",
        back_populates="design_project",
        cascade="all, delete-orphan",
        order_by="DesignVersion.version_number",
    )

    __table_args__ = (
        Index("ix_design_projects_project_id", "project_id"),
        Index("ix_design_projects_document_id", "document_id"),
        Index("ix_design_projects_status", "status"),
        Index("ix_design_projects_design_type", "design_type"),
    )


class DesignVersion(Base):
    __tablename__ = "design_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    design_project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("design_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_geometry_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    design_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_location: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    thumbnail_location: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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

    design_project: Mapped["DesignProject"] = relationship("DesignProject", back_populates="versions")

    __table_args__ = (
        Index("ix_design_versions_design_project_id", "design_project_id"),
        Index(
            "uq_design_versions_project_number",
            "design_project_id",
            "version_number",
            unique=True,
        ),
    )
