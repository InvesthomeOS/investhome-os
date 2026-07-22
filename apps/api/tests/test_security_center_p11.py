"""P11 Security Center — permission denial and session basics."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_security_dashboard_requires_auth(client: TestClient) -> None:
    res = client.get("/security/dashboard")
    assert res.status_code in {401, 403}


def test_security_api_keys_require_auth(client: TestClient) -> None:
    res = client.get("/security/api-keys")
    assert res.status_code in {401, 403}


def test_security_dashboard_superadmin(auth_client: TestClient) -> None:
    res = auth_client.get("/security/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert "kpis" in body
    backup = next((k for k in body["kpis"] if k["key"] == "backup_health"), None)
    assert backup is not None
    assert backup["available"] is False
    assert backup["value"] is None


def test_sso_providers_honest_missing(auth_client: TestClient) -> None:
    res = auth_client.get("/security/sso")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 5
    assert all(item["status"] in {"missing", "configured", "invalid", "disabled"} for item in items)
    # Without env credentials, expect missing (not fake healthy)
    assert any(item["status"] == "missing" for item in items)


def test_secrets_never_expose_values(auth_client: TestClient) -> None:
    res = auth_client.get("/security/secrets")
    assert res.status_code == 200
    blob = str(res.json()).lower()
    assert "sk-" not in blob
    assert "password=" not in blob
    for item in res.json()["items"]:
        assert "value" not in item
        assert "secret" not in item or item.get("secret") in (None, "")


def test_backup_unavailable_when_unconfigured(auth_client: TestClient) -> None:
    res = auth_client.get("/security/backup")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] in {"not_configured", "configured", "invalid"}
    if body["provider"] in {"none", "disabled", ""}:
        assert body["health"] == "unavailable"
        assert body["last_backup_at"] is None


def test_sessions_list_after_login(auth_client: TestClient) -> None:
    res = auth_client.get("/security/sessions")
    assert res.status_code == 200
    assert "items" in res.json()


def test_mfa_methods_not_fake_connected(auth_client: TestClient) -> None:
    res = auth_client.get("/security/mfa")
    assert res.status_code == 200
    body = res.json()
    assert body["recovery_codes_available"] is False
    for method in body["methods"]:
        assert method["status"] in {"not_connected", "missing", "configured", "invalid", "disabled"}
