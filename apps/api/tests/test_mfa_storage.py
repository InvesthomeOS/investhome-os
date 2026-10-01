"""MFA storage helpers — sealing and recovery hashes only, no enrollment."""

from __future__ import annotations

from investhome_api.services.crypto_seal import seal_secret, unseal_secret
from investhome_api.services.mfa_crypto import (
    CURRENT_PREFIX,
    hash_recovery_code,
    recovery_code_matches,
    seal_totp_secret,
    unseal_totp_secret,
)


def test_totp_secret_roundtrip_is_not_plaintext() -> None:
    secret = "JBSWY3DPEHPK3PXP"
    sealed = seal_totp_secret(secret)
    assert sealed.startswith(CURRENT_PREFIX)
    assert secret not in sealed
    assert unseal_totp_secret(sealed) == secret


def test_mfa_seal_is_not_openable_as_communication_credential() -> None:
    secret = "JBSWY3DPEHPK3PXP"
    mfa_blob = seal_totp_secret(secret)
    assert unseal_secret(mfa_blob) is None
    comm_blob = seal_secret({"token": "comm-only"})
    assert unseal_totp_secret(comm_blob) is None


def test_recovery_code_stores_hash_not_plaintext() -> None:
    code = "ABCD-EFGH-IJKL"
    digest = hash_recovery_code(code)
    assert code not in digest
    assert digest.startswith("$2")
    assert recovery_code_matches(code, digest)
    assert not recovery_code_matches("XXXX-XXXX-XXXX", digest)
