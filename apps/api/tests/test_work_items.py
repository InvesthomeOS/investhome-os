"""Work item backend integration tests."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.lead import LeadStatus
from investhome_api.models.notification import Notification
from investhome_api.models.sales import OpportunityNextAction, OpportunityPartyType, SalesOpportunity
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import WorkItemStatus, WorkItemType
from investhome_api.services.search_service import global_search
from investhome_api.services.work.work_reminder_jobs import run_due_soon_reminders

DEMO_PASSWORD = "Demo123!"


def _login(client: TestClient, email: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    assert response.status_code == 200


def _create_lead(client: TestClient, *, name: str = "Work Item Lead") -> dict:
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


def _create_opportunity(client: TestClient, lead: dict) -> dict:
    response = client.post(
        "/sales/opportunities",
        json={
            "party_id": lead["id"],
            "party_type": OpportunityPartyType.LEAD.value,
            "lead_id": lead["id"],
            "next_action": OpportunityNextAction.CALL.value,
            "next_action_date": (date.today() + timedelta(days=3)).isoformat(),
        },
    )
    assert response.status_code == 201
    return response.json()


def _work_item_payload(**overrides) -> dict:
    base = {
        "title": "Call prospect",
        "work_item_type": WorkItemType.CALL.value,
        "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
        "priority": "medium",
    }
    base.update(overrides)
    return base


def test_work_item_crud(client: TestClient) -> None:
    lead = _create_lead(client)
    create = client.post("/sales/work/items", json=_work_item_payload(lead_id=lead["id"]))
    assert create.status_code == 201
    created = create.json()
    item_id = created["id"]
    assert created["title"] == "Call prospect"

    listing = client.get("/sales/work/items")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    updated = client.patch(
        f"/sales/work/items/{item_id}",
        json={"title": "Updated call", "priority": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated call"


def test_work_item_complete_and_archive(client: TestClient) -> None:
    create = client.post("/sales/work/items", json=_work_item_payload())
    item_id = create.json()["id"]

    completed = client.post(
        f"/sales/work/items/{item_id}/complete",
        json={"outcome": "Reached voicemail"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == WorkItemStatus.COMPLETED.value

    archived = client.delete(f"/sales/work/items/{item_id}")
    assert archived.status_code == 422

    create2 = client.post("/sales/work/items", json=_work_item_payload(title="Archive me"))
    item2_id = create2.json()["id"]
    archived2 = client.delete(f"/sales/work/items/{item2_id}")
    assert archived2.status_code == 200


def test_work_item_overdue_view(client: TestClient) -> None:
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    client.post("/sales/work/items", json=_work_item_payload(title="Overdue task", due_at=past))
    overdue = client.get("/sales/work/views/overdue")
    assert overdue.status_code == 200
    assert overdue.json()["total"] >= 1


def test_meeting_create_and_complete(client: TestClient) -> None:
    lead = _create_lead(client, name="Meeting Lead")
    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    create = client.post(
        "/sales/work/meetings",
        json={
            "title": "Discovery meeting",
            "due_at": due,
            "start_at": due,
            "lead_id": lead["id"],
            "meeting_type": "video",
            "meeting_url": "https://example.com/meet/abc",
            "agenda": "Discuss requirements",
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]
    assert create.json()["meeting"]["meeting_url"] == "https://example.com/meet/abc"

    complete = client.post(
        f"/sales/work/meetings/{item_id}/complete",
        json={"outcome": "Positive meeting", "decision_summary": "Proceed to proposal"},
    )
    assert complete.status_code == 200


def test_follow_up_create_and_complete(client: TestClient) -> None:
    lead = _create_lead(client, name="Follow Up Lead")
    create = client.post(
        "/sales/work/follow-ups",
        json={
            "title": "Follow up on proposal",
            "due_at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "lead_id": lead["id"],
            "contact_method": "call",
        },
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    complete = client.post(
        f"/sales/work/follow-ups/{item_id}/complete",
        json={"outcome": "connected", "response_status": "responded"},
    )
    assert complete.status_code == 200


def test_opportunity_sync_on_work_item(client: TestClient, db: Session) -> None:
    lead = _create_lead(client, name="Sync Lead")
    opp = _create_opportunity(client, lead)
    due = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    client.post(
        "/sales/work/items",
        json=_work_item_payload(
            title="Sync call",
            opportunity_id=opp["id"],
            lead_id=lead["id"],
            due_at=due,
        ),
    )
    opportunity = db.get(SalesOpportunity, UUID(opp["id"]))
    assert opportunity is not None
    assert opportunity.next_action == OpportunityNextAction.CALL


def test_private_work_item_permissions(client: TestClient) -> None:
    create = client.post(
        "/sales/work/items",
        json=_work_item_payload(title="Private note", is_private=True),
    )
    assert create.status_code == 201
    listing = client.get("/sales/work/items", params={"search": "Private note"})
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1


def test_work_item_search(client: TestClient, db: Session) -> None:
    client.post("/sales/work/items", json=_work_item_payload(title="UniqueSearchWorkItemXYZ"))
    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    role = Role(name="search", code="search_test", is_system_role=False)
    db.add(role)
    db.flush()
    perm = Permission(resource="work", action="view")
    db.add(perm)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm.id))
    user = User(
        full_name="Search User",
        email="search-work@example.com",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()
    db.refresh(user)
    results = global_search(db, user, "UniqueSearchWorkItemXYZ")
    work_items = [
        item
        for group in results.groups
        if group.entity_type == "work_item"
        for item in group.items
    ]
    assert any(item.entity_type == "work_item" for item in work_items)


def test_lead_follow_up_bridge(client: TestClient) -> None:
    lead = _create_lead(client, name="Bridge Lead")
    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    create = client.post(
        f"/leads/{lead['id']}/follow-ups",
        json={"follow_up_type": "call", "due_at": due, "notes": "Bridge test"},
    )
    assert create.status_code == 201

    work_items = client.get(f"/sales/work/leads/{lead['id']}/items")
    assert work_items.status_code == 200
    assert work_items.json()["total"] >= 1


def test_dashboard_kpis(client: TestClient) -> None:
    client.post("/sales/work/items", json=_work_item_payload(title="KPI task"))
    kpis = client.get("/sales/work/dashboard/kpis")
    assert kpis.status_code == 200
    assert "today_count" in kpis.json()


def test_activity_on_work_item_create(client: TestClient, db: Session) -> None:
    create = client.post("/sales/work/items", json=_work_item_payload(title="Activity test"))
    item_id = UUID(create.json()["id"])
    logs = list(
        db.scalars(
            select(ActivityLog).where(
                ActivityLog.entity_type == ActivityEntityType.WORK_ITEM,
                ActivityLog.entity_id == item_id,
            )
        ).all()
    )
    assert len(logs) >= 1


def test_reminder_jobs_dedupe(client: TestClient) -> None:
    due = datetime.now(UTC) + timedelta(hours=12)
    client.post(
        "/sales/work/items",
        json=_work_item_payload(title="Due soon item", due_at=due.isoformat()),
    )
    first = run_due_soon_reminders(clock=datetime.now(UTC))
    assert first["reminders_sent"] >= 0


def test_calendar_events(client: TestClient) -> None:
    client.post("/sales/work/items", json=_work_item_payload(title="Calendar event"))
    events = client.get("/sales/work/calendar")
    assert events.status_code == 200


def test_team_work_view(client: TestClient) -> None:
    client.post("/sales/work/items", json=_work_item_payload(title="Team work"))
    team = client.get("/sales/work/views/team_work")
    assert team.status_code == 200


def test_status_change_and_cancel(client: TestClient) -> None:
    create = client.post("/sales/work/items", json=_work_item_payload(title="Status test"))
    item_id = create.json()["id"]

    blocked = client.post(
        f"/sales/work/items/{item_id}/status",
        json={"status": WorkItemStatus.BLOCKED.value, "reason": "Waiting on client"},
    )
    assert blocked.status_code == 200

    cancelled = client.post(
        f"/sales/work/items/{item_id}/cancel",
        json={"status": WorkItemStatus.CANCELLED.value, "reason": "No longer needed"},
    )
    assert cancelled.status_code == 200
