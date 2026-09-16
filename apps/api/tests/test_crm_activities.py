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


def test_list_activities_pagination_search_and_filters(client: TestClient) -> None:
    contact_id = _create_contact(client)
    titles = [f"Paged comment {i} {uuid4().hex[:4]}" for i in range(3)]
    created_ids: list[str] = []
    for title in titles:
        created = client.post("/crm/activities", json=_activity_payload(contact_id, title=title))
        assert created.status_code == 201, created.text
        created_ids.append(created.json()["activity"]["id"])

    page1 = client.get("/crm/activities?page=1&page_size=2&sort_by=created_at&sort_dir=desc")
    page2 = client.get("/crm/activities?page=2&page_size=2&sort_by=created_at&sort_dir=desc")
    assert page1.status_code == 200
    assert page2.status_code == 200
    body1 = page1.json()
    body2 = page2.json()
    assert body1["page"] == 1
    assert body1["page_size"] == 2
    assert body1["total"] >= 3
    ids1 = {item["id"] for item in body1["items"]}
    ids2 = {item["id"] for item in body2["items"]}
    assert ids1.isdisjoint(ids2)

    search = client.get(f"/crm/activities?search={quote(titles[0])}")
    assert search.status_code == 200
    search_ids = {item["id"] for item in search.json()["items"]}
    assert created_ids[0] in search_ids

    contact_name = client.get(f"/crm/contacts/{contact_id}").json()["display_name"]
    by_name = client.get(f"/crm/activities?search={quote(contact_name)}")
    assert by_name.status_code == 200
    assert any(item["entity_id"] == contact_id for item in by_name.json()["items"])

    by_type = client.get(f"/crm/activities?activity_types=note&entity_id={contact_id}")
    assert by_type.status_code == 200
    assert by_type.json()["total"] >= 3

    by_contact = client.get(f"/crm/activities?entity_type=contact&entity_id={contact_id}&page_size=2")
    assert by_contact.status_code == 200
    assert by_contact.json()["total"] >= 3
    assert len(by_contact.json()["items"]) == 2


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
