"""Merge Knowledge Hub (P10) and Security Enterprise (P11) heads.

Revision ID: 0059_merge_p10_p11
Revises: 0058_knowledge_hub, 0058_security_enterprise
Create Date: 2026-07-20
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0059_merge_p10_p11"
down_revision: tuple[str, str] | None = ("0058_knowledge_hub", "0058_security_enterprise")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
