"""Manual Lead → CRM task creation uses the existing /crm/tasks architecture."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityReminder,
    CrmActivityType,
    CrmReminderChannel,
    CrmTaskStatus,
)
from investhome_api.services.crm.task_reminder_jobs import run_crm_task_due_reminders

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


def test_task_due_time_and_reminders_replace_and_email(client: TestClient, db: Session, monkeypatch) -> None:
    person = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Hatırlatma Kişisi",
            "primary_email": "hatirlatma.kisi@example.com",
        },
    )
    assert person.status_code == 201, person.text
    contact_id = person.json()["contact"]["id"]
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Saatli görev",
            "contact_id": contact_id,
            "due_on": "2026-11-08",
            "due_time": "15:30",
            "timezone": "Europe/Istanbul",
            "reminders": [
                {
                    "channel": "in_app",
                    "remind_at": "2026-11-08T15:15:00+03:00",
                    "offset_minutes": 15,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    activity = created.json()["activity"]
    due = datetime.fromisoformat(activity["due_date"])
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    local = due.astimezone(ISTANBUL)
    assert (local.hour, local.minute) == (15, 30)
    assert local.hour != 12
    assert activity["reminders"][0]["channel"] == "in_app"
    assert activity["reminders"][0]["offset_minutes"] == 15

    cleared = client.put(
        f"/crm/activities/{activity['id']}",
        json={"reminders": [], "due_on": "2026-11-08", "due_time": "16:00", "timezone": "Europe/Istanbul"},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["activity"]["reminders"] == []
    moved = datetime.fromisoformat(cleared.json()["activity"]["due_date"])
    if moved.tzinfo is None:
        moved = moved.replace(tzinfo=UTC)
    assert moved.astimezone(ISTANBUL).hour == 16

    remind_at = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
    emailed = client.put(
        f"/crm/activities/{activity['id']}",
        json={
            "reminders": [
                {"channel": "email", "remind_at": remind_at, "offset_minutes": 0},
            ]
        },
    )
    assert emailed.status_code == 200, emailed.text
    sent_messages: list = []

    class Gateway:
        def dispatch(self, message, provider_id="email_smtp"):
            sent_messages.append((message, provider_id))
            return SimpleNamespace(ok=True, status="sent", provider_id=provider_id)

    from investhome_api.models.user_auth import User
    from investhome_api.services.user_notifications import save_preference_state

    owner = db.query(User).filter_by(email="dev-bypass@example.com").one()
    save_preference_state(
        db,
        owner.id,
        [{"event_key": "task_reminder", "in_app": True, "email": True}],
    )
    db.commit()
    monkeypatch.setattr(
        "investhome_api.services.user_notifications.get_notification_gateway",
        lambda: Gateway(),
    )
    result = run_crm_task_due_reminders(db=db)
    db.commit()
    assert result["reminders_sent"] == 1
    assert sent_messages[0][1] == "email_smtp"
    assert sent_messages[0][0].recipient == "dev-bypass@example.com"
    assert sent_messages[0][0].subject == "Görev Hatırlatması: Saatli görev"
    assert "Hatırlatma Kişisi" in sent_messages[0][0].body
    assert "08.11.2026 16:00" in sent_messages[0][0].body
    assert f"/workspaces/crm/tasks?task={activity['id']}" in sent_messages[0][0].body
    db.expire_all()
    row = db.query(CrmActivityReminder).filter_by(activity_id=UUID(activity["id"])).one()
    assert row.channel == CrmReminderChannel.EMAIL
    assert row.is_sent is True
    repeat = run_crm_task_due_reminders(db=db)
    db.commit()
    assert repeat["reminders_sent"] == 0
    assert len(sent_messages) == 1

    failed = client.post(
        "/crm/tasks",
        json={
            "title": "E-posta bekliyor",
            "contact_id": contact_id,
            "due_on": "2026-11-08",
            "due_time": "18:00",
            "timezone": "Europe/Istanbul",
            "reminders": [
                {"channel": "email", "remind_at": remind_at, "offset_minutes": 0},
            ],
        },
    )
    assert failed.status_code == 201, failed.text
    failed_id = failed.json()["activity"]["id"]

    class DownGateway:
        def dispatch(self, message, provider_id="email_smtp"):
            return SimpleNamespace(ok=False, status="not_connected", provider_id=provider_id)

    monkeypatch.setattr(
        "investhome_api.services.user_notifications.get_notification_gateway",
        lambda: DownGateway(),
    )
    missed = run_crm_task_due_reminders(db=db)
    db.commit()
    assert missed["reminders_sent"] == 0
    db.expire_all()
    waiting = db.query(CrmActivityReminder).filter_by(activity_id=UUID(failed_id)).one()
    assert waiting.is_sent is False


def test_creation_note_remains_when_a_later_note_is_added(client: TestClient) -> None:
    lead = _create_lead(
        client,
        full_name="Notlu Lead",
        email="note.keep@example.com",
        phone="+90 555 321 00 91",
        notes="İlk not",
    )
    assert lead["notes"] == "İlk not"
    detail = client.get(f"/crm/leads/{lead['id']}")
    assert detail.status_code == 200, detail.text
    first_bodies = [item["body"] for item in detail.json()["note_entries"]]
    assert first_bodies == ["İlk not"]
    assert detail.json()["note_entries"][0]["author_name"]
    assert detail.json()["note_entries"][0]["created_at"]

    added = client.post(
        "/crm/notes",
        json={"contact_id": lead["contact_id"], "description": "İkinci not"},
    )
    assert added.status_code == 201, added.text
    again = client.get(f"/crm/leads/{lead['id']}")
    assert again.status_code == 200, again.text
    assert again.json()["notes"] == "İlk not"
    bodies = [item["body"] for item in again.json()["note_entries"]]
    assert bodies == ["İlk not", "İkinci not"]
