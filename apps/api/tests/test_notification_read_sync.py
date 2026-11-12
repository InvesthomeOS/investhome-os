"""Notification reads stay cheap; legacy rules sync on the worker."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.models.notification import Notification
from investhome_api.models.user_auth import User
from investhome_api.services.notification_generator import (
    JOB_NOTIFICATION_RULE_SYNC,
    notification_rule_sync_job,
    run_notification_rule_sync,
)
from investhome_api.services.user_notifications import DispatchRequest, dispatch_user_event
from investhome_api.worker.settings import WorkerSettings


def _login(auth_client: TestClient, email: str) -> None:
    response = auth_client.post("/auth/login", json={"email": email, "password": "Demo123!"})
    assert response.status_code == 200


def _session(auth_client: TestClient) -> Session:
    from investhome_api.db.session import get_db

    override = auth_client.app.dependency_overrides.get(get_db)
    assert override is not None
    return next(override())


def test_read_endpoints_do_not_run_full_sync(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def forbidden(*_args, **_kwargs):
        calls.append("sync")
        raise AssertionError("notification read invoked full sync")

    monkeypatch.setattr(
        "investhome_api.services.notification_generator.sync_notifications_for_user",
        forbidden,
    )
    monkeypatch.setattr(
        "investhome_api.services.notification_generator.sync_notifications_for_all_users",
        forbidden,
    )
    _login(auth_client, "admin@example.com")
    for path in (
        "/notifications",
        "/notifications?sync=true",
        "/notifications/unread-count",
        "/notifications/unread-count?sync=true",
        "/notifications/summary",
        "/notifications/summary?sync=true",
    ):
        response = auth_client.get(path)
        assert response.status_code == 200, response.text
    assert calls == []


def test_unread_badge_and_list_without_sync(auth_client: TestClient) -> None:
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    entity_id = uuid4()
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        outcome = dispatch_user_event(
            session,
            DispatchRequest(
                event_key="new_lead",
                recipient_user_id=admin.id,
                title_key="notifications.crm.new_lead.title",
                message_key="notifications.crm.new_lead.message",
                rule_key="crm.lead.created.read-sync",
                related_entity_type="lead",
                related_entity_id=entity_id,
                metadata={"name": "Read Sync Lead"},
                allow_email=False,
            ),
        )
        session.commit()
        assert outcome["in_app"] == "sent"
    finally:
        session.close()

    listed = auth_client.get("/notifications")
    assert listed.status_code == 200
    body = listed.json()
    assert body["unread_count"] >= 1
    assert any(item["related_entity_id"] == str(entity_id) and item["status"] == "unread" for item in body["items"])

    counts = auth_client.get("/notifications/unread-count")
    assert counts.status_code == 200
    assert counts.json()["unread_count"] >= 1
    assert counts.json()["highest_priority"] in {"info", "low", "medium", "high", "critical"}


def test_notification_rule_sync_is_scheduled_every_five_minutes() -> None:
    assert notification_rule_sync_job in WorkerSettings.functions
    assert WorkerSettings.job_name_map[JOB_NOTIFICATION_RULE_SYNC] is notification_rule_sync_job
    matches = [job for job in WorkerSettings.cron_jobs if job.name == JOB_NOTIFICATION_RULE_SYNC]
    assert len(matches) == 1
    assert set(matches[0].minute) == {0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55}
    assert matches[0].coroutine is notification_rule_sync_job


def _spy_session(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    from investhome_api.db import session as db_session

    events: list[str] = []
    real = db_session.SessionLocal

    def factory():
        db = real()
        original_commit = db.commit
        original_rollback = db.rollback
        original_close = db.close

        def commit():
            events.append("commit")
            return original_commit()

        def rollback():
            events.append("rollback")
            return original_rollback()

        def close():
            events.append("close")
            return original_close()

        db.commit = commit  # type: ignore[method-assign]
        db.rollback = rollback  # type: ignore[method-assign]
        db.close = close  # type: ignore[method-assign]
        return db

    monkeypatch.setattr(db_session, "SessionLocal", factory)
    return events


def test_worker_sync_closes_session_after_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    del client
    events = _spy_session(monkeypatch)

    def fake_sync(db: Session) -> int:
        db.commit()
        return 4

    monkeypatch.setattr(
        "investhome_api.services.notification_generator.sync_notifications_for_all_users",
        fake_sync,
    )
    result = run_notification_rule_sync()
    assert result == {"notifications_synced": 4}
    assert events == ["commit", "close"]
    job_result = asyncio.run(notification_rule_sync_job({}))
    assert job_result == {"notifications_synced": 4}
    assert events == ["commit", "close", "commit", "close"]


def test_worker_sync_rolls_back_and_closes_after_exception(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    del client
    events = _spy_session(monkeypatch)

    def fake_sync(db: Session) -> int:
        db.execute(text("SELECT 1"))
        raise RuntimeError("sync failed")

    monkeypatch.setattr(
        "investhome_api.services.notification_generator.sync_notifications_for_all_users",
        fake_sync,
    )
    with pytest.raises(RuntimeError, match="sync failed"):
        run_notification_rule_sync()
    assert "rollback" in events
    assert "close" in events
    assert events.index("rollback") < events.index("close")
    assert db_has_no_open_job_session(events)


def db_has_no_open_job_session(events: list[str]) -> bool:
    return events[-1] == "close"


def test_event_dispatch_does_not_wait_for_rule_sync(auth_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        "investhome_api.services.notification_generator.sync_notifications_for_user",
        lambda *_args, **_kwargs: calls.append("user") or 0,
    )
    _login(auth_client, "admin@example.com")
    session = _session(auth_client)
    entity_id = uuid4()
    try:
        admin = session.scalar(select(User).where(User.email == "admin@example.com"))
        assert admin is not None
        outcome = dispatch_user_event(
            session,
            DispatchRequest(
                event_key="agreement_event",
                recipient_user_id=admin.id,
                title_key="notifications.crm.agreement.title",
                message_key="notifications.crm.agreement.message",
                rule_key="crm.agreement.created.read-sync",
                related_entity_type="crm_agreement",
                related_entity_id=entity_id,
                allow_email=False,
            ),
        )
        session.commit()
        stored = session.scalar(select(Notification).where(Notification.related_entity_id == entity_id))
        assert stored is not None
        assert outcome["in_app"] == "sent"
    finally:
        session.close()

    visible = auth_client.get("/notifications")
    assert visible.status_code == 200
    assert any(item["related_entity_id"] == str(entity_id) for item in visible.json()["items"])
    assert calls == []
