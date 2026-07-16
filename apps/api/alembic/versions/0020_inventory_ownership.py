"""Inventory ownership — immutable ownership history and transfer workflow.

Revision ID: 0020_inventory_ownership
Revises: 0019_inventory_pricing
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0020_inventory_ownership"
down_revision: str | None = "0019_inventory_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ownership_transfer_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("transfer_type", sa.String(length=50), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("source_ownership_snapshot", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supporting_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["finance_transactions.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ownership_transfer_requests_asset_id", "ownership_transfer_requests", ["inventory_asset_id"])
    op.create_index("ix_ownership_transfer_requests_status", "ownership_transfer_requests", ["status"])
    op.create_index("ix_ownership_transfer_requests_requester", "ownership_transfer_requests", ["requested_by_user_id"])
    op.create_index("ix_ownership_transfer_requests_effective_date", "ownership_transfer_requests", ["effective_date"])

    op.create_table(
        "inventory_ownership",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("ownership_type", sa.String(length=50), nullable=False),
        sa.Column("ownership_percentage", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("acquisition_method", sa.String(length=50), nullable=False),
        sa.Column("transfer_reason", sa.Text(), nullable=True),
        sa.Column("related_document_id", sa.Uuid(), nullable=True),
        sa.Column("related_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("ownership_transfer_request_id", sa.Uuid(), nullable=True),
        sa.Column("correction_of_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["party_id"], ["investors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["related_document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["related_transaction_id"], ["finance_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ownership_transfer_request_id"], ["ownership_transfer_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["correction_of_id"], ["inventory_ownership.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_ownership_asset_id", "inventory_ownership", ["inventory_asset_id"])
    op.create_index("ix_inventory_ownership_party_id", "inventory_ownership", ["party_id"])
    op.create_index("ix_inventory_ownership_status", "inventory_ownership", ["status"])
    op.create_index("ix_inventory_ownership_type", "inventory_ownership", ["ownership_type"])
    op.create_index(
        "uq_inventory_ownership_active_party_type",
        "inventory_ownership",
        ["inventory_asset_id", "party_id", "ownership_type"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "ownership_transfer_parties",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ownership_transfer_request_id", sa.Uuid(), nullable=False),
        sa.Column("party_id", sa.Uuid(), nullable=False),
        sa.Column("ownership_type", sa.String(length=50), nullable=False),
        sa.Column("previous_percentage", sa.Numeric(precision=7, scale=4), nullable=True),
        sa.Column("proposed_percentage", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ownership_transfer_request_id"], ["ownership_transfer_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["party_id"], ["investors.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ownership_transfer_parties_request_id",
        "ownership_transfer_parties",
        ["ownership_transfer_request_id"],
    )

    op.create_table(
        "ownership_approval_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ownership_transfer_request_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ownership_transfer_request_id"], ["ownership_transfer_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ownership_approval_records_request_id",
        "ownership_approval_records",
        ["ownership_transfer_request_id"],
    )

    op.create_table(
        "inventory_ownership_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("ownership_transfer_request_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_ownership_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ownership_transfer_request_id"], ["ownership_transfer_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_ownership_id"], ["inventory_ownership.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_ownership_events_asset_id", "inventory_ownership_events", ["inventory_asset_id"])
    op.create_index("ix_inventory_ownership_events_request_id", "inventory_ownership_events", ["ownership_transfer_request_id"])


def downgrade() -> None:
    op.drop_table("inventory_ownership_events")
    op.drop_table("ownership_approval_records")
    op.drop_table("ownership_transfer_parties")
    op.drop_table("inventory_ownership")
    op.drop_table("ownership_transfer_requests")
