"""Business unit identity is Project + optional Phase + Unit.

Revision ID: 0092_inventory_phase_unit_uniqueness
Revises: 0091_lead_phase_links

Replaces the applied physical-building uniqueness with the business key.
Existing rows are left unchanged. Duplicate keys abort the migration.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from investhome_api.services.inventory.phase_identity import (
    find_duplicate_phase_units,
    phase_unit_conflict_message,
)

revision: str = "0092_inventory_phase_unit_uniqueness"
down_revision: str | None = "0091_lead_phase_links"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conflicts = find_duplicate_phase_units(op.get_bind())
    if conflicts:
        raise RuntimeError(phase_unit_conflict_message(conflicts))
    op.execute(
        "ALTER TABLE inventory_assets DROP CONSTRAINT IF EXISTS uq_inventory_assets_project_building_phase_display"
    )
    op.execute(
        """
        ALTER TABLE inventory_assets
        ADD CONSTRAINT uq_inventory_assets_project_phase_display
        UNIQUE NULLS NOT DISTINCT (project_id, phase_id, display_id)
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE inventory_assets DROP CONSTRAINT IF EXISTS uq_inventory_assets_project_phase_display"
    )
    op.execute(
        """
        ALTER TABLE inventory_assets
        ADD CONSTRAINT uq_inventory_assets_project_building_phase_display
        UNIQUE NULLS NOT DISTINCT (project_id, building_id, phase_id, display_id)
        """
    )
