"""Sales opportunity backend integration tests."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.project import DevelopmentType, ProjectStatus, ProjectType
from investhome_api.models.sales import (
    OpportunityLossReason,
    OpportunityNextAction,
    OpportunityPartyType,
    OpportunityProbabilityHistory,
    OpportunityStage,
    OpportunityTimeline,
    SalesOpportunity,
)
from investhome_api.models.user_auth import User
from investhome_api.services.search_service import global_search

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _create_lead(client: TestClient, *, name: str = "Opportunity Lead") -> dict:
    response = client.post(
        "/leads",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}@example.com",
            "status": LeadStatus.QUALIFIED.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_project(client: TestClient, *, code: str = "PRJ-SALES-001") -> dict:
    response = client.post(
        "/projects",
        json={
            "project_code": code,
            "project_name": "Sales Test Project",
            "project_type": ProjectType.RESIDENTIAL.value,
            "development_type": DevelopmentType.GROUND_UP.value,
            "project_status": ProjectStatus.CONSTRUCTION.value,
        },
    )
    assert response.status_code == 201
    return response.json()


def _opportunity_payload(
    *,
    party_id: str,
    lead_id: str | None = None,
    next_action: str = OpportunityNextAction.CALL.value,
    next_action_date: str | None = None,
) -> dict:
    return {
        "party_id": party_id,
        "party_type": OpportunityPartyType.LEAD.value,
        "lead_id": lead_id,
        "expected_revenue": "500000.00",
        "currency": "USD",
        "probability": 25,
        "next_action": next_action,
        "next_action_date": next_action_date or (date.today() + timedelta(days=3)).isoformat(),
        "source": "Website",
        "notes": "Test opportunity",
    }


def test_sales_opportunity_crud_flow(client: TestClient) -> None:
    lead = _create_lead(client)
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    assert create.status_code == 201
    created = create.json()
    opp_id = created["id"]
    assert created["stage"] == OpportunityStage.NEW.value
    assert created["opportunity_code"].startswith("OPP-")
    assert created["expected_revenue"] == "500000.00"

    listing = client.get("/sales/opportunities")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"/sales/opportunities/{opp_id}")
    assert detail.status_code == 200

    updated = client.patch(
        f"/sales/opportunities/{opp_id}",
        json={"probability": 40, "notes": "Updated notes"},
    )
    assert updated.status_code == 200
    assert updated.json()["probability"] == 40

    archived = client.delete(f"/sales/opportunities/{opp_id}")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    hidden = client.get("/sales/opportunities")
    assert hidden.json()["total"] == 0

    restored = client.post(f"/sales/opportunities/{opp_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_stage_change_rules(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Stage Rules Lead")
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    opp_id = create.json()["id"]

    lost = client.post(
        f"/sales/opportunities/{opp_id}/stage",
        json={"stage": OpportunityStage.LOST.value},
    )
    assert lost.status_code == 422
    assert lost.json()["detail"] == "sales.errors.loss_reason_required"

    lost_ok = client.post(
        f"/sales/opportunities/{opp_id}/stage",
        json={
            "stage": OpportunityStage.LOST.value,
            "loss_reason": OpportunityLossReason.BUDGET.value,
            "loss_notes": "Over budget",
        },
    )
    assert lost_ok.status_code == 200
    assert lost_ok.json()["stage"] == OpportunityStage.LOST.value

    lead2 = _create_lead(client, name="Dormant Lead")
    create2 = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead2["id"], lead_id=lead2["id"]),
    )
    opp2_id = create2.json()["id"]
    dormant_fail = client.post(
        f"/sales/opportunities/{opp2_id}/stage",
        json={"stage": OpportunityStage.DORMANT.value},
    )
    assert dormant_fail.status_code == 422
    assert dormant_fail.json()["detail"] == "sales.errors.dormant_review_date_required"

    dormant_ok = client.post(
        f"/sales/opportunities/{opp2_id}/stage",
        json={
            "stage": OpportunityStage.DORMANT.value,
            "dormant_review_date": (date.today() + timedelta(days=30)).isoformat(),
        },
    )
    assert dormant_ok.status_code == 200

    lead3 = _create_lead(client, name="Cancelled Lead")
    create3 = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead3["id"], lead_id=lead3["id"]),
    )
    opp3_id = create3.json()["id"]
    cancelled_fail = client.post(
        f"/sales/opportunities/{opp3_id}/stage",
        json={"stage": OpportunityStage.CANCELLED.value},
    )
    assert cancelled_fail.status_code == 422

    cancelled_ok = client.post(
        f"/sales/opportunities/{opp3_id}/stage",
        json={
            "stage": OpportunityStage.CANCELLED.value,
            "cancelled_reason": "Duplicate record",
        },
    )
    assert cancelled_ok.status_code == 200

    lead4 = _create_lead(client, name="Won Lead")
    create4 = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead4["id"], lead_id=lead4["id"]),
    )
    opp4_id = create4.json()["id"]
    for stage in (
        OpportunityStage.QUALIFIED,
        OpportunityStage.MEETING_SCHEDULED,
        OpportunityStage.MEETING_COMPLETED,
        OpportunityStage.INVENTORY_MATCHING,
        OpportunityStage.PROPOSAL_PREPARATION,
        OpportunityStage.PROPOSAL_SENT,
        OpportunityStage.NEGOTIATION,
        OpportunityStage.RESERVATION,
        OpportunityStage.DEPOSIT_PENDING,
    ):
        response = client.post(
            f"/sales/opportunities/{opp4_id}/stage",
            json={"stage": stage.value},
        )
        assert response.status_code == 200, stage.value

    won_fail = client.post(
        f"/sales/opportunities/{opp4_id}/stage",
        json={"stage": OpportunityStage.WON.value},
    )
    assert won_fail.status_code == 422
    assert won_fail.json()["detail"] == "sales.errors.invalid_stage_transition"

    for stage in (OpportunityStage.CONTRACT, OpportunityStage.CLOSING_HANDOFF):
        response = client.post(
            f"/sales/opportunities/{opp4_id}/stage",
            json={"stage": stage.value},
        )
        assert response.status_code == 200

    won_ok = client.post(
        f"/sales/opportunities/{opp4_id}/stage",
        json={"stage": OpportunityStage.WON.value},
    )
    assert won_ok.status_code == 200
    assert won_ok.json()["stage"] == OpportunityStage.WON.value

    timeline = client.get(f"/sales/opportunities/{opp4_id}/timeline")
    assert timeline.status_code == 200
    events = timeline.json()
    assert len(events) >= 5
    assert any(event["event_type"] == "sales.won" for event in events)


def test_probability_history(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Probability Lead")
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    opp_id = create.json()["id"]

    changed = client.post(
        f"/sales/opportunities/{opp_id}/probability",
        json={"probability": 55, "reason": "Strong interest"},
    )
    assert changed.status_code == 200
    assert changed.json()["probability"] == 55

    history = db.scalars(
        select(OpportunityProbabilityHistory).where(
            OpportunityProbabilityHistory.opportunity_id == UUID(opp_id)
        )
    ).all()
    assert len(history) == 1
    assert history[0].old_probability == 25
    assert history[0].new_probability == 55


def test_timeline_on_create_and_stage(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Timeline Lead")
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    opp_id = UUID(create.json()["id"])

    client.post(
        f"/sales/opportunities/{opp_id}/stage",
        json={"stage": OpportunityStage.QUALIFIED.value},
    )

    entries = db.scalars(
        select(OpportunityTimeline).where(OpportunityTimeline.opportunity_id == opp_id)
    ).all()
    assert any(entry.event_type == "sales.opportunity.created" for entry in entries)
    assert any(entry.event_type == "sales.stage.changed" for entry in entries)


def test_permissions_enforced(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    lead = _create_lead(auth_client, name="Permission Lead")
    _login(auth_client, "readonly@example.com")

    denied_create = auth_client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    assert denied_create.status_code == 403

    denied_list = auth_client.get("/sales/opportunities")
    assert denied_list.status_code == 403

    _login(auth_client, "sales@example.com")
    allowed = auth_client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    assert allowed.status_code == 201


def test_search_provider_finds_opportunity(client: TestClient) -> None:
    lead = _create_lead(client, name="Searchable Opportunity Lead")
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    code = create.json()["opportunity_code"]

    response = client.get(f"/search?q={code}&entity_types=sales_opportunity")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    group = next(
        (item for item in payload["groups"] if item["entity_type"] == "sales_opportunity"),
        None,
    )
    assert group is not None
    assert any(item["title"] == code for item in group["items"])


def test_dashboard_and_pipeline_empty(client: TestClient) -> None:
    metrics = client.get("/sales/opportunities/dashboard/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["open_opportunities"] == 0
    assert body["pipeline_value"] == "0"

    pipeline = client.get("/sales/opportunities/pipeline")
    assert pipeline.status_code == 200
    assert pipeline.json()["total"] == 0


def test_dashboard_and_pipeline_with_data(client: TestClient) -> None:
    lead = _create_lead(client, name="Dashboard Lead")
    client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )

    metrics = client.get("/sales/opportunities/dashboard/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["open_opportunities"] == 1
    assert Decimal(metrics.json()["pipeline_value"]) == Decimal("500000.00")

    pipeline = client.get("/sales/opportunities/pipeline")
    assert pipeline.status_code == 200
    assert pipeline.json()["total"] == 1
    assert pipeline.json()["stages"].get(OpportunityStage.NEW.value) == 1


def test_executive_summary(client: TestClient) -> None:
    lead = _create_lead(client, name="Executive Lead")
    client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    response = client.get("/sales/opportunities/executive-summary")
    assert response.status_code == 200
    body = response.json()
    assert Decimal(body["pipeline_value"]) == Decimal("500000.00")
    assert body["no_follow_up_count"] == 0


def test_link_project(client: TestClient) -> None:
    lead = _create_lead(client, name="Project Link Lead")
    project = _create_project(client)
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    opp_id = create.json()["id"]

    linked = client.post(
        f"/sales/opportunities/{opp_id}/projects",
        json={"project_id": project["id"]},
    )
    assert linked.status_code == 201
    assert linked.json()["project_id"] == project["id"]

    timeline = client.get(f"/sales/opportunities/{opp_id}/timeline")
    assert any(event["event_type"] == "sales.project.linked" for event in timeline.json())


def test_next_action_required_on_open_opportunity(client: TestClient) -> None:
    lead = _create_lead(client, name="Follow Up Lead")
    response = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "sales.errors.next_action_required"


def test_activity_logged_on_create(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Activity Lead")
    create = client.post(
        "/sales/opportunities",
        json=_opportunity_payload(party_id=lead["id"], lead_id=lead["id"]),
    )
    opp_id = UUID(create.json()["id"])

    logs = db.scalars(
        select(ActivityLog).where(
            ActivityLog.entity_type == ActivityEntityType.SALES_OPPORTUNITY,
            ActivityLog.entity_id == opp_id,
        )
    ).all()
    assert len(logs) >= 1
    assert any(log.description_key == "activity.sales_opportunity.created" for log in logs)
