"""Phase-scoped budget versions and agreement-linked cash.

Revision ID: 0097_budget_scope_sale_cash
Revises: 0096_phase_address_budget_scope

Not applied by this change. Existing version ids, numbers, and approval
status stay as they are. A conflicting scope aborts the upgrade.
Nullable agreement and commission columns do not rewrite sales.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0097_budget_scope_sale_cash"
down_revision: str | None = "0096_phase_address_budget_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    conflicts = bind.execute(
        sa.text(
            """
            SELECT project_id, phase_id, audience, version_number, COUNT(*) AS n
            FROM project_budget_versions
            GROUP BY project_id, phase_id, audience, version_number
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    if conflicts:
        raise RuntimeError(
            "project_budget_versions already has "
            f"{len(conflicts)} duplicate project/phase/audience/version groups"
        )
    op.drop_constraint(
        "uq_project_budget_versions_project_version",
        "project_budget_versions",
        type_="unique",
    )
    op.create_index(
        "uq_project_budget_versions_project_scope",
        "project_budget_versions",
        ["project_id", "audience", "version_number"],
        unique=True,
        postgresql_where=sa.text("phase_id IS NULL"),
    )
    op.create_index(
        "uq_project_budget_versions_phase_scope",
        "project_budget_versions",
        ["project_id", "phase_id", "audience", "version_number"],
        unique=True,
        postgresql_where=sa.text("phase_id IS NOT NULL"),
    )
    op.add_column("finance_transactions", sa.Column("agreement_id", sa.Uuid(), nullable=True))
    op.create_index(
        "ix_finance_transactions_agreement_id",
        "finance_transactions",
        ["agreement_id"],
    )
    op.create_foreign_key(
        "fk_finance_transactions_agreement_id",
        "finance_transactions",
        "crm_agreements",
        ["agreement_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "crm_agreement_participants",
        sa.Column("commission_rate", sa.Numeric(7, 4), nullable=True),
    )
    op.add_column(
        "crm_agreement_participants",
        sa.Column("commission_amount", sa.Numeric(16, 2), nullable=True),
    )
    op.add_column(
        "crm_agreement_participants",
        sa.Column("commission_paid", sa.Numeric(16, 2), nullable=True),
    )
    op.add_column(
        "crm_agreement_participants",
        sa.Column("commission_condition", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("crm_agreement_participants", "commission_condition")
    op.drop_column("crm_agreement_participants", "commission_paid")
    op.drop_column("crm_agreement_participants", "commission_amount")
    op.drop_column("crm_agreement_participants", "commission_rate")
    op.drop_constraint(
        "fk_finance_transactions_agreement_id", "finance_transactions", type_="foreignkey"
    )
    op.drop_index("ix_finance_transactions_agreement_id", table_name="finance_transactions")
    op.drop_column("finance_transactions", "agreement_id")
    op.drop_index(
        "uq_project_budget_versions_phase_scope", table_name="project_budget_versions"
    )
    op.drop_index(
        "uq_project_budget_versions_project_scope", table_name="project_budget_versions"
    )
    op.create_unique_constraint(
        "uq_project_budget_versions_project_version",
        "project_budget_versions",
        ["project_id", "version_number"],
    )
