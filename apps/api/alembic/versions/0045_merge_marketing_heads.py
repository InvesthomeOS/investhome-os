"""Merge competing 0045 marketing migration heads.

Revision ID: 0045_merge_marketing_heads
Revises: 0045_marketing_attribution, 0045_marketing_budget_management, 0045_marketing_automation
Create Date: 2026-07-16

"""

from collections.abc import Sequence

revision: str = "0045_merge_marketing_heads"
down_revision: str | tuple[str, ...] | None = (
    "0045_marketing_attribution",
    "0045_marketing_budget_management",
    "0045_marketing_automation",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
