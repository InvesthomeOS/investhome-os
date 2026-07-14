"""create projects table

Revision ID: 0004_create_projects
Revises: 0003_create_investors
Create Date: 2026-07-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_create_projects"
down_revision: str | None = "0003_create_investors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_code", sa.String(length=50), nullable=False),
        sa.Column("project_name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("project_type", sa.String(length=50), nullable=False),
        sa.Column("development_type", sa.String(length=50), nullable=False),
        sa.Column("project_status", sa.String(length=50), nullable=False),
        sa.Column("ownership_entity", sa.String(length=255), nullable=True),
        sa.Column("total_units", sa.Integer(), nullable=True),
        sa.Column("residential_units", sa.Integer(), nullable=True),
        sa.Column("commercial_units", sa.Integer(), nullable=True),
        sa.Column("gross_square_feet", sa.Integer(), nullable=True),
        sa.Column("acquisition_price", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("total_development_cost", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("current_project_value", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("projected_sale_value", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("equity_required", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("equity_raised", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("debt_amount", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("loan_to_cost", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("projected_revenue", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("projected_profit", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("projected_roi", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("projected_irr", sa.Numeric(precision=8, scale=4), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_completion_date", sa.Date(), nullable=True),
        sa.Column("actual_completion_date", sa.Date(), nullable=True),
        sa.Column("assigned_project_manager", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.UniqueConstraint("project_code"),
    )
    op.create_index("ix_projects_project_status", "projects", ["project_status"], unique=False)
    op.create_index("ix_projects_project_type", "projects", ["project_type"], unique=False)
    op.create_index(
        "ix_projects_development_type",
        "projects",
        ["development_type"],
        unique=False,
    )
    op.create_index("ix_projects_city", "projects", ["city"], unique=False)
    op.create_index(
        "ix_projects_assigned_project_manager",
        "projects",
        ["assigned_project_manager"],
        unique=False,
    )
    op.create_index("ix_projects_archived_at", "projects", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_projects_archived_at", table_name="projects")
    op.drop_index("ix_projects_assigned_project_manager", table_name="projects")
    op.drop_index("ix_projects_city", table_name="projects")
    op.drop_index("ix_projects_development_type", table_name="projects")
    op.drop_index("ix_projects_project_type", table_name="projects")
    op.drop_index("ix_projects_project_status", table_name="projects")
    op.drop_table("projects")
