"""ARQ entrypoints. Each job reads the database and may call providers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from investhome_api.services.location_intelligence.service import run_location_refresh


def _run(project_id: str) -> None:
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        run_location_refresh(db, UUID(project_id))
    finally:
        db.close()


async def refresh_project_geocode_job(ctx: dict[str, Any], project_id: str) -> None:
    _run(project_id)


async def refresh_project_nearby_places_job(ctx: dict[str, Any], project_id: str) -> None:
    _run(project_id)


async def refresh_project_location_intelligence_job(ctx: dict[str, Any], project_id: str) -> None:
    _run(project_id)
