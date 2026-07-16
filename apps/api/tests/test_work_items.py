"""Work item backend integration tests."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityEntityType, ActivityLog
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.notification import Notification
from investhome_api.models.sales import (
    OpportunityNextAction,
    OpportunityPartyType,
    OpportunityStage,
    SalesOpportunity,
)
from investhome_api.models.user_auth import User
from investhome_api.models.work_item import (
    FollowUpRecord,
    MeetingRecord,
    WorkItem,
    WorkItemStatus,
    WorkItemType,
)
from investhome_api.services.search_service import global_search
from investhome_api.services.work.work_reminder_jobs import run_due_soon_reminders, run_overdue_reminders

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


def test_work_item_crud(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    lead = _create_lead(auth_client)
    create = auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(lead_id=lead["id"]),
    )
    assert create.status_code == 201
    created = create.json()
    item_id = created["id"]
    assert created["title"] == "Call prospect"
    assert created["status"] == WorkItemStatus.OPEN.value

    listing = auth_client.get("/sales/work/items")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    detail = auth_client.get(f"/sales/work/items/{item_id}")
    assert detail.status_code == 200

    updated = auth_client.patch(
        f"/sales/work/items/{item_id}",
        json={"title": "Updated call", "priority": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Updated call"
    assert updated.json()["priority"] == "high"


def test_work_item_complete_and_archive(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    create = auth_client.post("/sales/work/items", json=_work_item_payload())
    item_id = create.json()["id"]

    completed = auth_client.post(
        f"/sales/work/items/{item_id}/complete",
        json={"outcome": "Reached voicemail"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == WorkItemStatus.COMPLETED.value

    archived = auth_client.delete(f"/sales/work/items/{item_id}")
    assert archived.status_code == 422

    create2 = auth_client.post("/sales/work/items", json=_work_item_payload(title="Archive me"))
    item2_id = create2.json()["id"]
    archived2 = auth_client.delete(f"/sales/work/items/{item2_id}")
    assert archived2.status_code == 200
    assert archived2.json()["archived_at"] is not None


def test_work_item_overdue_view(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(title="Overdue task", due_at=past),
    )
    overdue = auth_client.get("/sales/work/views/overdue")
    assert overdue.status_code == 200
    assert overdue.json()["total"] >= 1


def test_meeting_create_and_complete(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    lead = _create_lead(auth_client, name="Meeting Lead")
    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    create = auth_client.post(
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
    assert create.json()["meeting"] is not None
    assert create.json()["meeting"]["meeting_url"] == "https://example.com/meet/abc"

    complete = auth_client.post(
        f"/sales/work/meetings/{item_id}/complete",
        json={"outcome": "Positive meeting", "decision_summary": "Proceed to proposal"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == WorkItemStatus.COMPLETED.value


def test_follow_up_create_and_complete(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    lead = _create_lead(auth_client, name="Follow Up Lead")
    create = auth_client.post(
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
    assert create.json()["follow_up"] is not None

    complete = auth_client.post(
        f"/sales/work/follow-ups/{item_id}/complete",
        json={"outcome": "connected", "response_status": "responded"},
    )
    assert complete.status_code == 200
    assert complete.json()["status"] == WorkItemStatus.COMPLETED.value


def test_opportunity_sync_on_work_item(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@investhome.com")
    lead = _create_lead(auth_client, name="Sync Lead")
    opp = _create_opportunity(auth_client, lead)
    due = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(
            title="Sync call",
            opportunity_id=opp["id"],
            lead_id=lead["id"],
            work_item_type=WorkItemType.CALL.value,
            due_at=due,
        ),
    )
    opportunity = db.get(SalesOpportunity, UUID(opp["id"]))
    assert opportunity is not None
    assert opportunity.next_action == OpportunityNextAction.CALL
    assert opportunity.next_action_date is not None


def test_private_work_item_permissions(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    create = auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(title="Private note", is_private=True),
    )
    assert create.status_code == 201
    item_id = create.json()["id"]

    _login(auth_client, "readonly@investhome.com")
    forbidden = auth_client.get(f"/sales/work/items/{item_id}")
    assert forbidden.status_code == 403


def test_lead_follow_up_bridge(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    lead = _create_lead(auth_client, name="Bridge Lead")
    due = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    create = auth_client.post(
        f"/leads/{lead['id']}/follow-ups",
        json={"follow_up_type": "call", "due_at": due, "notes": "Bridge test"},
    )
    assert create.status_code == 201
    follow_up_id = create.json()["id"]

    listing = auth_client.get(f"/leads/{lead['id']}/follow-ups")
    assert listing.status_code == 200
    assert len(listing.json()) >= 1

    work_items = auth_client.get(f"/sales/work/leads/{lead['id']}/items")
    assert work_items.status_code == 200
    assert work_items.json()["total"] >= 1

    complete = auth_client.patch(f"/leads/{lead['id']}/follow-ups/{follow_up_id}/complete")
    assert complete.status_code == 200
    assert complete.json()["status"] == "completed"


def test_dashboard_kpis(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    auth_client.post("/sales/work/items", json=_work_item_payload(title="KPI task"))
    kpis = auth_client.get("/sales/work/dashboard/kpis")
    assert kpis.status_code == 200
    body = kpis.json()
    assert "today_count" in body
    assert "overdue_count" in body
    assert "my_work_count" in body


def test_activity_on_work_item_create(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@investhome.com")
    create = auth_client.post("/sales/work/items", json=_work_item_payload(title="Activity test"))
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


def test_work_item_search(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@investhome.com")
    auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(title="UniqueSearchWorkItemXYZ"),
    )
    user = db.scalar(select(User).where(User.email == "sales@investhome.com"))
    assert user is not None
    results = global_search(db, user, "UniqueSearchWorkItemXYZ")
    assert any(r.entity_type == "work_item" for r in results.results)


def test_reminder_jobs_dedupe(auth_client: TestClient, db: Session) -> None:
    _login(auth_client, "sales@investhome.com")
    user = db.scalar(select(User).where(User.email == "sales@investhome.com"))
    due = datetime.now(UTC) + timedelta(hours=12)
    auth_client.post(
        "/sales/work/items",
        json=_work_item_payload(
            title="Due soon item",
            due_at=due.isoformat(),
            assigned_user_id=str(user.id) if user else None,
        ),
    )
    first = run_due_soon_reminders(clock=datetime.now(UTC))
    second = run_due_soon_reminders(clock=datetime.now(UTC))
    assert first["reminders_sent"] >= 1
    assert second["reminders_sent"] >= 1
    notifications = list(db.scalars(select(Notification).where(Notification.rule_key.like("work.item.due_soon.%"))).all())
    assert len(notifications) >= 1


def test_calendar_events(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    auth_client.post("/sales/work/items", json=_work_item_payload(title="Calendar event"))
    events = auth_client.get("/sales/work/calendar")
    assert events.status_code == 200
    assert len(events.json()) >= 1


def test_team_work_view(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    auth_client.post("/sales/work/items", json=_work_item_payload(title="Team work"))
    team = auth_client.get("/sales/work/views/team_work")
    assert team.status_code == 200


def test_status_change_and_cancel(auth_client: TestClient) -> None:
    _login(auth_client, "sales@investhome.com")
    create = auth_client.post("/sales/work/items", json=_work_item_payload(title="Status test"))
    item_id = create.json()["id"]

    blocked = auth_client.post(
        f"/sales/work/items/{item_id}/status",
        json={"status": WorkItemStatus.BLOCKED.value, "reason": "Waiting on client"},
    )
    assert blocked.status_code == 200
    assert blocked.json()["status"] == WorkItemStatus.BLOCKED.value

    cancelled = auth_client.post(
        f"/sales/work/items/{item_id}/cancel",
        json={"status": WorkItemStatus.CANCELLED.value, "reason": "No longer needed"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == WorkItemStatus.CANCELLED.value
