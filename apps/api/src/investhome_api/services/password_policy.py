"""Password policy for new passwords only. Existing hashes are never rewritten."""

from __future__ import annotations

import re
import secrets
from uuid import UUID

GENERIC_PASSWORD_ERROR = "Password does not meet requirements"

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 256

# Known demo/default staff passwords plus common weak values (lowercase).
_BLOCKED_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password12",
        "password123",
        "password1234",
        "password123!",
        "passw0rd",
        "passw0rd123",
        "12345678",
        "123456789",
        "1234567890",
        "123456789012",
        "qwertyuiop",
        "qwerty12345",
        "qwerty123456",
        "letmein1234",
        "welcome1234",
        "admin123456",
        "iloveyou123",
        "monkey12345",
        "dragon12345",
        "baseball1234",
        "football1234",
        "princess123",
        "sunshine123",
        "master12345",
        "login123456",
        "changeme1234",
        "demo123!",
        "demo123456",
        "investhome2026!",
        "inviteduser1!",
        "reset-password",
        "newpassword1",
        "newpassword12",
        "default12345",
        "p@ssw0rd1234",
        "abc123456789",
        "aaaaaaaaaaaa",
        "111111111111",
        "000000000000",
    }
)

_ALPHA_NUM = "abcdefghijklmnopqrstuvwxyz0123456789"
_KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm", "1234567890")
_REPEAT_CHUNK = re.compile(r"^(.+)\1{2,}$")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


class PasswordPolicyError(ValueError):
    def __init__(self) -> None:
        super().__init__(GENERIC_PASSWORD_ERROR)


def generate_temporary_password() -> str:
    """Random operator-delivered credential. Never log or return this value."""
    return secrets.token_urlsafe(24)


def production_blocks_demo_staff_login() -> bool:
    from investhome_api.config.settings import get_settings
    from investhome_api.db.demo.safety import PRODUCTION_ENVIRONMENTS

    return (get_settings().environment or "").strip().lower() in PRODUCTION_ENVIRONMENTS


def validate_new_password(
    password: str,
    *,
    email: str | None = None,
    full_name: str | None = None,
    user_id: UUID | str | None = None,
) -> None:
    if not isinstance(password, str):
        raise PasswordPolicyError()
    if len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        raise PasswordPolicyError()
    if "\x00" in password:
        raise PasswordPolicyError()

    lowered = password.lower()
    if lowered in _BLOCKED_PASSWORDS:
        raise PasswordPolicyError()
    if _is_trivial_pattern(lowered, password):
        raise PasswordPolicyError()
    if _contains_account_identifier(lowered, email=email, full_name=full_name, user_id=user_id):
        raise PasswordPolicyError()


def _is_trivial_pattern(lowered: str, original: str) -> bool:
    if len(set(original)) == 1:
        return True
    if _REPEAT_CHUNK.fullmatch(lowered):
        return True
    compact = _NON_ALNUM.sub("", lowered)
    if len(compact) >= MIN_PASSWORD_LENGTH and (len(set(compact)) == 1):
        return True
    if _is_sequential(compact):
        return True
    for row in _KEYBOARD_ROWS:
        if _contains_run(compact, row) or _contains_run(compact, row[::-1]):
            return True
    return False


def _is_sequential(compact: str) -> bool:
    if len(compact) < 8:
        return False
    for source in (_ALPHA_NUM, _ALPHA_NUM[::-1]):
        if compact in source:
            return True
        for index in range(0, len(compact) - 7):
            chunk = compact[index : index + 8]
            if chunk in source:
                return True
    return False


def _contains_run(compact: str, row: str) -> bool:
    if len(compact) < 8:
        return False
    for index in range(0, len(row) - 7):
        run = row[index : index + 8]
        if run in compact:
            return True
    return False


def _contains_account_identifier(
    lowered: str,
    *,
    email: str | None,
    full_name: str | None,
    user_id: UUID | str | None,
) -> bool:
    if email:
        normalized = email.strip().lower()
        if normalized and normalized in lowered:
            return True
        local, _, domain = normalized.partition("@")
        if len(local) >= 3 and local in lowered:
            return True
        host = domain.split(".")[0] if domain else ""
        if len(host) >= 4 and host in lowered:
            return True
    if full_name:
        for part in _NON_ALNUM.split(full_name.strip().lower()):
            if len(part) >= 4 and part in lowered:
                return True
    if user_id is not None:
        token = str(user_id).lower().replace("-", "")
        if len(token) >= 8 and token in lowered.replace("-", ""):
            return True
    return False
