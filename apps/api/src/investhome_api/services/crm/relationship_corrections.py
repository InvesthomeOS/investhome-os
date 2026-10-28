"""Authorized CRM ownership and agent corrections.

Removes relationship rows only. Contacts, activities, notes, and documents stay.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.activity import ActivityAction, ActivityEntityType
from investhome_api.models.crm_agreement import (
    CrmAgreement,
    CrmAgreementParticipant,
    CrmAgreementStatus,
)
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType
from investhome_api.models.user_auth import User
from investhome_api.services.activity_service import log_activity

HUNDRED = Decimal("100.00")
CENT = Decimal("0.01")
AGENT_TYPES = {CrmContactType.BROKER, CrmContactType.REALTOR}


class RelationshipCorrectionError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def normalize_person_name(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.replace("ı", "i").replace("İ", "i").casefold()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text).split())


def normalize_unit(value: str | None) -> str:
    raw = (value or "").strip().casefold()
    digits = re.sub(r"\D", "", raw)
    if digits:
        return digits.lstrip("0") or "0"
    return raw


def _pct(value: Decimal | str | int | float) -> Decimal:
    try:
        number = Decimal(str(value)).quantize(CENT)
    except Exception as exc:
        raise RelationshipCorrectionError("invalid_percentage") from exc
    if number <= 0 or number > HUNDRED:
        raise RelationshipCorrectionError("invalid_percentage")
    return number


def _participants(db: Session, agreement_id: UUID) -> list[CrmAgreementParticipant]:
    return list(
        db.scalars(
            select(CrmAgreementParticipant)
            .where(CrmAgreementParticipant.agreement_id == agreement_id)
            .order_by(CrmAgreementParticipant.created_at.asc())
        ).all()
    )


def _contact_or_error(db: Session, contact_id: UUID) -> CrmContact:
    contact = db.get(CrmContact, contact_id)
    if contact is None:
        raise RelationshipCorrectionError("contact_not_found")
    return contact


def _agreement_or_error(db: Session, agreement_id: UUID) -> CrmAgreement:
    row = db.get(CrmAgreement, agreement_id)
    if row is None:
        raise RelationshipCorrectionError("agreement_not_found")
    return row


def _audit(
    db: Session,
    *,
    agreement: CrmAgreement | None,
    entity_id: UUID,
    entity_type: ActivityEntityType,
    action_type: str,
    actor: User | None,
    previous: dict[str, object],
    new: dict[str, object],
) -> None:
    log_activity(
        db,
        action=ActivityAction.UPDATED,
        entity_type=entity_type,
        entity_id=entity_id,
        description_key=f"crm.correction.{action_type}",
        actor_user=actor,
        metadata={
            "correction_action": action_type,
            "agreement_id": str(agreement.id) if agreement is not None else None,
        },
        changed_fields=["relationship"],
        previous_values=previous,
        new_values=new,
    )


def _snapshot(row: CrmAgreementParticipant, contact: CrmContact) -> dict[str, object]:
    return {
        "participant_id": str(row.id),
        "contact_id": str(contact.id),
        "display_name": contact.display_name,
        "ownership_pct": str(row.ownership_pct) if row.ownership_pct is not None else None,
        "is_primary": bool(row.is_primary),
        "role": row.role,
    }


def _sum_pct(rows: list[CrmAgreementParticipant]) -> Decimal:
    total = Decimal("0.00")
    for row in rows:
        if row.ownership_pct is not None:
            total += Decimal(row.ownership_pct)
    return total.quantize(CENT)


def add_agreement_owner(
    db: Session,
    agreement_id: UUID,
    contact_id: UUID,
    ownership_pct: Decimal | str,
    *,
    actor: User | None,
) -> CrmAgreementParticipant:
    agreement = _agreement_or_error(db, agreement_id)
    contact = _contact_or_error(db, contact_id)
    share = _pct(ownership_pct)
    rows = _participants(db, agreement_id)
    if any(row.contact_id == contact.id for row in rows):
        raise RelationshipCorrectionError("owner_already_linked")
    if _sum_pct(rows) + share > HUNDRED:
        raise RelationshipCorrectionError("invalid_percentage_total")
    row = CrmAgreementParticipant(
        agreement_id=agreement.id,
        contact_id=contact.id,
        role="owner",
        ownership_pct=share,
        is_primary=not rows,
        source="crm_correction",
    )
    db.add(row)
    db.flush()
    _audit(
        db,
        agreement=agreement,
        entity_id=agreement.id,
        entity_type=ActivityEntityType.CRM_AGREEMENT,
        action_type="ownership_added",
        actor=actor,
        previous={
            "owners": [_snapshot(item, _contact_or_error(db, item.contact_id)) for item in rows]
        },
        new={"owner": _snapshot(row, contact)},
    )
    return row


def remove_agreement_owner(
    db: Session,
    agreement_id: UUID,
    contact_id: UUID,
    *,
    actor: User | None,
    complete_remaining: bool = True,
) -> None:
    agreement = _agreement_or_error(db, agreement_id)
    contact = _contact_or_error(db, contact_id)
    rows = _participants(db, agreement_id)
    target = next((row for row in rows if row.contact_id == contact.id), None)
    if target is None:
        raise RelationshipCorrectionError("owner_not_linked")
    previous = _snapshot(target, contact)
    remaining = [row for row in rows if row.id != target.id]
    db.delete(target)
    db.flush()
    new_values: dict[str, object] = {
        "removed_contact_id": str(contact.id),
        "contact_preserved": True,
    }
    if len(remaining) == 1 and complete_remaining:
        keeper = remaining[0]
        old_pct = str(keeper.ownership_pct) if keeper.ownership_pct is not None else None
        keeper.ownership_pct = HUNDRED
        keeper.is_primary = True
        new_values["remaining_contact_id"] = str(keeper.contact_id)
        new_values["remaining_ownership_pct"] = str(HUNDRED)
        if old_pct != str(HUNDRED):
            _audit(
                db,
                agreement=agreement,
                entity_id=agreement.id,
                entity_type=ActivityEntityType.CRM_AGREEMENT,
                action_type="ownership_percentage_changed",
                actor=actor,
                previous={"contact_id": str(keeper.contact_id), "ownership_pct": old_pct},
                new={"contact_id": str(keeper.contact_id), "ownership_pct": str(HUNDRED)},
            )
    elif not remaining:
        meta = dict(agreement.metadata_json or {})
        meta["relationship_detached"] = True
        meta["detached_contact_id"] = str(contact.id)
        agreement.metadata_json = meta
        flag_modified(agreement, "metadata_json")
        if agreement.status != CrmAgreementStatus.CANCELLED:
            agreement.status = CrmAgreementStatus.CANCELLED
        new_values["relationship_detached"] = True
        _audit(
            db,
            agreement=agreement,
            entity_id=agreement.id,
            entity_type=ActivityEntityType.CRM_AGREEMENT,
            action_type="agreement_contact_unlinked",
            actor=actor,
            previous=previous,
            new={"contact_id": str(contact.id), "contact_preserved": True},
        )
    _audit(
        db,
        agreement=agreement,
        entity_id=agreement.id,
        entity_type=ActivityEntityType.CRM_AGREEMENT,
        action_type="ownership_removed",
        actor=actor,
        previous=previous,
        new=new_values,
    )


def set_ownership_percentages(
    db: Session,
    agreement_id: UUID,
    shares: list[tuple[UUID, Decimal | str]],
    *,
    actor: User | None,
) -> list[CrmAgreementParticipant]:
    agreement = _agreement_or_error(db, agreement_id)
    rows = _participants(db, agreement_id)
    incoming: dict[UUID, Decimal] = {}
    for contact_id, raw in shares:
        if contact_id in incoming:
            raise RelationshipCorrectionError("duplicate_owner")
        incoming[contact_id] = _pct(raw)
        _contact_or_error(db, contact_id)
    total = sum(incoming.values(), Decimal("0.00")).quantize(CENT)
    if total != HUNDRED:
        raise RelationshipCorrectionError("invalid_percentage_total")
    previous = {
        str(row.contact_id): str(row.ownership_pct) if row.ownership_pct is not None else None
        for row in rows
    }
    top = max(incoming.values())
    primary_id = next(contact_id for contact_id, share in incoming.items() if share == top)
    existing = {row.contact_id: row for row in rows}
    changed = set(existing) != set(incoming)
    for contact_id, share in incoming.items():
        row = existing.get(contact_id)
        if row is None:
            row = CrmAgreementParticipant(
                agreement_id=agreement.id,
                contact_id=contact_id,
                role="owner",
                ownership_pct=share,
                is_primary=contact_id == primary_id,
                source="crm_correction",
            )
            db.add(row)
            rows.append(row)
            changed = True
            continue
        if row.ownership_pct != share or row.is_primary != (contact_id == primary_id):
            changed = True
        row.ownership_pct = share
        row.is_primary = contact_id == primary_id
    for row in list(existing.values()):
        if row.contact_id in incoming:
            continue
        contact = _contact_or_error(db, row.contact_id)
        previous_owner = _snapshot(row, contact)
        db.delete(row)
        changed = True
        _audit(
            db,
            agreement=agreement,
            entity_id=agreement.id,
            entity_type=ActivityEntityType.CRM_AGREEMENT,
            action_type="ownership_removed",
            actor=actor,
            previous=previous_owner,
            new={"removed_contact_id": str(contact.id), "contact_preserved": True},
        )
    if changed:
        _audit(
            db,
            agreement=agreement,
            entity_id=agreement.id,
            entity_type=ActivityEntityType.CRM_AGREEMENT,
            action_type="ownership_percentage_changed",
            actor=actor,
            previous={"ownership_pct": previous},
            new={"ownership_pct": {str(key): str(value) for key, value in incoming.items()}},
        )
    db.flush()
    return rows


def change_agreement_unit(
    db: Session,
    agreement_id: UUID,
    unit_number: str,
    *,
    actor: User | None,
) -> str:
    """Replace the current unit on the same agreement. Contact and history stay."""
    agreement = _agreement_or_error(db, agreement_id)
    if agreement.project_group == "reit":
        raise RelationshipCorrectionError("unit_not_applicable")
    cleaned = " ".join(str(unit_number or "").split())
    if not cleaned or len(cleaned) > 40:
        raise RelationshipCorrectionError("invalid_unit")
    previous = agreement.unit_number
    if normalize_unit(previous) == normalize_unit(cleaned):
        return "unchanged"
    agreement.unit_number = cleaned
    meta = dict(agreement.metadata_json) if isinstance(agreement.metadata_json, dict) else {}
    fields = meta.get("agreement_fields")
    if isinstance(fields, dict):
        fields = dict(fields)
        fields["unit_number"] = cleaned
        meta["agreement_fields"] = fields
    meta["unit_number"] = cleaned
    history = meta.get("unit_change_history")
    if not isinstance(history, list):
        history = []
    history.append({"from_unit": previous, "to_unit": cleaned})
    meta["unit_change_history"] = history
    agreement.metadata_json = meta
    flag_modified(agreement, "metadata_json")
    _audit(
        db,
        agreement=agreement,
        entity_id=agreement.id,
        entity_type=ActivityEntityType.CRM_AGREEMENT,
        action_type="unit_changed",
        actor=actor,
        previous={"unit_number": previous},
        new={"unit_number": cleaned, "contact_preserved": True},
    )
    db.flush()
    return "changed"


def remove_duplicate_owner(
    db: Session,
    agreement_id: UUID,
    *,
    actor: User | None,
    normalized_name: str | None = None,
) -> str:
    agreement = _agreement_or_error(db, agreement_id)
    rows = _participants(db, agreement_id)
    contacts = {row.contact_id: _contact_or_error(db, row.contact_id) for row in rows}
    groups: dict[str, list[CrmAgreementParticipant]] = {}
    for row in rows:
        key = normalize_person_name(contacts[row.contact_id].display_name)
        if normalized_name and key != normalized_name:
            continue
        groups.setdefault(key, []).append(row)
    duplicates = [group for group in groups.values() if len(group) > 1]
    if normalized_name and not duplicates:
        return "no_duplicate"
    if len(duplicates) != 1:
        raise RelationshipCorrectionError("ambiguous_duplicate")
    group = duplicates[0]
    keeper = next((row for row in group if row.contact_id == agreement.contact_id), None)
    if keeper is None:
        primary = [row for row in group if row.is_primary]
        if len(primary) != 1:
            raise RelationshipCorrectionError("ambiguous_duplicate")
        keeper = primary[0]
    for row in group:
        if row.id == keeper.id:
            continue
        contact = contacts[row.contact_id]
        previous = _snapshot(row, contact)
        db.delete(row)
        db.flush()
        _audit(
            db,
            agreement=agreement,
            entity_id=agreement.id,
            entity_type=ActivityEntityType.CRM_AGREEMENT,
            action_type="duplicate_relationship_removed",
            actor=actor,
            previous=previous,
            new={
                "kept_contact_id": str(keeper.contact_id),
                "contact_preserved": True,
            },
        )
    return "removed"


def archive_agent(db: Session, contact_id: UUID, *, actor: User | None) -> str:
    contact = _contact_or_error(db, contact_id)
    if contact.contact_type not in AGENT_TYPES:
        raise RelationshipCorrectionError("not_agent")
    if contact.status == CrmContactStatus.ARCHIVED and contact.archived_at is not None:
        return "already_archived"
    previous_status = contact.status.value
    contact.status = CrmContactStatus.ARCHIVED
    contact.archived_at = datetime.now(UTC)
    _audit(
        db,
        agreement=None,
        entity_id=contact.id,
        entity_type=ActivityEntityType.CRM_CONTACT,
        action_type="agent_archived",
        actor=actor,
        previous={"status": previous_status, "display_name": contact.display_name},
        new={"status": contact.status.value, "contact_preserved": True},
    )
    db.flush()
    return "archived"


def restore_agent(db: Session, contact_id: UUID, *, actor: User | None) -> str:
    contact = _contact_or_error(db, contact_id)
    if contact.contact_type not in AGENT_TYPES:
        raise RelationshipCorrectionError("not_agent")
    if contact.status != CrmContactStatus.ARCHIVED:
        return "already_active"
    contact.status = CrmContactStatus.ACTIVE
    contact.archived_at = None
    _audit(
        db,
        agreement=None,
        entity_id=contact.id,
        entity_type=ActivityEntityType.CRM_CONTACT,
        action_type="agent_restored",
        actor=actor,
        previous={"status": CrmContactStatus.ARCHIVED.value, "display_name": contact.display_name},
        new={"status": contact.status.value},
    )
    db.flush()
    return "restored"
