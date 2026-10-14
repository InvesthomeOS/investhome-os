"""Google Geocoding and Places. Callers must pass a transport so tests never hit the network."""

from __future__ import annotations

from typing import Any, Callable

import httpx

from investhome_api.config.settings import Settings, get_settings
from investhome_api.services.location_intelligence.normalize import (
    SEARCH_RADIUS_METERS,
    normalize_geocode_result,
    normalize_place_result,
)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

Transport = Callable[[str, dict[str, str]], dict[str, Any]]


class LocationProviderError(Exception):
    """Fail closed. Callers keep the last valid rows."""


class LocationProviderDisabled(LocationProviderError):
    pass


def provider_configured(settings: Settings | None = None, *, places: bool = False) -> bool:
    settings = settings or get_settings()
    key = (settings.google_maps_api_key or "").strip()
    enabled = settings.google_places_enabled if places else settings.google_geocoding_enabled
    return bool(key) and bool(enabled)


def _default_transport(url: str, params: dict[str, str]) -> dict[str, Any]:
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocationProviderError("location provider request failed") from exc
    status = payload.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise LocationProviderError(f"location provider status {status}")
    return payload


class GoogleLocationProvider:
    def __init__(self, settings: Settings | None = None, transport: Transport | None = None) -> None:
        self.settings = settings or get_settings()
        self.transport = transport or _default_transport

    def geocode(self, address: str) -> dict[str, Any] | None:
        if not provider_configured(self.settings, places=False):
            raise LocationProviderDisabled("geocoding disabled")
        cleaned = address.strip()
        if not cleaned:
            return None
        payload = self.transport(
            GEOCODE_URL,
            {"address": cleaned, "key": (self.settings.google_maps_api_key or "").strip()},
        )
        if payload.get("status") == "ZERO_RESULTS":
            return None
        return normalize_geocode_result(payload)

    def nearby(self, *, latitude: float, longitude: float, place_type: str) -> list[dict[str, Any]]:
        if not provider_configured(self.settings, places=True):
            raise LocationProviderDisabled("places disabled")
        payload = self.transport(
            PLACES_URL,
            {
                "location": f"{latitude},{longitude}",
                "radius": str(SEARCH_RADIUS_METERS),
                "type": place_type,
                "key": (self.settings.google_maps_api_key or "").strip(),
            },
        )
        if payload.get("status") == "ZERO_RESULTS":
            return []
        results = payload.get("results") or []
        return [item for item in results if isinstance(item, dict)]


def collect_places(
    provider: GoogleLocationProvider,
    *,
    latitude: float,
    longitude: float,
    searches: tuple[tuple[str, str, int], ...],
) -> list[Any]:
    found: dict[str, Any] = {}
    for category, place_type, limit in searches:
        for item in provider.nearby(latitude=latitude, longitude=longitude, place_type=place_type)[:limit]:
            normalized = normalize_place_result(
                category=category,
                item=item,
                origin_lat=latitude,
                origin_lng=longitude,
            )
            if normalized is None:
                continue
            found.setdefault(normalized.provider_place_id, normalized)
    return sorted(found.values(), key=lambda place: place.straight_line_distance_meters)
