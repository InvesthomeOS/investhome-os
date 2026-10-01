"""Gmail OAuth redirect URI allowlist — fail closed, no open redirects."""

from __future__ import annotations

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.services.crm import gmail_oauth

LOCAL_127 = "http://127.0.0.1:8000/crm/settings/communication-accounts/gmail/callback"
LOCAL_LOCALHOST = "http://localhost:8000/crm/settings/communication-accounts/gmail/callback"
PROD_HTTPS = "https://api.investhome.example/crm/settings/communication-accounts/gmail/callback"


@pytest.fixture(autouse=True)
def _gmail_redirect_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_ID", "drive-client-id")
    monkeypatch.setenv("GOOGLE_DRIVE_CLIENT_SECRET", "drive-client-secret")
    monkeypatch.delenv("GMAIL_OAUTH_REDIRECT_URI", raising=False)
    get_settings.cache_clear()
    gmail_oauth.clear_memory_states()
    monkeypatch.setattr(
        gmail_oauth,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )
    yield
    gmail_oauth.clear_memory_states()
    get_settings.cache_clear()


def _set_redirect(monkeypatch: pytest.MonkeyPatch, uri: str | None) -> None:
    if uri is None:
        monkeypatch.delenv("GMAIL_OAUTH_REDIRECT_URI", raising=False)
    else:
        monkeypatch.setenv("GMAIL_OAUTH_REDIRECT_URI", uri)
    get_settings.cache_clear()


def test_valid_local_callback_accepted_in_development() -> None:
    assert gmail_oauth.gmail_redirect_uri() == LOCAL_127
    assert gmail_oauth.is_allowed_gmail_redirect_uri(LOCAL_127)
    assert gmail_oauth.is_allowed_gmail_redirect_uri(LOCAL_LOCALHOST)


def test_valid_local_localhost_override_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_redirect(monkeypatch, LOCAL_LOCALHOST)
    assert gmail_oauth.gmail_redirect_uri() == LOCAL_LOCALHOST
    url = gmail_oauth.start_authorization(user_id="user-1")
    qs = parse_qs(urlparse(url).query)
    assert qs["redirect_uri"] == [LOCAL_LOCALHOST]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"][0]
    assert qs["code_challenge"][0]


def test_arbitrary_external_callback_rejected(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    evil = "https://evil.example/crm/settings/communication-accounts/gmail/callback"
    _set_redirect(monkeypatch, evil)
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(evil)
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.gmail_redirect_uri()
    gmail_oauth.clear_memory_states()
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.start_authorization(user_id="user-1")
    assert gmail_oauth._memory_states == {}
    http_factory = MagicMock()
    monkeypatch.setattr(gmail_oauth, "_http", http_factory)
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.exchange_authorization_code(code="auth-code", code_verifier="verifier")
    http_factory.assert_not_called()
    response = client.post("/crm/settings/communication-accounts/gmail/authorize")
    assert response.status_code == 503
    assert response.json()["detail"] == "gmail_redirect_uri_not_allowed"
    assert "drive-client-secret" not in response.text


def test_http_production_callback_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gmail_oauth, "_is_production_environment", lambda: True)
    _set_redirect(monkeypatch, LOCAL_127)
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(LOCAL_127)
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.gmail_redirect_uri()
    _set_redirect(monkeypatch, "http://api.investhome.example/crm/settings/communication-accounts/gmail/callback")
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.gmail_redirect_uri()


def test_valid_allowlisted_https_production_callback_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gmail_oauth, "_is_production_environment", lambda: True)
    _set_redirect(monkeypatch, PROD_HTTPS)
    assert gmail_oauth.gmail_redirect_uri() == PROD_HTTPS
    assert gmail_oauth.is_allowed_gmail_redirect_uri(PROD_HTTPS)
    url = gmail_oauth.start_authorization(user_id="user-1")
    qs = parse_qs(urlparse(url).query)
    assert qs["redirect_uri"] == [PROD_HTTPS]
    assert qs["code_challenge_method"] == ["S256"]
    assert "code_verifier" not in qs


def test_wildcard_and_subdomain_bypass_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gmail_oauth, "_is_production_environment", lambda: True)
    _set_redirect(monkeypatch, "https://*.investhome.example/crm/settings/communication-accounts/gmail/callback")
    with pytest.raises(ValueError, match="gmail_redirect_uri_not_allowed"):
        gmail_oauth.gmail_redirect_uri()

    _set_redirect(monkeypatch, PROD_HTTPS)
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(
        "https://evil.api.investhome.example/crm/settings/communication-accounts/gmail/callback"
    )
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(
        "https://api.investhome.example.attacker.com/crm/settings/communication-accounts/gmail/callback"
    )
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(
        "https://evil@api.investhome.example/crm/settings/communication-accounts/gmail/callback"
    )


def test_path_tampering_rejected(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(gmail_oauth, "_is_production_environment", lambda: True)
    _set_redirect(monkeypatch, PROD_HTTPS)
    assert gmail_oauth.is_allowed_gmail_redirect_uri(PROD_HTTPS)
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(PROD_HTTPS + "/extra")
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(PROD_HTTPS + "/")
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(PROD_HTTPS + "?next=https://evil.example")
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(
        "https://api.investhome.example/crm/settings/communication-accounts/gmail/callback/../oauth"
    )
    assert not gmail_oauth.is_allowed_gmail_redirect_uri(
        "https://api.investhome.example/other/callback"
    )

    monkeypatch.setattr(gmail_oauth, "_is_production_environment", lambda: False)
    _set_redirect(monkeypatch, LOCAL_127)
    start = client.post("/crm/settings/communication-accounts/gmail/authorize")
    assert start.status_code == 200, start.text
    state = parse_qs(urlparse(start.json()["authorize_url"]).query)["state"][0]
    _set_redirect(monkeypatch, LOCAL_127 + "/tampered")
    exchange = MagicMock()
    monkeypatch.setattr(gmail_oauth, "exchange_authorization_code", exchange)
    response = client.get(
        "/crm/settings/communication-accounts/gmail/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "invalid_callback" in response.headers["location"]
    exchange.assert_not_called()


def test_existing_authorize_keeps_state_and_pkce(client: TestClient) -> None:
    response = client.post("/crm/settings/communication-accounts/gmail/authorize")
    assert response.status_code == 200, response.text
    body = response.json()
    qs = parse_qs(urlparse(body["authorize_url"]).query)
    assert body["redirect_uri"] == LOCAL_127
    assert qs["redirect_uri"] == [LOCAL_127]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["state"][0]
    assert qs["code_challenge"][0]
    assert "code_verifier" not in body
    assert "drive-client-secret" not in response.text
