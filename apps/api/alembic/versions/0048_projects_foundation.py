"""Projects workspace foundation columns and team members.

Revision ID: 0048_projects_foundation
Revises: 0047_mkt_automation_meta
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "0048_projects_foundation"
down_revision: str | None = "0047_mkt_automation_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return column in {col["name"] for col in inspect(bind).get_columns(table)}


def _has_index(table: str, name: str) -> bool:
    bind = op.get_bind()
    return name in {idx["name"] for idx in inspect(bind).get_indexes(table)}


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return table in inspect(bind).get_table_names()


def _add_column(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def _create_index(name: str, table: str, columns: list[str], *, unique: bool = False) -> None:
    if not _has_index(table, name):
        op.create_index(name, table, columns, unique=unique)


def upgrade() -> None:
    _add_column("projects", sa.Column("slug", sa.String(length=280), nullable=True))
    _add_column("projects", sa.Column("address_line2", sa.String(length=500), nullable=True))
    _add_column("projects", sa.Column("latitude", sa.Numeric(precision=10, scale=7), nullable=True))
    _add_column("projects", sa.Column("longitude", sa.Numeric(precision=10, scale=7), nullable=True))
    _add_column("projects", sa.Column("timezone", sa.String(length=64), nullable=True))
    _add_column(
        "projects",
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="medium"),
    )
    _add_column("projects", sa.Column("development_stage", sa.String(length=40), nullable=True))
    _add_column("projects", sa.Column("company_id", sa.Uuid(), nullable=True))
    _add_column("projects", sa.Column("net_sellable_square_feet", sa.Integer(), nullable=True))
    _add_column("projects", sa.Column("lot_size", sa.Numeric(precision=16, scale=2), nullable=True))
    _add_column("projects", sa.Column("land_cost", sa.Numeric(precision=16, scale=2), nullable=True))
    _add_column(
        "projects",
        sa.Column("construction_budget", sa.Numeric(precision=16, scale=2), nullable=True),
    )
    _add_column(
        "projects",
        sa.Column("soft_cost_budget", sa.Numeric(precision=16, scale=2), nullable=True),
    )
    _add_column(
        "projects",
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
    )
    _add_column(
        "projects",
        sa.Column("completion_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    _add_column("projects", sa.Column("acquisition_date", sa.Date(), nullable=True))
    _add_column("projects", sa.Column("actual_start_date", sa.Date(), nullable=True))
    _add_column("projects", sa.Column("estimated_closing_date", sa.Date(), nullable=True))
    _add_column("projects", sa.Column("project_manager_user_id", sa.Uuid(), nullable=True))
    _add_column("projects", sa.Column("created_by_user_id", sa.Uuid(), nullable=True))
    _add_column("projects", sa.Column("updated_by_user_id", sa.Uuid(), nullable=True))

    bind = op.get_bind()
    fks = {fk["name"] for fk in inspect(bind).get_foreign_keys("projects")}
    if "fk_projects_company_id" not in fks:
        op.create_foreign_key(
            "fk_projects_company_id",
            "projects",
            "companies",
            ["company_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "fk_projects_project_manager_user_id" not in fks:
        op.create_foreign_key(
            "fk_projects_project_manager_user_id",
            "projects",
            "users",
            ["project_manager_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "fk_projects_created_by_user_id" not in fks:
        op.create_foreign_key(
            "fk_projects_created_by_user_id",
            "projects",
            "users",
            ["created_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
    if "fk_projects_updated_by_user_id" not in fks:
        op.create_foreign_key(
            "fk_projects_updated_by_user_id",
            "projects",
            "users",
            ["updated_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Existing indexes from 0004: project_status, project_type, city — skip those.
    _create_index("ix_projects_priority", "projects", ["priority"])
    _create_index("ix_projects_development_stage", "projects", ["development_stage"])
    _create_index("ix_projects_state", "projects", ["state"])
    _create_index("ix_projects_company_id", "projects", ["company_id"])
    _create_index("ix_projects_project_manager_user_id", "projects", ["project_manager_user_id"])
    _create_index("ix_projects_target_completion_date", "projects", ["target_completion_date"])
    _create_index("ix_projects_created_at", "projects", ["created_at"])
    _create_index("ix_projects_slug", "projects", ["slug"], unique=True)

    if not _has_table("project_team_members"):
        op.create_table(
            "project_team_members",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("project_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("role", sa.String(length=40), nullable=False),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("start_date", sa.Date(), nullable=True),
            sa.Column("end_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("notes", sa.String(length=500), nullable=True),
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
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "project_id",
                "user_id",
                "role",
                name="uq_project_team_members_project_user_role",
            ),
        )
        op.create_index("ix_project_team_members_project_id", "project_team_members", ["project_id"])
        op.create_index("ix_project_team_members_user_id", "project_team_members", ["user_id"])
        op.create_index("ix_project_team_members_status", "project_team_members", ["status"])

    op.execute(
        """
        UPDATE projects
        SET slug = lower(regexp_replace(project_code, '[^a-zA-Z0-9]+', '-', 'g'))
        WHERE slug IS NULL
        """
    )


def downgrade() -> None:
    if _has_table("project_team_members"):
        op.drop_index("ix_project_team_members_status", table_name="project_team_members")
        op.drop_index("ix_project_team_members_user_id", table_name="project_team_members")
        op.drop_index("ix_project_team_members_project_id", table_name="project_team_members")
        op.drop_table("project_team_members")

    for name in (
        "ix_projects_slug",
        "ix_projects_created_at",
        "ix_projects_target_completion_date",
        "ix_projects_project_manager_user_id",
        "ix_projects_company_id",
        "ix_projects_state",
        "ix_projects_development_stage",
        "ix_projects_priority",
    ):
        if _has_index("projects", name):
            op.drop_index(name, table_name="projects")

    bind = op.get_bind()
    fks = {fk["name"] for fk in inspect(bind).get_foreign_keys("projects")}
    for name in (
        "fk_projects_updated_by_user_id",
        "fk_projects_created_by_user_id",
        "fk_projects_project_manager_user_id",
        "fk_projects_company_id",
    ):
        if name in fks:
            op.drop_constraint(name, "projects", type_="foreignkey")

    for column in (
        "updated_by_user_id",
        "created_by_user_id",
        "project_manager_user_id",
        "estimated_closing_date",
        "actual_start_date",
        "acquisition_date",
        "completion_percentage",
        "currency",
        "soft_cost_budget",
        "construction_budget",
        "land_cost",
        "lot_size",
        "net_sellable_square_feet",
        "company_id",
        "development_stage",
        "priority",
        "timezone",
        "longitude",
        "latitude",
        "address_line2",
        "slug",
    ):
        if _has_column("projects", column):
            op.drop_column("projects", column)
