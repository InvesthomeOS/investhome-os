"""NEW website leads stay in the lead list until an explicit opportunity conversion."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.lead import LeadStatus
from investhome_api.models.sales import OpportunityPartyType, SalesOpportunity


def _create_website_lead(client: TestClient, *, name: str = "Website Yeni Lead") -> dict:
    response = client.post(
        "/leads",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}.{uuid4().hex[:6]}@example.com",
            "phone": "05551234567",
            "source": "website",
            "status": LeadStatus.NEW.value,
            "interested_project": "1812 H Place",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_new_lead_is_listed_and_not_an_opportunity(client: TestClient, db: Session) -> None:
    lead = _create_website_lead(client)
    lead_id = lead["id"]

    listed = client.get("/leads", params={"status": "New"})
    assert listed.status_code == 200, listed.text
    ids = {item["id"] for item in listed.json()["items"]}
    assert lead_id in ids
    assert all(item["status"] == LeadStatus.NEW.value for item in listed.json()["items"])

    qualified = client.get("/leads", params={"status": "Qualified"})
    assert qualified.status_code == 200, qualified.text
    assert lead_id not in {item["id"] for item in qualified.json()["items"]}

    opportunities = client.get("/sales/opportunities", params={"lead_id": lead_id})
    assert opportunities.status_code == 200, opportunities.text
    assert opportunities.json()["items"] == []
    assert opportunities.json()["total"] == 0
    db.expire_all()
    assert (
        list(
            db.scalars(
                select(SalesOpportunity).where(SalesOpportunity.lead_id == UUID(lead_id))
            ).all()
        )
        == []
    )


def test_new_lead_is_not_counted_as_qualified_until_qualification(client: TestClient) -> None:
    new_lead = _create_website_lead(client, name="KPI New Lead")
    existing_qualified = client.post(
        "/leads",
        json={
            "full_name": "Already Qualified",
            "email": f"qualified.{uuid4().hex[:6]}@example.com",
            "status": LeadStatus.QUALIFIED.value,
        },
    )
    assert existing_qualified.status_code == 201, existing_qualified.text

    new_list = client.get("/leads", params={"status": "New"}).json()["items"]
    qualified_list = client.get("/leads", params={"status": "Qualified"}).json()["items"]
    new_ids = {item["id"] for item in new_list}
    qualified_ids = {item["id"] for item in qualified_list}

    assert new_lead["id"] in new_ids
    assert new_lead["id"] not in qualified_ids
    assert existing_qualified.json()["id"] in qualified_ids
    assert existing_qualified.json()["id"] not in new_ids
    assert new_ids.isdisjoint(qualified_ids)


def test_qualified_lead_converts_to_opportunity_explicitly(client: TestClient) -> None:
    lead = _create_website_lead(client, name="Convert Lead")
    lead_id = lead["id"]

    in_review = client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": "in_review"},
    )
    assert in_review.status_code == 200, in_review.text
    qualified = client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": "qualified"},
    )
    assert qualified.status_code == 200, qualified.text

    after = client.get(f"/leads/{lead_id}")
    assert after.status_code == 200, after.text
    assert after.json()["status"] == LeadStatus.QUALIFIED.value
    assert lead_id not in {item["id"] for item in client.get("/leads", params={"status": "New"}).json()["items"]}
    assert lead_id in {item["id"] for item in client.get("/leads", params={"status": "Qualified"}).json()["items"]}

    still_empty = client.get("/sales/opportunities", params={"lead_id": lead_id})
    assert still_empty.json()["items"] == []

    created = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead_id,
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead_id,
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    )
    assert created.status_code == 201, created.text
    listed = client.get("/sales/opportunities", params={"lead_id": lead_id})
    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] >= 1
    assert any(item["lead_id"] == lead_id for item in listed.json()["items"])
