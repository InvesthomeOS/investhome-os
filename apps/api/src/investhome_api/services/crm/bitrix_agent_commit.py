"""Safe, idempotent Bitrix Acentalar role/profile enrichment."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactBrokerProfile,
    CrmContactStatus,
    CrmContactType,
    CrmContactTypeAssignment,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_import import BitrixBundle
from investhome_api.services.crm.identity import (
    IdentityIndex,
    IdentityMatchKind,
    IdentityRecord,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
)
from investhome_api.services.permission_service import user_has_permission

_LOCK_NAME = "investhome.crm.bitrix.agent-role-commit"
_METADATA_KEY = "bitrix_agent"


class BitrixAgentPreflightError(ValueError):
    pass


@dataclass
class SafeAgentPlan:
    contact_id: UUID
    external_ids: set[str] = field(default_factory=set)
    source_files: set[str] = field(default_factory=set)


@dataclass
class SafeAgentPlanSet:
    plans: list[SafeAgentPlan]
    safe_source_rows: int
    duplicate_source_rows: int
    quarantine_excluded: int
    review_excluded: int
    unmatched_safe: int


@dataclass
class BitrixAgentCommitResult:
    batch_identifier: str
    source_files: list[str]
    attempted: int
    contacts_matched: int
    role_type_additions: int
    broker_profiles_created: int
    broker_profiles_reused: int
    agent_statuses_active: int
    status_updates: int
    skipped: int
    failed: int
    duplicate_source_rows: int
    quarantine_excluded: int
    review_excluded: int
    contacts_created_accidentally: int
    activities_created_accidentally: int
    agreements_created_accidentally: int
    duplicate_agent_rows: int
    db_counts_before: dict[str, int]
    db_counts_after: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        return "\n".join(
            [
                "BITRIX SAFE AGENT ROLE COMMIT",
                f"batch_identifier: {self.batch_identifier}",
                f"attempted: {self.attempted}",
                f"contacts_matched: {self.contacts_matched}",
                f"role_type_additions: {self.role_type_additions}",
                f"broker_profiles_created: {self.broker_profiles_created}",
                f"broker_profiles_reused: {self.broker_profiles_reused}",
                f"agent_statuses_active: {self.agent_statuses_active}",
                f"status_updates: {self.status_updates}",
                f"skipped: {self.skipped}",
                f"failed: {self.failed}",
                f"quarantine_excluded: {self.quarantine_excluded}",
                f"contacts_created_accidentally: {self.contacts_created_accidentally}",
            ]
        )


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }


def _safe_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    return None


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def build_safe_agent_plans(db: Session, bundle: BitrixBundle) -> SafeAgentPlanSet:
    index = IdentityIndex()
    contacts = list(
        db.scalars(
            select(CrmContact).options(selectinload(CrmContact.type_assignments))
        ).all()
    )
    for contact in contacts:
        index.add(
            IdentityRecord(
                key=str(contact.id),
                display_name=contact.display_name,
                phone=parse_phone(contact.primary_phone),
                email=normalize_valid_email(contact.primary_email),
                name_key=normalize_full_name(contact.display_name),
                origin="crm",
                contact_id=contact.id,
            )
        )

    plans: dict[UUID, SafeAgentPlan] = {}
    order: list[UUID] = []
    safe_rows = quarantine = review = unmatched = 0
    for row in bundle.rows:
        if row.role != "agents":
            continue
        phone = _safe_phone(row.phone)
        email = normalize_valid_email(row.email)
        if not phone and not email:
            quarantine += 1
            continue
        match = index.match(row.phone, row.email, row.full_name)
        if match.kind == IdentityMatchKind.AMBIGUOUS:
            review += 1
            continue
        if (
            match.kind not in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL}
            or match.record is None
            or match.record.contact_id is None
        ):
            unmatched += 1
            continue
        safe_rows += 1
        contact_id = match.record.contact_id
        plan = plans.get(contact_id)
        if plan is None:
            plan = SafeAgentPlan(contact_id=contact_id)
            plans[contact_id] = plan
            order.append(contact_id)
        plan.source_files.add(row.source_file)
        if row.bitrix_id and row.bitrix_id.strip():
            plan.external_ids.add(f"{row.source_file}:{row.bitrix_id.strip()}")

    return SafeAgentPlanSet(
        plans=[plans[contact_id] for contact_id in order],
        safe_source_rows=safe_rows,
        duplicate_source_rows=safe_rows - len(plans),
        quarantine_excluded=quarantine,
        review_excluded=review,
        unmatched_safe=unmatched,
    )


def _agent_metadata(plan: SafeAgentPlan) -> dict[str, Any]:
    return {
        "version": 1,
        "source": "Bitrix",
        "section": "Acentalar",
        "status": "active",
        "source_files": sorted(plan.source_files),
        "external_ids": sorted(plan.external_ids),
    }


def _enrich_agent(
    db: Session,
    contact: CrmContact,
    plan: SafeAgentPlan,
) -> tuple[int, int, int, int, bool]:
    changed = False
    role_additions = profile_created = profile_reused = status_updates = 0
    existing_types = {assignment.contact_type for assignment in contact.type_assignments}
    if not existing_types:
        contact.type_assignments.append(
            CrmContactTypeAssignment(
                contact_type=contact.contact_type,
                is_primary=True,
            )
        )
        existing_types.add(contact.contact_type)
        changed = True
    if CrmContactType.BROKER not in existing_types:
        contact.type_assignments.append(
            CrmContactTypeAssignment(
                contact_type=CrmContactType.BROKER,
                is_primary=False,
            )
        )
        role_additions = 1
        changed = True

    if contact.broker_profile is None:
        contact.broker_profile = CrmContactBrokerProfile(contact_id=contact.id)
        profile_created = 1
        changed = True
    else:
        profile_reused = 1

    if contact.status != CrmContactStatus.ACTIVE:
        contact.status = CrmContactStatus.ACTIVE
        status_updates = 1
        changed = True

    metadata = dict(contact.metadata_json or {})
    agent_metadata = _agent_metadata(plan)
    if metadata.get(_METADATA_KEY) != agent_metadata:
        metadata[_METADATA_KEY] = agent_metadata
        contact.metadata_json = metadata
        changed = True
    if changed:
        db.flush()
    return role_additions, profile_created, profile_reused, status_updates, changed


def _batch_identifier(plans: list[SafeAgentPlan]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            [str(plan.contact_id) for plan in plans],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"bitrix-agents-{digest[:16]}"


def commit_safe_agent_roles(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User,
) -> BitrixAgentCommitResult:
    if not user_has_permission(actor, "crm", "import"):
        raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    plan_set = build_safe_agent_plans(db, bundle)
    if plan_set.unmatched_safe or plan_set.review_excluded:
        raise BitrixAgentPreflightError(
            "all safe agent identities must deterministically match one existing contact"
        )

    role_additions = profiles_created = profiles_reused = status_updates = skipped = 0
    with db.begin_nested():
        _acquire_lock(db)
        for plan in plan_set.plans:
            contact = db.scalar(
                select(CrmContact)
                .where(CrmContact.id == plan.contact_id)
                .options(
                    selectinload(CrmContact.type_assignments),
                    selectinload(CrmContact.broker_profile),
                )
            )
            if contact is None:
                raise BitrixAgentPreflightError("matched agent contact disappeared")
            added, created, reused, status_changed, changed = _enrich_agent(db, contact, plan)
            role_additions += added
            profiles_created += created
            profiles_reused += reused
            status_updates += status_changed
            skipped += int(not changed)
        db.flush()

    after = _db_counts(db)
    contacts_delta = after["crm_contacts"] - before["crm_contacts"]
    activities_delta = after["crm_activities"] - before["crm_activities"]
    agreements_delta = after["crm_agreements"] - before["crm_agreements"]
    agent_rows = list(
        db.scalars(
            select(CrmContactTypeAssignment).where(
                CrmContactTypeAssignment.contact_id.in_(
                    [plan.contact_id for plan in plan_set.plans]
                ),
                CrmContactTypeAssignment.contact_type == CrmContactType.BROKER,
            )
        ).all()
    )
    duplicate_agent_rows = len(agent_rows) - len({row.contact_id for row in agent_rows})
    if contacts_delta or activities_delta or agreements_delta or duplicate_agent_rows:
        raise BitrixAgentPreflightError(
            "post-write agent safety verification failed; transaction must be rolled back"
        )

    return BitrixAgentCommitResult(
        batch_identifier=_batch_identifier(plan_set.plans),
        source_files=sorted(
            {source_file for plan in plan_set.plans for source_file in plan.source_files}
        ),
        attempted=len(plan_set.plans),
        contacts_matched=len(plan_set.plans),
        role_type_additions=role_additions,
        broker_profiles_created=profiles_created,
        broker_profiles_reused=profiles_reused,
        agent_statuses_active=len(plan_set.plans),
        status_updates=status_updates,
        skipped=skipped,
        failed=0,
        duplicate_source_rows=plan_set.duplicate_source_rows,
        quarantine_excluded=plan_set.quarantine_excluded,
        review_excluded=plan_set.review_excluded,
        contacts_created_accidentally=contacts_delta,
        activities_created_accidentally=activities_delta,
        agreements_created_accidentally=agreements_delta,
        duplicate_agent_rows=duplicate_agent_rows,
        db_counts_before=before,
        db_counts_after=after,
    )
