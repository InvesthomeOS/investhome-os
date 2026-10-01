"""Safe CRM person matching for live Email / WhatsApp.

Exactly one identity match attaches automatically.
Zero or many matches go to the unmatched queue — never guess.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.identity import (
    normalize_email,
    parse_phone,
)


@dataclass
class SuggestedMatch:
    contact_id: UUID
    display_name: str
    reason: str

    def as_dict(self) -> dict[str, str]:
        return {
            "contact_id": str(self.contact_id),
            "display_name": self.display_name,
            "reason": self.reason,
        }


@dataclass
class MatchDecision:
    status: str
    contact_id: UUID | None = None
    suggestions: list[SuggestedMatch] = field(default_factory=list)


def _phone_keys(value: str | None) -> set[str]:
    parsed = parse_phone(value)
    if parsed is None:
        return set()
    keys = {parsed.match_key, parsed.digits}
    if parsed.e164:
        keys.add(parsed.e164)
        keys.add(parsed.e164.lstrip("+"))
    return {key for key in keys if key}


def _contact_emails(contact: CrmContact) -> set[str]:
    emails: set[str] = set()
    primary = normalize_email(contact.primary_email)
    if primary:
        emails.add(primary)
    for extra in contact.secondary_emails or []:
        normalized = normalize_email(str(extra))
        if normalized:
            emails.add(normalized)
    return emails


def _contact_phones(contact: CrmContact) -> set[str]:
    keys = _phone_keys(contact.primary_phone)
    for extra in contact.secondary_phones or []:
        keys.update(_phone_keys(str(extra)))
    return keys


def match_identities(
    db: Session,
    *,
    emails: list[str] | None = None,
    phones: list[str] | None = None,
) -> MatchDecision:
    email_keys = {normalize_email(item) for item in emails or []}
    email_keys.discard(None)
    phone_keys: set[str] = set()
    for phone in phones or []:
        phone_keys.update(_phone_keys(phone))
    if not email_keys and not phone_keys:
        return MatchDecision(status="unmatched")

    contacts = list(
        db.scalars(select(CrmContact).where(CrmContact.archived_at.is_(None))).all()
    )
    hits: dict[UUID, SuggestedMatch] = {}
    for contact in contacts:
        reasons: list[str] = []
        if email_keys and _contact_emails(contact) & email_keys:
            reasons.append("email")
        if phone_keys and _contact_phones(contact) & phone_keys:
            reasons.append("phone")
        if reasons:
            hits[contact.id] = SuggestedMatch(
                contact_id=contact.id,
                display_name=contact.display_name,
                reason="+".join(reasons),
            )
    suggestions = list(hits.values())
    if len(suggestions) == 1:
        return MatchDecision(status="matched", contact_id=suggestions[0].contact_id, suggestions=suggestions)
    if len(suggestions) > 1:
        return MatchDecision(status="ambiguous", suggestions=suggestions)
    return MatchDecision(status="unmatched", suggestions=suggestions)
