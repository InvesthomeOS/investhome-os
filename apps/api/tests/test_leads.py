from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from investhome_api.db.base import Base
from investhome_api.db.session import get_db
from investhome_api.main import app
from investhome_api.models.lead import LeadStatus

SQLALCHEMY_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def client() -> TestClient:
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Test Lead",
        "email": "test.lead@example.com",
        "phone": "+1 555 0100",
        "country": "United States",
        "source": "Website",
        "status": LeadStatus.NEW.value,
        "assigned_to": "Sarah Chen",
        "estimated_budget": "750000.00",
        "interested_project": "Demo Tower",
        "notes": "Integration test lead",
    }
    payload.update(overrides)
    return payload


def test_leads_crud_flow(client: TestClient) -> None:
    create_response = client.post("/leads", json=_create_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    lead_id = created["id"]
    assert created["full_name"] == "Test Lead"
    assert created["status"] == LeadStatus.NEW.value

    list_response = client.get("/leads")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    get_response = client.get(f"/leads/{lead_id}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "test.lead@example.com"

    update_response = client.patch(
        f"/leads/{lead_id}",
        json={"status": LeadStatus.QUALIFIED.value, "notes": "Updated in test"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == LeadStatus.QUALIFIED.value

    archive_response = client.delete(f"/leads/{lead_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    hidden_response = client.get("/leads")
    assert hidden_response.json()["total"] == 0

    archived_list_response = client.get("/leads?include_archived=true")
    assert archived_list_response.json()["total"] == 1


def test_leads_filters(client: TestClient) -> None:
    client.post("/leads", json=_create_payload(full_name="Alpha Lead", source="Website"))
    client.post(
        "/leads",
        json=_create_payload(
            full_name="Beta Lead",
            email="beta.lead@example.com",
            source="Referral",
            status=LeadStatus.CONTACTED.value,
        ),
    )

    filtered = client.get("/leads", params={"source": "Referral"})
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["full_name"] == "Beta Lead"

    searched = client.get("/leads", params={"search": "Alpha"})
    assert searched.json()["total"] == 1


def test_get_missing_lead_returns_404(client: TestClient) -> None:
    response = client.get(f"/leads/{UUID('00000000-0000-0000-0000-000000000001')}")
    assert response.status_code == 404
