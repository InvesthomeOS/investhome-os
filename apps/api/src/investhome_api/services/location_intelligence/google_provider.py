"""Google Geocoding and Places. Callers must pass a transport so tests never hit the network."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx

from investhome_api.config.settings import Settings, get_settings
from investhome_api.services.location_intelligence.normalize import (
    SEARCH_RADIUS_METERS,
    SUPPORTED_INCLUDED_TYPES,
    normalize_geocode_result,
    normalize_place_result,
)

logger = logging.getLogger(__name__)

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
PLACES_NEW_URL = "https://places.googleapis.com/v1/places:searchNearby"
PLACES_FIELD_MASK_FIELDS = (
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.primaryType",
    "places.types",
    "places.googleMapsUri",
)
PLACES_FIELD_MASK = ",".join(PLACES_FIELD_MASK_FIELDS)

Transport = Callable[[str, dict[str, str]], dict[str, Any]]
PlacesTransport = Callable[[str, dict[str, Any], dict[str, str]], dict[str, Any]]
_SECRET_PARAM = re.compile(r"(?i)(key|api[_-]?key|x-goog-api-key)\s*[=:]\s*\S+")
_GOOGLE_KEY = re.compile(r"AIza[0-9A-Za-z_\-]{10,}")


class LocationProviderError(Exception):
    """Fail closed. Callers keep the last valid rows."""

    def __init__(self, message: str, *, http_status: int | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status


class LocationProviderDisabled(LocationProviderError):
    pass


def provider_configured(settings: Settings | None = None, *, places: bool = False) -> bool:
    settings = settings or get_settings()
    key = (settings.google_maps_api_key or "").strip()
    enabled = settings.google_places_enabled if places else settings.google_geocoding_enabled
    return bool(key) and bool(enabled)


def sanitize_provider_text(text: str, secret: str = "") -> str:
    cleaned = text.replace(secret, "") if secret else text
    cleaned = _SECRET_PARAM.sub(r"\1=[redacted]", cleaned)
    cleaned = _GOOGLE_KEY.sub("[redacted]", cleaned)
    return " ".join(cleaned.split())[:200]


def _places_error_text(status: int, payload: Any, secret: str) -> str:
    reason = ""
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            reason = str(error.get("status") or error.get("message") or "")
    reason = sanitize_provider_text(reason, secret)
    return f"places provider status {status} {reason}".strip()


def _default_transport(url: str, params: dict[str, str]) -> dict[str, Any]:
    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise LocationProviderError("location provider request failed") from exc
    if not isinstance(payload, dict):
        raise LocationProviderError("location provider request failed")
    status = payload.get("status")
    if status not in {"OK", "ZERO_RESULTS"}:
        raise LocationProviderError(f"location provider status {status}")
    return payload


def _places_http(url: str, body: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    secret = headers.get("X-Goog-Api-Key", "")
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=10.0)
    except httpx.HTTPError:
        raise LocationProviderError("places provider request failed") from None
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if response.status_code < 200 or response.status_code >= 300:
        raise LocationProviderError(
            _places_error_text(response.status_code, payload, secret),
            http_status=response.status_code,
        ) from None
    if not isinstance(payload, dict):
        raise LocationProviderError(
            f"places provider status {response.status_code} invalid json",
            http_status=response.status_code,
        ) from None
    if isinstance(payload.get("error"), dict):
        raise LocationProviderError(
            _places_error_text(response.status_code, payload, secret),
            http_status=response.status_code,
        ) from None
    return payload


class GoogleLocationProvider:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: Transport | None = None,
        places_transport: PlacesTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.transport = transport or _default_transport
        self.places_transport = places_transport or _places_http

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

    def nearby(
        self,
        *,
        latitude: float,
        longitude: float,
        place_type: str,
        category: str,
        limit: int,
        project_id: UUID | str | None = None,
    ) -> list[dict[str, Any]]:
        if not provider_configured(self.settings, places=True):
            raise LocationProviderDisabled("places disabled")
        if place_type not in SUPPORTED_INCLUDED_TYPES:
            self._log_places(
                category,
                project_id,
                "unsupported",
                0,
                f"unsupported place type {place_type}",
            )
            raise LocationProviderError(f"unsupported place type {place_type}")
        secret = (self.settings.google_maps_api_key or "").strip()
        body = {
            "includedTypes": [place_type],
            "maxResultCount": max(1, min(int(limit), 20)),
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": latitude, "longitude": longitude},
                    "radius": float(SEARCH_RADIUS_METERS),
                }
            },
        }
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": secret,
            "X-Goog-FieldMask": PLACES_FIELD_MASK,
        }
        try:
            payload = self.places_transport(PLACES_NEW_URL, body, headers)
        except LocationProviderError as exc:
            self._log_places(
                category,
                project_id,
                exc.http_status or "error",
                0,
                sanitize_provider_text(str(exc), secret),
            )
            raise
        if isinstance(payload.get("error"), dict):
            message = _places_error_text(200, payload, secret)
            self._log_places(category, project_id, "error", 0, message)
            raise LocationProviderError(message)
        rows = payload.get("places", [])
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            self._log_places(category, project_id, "invalid", 0, "places response was not a list")
            raise LocationProviderError("places provider status invalid results")
        places = [item for item in rows if isinstance(item, dict)]
        self._log_places(category, project_id, 200, len(places), None)
        return places

    def _log_places(
        self,
        category: str,
        project_id: UUID | str | None,
        status: int | str,
        count: int,
        reason: str | None,
    ) -> None:
        project = str(project_id) if project_id is not None else "-"
        if reason:
            logger.warning(
                "places search provider=google_places_new category=%s project=%s "
                "status=%s results=%s reason=%s",
                category,
                project,
                status,
                count,
                reason,
            )
            return
        logger.info(
            "places search provider=google_places_new category=%s project=%s status=%s results=%s",
            category,
            project,
            status,
            count,
        )


def collect_places(
    provider: GoogleLocationProvider,
    *,
    latitude: float,
    longitude: float,
    searches: tuple[tuple[str, str, int], ...],
    project_id: UUID | None = None,
) -> list[Any]:
    found: dict[str, Any] = {}
    for category, place_type, limit in searches:
        rows = provider.nearby(
            latitude=latitude,
            longitude=longitude,
            place_type=place_type,
            category=category,
            limit=limit,
            project_id=project_id,
        )
        for item in rows[:limit]:
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
