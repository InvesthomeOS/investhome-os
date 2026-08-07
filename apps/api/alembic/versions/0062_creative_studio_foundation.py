"""Creative Studio foundation tables.

Revision ID: 0062_creative_studio_foundation
Revises: 0061_platform_core_g15a
Create Date: 2026-08-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0062_creative_studio_foundation"
down_revision: str | None = "0061_platform_core_g15a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "creative_studio_projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=True),
        sa.Column("linked_project_id", sa.Uuid(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_studio_projects_status", "creative_studio_projects", ["status"])
    op.create_index("ix_creative_studio_projects_owner_id", "creative_studio_projects", ["owner_id"])
    op.create_index("ix_creative_studio_projects_company_id", "creative_studio_projects", ["company_id"])
    op.create_index(
        "ix_creative_studio_projects_linked_project_id",
        "creative_studio_projects",
        ["linked_project_id"],
    )
    op.create_index("ix_creative_studio_projects_archived_at", "creative_studio_projects", ["archived_at"])

    op.create_table(
        "creative_studio_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("language", sa.String(length=10), nullable=True),
        sa.Column("thumbnail_url", sa.String(length=1000), nullable=True),
        sa.Column("draft_body_json", sa.JSON(), nullable=True),
        sa.Column("draft_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("draft_updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["creative_studio_projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["draft_updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_studio_documents_project_id", "creative_studio_documents", ["project_id"])
    op.create_index(
        "ix_creative_studio_documents_document_type",
        "creative_studio_documents",
        ["document_type"],
    )
    op.create_index("ix_creative_studio_documents_status", "creative_studio_documents", ["status"])
    op.create_index("ix_creative_studio_documents_archived_at", "creative_studio_documents", ["archived_at"])

    op.create_table(
        "creative_studio_document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("body_json", sa.JSON(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["creative_studio_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_creative_studio_document_versions_doc_number",
        ),
    )
    op.create_index(
        "ix_creative_studio_document_versions_document_id",
        "creative_studio_document_versions",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_creative_studio_document_versions_document_id",
        table_name="creative_studio_document_versions",
    )
    op.drop_table("creative_studio_document_versions")

    op.drop_index("ix_creative_studio_documents_archived_at", table_name="creative_studio_documents")
    op.drop_index("ix_creative_studio_documents_status", table_name="creative_studio_documents")
    op.drop_index("ix_creative_studio_documents_document_type", table_name="creative_studio_documents")
    op.drop_index("ix_creative_studio_documents_project_id", table_name="creative_studio_documents")
    op.drop_table("creative_studio_documents")

    op.drop_index("ix_creative_studio_projects_archived_at", table_name="creative_studio_projects")
    op.drop_index("ix_creative_studio_projects_linked_project_id", table_name="creative_studio_projects")
    op.drop_index("ix_creative_studio_projects_company_id", table_name="creative_studio_projects")
    op.drop_index("ix_creative_studio_projects_owner_id", table_name="creative_studio_projects")
    op.drop_index("ix_creative_studio_projects_status", table_name="creative_studio_projects")
    op.drop_table("creative_studio_projects")
