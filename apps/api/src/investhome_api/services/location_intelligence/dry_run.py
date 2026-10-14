"""Read-only check for a project location refresh. Writes nothing and calls no provider."""

from __future__ import annotations

import argparse
import json

from investhome_api.config.settings import get_settings
from investhome_api.models.project import Project
from investhome_api.models.project_location import ProjectLocationProfile, ProjectNearbyPlace
from investhome_api.services.location_intelligence.google_provider import provider_configured
from investhome_api.services.location_intelligence.normalize import format_project_address
from sqlalchemy import func, select


def inspect_project(*, project_code: str | None, project_id: str | None) -> dict:
    settings = get_settings()
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        query = select(Project)
        if project_id:
            query = query.where(Project.id == project_id)
        else:
            query = query.where(Project.project_code == project_code)
        project = db.scalar(query)
        if project is None:
            return {"found": False, "writes": 0, "project_code": project_code, "project_id": project_id}
        profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
        place_count = db.scalar(
            select(func.count()).select_from(ProjectNearbyPlace).where(ProjectNearbyPlace.project_id == project.id)
        )
        address = format_project_address(project)
        geocode_ready = provider_configured(settings, places=False)
        return {
            "found": True,
            "writes": 0,
            "project_code": project.project_code,
            "project_id": str(project.id),
            "address_present": bool(address),
            "address": address,
            "latitude": str(project.latitude) if project.latitude is not None else None,
            "longitude": str(project.longitude) if project.longitude is not None else None,
            "profile_status": profile.geocode_status.value if profile else None,
            "nearby_place_count": int(place_count or 0),
            "google_geocoding_enabled": bool(settings.google_geocoding_enabled),
            "google_places_enabled": bool(settings.google_places_enabled),
            "google_maps_api_key_present": bool((settings.google_maps_api_key or "").strip()),
            "refresh_allowed": bool(address) and geocode_ready,
        }
    finally:
        db.close()


def console_main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run project location intelligence status")
    parser.add_argument("--project-code", default="3220-16TH-NW")
    parser.add_argument("--project-id", default=None)
    args = parser.parse_args()
    print(json.dumps(inspect_project(project_code=args.project_code, project_id=args.project_id), indent=2))


if __name__ == "__main__":
    console_main()
