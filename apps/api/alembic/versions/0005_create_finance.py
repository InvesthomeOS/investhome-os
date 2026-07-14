"""create finance tables

Revision ID: 0005_create_finance
Revises: 0004_create_projects
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_create_finance"
down_revision: str | None = "0004_create_projects"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "financial_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("account_name", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=False),
        sa.Column("institution_name", sa.String(length=255), nullable=True),
        sa.Column("ownership_entity", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("current_balance", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("available_balance", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("account_reference", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index(
        "ix_financial_accounts_account_type",
        "financial_accounts",
        ["account_type"],
        unique=False,
    )
    op.create_index(
        "ix_financial_accounts_status",
        "financial_accounts",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_financial_accounts_currency",
        "financial_accounts",
        ["currency"],
        unique=False,
    )
    op.create_index(
        "ix_financial_accounts_archived_at",
        "financial_accounts",
        ["archived_at"],
        unique=False,
    )

    op.create_table(
        "finance_transactions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("transaction_date", sa.Date(), nullable=False),
        sa.Column("transaction_type", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("investor_id", sa.Uuid(), nullable=True),
        sa.Column("counterparty", sa.String(length=255), nullable=True),
        sa.Column("reference_number", sa.String(length=100), nullable=True),
        sa.Column("payment_method", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["account_id"], ["financial_accounts.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investor_id"], ["investors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_finance_transactions_transaction_date",
        "finance_transactions",
        ["transaction_date"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_transaction_type",
        "finance_transactions",
        ["transaction_type"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_status",
        "finance_transactions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_account_id",
        "finance_transactions",
        ["account_id"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_project_id",
        "finance_transactions",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_investor_id",
        "finance_transactions",
        ["investor_id"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_currency",
        "finance_transactions",
        ["currency"],
        unique=False,
    )
    op.create_index(
        "ix_finance_transactions_archived_at",
        "finance_transactions",
        ["archived_at"],
        unique=False,
    )

    op.create_table(
        "project_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("budget_name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("original_budget", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("revised_budget", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("committed_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("forecast_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_budgets_project_id",
        "project_budgets",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_project_budgets_category",
        "project_budgets",
        ["category"],
        unique=False,
    )

    op.create_table(
        "funding_commitments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("investor_id", sa.Uuid(), nullable=False),
        sa.Column("commitment_type", sa.String(length=50), nullable=False),
        sa.Column("committed_amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("funded_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("remaining_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("commitment_date", sa.Date(), nullable=True),
        sa.Column("target_funding_date", sa.Date(), nullable=True),
        sa.Column("actual_funding_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investor_id"], ["investors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_funding_commitments_project_id",
        "funding_commitments",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_funding_commitments_investor_id",
        "funding_commitments",
        ["investor_id"],
        unique=False,
    )
    op.create_index(
        "ix_funding_commitments_status",
        "funding_commitments",
        ["status"],
        unique=False,
    )

    op.create_table(
        "payment_obligations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("investor_id", sa.Uuid(), nullable=True),
        sa.Column("obligation_type", sa.String(length=50), nullable=False),
        sa.Column("payee", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("amount", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("priority", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["investor_id"], ["investors.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_payment_obligations_project_id",
        "payment_obligations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_obligations_investor_id",
        "payment_obligations",
        ["investor_id"],
        unique=False,
    )
    op.create_index(
        "ix_payment_obligations_status",
        "payment_obligations",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_payment_obligations_priority",
        "payment_obligations",
        ["priority"],
        unique=False,
    )
    op.create_index(
        "ix_payment_obligations_due_date",
        "payment_obligations",
        ["due_date"],
        unique=False,
    )
    op.create_index(
        "ix_payment_obligations_archived_at",
        "payment_obligations",
        ["archived_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_payment_obligations_archived_at", table_name="payment_obligations")
    op.drop_index("ix_payment_obligations_due_date", table_name="payment_obligations")
    op.drop_index("ix_payment_obligations_priority", table_name="payment_obligations")
    op.drop_index("ix_payment_obligations_status", table_name="payment_obligations")
    op.drop_index("ix_payment_obligations_investor_id", table_name="payment_obligations")
    op.drop_index("ix_payment_obligations_project_id", table_name="payment_obligations")
    op.drop_table("payment_obligations")

    op.drop_index("ix_funding_commitments_status", table_name="funding_commitments")
    op.drop_index("ix_funding_commitments_investor_id", table_name="funding_commitments")
    op.drop_index("ix_funding_commitments_project_id", table_name="funding_commitments")
    op.drop_table("funding_commitments")

    op.drop_index("ix_project_budgets_category", table_name="project_budgets")
    op.drop_index("ix_project_budgets_project_id", table_name="project_budgets")
    op.drop_table("project_budgets")

    op.drop_index("ix_finance_transactions_archived_at", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_currency", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_investor_id", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_project_id", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_account_id", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_status", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_transaction_type", table_name="finance_transactions")
    op.drop_index("ix_finance_transactions_transaction_date", table_name="finance_transactions")
    op.drop_table("finance_transactions")

    op.drop_index("ix_financial_accounts_archived_at", table_name="financial_accounts")
    op.drop_index("ix_financial_accounts_currency", table_name="financial_accounts")
    op.drop_index("ix_financial_accounts_status", table_name="financial_accounts")
    op.drop_index("ix_financial_accounts_account_type", table_name="financial_accounts")
    op.drop_table("financial_accounts")
