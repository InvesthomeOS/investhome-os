"""User invitation email delivery: generic SMTP, honest status, no secret leakage."""

from __future__ import annotations

import logging
import smtplib
from email.header import decode_header, make_header
from email.message import Message
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.config.settings import get_settings
from investhome_api.models.activity import ActivityLog
from investhome_api.models.user_invitation import UserInvitation
from investhome_api.services.invitation_email import build_invite_email
from investhome_api.services.notification_gateway import reset_notification_gateway_for_tests
from investhome_api.services.smtp_email import smtp_is_configured
from investhome_api.services.user_invitation import hash_invite_token, invite_url_for_token
from test_user_invitations import _invite_user, _login, _read_only_role_id, _set_invite_token

SMTP_PASSWORD = "smtp-test-password-never-log-this"
SMTP_FROM = "noreply@mail.test"
PUBLIC_URL = "https://app.example.test"


class FakeSMTP:
    instances: list["FakeSMTP"] = []
    sent: list[Message] = []
    login_usernames: list[str] = []
    fail_send = False

    def __init__(self, host, port, timeout=None):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.started_tls = False
        FakeSMTP.instances.append(self)

    def starttls(self, *args, **kwargs):
        self.started_tls = True

    def login(self, username, password):
        FakeSMTP.login_usernames.append(username)
        if password != SMTP_PASSWORD:
            raise smtplib.SMTPAuthenticationError(535, b"auth failed")

    def send_message(self, msg):
        if FakeSMTP.fail_send:
            raise smtplib.SMTPException("relay unavailable")
        FakeSMTP.sent.append(msg)
        return {}

    def quit(self):
        return None

    def close(self):
        return None


def _reset_fake_smtp() -> None:
    FakeSMTP.instances = []
    FakeSMTP.sent = []
    FakeSMTP.login_usernames = []
    FakeSMTP.fail_send = False


def _configure_smtp(monkeypatch, *, host: str = "smtp.example.test", from_email: str = SMTP_FROM) -> None:
    monkeypatch.setenv("SMTP_HOST", host)
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", SMTP_PASSWORD)
    monkeypatch.setenv("SMTP_USE_TLS", "true")
    monkeypatch.setenv("SMTP_FROM_EMAIL", from_email)
    monkeypatch.setenv("SMTP_FROM_NAME", "InvestHome OS")
    monkeypatch.setenv("APP_PUBLIC_URL", PUBLIC_URL)
    get_settings.cache_clear()
    reset_notification_gateway_for_tests()


def _patch_smtp(monkeypatch) -> None:
    _reset_fake_smtp()
    monkeypatch.setattr("investhome_api.services.smtp_email.smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("investhome_api.services.smtp_email.smtplib.SMTP_SSL", FakeSMTP)


def _decoded_subject(msg: Message) -> str:
    raw = msg["Subject"]
    if not raw:
        return ""
    return str(make_header(decode_header(raw)))


def _message_blob(msg: Message) -> str:
    parts = [_decoded_subject(msg), str(msg.get("To") or ""), str(msg.get("From") or "")]
    for part in msg.walk():
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        charset = part.get_content_charset() or "utf-8"
        parts.append(payload.decode(charset, errors="replace"))
    return "\n".join(parts)


def test_smtp_unconfigured_is_not_connected() -> None:
    assert smtp_is_configured() is False


def test_invite_url_uses_app_public_url(monkeypatch) -> None:
    monkeypatch.setenv("APP_PUBLIC_URL", f"{PUBLIC_URL}/")
    get_settings.cache_clear()
    token = "invite-url-token-aaaa"
    assert invite_url_for_token(token) == f"{PUBLIC_URL}/invite/{token}"


def test_invite_email_copy_includes_name_ttl_and_one_time_use() -> None:
    content = build_invite_email(
        full_name="Ayşe Yılmaz",
        invite_url=f"{PUBLIC_URL}/invite/sample-token-value",
        ttl_hours=72,
        locale="tr",
        from_name="InvestHome OS",
    )
    assert content.subject == "InvestHome OS daveti"
    assert "Ayşe Yılmaz" in content.text_body
    assert f"{PUBLIC_URL}/invite/sample-token-value" in content.text_body
    assert "72 saat" in content.text_body
    assert "bir kez" in content.text_body
    assert "Ayşe Yılmaz" in content.html_body
    assert "tek kullanımlık" in content.html_body


def test_provider_missing_returns_not_connected(auth_client: TestClient, monkeypatch) -> None:
    email = f"invite.smtp.off.{uuid4().hex[:8]}@example.com"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=f"invite-smtp-off-{uuid4().hex}",
    )
    assert user["status"] == "invited"
    created = auth_client.get(f"/users/{user['id']}")
    assert created.status_code == 200
    assert token not in created.text
    assert SMTP_PASSWORD not in created.text


def test_unconfigured_create_delivery_status_not_connected(
    auth_client: TestClient, monkeypatch
) -> None:
    email = f"invite.smtp.nc.{uuid4().hex[:8]}@example.com"
    _set_invite_token(monkeypatch, f"invite-smtp-nc-{uuid4().hex}")
    assert _login(auth_client).status_code == 200
    created = auth_client.post(
        "/users",
        json={
            "full_name": "No SMTP",
            "email": email,
            "department": "Sales",
            "role_ids": [_read_only_role_id(auth_client)],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["delivery_status"] == "not_connected"
    assert created.json()["delivery_status"] != "sent"


def test_successful_smtp_returns_sent(
    auth_client: TestClient, monkeypatch, caplog
) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    caplog.set_level(logging.DEBUG)
    email = f"invite.smtp.ok.{uuid4().hex[:8]}@example.com"
    token = f"invite-smtp-ok-{uuid4().hex}"
    full_name = "Ada Lovelace"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=token,
        full_name=full_name,
    )
    assert FakeSMTP.sent, "SMTP send_message was not called"
    msg = FakeSMTP.sent[-1]
    blob = _message_blob(msg)
    assert msg["To"] == email
    assert "InvestHome OS daveti" in _decoded_subject(msg)
    assert full_name in blob
    assert f"{PUBLIC_URL}/invite/{token}" in blob
    assert "72" in blob
    assert SMTP_PASSWORD not in blob
    for rec in caplog.records:
        if rec.name.startswith("investhome"):
            line = rec.getMessage()
            assert SMTP_PASSWORD not in line
            assert token not in line


def test_create_with_smtp_reports_sent(auth_client: TestClient, monkeypatch) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    email = f"invite.smtp.sent.{uuid4().hex[:8]}@example.com"
    token = f"invite-smtp-sent-{uuid4().hex}"
    _set_invite_token(monkeypatch, token)
    assert _login(auth_client).status_code == 200
    created = auth_client.post(
        "/users",
        json={
            "full_name": "Sent User",
            "email": email,
            "department": "Sales",
            "role_ids": [_read_only_role_id(auth_client)],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["delivery_status"] == "sent"
    assert token not in created.text
    assert SMTP_PASSWORD not in created.text
    assert "hashed_password" not in created.text


def test_smtp_error_returns_failed(auth_client: TestClient, monkeypatch, caplog) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    FakeSMTP.fail_send = True
    caplog.set_level(logging.DEBUG)
    email = f"invite.smtp.fail.{uuid4().hex[:8]}@example.com"
    token = f"invite-smtp-fail-{uuid4().hex}"
    _set_invite_token(monkeypatch, token)
    assert _login(auth_client).status_code == 200
    created = auth_client.post(
        "/users",
        json={
            "full_name": "Fail User",
            "email": email,
            "department": "Sales",
            "role_ids": [_read_only_role_id(auth_client)],
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["delivery_status"] == "failed"
    assert created.json()["delivery_status"] != "sent"
    assert FakeSMTP.sent == []
    assert token not in created.text
    assert SMTP_PASSWORD not in caplog.text
    assert token not in caplog.text
    assert "smtp_send_failed error_type=SMTPException" in caplog.text


def test_raw_token_not_stored_in_db(
    auth_client: TestClient, monkeypatch, db: Session
) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    email = f"invite.smtp.db.{uuid4().hex[:8]}@example.com"
    token = f"invite-smtp-db-{uuid4().hex}"
    user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=token,
    )
    rows = db.scalars(select(UserInvitation)).all()
    matching = [row for row in rows if row.token_hash == hash_invite_token(token)]
    assert matching
    for row in rows:
        assert token != row.token_hash
        blob = " ".join(str(getattr(row, col.key)) for col in row.__table__.columns)
        assert token not in blob


def test_raw_token_and_email_body_not_in_audit(
    auth_client: TestClient, monkeypatch, db: Session
) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    email = f"invite.smtp.audit.{uuid4().hex[:8]}@example.com"
    token = f"invite-smtp-audit-{uuid4().hex}"
    full_name = "Audit Person"
    _user, token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=token,
        full_name=full_name,
    )
    db.expire_all()
    logs = db.scalars(select(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(40)).all()
    for log in logs:
        blob = str(log.metadata_json or "")
        assert token not in blob
        assert SMTP_PASSWORD not in blob
        assert f"{PUBLIC_URL}/invite/" not in blob
        assert "Merhaba" not in blob
        assert full_name not in blob
        assert "Daveti kabul et" not in blob


def test_resend_invalidates_previous_and_sends_new_link(
    auth_client: TestClient, monkeypatch
) -> None:
    _configure_smtp(monkeypatch)
    _patch_smtp(monkeypatch)
    email = f"invite.smtp.resend.{uuid4().hex[:8]}@example.com"
    first_token = f"invite-smtp-first-{uuid4().hex}"
    user, _token = _invite_user(
        auth_client,
        monkeypatch,
        email=email,
        role_ids=[_read_only_role_id(auth_client)],
        token=first_token,
        full_name="Resend Person",
    )
    assert FakeSMTP.sent
    first_blob = _message_blob(FakeSMTP.sent[-1])
    assert f"{PUBLIC_URL}/invite/{first_token}" in first_blob
    second_token = f"invite-smtp-second-{uuid4().hex}"
    _set_invite_token(monkeypatch, second_token)
    assert _login(auth_client).status_code == 200
    resent = auth_client.post(f"/users/{user['id']}/invite/resend")
    assert resent.status_code == 200, resent.text
    assert resent.json()["delivery_status"] == "sent"
    assert first_token not in resent.text
    assert second_token not in resent.text
    assert auth_client.get(f"/auth/invite/{first_token}").status_code == 404
    assert auth_client.get(f"/auth/invite/{second_token}").status_code == 200
    latest = _message_blob(FakeSMTP.sent[-1])
    assert f"{PUBLIC_URL}/invite/{second_token}" in latest
    assert f"{PUBLIC_URL}/invite/{first_token}" not in latest
    assert email in (FakeSMTP.sent[-1]["To"] or "")
