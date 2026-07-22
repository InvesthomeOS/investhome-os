"""Department management tables.

Revision ID: 0030_departments
Revises: 0029_branches
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030_departments"
down_revision: str | None = "0029_branches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "company_departments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_code", sa.String(length=50), nullable=False),
        sa.Column("department_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("company_id", sa.Uuid(), nullable=False),
        sa.Column("branch_id", sa.Uuid(), nullable=True),
        sa.Column("department_type", sa.String(length=40), server_default="other", nullable=False),
        sa.Column("parent_department_id", sa.Uuid(), nullable=True),
        sa.Column("department_head_user_id", sa.Uuid(), nullable=True),
        sa.Column("cost_center", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("annual_budget", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=True),
        sa.Column("employee_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("team_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("open_positions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("merged_into_department_id", sa.Uuid(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["department_head_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["merged_into_department_id"], ["company_departments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["parent_department_id"], ["company_departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", "department_code", name="uq_company_departments_code"),
    )
    op.create_index("ix_company_departments_company_id", "company_departments", ["company_id"])
    op.create_index("ix_company_departments_branch_id", "company_departments", ["branch_id"])
    op.create_index("ix_company_departments_status", "company_departments", ["status"])
    op.create_index("ix_company_departments_parent_id", "company_departments", ["parent_department_id"])

    op.create_table(
        "department_employee_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("allocation_percentage", sa.Integer(), server_default="100", nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["company_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("department_id", "user_id", name="uq_dept_employee_assignments"),
    )

    op.create_table(
        "department_kpis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target", sa.Numeric(18, 4), nullable=True),
        sa.Column("current_value", sa.Numeric(18, 4), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("period", sa.String(length=50), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("progress", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="on_track", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["company_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "department_responsibilities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("review_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["company_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "department_budgets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("approved_budget", sa.Numeric(18, 2), nullable=True),
        sa.Column("used_budget", sa.Numeric(18, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("cost_center", sa.String(length=50), nullable=True),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("approval_status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["company_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "department_project_links",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("link_type", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["company_departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("department_project_links")
    op.drop_table("department_budgets")
    op.drop_table("department_responsibilities")
    op.drop_table("department_kpis")
    op.drop_table("department_employee_assignments")
    op.drop_table("company_departments")
