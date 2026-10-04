"""JWT / production security fail-closed guards."""

import pytest
from pydantic import ValidationError

from investhome_api.config.settings import (
    Settings,
    validate_production_security,
    validate_required_secrets,
)

_PLACEHOLDER_JWT = "dev-only-change-in-production-use-long-random-string"
_TEST_JWT = "unit-test-jwt-secret-not-for-production-32"
_TEST_REDIS = "redis://:unit-test-redis-password-not-used@localhost:6379/0"
_UNAUTH_REDIS = "redis://localhost:6379/0"
_PROD_CORS = "https://os.investhome.com"
_COMM_KEY = "unit-test-communication-credential-key-32b"


def test_placeholder_jwt_secret_rejected_in_all_environments() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, API_ENVIRONMENT="development", JWT_SECRET=_PLACEHOLDER_JWT)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            _env_file=None,
            API_ENVIRONMENT="production",
            JWT_SECRET=_PLACEHOLDER_JWT,
            AUTH_COOKIE_SECURE=True,
            API_DEBUG=False,
            API_ENABLE_OPENAPI=False,
            API_AUTH_ENABLED=True,
        )


def test_missing_jwt_secret_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None)


def test_short_jwt_secret_fails_closed() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(_env_file=None, JWT_SECRET="too-short")


def test_production_rejects_auth_disabled() -> None:
    settings = Settings(
        _env_file=None,
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=False,
        COMMUNICATION_CREDENTIAL_KEY="unit-test-communication-credential-key-32b",
    )
    with pytest.raises(RuntimeError, match="API_AUTH_ENABLED"):
        validate_production_security(settings)


def test_development_accepts_unique_jwt_secret() -> None:
    settings = Settings(_env_file=None, API_ENVIRONMENT="development", JWT_SECRET=_TEST_JWT)
    validate_required_secrets(settings)
    validate_production_security(settings)  # production-only cookie/debug checks skipped


def test_missing_redis_url_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(_env_file=None, JWT_SECRET=_TEST_JWT)


def test_empty_redis_url_fails_closed() -> None:
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(_env_file=None, JWT_SECRET=_TEST_JWT, REDIS_URL="   ")


def test_production_missing_redis_url_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(
            _env_file=None,
            API_ENVIRONMENT="production",
            JWT_SECRET="x" * 40,
            AUTH_COOKIE_SECURE=True,
            API_DEBUG=False,
            API_ENABLE_OPENAPI=False,
            API_AUTH_ENABLED=True,
            COMMUNICATION_CREDENTIAL_KEY=_COMM_KEY,
            API_CORS_ORIGINS=_PROD_CORS,
        )


def test_production_unauthenticated_redis_url_fails_closed() -> None:
    settings = Settings(
        _env_file=None,
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
        COMMUNICATION_CREDENTIAL_KEY=_COMM_KEY,
        REDIS_URL=_UNAUTH_REDIS,
        API_CORS_ORIGINS=_PROD_CORS,
    )
    with pytest.raises(RuntimeError, match="REDIS_URL must include a password"):
        validate_production_security(settings)


def test_production_authenticated_redis_url_accepted() -> None:
    settings = Settings(
        _env_file=None,
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
        COMMUNICATION_CREDENTIAL_KEY=_COMM_KEY,
        REDIS_URL=_TEST_REDIS,
        API_CORS_ORIGINS=_PROD_CORS,
    )
    validate_production_security(settings)


def test_development_explicit_redis_url_does_not_use_unauthenticated_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("REDIS_URL", raising=False)
    with pytest.raises(ValidationError, match="REDIS_URL"):
        Settings(_env_file=None, API_ENVIRONMENT="development", JWT_SECRET=_TEST_JWT)
