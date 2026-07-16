"""Inventory asset assignments — parking/storage assignment workflow.

Revision ID: 0021_inventory_assignments
Revises: 0020_inventory_ownership
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021_inventory_assignments"
down_revision: str | None = "0020_inventory_ownership"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inventory_asset_assignment_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_asset_id", sa.Uuid(), nullable=False),
        sa.Column("parent_asset_id", sa.Uuid(), nullable=True),
        sa.Column("request_type", sa.String(length=50), nullable=False),
        sa.Column("assignment_type", sa.String(length=50), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_assignment_snapshot", sa.Text(), nullable=False),
        sa.Column("assignment_price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("supporting_document_id", sa.Uuid(), nullable=True),
        sa.Column("related_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("requested_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_approver_user_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supporting_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["finance_transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_assignment_requests_child_asset_id", "inventory_asset_assignment_requests", ["child_asset_id"])
    op.create_index("ix_assignment_requests_parent_asset_id", "inventory_asset_assignment_requests", ["parent_asset_id"])
    op.create_index("ix_assignment_requests_status", "inventory_asset_assignment_requests", ["status"])
    op.create_index("ix_assignment_requests_requester", "inventory_asset_assignment_requests", ["requested_by_user_id"])
    op.create_index("ix_assignment_requests_effective_date", "inventory_asset_assignment_requests", ["effective_date"])

    op.create_table(
        "inventory_asset_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_asset_id", sa.Uuid(), nullable=False),
        sa.Column("parent_asset_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("assignment_price", sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("supporting_document_id", sa.Uuid(), nullable=True),
        sa.Column("related_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("assignment_request_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["child_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supporting_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["finance_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assignment_request_id"], ["inventory_asset_assignment_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_asset_assignments_child", "inventory_asset_assignments", ["child_asset_id"])
    op.create_index("ix_inventory_asset_assignments_parent", "inventory_asset_assignments", ["parent_asset_id"])
    op.create_index("ix_inventory_asset_assignments_status", "inventory_asset_assignments", ["status"])
    op.create_index(
        "uq_inventory_assignment_active_child",
        "inventory_asset_assignments",
        ["child_asset_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "inventory_asset_assignment_approvals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_request_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["assignment_request_id"], ["inventory_asset_assignment_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_assignment_approval_records_request_id",
        "inventory_asset_assignment_approvals",
        ["assignment_request_id"],
    )

    op.create_table(
        "inventory_asset_assignment_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("child_asset_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_request_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_asset_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["child_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignment_request_id"], ["inventory_asset_assignment_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_assignment_id"], ["inventory_asset_assignments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_assignment_events_child", "inventory_asset_assignment_events", ["child_asset_id"])
    op.create_index("ix_inventory_assignment_events_request_id", "inventory_asset_assignment_events", ["assignment_request_id"])


def downgrade() -> None:
    op.drop_table("inventory_asset_assignment_events")
    op.drop_table("inventory_asset_assignment_approvals")
    op.drop_table("inventory_asset_assignments")
    op.drop_table("inventory_asset_assignment_requests")
