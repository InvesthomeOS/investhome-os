"""Reusable CRM identity matching — phone first, email second, name review-only.

Phone normalization never assumes +1 for bare national numbers.
Turkish mobiles (05xx / 5xx / +90) and explicit US (+1 / 11-digit NANP) are supported.

ZERO-MISSING RULE: a person who exists in an authoritative source must exist
visibly in OS. Missing phone/email/address is never a reason to exclude them.
Name-only matching is review, never a silent merge.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

ZERO_MISSING_NOTE = (
    "BILGI_EKSIK: Source person kept visible with blank profile fields. "
    "Missing phone/email/address is not a reason to exclude."
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_NON_DIGIT = re.compile(r"\D")
_WHITESPACE = re.compile(r"\s+")
AGENT_ADVISOR_NAME_RE = re.compile(r"acenta\s*dan[ıi][sş]man", re.I)
_ZERO_MASK_PHONE = re.compile(r"0{5,}$")
_TR_FOLD = str.maketrans({
    "ı": "i",
    "ü": "u",
    "ö": "o",
    "ş": "s",
    "ğ": "g",
    "ç": "c",
    "â": "a",
})


class IdentityMatchKind(StrEnum):
    PHONE = "phone"
    EMAIL = "email"
    NAME_REVIEW = "name_review"
    NONE = "none"
    NO_IDENTITY = "no_identity"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class NormalizedPhone:
    raw: str
    digits: str
    e164: str | None
    country: str | None
    match_key: str
    suspicious: bool


@dataclass(frozen=True)
class IdentityRecord:
    key: str
    display_name: str
    phone: NormalizedPhone | None
    email: str | None
    name_key: str | None
    origin: str
    contact_id: UUID | None = None


@dataclass(frozen=True)
class IdentityMatch:
    kind: IdentityMatchKind
    record: IdentityRecord | None
    candidates: tuple[IdentityRecord, ...] = ()
    reason: str = ""


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def is_valid_email(value: str | None) -> bool:
    email = normalize_email(value)
    return bool(email and _EMAIL_RE.match(email))


def normalize_valid_email(value: str | None) -> str | None:
    email = normalize_email(value)
    return email if is_valid_email(email) else None


def normalize_full_name(value: str | None) -> str | None:
    if not value:
        return None
    folded = unicodedata.normalize("NFKC", value).casefold()
    folded = folded.translate(_TR_FOLD)
    folded = _WHITESPACE.sub(" ", folded).strip()
    folded = re.sub(r"[^\w\s]", "", folded, flags=re.UNICODE)
    folded = _WHITESPACE.sub(" ", folded).strip()
    return folded or None


def is_agent_advisor_name(value: str | None) -> bool:
    return bool(AGENT_ADVISOR_NAME_RE.search(value or ""))


_MULTI_VALUE_SPLIT = re.compile(r"[,;/|]+")


def split_multi_values(value: str | None) -> list[str]:
    """Split comma/semicolon-separated source cells without inventing values."""
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    parts = [part.strip() for part in _MULTI_VALUE_SPLIT.split(text) if part.strip()]
    return parts or [text]


def parse_phone(value: str | None) -> NormalizedPhone | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()
    had_plus = raw.startswith("+") or raw.startswith("00")
    digits = _NON_DIGIT.sub("", raw)
    if not digits:
        return None

    country: str | None = None
    e164: str | None = None
    suspicious = False

    if digits.startswith("00"):
        digits = digits[2:]
        had_plus = True

    if had_plus:
        if digits.startswith("90") and len(digits) >= 12:
            country = "TR"
            e164 = f"+{digits}"
        elif digits.startswith("1") and len(digits) == 11:
            country = "US"
            e164 = f"+{digits}"
        elif digits.startswith("90"):
            country = "TR"
            e164 = f"+{digits}"
        else:
            e164 = f"+{digits}"
            if len(digits) < 8:
                suspicious = True
    elif digits.startswith("90") and len(digits) == 12:
        country = "TR"
        e164 = f"+{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        country = "US"
        e164 = f"+{digits}"
    elif len(digits) == 11 and digits.startswith("05"):
        country = "TR"
        e164 = f"+90{digits[1:]}"
    elif len(digits) == 10 and digits.startswith("5"):
        country = "TR"
        e164 = f"+90{digits}"
    else:
        suspicious = True
        e164 = None

    match_key = e164 or f"d:{digits}"
    return NormalizedPhone(
        raw=raw,
        digits=digits,
        e164=e164,
        country=country,
        match_key=match_key,
        suspicious=suspicious,
    )


def normalize_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed is None:
        return None
    return parsed.e164 or parsed.digits


def phone_digits(value: str | None) -> str:
    if not value:
        return ""
    return _NON_DIGIT.sub("", str(value))


def is_zero_masked_phone(value: str | None) -> bool:
    """True when a phone looks like a truncated/masked numeric Excel value (trailing zeros)."""
    digits = phone_digits(value)
    return len(digits) >= 10 and bool(_ZERO_MASK_PHONE.search(digits))


def phone_quality(value: str | None) -> tuple[int, int]:
    """Higher tuple is a better canonical phone. Masked trailing-zero values rank lowest."""
    if not value or not str(value).strip():
        return (0, 0)
    digits = phone_digits(value)
    if not digits:
        return (0, 0)
    if is_zero_masked_phone(value):
        return (1, 0)
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return (5, len(digits))
    if parsed and not parsed.suspicious:
        return (4, len(digits))
    return (3, len(digits))


def phone_is_better(candidate: str | None, current: str | None) -> bool:
    return phone_quality(candidate) > phone_quality(current)


def prefer_better_phone(*values: str | None) -> str | None:
    best: str | None = None
    for value in values:
        if phone_is_better(value, best):
            best = value
    return best


def displayable_phone(*values: str | None) -> str | None:
    """Best phone that is safe to show. Masked/zero-corrupted Excel values stay blank."""
    best = prefer_better_phone(*values)
    if not best or is_zero_masked_phone(best):
        return None
    return str(best).strip() or None


def displayable_phones(values: list[str] | tuple[str, ...] | None) -> list[str] | None:
    if not values:
        return None
    visible = []
    seen: set[str] = set()
    for value in values:
        phone = displayable_phone(value)
        if not phone or phone in seen:
            continue
        seen.add(phone)
        visible.append(phone)
    return visible or None


def has_usable_identity(phone: str | None, email: str | None) -> bool:
    parsed_phone = parse_phone(phone)
    return bool(
        (parsed_phone and parsed_phone.e164 and not parsed_phone.suspicious)
        or normalize_valid_email(email)
    )


class IdentityIndex:
    """In-memory phone → email → name index. Name hits are never auto-linked."""

    def __init__(self) -> None:
        self._by_phone: dict[str, list[IdentityRecord]] = {}
        self._by_email: dict[str, list[IdentityRecord]] = {}
        self._by_name: dict[str, list[IdentityRecord]] = {}
        self.records: list[IdentityRecord] = []

    def add(self, record: IdentityRecord) -> None:
        self.records.append(record)
        if record.phone and record.phone.e164 and not record.phone.suspicious:
            self._by_phone.setdefault(record.phone.match_key, []).append(record)
        valid_email = normalize_valid_email(record.email)
        if valid_email:
            self._by_email.setdefault(valid_email, []).append(record)
        if record.name_key:
            self._by_name.setdefault(record.name_key, []).append(record)

    def match(self, phone: str | None, email: str | None, name: str | None) -> IdentityMatch:
        parsed_phone = parse_phone(phone)
        safe_phone = (
            parsed_phone
            if parsed_phone and parsed_phone.e164 and not parsed_phone.suspicious
            else None
        )
        parsed_email = normalize_valid_email(email)
        if safe_phone is None and parsed_email is None:
            name_key = normalize_full_name(name)
            if name_key:
                name_hits = tuple(self._by_name.get(name_key, ()))
                if name_hits:
                    return IdentityMatch(
                        kind=IdentityMatchKind.NAME_REVIEW,
                        record=None,
                        candidates=name_hits,
                        reason="name_only_review",
                    )
            return IdentityMatch(kind=IdentityMatchKind.NO_IDENTITY, record=None, reason="no_phone_no_email")

        if safe_phone is not None:
            keys = [safe_phone.match_key]
            seen: dict[str, IdentityRecord] = {}
            for key in keys:
                for hit in self._by_phone.get(key, ()):
                    seen[hit.key] = hit
            phone_hits = tuple(seen.values())
            if len(phone_hits) == 1:
                return IdentityMatch(kind=IdentityMatchKind.PHONE, record=phone_hits[0], candidates=phone_hits)
            if len(phone_hits) > 1:
                return IdentityMatch(
                    kind=IdentityMatchKind.AMBIGUOUS,
                    record=None,
                    candidates=phone_hits,
                    reason="ambiguous_phone",
                )

        if parsed_email is not None:
            email_hits = tuple(self._by_email.get(parsed_email, ()))
            if len(email_hits) == 1:
                return IdentityMatch(kind=IdentityMatchKind.EMAIL, record=email_hits[0], candidates=email_hits)
            if len(email_hits) > 1:
                return IdentityMatch(
                    kind=IdentityMatchKind.AMBIGUOUS,
                    record=None,
                    candidates=email_hits,
                    reason="ambiguous_email",
                )

        name_key = normalize_full_name(name)
        name_hits = tuple(self._by_name.get(name_key, ())) if name_key else ()
        reason = "deterministic_unmatched"
        if name_hits:
            reason = "deterministic_unmatched_same_name_warning"
        return IdentityMatch(
            kind=IdentityMatchKind.NONE,
            record=None,
            candidates=name_hits,
            reason=reason,
        )
