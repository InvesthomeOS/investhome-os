"""Transactional, safe-only Bitrix contact commit engine.

Only deterministic contact identities are writable here. Agent and agreement
rows may contribute a plain canonical contact, but this engine never writes
agent roles/profiles, agreements, comments, name-only rows, suspicious phones,
or no-identity rows.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_import import (
    BITRIX_SOURCE,
    MAIN_CONTACT_ROLES,
    BitrixBundle,
    BitrixSourceRow,
)
from investhome_api.services.crm.identity import (
    IdentityIndex,
    IdentityMatchKind,
    IdentityRecord,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
)
from investhome_api.services.permission_service import user_has_permission

_LOCK_NAME = "investhome.crm.bitrix.safe-contact-commit"
_METADATA_KEY = "bitrix_import"


class BitrixCommitPermissionError(PermissionError):
    pass


class BitrixCommitConflictError(ValueError):
    pass


@dataclass
class SafeContactPlan:
    key: str
    display_name: str
    phone: str | None
    email: str | None
    status: str
    existing_id: UUID | None = None
    source_rows: list[dict[str, Any]] = field(default_factory=list)
    external_ids: set[str] = field(default_factory=set)
    source_files: set[str] = field(default_factory=set)
    source_roles: set[str] = field(default_factory=set)
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    warning_flags: set[str] = field(default_factory=set)
    _selected_name_role: str = "junk"

    def apply(self, row: BitrixSourceRow, *, phone: str | None, email: str | None) -> None:
        role = row.role
        external_id = (row.bitrix_id or "").strip() or None
        source_name = (row.full_name or "").strip() or None
        self.source_files.add(row.source_file)
        self.source_roles.add(role)
        if external_id:
            self.external_ids.add(f"{row.source_file}:{external_id}")

        source = {
            "source_file": row.source_file,
            "role": role,
            "external_id": external_id,
            "display_name": source_name,
            "phone": (row.phone or "").strip() or None,
            "email": (row.email or "").strip() or None,
        }
        if source not in self.source_rows:
            self.source_rows.append(source)

        if source_name and source_name != self.display_name:
            self._record_conflict("display_name", self.display_name, source_name, row)
            if role == "active_customers" and self._selected_name_role != "active_customers":
                self.display_name = source_name
                self._selected_name_role = role
        if phone:
            if not self.phone:
                self.phone = phone
            elif self.phone != phone:
                self._record_conflict("phone", self.phone, phone, row)
        if email:
            if not self.email:
                self.email = email
            elif self.email != email:
                self._record_conflict("email", self.email, email, row)
        if role in {"active_customers", "agents"}:
            self.status = CrmContactStatus.ACTIVE.value
            if role == "active_customers":
                self._selected_name_role = role

    def _record_conflict(
        self,
        field_name: str,
        kept: str,
        observed: str,
        row: BitrixSourceRow,
    ) -> None:
        conflict = {
            "field": field_name,
            "kept": kept,
            "observed": observed,
            "source_file": row.source_file,
            "external_id": (row.bitrix_id or "").strip() or None,
        }
        if conflict not in self.conflicts:
            self.conflicts.append(conflict)


@dataclass
class SafeContactPlanSet:
    plans: list[SafeContactPlan]
    safe_rows: int
    safely_collapsed_rows: int
    review_excluded: int
    quarantine_excluded: int
    suspicious_phone_excluded: int
    ambiguous_excluded: int
    name_collision_warnings: int


@dataclass
class BitrixCommitResult:
    batch_identifier: str
    source_files: list[str]
    attempted: int
    created: int
    updated: int
    skipped: int
    failed: int
    review_excluded: int
    quarantine_excluded: int
    db_counts_before: dict[str, int]
    db_counts_after: dict[str, int]
    selected_safe_pool: int
    duplicate_contacts_created: int = 0
    review_or_quarantine_written: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        return "\n".join(
            [
                "BITRIX SAFE CONTACT COMMIT",
                f"batch_identifier: {self.batch_identifier}",
                f"source_files: {len(self.source_files)}",
                f"attempted: {self.attempted}",
                f"created: {self.created}",
                f"updated: {self.updated}",
                f"skipped: {self.skipped}",
                f"failed: {self.failed}",
                f"review_excluded: {self.review_excluded}",
                f"quarantine_excluded: {self.quarantine_excluded}",
                f"duplicate_contacts_created: {self.duplicate_contacts_created}",
                f"review_or_quarantine_written: {self.review_or_quarantine_written}",
            ]
        )


def _safe_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    return None


def _metadata_external_ids(contact: CrmContact) -> set[str]:
    metadata = contact.metadata_json or {}
    bitrix = metadata.get(_METADATA_KEY)
    if not isinstance(bitrix, dict):
        return set()
    values = bitrix.get("external_ids")
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if value}


def _db_counts(db: Session) -> dict[str, int]:
    from investhome_api.models.crm_activity import CrmActivity
    from investhome_api.models.crm_agreement import CrmAgreement

    return {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }


def _acquire_commit_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def build_safe_contact_plans(db: Session, bundle: BitrixBundle) -> SafeContactPlanSet:
    """Build all safe contact-identity plans without mutating the session."""
    existing = list(db.scalars(select(CrmContact)).all())
    phone_index: dict[str, set[str]] = {}
    email_index: dict[str, set[str]] = {}
    external_index: dict[str, set[str]] = {}
    plans: dict[str, SafeContactPlan] = {}
    order: list[str] = []
    audit_index = IdentityIndex()

    def add_index(index: dict[str, set[str]], value: str | None, key: str) -> None:
        if value:
            index.setdefault(value, set()).add(key)

    for contact in existing:
        key = f"db:{contact.id}"
        phone = _safe_phone(contact.primary_phone)
        email = normalize_valid_email(contact.primary_email)
        add_index(phone_index, phone, key)
        add_index(email_index, email, key)
        for external_id in _metadata_external_ids(contact):
            add_index(external_index, external_id, key)
        plans[key] = SafeContactPlan(
            key=key,
            display_name=contact.display_name,
            phone=phone,
            email=email,
            status=contact.status.value,
            existing_id=contact.id,
        )
        if not isinstance((contact.metadata_json or {}).get(_METADATA_KEY), dict):
            audit_index.add(
                IdentityRecord(
                    key=key,
                    display_name=contact.display_name,
                    phone=parse_phone(phone),
                    email=email,
                    name_key=normalize_full_name(contact.display_name),
                    origin="os",
                    contact_id=contact.id,
                )
            )

    safe_rows = 0
    review_excluded = 0
    quarantine_excluded = 0
    suspicious_excluded = 0
    ambiguous_excluded = 0
    name_to_keys: dict[str, set[str]] = {}

    contact_rows = [
        *[item for item in bundle.rows if item.role in MAIN_CONTACT_ROLES],
        *[item for item in bundle.rows if item.role == "agents"],
        *[item for item in bundle.rows if item.role == "agreements"],
    ]
    for row in contact_rows:
        parsed_phone = parse_phone(row.phone)
        phone = _safe_phone(row.phone)
        email = normalize_valid_email(row.email)
        if not phone and not email:
            if parsed_phone and parsed_phone.suspicious:
                suspicious_excluded += 1
                review_excluded += 1
            else:
                quarantine_excluded += 1
            continue

        audit_match = audit_index.match(row.phone, row.email, row.full_name)
        audit_record = IdentityRecord(
            key=f"source:{len(audit_index.records)}",
            display_name=(row.full_name or "").strip() or "(unnamed)",
            phone=parse_phone(phone),
            email=email,
            name_key=normalize_full_name(row.full_name),
            origin=row.role,
        )
        if row.role == "agreements" and audit_match.kind == IdentityMatchKind.AMBIGUOUS:
            ambiguous_excluded += 1
            review_excluded += 1
            audit_index.add(audit_record)
            continue

        phone_hits = phone_index.get(phone, set()) if phone else set()
        email_hits = email_index.get(email, set()) if email else set()
        external_ref = (
            f"{row.source_file}:{row.bitrix_id.strip()}"
            if row.bitrix_id and row.bitrix_id.strip()
            else None
        )
        external_hits = external_index.get(external_ref, set()) if external_ref else set()
        all_hits = phone_hits | email_hits | external_hits
        if (
            len(phone_hits) > 1
            or len(email_hits) > 1
            or len(external_hits) > 1
            or len(all_hits) > 1
        ):
            ambiguous_excluded += 1
            review_excluded += 1
            continue

        key = next(iter(phone_hits or email_hits or external_hits), None)
        if key is None:
            key = f"new:{len(order) + 1}"
            display_name = (row.full_name or "").strip() or "Bitrix Contact"
            plans[key] = SafeContactPlan(
                key=key,
                display_name=display_name,
                phone=phone,
                email=email,
                status=(
                    CrmContactStatus.ACTIVE.value
                    if row.role in {"active_customers", "agents", "agreements"}
                    else CrmContactStatus.ARCHIVED.value
                ),
                _selected_name_role=row.role,
            )
            order.append(key)
        elif key not in order:
            order.append(key)

        plan = plans[key]
        plan.apply(row, phone=phone, email=email)
        safe_rows += 1
        add_index(phone_index, phone, key)
        add_index(email_index, email, key)
        add_index(external_index, external_ref, key)
        name_key = normalize_full_name(row.full_name)
        if name_key:
            name_to_keys.setdefault(name_key, set()).add(key)
        audit_index.add(audit_record)

    warning_count = 0
    for keys in name_to_keys.values():
        if len(keys) < 2:
            continue
        for key in keys:
            plans[key].warning_flags.add("same_name_deterministic_collision")
            warning_count += 1

    selected_plans = [plans[key] for key in order]
    return SafeContactPlanSet(
        plans=selected_plans,
        safe_rows=safe_rows,
        safely_collapsed_rows=safe_rows - len(selected_plans),
        review_excluded=review_excluded,
        quarantine_excluded=quarantine_excluded,
        suspicious_phone_excluded=suspicious_excluded,
        ambiguous_excluded=ambiguous_excluded,
        name_collision_warnings=warning_count,
    )


def _bitrix_metadata(plan: SafeContactPlan) -> dict[str, Any]:
    return {
        "version": 1,
        "external_ids": sorted(plan.external_ids),
        "source_files": sorted(plan.source_files),
        "source_roles": sorted(plan.source_roles),
        "historical_junk": "junk" in plan.source_roles,
        "sources": sorted(
            plan.source_rows,
            key=lambda item: (
                str(item.get("source_file") or ""),
                str(item.get("external_id") or ""),
            ),
        ),
        "conflicts": plan.conflicts,
        "warning_flags": sorted(plan.warning_flags),
    }


def _apply_plan(db: Session, plan: SafeContactPlan) -> str:
    metadata = _bitrix_metadata(plan)
    if plan.existing_id is None:
        contact = CrmContact(
            contact_type=CrmContactType.PROSPECT,
            record_kind=CrmRecordKind.PERSON,
            display_name=plan.display_name,
            primary_phone=plan.phone,
            primary_email=plan.email,
            lifecycle_stage=CrmLifecycleStage.NEW,
            source="Bitrix",
            status=CrmContactStatus(plan.status),
            metadata_json={_METADATA_KEY: metadata},
        )
        db.add(contact)
        db.flush()
        plan.existing_id = contact.id
        return "created"

    contact = db.get(CrmContact, plan.existing_id)
    if contact is None:
        raise BitrixCommitConflictError("planned existing contact disappeared")
    changed = False
    if not contact.primary_phone and plan.phone:
        contact.primary_phone = plan.phone
        changed = True
    if not contact.primary_email and plan.email:
        contact.primary_email = plan.email
        changed = True
    if contact.source is None:
        contact.source = "Bitrix"
        changed = True
    desired_status = CrmContactStatus(plan.status)
    if contact.status != desired_status:
        contact.status = desired_status
        changed = True
    merged_metadata = dict(contact.metadata_json or {})
    if merged_metadata.get(_METADATA_KEY) != metadata:
        merged_metadata[_METADATA_KEY] = metadata
        contact.metadata_json = merged_metadata
        changed = True
    if changed:
        db.flush()
        return "updated"
    return "skipped"


def _batch_identifier(plans: list[SafeContactPlan]) -> str:
    digest_payload = [
        {
            "phone": plan.phone,
            "email": plan.email,
            "external_ids": sorted(plan.external_ids),
        }
        for plan in plans
    ]
    digest = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"bitrix-safe-{digest[:16]}"


def _verify_selected_contacts(
    db: Session,
    plans: list[SafeContactPlan],
) -> tuple[int, int]:
    contacts = list(db.scalars(select(CrmContact)).all())
    phones: dict[str, set[UUID]] = {}
    emails: dict[str, set[UUID]] = {}
    for contact in contacts:
        phone = _safe_phone(contact.primary_phone)
        email = normalize_valid_email(contact.primary_email)
        if phone:
            phones.setdefault(phone, set()).add(contact.id)
        if email:
            emails.setdefault(email, set()).add(contact.id)

    duplicate_plan_keys = 0
    unsafe_written = 0
    for plan in plans:
        contact = db.get(CrmContact, plan.existing_id) if plan.existing_id else None
        if contact is None:
            unsafe_written += 1
            continue
        phone = _safe_phone(contact.primary_phone)
        email = normalize_valid_email(contact.primary_email)
        if not phone and not email:
            unsafe_written += 1
        matched_ids = set()
        if plan.phone:
            matched_ids.update(phones.get(plan.phone, set()))
        if plan.email:
            matched_ids.update(emails.get(plan.email, set()))
        if len(matched_ids) > 1:
            duplicate_plan_keys += 1
    return duplicate_plan_keys, unsafe_written


def commit_safe_bitrix_contacts(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User,
    limit: int,
    offset: int = 0,
) -> BitrixCommitResult:
    """Commit one safe contact batch in a rollback-safe transaction."""
    if not user_has_permission(actor, "crm", "import"):
        raise BitrixCommitPermissionError("crm.import permission required")
    if limit < 1 or limit > 1_000:
        raise ValueError("limit must be between 1 and 1000")
    if offset < 0:
        raise ValueError("offset must not be negative")

    before = _db_counts(db)
    plan_set = build_safe_contact_plans(db, bundle)
    selected = plan_set.plans[offset : offset + limit]
    created = updated = skipped = failed = 0

    with db.begin_nested():
        _acquire_commit_lock(db)
        for plan in selected:
            outcome = _apply_plan(db, plan)
            if outcome == "created":
                created += 1
            elif outcome == "updated":
                updated += 1
            else:
                skipped += 1
        db.flush()

    after = _db_counts(db)
    duplicate_contacts, unsafe_written = _verify_selected_contacts(db, selected)
    if duplicate_contacts or unsafe_written:
        raise BitrixCommitConflictError(
            "post-write safety verification failed; transaction must be rolled back"
        )
    return BitrixCommitResult(
        batch_identifier=_batch_identifier(selected),
        source_files=sorted(
            {source for plan in selected for source in plan.source_files}
        ),
        attempted=len(selected),
        created=created,
        updated=updated,
        skipped=skipped,
        failed=failed,
        review_excluded=plan_set.review_excluded,
        quarantine_excluded=plan_set.quarantine_excluded,
        db_counts_before=before,
        db_counts_after=after,
        selected_safe_pool=len(plan_set.plans),
        duplicate_contacts_created=duplicate_contacts,
        review_or_quarantine_written=unsafe_written,
    )
