"""Authenticated encryption for live Email / WhatsApp tokens at rest.

Uses AES-256-GCM with COMMUNICATION_CREDENTIAL_KEY only.
JWT_SECRET is never used to derive the current communication credential key.

Never log plaintext, ciphertext, or key material.
Legacy HMAC-XOR blobs (v1) can still be opened and are re-wrapped to v2.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from investhome_api.config.settings import get_settings

CURRENT_PREFIX = "v2:aesgcm:"
_AAD = b"investhome-os:communication-credentials:v2"
_HKDF_SALT = b"investhome-os-live-comm-v2"
_HKDF_INFO = b"communication-credentials-aesgcm"
_LEGACY_PURPOSE = "live-comm-v1"

_SECRET_FIELD_NAMES = frozenset(
    {
        "password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "client_secret",
        "credentials",
        "encrypted_credentials",
        "authorization",
        "id_token",
        "session_token",
    }
)


def is_current_seal(token: str | None) -> bool:
    return bool(token) and token.startswith(CURRENT_PREFIX)


def _parse_configured_key(value: str) -> bytes:
    stripped = value.strip()
    padded = stripped + ("=" * ((4 - len(stripped) % 4) % 4))
    try:
        decoded = base64.urlsafe_b64decode(padded.encode("ascii"))
        if len(decoded) == 32:
            return decoded
    except (ValueError, UnicodeEncodeError):
        pass
    try:
        decoded = bytes.fromhex(stripped)
        if len(decoded) == 32:
            return decoded
    except ValueError:
        pass
    if len(stripped.encode("utf-8")) < 32:
        raise ValueError("communication_credential_key_too_short")
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(stripped.encode("utf-8"))


def _aes_key() -> bytes:
    settings = get_settings()
    explicit = (settings.communication_credential_key or "").strip()
    if not explicit:
        raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY is required")
    if explicit == (settings.jwt_secret or "").strip():
        raise RuntimeError("COMMUNICATION_CREDENTIAL_KEY must be distinct from JWT_SECRET")
    return _parse_configured_key(explicit)


def seal_secret(payload: dict[str, Any]) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    nonce = os.urandom(12)
    cipher = AESGCM(_aes_key()).encrypt(nonce, body, _AAD)
    return CURRENT_PREFIX + base64.urlsafe_b64encode(nonce + cipher).decode("ascii")


def _unseal_v2(token: str) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode(token[len(CURRENT_PREFIX) :].encode("ascii"))
        if len(raw) < 13 + 16:
            return None
        nonce, cipher = raw[:12], raw[12:]
        body = AESGCM(_aes_key()).decrypt(nonce, cipher, _AAD)
        data = json.loads(body.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _legacy_v1_key(secret: str) -> bytes:
    return hashlib.sha256(f"{_LEGACY_PURPOSE}:{secret}".encode("utf-8")).digest()


def _unseal_legacy_v1(token: str) -> dict[str, Any] | None:
    """Open pre-hardening HMAC-XOR blobs so they can be re-wrapped."""
    secret = get_settings().jwt_secret
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(raw) < 33:
            return None
        mac, cipher = raw[:32], raw[32:]
        key = _legacy_v1_key(secret)
        expected = hmac.new(key, cipher, hashlib.sha256).digest()
        if not hmac.compare_digest(mac, expected):
            return None
        pad = bytearray()
        counter = 0
        while len(pad) < len(cipher):
            pad.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
            counter += 1
        body = bytes(a ^ b for a, b in zip(cipher, pad[: len(cipher)], strict=True))
        data = json.loads(body.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def seal_legacy_v1_for_tests(payload: dict[str, Any]) -> str:
    """Test-only helper to build a v1 blob. Do not use for new storage."""
    secret = get_settings().jwt_secret
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    key = _legacy_v1_key(secret)
    pad = bytearray()
    counter = 0
    while len(pad) < len(body):
        pad.extend(hmac.new(key, counter.to_bytes(4, "big"), hashlib.sha256).digest())
        counter += 1
    cipher = bytes(a ^ b for a, b in zip(body, pad[: len(body)], strict=True))
    mac = hmac.new(key, cipher, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(mac + cipher).decode("ascii")


def unseal_secret(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    if is_current_seal(token):
        return _unseal_v2(token)
    return _unseal_legacy_v1(token)


def rewrap_secret(token: str | None) -> str | None:
    """Return a v2 AES-GCM blob, upgrading a legacy v1 token when needed."""
    if not token:
        return None
    if is_current_seal(token):
        return token
    payload = unseal_secret(token)
    if payload is None:
        return None
    return seal_secret(payload)


def redact_secret_fields(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_FIELD_NAMES:
                redacted[key] = "[redacted]"
            else:
                redacted[key] = redact_secret_fields(item)
        return redacted
    if isinstance(value, list):
        return [redact_secret_fields(item) for item in value]
    return value
