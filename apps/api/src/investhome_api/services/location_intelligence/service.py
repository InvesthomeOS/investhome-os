"""Orchestration over stored rows. Provider calls happen only from the worker."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import Settings, get_settings
from investhome_api.models.project import Project
from investhome_api.models.project_location import (
    GeocodeStatus,
    ProjectLocationAiSummary,
    ProjectLocationProfile,
    ProjectNearbyPlace,
)
from investhome_api.models.user_auth import User
from investhome_api.services.permission_service import user_has_permission
from investhome_api.services.location_intelligence.google_provider import (
    GoogleLocationProvider,
    LocationProviderDisabled,
    LocationProviderError,
    collect_places,
    provider_configured,
)
from investhome_api.services.location_intelligence.normalize import (
    MAX_STORED_PLACES,
    PLACE_SEARCHES,
    PROMPT_VERSION,
    address_fingerprint,
    facts_prompt,
    format_project_address,
    group_places,
    source_fingerprint,
)
from investhome_api.services.project_assistant.llm_provider import (
    LOCAL_PROVIDER_ALIASES,
    LLMProvider,
    get_llm_provider,
)

logger = logging.getLogger(__name__)

SUMMARY_TYPE = "neighborhood"
SUMMARY_SYSTEM = (
    "You summarize only the FACTS block. "
    "Do not add place names, distances, travel times, scores, prices, demographics, "
    "safety claims, or market values. If a fact is absent, omit it."
)


def mark_location_pending(db: Session, project: Project) -> ProjectLocationProfile:
    """Address text changed. Hide the previous point until a new geocode succeeds."""
    profile = _profile(db, project.id)
    if profile is None:
        profile = ProjectLocationProfile(project_id=project.id, geocode_status=GeocodeStatus.PENDING)
        db.add(profile)
    profile.geocode_status = GeocodeStatus.PENDING
    profile.address_fingerprint = address_fingerprint(project)
    profile.last_error = None
    project.latitude = None
    project.longitude = None
    return profile


def read_location_intelligence(db: Session, project: Project, *, user: User | None) -> dict:
    profile = _profile(db, project.id)
    status = profile.geocode_status.value if profile else "none"
    current_fp = address_fingerprint(project)
    visible = (
        profile is not None
        and profile.geocode_status == GeocodeStatus.SUCCESS
        and profile.address_fingerprint == current_fp
        and project.latitude is not None
        and project.longitude is not None
    )
    places = _places(db, project.id) if visible else []
    summary = _summary(db, project.id) if visible else None
    if summary is not None and profile is not None and summary.source_fingerprint != source_fingerprint(
        neighborhood=profile.neighborhood,
        locality=profile.locality,
        places=places,
    ):
        summary = None
    place_rows = [_place_dict(row) for row in places]
    groups = [
        {
            "category": group["category"],
            "place_count": group["place_count"],
            "nearest_distance_meters": group["nearest_distance_meters"],
            "places": [_place_dict(row) for row in group["places"]],
        }
        for group in (group_places(places) if visible else [])
    ]
    return {
        "project_id": project.id,
        "status": status if profile else "none",
        "formatted_address": profile.formatted_address if visible and profile else None,
        "neighborhood": profile.neighborhood if visible and profile else None,
        "locality": profile.locality if visible and profile else None,
        "county": profile.county if visible and profile else None,
        "latitude": float(project.latitude) if visible else None,
        "longitude": float(project.longitude) if visible else None,
        "provider": profile.provider if visible and profile else None,
        "fetched_at": profile.fetched_at if visible and profile else None,
        "refreshed_at": profile.refreshed_at if profile else None,
        "nearby_places": place_rows,
        "amenity_groups": groups,
        "ai_summary": _summary_dict(summary) if summary else None,
        "can_refresh": user_may_refresh(user, db) and bool(format_project_address(project)),
    }


def user_may_refresh(user: User | None, db: Session) -> bool:
    if user is None:
        return False
    settings = get_settings()
    if not settings.auth_enabled:
        return True
    return user_has_permission(user, "projects", "update", db=db)


def run_location_refresh(
    db: Session,
    project_id: UUID,
    *,
    settings: Settings | None = None,
    geocoder: GoogleLocationProvider | None = None,
    llm: LLMProvider | None = None,
) -> str:
    settings = settings or get_settings()
    project = db.get(Project, project_id)
    if project is None:
        return "missing"
    address = format_project_address(project)
    profile = _profile(db, project.id)
    if profile is None:
        profile = ProjectLocationProfile(project_id=project.id, geocode_status=GeocodeStatus.PENDING)
        db.add(profile)
        db.flush()
    fingerprint = address_fingerprint(project)
    if not address:
        profile.geocode_status = GeocodeStatus.FAILED
        profile.last_error = "address missing"
        db.commit()
        return "failed"
    if not provider_configured(settings, places=False):
        if profile.geocode_status != GeocodeStatus.SUCCESS:
            profile.geocode_status = GeocodeStatus.DISABLED
        profile.last_error = "geocoding disabled"
        db.commit()
        return "disabled"

    provider = geocoder or GoogleLocationProvider(settings)
    try:
        geocoded = provider.geocode(address)
    except LocationProviderDisabled:
        if profile.geocode_status != GeocodeStatus.SUCCESS:
            profile.geocode_status = GeocodeStatus.DISABLED
        profile.last_error = "geocoding disabled"
        db.commit()
        return "disabled"
    except LocationProviderError as exc:
        _keep_or_fail(profile, fingerprint, str(exc))
        db.commit()
        return "failed"
    if geocoded is None:
        _keep_or_fail(profile, fingerprint, "geocode returned no verified location")
        db.commit()
        return "failed"

    previous_fingerprint = profile.address_fingerprint
    now = datetime.now(UTC)
    profile.formatted_address = geocoded["formatted_address"]
    profile.neighborhood = geocoded["neighborhood"]
    profile.locality = geocoded["locality"]
    profile.county = geocoded["county"]
    profile.state = geocoded["state"]
    profile.postal_code = geocoded["postal_code"]
    profile.country = geocoded["country"]
    profile.latitude = Decimal(str(geocoded["latitude"]))
    profile.longitude = Decimal(str(geocoded["longitude"]))
    profile.provider = "google_geocoding"
    profile.provider_place_id = geocoded["provider_place_id"]
    profile.geocode_status = GeocodeStatus.SUCCESS
    profile.address_fingerprint = fingerprint
    profile.last_error = None
    profile.raw_payload = geocoded["raw_payload"]
    profile.fetched_at = now
    profile.refreshed_at = now
    project.latitude = profile.latitude
    project.longitude = profile.longitude
    if previous_fingerprint != fingerprint:
        _delete_places(db, project.id)

    if provider_configured(settings, places=True):
        try:
            places = collect_places(
                provider,
                latitude=geocoded["latitude"],
                longitude=geocoded["longitude"],
                searches=PLACE_SEARCHES,
                project_id=project.id,
            )[:MAX_STORED_PLACES]
        except LocationProviderError as exc:
            profile.last_error = str(exc)
            db.commit()
            _refresh_summary(db, project, profile, llm=llm, settings=settings)
            return "places_failed"
        _replace_places(db, project.id, places, fetched_at=now)
    db.commit()
    db.refresh(profile)
    _refresh_summary(db, project, profile, llm=llm, settings=settings)
    return "success"


def _refresh_summary(
    db: Session,
    project: Project,
    profile: ProjectLocationProfile,
    *,
    llm: LLMProvider | None,
    settings: Settings,
) -> None:
    places = _places(db, project.id)
    if not places and not profile.neighborhood and not profile.locality:
        return
    fingerprint = source_fingerprint(
        neighborhood=profile.neighborhood,
        locality=profile.locality,
        places=places,
    )
    existing = _summary(db, project.id)
    if existing is not None and existing.source_fingerprint == fingerprint:
        return
    provider_name = (settings.ai_provider or "local").strip().lower()
    if llm is None and provider_name in LOCAL_PROVIDER_ALIASES:
        return
    try:
        selected = llm or get_llm_provider(settings)
    except Exception:
        logger.warning("location ai provider unavailable project=%s", project.id)
        return
    if selected.name in LOCAL_PROVIDER_ALIASES and llm is None:
        return
    try:
        result = selected.generate(
            system=SUMMARY_SYSTEM,
            user=facts_prompt(neighborhood=profile.neighborhood, locality=profile.locality, places=places),
        )
    except Exception:
        logger.warning("location ai summary failed project=%s", project.id)
        return
    text = (result.answer or "").strip()
    if not text:
        return
    now = datetime.now(UTC)
    if existing is None:
        existing = ProjectLocationAiSummary(
            project_id=project.id,
            summary_type=SUMMARY_TYPE,
            summary_text=text,
            source_fingerprint=fingerprint,
            generated_at=now,
        )
        db.add(existing)
    existing.summary_text = text
    existing.source_fingerprint = fingerprint
    existing.model_provider = result.provider
    existing.model_name = result.model
    existing.prompt_version = PROMPT_VERSION
    existing.generated_at = now
    db.commit()


def _keep_or_fail(profile: ProjectLocationProfile, fingerprint: str, error: str) -> None:
    profile.last_error = error
    if profile.geocode_status == GeocodeStatus.SUCCESS and profile.address_fingerprint == fingerprint:
        return
    profile.geocode_status = GeocodeStatus.FAILED


def _delete_places(db: Session, project_id: UUID) -> None:
    for row in _places(db, project_id):
        db.delete(row)


def _replace_places(db: Session, project_id: UUID, places: list, *, fetched_at: datetime) -> None:
    existing = {row.provider_place_id: row for row in _places(db, project_id)}
    seen: set[str] = set()
    for place in places:
        seen.add(place.provider_place_id)
        row = existing.get(place.provider_place_id)
        if row is None:
            row = ProjectNearbyPlace(
                project_id=project_id,
                provider=place.provider,
                provider_place_id=place.provider_place_id,
                name=place.name,
                category=place.category,
                latitude=Decimal(str(place.latitude)),
                longitude=Decimal(str(place.longitude)),
                straight_line_distance_meters=place.straight_line_distance_meters,
                fetched_at=fetched_at,
            )
            db.add(row)
        row.name = place.name
        row.category = place.category
        row.latitude = Decimal(str(place.latitude))
        row.longitude = Decimal(str(place.longitude))
        row.straight_line_distance_meters = place.straight_line_distance_meters
        row.walking_distance_meters = None
        row.walking_duration_minutes = None
        row.rating = Decimal(str(place.rating)) if place.rating is not None else None
        row.address = place.address
        row.raw_payload = place.raw_payload
        row.fetched_at = fetched_at
    for place_id, row in existing.items():
        if place_id not in seen:
            db.delete(row)


def _profile(db: Session, project_id: UUID) -> ProjectLocationProfile | None:
    return db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project_id))


def _places(db: Session, project_id: UUID) -> list[ProjectNearbyPlace]:
    return list(
        db.scalars(
            select(ProjectNearbyPlace)
            .where(ProjectNearbyPlace.project_id == project_id)
            .order_by(ProjectNearbyPlace.straight_line_distance_meters)
        ).all()
    )


def _summary(db: Session, project_id: UUID) -> ProjectLocationAiSummary | None:
    return db.scalar(
        select(ProjectLocationAiSummary).where(
            ProjectLocationAiSummary.project_id == project_id,
            ProjectLocationAiSummary.summary_type == SUMMARY_TYPE,
        )
    )


def _place_dict(row: ProjectNearbyPlace) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "category": row.category,
        "latitude": float(row.latitude),
        "longitude": float(row.longitude),
        "straight_line_distance_meters": row.straight_line_distance_meters,
        "walking_distance_meters": row.walking_distance_meters,
        "walking_duration_minutes": row.walking_duration_minutes,
        "rating": float(row.rating) if row.rating is not None else None,
        "address": row.address,
    }


def _summary_dict(row: ProjectLocationAiSummary) -> dict:
    return {
        "summary_text": row.summary_text,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "prompt_version": row.prompt_version,
        "generated_at": row.generated_at,
    }
