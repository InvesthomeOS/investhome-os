"""Manual Lead → CRM task creation uses the existing /crm/tasks architecture."""

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityType, CrmTaskStatus

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _create_lead(client: TestClient, **overrides: object) -> dict:
    payload = {
        "full_name": "Görevli Lead",
        "email": "gorevli.lead@example.com",
        "phone": "+90 555 321 00 11",
        "source": "manual",
        **overrides,
    }
    response = client.post("/crm/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_task_from_lead_persists_name_due_and_links(client: TestClient, db: Session) -> None:
    lead = _create_lead(client)
    lead_id = lead["id"]
    contact_id = lead["contact_id"]
    assert contact_id

    created = client.post(
        "/crm/tasks",
        json={
            "title": "Teklif görüşmesi",
            "lead_id": lead_id,
            "due_on": "2026-10-09",
            "due_time": "14:30",
            "timezone": "Europe/Istanbul",
        },
    )
    assert created.status_code == 201, created.text
    activity = created.json()["activity"]
    assert activity["title"] == "Teklif görüşmesi"
    assert activity["activity_type"] == "task"
    assert activity["task_status"] == "not_started"
    assert activity["status"] == "planned"
    assert activity["timezone"] == "Europe/Istanbul"
    assert activity["entity_type"] == "contact"
    assert activity["entity_id"] == contact_id
    assert activity["metadata_json"]["task_links"]["lead_id"] == lead_id
    assert activity["metadata_json"]["task_links"]["contact_id"] == contact_id

    due = datetime.fromisoformat(activity["due_date"])
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    local = due.astimezone(ISTANBUL)
    assert local.year == 2026
    assert local.month == 10
    assert local.day == 9
    assert local.hour == 14
    assert local.minute == 30

    db.expire_all()
    row = db.get(CrmActivity, UUID(activity["id"]))
    assert row is not None
    assert row.activity_type == CrmActivityType.TASK
    assert row.task_status == CrmTaskStatus.NOT_STARTED
    assert row.title == "Teklif görüşmesi"

    listed_tasks = client.get("/crm/tasks")
    assert listed_tasks.status_code == 200
    assert any(item["id"] == activity["id"] for item in listed_tasks.json()["items"])

    by_lead = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert by_lead.status_code == 200
    assert any(item["id"] == activity["id"] for item in by_lead.json()["items"])

    refreshed = client.get(f"/crm/leads/{lead_id}")
    assert refreshed.status_code == 200
    tasks = refreshed.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["id"] == activity["id"]
    assert tasks[0]["title"] == "Teklif görüşmesi"
    assert tasks[0]["contact_id"] == contact_id
    assert tasks[0]["status"] == "open"
    again = client.get(f"/crm/leads/{lead_id}")
    assert again.json()["tasks"][0]["id"] == activity["id"]


def test_lead_task_rejects_missing_name_date_and_time(client: TestClient) -> None:
    lead = _create_lead(client, email="gorev.eksik@example.com", phone="+90 555 321 00 12")
    lead_id = lead["id"]
    base = {"lead_id": lead_id, "due_on": "2026-10-09", "due_time": "09:15"}

    missing_name = client.post("/crm/tasks", json={**base, "title": "   "})
    assert missing_name.status_code in {400, 422}

    missing_date = client.post("/crm/tasks", json={"title": "Arama", "lead_id": lead_id, "due_time": "09:15"})
    assert missing_date.status_code == 400
    assert "Tarih" in missing_date.json()["detail"]

    missing_time = client.post("/crm/tasks", json={"title": "Arama", "lead_id": lead_id, "due_on": "2026-10-09"})
    assert missing_time.status_code == 400
    assert "Saat" in missing_time.json()["detail"]

    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert listed.status_code == 200
    assert listed.json()["items"] == []


def test_existing_task_create_without_lead_still_works(client: TestClient) -> None:
    person = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Görev Kişisi",
            "primary_email": "gorev.kisi@example.com",
        },
    )
    assert person.status_code == 201, person.text
    contact_id = person.json()["contact"]["id"]
    due = datetime(2026, 10, 10, 12, 0, tzinfo=ISTANBUL).isoformat()
    created = client.post(
        "/crm/tasks",
        json={"title": "Contact follow up", "contact_id": contact_id, "due_date": due},
    )
    assert created.status_code == 201, created.text
    assert created.json()["activity"]["entity_id"] == contact_id
    assert created.json()["activity"]["title"] == "Contact follow up"
    listed = client.get("/crm/tasks")
    assert any(item["id"] == created.json()["activity"]["id"] for item in listed.json()["items"])
