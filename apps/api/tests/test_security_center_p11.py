"""P11 Security Center — permission denial and session basics."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _login_admin(client: TestClient) -> None:
    res = client.post("/auth/login", json={"email": "admin@example.com", "password": "Demo123!"})
    assert res.status_code == 200, res.text


def test_security_dashboard_requires_auth(client: TestClient) -> None:
    res = client.get("/security/dashboard")
    assert res.status_code in {401, 403}


def test_security_api_keys_require_auth(client: TestClient) -> None:
    res = client.get("/security/api-keys")
    assert res.status_code in {401, 403}


def test_security_dashboard_superadmin(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "kpis" in body
    backup = next((k for k in body["kpis"] if k["key"] == "backup_health"), None)
    assert backup is not None
    assert backup["available"] is True
    assert backup["value"] == "not_configured"


def test_sso_providers_honest_missing(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/sso")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 5
    assert all(item["status"] in {"missing", "configured", "invalid", "disabled"} for item in items)
    # Without env credentials, expect missing (not fake healthy)
    assert any(item["status"] == "missing" for item in items)


def test_secrets_never_expose_values(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/secrets")
    assert res.status_code == 200
    blob = str(res.json()).lower()
    assert "sk-" not in blob
    assert "password=" not in blob
    for item in res.json()["items"]:
        assert "value" not in item
        assert "secret" not in item or item.get("secret") in (None, "")


def test_backup_unavailable_when_unconfigured(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/backup")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "not_configured"
    assert body["health"] == "unavailable"
    assert body["last_backup_at"] is None
    assert body["restore_verified"] is False
    assert body["warning"] is True


def test_sessions_list_after_login(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/sessions")
    assert res.status_code == 200
    assert "items" in res.json()


def test_mfa_methods_not_fake_connected(auth_client: TestClient) -> None:
    _login_admin(auth_client)
    res = auth_client.get("/security/mfa")
    assert res.status_code == 200
    body = res.json()
    assert body["recovery_codes_available"] is False
    for method in body["methods"]:
        assert method["status"] in {"not_connected", "missing", "configured", "invalid", "disabled"}


def test_email_mfa_stays_not_connected_when_smtp_username_is_set(
    auth_client: TestClient, monkeypatch
) -> None:
    monkeypatch.setenv("SMTP_HOST", "smtp.example.test")
    monkeypatch.setenv("SMTP_USERNAME", "smtp-user")
    monkeypatch.setenv("SMTP_PASSWORD", "smtp-test-password-never-log-this")
    _login_admin(auth_client)
    res = auth_client.get("/security/mfa")
    assert res.status_code == 200
    email = next(item for item in res.json()["methods"] if item["provider_id"] == "email")
    assert email["status"] == "not_connected"
    assert email["configured"] is False
    assert "not wired" in (email.get("message") or "").lower()
    blob = str(res.json())
    assert "smtp-test-password-never-log-this" not in blob
