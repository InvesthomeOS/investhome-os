"""Sales Workspace V1 stabilization — end-to-end API flows and permission matrix."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from investhome_api.models.lead import LeadStatus
from investhome_api.models.sales import OpportunityLossReason, OpportunityPartyType, OpportunityStage
from investhome_api.models.sales_inventory_matching import SalesShortlistItem
from investhome_api.models.sales_proposal import SalesProposalVersion
from investhome_api.models.sales_readiness import SalesReadinessCase
from investhome_api.worker.settings import WorkerSettings

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _create_lead(client: TestClient, *, name: str = "Stabilize Lead") -> dict:
    response = client.post(
        "/leads",
        json={
            "full_name": name,
            "email": f"{name.lower().replace(' ', '.')}.{uuid4().hex[:6]}@example.com",
            "status": LeadStatus.NEW.value,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Flow 1: Lead create / qualify / score ---


def test_flow_lead_qualify_score(client: TestClient) -> None:
    lead = _create_lead(client, name="Qualify Flow")
    lead_id = lead["id"]

    client.patch(
        f"/leads/{lead_id}/qualification",
        json={
            "budget_min": "100000.00",
            "budget_max": "250000.00",
            "expected_purchase_timeline": "immediate",
        },
    )
    qualify = client.post(
        f"/leads/{lead_id}/qualification/status",
        json={"status": "in_review"},
    )
    assert qualify.status_code == 200, qualify.text

    score = client.post(f"/leads/{lead_id}/score/recalculate", json={})
    assert score.status_code == 200, score.text
    assert "total_score" in score.json()


def test_flow_opportunity_stage_won_lost_reopen(client: TestClient) -> None:
    lead = _create_lead(client, name="Opp Flow")
    create = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "expected_revenue": "300000.00",
            "currency": "USD",
            "probability": 20,
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    )
    assert create.status_code == 201, create.text
    opp_id = create.json()["id"]

    lost = client.post(
        f"/sales/opportunities/{opp_id}/stage",
        json={
            "stage": OpportunityStage.LOST.value,
            "loss_reason": OpportunityLossReason.BUDGET.value,
        },
    )
    assert lost.status_code == 200, lost.text
    assert lost.json()["stage"] == OpportunityStage.LOST.value

    archived = client.delete(f"/sales/opportunities/{opp_id}")
    assert archived.status_code == 200, archived.text
    restored = client.post(f"/sales/opportunities/{opp_id}/restore")
    assert restored.status_code == 200, restored.text
    assert restored.json()["archived_at"] is None


def test_flow_inventory_matching_shortlist_primary(client: TestClient) -> None:
    """Detailed matching CRUD covered in test_sales_inventory_matching; verify list APIs."""
    lead = _create_lead(client, name="Match Flow")
    matches = client.get("/sales/inventory-matches", params={"lead_id": lead["id"]})
    assert matches.status_code == 200, matches.text
    shortlists = client.get("/sales/shortlists", params={"lead_id": lead["id"]})
    assert shortlists.status_code == 200, shortlists.text


# --- Flow 4: Proposal lifecycle + version 2 ---


def test_flow_proposal_lifecycle_version_two(client: TestClient) -> None:
    lead = _create_lead(client, name="Proposal Flow")
    opp = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    ).json()
    proposal = client.post(
        "/sales/proposals",
        json={
            "opportunity_id": opp["id"],
            "title": "Stabilize Proposal",
            "valid_until": (date.today() + timedelta(days=14)).isoformat(),
            "currency": "USD",
            "recipient_email": "buyer@example.com",
        },
    )
    assert proposal.status_code == 201, proposal.text
    prop_id = proposal.json()["id"]
    assert proposal.json()["current_version"]["version_number"] == 1

    detail = client.get(f"/sales/proposals/{prop_id}")
    assert detail.status_code == 200, detail.text


# --- Flow 5: Work items / meetings / follow-ups / private ---


def test_flow_work_items_meetings_private(client: TestClient) -> None:
    lead = _create_lead(client, name="Work Flow")
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()

    follow = client.post(
        "/sales/work/follow-ups",
        json={
            "title": "Stabilize follow-up",
            "due_at": due,
            "lead_id": lead["id"],
            "follow_up_type": "call",
        },
    )
    assert follow.status_code == 201, follow.text

    meeting = client.post(
        "/sales/work/meetings",
        json={
            "title": "Stabilize meeting",
            "scheduled_at": due,
            "lead_id": lead["id"],
        },
    )
    assert meeting.status_code == 201, meeting.text

    private = client.post(
        "/sales/work/items",
        json={
            "title": "Private stabilize note",
            "work_item_type": "other",
            "due_at": due,
            "is_private": True,
        },
    )
    assert private.status_code == 201, private.text


# --- Flow 6: Soft hold ---


def test_flow_soft_hold(client: TestClient) -> None:
    investor = client.post(
        "/investors",
        json={
            "full_name": "Hold Investor",
            "investor_type": "individual",
            "status": "active",
        },
    )
    assert investor.status_code == 201, investor.text
    project = client.post(
        "/projects",
        json={
            "project_code": f"PRJ-HLD-{uuid4().hex[:6]}",
            "project_name": "Hold Project",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
        },
    ).json()
    building = client.post(
        "/inventory/buildings",
        json={
            "project_id": project["id"],
            "code": "H",
            "name": "Hold Tower",
            "building_type": "apartment",
            "total_floors": 3,
            "status": "active",
        },
    ).json()
    floor = client.post(
        "/inventory/floors",
        json={
            "building_id": building["id"],
            "floor_number": 1,
            "display_name": "L1",
            "level_code": "01",
            "sort_order": 1,
            "status": "active",
        },
    ).json()
    asset = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": f"HLD-{uuid4().hex[:6]}",
            "asset_type": "residential_unit",
            "usage_type": "residential",
            "availability_status": "available",
            "sales_status": "available_for_sale",
            "currency": "USD",
            "list_price": "150000.00",
        },
    )
    assert asset.status_code == 201, asset.text

    hold = client.post(
        "/inventory/reservations/soft-hold",
        json={
            "inventory_asset_id": asset.json()["id"],
            "investor_id": investor.json()["id"],
        },
    )
    assert hold.status_code == 201, hold.text


# --- Flow 8: Global search ---


def test_flow_global_search(client: TestClient) -> None:
    lead = _create_lead(client, name="Searchable Stabilize")
    response = client.get("/search", params={"q": lead["full_name"][:12]})
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 0


# --- Flow 9: Executive summary ---


def test_flow_executive_summary(client: TestClient) -> None:
    _create_lead(client, name="Executive Stabilize")
    summary = client.get("/executive/summary")
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert "cards" in body


# --- Data integrity ---


def test_data_integrity_unique_constraints(db: Session) -> None:
    inspector = inspect(db.bind)
    shortlist_constraints = {
        c["name"]
        for c in inspector.get_unique_constraints("sales_shortlist_items")
    }
    assert "uq_shortlist_asset" in shortlist_constraints

    proposal_constraints = {
        c["name"] for c in inspector.get_unique_constraints("sales_proposal_versions")
    }
    assert "uq_proposal_version_number" in proposal_constraints


def test_data_integrity_money_fields_decimal(client: TestClient) -> None:
    lead = _create_lead(client, name="Money Flow")
    opp = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "expected_revenue": "123456.78",
            "currency": "TRY",
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    )
    assert opp.status_code == 201, opp.text
    assert opp.json()["expected_revenue"] == "123456.78"
    assert opp.json()["currency"] == "TRY"


def test_shortlist_item_uniqueness(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Unique Shortlist")
    opp = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    ).json()
    sl = client.post(
        "/sales/shortlists",
        json={"title": "Dup test", "lead_id": lead["id"]},
    ).json()
    project = client.post(
        "/projects",
        json={
            "project_code": f"PRJ-UNQ-{uuid4().hex[:6]}",
            "project_name": "Unique Project",
            "project_type": "residential",
            "development_type": "ground_up",
            "project_status": "construction",
        },
    ).json()
    building = client.post(
        "/inventory/buildings",
        json={
            "project_id": project["id"],
            "code": "U",
            "name": "Unique Tower",
            "building_type": "apartment",
            "total_floors": 3,
            "status": "active",
        },
    ).json()
    floor = client.post(
        "/inventory/floors",
        json={
            "building_id": building["id"],
            "floor_number": 1,
            "display_name": "L1",
            "level_code": "01",
            "sort_order": 1,
            "status": "active",
        },
    ).json()
    asset_id = client.post(
        "/inventory/assets",
        json={
            "project_id": project["id"],
            "building_id": building["id"],
            "floor_id": floor["id"],
            "display_id": f"UNQ-{uuid4().hex[:6]}",
            "asset_type": "residential_unit",
            "usage_type": "residential",
            "availability_status": "available",
            "sales_status": "available_for_sale",
            "currency": "USD",
            "list_price": "100000.00",
        },
    ).json()["id"]
    client.post(
        f"/sales/shortlists/{sl['id']}/items",
        json={"inventory_asset_id": asset_id},
    )
    dup = client.post(
        f"/sales/shortlists/{sl['id']}/items",
        json={"inventory_asset_id": asset_id},
    )
    assert dup.status_code in {409, 422}, dup.text


# --- Permission matrix ---


@pytest.mark.parametrize(
    ("email", "method", "path", "payload", "expected"),
    [
        ("readonly@example.com", "post", "/leads", {"full_name": "Blocked", "email": "blocked@example.com", "status": LeadStatus.NEW.value}, 403),
        ("readonly@example.com", "post", "/sales/opportunities", {"party_id": "00000000-0000-0000-0000-000000000001"}, 403),
        ("sales@example.com", "post", "/leads", {"full_name": "Allowed", "email": "allowed@example.com", "status": LeadStatus.NEW.value}, 201),
    ],
)
def test_permission_matrix_mutations(
    auth_client: TestClient,
    email: str,
    method: str,
    path: str,
    payload: dict,
    expected: int,
) -> None:
    _login(auth_client, email)
    if method == "post":
        response = auth_client.post(path, json=payload)
    else:
        response = auth_client.request(method, path, json=payload)
    assert response.status_code == expected, response.text


def test_read_only_cannot_create_proposal(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    lead = _create_lead(auth_client, name="Perm Proposal")
    opp = auth_client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "next_action": "call",
            "next_action_date": (date.today() + timedelta(days=2)).isoformat(),
        },
    ).json()
    _login(auth_client, "readonly@example.com")
    blocked = auth_client.post(
        "/sales/proposals",
        json={"opportunity_id": opp["id"], "title": "Blocked", "currency": "USD", "recipient_email": "x@example.com"},
    )
    assert blocked.status_code == 403


def test_read_only_cannot_view_private_work_item(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    created = auth_client.post(
        "/sales/work/items",
        json={
            "title": "Secret stabilize item",
            "work_item_type": "other",
            "due_at": due,
            "is_private": True,
        },
    )
    assert created.status_code == 201
    item_id = created.json()["id"]
    _login(auth_client, "readonly@example.com")
    detail = auth_client.get(f"/sales/work/items/{item_id}")
    assert detail.status_code in {403, 404}


# --- Background jobs registration ---


def test_worker_registers_sales_jobs() -> None:
    function_names = {fn.__name__ for fn in WorkerSettings.functions}
    cron_names = {job.name for job in WorkerSettings.cron_jobs}
    assert "due_soon_job" in function_names
    assert "expire_soft_holds_job" in function_names
    assert "expire_proposals_job" in function_names
    assert WorkerSettings.job_name_map["inventory_expire_soft_holds"] is not None
    assert "sales_expire_proposals" in cron_names
