"""Location intelligence uses mocked providers. These tests never call Google."""

from __future__ import annotations

import asyncio
import inspect
import logging
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from investhome_api.api.deps.auth import get_current_user
from investhome_api.config.settings import get_settings
from investhome_api.models.project import Project, ProjectStatus, ProjectType
from investhome_api.models.project_location import ProjectLocationProfile, ProjectNearbyPlace
from investhome_api.models.user_auth import User, UserStatus
from investhome_api.schemas.project import ProjectUpdate
from investhome_api.services.location_intelligence import queue as location_queue
from investhome_api.services.location_intelligence.google_provider import (
    GEOCODE_URL,
    PLACES_FIELD_MASK,
    PLACES_NEW_URL,
    GoogleLocationProvider,
    LocationProviderDisabled,
    LocationProviderError,
)
from investhome_api.services.location_intelligence.normalize import (
    CATEGORY_INCLUDED_TYPES,
    PLACE_CATEGORIES,
    PLACE_SEARCHES,
    SEARCH_RADIUS_METERS,
    SUPPORTED_INCLUDED_TYPES,
    facts_prompt,
    format_project_address,
    group_places,
    haversine_meters,
    normalize_geocode_result,
    normalize_place_result,
)
from investhome_api.services.location_intelligence.service import run_location_refresh
from investhome_api.services.project_assistant.llm_provider import LLMProviderError, LLMResult
from investhome_api.services.project_service import update_project


def _project(db, **address) -> Project:
    project = Project(
        id=uuid4(),
        project_code=f"LOC-{uuid4().hex[:8]}",
        project_name="Location Project",
        project_type=ProjectType.RESIDENTIAL,
        project_status=ProjectStatus.PIPELINE,
        address=address.get("address", "3220 16th St NW"),
        city=address.get("city", "Washington"),
        state=address.get("state", "DC"),
        postal_code=address.get("postal_code", "20009"),
        country=address.get("country", "United States"),
    )
    db.add(project)
    db.commit()
    return project


def _user(db) -> User:
    user = User(
        id=uuid4(),
        full_name="Location Editor",
        email=f"loc-{uuid4().hex[:8]}@example.com",
        hashed_password="not-used",
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.commit()
    return user


def _settings(**overrides):
    values = {
        "google_maps_api_key": "test-key",
        "google_geocoding_enabled": True,
        "google_places_enabled": True,
        "ai_provider": "mock",
    }
    values.update(overrides)
    return get_settings().model_copy(update=values)


def _geocode(*, neighborhood: str | None = "Adams Morgan", location_type: str = "ROOFTOP") -> dict:
    components = [
        {"long_name": "Washington", "types": ["locality", "political"]},
        {"long_name": "District of Columbia", "types": ["administrative_area_level_1", "political"]},
        {"long_name": "United States", "types": ["country", "political"]},
        {"long_name": "20009", "types": ["postal_code"]},
    ]
    if neighborhood:
        components.append({"long_name": neighborhood, "types": ["neighborhood", "political"]})
    return {
        "status": "OK",
        "results": [
            {
                "formatted_address": "3220 16th St NW, Washington, DC 20009, USA",
                "place_id": "place-3220",
                "address_components": components,
                "geometry": {
                    "location": {"lat": 38.9321, "lng": -77.0365},
                    "location_type": location_type,
                },
            }
        ],
    }


def _place(place_id: str = "metro-1", name: str = "Columbia Heights Station", rating: float | None = 4.2) -> dict:
    item = {
        "id": place_id,
        "displayName": {"text": name, "languageCode": "en"},
        "formattedAddress": "14th St NW, Washington, DC",
        "location": {"latitude": 38.9284, "longitude": -77.0326},
        "primaryType": "transit_station",
        "types": ["transit_station"],
        "googleMapsUri": "https://maps.google.com/?cid=1",
    }
    if rating is not None:
        item["rating"] = rating
    return {"places": [item]}


def _geocode_transport(geocode: dict):
    def transport(url: str, params: dict[str, str]) -> dict:
        if url == GEOCODE_URL:
            return geocode
        raise AssertionError(url)

    return transport


def _places_transport(
    places: dict | None,
    *,
    fail_places: bool = False,
    match_types: tuple[str, ...] = ("transit_station",),
):
    def transport(url: str, body: dict, headers: dict) -> dict:
        if "nearbysearch" in url:
            raise AssertionError("legacy nearby search")
        if fail_places:
            raise LocationProviderError("places unavailable")
        included = (body.get("includedTypes") or [None])[0]
        rows = (places or {}).get("places") or []
        if not rows or included not in match_types:
            return {"places": []}
        return places

    return transport


def _provider(
    settings,
    geocode: dict,
    places: dict | None = None,
    *,
    fail_places: bool = False,
    match_types: tuple[str, ...] = ("transit_station",),
):
    return GoogleLocationProvider(
        settings,
        _geocode_transport(geocode),
        places_transport=_places_transport(places, fail_places=fail_places, match_types=match_types),
    )


def test_address_normalization():
    project = Project(address=" 3220 16th St NW ", address_line2=" ", city="Washington", state="DC", country="United States")
    assert format_project_address(project) == "3220 16th St NW, Washington, DC, United States"


def test_provider_disabled_makes_no_call(db):
    project = _project(db)
    called = {"n": 0}

    def transport(url, params):
        called["n"] += 1
        return {}

    result = run_location_refresh(
        db,
        project.id,
        settings=_settings(google_geocoding_enabled=False, google_places_enabled=False),
        geocoder=GoogleLocationProvider(_settings(google_geocoding_enabled=False), transport),
    )
    assert result == "disabled"
    assert called["n"] == 0
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.geocode_status.value == "disabled"


def test_missing_key_makes_no_call():
    called = {"n": 0}
    settings = _settings(google_maps_api_key=None, google_geocoding_enabled=True)
    provider = GoogleLocationProvider(settings, lambda url, params: called.__setitem__("n", 1))
    with pytest.raises(LocationProviderDisabled):
        provider.geocode("3220 16th St NW, Washington, DC")
    assert called["n"] == 0


def test_successful_geocode_and_places(db):
    project = _project(db)
    settings = _settings()
    provider = _provider(settings, _geocode(), _place())
    assert run_location_refresh(db, project.id, settings=settings, geocoder=provider) == "success"
    db.refresh(project)
    assert float(project.latitude) == pytest.approx(38.9321)
    assert float(project.longitude) == pytest.approx(-77.0365)
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.neighborhood == "Adams Morgan"
    assert profile.locality == "Washington"
    assert profile.provider == "google_geocoding"
    place = db.scalar(select(ProjectNearbyPlace).where(ProjectNearbyPlace.project_id == project.id))
    assert place.provider == "google_places"
    assert place.provider_place_id == "metro-1"
    assert place.name == "Columbia Heights Station"
    assert place.address == "14th St NW, Washington, DC"
    assert place.category == "transit"
    assert place.walking_distance_meters is None
    assert place.walking_duration_minutes is None
    assert float(place.rating) == pytest.approx(4.2)
    assert place.straight_line_distance_meters > 0


def test_failed_geocode_keeps_empty(db):
    project = _project(db)
    settings = _settings()
    provider = _provider(settings, {"status": "ZERO_RESULTS", "results": []})
    assert run_location_refresh(db, project.id, settings=settings, geocoder=provider) == "failed"
    db.refresh(project)
    assert project.latitude is None
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.geocode_status.value == "failed"


def test_geocode_without_neighborhood_stays_null(db):
    project = _project(db)
    settings = _settings()
    provider = _provider(settings, _geocode(neighborhood=None), {"places": []})
    run_location_refresh(db, project.id, settings=settings, geocoder=provider)
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.neighborhood is None
    assert profile.locality == "Washington"
    assert normalize_geocode_result(_geocode(location_type="APPROXIMATE")) is None


def test_duplicate_provider_place_is_stored_once(db):
    project = _project(db)
    places = _place()

    settings = _settings()
    provider = _provider(settings, _geocode(), places, match_types=("restaurant", "cafe"))
    run_location_refresh(db, project.id, settings=settings, geocoder=provider)
    run_location_refresh(db, project.id, settings=settings, geocoder=provider)
    count = db.scalar(select(func.count()).select_from(ProjectNearbyPlace).where(ProjectNearbyPlace.project_id == project.id))
    assert count == 1


def test_place_normalization_and_grouping_and_distance():
    origin = (38.9321, -77.0365)
    normalized = normalize_place_result(
        category="grocery",
        item=_place("grocery-1", "Whole Foods", rating=None)["places"][0],
        origin_lat=origin[0],
        origin_lng=origin[1],
    )
    assert normalized is not None
    assert normalized.rating is None
    assert normalized.straight_line_distance_meters == haversine_meters(origin[0], origin[1], 38.9284, -77.0326)
    assert haversine_meters(0, 0, 0, 0) == 0
    groups = group_places([normalized])
    assert groups[0]["category"] == "grocery"
    assert groups[0]["place_count"] == 1
    assert groups[0]["nearest_distance_meters"] == normalized.straight_line_distance_meters


def test_ai_uses_only_stored_facts_and_skips_repeat(db):
    project = _project(db)
    settings = _settings(ai_provider="openai")
    calls = {"n": 0, "user": ""}

    class Recorder:
        name = "openai"

        def generate(self, *, system, user, timeout_seconds=45.0):
            calls["n"] += 1
            calls["user"] = user
            return LLMResult(
                answer="Stored transit is nearby.",
                provider="openai",
                model="gpt-test",
                input_tokens=1,
                output_tokens=1,
            )

    provider = _provider(settings, _geocode(), _place())
    run_location_refresh(db, project.id, settings=settings, geocoder=provider, llm=Recorder())
    run_location_refresh(db, project.id, settings=settings, geocoder=provider, llm=Recorder())
    assert calls["n"] == 1
    assert calls["user"].startswith("FACTS")
    assert "Columbia Heights Station" in calls["user"]
    assert "Adams Morgan" in calls["user"]
    assert "Walk Score" not in calls["user"]
    assert calls["user"] == facts_prompt(
        neighborhood="Adams Morgan",
        locality="Washington",
        places=list(db.scalars(select(ProjectNearbyPlace).where(ProjectNearbyPlace.project_id == project.id)).all()),
    )


def test_ai_failure_keeps_location_facts(db):
    project = _project(db)
    settings = _settings(ai_provider="openai")

    class Boom:
        name = "openai"

        def generate(self, *, system, user, timeout_seconds=45.0):
            raise LLMProviderError("unavailable", category="request", provider="openai")

    provider = _provider(settings, _geocode(), _place())
    assert run_location_refresh(db, project.id, settings=settings, geocoder=provider, llm=Boom()) == "success"
    assert db.scalar(select(func.count()).select_from(ProjectNearbyPlace).where(ProjectNearbyPlace.project_id == project.id)) == 1


def test_same_address_provider_failure_keeps_last_success(db):
    project = _project(db)
    settings = _settings()
    ok = _provider(settings, _geocode(), _place())
    run_location_refresh(db, project.id, settings=settings, geocoder=ok)

    def fail(url, params):
        raise LocationProviderError("geocoder down")

    assert run_location_refresh(db, project.id, settings=settings, geocoder=GoogleLocationProvider(settings, fail)) == "failed"
    db.refresh(project)
    assert float(project.latitude) == pytest.approx(38.9321)
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.geocode_status.value == "success"
    assert profile.last_error == "geocoder down"


def test_address_change_queues_refresh_without_calling_provider(db, monkeypatch):
    project = _project(db)
    user = _user(db)
    queued: list = []
    monkeypatch.setattr(
        "investhome_api.services.project_service.enqueue_location_refresh",
        lambda project_id: queued.append(project_id) or "queued",
    )
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider called")))
    update_project(db, project.id, ProjectUpdate(city="Arlington"), actor=user)
    assert queued == [project.id]
    db.refresh(project)
    assert project.city == "Arlington"
    assert project.latitude is None
    profile = db.scalar(select(ProjectLocationProfile).where(ProjectLocationProfile.project_id == project.id))
    assert profile.geocode_status.value == "pending"


def test_overview_get_never_calls_provider(client, db, monkeypatch):
    project = _project(db)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("provider called")))
    monkeypatch.setattr(
        GoogleLocationProvider,
        "geocode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("geocode called")),
    )
    response = client.get(f"/projects/{project.id}/location-intelligence")
    assert response.status_code == 200
    body = response.json()
    assert body["nearby_places"] == []
    assert body["latitude"] is None
    assert body["ai_summary"] is None


def test_manual_refresh_enqueues_and_permission_blocks(client, db, monkeypatch):
    project = _project(db)
    calls = {"n": 0}
    monkeypatch.setattr(
        "investhome_api.api.routes.projects.provider_configured",
        lambda *args, **kwargs: True,
    )
    monkeypatch.setattr(
        "investhome_api.api.routes.projects.enqueue_location_refresh",
        lambda project_id: calls.__setitem__("n", calls["n"] + 1) or "queued",
    )
    monkeypatch.setattr(
        GoogleLocationProvider,
        "geocode",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("geocode called")),
    )
    allowed = client.post(f"/projects/{project.id}/location-intelligence/refresh")
    assert allowed.status_code == 200
    assert allowed.json()["status"] == "queued"
    assert calls["n"] == 1

    user = _user(db)
    monkeypatch.setenv("API_AUTH_ENABLED", "true")
    get_settings.cache_clear()
    monkeypatch.setattr("investhome_api.api.deps.auth.user_has_permission", lambda *args, **kwargs: False)
    client.app.dependency_overrides[get_current_user] = lambda: user
    try:
        denied = client.post(f"/projects/{project.id}/location-intelligence/refresh")
        assert denied.status_code == 403
    finally:
        client.app.dependency_overrides.clear()
        get_settings.cache_clear()


def test_refresh_rate_limit_and_job_id(monkeypatch):
    project_id = uuid4()
    monkeypatch.setattr(location_queue, "_acquire_lock", lambda project_id: False)
    assert location_queue.enqueue_location_refresh(project_id) == "already_queued"

    captured = {}

    class Pool:
        async def enqueue_job(self, name, raw_id, _job_id=None):
            captured["name"] = name
            captured["job_id"] = _job_id

        async def close(self):
            return None

    async def create_pool(_settings):
        return Pool()

    monkeypatch.setattr("arq.create_pool", create_pool)
    asyncio.run(location_queue._enqueue(project_id))
    assert captured["job_id"] == f"location-intel:{project_id}"


def test_dry_run_reads_without_writing_or_leaking_key(db, monkeypatch):
    project = _project(db)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-key")
    monkeypatch.setenv("GOOGLE_GEOCODING_ENABLED", "true")
    get_settings.cache_clear()
    from investhome_api.services.location_intelligence.dry_run import inspect_project

    report = inspect_project(project_code=project.project_code, project_id=None)
    assert report["writes"] == 0
    assert report["found"] is True
    assert report["address_present"] is True
    assert report["google_maps_api_key_present"] is True
    assert "super-secret-key" not in str(report)
    assert db.scalar(select(func.count()).select_from(ProjectLocationProfile)) == 0
    get_settings.cache_clear()


def test_places_api_new_request_and_category_mapping(monkeypatch, caplog):
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"places": []}

    def post(url, json=None, headers=None, timeout=None):
        captured["url"] = url
        captured["method"] = "POST"
        captured["json"] = json
        captured["headers"] = headers
        return Response()

    def reject_get(*_args, **_kwargs):
        raise AssertionError("legacy get")

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "get", reject_get)
    provider = GoogleLocationProvider(_settings())
    project_id = "d08ffa5a-bb69-4eaf-976c-b8ceae218e41"
    with caplog.at_level(logging.INFO):
        rows = provider.nearby(
            latitude=38.9321,
            longitude=-77.0365,
            place_type="transit_station",
            category="transit",
            limit=5,
            project_id=project_id,
        )
    assert rows == []
    assert captured["method"] == "POST"
    assert captured["url"] == PLACES_NEW_URL
    assert captured["headers"]["Content-Type"] == "application/json"
    assert captured["headers"]["X-Goog-Api-Key"] == "test-key"
    assert captured["headers"]["X-Goog-FieldMask"] == PLACES_FIELD_MASK
    assert "places.rating" not in PLACES_FIELD_MASK
    body = captured["json"]
    assert body["includedTypes"] == ["transit_station"]
    assert body["maxResultCount"] == 5
    center = body["locationRestriction"]["circle"]
    assert center["center"] == {"latitude": 38.9321, "longitude": -77.0365}
    assert center["radius"] == float(SEARCH_RADIUS_METERS)
    assert set(CATEGORY_INCLUDED_TYPES) == set(PLACE_CATEGORIES)
    for category, place_type, limit in PLACE_SEARCHES:
        assert place_type in CATEGORY_INCLUDED_TYPES[category]
        assert place_type in SUPPORTED_INCLUDED_TYPES
        assert 1 <= limit <= 20
    assert "test-key" not in caplog.text
    assert project_id in caplog.text
    assert "results=0" in caplog.text


def test_places_structured_error_is_not_empty(monkeypatch, caplog):
    class Response:
        status_code = 403

        def json(self):
            return {
                "error": {
                    "code": 403,
                    "status": "PERMISSION_DENIED",
                    "message": "Places API (New) has not been used for key test-key",
                }
            }

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Response())
    provider = GoogleLocationProvider(_settings())
    with caplog.at_level(logging.WARNING), pytest.raises(LocationProviderError) as caught:
        provider.nearby(
            latitude=38.9321,
            longitude=-77.0365,
            place_type="park",
            category="parks",
            limit=4,
            project_id="project-1",
        )
    assert caught.value.http_status == 403
    assert "PERMISSION_DENIED" in str(caught.value)
    assert "test-key" not in str(caught.value)
    assert "test-key" not in caplog.text
    assert "nearbysearch" not in caplog.text


def test_unsupported_place_type_does_not_call_google(monkeypatch):
    def reject_post(*_args, **_kwargs):
        raise AssertionError("posted")

    monkeypatch.setattr(httpx, "post", reject_post)
    provider = GoogleLocationProvider(_settings())
    with pytest.raises(LocationProviderError, match="unsupported place type"):
        provider.nearby(
            latitude=1,
            longitude=2,
            place_type="not_a_place_type",
            category="retail",
            limit=3,
        )


def test_location_intelligence_does_not_call_legacy_nearby_search():
    import investhome_api.services.location_intelligence.dry_run as dry_run
    import investhome_api.services.location_intelligence.google_provider as provider
    import investhome_api.services.location_intelligence.jobs as jobs
    import investhome_api.services.location_intelligence.normalize as normalize
    import investhome_api.services.location_intelligence.queue as queue
    import investhome_api.services.location_intelligence.service as service

    modules = (dry_run, provider, jobs, normalize, queue, service)
    source = "\n".join(inspect.getsource(module) for module in modules)
    assert "nearbysearch" not in source
    assert PLACES_NEW_URL in source

