"""API shapes for stored location intelligence. No provider payloads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NearbyPlaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str
    latitude: float
    longitude: float
    straight_line_distance_meters: int
    walking_distance_meters: int | None = None
    walking_duration_minutes: int | None = None
    rating: float | None = None
    address: str | None = None


class AmenityGroupResponse(BaseModel):
    category: str
    place_count: int
    nearest_distance_meters: int | None = None
    places: list[NearbyPlaceResponse] = Field(default_factory=list)


class LocationAiSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary_text: str
    model_provider: str | None = None
    model_name: str | None = None
    prompt_version: str | None = None
    generated_at: datetime | None = None


class LocationIntelligenceResponse(BaseModel):
    project_id: UUID
    status: str
    formatted_address: str | None = None
    neighborhood: str | None = None
    locality: str | None = None
    county: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    provider: str | None = None
    fetched_at: datetime | None = None
    refreshed_at: datetime | None = None
    nearby_places: list[NearbyPlaceResponse] = Field(default_factory=list)
    amenity_groups: list[AmenityGroupResponse] = Field(default_factory=list)
    ai_summary: LocationAiSummaryResponse | None = None
    can_refresh: bool = False


class LocationRefreshResponse(BaseModel):
    status: str
