"""Notification center tests."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import ActivityLog
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.notification import (
    Notification,
    NotificationPriority,
    NotificationSource,
    NotificationStatus,
    NotificationType,
)
from investhome_api.models.user_auth import User
from investhome_api.services.notification_generator import sync_notifications_for_user
from investhome_api.services.notification_service import create_notification


def _login(auth_client: TestClient, email: str) -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _session(auth_client: TestClient) -> Session:
    from investhome_api.db.session import get_db

    override = auth_client.app.dependency_overrides.get(get_db)
    assert override is not None
    return next(override())


def test_notifications_require_permission(auth_client: TestClient) -> None:
    _login(auth_client, "readonly@example.com")
    denied = auth_client.get("/notifications")
    assert denied.status_code == 403

    _login(auth_client, "admin@example.com")
    allowed = auth_client.get("/notifications")
    assert allowed.status_code == 200
    assert "items" in allowed.json()


def test_create_notification_and_list(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        entity_id = uuid4()
        create_notification(
            session,
            recipient_user_id=admin.id,
            type=NotificationType.REMINDER,
            priority=NotificationPriority.HIGH,
            title_key="notifications.lead.no_followup.title",
            message_key="notifications.lead.no_followup.message",
            rule_key="lead.no_followup",
            related_entity_type="lead",
            related_entity_id=entity_id,
            metadata={"name": "Test Lead", "days": 7},
            source=NotificationSource.AUTOMATION,
            commit=True,
        )
    finally:
        session.close()

    response = auth_client.get("/notifications?sync=false")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] >= 1
    assert payload["unread_count"] >= 1
    assert any(item["title_key"] == "notifications.lead.no_followup.title" for item in payload["items"])


def test_mark_read_and_dismiss(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    notification_id: UUID | None = None
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        notification = create_notification(
            session,
            recipient_user_id=admin.id,
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.INFO,
            title_key="notifications.user.invited.title",
            message_key="notifications.user.invited.message",
            rule_key="user.invited",
            related_entity_type="user",
            related_entity_id=admin.id,
            source=NotificationSource.ACTIVITY,
            commit=True,
        )
        assert notification is not None
        notification_id = notification.id
    finally:
        session.close()

    assert notification_id is not None
    read_response = auth_client.post(f"/notifications/{notification_id}/read")
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"

    dismiss_response = auth_client.post(f"/notifications/{notification_id}/dismiss")
    assert dismiss_response.status_code == 200
    assert dismiss_response.json()["status"] == "dismissed"


def test_mark_all_read(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        for index in range(2):
            create_notification(
                session,
                recipient_user_id=admin.id,
                type=NotificationType.REMINDER,
                priority=NotificationPriority.MEDIUM,
                title_key="notifications.lead.qualified_waiting.title",
                message_key="notifications.lead.qualified_waiting.message",
                rule_key=f"lead.qualified_waiting.{index}",
                related_entity_type="lead",
                related_entity_id=uuid4(),
                metadata={"name": f"Lead {index}"},
                source=NotificationSource.AUTOMATION,
                commit=True,
            )
    finally:
        session.close()

    mark_all = auth_client.post("/notifications/read-all")
    assert mark_all.status_code == 200
    assert mark_all.json()["updated"] >= 2

    unread = auth_client.get("/notifications/unread-count?sync=false")
    assert unread.status_code == 200
    assert unread.json()["unread_count"] == 0


def test_summary_counts(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        specs = [
            (NotificationPriority.CRITICAL, "critical.rule"),
            (NotificationPriority.HIGH, "high.rule"),
            (NotificationPriority.MEDIUM, "medium.rule"),
        ]
        for priority, rule in specs:
            create_notification(
                session,
                recipient_user_id=admin.id,
                type=NotificationType.SYSTEM,
                priority=priority,
                title_key="notifications.activity.permission_changed.title",
                message_key="notifications.activity.permission_changed.message",
                rule_key=rule,
                related_entity_type="role",
                related_entity_id=uuid4(),
                source=NotificationSource.ACTIVITY,
                commit=True,
            )
    finally:
        session.close()

    summary = auth_client.get("/notifications/summary?sync=false")
    assert summary.status_code == 200
    body = summary.json()
    assert body["critical"] >= 1
    assert body["high"] >= 1
    assert body["medium"] >= 1
    assert body["unread"] >= 3


def test_reading_notification_does_not_create_activity(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    notification_id: UUID | None = None
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        before_count = len(session.scalars(select(ActivityLog)).all())
        notification = create_notification(
            session,
            recipient_user_id=admin.id,
            type=NotificationType.REMINDER,
            priority=NotificationPriority.LOW,
            title_key="notifications.lead.meeting_today.title",
            message_key="notifications.lead.meeting_today.message",
            rule_key="lead.meeting_today",
            related_entity_type="lead",
            related_entity_id=uuid4(),
            metadata={"name": "Meeting Lead"},
            source=NotificationSource.AUTOMATION,
            commit=True,
        )
        assert notification is not None
        notification_id = notification.id
        after_create_count = len(session.scalars(select(ActivityLog)).all())
        assert after_create_count == before_count
    finally:
        session.close()

    assert notification_id is not None
    read_response = auth_client.post(f"/notifications/{notification_id}/read")
    assert read_response.status_code == 200

    session = _session(auth_client)
    try:
        after_read_count = len(session.scalars(select(ActivityLog)).all())
        assert after_read_count == before_count
    finally:
        session.close()


def test_sync_generates_lead_no_followup_notification(auth_client: TestClient) -> None:
    _login(auth_client, "sales@example.com")
    session = _session(auth_client)
    try:
        sales = session.scalar(select(User).where(User.email == "sales@example.com"))
        assert sales is not None
        lead = Lead(
            full_name="Stale Lead",
            email="stale.lead@example.com",
            status=LeadStatus.NEW,
        )
        session.add(lead)
        session.flush()
        lead.updated_at = datetime.now(UTC) - timedelta(days=10)
        session.commit()
        sync_notifications_for_user(session, sales)
        session.commit()
        notification = session.scalar(
            select(Notification).where(
                Notification.recipient_user_id == sales.id,
                Notification.dedupe_key.like("lead.no_followup:%"),
            )
        )
        assert notification is not None
        assert notification.title_key == "notifications.lead.no_followup.title"
    finally:
        session.close()

    listed = auth_client.get("/notifications?sync=false")
    assert listed.status_code == 200
    assert any(
        item["title_key"] == "notifications.lead.no_followup.title" for item in listed.json()["items"]
    )


def test_user_only_sees_own_notifications(auth_client: TestClient) -> None:
    session = _session(auth_client)
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        sales = session.scalar(select(User).where(User.email == "sales@example.com"))
        assert admin is not None and sales is not None
        create_notification(
            session,
            recipient_user_id=admin.id,
            type=NotificationType.SYSTEM,
            priority=NotificationPriority.HIGH,
            title_key="notifications.user.deactivated.title",
            message_key="notifications.user.deactivated.message",
            rule_key="user.deactivated",
            related_entity_type="user",
            related_entity_id=admin.id,
            source=NotificationSource.ACTIVITY,
            commit=True,
        )
    finally:
        session.close()

    _login(auth_client, "sales@example.com")
    sales_list = auth_client.get("/notifications?sync=false")
    assert sales_list.status_code == 200
    sales_body = sales_list.json()
    session = _session(auth_client)
    try:
        sales = session.scalar(select(User).where(User.email == "sales@example.com"))
        assert sales is not None
        assert all(item["recipient_user_id"] == str(sales.id) for item in sales_body["items"])
        assert all(
            item["title_key"] != "notifications.user.deactivated.title" for item in sales_body["items"]
        )
    finally:
        session.close()
