"""Sales proposal engine.

Revision ID: 0025_sales_proposals
Revises: 0024_sales_inventory_matching
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025_sales_proposals"
down_revision: str | None = "0024_sales_inventory_matching"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sales_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("opportunity_id", sa.Uuid(), nullable=False),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("proposal_number", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("primary_project_id", sa.Uuid(), nullable=True),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("assigned_sales_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by_proposal_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_sales_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["opportunity_id"], ["sales_opportunities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["primary_project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["superseded_by_proposal_id"], ["sales_proposals.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_number"),
    )
    op.create_index("ix_sales_proposals_opportunity_id", "sales_proposals", ["opportunity_id"])
    op.create_index("ix_sales_proposals_status", "sales_proposals", ["status"])
    op.create_index("ix_sales_proposals_proposal_number", "sales_proposals", ["proposal_number"], unique=True)
    op.create_index("ix_sales_proposals_party_id", "sales_proposals", ["party_id"])
    op.create_index("ix_sales_proposals_assigned_sales_user_id", "sales_proposals", ["assigned_sales_user_id"])
    op.create_index("ix_sales_proposals_primary_project_id", "sales_proposals", ["primary_project_id"])

    op.create_table(
        "sales_proposal_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source_shortlist_id", sa.Uuid(), nullable=True),
        sa.Column("content_snapshot", sa.JSON(), nullable=True),
        sa.Column("pricing_snapshot", sa.JSON(), nullable=True),
        sa.Column("terms_snapshot", sa.JSON(), nullable=True),
        sa.Column("branding_snapshot", sa.JSON(), nullable=True),
        sa.Column("generated_document_id", sa.Uuid(), nullable=True),
        sa.Column("is_approved", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["generated_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_shortlist_id"], ["sales_shortlists.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "version_number", name="uq_proposal_version_number"),
    )
    op.create_index("ix_sales_proposal_versions_proposal_id", "sales_proposal_versions", ["proposal_id"])

    op.create_table(
        "sales_proposal_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_version_id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("item_title", sa.String(length=255), nullable=True),
        sa.Column("approved_price_id", sa.Uuid(), nullable=False),
        sa.Column("displayed_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("promotional_terms", sa.Text(), nullable=True),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("estimated_rent", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("selected_documents", sa.JSON(), nullable=True),
        sa.Column("selected_media", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_price_id"], ["inventory_asset_prices.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_version_id"], ["sales_proposal_versions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_proposal_items_version_id", "sales_proposal_items", ["proposal_version_id"])
    op.create_index("ix_sales_proposal_items_asset_id", "sales_proposal_items", ["inventory_asset_id"])

    op.create_table(
        "sales_proposal_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("proposal_version_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposal_version_id"], ["sales_proposal_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_proposal_approvals_proposal_id", "sales_proposal_approvals", ["proposal_id"])

    op.create_table(
        "sales_proposal_recipients",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=True),
        sa.Column("recipient_type", sa.String(length=20), server_default=sa.text("'primary'"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("email_snapshot", sa.String(length=255), nullable=True),
        sa.Column("language", sa.String(length=10), server_default=sa.text("'en'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "recipient_type != 'primary' OR is_primary = true",
            name="ck_proposal_recipient_primary_flag",
        ),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_proposal_recipients_proposal_id", "sales_proposal_recipients", ["proposal_id"])

    op.create_table(
        "sales_proposal_activities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["proposal_id"], ["sales_proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sales_proposal_activities_proposal_id", "sales_proposal_activities", ["proposal_id"])


def downgrade() -> None:
    op.drop_table("sales_proposal_activities")
    op.drop_table("sales_proposal_recipients")
    op.drop_table("sales_proposal_approvals")
    op.drop_table("sales_proposal_items")
    op.drop_table("sales_proposal_versions")
    op.drop_table("sales_proposals")
