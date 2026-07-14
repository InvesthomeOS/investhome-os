"""create investors table

Revision ID: 0003_create_investors
Revises: 0002_create_leads
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_create_investors"
down_revision: str | None = "0002_create_leads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("investor_type", sa.String(length=50), nullable=False),
        sa.Column("accreditation_status", sa.String(length=50), nullable=False),
        sa.Column("preferred_investment_model", sa.String(length=50), nullable=True),
        sa.Column("investment_capacity", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("minimum_ticket", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("maximum_ticket", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("preferred_markets", sa.Text(), nullable=True),
        sa.Column("preferred_projects", sa.Text(), nullable=True),
        sa.Column("risk_profile", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_contact_date", sa.Date(), nullable=True),
        sa.Column("next_follow_up_date", sa.Date(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investors_status", "investors", ["status"], unique=False)
    op.create_index("ix_investors_investor_type", "investors", ["investor_type"], unique=False)
    op.create_index("ix_investors_country", "investors", ["country"], unique=False)
    op.create_index(
        "ix_investors_preferred_investment_model",
        "investors",
        ["preferred_investment_model"],
        unique=False,
    )
    op.create_index("ix_investors_archived_at", "investors", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_investors_archived_at", table_name="investors")
    op.drop_index("ix_investors_preferred_investment_model", table_name="investors")
    op.drop_index("ix_investors_country", table_name="investors")
    op.drop_index("ix_investors_investor_type", table_name="investors")
    op.drop_index("ix_investors_status", table_name="investors")
    op.drop_table("investors")
