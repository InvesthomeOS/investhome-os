"""Inventory pricing — versioned prices and approval workflow.

Revision ID: 0019_inventory_pricing
Revises: 0018_inventory_reservations
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_inventory_pricing"
down_revision: str | None = "0018_inventory_reservations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("inventory_assets", sa.Column("list_price", sa.Numeric(precision=16, scale=2), nullable=True))
    op.add_column(
        "inventory_assets",
        sa.Column("promotional_price", sa.Numeric(precision=16, scale=2), nullable=True),
    )

    op.create_table(
        "price_change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("price_type", sa.String(length=50), nullable=False),
        sa.Column("current_price_id", sa.Uuid(), nullable=True),
        sa.Column("current_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("proposed_amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("change_amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("change_percentage", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("supporting_document_id", sa.Uuid(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_price_change_requests_asset_id", "price_change_requests", ["inventory_asset_id"])
    op.create_index("ix_price_change_requests_status", "price_change_requests", ["status"])
    op.create_index("ix_price_change_requests_requester", "price_change_requests", ["requested_by_user_id"])
    op.create_index("ix_price_change_requests_approver", "price_change_requests", ["assigned_approver_user_id"])

    op.create_table(
        "inventory_asset_prices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("price_type", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("approved_request_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["approved_request_id"], ["price_change_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_asset_prices_asset_id", "inventory_asset_prices", ["inventory_asset_id"])
    op.create_index(
        "ix_inventory_asset_prices_type_status",
        "inventory_asset_prices",
        ["price_type", "status"],
    )
    op.create_index(
        "uq_inventory_asset_prices_active",
        "inventory_asset_prices",
        ["inventory_asset_id", "price_type", "currency"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_foreign_key(
        "fk_price_change_requests_current_price",
        "price_change_requests",
        "inventory_asset_prices",
        ["current_price_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "price_approval_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("price_change_request_id", sa.Uuid(), nullable=False),
        sa.Column("reviewer_user_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["price_change_request_id"], ["price_change_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_price_approval_records_request_id",
        "price_approval_records",
        ["price_change_request_id"],
    )

    op.create_table(
        "inventory_price_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("price_change_request_id", sa.Uuid(), nullable=True),
        sa.Column("inventory_asset_price_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["price_change_request_id"], ["price_change_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_price_id"], ["inventory_asset_prices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_price_events_asset_id", "inventory_price_events", ["inventory_asset_id"])
    op.create_index("ix_inventory_price_events_request_id", "inventory_price_events", ["price_change_request_id"])


def downgrade() -> None:
    op.drop_table("inventory_price_events")
    op.drop_table("price_approval_records")
    op.drop_constraint("fk_price_change_requests_current_price", "price_change_requests", type_="foreignkey")
    op.drop_table("inventory_asset_prices")
    op.drop_table("price_change_requests")
    op.drop_column("inventory_assets", "promotional_price")
    op.drop_column("inventory_assets", "list_price")
