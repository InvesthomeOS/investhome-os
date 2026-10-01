"""API_AUTH_ENABLED=false is local loopback development only."""

import pytest

from investhome_api.config.settings import Settings, validate_auth_bypass

_TEST_JWT = "unit-test-jwt-secret-not-for-production-32"


def _settings(**kwargs) -> Settings:
    return Settings(_env_file=None, JWT_SECRET=_TEST_JWT, **kwargs)


def test_production_auth_disabled_rejected() -> None:
    settings = _settings(
        API_ENVIRONMENT="production",
        API_HOST="127.0.0.1",
        API_AUTH_ENABLED=False,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
    )
    with pytest.raises(RuntimeError, match="production"):
        validate_auth_bypass(settings)


def test_staging_auth_disabled_rejected() -> None:
    settings = _settings(
        API_ENVIRONMENT="staging",
        API_HOST="127.0.0.1",
        API_AUTH_ENABLED=False,
    )
    with pytest.raises(RuntimeError, match="staging"):
        validate_auth_bypass(settings)


def test_network_bind_auth_disabled_rejected() -> None:
    settings = _settings(
        API_ENVIRONMENT="development",
        API_HOST="0.0.0.0",
        API_AUTH_ENABLED=False,
    )
    with pytest.raises(RuntimeError, match="loopback"):
        validate_auth_bypass(settings)


def test_explicit_localhost_development_bypass_allowed() -> None:
    settings = _settings(
        API_ENVIRONMENT="development",
        API_HOST="127.0.0.1",
        API_AUTH_ENABLED=False,
    )
    validate_auth_bypass(settings)


def test_missing_auth_flag_does_not_disable_auth(monkeypatch) -> None:
    monkeypatch.delenv("API_AUTH_ENABLED", raising=False)
    settings = _settings(API_ENVIRONMENT="development", API_HOST="0.0.0.0")
    assert settings.auth_enabled is True
    validate_auth_bypass(settings)


def test_authenticated_mode_unchanged_on_network_bind() -> None:
    settings = _settings(
        API_ENVIRONMENT="production",
        API_HOST="0.0.0.0",
        API_AUTH_ENABLED=True,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
    )
    validate_auth_bypass(settings)


def test_networked_bypass_does_not_create_fake_superadmin(client, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    settings = _settings(
        API_ENVIRONMENT="development",
        API_HOST="0.0.0.0",
        API_AUTH_ENABLED=False,
    )
    monkeypatch.setattr("investhome_api.api.deps.auth.get_settings", lambda: settings)
    assert isinstance(client, TestClient)
    response = client.get("/leads")
    assert response.status_code == 503
    assert response.json()["detail"] == "Insecure authentication configuration"
