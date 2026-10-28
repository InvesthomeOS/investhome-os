"""Idempotent corrections for the known CRM relationship mistakes.

Records are selected by agreement id plus project, unit, and amount.
A name is only a confirmation. Ambiguous rows are left unchanged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import (
    CrmAgreement,
    CrmAgreementParticipant,
    CrmAgreementStatus,
)
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType
from investhome_api.models.user_auth import User
from investhome_api.services.crm.relationship_corrections import (
    AGENT_TYPES,
    HUNDRED,
    RelationshipCorrectionError,
    add_agreement_owner,
    archive_agent,
    normalize_person_name,
    normalize_unit,
    remove_agreement_owner,
    remove_duplicate_owner,
)

ONTARIO = "2319_ontario"
KST = "1307_k_st"
HPL = "1812_h_pl"
UNILOFT = "uniloft"
REIT = "reit"


@dataclass(frozen=True)
class _OwnerFix:
    key: str
    agreement_id: UUID
    project_group: str
    unit: str | None
    amount_digits: str | None
    keeper_name: str
    remove_name: str


@dataclass(frozen=True)
class _DuplicateFix:
    key: str
    agreement_id: UUID
    project_group: str
    unit: str
    person_name: str


@dataclass(frozen=True)
class _UnlinkFix:
    key: str
    agreement_id: UUID
    project_group: str
    unit: str
    person_name: str


@dataclass(frozen=True)
class _AgentFix:
    key: str
    person_name: str


OWNER_FIXES = (
    _OwnerFix(
        "2319-unit-101",
        UUID("db40cd62-2ff1-475f-a603-af9a2a139062"),
        ONTARIO,
        "101",
        None,
        "Murat Zengin",
        "Yesim Zengin",
    ),
    _OwnerFix(
        "2319-unit-002",
        UUID("1ab68f53-2f72-457b-8ea3-b59572b1d507"),
        ONTARIO,
        "002",
        None,
        "Bahar Basara",
        "Gizem Basara",
    ),
    _OwnerFix(
        "reit-100000",
        UUID("2b02776d-935e-48c5-9def-15dc603cffa1"),
        REIT,
        None,
        "100000",
        "Alper Levi",
        "Selim Levi Beceren",
    ),
    _OwnerFix(
        "1307-unit-302",
        UUID("4f45131d-eb01-4e29-80ab-24940c02b445"),
        KST,
        "302",
        None,
        "Alper Levi",
        "Selim Levi Beceren",
    ),
    _OwnerFix(
        "1307-unit-201",
        UUID("fbba4896-2186-434a-aad5-b3e228a57143"),
        KST,
        "201",
        None,
        "Mujgan Ozdarendeli",
        "",
    ),
)

DUPLICATE_FIXES = (
    _DuplicateFix(
        "1812-unit-306",
        UUID("7f5aa305-04a4-49f6-923b-4b7a560dbfa4"),
        HPL,
        "306",
        "Gokhan Bulbul",
    ),
)

UNLINK_FIXES = (
    _UnlinkFix(
        "uniloft-unit-204",
        UUID("b1caae99-c1ab-4840-b9d4-730d406b6ade"),
        UNILOFT,
        "204",
        "Vedat Mizrahi",
    ),
)

AGENT_FIXES = (
    _AgentFix("agent-kurtulus-goksu", "Kurtulus Goksu"),
    _AgentFix("agent-musa-cobaner", "Musa Cobaner"),
)


def _result(key: str, status: str, detail: str | None = None) -> dict[str, str | None]:
    return {"key": key, "status": status, "detail": detail}


def _money_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def _scoped(
    agreement: CrmAgreement, project_group: str, unit: str | None, amount_digits: str | None
) -> bool:
    if agreement.project_group != project_group:
        return False
    if unit is not None and normalize_unit(agreement.unit_number) != normalize_unit(unit):
        return False
    if amount_digits is None:
        return True
    return _money_digits(agreement.investment_amount).startswith(amount_digits)


def _named(
    rows: list[tuple[CrmAgreementParticipant, CrmContact]], name: str
) -> list[CrmAgreementParticipant]:
    target = normalize_person_name(name)
    return [row for row, contact in rows if normalize_person_name(contact.display_name) == target]


def _load_pairs(
    db: Session, agreement_id: UUID
) -> list[tuple[CrmAgreementParticipant, CrmContact]]:
    participants = list(
        db.scalars(
            select(CrmAgreementParticipant).where(
                CrmAgreementParticipant.agreement_id == agreement_id
            )
        ).all()
    )
    pairs: list[tuple[CrmAgreementParticipant, CrmContact]] = []
    for row in participants:
        contact = db.get(CrmContact, row.contact_id)
        if contact is not None:
            pairs.append((row, contact))
    return pairs


def _apply_owner_fix(db: Session, fix: _OwnerFix, actor: User | None) -> dict[str, str | None]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _result(fix.key, "not_found")
    if not _scoped(agreement, fix.project_group, fix.unit, fix.amount_digits):
        return _result(fix.key, "ambiguous", "project_unit_or_amount")
    pairs = _load_pairs(db, agreement.id)
    keepers = _named(pairs, fix.keeper_name)
    contact = db.get(CrmContact, agreement.contact_id)
    keeper_is_primary = contact is not None and normalize_person_name(
        contact.display_name
    ) == normalize_person_name(fix.keeper_name)
    if not keepers and keeper_is_primary and contact is not None:
        db.add(
            CrmAgreementParticipant(
                agreement_id=agreement.id,
                contact_id=contact.id,
                role="owner",
                ownership_pct=HUNDRED,
                is_primary=True,
                source="crm_correction",
            )
        )
        db.flush()
        pairs = _load_pairs(db, agreement.id)
        keepers = _named(pairs, fix.keeper_name)
    if fix.remove_name:
        removals = _named(pairs, fix.remove_name)
        if len(removals) > 1 or (not keepers and not keeper_is_primary):
            return _result(fix.key, "ambiguous", "owner_identity")
        if not removals:
            if len(keepers) == 1 and keepers[0].ownership_pct == HUNDRED:
                return _result(fix.key, "already_applied")
            if keeper_is_primary and not pairs:
                return _result(fix.key, "already_applied")
            return _result(fix.key, "ambiguous", "remove_target_missing")
        remove_agreement_owner(db, agreement.id, removals[0].contact_id, actor=actor)
        return _result(fix.key, "applied")
    extras = [
        row
        for row, person in pairs
        if normalize_person_name(person.display_name) != normalize_person_name(fix.keeper_name)
    ]
    if not keeper_is_primary and not keepers:
        return _result(fix.key, "ambiguous", "keeper_missing")
    if not extras:
        if keepers and keepers[0].ownership_pct == HUNDRED and len(pairs) == 1:
            return _result(fix.key, "already_applied")
        return _result(fix.key, "ambiguous", "no_extra_owner")
    for row in extras:
        remove_agreement_owner(
            db, agreement.id, row.contact_id, actor=actor, complete_remaining=False
        )
    remaining = _load_pairs(db, agreement.id)
    keeper_rows = _named(remaining, fix.keeper_name)
    if len(keeper_rows) != 1 or len(remaining) != 1:
        raise RelationshipCorrectionError("ambiguous_remaining_owners")
    if keeper_rows[0].ownership_pct != HUNDRED:
        from investhome_api.services.crm.relationship_corrections import set_ownership_percentages

        set_ownership_percentages(
            db,
            agreement.id,
            [(keeper_rows[0].contact_id, Decimal("100"))],
            actor=actor,
        )
    return _result(fix.key, "applied")


def _apply_duplicate_fix(
    db: Session, fix: _DuplicateFix, actor: User | None
) -> dict[str, str | None]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _result(fix.key, "not_found")
    if not _scoped(agreement, fix.project_group, fix.unit, None):
        return _result(fix.key, "ambiguous", "project_or_unit")
    pairs = _load_pairs(db, agreement.id)
    matches = _named(pairs, fix.person_name)
    if len(matches) <= 1:
        return _result(fix.key, "no_duplicate")
    if len(matches) != 2:
        return _result(fix.key, "ambiguous", "duplicate_count")
    outcome = remove_duplicate_owner(
        db,
        agreement.id,
        actor=actor,
        normalized_name=normalize_person_name(fix.person_name),
    )
    return _result(fix.key, "applied" if outcome == "removed" else outcome)


def _apply_unlink_fix(db: Session, fix: _UnlinkFix, actor: User | None) -> dict[str, str | None]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _result(fix.key, "not_found")
    if not _scoped(agreement, fix.project_group, fix.unit, None):
        return _result(fix.key, "ambiguous", "project_or_unit")
    contact = db.get(CrmContact, agreement.contact_id)
    if contact is None or normalize_person_name(contact.display_name) != normalize_person_name(
        fix.person_name
    ):
        return _result(fix.key, "ambiguous", "contact_identity")
    pairs = _load_pairs(db, agreement.id)
    linked = _named(pairs, fix.person_name)
    others = [row for row, _person in pairs if row not in linked]
    meta = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    if (
        not linked
        and meta.get("relationship_detached")
        and agreement.status == CrmAgreementStatus.CANCELLED
    ):
        return _result(fix.key, "already_applied")
    if len(linked) > 1 or others:
        return _result(fix.key, "ambiguous", "other_owners_present")
    if linked:
        remove_agreement_owner(
            db, agreement.id, linked[0].contact_id, actor=actor, complete_remaining=False
        )
        return _result(fix.key, "applied")
    add_agreement_owner(db, agreement.id, contact.id, HUNDRED, actor=actor)
    remove_agreement_owner(db, agreement.id, contact.id, actor=actor, complete_remaining=False)
    return _result(fix.key, "applied")


def _agent_matches(db: Session, name: str) -> list[CrmContact]:
    target = normalize_person_name(name)
    rows = db.scalars(
        select(CrmContact).where(CrmContact.contact_type.in_(tuple(AGENT_TYPES)))
    ).all()
    return [row for row in rows if normalize_person_name(row.display_name) == target]


def _agent_has_purchase(db: Session, contact_id: UUID) -> bool:
    agreement = db.scalar(
        select(CrmAgreement.id).where(
            CrmAgreement.contact_id == contact_id,
            CrmAgreement.status != CrmAgreementStatus.CANCELLED,
        )
    )
    participant = db.scalar(
        select(CrmAgreementParticipant.id).where(CrmAgreementParticipant.contact_id == contact_id)
    )
    return agreement is not None or participant is not None


def _apply_agent_fix(db: Session, fix: _AgentFix, actor: User | None) -> dict[str, str | None]:
    matches = _agent_matches(db, fix.person_name)
    if len(matches) != 1:
        return _result(fix.key, "ambiguous" if matches else "not_found", "agent_identity")
    contact = matches[0]
    if contact.contact_type not in {CrmContactType.BROKER, CrmContactType.REALTOR}:
        return _result(fix.key, "ambiguous", "not_agent")
    if _agent_has_purchase(db, contact.id):
        return _result(fix.key, "ambiguous", "agent_has_purchase")
    status = archive_agent(db, contact.id, actor=actor)
    return _result(fix.key, "already_applied" if status == "already_archived" else "applied")


def _share(value: object) -> str | None:
    if value is None:
        return None
    return format(Decimal(str(value)), "f")


def _people(pairs: list[tuple[CrmAgreementParticipant, CrmContact]]) -> list[dict[str, object]]:
    return [
        {
            "contact_id": str(contact.id),
            "display_name": contact.display_name,
            "ownership_pct": _share(row.ownership_pct),
            "is_primary": bool(row.is_primary),
        }
        for row, contact in pairs
    ]


def _preview_item(
    key: str,
    status: str,
    *,
    agreement_id: UUID | None = None,
    contact_id: UUID | None = None,
    current: dict[str, object] | None = None,
    intended: dict[str, object] | None = None,
    detail: str | None = None,
) -> dict[str, object]:
    return {
        "key": key,
        "status": status,
        "agreement_id": str(agreement_id) if agreement_id else None,
        "contact_id": str(contact_id) if contact_id else None,
        "current": current or {},
        "intended": intended or {},
        "detail": detail,
    }


def _preview_owner_fix(db: Session, fix: _OwnerFix) -> dict[str, object]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _preview_item(fix.key, "not_found", detail="agreement")
    if not _scoped(agreement, fix.project_group, fix.unit, fix.amount_digits):
        return _preview_item(
            fix.key,
            "ambiguous",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            detail="project_unit_or_amount",
        )
    pairs = _load_pairs(db, agreement.id)
    keepers = _named(pairs, fix.keeper_name)
    contact = db.get(CrmContact, agreement.contact_id)
    keeper_is_primary = contact is not None and normalize_person_name(
        contact.display_name
    ) == normalize_person_name(fix.keeper_name)
    current = {"participants": _people(pairs)}
    keep = {
        "display_name": fix.keeper_name,
        "ownership_pct": "100.00",
        "contact_id": str(keepers[0].contact_id) if len(keepers) == 1 else None,
    }
    if fix.remove_name:
        removals = _named(pairs, fix.remove_name)
        if len(removals) > 1 or (not keepers and not keeper_is_primary):
            return _preview_item(
                fix.key,
                "ambiguous",
                agreement_id=agreement.id,
                contact_id=agreement.contact_id,
                current=current,
                detail="owner_identity",
            )
        if not removals:
            done = (len(keepers) == 1 and keepers[0].ownership_pct == HUNDRED) or (
                keeper_is_primary and not pairs
            )
            return _preview_item(
                fix.key,
                "already_applied" if done else "ambiguous",
                agreement_id=agreement.id,
                contact_id=agreement.contact_id,
                current=current,
                intended={"keep": [keep], "remove": []},
                detail=None if done else "remove_target_missing",
            )
        remove = _people(
            [(removals[0], next(person for row, person in pairs if row is removals[0]))]
        )
        return _preview_item(
            fix.key,
            "ready",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            current=current,
            intended={"keep": [keep], "remove": remove},
        )
    extras = [
        (row, person)
        for row, person in pairs
        if normalize_person_name(person.display_name) != normalize_person_name(fix.keeper_name)
    ]
    if not keeper_is_primary and not keepers:
        return _preview_item(
            fix.key,
            "ambiguous",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            current=current,
            detail="keeper_missing",
        )
    if not extras:
        done = bool(keepers) and keepers[0].ownership_pct == HUNDRED and len(pairs) == 1
        return _preview_item(
            fix.key,
            "already_applied" if done else "ambiguous",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            current=current,
            intended={"keep": [keep], "remove": []},
            detail=None if done else "no_extra_owner",
        )
    return _preview_item(
        fix.key,
        "ready",
        agreement_id=agreement.id,
        contact_id=agreement.contact_id,
        current=current,
        intended={"keep": [keep], "remove": _people(extras)},
    )


def _preview_duplicate_fix(db: Session, fix: _DuplicateFix) -> dict[str, object]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _preview_item(fix.key, "not_found", detail="agreement")
    if not _scoped(agreement, fix.project_group, fix.unit, None):
        return _preview_item(
            fix.key,
            "ambiguous",
            agreement_id=agreement.id,
            detail="project_or_unit",
        )
    pairs = _load_pairs(db, agreement.id)
    matches = [(row, person) for row, person in pairs if row in _named(pairs, fix.person_name)]
    current = {"participants": _people(pairs)}
    if len(matches) <= 1:
        return _preview_item(
            fix.key,
            "already_applied",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            current=current,
            detail="no_duplicate",
        )
    if len(matches) != 2:
        return _preview_item(
            fix.key,
            "blocked",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            current=current,
            detail="duplicate_count",
        )
    keeper = next((row for row, _person in matches if row.contact_id == agreement.contact_id), None)
    if keeper is None:
        primary = [row for row, _person in matches if row.is_primary]
        keeper = primary[0] if len(primary) == 1 else None
    if keeper is None:
        return _preview_item(
            fix.key,
            "blocked",
            agreement_id=agreement.id,
            current=current,
            detail="duplicate_keeper",
        )
    remove = [(row, person) for row, person in matches if row.id != keeper.id]
    return _preview_item(
        fix.key,
        "ready",
        agreement_id=agreement.id,
        contact_id=agreement.contact_id,
        current=current,
        intended={
            "keep": _people([(keeper, next(person for row, person in matches if row is keeper))]),
            "remove": _people(remove),
            "historical_activity_preserved": True,
        },
    )


def _preview_unlink_fix(db: Session, fix: _UnlinkFix) -> dict[str, object]:
    agreement = db.get(CrmAgreement, fix.agreement_id)
    if agreement is None:
        return _preview_item(fix.key, "not_found", detail="agreement")
    if not _scoped(agreement, fix.project_group, fix.unit, None):
        return _preview_item(
            fix.key,
            "ambiguous",
            agreement_id=agreement.id,
            detail="project_or_unit",
        )
    contact = db.get(CrmContact, agreement.contact_id)
    if contact is None or normalize_person_name(contact.display_name) != normalize_person_name(
        fix.person_name
    ):
        return _preview_item(
            fix.key,
            "ambiguous",
            agreement_id=agreement.id,
            contact_id=agreement.contact_id,
            detail="contact_identity",
        )
    pairs = _load_pairs(db, agreement.id)
    linked = _named(pairs, fix.person_name)
    others = [row for row, _person in pairs if row not in linked]
    meta = agreement.metadata_json if isinstance(agreement.metadata_json, dict) else {}
    ceased = {
        "active_purchaser": False,
        "relationship_detached": True,
        "agreement_status": CrmAgreementStatus.CANCELLED.value,
        "contact_preserved": True,
        "display_name": contact.display_name,
    }
    current = {
        "participants": _people(pairs),
        "agreement_status": agreement.status.value,
        "active_purchaser": not (
            meta.get("relationship_detached") and agreement.status == CrmAgreementStatus.CANCELLED
        ),
    }
    if (
        not linked
        and meta.get("relationship_detached")
        and agreement.status == CrmAgreementStatus.CANCELLED
    ):
        return _preview_item(
            fix.key,
            "already_applied",
            agreement_id=agreement.id,
            contact_id=contact.id,
            current=current,
            intended=ceased,
        )
    if len(linked) > 1 or others:
        return _preview_item(
            fix.key,
            "blocked",
            agreement_id=agreement.id,
            contact_id=contact.id,
            current=current,
            detail="other_owners_present",
        )
    return _preview_item(
        fix.key,
        "ready",
        agreement_id=agreement.id,
        contact_id=contact.id,
        current=current,
        intended=ceased,
    )


def _preview_agent_fix(db: Session, fix: _AgentFix) -> dict[str, object]:
    matches = _agent_matches(db, fix.person_name)
    if not matches:
        return _preview_item(fix.key, "not_found", detail="agent_identity")
    if len(matches) != 1:
        return _preview_item(fix.key, "ambiguous", detail="agent_identity")
    contact = matches[0]
    current = {"display_name": contact.display_name, "status": contact.status.value}
    if _agent_has_purchase(db, contact.id):
        return _preview_item(
            fix.key,
            "blocked",
            contact_id=contact.id,
            current=current,
            detail="agent_has_purchase",
        )
    if contact.status == CrmContactStatus.ARCHIVED:
        return _preview_item(
            fix.key,
            "already_applied",
            contact_id=contact.id,
            current=current,
            intended={"action": "archive", "status": "archived"},
        )
    return _preview_item(
        fix.key,
        "ready",
        contact_id=contact.id,
        current=current,
        intended={"action": "archive", "status": "archived"},
    )


def preview_known_crm_corrections(db: Session) -> list[dict[str, object]]:
    """Read-only plan. Does not write rows and does not authorize a later apply."""
    return [
        *(_preview_owner_fix(db, fix) for fix in OWNER_FIXES),
        *(_preview_duplicate_fix(db, fix) for fix in DUPLICATE_FIXES),
        *(_preview_unlink_fix(db, fix) for fix in UNLINK_FIXES),
        *(_preview_agent_fix(db, fix) for fix in AGENT_FIXES),
    ]


def apply_known_crm_corrections(db: Session, *, actor: User | None) -> list[dict[str, str | None]]:
    """Apply each known case in its own savepoint. Ambiguity changes nothing for that case."""
    results: list[dict[str, str | None]] = []
    steps: list[tuple[str, object]] = [
        *((fix.key, lambda fix=fix: _apply_owner_fix(db, fix, actor)) for fix in OWNER_FIXES),
        *(
            (fix.key, lambda fix=fix: _apply_duplicate_fix(db, fix, actor))
            for fix in DUPLICATE_FIXES
        ),
        *((fix.key, lambda fix=fix: _apply_unlink_fix(db, fix, actor)) for fix in UNLINK_FIXES),
        *((fix.key, lambda fix=fix: _apply_agent_fix(db, fix, actor)) for fix in AGENT_FIXES),
    ]
    for key, step in steps:
        nested = db.begin_nested()
        try:
            outcome = step()
            if outcome["status"] in {"ambiguous", "failed"}:
                nested.rollback()
                results.append(outcome)
            else:
                nested.commit()
                results.append(outcome)
        except RelationshipCorrectionError as exc:
            nested.rollback()
            results.append(_result(key, "ambiguous", exc.code))
        except Exception:
            nested.rollback()
            results.append(_result(key, "failed", "unexpected"))
    return results
