"""Login brute-force protection tests."""

from __future__ import annotations

import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from starlette.requests import Request

from investhome_api.services.login_rate_limit import (
    GENERIC_LOCKOUT_MESSAGE,
    MAX_FAILED_ATTEMPTS,
    LoginRateLimitStoreError,
    RedisLoginAttemptStore,
    enforce_login_rate_limit,
    identity_counter_key,
    ip_counter_key,
    reset_login_rate_limiter_for_tests,
    resolve_client_ip,
)

DEMO_PASSWORD = "Demo123!"
WRONG_PASSWORD = "WrongPass1"


def _set_peer_ip(client: TestClient, ip: str) -> None:
    """Set the ASGI TCP peer used as request.client.host."""
    candidates = [
        getattr(client, "_transport", None),
        getattr(client, "transport", None),
    ]
    for transport in candidates:
        if transport is not None and hasattr(transport, "client"):
            transport.client = (ip, 50000)
            return
    raise AssertionError("TestClient transport does not expose ASGI client peer")


def _login(
    client: TestClient,
    email: str,
    password: str,
    *,
    ip: str = "testclient",
    headers: dict[str, str] | None = None,
):
    _set_peer_ip(client, ip)
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
        headers=headers or {},
    )


def _asgi_request(peer: str, headers: dict[str, str] | None = None) -> Request:
    encoded = [
        (key.lower().encode("latin-1"), value.encode("latin-1"))
        for key, value in (headers or {}).items()
    ]
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/auth/login",
        "raw_path": b"/auth/login",
        "query_string": b"",
        "headers": encoded,
        "client": (peer, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


def test_successful_login(auth_client: TestClient) -> None:
    response = _login(auth_client, "admin@example.com", DEMO_PASSWORD)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"


def test_failed_attempts_below_limit_remain_generic_401(auth_client: TestClient) -> None:
    email = "unknown.below.limit@example.com"
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        response = _login(auth_client, email, WRONG_PASSWORD, ip="203.0.113.21")
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


def test_lockout_after_threshold_returns_429(auth_client: TestClient) -> None:
    email = "unknown.lockout@example.com"
    ip = "203.0.113.22"
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert _login(auth_client, email, WRONG_PASSWORD, ip=ip).status_code == 401
    blocked = _login(auth_client, email, WRONG_PASSWORD, ip=ip)
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == GENERIC_LOCKOUT_MESSAGE


def test_lockout_includes_retry_after(auth_client: TestClient) -> None:
    email = "unknown.retry@example.com"
    ip = "203.0.113.23"
    for _ in range(MAX_FAILED_ATTEMPTS):
        _login(auth_client, email, WRONG_PASSWORD, ip=ip)
    blocked = _login(auth_client, email, WRONG_PASSWORD, ip=ip)
    assert blocked.status_code == 429
    retry_after = blocked.headers.get("retry-after")
    assert retry_after is not None
    seconds = int(retry_after)
    assert 1 <= seconds <= 15 * 60


def test_successful_login_resets_account_counter(auth_client: TestClient) -> None:
    ip_before = "203.0.113.24"
    for _ in range(3):
        assert (
            _login(
                auth_client,
                "admin@example.com",
                WRONG_PASSWORD,
                ip=ip_before,
            ).status_code
            == 401
        )
    success = _login(auth_client, "admin@example.com", DEMO_PASSWORD, ip=ip_before)
    assert success.status_code == 200

    # New IP so leftover IP counters cannot hide a missing identity reset.
    ip_after = "198.51.100.24"
    for _ in range(MAX_FAILED_ATTEMPTS):
        response = _login(
            auth_client, "admin@example.com", WRONG_PASSWORD, ip=ip_after
        )
        assert response.status_code == 401, response.text
    blocked = _login(auth_client, "admin@example.com", WRONG_PASSWORD, ip=ip_after)
    assert blocked.status_code == 429


def test_different_ip_and_identity_are_isolated(auth_client: TestClient) -> None:
    locked_email = "unknown.isolated.a@example.com"
    locked_ip = "203.0.113.25"
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert _login(auth_client, locked_email, WRONG_PASSWORD, ip=locked_ip).status_code == 401
    assert _login(auth_client, locked_email, WRONG_PASSWORD, ip=locked_ip).status_code == 429

    other = _login(
        auth_client,
        "unknown.isolated.b@example.com",
        WRONG_PASSWORD,
        ip="198.51.100.25",
    )
    assert other.status_code == 401
    assert other.json()["detail"] == "Invalid email or password"


def test_lockout_message_does_not_reveal_account(auth_client: TestClient) -> None:
    known_ip = "203.0.113.26"
    unknown_ip = "203.0.113.27"
    for _ in range(MAX_FAILED_ATTEMPTS):
        _login(auth_client, "admin@example.com", WRONG_PASSWORD, ip=known_ip)
        _login(auth_client, "missing.lockout@example.com", WRONG_PASSWORD, ip=unknown_ip)
    known_block = _login(auth_client, "admin@example.com", WRONG_PASSWORD, ip=known_ip)
    unknown_block = _login(
        auth_client, "missing.lockout@example.com", WRONG_PASSWORD, ip=unknown_ip
    )
    assert known_block.status_code == 429
    assert unknown_block.status_code == 429
    assert known_block.json()["detail"] == unknown_block.json()["detail"] == GENERIC_LOCKOUT_MESSAGE


def test_production_store_failure_does_not_fail_open(monkeypatch, caplog) -> None:
    class BoomStore:
        def retry_after_seconds(self, ip_key: str, identity_key: str) -> int | None:
            raise LoginRateLimitStoreError("forced backend failure")

        def record_failure(self, ip_key: str, identity_key: str) -> None:
            raise LoginRateLimitStoreError("forced backend failure")

        def clear_identity(self, identity_key: str) -> None:
            raise LoginRateLimitStoreError("forced backend failure")

    class _ProductionSettings:
        environment = "production"
        trusted_proxy_ips: list[str] = []

    monkeypatch.setattr(
        "investhome_api.services.login_rate_limit.get_settings",
        lambda: _ProductionSettings(),
    )
    reset_login_rate_limiter_for_tests(BoomStore())
    caplog.set_level(logging.ERROR, logger="investhome.auth.rate_limit")
    with pytest.raises(HTTPException) as excinfo:
        enforce_login_rate_limit(ip="203.0.113.28", identity="admin@example.com")
    assert excinfo.value.status_code == 503
    assert "login_rate_limit_backend_failure" in caplog.text


def test_non_production_store_failure_logs_and_still_limits(
    auth_client: TestClient, monkeypatch, caplog
) -> None:
    class BoomStore:
        def retry_after_seconds(self, ip_key: str, identity_key: str) -> int | None:
            raise LoginRateLimitStoreError("forced backend failure")

        def record_failure(self, ip_key: str, identity_key: str) -> None:
            raise LoginRateLimitStoreError("forced backend failure")

        def clear_identity(self, identity_key: str) -> None:
            raise LoginRateLimitStoreError("forced backend failure")

    class _DevSettings:
        environment = "development"
        trusted_proxy_ips: list[str] = []

    monkeypatch.setattr(
        "investhome_api.services.login_rate_limit.get_settings",
        lambda: _DevSettings(),
    )
    reset_login_rate_limiter_for_tests(BoomStore())
    caplog.set_level(logging.ERROR, logger="investhome.auth.rate_limit")
    email = "unknown.fallback@example.com"
    ip = "203.0.113.29"
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert _login(auth_client, email, WRONG_PASSWORD, ip=ip).status_code == 401
    blocked = _login(auth_client, email, WRONG_PASSWORD, ip=ip)
    assert blocked.status_code == 429
    assert "login_rate_limit_backend_failure" in caplog.text
    assert "login_rate_limit_using_memory_fallback" in caplog.text


def test_redis_store_increments_and_clears_identity() -> None:
    class FakeRedis:
        def __init__(self) -> None:
            self.values: dict[str, int] = {}
            self.expiry: dict[str, int] = {}

        def get(self, key: str) -> str | None:
            value = self.values.get(key)
            return None if value is None else str(value)

        def incr(self, key: str) -> int:
            self.values[key] = int(self.values.get(key) or 0) + 1
            return self.values[key]

        def expire(self, key: str, seconds: int) -> bool:
            self.expiry[key] = seconds
            return True

        def ttl(self, key: str) -> int:
            if key not in self.values:
                return -2
            return int(self.expiry.get(key, -1))

        def delete(self, key: str) -> int:
            existed = int(key in self.values)
            self.values.pop(key, None)
            self.expiry.pop(key, None)
            return existed

    redis = FakeRedis()
    store = RedisLoginAttemptStore(client=redis)
    ip_key = ip_counter_key("203.0.113.40")
    id_key = identity_counter_key("victim@example.com")
    assert store.retry_after_seconds(ip_key, id_key) is None
    for _ in range(MAX_FAILED_ATTEMPTS):
        store.record_failure(ip_key, id_key)
    assert store.retry_after_seconds(ip_key, id_key) == 15 * 60
    store.clear_identity(id_key)
    assert id_key not in redis.values
    assert ip_key in redis.values


def test_forged_x_forwarded_for_does_not_bypass_rate_limit(auth_client: TestClient) -> None:
    email = "unknown.spoof.xff@example.com"
    peer = "203.0.113.50"
    for index in range(MAX_FAILED_ATTEMPTS):
        response = _login(
            auth_client,
            email,
            WRONG_PASSWORD,
            ip=peer,
            headers={"X-Forwarded-For": f"198.51.100.{index}"},
        )
        assert response.status_code == 401
    blocked = _login(
        auth_client,
        email,
        WRONG_PASSWORD,
        ip=peer,
        headers={"X-Forwarded-For": "198.51.100.99"},
    )
    assert blocked.status_code == 429


def test_forged_x_real_ip_does_not_bypass_rate_limit(auth_client: TestClient) -> None:
    email = "unknown.spoof.realip@example.com"
    peer = "203.0.113.51"
    for index in range(MAX_FAILED_ATTEMPTS):
        response = _login(
            auth_client,
            email,
            WRONG_PASSWORD,
            ip=peer,
            headers={"X-Real-IP": f"192.0.2.{index}"},
        )
        assert response.status_code == 401
    blocked = _login(
        auth_client,
        email,
        WRONG_PASSWORD,
        ip=peer,
        headers={"X-Real-IP": "192.0.2.99"},
    )
    assert blocked.status_code == 429


def test_direct_client_ip_isolation(auth_client: TestClient) -> None:
    locked_email = "unknown.direct.a@example.com"
    other_email = "unknown.direct.b@example.com"
    locked_ip = "203.0.113.52"
    other_ip = "198.51.100.52"
    for _ in range(MAX_FAILED_ATTEMPTS):
        assert _login(auth_client, locked_email, WRONG_PASSWORD, ip=locked_ip).status_code == 401
    assert _login(auth_client, locked_email, WRONG_PASSWORD, ip=locked_ip).status_code == 429
    other = _login(auth_client, other_email, WRONG_PASSWORD, ip=other_ip)
    assert other.status_code == 401
    assert other.json()["detail"] == "Invalid email or password"


def test_resolve_client_ip_ignores_forwarded_headers_without_trusted_proxy(
    monkeypatch,
) -> None:
    class _Settings:
        trusted_proxy_ips: list[str] = []
        environment = "development"

    monkeypatch.setattr(
        "investhome_api.services.login_rate_limit.get_settings",
        lambda: _Settings(),
    )
    request = _asgi_request(
        "203.0.113.60",
        {"X-Forwarded-For": "198.51.100.60", "X-Real-IP": "192.0.2.60"},
    )
    assert resolve_client_ip(request) == "203.0.113.60"


def test_resolve_client_ip_trusts_forwarded_headers_only_from_trusted_proxy(
    monkeypatch,
) -> None:
    class _Settings:
        trusted_proxy_ips = ["10.0.0.1"]
        environment = "development"

    monkeypatch.setattr(
        "investhome_api.services.login_rate_limit.get_settings",
        lambda: _Settings(),
    )
    from_proxy = _asgi_request("10.0.0.1", {"X-Forwarded-For": "203.0.113.70"})
    assert resolve_client_ip(from_proxy) == "203.0.113.70"
    from_internet = _asgi_request("8.8.8.8", {"X-Forwarded-For": "203.0.113.70"})
    assert resolve_client_ip(from_internet) == "8.8.8.8"
    real_ip = _asgi_request("10.0.0.1", {"X-Real-IP": "198.51.100.70"})
    assert resolve_client_ip(real_ip) == "198.51.100.70"
