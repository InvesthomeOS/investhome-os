"""Inventory reservations — soft hold and reservation workflow.

Revision ID: 0018_inventory_reservations
Revises: 0017_inventory_assets
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_inventory_reservations"
down_revision: str | None = "0017_inventory_assets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_STATUSES = ("active", "requested", "approved", "deposit_pending", "deposit_received")


def upgrade() -> None:
    op.create_table(
        "inventory_reservations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("inventory_asset_id", sa.Uuid(), nullable=False),
        sa.Column("reservation_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=50), server_default="manual", nullable=False),
        sa.Column("investor_id", sa.Uuid(), nullable=True),
        sa.Column("lead_id", sa.Uuid(), nullable=True),
        sa.Column("reserved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("approved_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deposit_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deposit_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("deposit_currency", sa.String(length=3), nullable=True),
        sa.Column("finance_transaction_id", sa.Uuid(), nullable=True),
        sa.Column("extension_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deposit_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["finance_transaction_id"], ["finance_transactions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inventory_asset_id"], ["inventory_assets.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["investor_id"], ["investors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventory_reservations_asset_id", "inventory_reservations", ["inventory_asset_id"])
    op.create_index("ix_inventory_reservations_investor_id", "inventory_reservations", ["investor_id"])
    op.create_index("ix_inventory_reservations_lead_id", "inventory_reservations", ["lead_id"])
    op.create_index("ix_inventory_reservations_status", "inventory_reservations", ["status"])
    op.create_index("ix_inventory_reservations_expires_at", "inventory_reservations", ["expires_at"])
    op.create_index(
        "uq_inventory_reservations_active_asset",
        "inventory_reservations",
        ["inventory_asset_id"],
        unique=True,
        postgresql_where=sa.text(f"status IN {ACTIVE_STATUSES}"),
        sqlite_where=sa.text(f"status IN {ACTIVE_STATUSES}"),
    )

    op.create_table(
        "inventory_reservation_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("reservation_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("from_status", sa.String(length=50), nullable=True),
        sa.Column("to_status", sa.String(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["reservation_id"], ["inventory_reservations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inventory_reservation_events_reservation_id",
        "inventory_reservation_events",
        ["reservation_id"],
    )

    op.add_column("inventory_assets", sa.Column("active_reservation_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_inventory_assets_active_reservation_id",
        "inventory_assets",
        "inventory_reservations",
        ["active_reservation_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_inventory_assets_active_reservation_id", "inventory_assets", type_="foreignkey")
    op.drop_column("inventory_assets", "active_reservation_id")
    op.drop_index("ix_inventory_reservation_events_reservation_id", table_name="inventory_reservation_events")
    op.drop_table("inventory_reservation_events")
    op.drop_index("uq_inventory_reservations_active_asset", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_expires_at", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_status", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_lead_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_investor_id", table_name="inventory_reservations")
    op.drop_index("ix_inventory_reservations_asset_id", table_name="inventory_reservations")
    op.drop_table("inventory_reservations")
