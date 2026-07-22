"""HMAC webhook signature foundation for platform outbound webhooks."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Any


SIGNATURE_HEADER = "X-InvestHome-Signature"
TIMESTAMP_HEADER = "X-InvestHome-Timestamp"
NONCE_HEADER = "X-InvestHome-Nonce"
WEBHOOK_SECRET_PREFIX = "whsec_"

# In-process replay cache (foundation). Production should use Redis.
_SEEN_NONCES: dict[str, int] = {}


def generate_webhook_secret() -> tuple[str, str, str]:
    """Return (raw_secret, prefix, sha256_hash). Raw shown once to admin."""
    raw = WEBHOOK_SECRET_PREFIX + secrets.token_urlsafe(32)
    prefix = raw[:12]
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, prefix, digest


def hash_webhook_secret(raw_secret: str) -> str:
    return hashlib.sha256(raw_secret.encode("utf-8")).hexdigest()


def sign_payload(
    secret: str,
    payload_bytes: bytes,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> str:
    """
    Sign payload with HMAC-SHA256.

    Format: t=<unix>,v1=<hex_digest>[,n=<nonce>] over "{timestamp}.{nonce}.{payload}".
    """
    ts = timestamp if timestamp is not None else int(time.time())
    n = nonce or secrets.token_hex(8)
    signed = f"{ts}.{n}.".encode("utf-8") + payload_bytes
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest},n={n}"


def verify_signature(
    secret: str,
    payload_bytes: bytes,
    signature_header: str,
    *,
    tolerance_seconds: int = 300,
    enforce_replay: bool = True,
) -> bool:
    """Verify signed webhook payload. Rejects skew and replayed nonces."""
    try:
        parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
        ts = int(parts["t"])
        expected_v1 = parts["v1"]
        nonce = parts.get("n", "")
    except (KeyError, ValueError):
        return False

    now = int(time.time())
    if abs(now - ts) > tolerance_seconds:
        return False

    if enforce_replay and nonce:
        # purge old
        stale = [k for k, exp in _SEEN_NONCES.items() if exp < now]
        for k in stale:
            _SEEN_NONCES.pop(k, None)
        if nonce in _SEEN_NONCES:
            return False

    signed = f"{ts}.{nonce}.".encode("utf-8") + payload_bytes
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    ok = hmac.compare_digest(digest, expected_v1)
    if ok and enforce_replay and nonce:
        _SEEN_NONCES[nonce] = now + tolerance_seconds
    return ok


def build_signed_headers(secret: str, payload: dict[str, Any] | bytes) -> dict[str, str]:
    import json

    if isinstance(payload, bytes):
        body = payload
    else:
        body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ts = int(time.time())
    nonce = secrets.token_hex(8)
    sig = sign_payload(secret, body, timestamp=ts, nonce=nonce)
    return {
        SIGNATURE_HEADER: sig,
        TIMESTAMP_HEADER: str(ts),
        NONCE_HEADER: nonce,
        "Content-Type": "application/json",
    }
