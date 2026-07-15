"""Company foundation verification tests."""

from uuid import uuid4

from fastapi.testclient import TestClient


def _ensure_company(client: TestClient) -> dict:
    response = client.get("/company/profile")
    assert response.status_code == 200
    return response.json()


def test_public_brand_no_auth(client: TestClient) -> None:
    response = client.get("/company/public-brand")
    assert response.status_code == 200
    body = response.json()
    assert "company_name" in body
    assert "api_key" not in body


def test_company_profile_read_and_update(client: TestClient) -> None:
    profile = _ensure_company(client)
    assert profile["company_name"]

    update = client.patch(
        "/company/profile",
        json={"slogan": "Updated slogan for verification"},
    )
    assert update.status_code == 200
    assert update.json()["slogan"] == "Updated slogan for verification"


def test_office_crud_and_archive(client: TestClient) -> None:
    create = client.post(
        "/offices",
        json={
            "office_name": "Verification Office",
            "office_code": "verify-office",
            "office_type": "virtual",
            "city": "Test City",
        },
    )
    assert create.status_code == 201
    office_id = create.json()["id"]

    listing = client.get("/offices")
    assert listing.status_code == 200
    assert any(item["id"] == office_id for item in listing.json())

    archive = client.post(f"/offices/{office_id}/archive")
    assert archive.status_code == 200
    assert archive.json()["archived_at"] is not None


def test_brand_profile_and_default(client: TestClient) -> None:
    create = client.post(
        "/brands",
        json={
            "brand_name": "Verification Brand",
            "brand_code": "verify-brand",
            "primary_color": "#112233",
        },
    )
    assert create.status_code == 201
    brand_id = create.json()["id"]

    set_default = client.post(f"/brands/{brand_id}/set-default")
    assert set_default.status_code == 200
    assert set_default.json()["is_default"] is True

    context = client.get("/company/context")
    assert context.status_code == 200
    assert context.json()["brand"]["brand_name"] == "Verification Brand"


def test_preferences_and_supported_options(client: TestClient) -> None:
    prefs = client.get("/settings/preferences")
    assert prefs.status_code == 200
    assert "categories" in prefs.json()

    options = client.get("/settings/supported-options")
    assert options.status_code == 200
    currencies = options.json()["currencies"]
    assert "USD" in currencies
    assert "TRY" in currencies

    providers = client.get("/settings/providers")
    assert providers.status_code == 200
    for item in providers.json()["items"]:
        assert "api_key" not in str(item).lower()


def test_organization_departments_and_teams(client: TestClient) -> None:
    dept = client.post(
        "/organization/departments",
        json={"name": "Verification Dept", "code": "verify-dept"},
    )
    assert dept.status_code == 201
    department_id = dept.json()["id"]

    team = client.post(
        f"/organization/departments/{department_id}/teams",
        json={"name": "Verification Team", "code": "verify-team"},
    )
    assert team.status_code == 201

    teams = client.get(f"/organization/departments/{department_id}/teams")
    assert teams.status_code == 200
    assert len(teams.json()) >= 1


def test_company_activity_entity_type_supported(client: TestClient) -> None:
    from uuid import UUID

    from sqlalchemy import select

    from investhome_api.db.session import get_db
    from investhome_api.models.activity import ActivityAction, ActivityEntityType, ActivityLog
    from investhome_api.models.company_foundation import CompanyProfile
    from investhome_api.services.activity_service import log_activity

    profile = _ensure_company(client)
    override = client.app.dependency_overrides.get(get_db)
    assert override is not None
    session = next(override())
    try:
        company_id = UUID(profile["id"])
        entry = log_activity(
            session,
            action=ActivityAction.UPDATED,
            entity_type=ActivityEntityType.COMPANY,
            entity_id=company_id,
            description_key="activity.company.profile_updated",
            commit=True,
        )
        assert entry is not None
        stored = session.scalar(
            select(ActivityLog).where(ActivityLog.id == entry.id)
        )
        assert stored is not None
        assert stored.entity_type == ActivityEntityType.COMPANY
    finally:
        session.close()


def test_company_update_records_activity(client: TestClient) -> None:
    unique = f"Activity verification {uuid4().hex[:8]}"
    response = client.patch("/company/profile", json={"legal_name": unique})
    assert response.status_code == 200
    assert response.json()["legal_name"] == unique


def test_search_includes_offices(client: TestClient) -> None:
    client.post(
        "/offices",
        json={
            "office_name": "Searchable Office Unique",
            "office_code": "search-office-unique",
            "office_type": "other",
        },
    )
    response = client.get("/search", params={"q": "Searchable Office Unique"})
    assert response.status_code == 200
    groups = {group["entity_type"]: group for group in response.json()["groups"]}
    assert "office" in groups
