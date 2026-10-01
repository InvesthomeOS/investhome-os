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
    created = client.post("/crm/activities", json=_activity_payload(contact_id))
    assert created.status_code == 201, created.text
    contact_name = client.get(f"/crm/contacts/{contact_id}").json()["display_name"]
    response = client.get(f"/crm/timeline?entity_type=contact&entity_id={contact_id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) >= 1
    assert body["total"] == len(body["items"]) or body["total"] >= len(body["items"])
    named = [item for item in body["items"] if item.get("entity_id") == contact_id]
    assert named
    assert all(item.get("person_name") not in {None, "Contact", "contact"} for item in named)
    assert any(item.get("person_name") == contact_name for item in named)

    notes = client.get(
        f"/crm/timeline?entity_type=contact&entity_id={contact_id}&event_kind=note"
    )
    assert notes.status_code == 200
    assert all(item.get("event_kind") == "note" for item in notes.json()["items"] if item.get("source") == "crm_activity")


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


def _login(client: TestClient, email: str, password: str = "Demo123!") -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


def _crm_reader(db) -> str:
    from uuid import uuid4 as _uuid4

    from investhome_api.models.user_auth import Permission, Role, RolePermission, User, UserRole, UserStatus
    from investhome_api.services.auth_service import hash_password

    perm_read = db.query(Permission).filter_by(resource="crm", action="read").one()
    perm_activities = db.query(Permission).filter_by(resource="crm", action="view_activities").one_or_none()
    if perm_activities is None:
        perm_activities = Permission(resource="crm", action="view_activities")
        db.add(perm_activities)
        db.flush()
    role = Role(name="crm_activity_reader", code=f"crm_act_{_uuid4().hex[:6]}", is_system_role=False)
    db.add(role)
    db.flush()
    db.add(RolePermission(role_id=role.id, permission_id=perm_read.id))
    db.add(RolePermission(role_id=role.id, permission_id=perm_activities.id))
    email = f"crm.act.{_uuid4().hex[:8]}@example.com"
    user = User(
        email=email,
        full_name="CRM Activity Reader",
        hashed_password=hash_password("Demo123!"),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    return email


def test_private_activity_hidden_from_unauthorized_direct_id_and_contact(
    auth_client: TestClient, db
) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(db, Session)
    _login(auth_client, "sales@example.com")
    contact_id = _create_contact(auth_client)
    private = auth_client.post(
        "/crm/activities",
        json=_activity_payload(contact_id, title="Secret private note", visibility="private"),
    )
    public = auth_client.post(
        "/crm/activities",
        json=_activity_payload(contact_id, title="Org visible note", visibility="organization"),
    )
    assert private.status_code == 201, private.text
    assert public.status_code == 201, public.text
    private_id = private.json()["activity"]["id"]
    public_id = public.json()["activity"]["id"]

    owner_detail = auth_client.get(f"/crm/activities/{private_id}")
    assert owner_detail.status_code == 200, owner_detail.text
    assert owner_detail.json()["id"] == private_id
    assert owner_detail.json()["visibility"] == "private"
    assert auth_client.get(f"/crm/activities/{public_id}").status_code == 200

    owner_list = auth_client.get(f"/crm/activities?entity_type=contact&entity_id={contact_id}")
    owner_ids = {item["id"] for item in owner_list.json()["items"]}
    assert private_id in owner_ids
    assert public_id in owner_ids

    owner_contact = auth_client.get(f"/crm/contacts/{contact_id}")
    owner_embedded = {item["id"] for item in owner_contact.json()["crm_activities"]}
    assert private_id in owner_embedded
    assert public_id in owner_embedded

    email = _crm_reader(db)
    db.commit()
    auth_client.post("/auth/logout")
    _login(auth_client, email)

    hidden = auth_client.get(f"/crm/activities/{private_id}")
    assert hidden.status_code == 404
    assert "Secret private note" not in hidden.text
    visible = auth_client.get(f"/crm/activities/{public_id}")
    assert visible.status_code == 200
    assert visible.json()["id"] == public_id
    assert visible.json()["title"] == "Org visible note"

    other_list = auth_client.get(f"/crm/activities?entity_type=contact&entity_id={contact_id}")
    other_ids = {item["id"] for item in other_list.json()["items"]}
    assert private_id not in other_ids
    assert public_id in other_ids

    other_contact = auth_client.get(f"/crm/contacts/{contact_id}")
    assert other_contact.status_code == 200
    embedded = other_contact.json()["crm_activities"]
    embedded_ids = {item["id"] for item in embedded}
    assert private_id not in embedded_ids
    assert public_id in embedded_ids
    assert all(item.get("title") != "Secret private note" for item in embedded)

    timeline = auth_client.get(f"/crm/contacts/{contact_id}/timeline")
    assert timeline.status_code == 200
    timeline_ids = {item["id"] for item in timeline.json()["items"]}
    assert private_id not in timeline_ids
    assert public_id in timeline_ids
