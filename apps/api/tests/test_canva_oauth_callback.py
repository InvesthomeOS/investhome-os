"""Canva OAuth 2.0 + PKCE — authorize, callback token exchange, disconnect."""

from __future__ import annotations

from unittest.mock import MagicMock
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.models.platform_core import (  # noqa: F401 — register tables for create_all
    PlatformIntegration,
)
from investhome_api.services import canva_oauth_service as canva


def _location_parts(response):
    assert response.status_code == 302
    loc = response.headers["location"]
    parsed = urlparse(loc)
    return parsed, parse_qs(parsed.query)


@pytest.fixture(autouse=True)
def _clear_canva_state(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    monkeypatch.setenv("CANVA_CLIENT_ID", "test-canva-client-id")
    monkeypatch.setenv("CANVA_CLIENT_SECRET", "test-canva-client-secret")
    get_settings.cache_clear()
    canva.clear_memory_states()
    yield
    canva.clear_memory_states()
    get_settings.cache_clear()


def test_canva_authorize_returns_pkce_url(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        canva,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )
    response = client.post("/platform/integrations/canva/authorize")
    assert response.status_code == 200
    body = response.json()
    assert body["redirect_uri"] == canva.CANVA_REDIRECT_URI
    assert body["redirect_uri"] == "http://127.0.0.1:8000/platform/integrations/canva/callback"
    parsed = urlparse(body["authorize_url"])
    assert parsed.netloc == "www.canva.com"
    assert parsed.path == "/api/oauth/authorize"
    qs = parse_qs(parsed.query)
    assert qs["response_type"] == ["code"]
    assert qs["code_challenge_method"] == ["S256"]
    assert qs["client_id"] == ["test-canva-client-id"]
    assert qs["redirect_uri"] == [canva.CANVA_REDIRECT_URI]
    scopes = qs["scope"][0].split()
    assert scopes == list(canva.CANVA_SCOPES)
    assert "code_challenge" in qs
    assert "state" in qs
    assert "client_secret" not in body["authorize_url"].lower()


def test_canva_authorize_requires_credentials(client: TestClient, monkeypatch):
    monkeypatch.delenv("CANVA_CLIENT_ID", raising=False)
    monkeypatch.delenv("CANVA_CLIENT_SECRET", raising=False)
    get_settings.cache_clear()
    response = client.post("/platform/integrations/canva/authorize")
    assert response.status_code == 503


def test_canva_callback_exchanges_code_and_stores_tokens(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        canva,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )

    def fake_exchange(*, code: str, code_verifier: str):
        assert code == "auth-code"
        assert code_verifier
        return {
            "access_token": "access-xyz",
            "refresh_token": "refresh-xyz",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(canva.CANVA_SCOPES),
        }

    monkeypatch.setattr(canva, "exchange_authorization_code", fake_exchange)

    state = "csrf-state-valid"
    canva.save_oauth_state(state=state, code_verifier="verifier-abc", user_id="user-1")

    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    parsed, qs = _location_parts(response)
    assert parsed.path == "/dashboard/admin/platform/integrations"
    assert qs.get("canva") == ["connected"]
    assert "canva_error" not in qs
    assert "code" not in qs
    assert "access_token" not in response.headers["location"].lower()

    # State is one-time
    assert canva.pop_oauth_state(state) is None

    integrations = client.get("/platform/integrations").json()["items"]
    canva_row = next(i for i in integrations if i["code"] == "canva")
    assert canva_row["status"] == "connected"
    assert canva_row["configured"] is True
    assert canva_row["connectable"] is True
    assert "access_token" not in str(canva_row).lower()
    assert "refresh_token" not in str(canva_row).lower()


def test_canva_callback_invalid_state(client: TestClient):
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code", "state": "unknown-state"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["invalid_state"]


def test_canva_callback_error_redirects_with_safe_error(client: TestClient):
    response = client.get(
        "/platform/integrations/canva/callback",
        params={
            "error": "access_denied",
            "error_description": "User denied access - secret=should-not-leak",
        },
        follow_redirects=False,
    )
    parsed, qs = _location_parts(response)
    assert parsed.path == "/dashboard/admin/platform/integrations"
    assert qs.get("canva_error") == ["access_denied"]
    assert "secret" not in response.headers["location"].lower()
    assert "error_description" not in qs


def test_canva_callback_missing_state_is_invalid(client: TestClient):
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["missing_state"]


def test_canva_callback_missing_code_is_invalid(client: TestClient):
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"state": "csrf-state"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["missing_code"]


def test_canva_callback_strips_unknown_error_payload(client: TestClient):
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"error": "weird<script>alert(1)</script>"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["oauth_error"]
    assert "<script>" not in response.headers["location"]


def test_canva_callback_token_exchange_failure(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        canva,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )

    def boom(*, code: str, code_verifier: str):
        raise ValueError("token_exchange_failed")

    monkeypatch.setattr(canva, "exchange_authorization_code", boom)
    state = "state-fail"
    canva.save_oauth_state(state=state, code_verifier="verifier-fail")
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["token_exchange_failed"]


def test_canva_disconnect(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        canva,
        "_redis_client",
        MagicMock(side_effect=RuntimeError("no redis in test")),
    )

    monkeypatch.setattr(
        canva,
        "exchange_authorization_code",
        lambda **kwargs: {
            "access_token": "access-xyz",
            "refresh_token": "refresh-xyz",
            "token_type": "Bearer",
            "expires_in": 60,
        },
    )
    state = "state-disconnect"
    canva.save_oauth_state(state=state, code_verifier="verifier")
    client.get(
        "/platform/integrations/canva/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )

    response = client.post("/platform/integrations/canva/disconnect")
    assert response.status_code == 200
    assert response.json()["status"] == "not_connected"

    integrations = client.get("/platform/integrations").json()["items"]
    canva_row = next(i for i in integrations if i["code"] == "canva")
    assert canva_row["status"] == "not_connected"
    assert canva_row["configured"] is False
    assert canva_row["connectable"] is True


def test_list_integrations_includes_connectable_canva(client: TestClient):
    response = client.get("/platform/integrations")
    assert response.status_code == 200
    items = response.json()["items"]
    canva_row = next(i for i in items if i["code"] == "canva")
    assert canva_row["connectable"] is True
    assert canva_row["status"] == "not_connected"
    assert canva_row["configured"] is False
    assert {i["code"] for i in items if i["connectable"]} == {"canva"}


def test_pkce_challenge_is_s256():
    verifier = "a" * 64
    challenge = canva.generate_code_challenge(verifier)
    assert len(challenge) >= 43
    assert "=" not in challenge


def test_redirect_uri_constant_exact_match():
    assert canva.CANVA_REDIRECT_URI == "http://127.0.0.1:8000/platform/integrations/canva/callback"
