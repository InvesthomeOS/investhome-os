"""AES-256-GCM credential sealing — round-trip, tamper, legacy rewrap."""

from __future__ import annotations

import logging

import pytest

from investhome_api.config.settings import Settings, get_settings, validate_production_security
from investhome_api.services.crypto_seal import (
    CURRENT_PREFIX,
    is_current_seal,
    redact_secret_fields,
    rewrap_secret,
    seal_legacy_v1_for_tests,
    seal_secret,
    unseal_secret,
)


TOKENS = {
    "access_token": "ya29.access-secret-value",
    "refresh_token": "1//refresh-secret-value",
    "expires_in": 3600,
}


def test_aesgcm_roundtrip_access_and_refresh_tokens() -> None:
    sealed = seal_secret(TOKENS)
    assert sealed.startswith(CURRENT_PREFIX)
    assert TOKENS["access_token"] not in sealed
    assert TOKENS["refresh_token"] not in sealed
    opened = unseal_secret(sealed)
    assert opened == TOKENS


def test_aesgcm_is_not_deterministic() -> None:
    first = seal_secret(TOKENS)
    second = seal_secret(TOKENS)
    assert first != second
    assert unseal_secret(first) == unseal_secret(second) == TOKENS


def test_tampered_ciphertext_does_not_open() -> None:
    sealed = seal_secret(TOKENS)
    mutated = sealed[:-4] + ("A" if sealed[-4] != "A" else "B") + sealed[-3:]
    assert unseal_secret(mutated) is None


def test_legacy_hmac_xor_unseals_and_rewraps_to_aesgcm() -> None:
    legacy = seal_legacy_v1_for_tests(TOKENS)
    assert not is_current_seal(legacy)
    assert unseal_secret(legacy) == TOKENS
    upgraded = rewrap_secret(legacy)
    assert upgraded is not None
    assert is_current_seal(upgraded)
    assert unseal_secret(upgraded) == TOKENS


def test_unseal_empty_is_none() -> None:
    assert unseal_secret(None) is None
    assert unseal_secret("") is None


def test_redact_secret_fields() -> None:
    redacted = redact_secret_fields(
        {"account_id": "abc", "access_token": "secret", "nested": {"refresh_token": "also"}}
    )
    assert redacted["account_id"] == "abc"
    assert redacted["access_token"] == "[redacted]"
    assert redacted["nested"]["refresh_token"] == "[redacted]"


def test_production_rejects_short_communication_credential_key() -> None:
    settings = Settings(
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
        COMMUNICATION_CREDENTIAL_KEY="too-short",
    )
    with pytest.raises(RuntimeError, match="COMMUNICATION_CREDENTIAL_KEY"):
        validate_production_security(settings)


def test_dedicated_env_key_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", "unit-test-communication-credential-key-32b")
    get_settings.cache_clear()
    try:
        sealed = seal_secret(TOKENS)
        assert unseal_secret(sealed) == TOKENS
        assert TOKENS["access_token"] not in sealed
        assert TOKENS["refresh_token"] not in sealed
    finally:
        get_settings.cache_clear()


def test_jwt_secret_rotation_does_not_break_communication_unseal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", "unit-test-communication-credential-key-32b")
    monkeypatch.setenv("JWT_SECRET", "unit-test-jwt-secret-not-for-production-32")
    get_settings.cache_clear()
    sealed = seal_secret(TOKENS)
    monkeypatch.setenv("JWT_SECRET", "rotated-jwt-secret-value-independent-32xx")
    get_settings.cache_clear()
    opened = unseal_secret(sealed)
    assert opened == TOKENS


def test_production_missing_communication_credential_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("COMMUNICATION_CREDENTIAL_KEY", raising=False)
    settings = Settings(
        _env_file=None,
        API_ENVIRONMENT="production",
        JWT_SECRET="x" * 40,
        AUTH_COOKIE_SECURE=True,
        API_DEBUG=False,
        API_ENABLE_OPENAPI=False,
        API_AUTH_ENABLED=True,
    )
    with pytest.raises(RuntimeError, match="COMMUNICATION_CREDENTIAL_KEY"):
        validate_production_security(settings)


def test_missing_communication_key_does_not_fall_back_to_jwt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Settings:
        communication_credential_key = None
        jwt_secret = "unit-test-jwt-secret-not-for-production-32"
        environment = "development"

    monkeypatch.setattr("investhome_api.services.crypto_seal.get_settings", lambda: _Settings())
    with pytest.raises(RuntimeError, match="COMMUNICATION_CREDENTIAL_KEY is required"):
        seal_secret(TOKENS)


def test_invalid_communication_key_fails_safely(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", "too-short")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="COMMUNICATION_CREDENTIAL_KEY"):
        get_settings()
    get_settings.cache_clear()
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", "unit-test-communication-credential-key-32b")
    get_settings.cache_clear()
    sealed = seal_secret(TOKENS)
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", "different-unit-test-communication-key-32")
    get_settings.cache_clear()
    assert unseal_secret(sealed) is None
    assert TOKENS["access_token"] not in (sealed or "")
    assert TOKENS["refresh_token"] not in (sealed or "")


def test_communication_key_must_not_equal_jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    shared = "shared-secret-must-not-be-reused-32chars"
    monkeypatch.setenv("JWT_SECRET", shared)
    monkeypatch.setenv("COMMUNICATION_CREDENTIAL_KEY", shared)
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="distinct from JWT_SECRET"):
        get_settings()


def test_seal_does_not_log_tokens(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG):
        sealed = seal_secret(TOKENS)
        unseal_secret(sealed)
    joined = caplog.text
    assert TOKENS["access_token"] not in joined
    assert TOKENS["refresh_token"] not in joined
