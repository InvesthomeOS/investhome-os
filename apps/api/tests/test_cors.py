"""CORS allowlist: trusted origins, methods, and headers only."""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from investhome_api.config.cors import (
    CORS_ALLOWED_HEADERS,
    CORS_ALLOWED_METHODS,
    CORS_EXPOSE_HEADERS,
    production_cors_problems,
    sanitize_cors_origins,
)
from investhome_api.config.settings import Settings, get_settings, validate_production_security
from investhome_api.main import create_app

TRUSTED = "http://localhost:3000"
TRUSTED_LOOPBACK = "http://127.0.0.1:3000"
UNTRUSTED = "https://evil.example"
_JWT = "unit-test-jwt-secret-not-for-production-32"
_TEST_REDIS = "redis://:unit-test-redis-password-not-used@localhost:6379/0"
_COMM_KEY = "unit-test-communication-credential-key-32b"
_PROD_ORIGIN = "https://os.investhome.com"


@pytest.fixture
def cors_app(monkeypatch: pytest.MonkeyPatch):
    def factory(origins: str) -> TestClient:
        monkeypatch.setenv("API_CORS_ORIGINS", origins)
        monkeypatch.setenv("JWT_SECRET", _JWT)
        get_settings.cache_clear()
        return TestClient(create_app())

    yield factory
    get_settings.cache_clear()


def _preflight(
    client: TestClient,
    *,
    origin: str,
    method: str = "POST",
    headers: str = "X-CSRF-Token,Content-Type",
):
    return client.options(
        "/health",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": headers,
        },
    )


def test_sanitize_drops_wildcard_and_null() -> None:
    assert sanitize_cors_origins(["*", "null", "https://*.evil.test", TRUSTED]) == [TRUSTED]
    assert sanitize_cors_origins(["*"]) == []


def test_settings_reject_wildcard_origin() -> None:
    settings = Settings(_env_file=None, JWT_SECRET=_JWT, API_CORS_ORIGINS='["*"]')
    assert "*" not in settings.cors_origins
    assert settings.cors_origins == []


def test_settings_default_local_origins() -> None:
    settings = Settings(_env_file=None, JWT_SECRET=_JWT, API_CORS_ORIGINS=None)
    assert TRUSTED in settings.cors_origins
    assert TRUSTED_LOOPBACK in settings.cors_origins


def _production_settings(**kwargs) -> Settings:
    payload = {
        "_env_file": None,
        "API_ENVIRONMENT": "production",
        "JWT_SECRET": "x" * 40,
        "AUTH_COOKIE_SECURE": True,
        "API_DEBUG": False,
        "API_ENABLE_OPENAPI": False,
        "API_AUTH_ENABLED": True,
        "COMMUNICATION_CREDENTIAL_KEY": _COMM_KEY,
        "REDIS_URL": _TEST_REDIS,
        "API_CORS_ORIGINS": _PROD_ORIGIN,
    }
    payload.update(kwargs)
    return Settings(**payload)


def test_production_missing_cors_fails_closed() -> None:
    settings = _production_settings(API_CORS_ORIGINS=None)
    assert settings.cors_origins == []
    with pytest.raises(RuntimeError, match="API_CORS_ORIGINS is required"):
        validate_production_security(settings)
    assert production_cors_problems([]) == ["API_CORS_ORIGINS is required in production"]


def test_production_wildcard_cors_fails_closed() -> None:
    settings = _production_settings(API_CORS_ORIGINS="*")
    assert settings.cors_origins == []
    with pytest.raises(RuntimeError, match="API_CORS_ORIGINS is required"):
        validate_production_security(settings)


def test_production_malformed_cors_fails_closed() -> None:
    with pytest.raises(ValidationError, match="malformed"):
        _production_settings(API_CORS_ORIGINS="[not-json")
    settings = _production_settings(API_CORS_ORIGINS="not-a-url")
    with pytest.raises(RuntimeError, match="malformed"):
        validate_production_security(settings)


def test_production_localhost_cors_fails_closed() -> None:
    settings = _production_settings(
        API_CORS_ORIGINS='["http://localhost:3000","http://127.0.0.1:3000"]'
    )
    with pytest.raises(RuntimeError, match="localhost-only"):
        validate_production_security(settings)


def test_production_http_only_cors_fails_closed() -> None:
    settings = _production_settings(API_CORS_ORIGINS="http://os.investhome.com")
    with pytest.raises(RuntimeError, match="HTTP-only"):
        validate_production_security(settings)


def test_production_https_cors_accepted() -> None:
    settings = _production_settings()
    validate_production_security(settings)
    assert settings.cors_origins == [_PROD_ORIGIN]


def test_trusted_local_origin_accepted(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}","{TRUSTED_LOOPBACK}"]')
    response = _preflight(client, origin=TRUSTED)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == TRUSTED
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_trusted_loopback_origin_accepted(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}","{TRUSTED_LOOPBACK}"]')
    response = _preflight(client, origin=TRUSTED_LOOPBACK, method="GET")
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == TRUSTED_LOOPBACK


def test_untrusted_origin_rejected(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = _preflight(client, origin=UNTRUSTED)
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_untrusted_origin_has_no_credential_headers(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = client.get("/health", headers={"Origin": UNTRUSTED})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") is None
    assert response.headers.get("access-control-allow-credentials") is None


def test_wildcard_origin_not_accepted(cors_app) -> None:
    client = cors_app('["*"]')
    response = _preflight(client, origin=TRUSTED)
    assert response.status_code == 400
    star = client.get("/health", headers={"Origin": "*"})
    assert star.headers.get("access-control-allow-origin") not in {"*", TRUSTED}


def test_credentials_only_for_trusted_origin(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    trusted = client.get("/health", headers={"Origin": TRUSTED})
    assert trusted.status_code == 200
    assert trusted.headers.get("access-control-allow-origin") == TRUSTED
    assert trusted.headers.get("access-control-allow-credentials") == "true"
    untrusted = client.get("/health", headers={"Origin": UNTRUSTED})
    assert untrusted.headers.get("access-control-allow-origin") is None
    assert untrusted.headers.get("access-control-allow-credentials") is None


def test_allowed_methods_work(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    for method in CORS_ALLOWED_METHODS:
        if method == "OPTIONS":
            continue
        response = _preflight(client, origin=TRUSTED, method=method)
        assert response.status_code == 200, method
        allow = response.headers.get("access-control-allow-methods", "")
        assert method in allow


def test_disallowed_method_rejected(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = _preflight(client, origin=TRUSTED, method="TRACE")
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_csrf_header_allowed(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = _preflight(client, origin=TRUSTED, headers="X-CSRF-Token")
    assert response.status_code == 200
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-csrf-token" in allowed


def test_disallowed_header_rejected(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = _preflight(client, origin=TRUSTED, headers="X-Evil-Header")
    assert response.status_code == 400


def test_exposed_headers_are_request_id_only(cors_app) -> None:
    client = cors_app(f'["{TRUSTED}"]')
    response = client.get("/health", headers={"Origin": TRUSTED})
    expose = response.headers.get("access-control-expose-headers", "")
    assert "x-request-id" in expose.lower()
    for name in CORS_EXPOSE_HEADERS:
        assert name.lower() in expose.lower()
    assert "set-cookie" not in expose.lower()
    assert "authorization" not in expose.lower()


def test_allowed_headers_do_not_include_wildcard() -> None:
    assert "*" not in CORS_ALLOWED_HEADERS
    assert "*" not in CORS_ALLOWED_METHODS
    assert "X-CSRF-Token" in CORS_ALLOWED_HEADERS
    assert "Authorization" in CORS_ALLOWED_HEADERS
    assert "Content-Type" in CORS_ALLOWED_HEADERS
