"""Inbound Meta CRM email notifications: queue after commit, send in the worker."""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.crm_communication import CrmCommunication
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.lead import Lead
from investhome_api.models.user_auth import Role, User, UserRole, UserStatus
from investhome_api.services.auth_service import hash_password
from investhome_api.services.crm import meta_webhook as meta
from investhome_api.services.crm.meta_comments import (
    comment_conversation_key,
    send_meta_comment_reply,
)
from investhome_api.services.crm.meta_inbound_notify import (
    MemoryNotifyLock,
    MetaInboundEmailRetry,
    deliver_meta_inbound_email,
    meta_inbound_email_job,
)
from investhome_api.services.crm.meta_send import send_meta_dm
from investhome_api.services.notification_gateway import GatewayResult, NotificationChannel
from test_meta_comments import _fb_comment_payload, _ig_comment_payload
from test_meta_webhook import (
    IG_WEBHOOK_ACCOUNT_ID,
    PAGE_ID,
    _ig_payload,
    _payload,
    _post,
)

NOTIFY = "investhome.crm.meta_inbound_email"


class _Queue:
    def __init__(self) -> None:
        self.ids: list[str] = []
        self.fail = False

    def __call__(self, communication_ids: list[str]) -> None:
        if self.fail:
            raise RuntimeError("redis down")
        self.ids.extend(communication_ids)


class _Gateway:
    def __init__(self, *, ok: bool = True, fail_emails: set[str] | None = None) -> None:
        self.ok = ok
        self.fail_emails = set(fail_emails or set())
        self.messages: list = []

    def dispatch(self, message, *, provider_id: str | None = None):
        assert provider_id == "email_smtp"
        self.messages.append(message)
        failed = (not self.ok) or message.recipient in self.fail_emails
        return GatewayResult(
            ok=not failed,
            provider_id="email_smtp",
            channel=NotificationChannel.EMAIL,
            status="sent" if not failed else "failed",
            detail=None if not failed else "SMTP send failed",
        )


@pytest.fixture(autouse=True)
def _notify_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("META_APP_SECRET", "unit-test-meta-app-secret-32charsxxxx")
    monkeypatch.setenv("META_INSTAGRAM_APP_SECRET", "unit-test-meta-ig-app-secret-32charsxxx")
    monkeypatch.setenv("META_VERIFY_TOKEN", "unit-test-meta-verify-token")
    monkeypatch.setenv("META_PAGE_ID", PAGE_ID)
    monkeypatch.setenv("META_INSTAGRAM_ACCOUNT_ID", "27943000000000001")
    monkeypatch.setenv("META_INSTAGRAM_WEBHOOK_ACCOUNT_ID", IG_WEBHOOK_ACCOUNT_ID)
    monkeypatch.setenv("CRM_INBOUND_EMAIL_NOTIFICATIONS_ENABLED", "true")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://os.example.test")
    monkeypatch.delenv("CRM_INBOUND_NOTIFY_EMAIL", raising=False)
    get_settings.cache_clear()
    meta.reset_meta_idempotency_for_tests()
    queue = _Queue()
    monkeypatch.setattr(
        "investhome_api.services.crm.meta_inbound_notify._enqueue_ids",
        queue,
    )
    yield queue
    meta.reset_meta_idempotency_for_tests()
    get_settings.cache_clear()


def _count(db: Session, external_id: str) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(CrmCommunication).where(
                CrmCommunication.external_provider_id == external_id
            )
        )
        or 0
    )


def _row(db: Session, external_id: str) -> CrmCommunication:
    db.expire_all()
    row = db.scalar(
        select(CrmCommunication).where(CrmCommunication.external_provider_id == external_id)
    )
    assert row is not None
    return row


def _user(db: Session, email: str, status: UserStatus) -> User:
    user = User(
        full_name="Ayse Yilmaz",
        email=email,
        hashed_password=hash_password("Demo123!"),
        status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _assign_role(db: Session, user: User, code: str) -> None:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        role = Role(name=code, code=code, is_system_role=True)
        db.add(role)
        db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    db.commit()


def _sales_user(db: Session, email: str, status: UserStatus = UserStatus.ACTIVE) -> User:
    user = _user(db, email, status)
    _assign_role(db, user, "sales")
    return user


def _sent_to(gateway: _Gateway) -> set[str]:
    return {item.recipient for item in gateway.messages}


def _gateway(
    monkeypatch: pytest.MonkeyPatch,
    *,
    ok: bool = True,
    fail_emails: set[str] | None = None,
) -> _Gateway:
    gateway = _Gateway(ok=ok, fail_emails=fail_emails)
    monkeypatch.setattr(
        "investhome_api.services.crm.meta_inbound_notify.get_notification_gateway",
        lambda: gateway,
    )
    return gateway


def _deliver(db: Session, communication_id, gateway_lock: MemoryNotifyLock | None = None) -> str:
    return deliver_meta_inbound_email(
        communication_id,
        db=db,
        lock=gateway_lock or MemoryNotifyLock(),
    )


def test_new_instagram_dm_queues_one_job(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(
        client,
        _ig_payload(message_id=message_id, text="Merhaba <script>alert(1)</script>"),
    )
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    assert "created_ids" not in response.json()
    assert _count(db, message_id) == 1
    assert _notify_env.ids == [str(_row(db, message_id).id)]


def test_duplicate_instagram_dm_does_not_queue_again(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    payload = _ig_payload(message_id=message_id, text="Bir kez")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.status_code == 200
    assert second.json()["duplicate"] is True
    assert _count(db, message_id) == 1
    assert len(_notify_env.ids) == 1


def test_new_facebook_dm_queues_one_job(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _payload(message_id=message_id, text="FB mesaj"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    assert _notify_env.ids == [str(_row(db, message_id).id)]


def test_new_instagram_comment_queues_one_job(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    comment_id = f"igc_{uuid4().hex[:10]}"
    response, _ = _post(client, _ig_comment_payload(comment_id=comment_id, text="IG yorum"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    assert _notify_env.ids == [str(_row(db, comment_id).id)]


def test_new_facebook_comment_queues_one_job(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comment_id = f"{PAGE_ID}_cmt_{uuid4().hex[:8]}"
    response, _ = _post(client, _fb_comment_payload(comment_id=comment_id, name="The Temple"))
    assert response.status_code == 200, response.text
    assert response.json()["ingested"] == 1
    comm = _row(db, comment_id)
    assert _notify_env.ids == [str(comm.id)]
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    contact.display_name = "The Temple"
    db.commit()
    fallback = f"fb-{uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("CRM_INBOUND_NOTIFY_EMAIL", fallback)
    get_settings.cache_clear()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert gateway.messages[0].subject == "[Investhome CRM] Yeni Facebook Yorumu — The Temple"
    assert "Tür: Yorum" in gateway.messages[0].body
    assert gateway.messages[0].recipient == fallback


def test_facebook_page_comment_and_delete_do_not_queue(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    own_id = f"{PAGE_ID}_own_{uuid4().hex[:8]}"
    delete_id = f"{PAGE_ID}_del_{uuid4().hex[:8]}"
    remove_id = f"{PAGE_ID}_rm_{uuid4().hex[:8]}"
    own, _ = _post(client, _fb_comment_payload(comment_id=own_id, sender=PAGE_ID))
    deleted, _ = _post(client, _fb_comment_payload(comment_id=delete_id, verb="delete"))
    removed, _ = _post(client, _fb_comment_payload(comment_id=remove_id, verb="remove"))
    assert own.json()["ingested"] == 0
    assert deleted.json()["ingested"] == 0
    assert removed.json()["ingested"] == 0
    assert _notify_env.ids == []
    assert _count(db, own_id) == 0
    assert _count(db, delete_id) == 0
    assert _count(db, remove_id) == 0


def test_instagram_account_comment_does_not_queue(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    comment_id = f"igown_{uuid4().hex[:8]}"
    response, _ = _post(
        client,
        _ig_comment_payload(comment_id=comment_id, sender=IG_WEBHOOK_ACCOUNT_ID),
    )
    assert response.status_code == 200
    assert response.json()["ingested"] == 0
    assert _notify_env.ids == []
    assert _count(db, comment_id) == 0


def test_facebook_comment_edit_does_not_queue_again(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
) -> None:
    comment_id = f"{PAGE_ID}_edit_{uuid4().hex[:8]}"
    first, _ = _post(client, _fb_comment_payload(comment_id=comment_id, verb="add"))
    second, _ = _post(
        client,
        _fb_comment_payload(comment_id=comment_id, verb="edit", text="Guncel"),
    )
    assert first.json()["ingested"] == 1
    assert second.json()["ingested"] == 0
    assert _count(db, comment_id) == 1
    assert len(_notify_env.ids) == 1


def test_echo_does_not_queue(client: TestClient, db: Session, _notify_env: _Queue) -> None:
    message_id = f"mid.{uuid4().hex}"
    payload = _payload(message_id=message_id)
    payload["entry"][0]["messaging"][0]["message"]["is_echo"] = True
    response, _ = _post(client, payload)
    assert response.status_code == 200
    assert response.json()["ingested"] == 0
    assert _notify_env.ids == []
    assert _count(db, message_id) == 0


def test_outgoing_dm_and_comment_reply_do_not_queue(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    sender = "1029384756102938"
    _post(client, _payload(message_id=message_id, sender=sender, text="Gelen"))
    assert len(_notify_env.ids) == 1
    inbound = _row(db, message_id)
    actor = _user(db, f"actor-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    monkeypatch.setattr(
        "investhome_api.services.crm.meta_send.graph_send_text",
        lambda **kwargs: f"out-{uuid4().hex}",
    )
    outbound, created = send_meta_dm(
        db,
        channel="facebook",
        contact_id=inbound.contact_id,
        text="Cevap",
        conversation_key=sender,
        actor=actor,
    )
    assert created is True
    assert outbound.direction == "outbound"
    assert _notify_env.ids == [str(inbound.id)]

    comment_id = f"{PAGE_ID}_cmt_{uuid4().hex[:8]}"
    _post(client, _fb_comment_payload(comment_id=comment_id, text="Yorum"))
    assert len(_notify_env.ids) == 2
    comment = _row(db, comment_id)
    monkeypatch.setattr(
        "investhome_api.services.crm.meta_comments.graph_reply_comment",
        lambda **kwargs: f"reply-{uuid4().hex}",
    )
    reply, reply_created = send_meta_comment_reply(
        db,
        channel="facebook",
        contact_id=comment.contact_id,
        text="Tesekkurler",
        conversation_key=comment_conversation_key(comment_id),
        actor=actor,
    )
    assert reply_created is True
    assert reply.direction == "outbound"
    assert str(reply.id) not in _notify_env.ids
    gateway = _gateway(monkeypatch)
    assert _deliver(db, outbound.id) == "skipped"
    assert _deliver(db, reply.id) == "skipped"
    assert gateway.messages == []


def test_active_contact_owner_receives_email(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    text = "Merhaba <script>alert(1)</script>"
    _post(client, _ig_payload(message_id=message_id, text=text))
    comm = _row(db, message_id)
    owner = _user(db, f"owner-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    manager = _user(db, f"manager-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    contact.display_name = "Ahmet Yilmaz"
    contact.owner_user_id = owner.id
    lead = db.get(Lead, contact.lead_id)
    assert lead is not None
    lead.assigned_manager_id = manager.id
    lead.interested_project = "The Temple"
    db.commit()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    by_recipient = {item.recipient: item for item in gateway.messages}
    assert set(by_recipient) == {owner.email, manager.email}
    message = by_recipient[owner.email]
    assert message.subject == "[Investhome CRM] Yeni Instagram Mesajı — Ahmet Yilmaz"
    assert "Platform: Instagram" in message.body
    assert "Tür: Mesaj" in message.body
    assert "The Temple" in message.body
    assert "&lt;script&gt;" in message.html_body
    assert "<script>" not in message.html_body
    assert f"/workspaces/crm/contacts/{contact.id}" in message.body
    assert str(comm.id) not in message.body
    db.refresh(comm)
    notice = (comm.metadata_json or {})["inbound_email_notification"]
    assert notice["status"] == "sent"
    assert notice["recipients"][str(owner.id)]["source"] == "contact_owner"
    assert notice["recipients"][str(manager.id)]["source"] == "lead_manager"
    assert "email" not in notice


def test_lead_manager_used_when_contact_has_no_owner(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _payload(message_id=message_id, text="FB"))
    comm = _row(db, message_id)
    manager = _user(db, f"lead-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None and contact.owner_user_id is None
    lead = db.get(Lead, contact.lead_id)
    assert lead is not None
    lead.assigned_manager_id = manager.id
    db.commit()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert gateway.messages[0].recipient == manager.email
    db.refresh(comm)
    notice = comm.metadata_json["inbound_email_notification"]
    assert notice["recipients"][str(manager.id)]["source"] == "lead_manager"


@pytest.mark.parametrize("status", [UserStatus.INACTIVE, UserStatus.SUSPENDED, UserStatus.INVITED])
def test_inactive_owner_uses_fallback(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
    status: UserStatus,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _ig_payload(message_id=message_id, text="Durum"))
    comm = _row(db, message_id)
    owner = _user(db, f"off-{uuid4().hex[:8]}@example.com", status)
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    contact.owner_user_id = owner.id
    db.commit()
    fallback = f"fallback-{uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("CRM_INBOUND_NOTIFY_EMAIL", fallback)
    get_settings.cache_clear()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert gateway.messages[0].recipient == fallback
    assert owner.email not in {item.recipient for item in gateway.messages}
    db.refresh(comm)
    notice = comm.metadata_json["inbound_email_notification"]
    assert notice["recipients"]["fallback"]["source"] == "fallback"


def test_missing_recipient_skips_without_failing_ingestion(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, text="Sahipsiz"))
    assert response.status_code == 200
    comm = _row(db, message_id)
    gateway = _gateway(monkeypatch)
    with caplog.at_level("INFO", logger=NOTIFY):
        assert _deliver(db, comm.id) == "skipped"
    assert gateway.messages == []
    assert "reason=no_recipient" in caplog.text
    assert _count(db, message_id) == 1
    db.refresh(comm)
    assert "inbound_email_notification" not in (comm.metadata_json or {})


def test_fallback_used_when_no_owner_or_manager(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _ig_payload(message_id=message_id, text="Yedek"))
    comm = _row(db, message_id)
    fallback = f"desk-{uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("CRM_INBOUND_NOTIFY_EMAIL", fallback)
    get_settings.cache_clear()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert gateway.messages[0].recipient == fallback


def test_smtp_failure_keeps_communication_and_retries(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, text="SMTP"))
    assert response.status_code == 200
    comm = _row(db, message_id)
    fallback = f"retry-{uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("CRM_INBOUND_NOTIFY_EMAIL", fallback)
    get_settings.cache_clear()
    gateway = _gateway(monkeypatch, ok=False)
    lock = MemoryNotifyLock()
    monkeypatch.setattr(
        "investhome_api.services.crm.meta_inbound_notify._notify_lock",
        lambda: lock,
    )
    with pytest.raises(MetaInboundEmailRetry):
        asyncio.run(meta_inbound_email_job({}, str(comm.id)))
    db.refresh(comm)
    assert "inbound_email_notification" not in (comm.metadata_json or {})
    assert _count(db, message_id) == 1
    gateway.ok = True
    result = asyncio.run(meta_inbound_email_job({}, str(comm.id)))
    assert result["status"] == "sent"
    assert len(gateway.messages) == 2
    assert sum(1 for item in gateway.messages if item.recipient == fallback) == 2


def test_duplicate_worker_sends_one_email(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _payload(message_id=message_id, text="Tek posta"))
    comm = _row(db, message_id)
    owner = _user(db, f"once-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    contact.owner_user_id = owner.id
    db.commit()
    gateway = _gateway(monkeypatch)
    lock = MemoryNotifyLock()
    assert _deliver(db, comm.id, lock) == "sent"
    assert _deliver(db, comm.id, lock) == "skipped"
    assert len(gateway.messages) == 1


def test_feature_flag_false_does_not_queue(
    client: TestClient,
    db: Session,
    monkeypatch: pytest.MonkeyPatch,
    _notify_env: _Queue,
) -> None:
    monkeypatch.setenv("CRM_INBOUND_EMAIL_NOTIFICATIONS_ENABLED", "false")
    get_settings.cache_clear()
    message_id = f"mid.{uuid4().hex}"
    response, _ = _post(client, _ig_payload(message_id=message_id, text="Kapali"))
    assert response.status_code == 200
    assert response.json()["ingested"] == 1
    assert _notify_env.ids == []
    assert _count(db, message_id) == 1


def test_enqueue_failure_still_returns_success(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _notify_env.fail = True
    message_id = f"mid.{uuid4().hex}"
    with caplog.at_level("ERROR", logger=NOTIFY):
        response, _ = _post(client, _payload(message_id=message_id, text="Kuyruk"))
    assert response.status_code == 200
    assert response.json()["ingested"] == 1
    assert _count(db, message_id) == 1
    assert "meta_inbound_email_enqueue_failed" in caplog.text


def test_stored_removal_signal_skips_notification(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comment_id = f"igc_{uuid4().hex[:10]}"
    _post(client, _ig_comment_payload(comment_id=comment_id, text="Silinebilir"))
    comm = _row(db, comment_id)
    meta_json = dict(comm.metadata_json or {})
    meta_json["verb"] = "remove"
    comm.metadata_json = meta_json
    db.commit()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "skipped"
    assert gateway.messages == []


def _ig_comm(client: TestClient, db: Session) -> CrmCommunication:
    message_id = f"mid.{uuid4().hex}"
    _post(client, _ig_payload(message_id=message_id, text=f"Satis {message_id}"))
    return _row(db, message_id)


def _assign_owner(db: Session, comm: CrmCommunication, user: User) -> CrmContact:
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    contact.owner_user_id = user.id
    db.commit()
    return contact


def _assign_manager(db: Session, comm: CrmCommunication, user: User) -> None:
    contact = db.get(CrmContact, comm.contact_id)
    assert contact is not None
    lead = db.get(Lead, contact.lead_id)
    assert lead is not None
    lead.assigned_manager_id = user.id
    db.commit()


def test_active_sales_users_each_receive_one_email(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    first = _sales_user(db, f"sales-a-{uuid4().hex[:8]}@example.com")
    second = _sales_user(db, f"sales-b-{uuid4().hex[:8]}@example.com")
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert _sent_to(gateway) == {first.email, second.email}
    assert len(gateway.messages) == 2
    db.refresh(comm)
    notice = comm.metadata_json["inbound_email_notification"]
    assert notice["status"] == "sent"
    assert notice["recipients"][str(first.id)]["source"] == "sales_role"
    assert notice["recipients"][str(second.id)]["source"] == "sales_role"


@pytest.mark.parametrize("status", [UserStatus.INACTIVE, UserStatus.SUSPENDED, UserStatus.INVITED])
def test_non_active_sales_user_is_not_emailed(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
    status: UserStatus,
) -> None:
    comm = _ig_comm(client, db)
    active = _sales_user(db, f"live-{uuid4().hex[:8]}@example.com")
    skipped = _sales_user(db, f"off-{status.value}-{uuid4().hex[:6]}@example.com", status)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert _sent_to(gateway) == {active.email}
    assert skipped.email not in _sent_to(gateway)


def test_user_without_sales_role_is_not_emailed(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    reader = _user(db, f"reader-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    _assign_role(db, reader, "read_only")
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "skipped"
    assert gateway.messages == []
    _assign_owner(db, comm, reader)
    assert _deliver(db, comm.id) == "sent"
    assert _sent_to(gateway) == {reader.email}
    db.refresh(comm)
    recipients = comm.metadata_json["inbound_email_notification"]["recipients"]
    assert recipients[str(reader.id)]["source"] == "contact_owner"


def test_sales_and_read_only_roles_receive_one_email(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    person = _sales_user(db, f"both-roles-{uuid4().hex[:8]}@example.com")
    _assign_role(db, person, "read_only")
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert [item.recipient for item in gateway.messages] == [person.email]
    db.refresh(comm)
    recipients = comm.metadata_json["inbound_email_notification"]["recipients"]
    assert recipients[str(person.id)]["source"] == "sales_role"


def test_non_sales_owner_receives_copy_with_sales_team(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    sales = _sales_user(db, f"sales-{uuid4().hex[:8]}@example.com")
    owner = _user(db, f"owner-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    _assign_role(db, owner, "read_only")
    _assign_owner(db, comm, owner)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert _sent_to(gateway) == {sales.email, owner.email}
    db.refresh(comm)
    recipients = comm.metadata_json["inbound_email_notification"]["recipients"]
    assert recipients[str(sales.id)]["source"] == "sales_role"
    assert recipients[str(owner.id)]["source"] == "contact_owner"


def test_non_sales_lead_manager_receives_copy_with_sales_team(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    sales = _sales_user(db, f"sales-{uuid4().hex[:8]}@example.com")
    manager = _user(db, f"mgr-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    _assign_role(db, manager, "read_only")
    _assign_manager(db, comm, manager)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert _sent_to(gateway) == {sales.email, manager.email}
    db.refresh(comm)
    recipients = comm.metadata_json["inbound_email_notification"]["recipients"]
    assert recipients[str(manager.id)]["source"] == "lead_manager"


def test_sales_owner_receives_one_copy(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    owner = _sales_user(db, f"both-{uuid4().hex[:8]}@example.com")
    _assign_owner(db, comm, owner)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert [item.recipient for item in gateway.messages] == [owner.email]
    db.refresh(comm)
    row = comm.metadata_json["inbound_email_notification"]["recipients"][str(owner.id)]
    assert row["source"] == "sales_role"


def test_sales_lead_manager_receives_one_copy(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    manager = _sales_user(db, f"mgr-sales-{uuid4().hex[:8]}@example.com")
    _assign_manager(db, comm, manager)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert [item.recipient for item in gateway.messages] == [manager.email]


def test_owner_and_manager_same_user_receives_one_copy(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    person = _user(db, f"same-{uuid4().hex[:8]}@example.com", UserStatus.ACTIVE)
    _assign_owner(db, comm, person)
    _assign_manager(db, comm, person)
    gateway = _gateway(monkeypatch)
    assert _deliver(db, comm.id) == "sent"
    assert [item.recipient for item in gateway.messages] == [person.email]
    db.refresh(comm)
    recipients = comm.metadata_json["inbound_email_notification"]["recipients"]
    assert recipients[str(person.id)]["source"] == "contact_owner"


def test_fallback_used_only_when_recipient_set_is_empty(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = _ig_comm(client, db)
    fallback = f"desk-{uuid4().hex[:8]}@example.com"
    monkeypatch.setenv("CRM_INBOUND_NOTIFY_EMAIL", fallback)
    get_settings.cache_clear()
    gateway = _gateway(monkeypatch)
    assert _deliver(db, empty.id) == "sent"
    assert _sent_to(gateway) == {fallback}

    covered = _ig_comm(client, db)
    sales = _sales_user(db, f"covered-{uuid4().hex[:8]}@example.com")
    assert _deliver(db, covered.id) == "sent"
    assert sales.email in _sent_to(gateway)
    assert sum(1 for item in gateway.messages if item.recipient == fallback) == 1


def test_partial_smtp_failure_retries_only_failed_recipient(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    first = _sales_user(db, f"ok-{uuid4().hex[:8]}@example.com")
    second = _sales_user(db, f"retry-{uuid4().hex[:8]}@example.com")
    gateway = _gateway(monkeypatch, fail_emails={second.email})
    with pytest.raises(MetaInboundEmailRetry):
        _deliver(db, comm.id)
    db.refresh(comm)
    notice = comm.metadata_json["inbound_email_notification"]
    assert notice["status"] == "partial"
    assert notice["recipients"][str(first.id)]["status"] == "sent"
    assert str(second.id) not in notice["recipients"]
    gateway.fail_emails.clear()
    assert _deliver(db, comm.id) == "sent"
    assert sum(1 for item in gateway.messages if item.recipient == first.email) == 1
    assert sum(1 for item in gateway.messages if item.recipient == second.email) == 2
    db.refresh(comm)
    done = comm.metadata_json["inbound_email_notification"]
    assert done["status"] == "sent"
    assert done["recipients"][str(second.id)]["status"] == "sent"


def test_duplicate_worker_does_not_resend_sales_recipients(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    comm = _ig_comm(client, db)
    first = _sales_user(db, f"once-a-{uuid4().hex[:8]}@example.com")
    second = _sales_user(db, f"once-b-{uuid4().hex[:8]}@example.com")
    gateway = _gateway(monkeypatch)
    lock = MemoryNotifyLock()
    assert _deliver(db, comm.id, lock) == "sent"
    assert _deliver(db, comm.id, lock) == "skipped"
    assert _sent_to(gateway) == {first.email, second.email}
    assert len(gateway.messages) == 2


def test_duplicate_meta_webhook_does_not_notify_twice(
    client: TestClient,
    db: Session,
    _notify_env: _Queue,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sales = _sales_user(db, f"once-{uuid4().hex[:8]}@example.com")
    message_id = f"mid.{uuid4().hex}"
    payload = _ig_payload(message_id=message_id, text="Tekrar")
    first, _ = _post(client, payload)
    second, _ = _post(client, payload)
    assert first.json()["ingested"] == 1
    assert second.json()["duplicate"] is True
    assert len(_notify_env.ids) == 1
    gateway = _gateway(monkeypatch)
    assert _deliver(db, _row(db, message_id).id) == "sent"
    assert [item.recipient for item in gateway.messages] == [sales.email]

