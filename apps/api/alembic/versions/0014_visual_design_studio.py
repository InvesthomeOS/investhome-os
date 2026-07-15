"""Visual Design Studio tables.

Revision ID: 0014_visual_design_studio
Revises: 0013_company_foundation
Create Date: 2026-07-15

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_visual_design_studio"
down_revision: str | None = "0013_company_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "design_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("document_version_id", sa.Uuid(), nullable=False),
        sa.Column("drawing_analysis_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("design_type", sa.String(length=40), server_default="colored_floor_plan", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("source_geometry_version", sa.String(length=80), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("review_submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["drawing_analysis_id"], ["drawing_analyses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_design_projects_project_id", "design_projects", ["project_id"])
    op.create_index("ix_design_projects_document_id", "design_projects", ["document_id"])
    op.create_index("ix_design_projects_status", "design_projects", ["status"])
    op.create_index("ix_design_projects_design_type", "design_projects", ["design_type"])

    op.create_table(
        "design_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("design_project_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_geometry_version", sa.String(length=80), nullable=True),
        sa.Column("design_parameters", sa.JSON(), nullable=True),
        sa.Column("output_location", sa.String(length=1000), nullable=True),
        sa.Column("thumbnail_location", sa.String(length=1000), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["design_project_id"], ["design_projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_design_versions_design_project_id", "design_versions", ["design_project_id"])
    op.create_index(
        "uq_design_versions_project_number",
        "design_versions",
        ["design_project_id", "version_number"],
        unique=True,
    )

    op.create_table(
        "style_presets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color_palette", sa.JSON(), nullable=True),
        sa.Column("material_preferences", sa.JSON(), nullable=True),
        sa.Column("furniture_preferences", sa.JSON(), nullable=True),
        sa.Column("is_system_preset", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_style_presets_code", "style_presets", ["code"])
    op.create_index("ix_style_presets_is_system", "style_presets", ["is_system_preset"])

    op.create_table(
        "material_packages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("flooring", sa.String(length=120), nullable=True),
        sa.Column("wall_finish", sa.String(length=120), nullable=True),
        sa.Column("ceiling_finish", sa.String(length=120), nullable=True),
        sa.Column("cabinetry", sa.String(length=120), nullable=True),
        sa.Column("countertop", sa.String(length=120), nullable=True),
        sa.Column("backsplash", sa.String(length=120), nullable=True),
        sa.Column("bathroom_finish", sa.String(length=120), nullable=True),
        sa.Column("metal_finish", sa.String(length=120), nullable=True),
        sa.Column("door_finish", sa.String(length=120), nullable=True),
        sa.Column("color_palette", sa.JSON(), nullable=True),
        sa.Column("reference_document_ids", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_material_packages_name", "material_packages", ["name"])

    op.create_table(
        "furniture_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("room_type", sa.String(length=40), nullable=True),
        sa.Column("furniture_type", sa.String(length=40), nullable=False),
        sa.Column("width", sa.Float(), nullable=True),
        sa.Column("depth", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("measurement_unit", sa.String(length=10), server_default="cm", nullable=False),
        sa.Column("default_rotation", sa.Float(), server_default="0", nullable=False),
        sa.Column("icon_or_preview", sa.String(length=500), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("is_system_item", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_furniture_items_code", "furniture_items", ["code"])
    op.create_index("ix_furniture_items_furniture_type", "furniture_items", ["furniture_type"])


def downgrade() -> None:
    op.drop_index("ix_furniture_items_furniture_type", table_name="furniture_items")
    op.drop_index("ix_furniture_items_code", table_name="furniture_items")
    op.drop_table("furniture_items")
    op.drop_index("ix_material_packages_name", table_name="material_packages")
    op.drop_table("material_packages")
    op.drop_index("ix_style_presets_is_system", table_name="style_presets")
    op.drop_index("ix_style_presets_code", table_name="style_presets")
    op.drop_table("style_presets")
    op.drop_index("uq_design_versions_project_number", table_name="design_versions")
    op.drop_index("ix_design_versions_design_project_id", table_name="design_versions")
    op.drop_table("design_versions")
    op.drop_index("ix_design_projects_design_type", table_name="design_projects")
    op.drop_index("ix_design_projects_status", table_name="design_projects")
    op.drop_index("ix_design_projects_document_id", table_name="design_projects")
    op.drop_index("ix_design_projects_project_id", table_name="design_projects")
    op.drop_table("design_projects")
