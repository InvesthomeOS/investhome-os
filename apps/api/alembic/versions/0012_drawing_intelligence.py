"""Architectural drawing intelligence tables.

Revision ID: 0012_drawing_intelligence
Revises: 0011_document_intelligence
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_drawing_intelligence"
down_revision: str | None = "0011_document_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "drawing_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("source_format", sa.String(length=20), nullable=True),
        sa.Column("conversion_method", sa.String(length=50), nullable=True),
        sa.Column("preview_status", sa.String(length=30), nullable=True),
        sa.Column("preview_storage_key", sa.String(length=1000), nullable=True),
        sa.Column("geometry_storage_key", sa.String(length=1000), nullable=True),
        sa.Column("geometry_size_bytes", sa.Integer(), nullable=True),
        sa.Column("discipline", sa.String(length=30), nullable=True),
        sa.Column("discipline_confidence", sa.String(length=20), nullable=True),
        sa.Column("drawing_type", sa.String(length=30), nullable=True),
        sa.Column("drawing_type_confidence", sa.String(length=20), nullable=True),
        sa.Column("scale_detected", sa.String(length=120), nullable=True),
        sa.Column("scale_confidence", sa.String(length=20), nullable=True),
        sa.Column("scale_corrected", sa.String(length=120), nullable=True),
        sa.Column("scale_corrected_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("scale_corrected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sheet_count", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_en", sa.Text(), nullable=True),
        sa.Column("title_block_json", sa.Text(), nullable=True),
        sa.Column("schedules_json", sa.Text(), nullable=True),
        sa.Column("comparison_summary_json", sa.Text(), nullable=True),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id"),
    )
    op.create_index("ix_drawing_analyses_document_version_id", "drawing_analyses", ["document_version_id"])
    op.create_index("ix_drawing_analyses_processing_status", "drawing_analyses", ["processing_status"])
    op.create_index("ix_drawing_analyses_discipline", "drawing_analyses", ["discipline"])

    op.create_table(
        "drawing_sheets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_index", sa.Integer(), nullable=False),
        sa.Column("sheet_name", sa.String(length=200), nullable=True),
        sa.Column("sheet_number", sa.String(length=80), nullable=True),
        sa.Column("sheet_type", sa.String(length=30), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=True),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["drawing_analyses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_sheets_analysis_id", "drawing_sheets", ["analysis_id"])

    op.create_table(
        "drawing_elements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_id", sa.Uuid(), nullable=True),
        sa.Column("element_type", sa.String(length=30), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("value_text", sa.String(length=500), nullable=True),
        sa.Column("numeric_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("geometry_json", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["drawing_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["drawing_sheets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_elements_analysis_id", "drawing_elements", ["analysis_id"])
    op.create_index("ix_drawing_elements_element_type", "drawing_elements", ["element_type"])
    op.create_index("ix_drawing_elements_confidence", "drawing_elements", ["confidence"])

    op.create_table(
        "drawing_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("sheet_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("geometry_json", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=20), nullable=True),
        sa.Column("is_resolved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["drawing_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sheet_id"], ["drawing_sheets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_annotations_analysis_id", "drawing_annotations", ["analysis_id"])

    op.create_table(
        "drawing_unit_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("element_id", sa.Uuid(), nullable=True),
        sa.Column("unit_label", sa.String(length=120), nullable=False),
        sa.Column("unit_type", sa.String(length=80), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_unit_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["drawing_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["element_id"], ["drawing_elements.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_unit_proposals_analysis_id", "drawing_unit_proposals", ["analysis_id"])
    op.create_index("ix_drawing_unit_proposals_status", "drawing_unit_proposals", ["status"])

    op.create_table(
        "drawing_version_comparisons",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("parent_document_id", sa.Uuid(), nullable=False),
        sa.Column("from_version_id", sa.Uuid(), nullable=False),
        sa.Column("to_version_id", sa.Uuid(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("summary_en", sa.Text(), nullable=True),
        sa.Column("changes_json", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_drawing_version_comparisons_parent", "drawing_version_comparisons", ["parent_document_id"])
    op.create_index(
        "ix_drawing_version_comparisons_versions",
        "drawing_version_comparisons",
        ["from_version_id", "to_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_drawing_version_comparisons_versions", table_name="drawing_version_comparisons")
    op.drop_index("ix_drawing_version_comparisons_parent", table_name="drawing_version_comparisons")
    op.drop_table("drawing_version_comparisons")
    op.drop_index("ix_drawing_unit_proposals_status", table_name="drawing_unit_proposals")
    op.drop_index("ix_drawing_unit_proposals_analysis_id", table_name="drawing_unit_proposals")
    op.drop_table("drawing_unit_proposals")
    op.drop_index("ix_drawing_annotations_analysis_id", table_name="drawing_annotations")
    op.drop_table("drawing_annotations")
    op.drop_index("ix_drawing_elements_confidence", table_name="drawing_elements")
    op.drop_index("ix_drawing_elements_element_type", table_name="drawing_elements")
    op.drop_index("ix_drawing_elements_analysis_id", table_name="drawing_elements")
    op.drop_table("drawing_elements")
    op.drop_index("ix_drawing_sheets_analysis_id", table_name="drawing_sheets")
    op.drop_table("drawing_sheets")
    op.drop_index("ix_drawing_analyses_discipline", table_name="drawing_analyses")
    op.drop_index("ix_drawing_analyses_processing_status", table_name="drawing_analyses")
    op.drop_index("ix_drawing_analyses_document_version_id", table_name="drawing_analyses")
    op.drop_table("drawing_analyses")
