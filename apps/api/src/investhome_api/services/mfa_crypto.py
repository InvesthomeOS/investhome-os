"""Authenticated encryption for TOTP secrets at rest.

AES-256-GCM with an MFA-specific HKDF purpose so communication-credential
seals cannot open MFA blobs (and vice versa). Never log plaintext, ciphertext,
or key material.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from investhome_api.config.settings import get_settings

CURRENT_PREFIX = "v2:aesgcm:"
_AAD = b"investhome-os:mfa-totp-secret:v1"
_HKDF_SALT = b"investhome-os-mfa-totp-v1"
_HKDF_INFO = b"mfa-totp-secret-aesgcm"


def _aes_key() -> bytes:
    settings = get_settings()
    return HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_HKDF_SALT,
        info=_HKDF_INFO,
    ).derive(settings.jwt_secret.encode("utf-8"))


def seal_totp_secret(secret: str) -> str:
    """Encrypt a TOTP shared secret. Caller must not log `secret` or the blob."""
    nonce = os.urandom(12)
    cipher = AESGCM(_aes_key()).encrypt(nonce, secret.encode("utf-8"), _AAD)
    return CURRENT_PREFIX + base64.urlsafe_b64encode(nonce + cipher).decode("ascii")


def unseal_totp_secret(token: str | None) -> str | None:
    if not token or not token.startswith(CURRENT_PREFIX):
        return None
    try:
        raw = base64.urlsafe_b64decode(token[len(CURRENT_PREFIX) :].encode("ascii"))
        if len(raw) < 13 + 16:
            return None
        nonce, cipher = raw[:12], raw[12:]
        return AESGCM(_aes_key()).decrypt(nonce, cipher, _AAD).decode("utf-8")
    except Exception:
        return None


def hash_recovery_code(code: str) -> str:
    """bcrypt hash for a recovery code. Never persist the plaintext code."""
    from investhome_api.services.auth_service import hash_password

    return hash_password(code)


def recovery_code_matches(code: str, code_hash: str) -> bool:
    from investhome_api.services.auth_service import verify_password

    return verify_password(code, code_hash)
