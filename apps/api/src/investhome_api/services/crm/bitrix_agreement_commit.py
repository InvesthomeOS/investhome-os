"""Safe, idempotent Bitrix historical agreement commit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactBrokerProfile,
    CrmContactType,
    CrmContactTypeAssignment,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.bitrix_project_aliases import (
    BITRIX_PROJECT_GROUP_LABELS,
    BitrixProjectGroup,
    load_project_ids_by_name,
    resolve_project_alias,
)
from investhome_api.services.crm.bitrix_reit_membership import (
    detect_excluded_reit_source_ids,
    is_excluded_reit_source_id,
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

_SOURCE = "bitrix"
_LOCK_NAME = "investhome.crm.bitrix.agreement-commit"


class BitrixAgreementPreflightError(ValueError):
    pass


@dataclass
class SafeAgreementPlan:
    contact_id: UUID
    project_id: UUID | None
    project_group: str
    project_label: str
    source_external_id: str
    source_file: str
    source_row_identifier: str
    agreement_date: Any
    metadata_json: dict[str, Any]


@dataclass
class AgreementProjectResult:
    label: str
    safe_source_rows: int = 0
    agreements_created: int = 0
    agreements_reused: int = 0
    review_excluded: int = 0
    quarantine_excluded: int = 0
    project_id_resolved: bool = False


@dataclass
class SafeAgreementPlanSet:
    plans: list[SafeAgreementPlan]
    total_source_rows: int
    review_excluded: int
    quarantine_excluded: int
    unmatched_safe: int
    project_resolution_errors: int
    duplicate_source_rows: int
    by_project: dict[str, AgreementProjectResult]


@dataclass
class BitrixAgreementCommitResult:
    batch_identifier: str
    source_files: list[str]
    attempted: int
    contact_matches: int
    agreements_created: int
    agreements_reused: int
    skipped: int
    failed: int
    review_excluded: int
    quarantine_excluded: int
    duplicate_source_rows: int
    contacts_created_accidentally: int
    activities_created_accidentally: int
    agent_roles_created_accidentally: int
    broker_profiles_created_accidentally: int
    duplicate_agreements: int
    by_project: dict[str, dict[str, Any]]
    db_counts_before: dict[str, int]
    db_counts_after: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        return "\n".join(
            [
                "BITRIX SAFE AGREEMENT COMMIT",
                f"batch_identifier: {self.batch_identifier}",
                f"attempted: {self.attempted}",
                f"contact_matches: {self.contact_matches}",
                f"agreements_created: {self.agreements_created}",
                f"agreements_reused: {self.agreements_reused}",
                f"skipped: {self.skipped}",
                f"failed: {self.failed}",
                f"review_excluded: {self.review_excluded}",
                f"quarantine_excluded: {self.quarantine_excluded}",
                f"contacts_created_accidentally: {self.contacts_created_accidentally}",
                f"duplicate_agreements: {self.duplicate_agreements}",
            ]
        )


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }


def _agent_counts(db: Session) -> tuple[int, int]:
    assignments = db.query(CrmContactTypeAssignment).filter(
        CrmContactTypeAssignment.contact_type == CrmContactType.BROKER
    ).count()
    profiles = db.query(CrmContactBrokerProfile).count()
    return assignments, profiles


def _safe_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    return None


def _contact_external_ids(contact: CrmContact) -> set[str]:
    bitrix = (contact.metadata_json or {}).get("bitrix_import")
    if not isinstance(bitrix, dict):
        return set()
    values = bitrix.get("external_ids")
    if not isinstance(values, list):
        return set()
    return {str(value) for value in values if value}


def _row_contact_external_id(row: BitrixSourceRow) -> str | None:
    value = (row.bitrix_id or "").strip()
    return f"{row.source_file}:{value}" if value else None


def _stable_source_external_id(row: BitrixSourceRow) -> str:
    external = _row_contact_external_id(row)
    if external:
        return external[:120]
    digest = hashlib.sha256(
        json.dumps(
            {
                "source_file": row.source_file,
                "project_hint": row.project_hint,
                "phone": _safe_phone(row.phone),
                "email": normalize_valid_email(row.email),
                "agreement_date": row.agreement_date,
                "extra": row.extra,
            },
            sort_keys=True,
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"{row.source_file[:40]}:sha256:{digest[:48]}"


def _agreement_metadata(
    row: BitrixSourceRow,
    *,
    project_group: str,
    project_label: str,
    source_external_id: str,
) -> dict[str, Any]:
    return {
        "version": 1,
        "source": "Bitrix",
        "imported_historical_agreement": True,
        "source_file": row.source_file,
        "source_row_identifier": (row.bitrix_id or "").strip() or source_external_id,
        "project_group": project_group,
        "project_label": project_label,
        "source_data": row.extra,
    }


def _project_results() -> dict[str, AgreementProjectResult]:
    return {
        group.value: AgreementProjectResult(
            label=label,
            project_id_resolved=False,
        )
        for group, label in BITRIX_PROJECT_GROUP_LABELS.items()
    }


def _approved_agreement_classification(
    db: Session,
    bundle: BitrixBundle,
) -> dict[int, str]:
    """Reproduce the approved Phase 4B source-order safety boundary."""
    audit_index = IdentityIndex()
    for contact in db.scalars(select(CrmContact)).all():
        if isinstance((contact.metadata_json or {}).get("bitrix_import"), dict):
            continue
        audit_index.add(
            IdentityRecord(
                key=f"db:{contact.id}",
                display_name=contact.display_name,
                phone=parse_phone(contact.primary_phone),
                email=normalize_valid_email(contact.primary_email),
                name_key=normalize_full_name(contact.display_name),
                origin="crm",
                contact_id=contact.id,
            )
        )

    classifications: dict[int, str] = {}
    ordered_rows = [
        *[row for row in bundle.rows if row.role in {"active_customers", "junk"}],
        *[row for row in bundle.rows if row.role == "agents"],
        *[row for row in bundle.rows if row.role == "agreements"],
    ]
    for sequence, row in enumerate(ordered_rows):
        phone = _safe_phone(row.phone)
        email = normalize_valid_email(row.email)
        parsed_phone = parse_phone(row.phone)
        if not phone and not email:
            if row.role == "agreements":
                classifications[id(row)] = (
                    "review" if parsed_phone and parsed_phone.suspicious else "quarantine"
                )
            continue
        match = audit_index.match(row.phone, row.email, row.full_name)
        record = IdentityRecord(
            key=f"source:{sequence}",
            display_name=(row.full_name or "").strip() or "(unnamed)",
            phone=parse_phone(phone),
            email=email,
            name_key=normalize_full_name(row.full_name),
            origin=row.role,
        )
        if row.role == "agreements":
            classifications[id(row)] = (
                "review" if match.kind == IdentityMatchKind.AMBIGUOUS else "safe"
            )
        audit_index.add(record)
    return classifications


def build_safe_agreement_plans(db: Session, bundle: BitrixBundle) -> SafeAgreementPlanSet:
    index = IdentityIndex()
    external_index: dict[str, set[UUID]] = {}
    for contact in db.scalars(select(CrmContact)).all():
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
        for external_id in _contact_external_ids(contact):
            external_index.setdefault(external_id, set()).add(contact.id)

    projects = load_project_ids_by_name(db)
    approved_classification = _approved_agreement_classification(db, bundle)
    by_project = _project_results()
    candidates: list[SafeAgreementPlan] = []
    review = quarantine = unmatched = project_errors = 0
    total = 0
    source_key_counts: dict[str, int] = {}

    excluded_reit, _ = detect_excluded_reit_source_ids(bundle)

    for row in bundle.rows:
        if row.role != "agreements":
            continue
        total += 1
        if is_excluded_reit_source_id(_stable_source_external_id(row), excluded_reit):
            continue
        resolution = resolve_project_alias(
            row.project_hint or row.source_file,
            project_ids_by_name=projects,
        )
        if resolution.group is None or resolution.label is None:
            project_errors += 1
            review += 1
            continue
        project_result = by_project[resolution.group.value]
        project_result.project_id_resolved = resolution.project_id is not None
        if resolution.group != BitrixProjectGroup.REIT and resolution.project_id is None:
            project_errors += 1
            project_result.review_excluded += 1
            review += 1
            continue

        approved = approved_classification.get(id(row), "quarantine")
        if approved == "review":
            review += 1
            project_result.review_excluded += 1
            continue
        if approved == "quarantine":
            quarantine += 1
            project_result.quarantine_excluded += 1
            continue

        safe_phone = _safe_phone(row.phone)
        safe_email = normalize_valid_email(row.email)
        external_id = _row_contact_external_id(row)
        external_hits = external_index.get(external_id, set()) if external_id else set()
        match = index.match(row.phone, row.email, row.full_name)
        contact_id: UUID | None = None
        if match.kind in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL} and match.record:
            contact_id = match.record.contact_id
            if external_hits and contact_id not in external_hits:
                contact_id = None
                review += 1
                project_result.review_excluded += 1
                continue
        elif match.kind == IdentityMatchKind.AMBIGUOUS or len(external_hits) > 1:
            review += 1
            project_result.review_excluded += 1
            continue
        elif len(external_hits) == 1:
            contact_id = next(iter(external_hits))
        elif safe_phone or safe_email:
            unmatched += 1
            project_result.review_excluded += 1
            continue
        else:
            quarantine += 1
            project_result.quarantine_excluded += 1
            continue

        if contact_id is None:
            quarantine += 1
            project_result.quarantine_excluded += 1
            continue
        source_external_id = _stable_source_external_id(row)
        source_key_counts[source_external_id] = source_key_counts.get(source_external_id, 0) + 1
        candidates.append(
            SafeAgreementPlan(
                contact_id=contact_id,
                project_id=resolution.project_id,
                project_group=resolution.group.value,
                project_label=resolution.label,
                source_external_id=source_external_id,
                source_file=row.source_file,
                source_row_identifier=(row.bitrix_id or "").strip() or source_external_id,
                agreement_date=row.agreement_date,
                metadata_json=_agreement_metadata(
                    row,
                    project_group=resolution.group.value,
                    project_label=resolution.label,
                    source_external_id=source_external_id,
                ),
            )
        )

    duplicate_keys = {key for key, count in source_key_counts.items() if count > 1}
    plans: list[SafeAgreementPlan] = []
    duplicate_rows = 0
    for plan in candidates:
        if plan.source_external_id in duplicate_keys:
            duplicate_rows += 1
            review += 1
            by_project[plan.project_group].review_excluded += 1
            continue
        plans.append(plan)
        by_project[plan.project_group].safe_source_rows += 1

    return SafeAgreementPlanSet(
        plans=plans,
        total_source_rows=total,
        review_excluded=review,
        quarantine_excluded=quarantine,
        unmatched_safe=unmatched,
        project_resolution_errors=project_errors,
        duplicate_source_rows=duplicate_rows,
        by_project=by_project,
    )


def _batch_identifier(plans: list[SafeAgreementPlan]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            sorted(plan.source_external_id for plan in plans),
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"bitrix-agreements-{digest[:16]}"


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def commit_safe_agreements(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User,
) -> BitrixAgreementCommitResult:
    if not user_has_permission(actor, "crm", "import", db=db):
        raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    agent_before = _agent_counts(db)
    plan_set = build_safe_agreement_plans(db, bundle)
    if plan_set.unmatched_safe:
        raise BitrixAgreementPreflightError(
            "a safe agreement identity did not match an existing canonical contact"
        )
    if plan_set.project_resolution_errors:
        raise BitrixAgreementPreflightError(
            "every agreement file must resolve through an explicit canonical project alias"
        )

    existing = {
        row.source_external_id: row
        for row in db.scalars(
            select(CrmAgreement).where(
                CrmAgreement.source == _SOURCE,
                CrmAgreement.source_external_id.in_(
                    [plan.source_external_id for plan in plan_set.plans]
                ),
            )
        ).all()
    }
    created = reused = 0
    with db.begin_nested():
        _acquire_lock(db)
        for plan in plan_set.plans:
            agreement = existing.get(plan.source_external_id)
            if agreement is not None:
                if (
                    agreement.contact_id != plan.contact_id
                    or agreement.project_id != plan.project_id
                    or agreement.project_group != plan.project_group
                ):
                    raise BitrixAgreementPreflightError(
                        "existing imported agreement conflicts with the safe source plan"
                    )
                reused += 1
                plan_set.by_project[plan.project_group].agreements_reused += 1
                continue
            db.add(
                CrmAgreement(
                    contact_id=plan.contact_id,
                    project_id=plan.project_id,
                    project_group=plan.project_group,
                    source=_SOURCE,
                    source_external_id=plan.source_external_id,
                    status=CrmAgreementStatus.UNKNOWN,
                    agreement_date=plan.agreement_date,
                    metadata_json=plan.metadata_json,
                )
            )
            created += 1
            plan_set.by_project[plan.project_group].agreements_created += 1
        db.flush()

    after = _db_counts(db)
    agent_after = _agent_counts(db)
    contacts_delta = after["crm_contacts"] - before["crm_contacts"]
    activities_delta = after["crm_activities"] - before["crm_activities"]
    agreement_delta = after["crm_agreements"] - before["crm_agreements"]
    role_delta = agent_after[0] - agent_before[0]
    profile_delta = agent_after[1] - agent_before[1]
    if (
        contacts_delta
        or activities_delta
        or role_delta
        or profile_delta
        or agreement_delta != created
    ):
        raise BitrixAgreementPreflightError(
            "post-write agreement safety verification failed; transaction must be rolled back"
        )

    duplicate_agreements = (
        db.query(CrmAgreement).filter(CrmAgreement.source == _SOURCE).count()
        - db.query(CrmAgreement.source_external_id)
        .filter(CrmAgreement.source == _SOURCE)
        .distinct()
        .count()
    )
    if duplicate_agreements:
        raise BitrixAgreementPreflightError("duplicate imported agreement identities detected")

    return BitrixAgreementCommitResult(
        batch_identifier=_batch_identifier(plan_set.plans),
        source_files=sorted({plan.source_file for plan in plan_set.plans}),
        attempted=len(plan_set.plans),
        contact_matches=len(plan_set.plans),
        agreements_created=created,
        agreements_reused=reused,
        skipped=reused,
        failed=0,
        review_excluded=plan_set.review_excluded,
        quarantine_excluded=plan_set.quarantine_excluded,
        duplicate_source_rows=plan_set.duplicate_source_rows,
        contacts_created_accidentally=contacts_delta,
        activities_created_accidentally=activities_delta,
        agent_roles_created_accidentally=role_delta,
        broker_profiles_created_accidentally=profile_delta,
        duplicate_agreements=duplicate_agreements,
        by_project={
            key: asdict(value)
            for key, value in plan_set.by_project.items()
        },
        db_counts_before=before,
        db_counts_after=after,
    )
