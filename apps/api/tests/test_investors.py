from datetime import date
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
from investhome_api.models.investor import (
    InvestmentModel,
    InvestorStatus,
    InvestorType,
)

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
        "full_name": "Test Investor",
        "email": "test.investor@example.com",
        "phone": "+1 555 0200",
        "country": "Türkiye",
        "city": "İstanbul",
        "investor_type": InvestorType.INDIVIDUAL.value,
        "status": InvestorStatus.PROSPECT.value,
        "preferred_investment_model": InvestmentModel.RENTAL_INCOME.value,
        "investment_capacity": "1000000.00",
        "minimum_ticket": "100000.00",
        "maximum_ticket": "500000.00",
        "preferred_markets": "Türkiye, UAE",
        "preferred_projects": "Residential",
        "assigned_to": "Emre Kaya",
        "source": "Referral",
        "notes": "Integration test investor",
        "last_contact_date": date(2026, 7, 1).isoformat(),
        "next_follow_up_date": date(2026, 8, 1).isoformat(),
    }
    payload.update(overrides)
    return payload


def test_investors_crud_flow(client: TestClient) -> None:
    create_response = client.post("/investors", json=_create_payload())
    assert create_response.status_code == 201
    created = create_response.json()
    investor_id = created["id"]
    assert created["full_name"] == "Test Investor"
    assert created["status"] == InvestorStatus.PROSPECT.value

    list_response = client.get("/investors")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["page"] == 1

    get_response = client.get(f"/investors/{investor_id}")
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "test.investor@example.com"

    update_response = client.patch(
        f"/investors/{investor_id}",
        json={"status": InvestorStatus.ACTIVE.value, "notes": "Updated in test"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == InvestorStatus.ACTIVE.value

    archive_response = client.delete(f"/investors/{investor_id}")
    assert archive_response.status_code == 200
    assert archive_response.json()["archived_at"] is not None

    hidden_response = client.get("/investors")
    assert hidden_response.json()["total"] == 0

    archived_list_response = client.get("/investors?include_archived=true")
    assert archived_list_response.json()["total"] == 1


def test_investors_filters_pagination_and_sorting(client: TestClient) -> None:
    client.post("/investors", json=_create_payload(full_name="Alpha Investor", country="Türkiye"))
    client.post(
        "/investors",
        json=_create_payload(
            full_name="Beta Investor",
            email="beta.investor@example.com",
            country="United States",
            investor_type=InvestorType.FUND.value,
            status=InvestorStatus.ACTIVE.value,
            preferred_investment_model=InvestmentModel.JOINT_VENTURE.value,
        ),
    )

    filtered = client.get("/investors", params={"country": "United States"})
    assert filtered.status_code == 200
    payload = filtered.json()
    assert payload["total"] == 1
    assert payload["items"][0]["full_name"] == "Beta Investor"

    searched = client.get("/investors", params={"search": "Alpha"})
    assert searched.json()["total"] == 1

    paged = client.get("/investors", params={"page": 1, "page_size": 1, "sort_by": "full_name"})
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1
    assert paged.json()["pages"] == 2


def test_investor_stats(client: TestClient) -> None:
    client.post(
        "/investors",
        json=_create_payload(
            status=InvestorStatus.ACTIVE.value,
            investment_capacity="2000000.00",
        ),
    )
    client.post(
        "/investors",
        json=_create_payload(
            full_name="Invested One",
            email="invested@example.com",
            status=InvestorStatus.INVESTED.value,
            investment_capacity="3000000.00",
        ),
    )

    stats = client.get("/investors/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert body["total"] == 2
    assert body["active"] == 1
    assert body["invested"] == 1
    assert Decimal(body["total_investment_capacity"]) == Decimal("5000000.00")


def test_get_missing_investor_returns_404(client: TestClient) -> None:
    response = client.get(f"/investors/{UUID('00000000-0000-0000-0000-000000000002')}")
    assert response.status_code == 404
