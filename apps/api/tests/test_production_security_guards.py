"""Production security fail-closed guards (G10)."""

import pytest

from investhome_api.config.settings import Settings, validate_production_security


def test_production_rejects_dev_jwt_secret() -> None:
    settings = Settings(
        API_ENVIRONMENT="production",
        JWT_SECRET="dev-only-change-in-production-use-long-random-string",
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_production_security(settings)


def test_production_rejects_auth_disabled() -> None:
    settings = Settings(
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=False,
    )
    with pytest.raises(RuntimeError, match="API_AUTH_ENABLED"):
        validate_production_security(settings)


def test_development_allows_defaults() -> None:
    settings = Settings(API_ENVIRONMENT="development")
    validate_production_security(settings)  # must not raise
