"""Marketing automation workflow metadata columns.

Revision ID: 0047_mkt_automation_meta
Revises: 0046_marketing_ai_intelligence
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0047_mkt_automation_meta"
down_revision: str | None = "0046_marketing_ai_intelligence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "marketing_automation_workflows",
        sa.Column("created_by_user_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "marketing_automation_workflows",
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketing_automation_workflows",
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "marketing_automation_workflows",
        sa.Column("execution_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "fk_mkt_automation_workflows_created_by",
        "marketing_automation_workflows",
        "users",
        ["created_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "marketing_automation_executions",
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute("ALTER TYPE marketing_automation_workflow_status ADD VALUE IF NOT EXISTS 'error'")


def downgrade() -> None:
    op.drop_column("marketing_automation_executions", "retry_count")
    op.drop_constraint("fk_mkt_automation_workflows_created_by", "marketing_automation_workflows", type_="foreignkey")
    op.drop_column("marketing_automation_workflows", "execution_count")
    op.drop_column("marketing_automation_workflows", "last_run_at")
    op.drop_column("marketing_automation_workflows", "activated_at")
    op.drop_column("marketing_automation_workflows", "created_by_user_id")
