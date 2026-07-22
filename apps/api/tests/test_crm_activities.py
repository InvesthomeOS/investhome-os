"""CRM activity timeline, tasks, notes, and follow-up API tests."""

from datetime import UTC, datetime, timedelta
from urllib.parse import quote
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _create_contact(client: TestClient) -> str:
    payload = {
        "contact_type": "prospect",
        "record_kind": "person",
        "display_name": f"Activity Contact {uuid4().hex[:6]}",
        "primary_email": f"act.{uuid4().hex[:8]}@example.com",
    }
    response = client.post("/crm/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["contact"]["id"]


def _activity_payload(contact_id: str, **overrides) -> dict:
    base = {
        "entity_type": "contact",
        "entity_id": contact_id,
        "activity_type": "note",
        "title": f"Test note {uuid4().hex[:6]}",
        "description": "Activity description",
        "visibility": "organization",
    }
    base.update(overrides)
    return base


def test_create_activity(client: TestClient) -> None:
    contact_id = _create_contact(client)
    response = client.post("/crm/activities", json=_activity_payload(contact_id))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["activity"]["title"].startswith("Test note")
    assert body["activity"]["entity_id"] == contact_id


def test_list_activities(client: TestClient) -> None:
    contact_id = _create_contact(client)
    client.post("/crm/activities", json=_activity_payload(contact_id))
    response = client.get(f"/crm/activities?entity_type=contact&entity_id={contact_id}")
    assert response.status_code == 200
    assert response.json()["total"] >= 1


def test_get_timeline(client: TestClient) -> None:
    contact_id = _create_contact(client)
    client.post("/crm/activities", json=_activity_payload(contact_id))
    response = client.get(f"/crm/timeline?entity_type=contact&entity_id={contact_id}")
    assert response.status_code == 200
    assert len(response.json()["items"]) >= 1


def test_create_task_and_complete(client: TestClient) -> None:
    contact_id = _create_contact(client)
    due = (datetime.now(tz=UTC) + timedelta(days=2)).isoformat()
    created = client.post(
        "/crm/tasks",
        json=_activity_payload(
            contact_id,
            activity_type="task",
            title="Follow up call",
            due_date=due,
        ),
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["activity"]["id"]
    completed = client.post(f"/crm/tasks/{task_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["activity"]["status"] == "completed"


def test_create_note(client: TestClient) -> None:
    contact_id = _create_contact(client)
    response = client.post(
        "/crm/notes",
        json=_activity_payload(contact_id, title="Private note", visibility="private"),
    )
    assert response.status_code == 201
    note_id = response.json()["activity"]["id"]
    detail = client.get(f"/crm/activities/{note_id}")
    assert detail.status_code == 200
    assert detail.json()["visibility"] == "private"


def test_create_meeting(client: TestClient) -> None:
    contact_id = _create_contact(client)
    start = (datetime.now(tz=UTC) + timedelta(days=1)).isoformat()
    response = client.post(
        "/crm/meetings",
        json=_activity_payload(
            contact_id,
            activity_type="meeting",
            title="Investor sync",
            start_date=start,
            meeting_url="https://zoom.us/j/123",
        ),
    )
    assert response.status_code == 201
    assert response.json()["activity"]["activity_type"] == "meeting"


def test_create_follow_up(client: TestClient) -> None:
    contact_id = _create_contact(client)
    due = (datetime.now(tz=UTC) + timedelta(days=5)).isoformat()
    response = client.post(
        "/crm/follow-ups",
        json={
            "entity_type": "contact",
            "entity_id": contact_id,
            "reason": "investor",
            "due_date": due,
            "notes": "Check in on proposal",
        },
    )
    assert response.status_code == 201
    follow_up_id = response.json()["activity"]["id"]
    completed = client.post(f"/crm/follow-ups/{follow_up_id}/complete")
    assert completed.status_code == 200
    assert completed.json()["activity"]["status"] == "completed"


def test_archive_and_restore_activity(client: TestClient) -> None:
    contact_id = _create_contact(client)
    created = client.post("/crm/activities", json=_activity_payload(contact_id)).json()
    activity_id = created["activity"]["id"]
    archived = client.post(f"/crm/activities/{activity_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["activity"]["archived_at"] is not None
    restored = client.post(f"/crm/activities/{activity_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["activity"]["archived_at"] is None


def test_bulk_update_activities(client: TestClient) -> None:
    contact_id = _create_contact(client)
    ids = []
    for _ in range(2):
        created = client.post("/crm/activities", json=_activity_payload(contact_id)).json()
        ids.append(created["activity"]["id"])
    response = client.post(
        "/crm/activities/bulk-update",
        json={"activity_ids": ids, "priority": "high"},
    )
    assert response.status_code == 200
    assert response.json()["updated"] == 2


def test_calendar_events(client: TestClient) -> None:
    contact_id = _create_contact(client)
    start = datetime.now(tz=UTC)
    end = start + timedelta(days=14)
    client.post(
        "/crm/meetings",
        json=_activity_payload(
            contact_id,
            activity_type="meeting",
            title="Calendar meeting",
            start_date=(start + timedelta(days=3)).isoformat(),
        ),
    )
    response = client.get(
        f"/crm/calendar?start={quote(start.isoformat())}&end={quote(end.isoformat())}"
    )
    assert response.status_code == 200
    assert len(response.json()["events"]) >= 1


def test_activity_widgets(client: TestClient) -> None:
    response = client.get("/crm/activities/widgets")
    assert response.status_code == 200
    body = response.json()
    assert "todays_tasks" in body
    assert "recent_activities" in body
