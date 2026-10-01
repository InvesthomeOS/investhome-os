"""Security event monitoring — pattern signals without storing secrets or raw IPs."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from investhome_api.services.login_rate_limit import record_failed_login_attempt, record_failed_mfa_verify
from investhome_api.services.security_monitoring import (
    SecurityEventKind,
    SignalType,
    list_active_signals,
    observe_security_event,
    reset_security_monitor_for_tests,
    sanitize_metadata,
)

FORBIDDEN_VALUES = (
    "SuperSecretPassword!",
    "123456",
    "recovery-ABC",
    "sess_live_token",
    "whsec_live_secret",
    "document-bytes-here",
    "raw form body",
    "203.0.113.50",
    "victim@example.com",
)


class _CaptureDispatcher:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def dispatch(self, signal: object) -> None:
        self.calls.append(signal)


def _blob() -> str:
    return json.dumps(list_active_signals(), default=str).lower()


def test_single_failed_login_does_not_create_signal() -> None:
    record_failed_login_attempt(ip="203.0.113.10", identity="one@example.com")
    assert list_active_signals() == []


def test_failed_login_burst_creates_signal() -> None:
    for _ in range(5):
        record_failed_login_attempt(ip="203.0.113.11", identity="burst@example.com")
    types = {row["signal_type"] for row in list_active_signals()}
    assert SignalType.FAILED_LOGIN_IP.value in types
    assert SignalType.FAILED_LOGIN_ACCOUNT.value in types
    for row in list_active_signals():
        assert row["severity"] in {"info", "warning", "high", "critical"}
        assert row["event_count"] >= 5
        assert row["first_seen"] is not None
        assert row["last_seen"] is not None


def test_repeated_events_increment_same_signal() -> None:
    capture = _CaptureDispatcher()
    reset_security_monitor_for_tests(dispatcher=capture)
    for _ in range(5):
        observe_security_event(SecurityEventKind.FAILED_LOGIN, ip="198.51.100.9", identity="same@example.com")
    first = [row for row in list_active_signals() if row["signal_type"] == SignalType.FAILED_LOGIN_IP.value]
    assert len(first) == 1
    created_dispatches = len(capture.calls)
    observe_security_event(SecurityEventKind.FAILED_LOGIN, ip="198.51.100.9", identity="same@example.com")
    again = [row for row in list_active_signals() if row["signal_type"] == SignalType.FAILED_LOGIN_IP.value]
    assert len(again) == 1
    assert again[0]["id"] == first[0]["id"]
    assert again[0]["event_count"] == first[0]["event_count"] + 1
    assert len(capture.calls) == created_dispatches


def test_multi_account_attack_pattern() -> None:
    ip = "198.51.100.20"
    for identity in ("a@example.com", "b@example.com", "c@example.com"):
        observe_security_event(SecurityEventKind.FAILED_LOGIN, ip=ip, identity=identity)
    types = {row["signal_type"] for row in list_active_signals()}
    assert SignalType.FAILED_LOGIN_MULTI_ACCOUNT.value in types
    multi = next(row for row in list_active_signals() if row["signal_type"] == SignalType.FAILED_LOGIN_MULTI_ACCOUNT.value)
    assert multi["severity"] == "high"
    assert multi["event_count"] >= 3


def test_mfa_failure_burst() -> None:
    for _ in range(4):
        record_failed_mfa_verify(ip="198.51.100.30", identity="mfa@example.com")
    assert all(row["signal_type"] != SignalType.MFA_FAILURE_BURST.value for row in list_active_signals())
    record_failed_mfa_verify(ip="198.51.100.30", identity="mfa@example.com")
    types = {row["signal_type"] for row in list_active_signals()}
    assert SignalType.MFA_FAILURE_BURST.value in types


def test_csrf_and_webhook_failures_generate_signals() -> None:
    for _ in range(8):
        observe_security_event(SecurityEventKind.CSRF_REJECTED, ip="198.51.100.40")
    for _ in range(5):
        observe_security_event(SecurityEventKind.WEBHOOK_SIGNATURE_FAILURE, ip="198.51.100.41")
    types = {row["signal_type"] for row in list_active_signals()}
    assert SignalType.CSRF_FAILURE_BURST.value in types
    assert SignalType.WEBHOOK_SIGNATURE_BURST.value in types


def test_sensitive_values_never_stored() -> None:
    observe_security_event(
        SecurityEventKind.FAILED_LOGIN,
        ip="203.0.113.50",
        identity="victim@example.com",
        metadata={
            "password": "SuperSecretPassword!",
            "mfa_code": "123456",
            "recovery_code": "recovery-ABC",
            "session_token": "sess_live_token",
            "webhook_secret": "whsec_live_secret",
            "document_content": "document-bytes-here",
            "raw_body": "raw form body",
            "ip": "203.0.113.50",
            "email": "victim@example.com",
            "reason": "invalid_credentials",
        },
    )
    for _ in range(4):
        observe_security_event(
            SecurityEventKind.FAILED_LOGIN,
            ip="203.0.113.50",
            identity="victim@example.com",
            metadata={"password": "SuperSecretPassword!", "mfa_code": "123456"},
        )
    blob = _blob()
    for value in FORBIDDEN_VALUES:
        assert value.lower() not in blob
    for row in list_active_signals():
        meta = row.get("metadata") or {}
        assert "password" not in meta
        assert "mfa_code" not in meta
        assert "ip" not in meta
        assert "email" not in meta
        assert row.get("correlation_key") != "203.0.113.50"
        assert "victim@example.com" not in json.dumps(row, default=str)


def test_sanitize_metadata_drops_secrets() -> None:
    cleaned = sanitize_metadata(
        {
            "password": "x",
            "otp": "111111",
            "reason": "locked",
            "ip_address": "10.0.0.1",
        }
    )
    assert cleaned == {"reason": "locked"}


def test_security_center_displays_active_signals(auth_client: TestClient) -> None:
    for _ in range(5):
        record_failed_login_attempt(ip="198.51.100.77", identity="center@example.com")
    login = auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    assert login.status_code == 200, login.text
    dashboard = auth_client.get("/security/dashboard")
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["signals"]
    kpi = next((item for item in body["kpis"] if item["key"] == "security_signals"), None)
    assert kpi is not None
    assert kpi["value"] >= 1
    listed = auth_client.get("/security/signals")
    assert listed.status_code == 200, listed.text
    payload = listed.json()
    assert payload["total"] >= 1
    blob = json.dumps(payload).lower()
    assert "198.51.100.77" not in blob
    assert "demo123!" not in blob
    item = payload["items"][0]
    assert item["signal_type"]
    assert item["severity"]
    assert item["event_count"] >= 1
    assert item["first_seen"]
    assert item["last_seen"]


def test_csrf_http_rejections_can_generate_signal(auth_client: TestClient) -> None:
    from investhome_api.models.lead import LeadStatus

    auth_client.auto_csrf = False
    login = auth_client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    assert login.status_code == 200, login.text
    for index in range(8):
        response = auth_client.post(
            "/leads",
            json={
                "full_name": "Monitor Lead",
                "email": f"monitor{index}@example.com",
                "status": LeadStatus.NEW.value,
            },
        )
        assert response.status_code == 403
    types = {row["signal_type"] for row in list_active_signals()}
    assert SignalType.CSRF_FAILURE_BURST.value in types
