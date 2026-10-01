"""Mandatory MFA for privileged roles. Does not change permissions or schema."""

from __future__ import annotations

from investhome_api.models.user_auth import User

MANDATORY_MFA_ROLE_CODES = frozenset(
    {
        "super_admin",
        "executive",
        "finance",
        "operations",
        "investor_relations",
        "marketing",
    }
)

OPTIONAL_MFA_ROLE_CODES = frozenset(
    {
        "sales",
        "construction",
        "partner",
        "assistant",
        "read_only",
    }
)

PURPOSE_LOGIN = "login"
PURPOSE_ENROLLMENT = "enrollment"

_enforcement_disabled_for_tests = False


def set_mfa_enforcement_disabled_for_tests(disabled: bool) -> None:
    """Test isolation only. Production always uses MANDATORY_MFA_ROLE_CODES."""
    global _enforcement_disabled_for_tests
    _enforcement_disabled_for_tests = disabled


def get_mandatory_mfa_role_codes() -> frozenset[str]:
    if _enforcement_disabled_for_tests:
        return frozenset()
    return MANDATORY_MFA_ROLE_CODES


def user_role_codes(user: User) -> set[str]:
    return {role.code for role in (user.roles or [])}


def user_requires_mandatory_mfa(user: User) -> bool:
    return bool(user_role_codes(user) & get_mandatory_mfa_role_codes())


def user_needs_mfa_enrollment(user: User) -> bool:
    return user_requires_mandatory_mfa(user) and not bool(user.mfa_enabled)
