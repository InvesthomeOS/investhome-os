"""Deterministic location helpers. No provider calls."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

ADDRESS_TEXT_FIELDS = frozenset({"address", "address_line2", "city", "state", "postal_code", "country"})

PLACE_CATEGORIES = (
    "transit",
    "grocery",
    "food",
    "parks",
    "education",
    "healthcare",
    "fitness",
    "retail",
    "landmarks",
)

# Places API (New) Table A types. One included type per search so category caps stay stable.
# https://developers.google.com/maps/documentation/places/web-service/place-types
CATEGORY_INCLUDED_TYPES: dict[str, tuple[str, ...]] = {
    "transit": ("transit_station",),
    "grocery": ("supermarket",),
    "food": ("restaurant", "cafe"),
    "parks": ("park",),
    "education": ("university", "school"),
    "healthcare": ("hospital",),
    "fitness": ("gym",),
    "retail": ("shopping_mall",),
    "landmarks": ("tourist_attraction",),
}
PLACE_SEARCHES: tuple[tuple[str, str, int], ...] = (
    ("transit", "transit_station", 5),
    ("grocery", "supermarket", 4),
    ("food", "restaurant", 4),
    ("food", "cafe", 3),
    ("parks", "park", 4),
    ("education", "university", 3),
    ("education", "school", 3),
    ("healthcare", "hospital", 3),
    ("fitness", "gym", 3),
    ("retail", "shopping_mall", 3),
    ("landmarks", "tourist_attraction", 3),
)
SUPPORTED_INCLUDED_TYPES = frozenset(place_type for _, place_type, _ in PLACE_SEARCHES)

SEARCH_RADIUS_METERS = 1200
MAX_STORED_PLACES = 30
ACCEPTED_LOCATION_TYPES = frozenset({"ROOFTOP", "RANGE_INTERPOLATED", "GEOMETRIC_CENTER"})
PROMPT_VERSION = "location-neighborhood-v1"


@dataclass(frozen=True)
class NormalizedPlace:
    provider: str
    provider_place_id: str
    name: str
    category: str
    latitude: float
    longitude: float
    straight_line_distance_meters: int
    rating: float | None
    address: str | None
    raw_payload: dict[str, Any]


def format_project_address(project: Any) -> str:
    parts = [
        getattr(project, "address", None),
        getattr(project, "address_line2", None),
        getattr(project, "city", None),
        getattr(project, "state", None),
        getattr(project, "postal_code", None),
        getattr(project, "country", None),
    ]
    return ", ".join(part.strip() for part in parts if isinstance(part, str) and part.strip())


def address_fingerprint(project: Any) -> str:
    payload = {field: (getattr(project, field, None) or "").strip() for field in sorted(ADDRESS_TEXT_FIELDS)}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def component(components: list[dict[str, Any]], *types: str) -> str | None:
    wanted = set(types)
    for item in components:
        if wanted.intersection(item.get("types") or []):
            value = item.get("long_name")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lng / 2) ** 2
    return int(round(2 * radius * math.asin(math.sqrt(a))))


def normalize_geocode_result(payload: dict[str, Any]) -> dict[str, Any] | None:
    results = payload.get("results") or []
    if not results or not isinstance(results, list):
        return None
    first = results[0]
    if not isinstance(first, dict):
        return None
    location_type = ((first.get("geometry") or {}).get("location_type") or "").upper()
    if location_type not in ACCEPTED_LOCATION_TYPES:
        return None
    location = (first.get("geometry") or {}).get("location") or {}
    lat, lng = location.get("lat"), location.get("lng")
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        return None
    if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
        return None
    components = first.get("address_components") or []
    neighborhood = component(components, "neighborhood", "sublocality_level_1", "sublocality")
    return {
        "formatted_address": first.get("formatted_address") or None,
        "neighborhood": neighborhood,
        "locality": component(components, "locality"),
        "county": component(components, "administrative_area_level_2"),
        "state": component(components, "administrative_area_level_1"),
        "postal_code": component(components, "postal_code"),
        "country": component(components, "country"),
        "latitude": float(lat),
        "longitude": float(lng),
        "provider_place_id": first.get("place_id") or None,
        "raw_payload": first,
    }


def _place_id(item: dict[str, Any]) -> str | None:
    raw = item.get("id")
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.strip()
    if value.startswith("places/"):
        value = value.split("/", 1)[1]
    return value or None


def _place_name(item: dict[str, Any]) -> str | None:
    display = item.get("displayName")
    if isinstance(display, dict):
        text = display.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
    return None


def _place_coordinates(item: dict[str, Any]) -> tuple[float, float] | None:
    location = item.get("location")
    if not isinstance(location, dict):
        return None
    lat, lng = location.get("latitude"), location.get("longitude")
    if not isinstance(lat, int | float) or not isinstance(lng, int | float):
        return None
    if not (-90 <= float(lat) <= 90 and -180 <= float(lng) <= 180):
        return None
    return float(lat), float(lng)


def normalize_place_result(
    *,
    category: str,
    item: dict[str, Any],
    origin_lat: float,
    origin_lng: float,
) -> NormalizedPlace | None:
    place_id = _place_id(item)
    name = _place_name(item)
    coordinates = _place_coordinates(item)
    if place_id is None or name is None or coordinates is None:
        return None
    lat, lng = coordinates
    rating = item.get("rating")
    rating_value = float(rating) if isinstance(rating, int | float) else None
    formatted = item.get("formattedAddress")
    return NormalizedPlace(
        provider="google_places",
        provider_place_id=place_id,
        name=name,
        category=category,
        latitude=lat,
        longitude=lng,
        straight_line_distance_meters=haversine_meters(origin_lat, origin_lng, lat, lng),
        rating=rating_value,
        address=formatted.strip() if isinstance(formatted, str) and formatted.strip() else None,
        raw_payload=item,
    )


def group_places(places: list[Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Any]] = {category: [] for category in PLACE_CATEGORIES}
    for place in places:
        category = getattr(place, "category", None) or place.get("category")
        if category in grouped:
            grouped[category].append(place)
    groups = []
    for category in PLACE_CATEGORIES:
        rows = sorted(grouped[category], key=lambda item: _distance(item))
        if not rows:
            continue
        selected = rows[:3]
        groups.append(
            {
                "category": category,
                "place_count": len(rows),
                "nearest_distance_meters": _distance(rows[0]),
                "places": selected,
            }
        )
    return groups


def source_fingerprint(*, neighborhood: str | None, locality: str | None, places: list[Any]) -> str:
    facts = {
        "neighborhood": neighborhood or "",
        "locality": locality or "",
        "places": [
            {
                "id": getattr(place, "provider_place_id", None) or place.get("provider_place_id"),
                "name": getattr(place, "name", None) or place.get("name"),
                "category": getattr(place, "category", None) or place.get("category"),
                "meters": _distance(place),
            }
            for place in sorted(places, key=lambda item: str(getattr(item, "provider_place_id", "") or item.get("provider_place_id")))
        ],
    }
    return hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()


def facts_prompt(*, neighborhood: str | None, locality: str | None, places: list[Any]) -> str:
    lines = [
        "FACTS",
        f"neighborhood: {neighborhood or ''}",
        f"locality: {locality or ''}",
    ]
    for place in places:
        rating = getattr(place, "rating", None)
        if rating is None and isinstance(place, dict):
            rating = place.get("rating")
        lines.append(
            "place: "
            f"name={getattr(place, 'name', None) or place.get('name')}; "
            f"category={getattr(place, 'category', None) or place.get('category')}; "
            f"straight_line_meters={_distance(place)}; "
            f"rating={'' if rating is None else rating}"
        )
    return "\n".join(lines)


def _distance(place: Any) -> int:
    value = getattr(place, "straight_line_distance_meters", None)
    if value is None and isinstance(place, dict):
        value = place.get("straight_line_distance_meters")
    return int(value or 0)
