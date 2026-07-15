"""Architectural drawing intelligence models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from investhome_api.db.base import Base


class DrawingProcessingStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    CONVERTING = "converting"
    EXTRACTING_GEOMETRY = "extracting_geometry"
    DETECTING_ELEMENTS = "detecting_elements"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    NOT_SUPPORTED = "not_supported"
    PREVIEW_UNAVAILABLE = "preview_unavailable"


class DrawingDiscipline(str, enum.Enum):
    ARCHITECTURAL = "architectural"
    STRUCTURAL = "structural"
    MECHANICAL = "mechanical"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    CIVIL = "civil"
    LANDSCAPE = "landscape"
    INTERIOR = "interior"
    UNKNOWN = "unknown"


class DrawingSheetType(str, enum.Enum):
    FLOOR_PLAN = "floor_plan"
    ELEVATION = "elevation"
    SECTION = "section"
    DETAIL = "detail"
    SITE_PLAN = "site_plan"
    SCHEDULE = "schedule"
    TITLE_BLOCK = "title_block"
    UNKNOWN = "unknown"


class DrawingElementType(str, enum.Enum):
    ROOM = "room"
    WALL = "wall"
    DOOR = "door"
    WINDOW = "window"
    DIMENSION = "dimension"
    UNIT = "unit"
    AREA = "area"
    TITLE_BLOCK = "title_block"
    SCHEDULE = "schedule"


class ConfidenceLevel(str, enum.Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class UnitProposalStatus(str, enum.Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class DrawingAnalysis(Base):
    __tablename__ = "drawing_analyses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    document_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="uploaded")
    source_format: Mapped[str | None] = mapped_column(String(20), nullable=True)
    conversion_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preview_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preview_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geometry_storage_key: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    geometry_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(30), nullable=True)
    discipline_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    drawing_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    drawing_type_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scale_detected: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scale_confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scale_corrected: Mapped[str | None] = mapped_column(String(120), nullable=True)
    scale_corrected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    scale_corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sheet_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    title_block_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    schedules_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_summary_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(nullable=False, default=0)
    processing_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    document: Mapped["Document"] = relationship("Document", back_populates="drawing_analysis")
    sheets: Mapped[list["DrawingSheet"]] = relationship(
        "DrawingSheet",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    elements: Mapped[list["DrawingElement"]] = relationship(
        "DrawingElement",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    annotations: Mapped[list["DrawingAnnotation"]] = relationship(
        "DrawingAnnotation",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    unit_proposals: Mapped[list["DrawingUnitProposal"]] = relationship(
        "DrawingUnitProposal",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_drawing_analyses_document_version_id", "document_version_id"),
        Index("ix_drawing_analyses_processing_status", "processing_status"),
        Index("ix_drawing_analyses_discipline", "discipline"),
    )


class DrawingSheet(Base):
    __tablename__ = "drawing_sheets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("drawing_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    sheet_index: Mapped[int] = mapped_column(nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sheet_number: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sheet_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    width: Mapped[float | None] = mapped_column(nullable=True)
    height: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    analysis: Mapped["DrawingAnalysis"] = relationship("DrawingAnalysis", back_populates="sheets")

    __table_args__ = (
        Index("ix_drawing_sheets_analysis_id", "analysis_id"),
    )


class DrawingElement(Base):
    __tablename__ = "drawing_elements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("drawing_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    sheet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("drawing_sheets.id", ondelete="SET NULL"),
        nullable=True,
    )
    element_type: Mapped[str] = mapped_column(String(30), nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    numeric_value: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    geometry_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    analysis: Mapped["DrawingAnalysis"] = relationship("DrawingAnalysis", back_populates="elements")
    sheet: Mapped["DrawingSheet | None"] = relationship("DrawingSheet")

    __table_args__ = (
        Index("ix_drawing_elements_analysis_id", "analysis_id"),
        Index("ix_drawing_elements_element_type", "element_type"),
        Index("ix_drawing_elements_confidence", "confidence"),
    )


class DrawingAnnotation(Base):
    __tablename__ = "drawing_annotations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("drawing_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    sheet_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("drawing_sheets.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    geometry_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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

    analysis: Mapped["DrawingAnalysis"] = relationship("DrawingAnalysis", back_populates="annotations")

    __table_args__ = (
        Index("ix_drawing_annotations_analysis_id", "analysis_id"),
    )


class DrawingUnitProposal(Base):
    __tablename__ = "drawing_unit_proposals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("drawing_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    element_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("drawing_elements.id", ondelete="SET NULL"),
        nullable=True,
    )
    unit_label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    area_sqm: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="proposed")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_unit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    analysis: Mapped["DrawingAnalysis"] = relationship("DrawingAnalysis", back_populates="unit_proposals")

    __table_args__ = (
        Index("ix_drawing_unit_proposals_analysis_id", "analysis_id"),
        Index("ix_drawing_unit_proposals_status", "status"),
    )


class DrawingVersionComparison(Base):
    __tablename__ = "drawing_version_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_document_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    from_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    to_version_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    changes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    __table_args__ = (
        Index("ix_drawing_version_comparisons_parent", "parent_document_id"),
        Index("ix_drawing_version_comparisons_versions", "from_version_id", "to_version_id"),
    )


# Avoid circular import at runtime
from investhome_api.models.document import Document  # noqa: E402, F401
