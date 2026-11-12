"""Project + optional phase + unit identity.

`building_id` is physical location. It is not part of the business unit key.
PostgreSQL NULLS NOT DISTINCT is what makes two phase-less units collide.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection


def operational_phase_id(*, uses_phases: bool, phase_id: UUID | None) -> UUID | None:
    """Phase filters apply only while a project still uses phases."""
    if not uses_phases:
        return None
    return phase_id


def find_duplicate_phase_units(connection: Connection) -> list[dict[str, Any]]:
    """Rows that would violate Project + Phase + Unit, including NULL phase."""
    rows = connection.execute(
        text(
            """
            SELECT project_id, phase_id, display_id, COUNT(*) AS duplicate_count
            FROM inventory_assets
            GROUP BY project_id, phase_id, display_id
            HAVING COUNT(*) > 1
            ORDER BY display_id
            """
        )
    ).mappings()
    return [dict(row) for row in rows]


def phase_unit_conflict_message(conflicts: list[dict[str, Any]]) -> str:
    lines = [
        "0092_inventory_phase_unit_uniqueness refused to continue.",
        "Existing inventory rows already share Project + Phase + Unit.",
        "No unit was renamed, deleted, or rewritten.",
    ]
    for row in conflicts:
        lines.append(
            "conflict project_id={project_id} phase_id={phase_id} display_id={display_id} count={duplicate_count}".format(
                **row
            )
        )
    return "\n".join(lines)
