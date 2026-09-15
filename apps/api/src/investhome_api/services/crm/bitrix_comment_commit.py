"""Safe, idempotent Bitrix historical-comment activity importer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactTypeAssignment
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.identity import (
    IdentityIndex,
    IdentityMatchKind,
    IdentityRecord,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
)
from investhome_api.services.permission_service import user_has_permission

_COMMENT_METADATA_KEY = "bitrix_historical_comment"
_LOCK_NAME = "investhome.crm.bitrix.historical-comment-commit"


class BitrixCommentConflictError(ValueError):
    pass


@dataclass(frozen=True)
class SafeCommentPlan:
    import_key: str
    contact_id: UUID
    source_file: str
    source_role: str
    source_row_identifier: str | None
    comment: str
    content_sha256: str
    matched_by: str


@dataclass
class SafeCommentPlanSet:
    plans: list[SafeCommentPlan]
    review_excluded: int
    matched_by_phone: int
    matched_by_email: int
    active_source_comments: int
    junk_source_comments: int


@dataclass
class BitrixCommentCommitResult:
    batch_identifier: str
    source_files: list[str]
    attempted: int
    created: int
    skipped: int
    failed: int
    review_excluded: int
    matched_by_phone: int
    matched_by_email: int
    active_source_comments: int
    junk_source_comments: int
    contacts_created_accidentally: int
    agreements_created_accidentally: int
    agent_roles_created_accidentally: int
    duplicate_activities: int
    db_counts_before: dict[str, int]
    db_counts_after: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        return "\n".join(
            [
                "BITRIX SAFE HISTORICAL COMMENT COMMIT",
                f"batch_identifier: {self.batch_identifier}",
                f"attempted: {self.attempted}",
                f"created: {self.created}",
                f"skipped: {self.skipped}",
                f"failed: {self.failed}",
                f"review_excluded: {self.review_excluded}",
                f"matched_by_phone: {self.matched_by_phone}",
                f"matched_by_email: {self.matched_by_email}",
                f"duplicate_activities: {self.duplicate_activities}",
                f"contacts_created_accidentally: {self.contacts_created_accidentally}",
            ]
        )


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }


def _agent_role_count(db: Session) -> int:
    return db.scalar(
        select(text("count(*)")).select_from(CrmContactTypeAssignment).where(
            CrmContactTypeAssignment.contact_type.in_(["broker", "realtor"])
        )
    ) or 0


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def _comment_identity(row: BitrixSourceRow, comment: str) -> tuple[str, str]:
    content_sha256 = hashlib.sha256(comment.encode("utf-8")).hexdigest()
    row_identifier = (row.bitrix_id or "").strip()
    if row_identifier:
        seed = f"{row.source_file}\0{row_identifier}"
    else:
        phone = parse_phone(row.phone)
        safe_phone = phone.e164 if phone and phone.e164 and not phone.suspicious else ""
        email = normalize_valid_email(row.email) or ""
        seed = f"{row.source_file}\0{row.role}\0{safe_phone}\0{email}\0{content_sha256}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"bitrix-comment-{digest}", content_sha256


def build_safe_comment_plans(db: Session, bundle: BitrixBundle) -> SafeCommentPlanSet:
    index = IdentityIndex()
    for contact in db.scalars(select(CrmContact)).all():
        bitrix = (contact.metadata_json or {}).get("bitrix_import")
        if isinstance(bitrix, dict):
            roles = set(bitrix.get("source_roles") or [])
            if not roles.intersection({"active_customers", "junk"}):
                # Supplementary customer comments may not be promoted by a
                # later agent/agreement-only contact identity.
                continue
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

    plans: list[SafeCommentPlan] = []
    seen: dict[str, SafeCommentPlan] = {}
    review_excluded = matched_phone = matched_email = active_count = junk_count = 0
    for row in bundle.rows:
        if row.role not in {"active_comments", "junk_comments"}:
            continue
        comment = (row.comment or "").strip()
        match = index.match(row.phone, row.email, row.full_name)
        if (
            not comment
            or match.kind not in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL}
            or match.record is None
            or match.record.contact_id is None
        ):
            review_excluded += 1
            continue
        import_key, content_sha256 = _comment_identity(row, comment)
        plan = SafeCommentPlan(
            import_key=import_key,
            contact_id=match.record.contact_id,
            source_file=row.source_file,
            source_role=row.role,
            source_row_identifier=(row.bitrix_id or "").strip() or None,
            comment=comment,
            content_sha256=content_sha256,
            matched_by=match.kind.value,
        )
        prior = seen.get(import_key)
        if prior is not None:
            if prior.contact_id != plan.contact_id or prior.content_sha256 != content_sha256:
                raise BitrixCommentConflictError("duplicate source comment identity conflict")
            continue
        seen[import_key] = plan
        plans.append(plan)
        if match.kind == IdentityMatchKind.PHONE:
            matched_phone += 1
        else:
            matched_email += 1
        if row.role == "active_comments":
            active_count += 1
        else:
            junk_count += 1

    return SafeCommentPlanSet(
        plans=plans,
        review_excluded=review_excluded,
        matched_by_phone=matched_phone,
        matched_by_email=matched_email,
        active_source_comments=active_count,
        junk_source_comments=junk_count,
    )


def _existing_imports(db: Session) -> dict[str, CrmActivity]:
    found: dict[str, CrmActivity] = {}
    for activity in db.scalars(select(CrmActivity)).all():
        metadata = activity.metadata_json or {}
        imported = metadata.get(_COMMENT_METADATA_KEY)
        if not isinstance(imported, dict):
            continue
        import_key = imported.get("import_key")
        if import_key:
            found[str(import_key)] = activity
    return found


def _create_activity(db: Session, plan: SafeCommentPlan, actor: User) -> None:
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=plan.contact_id,
            activity_type=CrmActivityType.COMMENT,
            activity_category=CrmActivityCategory.NOTE,
            title="Historical Bitrix comment",
            description=plan.comment,
            status=CrmActivityStatus.COMPLETED,
            priority=CrmActivityPriority.MEDIUM,
            visibility=CrmActivityVisibility.ORGANIZATION,
            created_by=actor.id,
            updated_by=actor.id,
            metadata_json={
                _COMMENT_METADATA_KEY: {
                    "import_key": plan.import_key,
                    "source": "Bitrix",
                    "source_file": plan.source_file,
                    "source_role": plan.source_role,
                    "source_row_identifier": plan.source_row_identifier,
                    "content_sha256": plan.content_sha256,
                    "imported_historical_comment": True,
                    "matched_by": plan.matched_by,
                }
            },
        )
    )


def _batch_identifier(plans: list[SafeCommentPlan]) -> str:
    digest = hashlib.sha256(
        json.dumps(
            [plan.import_key for plan in plans],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return f"bitrix-comments-{digest[:16]}"


def commit_safe_historical_comments(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User,
) -> BitrixCommentCommitResult:
    if not user_has_permission(actor, "crm", "import", db=db):
        raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    roles_before = _agent_role_count(db)
    plan_set = build_safe_comment_plans(db, bundle)
    created = skipped = 0
    with db.begin_nested():
        _acquire_lock(db)
        existing = _existing_imports(db)
        for plan in plan_set.plans:
            prior = existing.get(plan.import_key)
            if prior is not None:
                metadata = (prior.metadata_json or {}).get(_COMMENT_METADATA_KEY)
                if (
                    prior.entity_id != plan.contact_id
                    or not isinstance(metadata, dict)
                    or metadata.get("content_sha256") != plan.content_sha256
                ):
                    raise BitrixCommentConflictError("existing historical comment identity conflict")
                skipped += 1
                continue
            _create_activity(db, plan, actor)
            created += 1
        db.flush()

    after = _db_counts(db)
    roles_after = _agent_role_count(db)
    imported_keys = [
        str((activity.metadata_json or {})[_COMMENT_METADATA_KEY]["import_key"])
        for activity in db.scalars(select(CrmActivity)).all()
        if isinstance((activity.metadata_json or {}).get(_COMMENT_METADATA_KEY), dict)
    ]
    duplicate_activities = len(imported_keys) - len(set(imported_keys))
    contacts_delta = after["crm_contacts"] - before["crm_contacts"]
    agreements_delta = after["crm_agreements"] - before["crm_agreements"]
    roles_delta = roles_after - roles_before
    if duplicate_activities or contacts_delta or agreements_delta or roles_delta:
        raise BitrixCommentConflictError(
            "post-write comment safety verification failed; transaction must be rolled back"
        )

    return BitrixCommentCommitResult(
        batch_identifier=_batch_identifier(plan_set.plans),
        source_files=sorted({plan.source_file for plan in plan_set.plans}),
        attempted=len(plan_set.plans),
        created=created,
        skipped=skipped,
        failed=0,
        review_excluded=plan_set.review_excluded,
        matched_by_phone=plan_set.matched_by_phone,
        matched_by_email=plan_set.matched_by_email,
        active_source_comments=plan_set.active_source_comments,
        junk_source_comments=plan_set.junk_source_comments,
        contacts_created_accidentally=contacts_delta,
        agreements_created_accidentally=agreements_delta,
        agent_roles_created_accidentally=roles_delta,
        duplicate_activities=duplicate_activities,
        db_counts_before=before,
        db_counts_after=after,
    )
