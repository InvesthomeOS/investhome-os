"""Canva OAuth callback foundation - redirect only, no token exchange."""

from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient

from investhome_api.config.settings import get_settings
from investhome_api.main import app


def _location_parts(response):
    assert response.status_code == 302
    loc = response.headers["location"]
    parsed = urlparse(loc)
    return parsed, parse_qs(parsed.query)


def test_canva_callback_success_redirects_to_platform_integrations(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code", "state": "csrf-state"},
        follow_redirects=False,
    )
    parsed, qs = _location_parts(response)
    assert parsed.scheme == "http"
    assert parsed.netloc == "localhost:3000"
    assert parsed.path == "/dashboard/admin/platform/integrations"
    assert qs.get("canva") == ["connected"]
    assert "canva_error" not in qs
    assert "code" not in qs
    assert "error_description" not in qs
    get_settings.cache_clear()


def test_canva_callback_error_redirects_with_safe_error(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    client = TestClient(app)
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
    get_settings.cache_clear()


def test_canva_callback_missing_state_is_invalid(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"code": "auth-code"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["missing_state"]
    get_settings.cache_clear()


def test_canva_callback_missing_code_is_invalid(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"state": "csrf-state"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["missing_code"]
    get_settings.cache_clear()


def test_canva_callback_strips_unknown_error_payload(monkeypatch):
    monkeypatch.setenv("API_CORS_ORIGINS", '["http://localhost:3000"]')
    get_settings.cache_clear()
    client = TestClient(app)
    response = client.get(
        "/platform/integrations/canva/callback",
        params={"error": "weird<script>alert(1)</script>"},
        follow_redirects=False,
    )
    _, qs = _location_parts(response)
    assert qs.get("canva_error") == ["oauth_error"]
    assert "<script>" not in response.headers["location"]
    get_settings.cache_clear()