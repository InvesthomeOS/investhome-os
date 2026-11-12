"""User notification preferences and the shared dispatch path."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity, CrmActivityReminder, CrmActivityType, CrmReminderChannel
from investhome_api.models.notification import Notification, NotificationStatus
from investhome_api.models.user_auth import User
from investhome_api.services.crm.task_reminder_jobs import run_crm_task_due_reminders
from investhome_api.services.notification_service import enrich_notification
from investhome_api.services.user_notifications import (
    DispatchRequest,
    dispatch_user_event,
    email_enabled,
    in_app_enabled,
    list_preference_state,
)


def _bypass(client: TestClient, db: Session) -> User:
    saved = client.put("/notifications/preferences", json={"items": []})
    assert saved.status_code == 200, saved.text
    db.expire_all()
    return db.query(User).filter_by(email="dev-bypass@example.com").one()


def test_default_preferences_are_in_app_on_email_off(client: TestClient, db: Session) -> None:
    user = _bypass(client, db)
    state = {item["event_key"]: item for item in list_preference_state(db, user.id)}
    assert state["new_lead"]["in_app"] is True
    assert state["new_lead"]["email"] is False
    assert state["task_reminder"]["email"] is False
    assert in_app_enabled(db, user.id, "instagram_message") is True
    assert email_enabled(db, user.id, "instagram_message") is False


def test_preference_update_and_both_disabled(client: TestClient, db: Session) -> None:
    user = _bypass(client, db)
    saved = client.put(
        "/notifications/preferences",
        json={
            "items": [
                {"event_key": "new_lead", "in_app": False, "email": True},
                {"event_key": "task_overdue", "in_app": False, "email": False},
            ]
        },
    )
    assert saved.status_code == 200, saved.text
    by_key = {item["event_key"]: item for item in saved.json()["items"]}
    assert by_key["new_lead"]["in_app"] is False
    assert by_key["new_lead"]["email"] is True
    assert by_key["task_overdue"]["in_app"] is False
    assert by_key["task_overdue"]["email"] is False
    assert by_key["task_reminder"]["in_app"] is True
    assert by_key["task_reminder"]["email"] is False

    entity_id = uuid4()
    outcome = dispatch_user_event(
        db,
        DispatchRequest(
            event_key="task_overdue",
            recipient_user_id=user.id,
            title_key="notifications.crm.task_overdue.title",
            message_key="notifications.crm.task_overdue.message",
            rule_key="crm.task.overdue.test",
            related_entity_type="crm_activity",
            related_entity_id=entity_id,
            metadata={"title": "Teklif gönder"},
        ),
    )
    db.commit()
    assert outcome["in_app"] == "disabled"
    assert outcome["email"] == "disabled"
    assert db.query(Notification).filter_by(recipient_user_id=user.id, related_entity_id=entity_id).count() == 0


def test_in_app_unread_link_and_duplicate_and_missing_email(client: TestClient, db: Session, monkeypatch) -> None:
    user = _bypass(client, db)
    user.email = ""
    db.commit()
    entity_id = uuid4()
    calls: list = []

    class Gateway:
        def dispatch(self, message, provider_id="email_smtp"):
            calls.append(message)
            return SimpleNamespace(ok=True, status="sent")

    monkeypatch.setattr(
        "investhome_api.services.user_notifications.get_notification_gateway",
        lambda: Gateway(),
    )
    client.put(
        "/notifications/preferences",
        json={"items": [{"event_key": "new_lead", "in_app": True, "email": True}]},
    )
    request = DispatchRequest(
        event_key="new_lead",
        recipient_user_id=user.id,
        title_key="notifications.crm.new_lead.title",
        message_key="notifications.crm.new_lead.message",
        rule_key="crm.lead.created",
        related_entity_type="lead",
        related_entity_id=entity_id,
        link_module="crm/contacts",
        link_query={"contact": str(uuid4()), "lead": str(entity_id)},
        destination_path=f"/workspaces/crm/contacts?lead={entity_id}",
        email_subject="Yeni Lead: Ahmet Yılmaz",
        metadata={"name": "Ahmet Yılmaz", "title": "Ahmet Yılmaz"},
    )
    first = dispatch_user_event(db, request)
    db.commit()
    assert first["in_app"] == "sent"
    assert first["email"] == "missing"
    assert calls == []
    row = db.query(Notification).filter_by(recipient_user_id=user.id, related_entity_id=entity_id).one()
    assert row.status == NotificationStatus.UNREAD
    enriched = enrich_notification(row)
    assert enriched["link_module"] == "crm/contacts"
    assert enriched["link_query"]["lead"] == str(entity_id)
    second = dispatch_user_event(db, request)
    db.commit()
    assert second["in_app"] == "duplicate"
    assert db.query(Notification).filter_by(recipient_user_id=user.id, related_entity_id=entity_id).count() == 1


def test_new_lead_notifies_once_and_update_does_not(client: TestClient, db: Session) -> None:
    created = client.post(
        "/crm/leads",
        json={"full_name": "Ahmet Yılmaz", "phone": "+90 555 100 20 30", "source": "manual"},
    )
    assert created.status_code == 201, created.text
    lead_id = created.json()["id"]
    db.expire_all()
    notes = db.query(Notification).filter(Notification.dedupe_key.like(f"crm.lead.created:lead:{lead_id}")).all()
    assert len(notes) == 1
    assert notes[0].title_key == "notifications.crm.new_lead.title"
    updated = client.patch(f"/crm/leads/{lead_id}", json={"notes": "sadece güncelleme"})
    assert updated.status_code == 200, updated.text
    db.expire_all()
    assert db.query(Notification).filter(Notification.dedupe_key.like(f"crm.lead.created:lead:{lead_id}")).count() == 1


def test_task_reminder_respects_email_preference_and_overdue_is_once(
    client: TestClient, db: Session, monkeypatch
) -> None:
    user = _bypass(client, db)
    calls: list = []

    class Gateway:
        def dispatch(self, message, provider_id="email_smtp"):
            calls.append((message.subject, provider_id))
            return SimpleNamespace(ok=True, status="sent")

    monkeypatch.setattr(
        "investhome_api.services.user_notifications.get_notification_gateway",
        lambda: Gateway(),
    )
    person = client.post(
        "/crm/contacts",
        json={
            "contact_type": "prospect",
            "record_kind": "person",
            "display_name": "Görev Kişisi",
            "primary_email": "gorev.pref@example.com",
        },
    )
    assert person.status_code == 201, person.text
    contact_id = person.json()["contact"]["id"]
    due = datetime.now(UTC) - timedelta(hours=2)
    created = client.post(
        "/crm/tasks",
        json={
            "title": "Teklif gönder",
            "contact_id": contact_id,
            "assigned_user_id": str(user.id),
            "due_date": due.isoformat(),
            "reminders": [
                {"channel": "in_app", "remind_at": (due - timedelta(minutes=15)).isoformat(), "offset_minutes": 15},
                {"channel": "email", "remind_at": (due - timedelta(minutes=15)).isoformat(), "offset_minutes": 15},
            ],
        },
    )
    assert created.status_code == 201, created.text
    activity_id = UUID(created.json()["activity"]["id"])
    result = run_crm_task_due_reminders(clock=datetime.now(UTC), db=db)
    db.commit()
    assert result["reminders_sent"] == 2
    assert calls == []
    db.expire_all()
    reminders = db.query(CrmActivityReminder).filter_by(activity_id=activity_id).all()
    assert {row.channel for row in reminders} == {CrmReminderChannel.IN_APP, CrmReminderChannel.EMAIL}
    assert all(row.is_sent for row in reminders)
    in_app = (
        db.query(Notification)
        .filter(Notification.dedupe_key.like(f"crm.task.due.{activity_id}.%"))
        .all()
    )
    assert len(in_app) == 1
    overdue = (
        db.query(Notification)
        .filter(Notification.dedupe_key.like(f"crm.task.overdue.{activity_id}:%"))
        .one()
    )
    assert overdue.title_key == "notifications.crm.task_overdue.title"
    assert enrich_notification(overdue)["link_module"] == "crm/tasks"
    again = run_crm_task_due_reminders(clock=datetime.now(UTC) + timedelta(minutes=10), db=db)
    db.commit()
    assert again["reminders_sent"] == 0
    assert db.query(Notification).filter(Notification.dedupe_key.like(f"crm.task.overdue.{activity_id}:%")).count() == 1
    task = db.get(CrmActivity, activity_id)
    assert task is not None
    assert task.activity_type == CrmActivityType.TASK
