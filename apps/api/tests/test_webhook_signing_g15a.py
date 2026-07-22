"""G15A webhook HMAC signature foundation tests."""

from investhome_api.services.webhook_signing import (
    generate_webhook_secret,
    sign_payload,
    verify_signature,
)


def test_sign_and_verify_roundtrip():
    raw, prefix, digest = generate_webhook_secret()
    assert raw.startswith("whsec_")
    assert prefix.startswith("whsec_")
    assert len(digest) == 64

    payload = b'{"module":"platform_admin","ok":true}'
    header = sign_payload(raw, payload, timestamp=1_700_000_000, nonce="abc123")
    assert "t=1700000000" in header
    assert "v1=" in header
    assert "n=abc123" in header
    assert verify_signature(raw, payload, header, tolerance_seconds=10**9) is True


def test_verify_rejects_replayed_nonce():
    raw, _, _ = generate_webhook_secret()
    payload = b'{"a":1}'
    header = sign_payload(raw, payload, timestamp=1_700_000_000, nonce="replay-me")
    assert verify_signature(raw, payload, header, tolerance_seconds=10**9) is True
    assert verify_signature(raw, payload, header, tolerance_seconds=10**9) is False


def test_verify_rejects_tampered_payload():
    raw, _, _ = generate_webhook_secret()
    payload = b'{"a":1}'
    header = sign_payload(raw, payload, timestamp=1_700_000_000, nonce="n1")
    assert verify_signature(raw, b'{"a":2}', header, tolerance_seconds=10**9, enforce_replay=False) is False


def test_verify_rejects_bad_header():
    raw, _, _ = generate_webhook_secret()
    assert verify_signature(raw, b"{}", "not-a-signature") is False
