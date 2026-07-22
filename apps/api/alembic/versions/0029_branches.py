"""Branch management tables.

Revision ID: 0029_branches
Revises: 0028_companies_management
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029_branches"
down_revision: str | None = "0028_companies_management"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_code", sa.String(length=50), nullable=False),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("branch_type", sa.String(length=40), server_default="other", nullable=False),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("district", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=30), nullable=True),
        sa.Column("full_address", sa.String(length=500), nullable=False),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("google_maps_link", sa.String(length=1000), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("main_phone", sa.String(length=50), nullable=True),
        sa.Column("mobile_phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("emergency_contact", sa.String(length=255), nullable=True),
        sa.Column("manager_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="planning", nullable=False),
        sa.Column("opening_date", sa.Date(), nullable=True),
        sa.Column("department_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["manager_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_code", name="uq_branches_branch_code"),
    )
    op.create_index("ix_branches_company_id", "branches", ["company_id"])
    op.create_index("ix_branches_status", "branches", ["status"])
    op.create_index("ix_branches_city", "branches", ["city"])

    op.create_table(
        "branch_working_hours",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("business_days", sa.JSON(), nullable=True),
        sa.Column("open_time", sa.String(length=10), nullable=True),
        sa.Column("close_time", sa.String(length=10), nullable=True),
        sa.Column("holidays", sa.JSON(), nullable=True),
        sa.Column("special_hours", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("branch_id"),
    )

    op.create_table(
        "branch_assets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_branch_assets_branch_id", "branch_assets", ["branch_id"])

    op.create_table(
        "branch_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("document_type", sa.String(length=30), server_default="other", nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_branch_documents_branch_id", "branch_documents", ["branch_id"])


def downgrade() -> None:
    op.drop_index("ix_branch_documents_branch_id", table_name="branch_documents")
    op.drop_table("branch_documents")
    op.drop_index("ix_branch_assets_branch_id", table_name="branch_assets")
    op.drop_table("branch_assets")
    op.drop_table("branch_working_hours")
    op.drop_index("ix_branches_city", table_name="branches")
    op.drop_index("ix_branches_status", table_name="branches")
    op.drop_index("ix_branches_company_id", table_name="branches")
    op.drop_table("branches")
