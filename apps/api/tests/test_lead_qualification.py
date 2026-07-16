"""Lead qualification integration tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.lead import LeadStatus
from investhome_api.models.lead_qualification import (
    LeadQualification,
    LeadScore,
    LeadTimeline,
    QualificationStatus,
)


def _create_lead(client: TestClient, *, name: str = "Qual Lead") -> dict:
    response = client.post(
        "/leads",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "status": LeadStatus.NEW.value,
            "company": "Acme Corp",
            "preferred_market": "Dubai",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_qualification_crud_and_status(client: TestClient, db: Session) -> None:
    lead = _create_lead(client)
    lead_id = lead["id"]

    get_response = client.get(f"/leads/{lead_id}/qualification")
    assert get_response.status_code == 200
    assert get_response.json()["qualification_status"] == QualificationStatus.NEW.value

    patch_response = client.patch(
        f"/leads/{lead_id}/qualification",
        json={
            "investment_objective": "rental_income",
            "budget_min": "250000.00",
            "budget_max": "500000.00",
            "expected_purchase_timeline": "3_months",
            "cash_or_financing": "cash",
        },
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["budget_min"] == "250000.00"

    review_response = client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.IN_REVIEW.value},
    )
    assert review_response.status_code == 200

    qualify_response = client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.QUALIFIED.value, "notes": "Human approved"},
    )
    assert qualify_response.status_code == 200
    assert qualify_response.json()["qualification_status"] == QualificationStatus.QUALIFIED.value
    assert qualify_response.json()["qualified_by_id"] is not None

    qual = db.scalar(select(LeadQualification).where(LeadQualification.lead_id == UUID(lead_id)))
    assert qual is not None
    assert qual.qualification_status == QualificationStatus.QUALIFIED


def test_lead_score_recalculate(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Score Lead")
    lead_id = lead["id"]

    client.patch(
        f"/leads/{lead_id}/qualification",
        json={
            "budget_min": "100000.00",
            "budget_max": "200000.00",
            "expected_purchase_timeline": "immediate",
            "investment_capacity": "high",
        },
    )
    client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.IN_REVIEW.value},
    )

    score_response = client.post(f"/leads/{lead_id}/score/recalculate", json={})
    assert score_response.status_code == 200
    payload = score_response.json()
    assert 0 <= payload["total_score"] <= 100
    assert len(payload["components"]) == 8

    score_row = db.scalar(select(LeadScore).where(LeadScore.lead_id == UUID(lead_id)))
    assert score_row is not None
    assert score_row.total_score == payload["total_score"]


def test_timeline_aggregation(client: TestClient) -> None:
    lead = _create_lead(client, name="Timeline Lead")
    lead_id = lead["id"]

    client.patch(f"/leads/{lead_id}/qualification", json={"sales_notes": "Initial review"})
    client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.IN_REVIEW.value},
    )

    timeline_response = client.get(f"/leads/{lead_id}/timeline")
    assert timeline_response.status_code == 200
    items = timeline_response.json()["items"]
    assert len(items) >= 2
    assert any("qualification" in item["event_type"] for item in items)


def test_follow_up_flow(client: TestClient) -> None:
    lead = _create_lead(client, name="Follow Up Lead")
    lead_id = lead["id"]
    due_at = (datetime.now(UTC) + timedelta(days=2)).isoformat()

    create_response = client.post(
        f"/leads/{lead_id}/follow-ups",
        json={"follow_up_type": "call", "due_at": due_at, "notes": "Check budget"},
    )
    assert create_response.status_code == 201
    follow_up_id = create_response.json()["id"]

    list_response = client.get(f"/leads/{lead_id}/follow-ups")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    complete_response = client.patch(f"/leads/{lead_id}/follow-ups/{follow_up_id}/complete")
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "completed"


def test_lead_detail_summary(client: TestClient) -> None:
    lead = _create_lead(client, name="Summary Lead")
    lead_id = lead["id"]

    summary_response = client.get(f"/leads/{lead_id}/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["lead_id"] == lead_id
    assert summary["opportunity_count"] == 0


def test_executive_qualification_summary(client: TestClient) -> None:
    _create_lead(client, name="Exec Qual Lead")
    response = client.get("/leads/executive/qualification-summary")
    assert response.status_code == 200
    payload = response.json()
    assert "qualified_count" in payload
    assert "avg_lead_score" in payload


def test_qualification_permissions(auth_client: TestClient) -> None:
    auth_client.post("/auth/login", json={"email": "sales@example.com", "password": "Demo123!"})
    lead = _create_lead(auth_client, name="Perm Lead")
    lead_id = lead["id"]

    auth_client.post("/auth/login", json={"email": "readonly@example.com", "password": "Demo123!"})
    denied = auth_client.patch(
        f"/leads/{lead_id}/qualification",
        json={"sales_notes": "Should fail"},
    )
    assert denied.status_code == 403


def test_activity_logged_on_qualification_update(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Activity Qual Lead")
    lead_id = lead["id"]

    client.patch(f"/leads/{lead_id}/qualification", json={"sales_notes": "Logged update"})

    logs = list(
        db.scalars(
            select(ActivityLog).where(
                ActivityLog.entity_type == ActivityEntityType.LEAD_QUALIFICATION,
            )
        ).all()
    )
    assert any(log.description_key == "activity.lead_qualification.updated" for log in logs)


def test_timeline_domain_entries(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Domain Timeline Lead")
    lead_id = lead["id"]

    client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.IN_REVIEW.value},
    )

    entries = list(
        db.scalars(select(LeadTimeline).where(LeadTimeline.lead_id == UUID(lead_id))).all()
    )
    assert len(entries) >= 1


def test_lead_list_qualification_filter(client: TestClient) -> None:
    lead = _create_lead(client, name="Filter Qual Lead")
    lead_id = lead["id"]

    client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": QualificationStatus.IN_REVIEW.value},
    )

    filtered = client.get("/leads", params={"qualification_status": QualificationStatus.IN_REVIEW.value})
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1
