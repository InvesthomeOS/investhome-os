"""Stage-based automatic follow-up tasks for contacted and proposal moves."""

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityReminder, CrmTaskStatus
from investhome_api.models.notification import Notification, NotificationType
from investhome_api.services.crm.crm_lead_service import _auto_followup_due_at
from investhome_api.services.crm.task_reminder_jobs import run_crm_task_due_reminders

ISTANBUL = ZoneInfo("Europe/Istanbul")


def _create_lead(client: TestClient, **overrides: object) -> dict:
    payload = {
        "full_name": "Otomatik Takip Lead",
        "email": "auto.follow@example.com",
        "phone": "+90 555 321 44 01",
        "source": "manual",
        **overrides,
    }
    response = client.post("/crm/leads", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _task_row(db: Session, activity_id: str) -> CrmActivity:
    row = db.get(CrmActivity, UUID(activity_id))
    assert row is not None
    return row


def test_auto_followup_due_is_exactly_two_istanbul_calendar_days() -> None:
    transition = datetime(2026, 10, 7, 14, 30, tzinfo=ISTANBUL)
    due = _auto_followup_due_at(transition)
    local = due.astimezone(ISTANBUL)
    assert local == datetime(2026, 10, 9, 14, 30, tzinfo=ISTANBUL)


def test_moving_into_contacted_creates_one_linked_followup_task(client: TestClient, db: Session) -> None:
    lead = _create_lead(client)
    lead_id = lead["id"]
    contact_id = lead["contact_id"]
    assert contact_id

    before = datetime.now(tz=UTC)
    moved = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    after = datetime.now(tz=UTC)
    assert moved.status_code == 200, moved.text
    assert moved.json()["stage"] == "contacted"

    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert listed.status_code == 200
    items = listed.json()["items"]
    assert len(items) == 1
    task_id = items[0]["id"]
    assert items[0]["title"] == f"Takip — {lead['full_name']}"
    assert items[0]["timezone"] == "Europe/Istanbul"

    db.expire_all()
    row = _task_row(db, task_id)
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    assert meta["source"] == "stage_automation"
    assert meta["source_stage_id"] == "contacted"
    assert meta["lead_id"] == lead_id
    assert meta["contact_id"] == contact_id
    assert meta["title_en"] == f"Follow-up — {lead['full_name']}"
    links = meta.get("task_links") or {}
    assert links["lead_id"] == lead_id
    assert links["contact_id"] == contact_id
    assert row.entity_id == UUID(contact_id)
    assert str(row.assigned_user_id)

    due = row.due_date
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    expected_min = _auto_followup_due_at(before)
    expected_max = _auto_followup_due_at(after)
    assert expected_min <= due <= expected_max

    detail = client.get(f"/crm/leads/{lead_id}")
    assert detail.status_code == 200
    tasks = detail.json()["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["id"] == task_id
    assert tasks[0]["contact_id"] == contact_id

    reminders = db.query(CrmActivityReminder).filter_by(activity_id=row.id).all()
    assert len(reminders) == 1
    assert reminders[0].is_sent is False
    remind_at = reminders[0].remind_at
    if remind_at.tzinfo is None:
        remind_at = remind_at.replace(tzinfo=UTC)
    assert remind_at == due


def test_moving_into_proposal_creates_one_followup_task(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.proposal@example.com",
        phone="+90 555 321 44 02",
        full_name="Teklif Lead",
    )
    lead_id = lead["id"]
    moved = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "proposal"})
    assert moved.status_code == 200, moved.text
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1
    db.expire_all()
    row = _task_row(db, listed.json()["items"][0]["id"])
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    assert meta["source"] == "stage_automation"
    assert meta["source_stage_id"] == "proposal"
    assert row.title == "Takip — Teklif Lead"


def test_other_stage_moves_and_refresh_create_no_automatic_task(client: TestClient) -> None:
    lead = _create_lead(
        client,
        email="auto.other@example.com",
        phone="+90 555 321 44 03",
        full_name="Diğer Aşama",
    )
    lead_id = lead["id"]
    for stage in ("following", "qualified", "negotiation", "long_term", "unqualified"):
        payload: dict[str, str] = {"stage": stage}
        if stage == "unqualified":
            payload["junk_reason"] = "spam"
        moved = client.post(f"/crm/leads/{lead_id}/stage", json=payload)
        assert moved.status_code == 200, moved.text
        listed = client.get("/crm/tasks", params={"lead_id": lead_id})
        assert listed.json()["items"] == []
    refreshed = client.get(f"/crm/leads/{lead_id}")
    assert refreshed.status_code == 200
    assert refreshed.json()["tasks"] == []
    listed_again = client.get("/crm/leads")
    assert listed_again.status_code == 200
    listed_tasks = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert listed_tasks.json()["items"] == []


def test_create_already_in_contacted_does_not_create_automatic_task(client: TestClient) -> None:
    lead = _create_lead(
        client,
        email="auto.created.contacted@example.com",
        phone="+90 555 321 44 04",
        full_name="Doğrudan Contacted",
        stage="contacted",
    )
    listed = client.get("/crm/tasks", params={"lead_id": lead["id"]})
    assert listed.json()["items"] == []


def test_retry_same_stage_and_remaining_in_stage_do_not_duplicate(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.retry@example.com",
        phone="+90 555 321 44 05",
        full_name="Retry Lead",
    )
    lead_id = lead["id"]
    first = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    retry = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    assert first.status_code == 200
    assert retry.status_code == 200
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert len(listed.json()["items"]) == 1
    db.expire_all()
    row = _task_row(db, listed.json()["items"][0]["id"])
    assert (row.metadata_json or {}).get("source") == "stage_automation"


def test_leave_stage_creates_no_task_and_reenter_with_active_task_does_not_duplicate(
    client: TestClient,
) -> None:
    lead = _create_lead(
        client,
        email="auto.reenter@example.com",
        phone="+90 555 321 44 06",
        full_name="Reenter Lead",
    )
    lead_id = lead["id"]
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    left = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "following"})
    assert left.status_code == 200
    after_leave = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert len(after_leave.json()["items"]) == 1
    reentered = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    assert reentered.status_code == 200
    after_reenter = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert len(after_reenter.json()["items"]) == 1


def test_reenter_after_completed_auto_task_creates_new_task(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.complete@example.com",
        phone="+90 555 321 44 07",
        full_name="Complete Lead",
    )
    lead_id = lead["id"]
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    task_id = listed.json()["items"][0]["id"]
    completed = client.post(f"/crm/tasks/{task_id}/complete")
    assert completed.status_code == 200, completed.text
    db.expire_all()
    assert _task_row(db, task_id).task_status == CrmTaskStatus.COMPLETED

    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "following"})
    reentered = client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    assert reentered.status_code == 200
    after = client.get("/crm/tasks", params={"lead_id": lead_id})
    ids = {item["id"] for item in after.json()["items"]}
    assert task_id in ids
    assert len(ids) == 2
    new_ids = ids - {task_id}
    db.expire_all()
    new_row = _task_row(db, next(iter(new_ids)))
    assert (new_row.metadata_json or {}).get("source") == "stage_automation"
    assert (new_row.metadata_json or {}).get("source_stage_id") == "contacted"
    assert new_row.task_status == CrmTaskStatus.NOT_STARTED


def test_manual_task_creation_still_works_alongside_auto_task(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.manual@example.com",
        phone="+90 555 321 44 08",
        full_name="Manual Mix",
    )
    lead_id = lead["id"]
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    manual = client.post(
        "/crm/tasks",
        json={
            "title": "Elle eklenen görev",
            "lead_id": lead_id,
            "due_on": "2026-10-12",
            "due_time": "11:00",
            "timezone": "Europe/Istanbul",
        },
    )
    assert manual.status_code == 201, manual.text
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    titles = {item["title"] for item in listed.json()["items"]}
    assert "Elle eklenen görev" in titles
    assert f"Takip — {lead['full_name']}" in titles
    db.expire_all()
    auto_rows = [
        row
        for row in db.query(CrmActivity).all()
        if isinstance(row.metadata_json, dict) and row.metadata_json.get("source") == "stage_automation"
        and (row.metadata_json.get("task_links") or {}).get("lead_id") == lead_id
    ]
    assert len(auto_rows) == 1
    manual_meta = manual.json()["activity"]["metadata_json"]
    assert (manual_meta or {}).get("source") != "stage_automation"


def test_contacted_and_proposal_automations_are_independent(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.both@example.com",
        phone="+90 555 321 44 09",
        full_name="İki Aşama",
    )
    lead_id = lead["id"]
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "proposal"})
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    assert len(listed.json()["items"]) == 2
    db.expire_all()
    stages = set()
    for item in listed.json()["items"]:
        meta = _task_row(db, item["id"]).metadata_json or {}
        stages.add(meta.get("source_stage_id"))
    assert stages == {"contacted", "proposal"}


def test_due_reminder_dispatches_existing_in_app_notification(client: TestClient, db: Session) -> None:
    lead = _create_lead(
        client,
        email="auto.remind@example.com",
        phone="+90 555 321 44 10",
        full_name="Hatırlatma Lead",
    )
    lead_id = lead["id"]
    client.post(f"/crm/leads/{lead_id}/stage", json={"stage": "contacted"})
    listed = client.get("/crm/tasks", params={"lead_id": lead_id})
    task_id = listed.json()["items"][0]["id"]
    db.expire_all()
    row = _task_row(db, task_id)
    due = row.due_date
    if due.tzinfo is None:
        due = due.replace(tzinfo=UTC)
    result = run_crm_task_due_reminders(clock=due + timedelta(seconds=1), db=db)
    db.commit()
    assert result["reminders_sent"] == 1
    reminder = db.query(CrmActivityReminder).filter_by(activity_id=row.id).one()
    assert reminder.is_sent is True
    notifications = (
        db.query(Notification)
        .filter(Notification.dedupe_key.like(f"crm.task.due.{row.id}:%"))
        .all()
    )
    assert len(notifications) == 1
    assert notifications[0].title_key == "notifications.crm.task_due.title"
    assert notifications[0].type == NotificationType.REMINDER
    assert str(notifications[0].recipient_user_id) == str(row.assigned_user_id)
    repeat = run_crm_task_due_reminders(clock=due + timedelta(minutes=5), db=db)
    db.commit()
    assert repeat["reminders_sent"] == 0
