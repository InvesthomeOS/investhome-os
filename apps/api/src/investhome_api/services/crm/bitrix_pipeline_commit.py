"""Idempotent Bitrix Active-customer Sales pipeline commit.

ALL canonical Active Bitrix customers initially appear in Pipeline as Yeni.
Original Bitrix Aşama is preserved only as historical metadata.
This engine never creates CrmContact rows and never invents deal value.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, attributes

import investhome_api.models  # noqa: F401  register related Sales FKs
from investhome_api.models.crm_activity import CrmActivity
from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.models.inventory import InventoryReservation  # noqa: F401
from investhome_api.models.lead import Lead
from investhome_api.models.sales import (
    OpportunityPartyType,
    OpportunityPriority,
    OpportunityStage,
    OpportunityTimeline,
    SalesOpportunity,
)
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_field_backfill import match_source_row
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.bitrix_stage_mapping import (
    PIPELINE_EXCLUDED_STAGES,
    SAFE_BITRIX_STAGE_TO_SALES,
    STAGE_MAPPING_NOTES,
    UNMAPPED_REVIEW_STAGES,
    is_pipeline_excluded_stage,
    map_bitrix_stage,
    normalize_bitrix_stage,
)
from investhome_api.services.crm.identity import normalize_valid_email, parse_phone
from investhome_api.services.permission_service import user_has_permission

_METADATA_KEY = "bitrix_import"
_LOCK_NAME = "investhome.sales.bitrix.pipeline-commit"
_SOURCE = "Bitrix"
_CODE_PREFIX = "BITRIX-HIST-"


@dataclass
class PipelineContactPlan:
    contact_id: UUID
    display_name: str
    status: str
    original_asama: str | None
    asama_by_source: dict[str, str]
    mapped_stage: str | None
    current_stage: str
    pipeline_excluded: bool
    already_in_sales: bool
    unmapped_review: bool
    junk_current: bool
    opportunity_code: str
    existing_opportunity_id: UUID | None = None
    bitrix_external_id: str | None = None
    responsible: str | None = None
    assigned_sales_user_id: UUID | None = None


@dataclass
class BitrixPipelineReport:
    dry_run: bool
    active_source_rows: int
    active_bitrix_contacts: int
    canonical_active_customers: int
    contacts_with_stage: int
    stage_counts: dict[str, int]
    pipeline_yeni_count: int
    safe_stage_mappings: dict[str, str]
    unmapped_review_stages: dict[str, int]
    junk_stage_counts: dict[str, int]
    historical_sales_records_planned: int
    historical_sales_records_created: int
    historical_sales_records_reused: int
    historical_sales_records_updated: int
    contacts_already_represented_in_sales: int
    duplicates_avoided: int
    junk_excluded_from_pipeline: int
    unmatched_source_rows: int
    ambiguous_source_rows: int
    metadata_updates_planned: int
    metadata_updates_written: int
    contacts_count_before: int
    contacts_count_after: int
    leads_count_before: int
    leads_count_after: int
    opportunities_count_before: int
    opportunities_count_after: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        payload = self.to_dict()
        lines = [
            "BITRIX PIPELINE " + ("DRY-RUN (zero Sales writes)" if self.dry_run else "COMMIT"),
            "",
        ]
        for key, value in payload.items():
            if key == "notes":
                continue
            lines.append(f"{key}: {value}")
        if self.notes:
            lines.append("notes:")
            lines.extend(f"  - {note}" for note in self.notes)
        return "\n".join(lines)


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "leads": db.query(Lead).count(),
        "sales_opportunities": db.query(SalesOpportunity).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
    }


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def _safe_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    return None


def _bitrix_meta(contact: CrmContact) -> dict[str, Any]:
    metadata = contact.metadata_json or {}
    bitrix = metadata.get(_METADATA_KEY)
    return dict(bitrix) if isinstance(bitrix, dict) else {}


def _external_ids(contact: CrmContact) -> set[str]:
    values = _bitrix_meta(contact).get("external_ids")
    if not isinstance(values, list):
        return set()
    return {str(item) for item in values if item}


def _source_roles(contact: CrmContact) -> set[str]:
    values = _bitrix_meta(contact).get("source_roles")
    if not isinstance(values, list):
        return set()
    return {str(item) for item in values if item}


def _is_current_junk(contact: CrmContact) -> bool:
    if contact.status != CrmContactStatus.ARCHIVED:
        return False
    if (contact.source or "").strip().lower() != "bitrix":
        return False
    roles = _source_roles(contact)
    return (not roles) or ("junk" in roles and "active_customers" not in roles)


def _opportunity_code_for(contact_id: UUID) -> str:
    return f"{_CODE_PREFIX}{contact_id}"


def _index_contacts(contacts: list[CrmContact]) -> tuple[
    dict[str, set[UUID]],
    dict[str, set[UUID]],
    dict[str, set[UUID]],
    dict[UUID, CrmContact],
]:
    by_phone: dict[str, set[UUID]] = defaultdict(set)
    by_email: dict[str, set[UUID]] = defaultdict(set)
    by_external: dict[str, set[UUID]] = defaultdict(set)
    by_id = {contact.id: contact for contact in contacts}
    for contact in contacts:
        for value in (
            [contact.primary_phone],
            contact.secondary_phones or [],
            [contact.whatsapp],
        ):
            if isinstance(value, list):
                candidates = value
            else:
                candidates = [value]
            for item in candidates:
                phone = _safe_phone(item)
                if phone:
                    by_phone[phone].add(contact.id)
        for value in ([contact.primary_email], contact.secondary_emails or []):
            candidates = value if isinstance(value, list) else [value]
            for item in candidates:
                email = normalize_valid_email(item)
                if email:
                    by_email[email].add(contact.id)
        for external_id in _external_ids(contact):
            by_external[external_id].add(contact.id)
    return by_phone, by_email, by_external, by_id


def _match_row(
    row: BitrixSourceRow,
    *,
    by_phone: dict[str, set[UUID]],
    by_email: dict[str, set[UUID]],
    by_external: dict[str, set[UUID]],
) -> tuple[UUID | None, str]:
    return match_source_row(
        row,
        by_phone=by_phone,
        by_email=by_email,
        by_external=by_external,
    )


def _preferred_asama(asama_by_source: dict[str, str]) -> str | None:
    active_values = [
        value
        for file_name, value in asama_by_source.items()
        if "junklar" not in file_name.casefold()
        and "junk" not in file_name.casefold()
        and value not in PIPELINE_EXCLUDED_STAGES
    ]
    if active_values:
        return active_values[0]
    for value in asama_by_source.values():
        if value:
            return value
    return None


def _map_responsible_user(db: Session, name: str | None) -> UUID | None:
    if not name or not name.strip():
        return None
    needle = name.strip().casefold()
    matches = [
        user.id
        for user in db.scalars(select(User)).all()
        if (user.full_name or "").strip().casefold() == needle
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _already_in_sales(
    contact: CrmContact,
    *,
    by_code: dict[str, SalesOpportunity],
    by_contact: dict[UUID, SalesOpportunity],
    by_lead: dict[UUID, SalesOpportunity],
) -> SalesOpportunity | None:
    existing = by_contact.get(contact.id) or by_code.get(_opportunity_code_for(contact.id))
    if existing:
        return existing
    if contact.lead_id:
        return by_lead.get(contact.lead_id)
    return None


def build_pipeline_plans(db: Session, bundle: BitrixBundle) -> tuple[
    list[PipelineContactPlan],
    dict[str, Any],
]:
    contacts = list(db.scalars(select(CrmContact)).all())
    bitrix_contacts = [
        contact for contact in contacts if (contact.source or "").strip().lower() == "bitrix"
    ]
    opportunities = list(db.scalars(select(SalesOpportunity)).all())
    by_code = {item.opportunity_code: item for item in opportunities}
    by_contact = {
        item.crm_contact_id: item for item in opportunities if item.crm_contact_id
    }
    by_lead = {item.lead_id: item for item in opportunities if item.lead_id}

    by_phone, by_email, by_external, by_id = _index_contacts(bitrix_contacts)
    asama_by_contact: dict[UUID, dict[str, str]] = defaultdict(dict)
    responsible_by_contact: dict[UUID, str] = {}
    unmatched = 0
    ambiguous = 0
    active_stage_counts: Counter[str] = Counter()
    junk_stage_counts: Counter[str] = Counter()
    active_source_rows = 0
    matched_active_ids: set[UUID] = set()

    for row in bundle.rows:
        if row.role == "junk":
            stage = normalize_bitrix_stage(row.stage)
            if stage:
                junk_stage_counts[stage] += 1
            continue
        if row.role != "active_customers":
            continue
        active_source_rows += 1
        stage = normalize_bitrix_stage(row.stage)
        if stage:
            active_stage_counts[stage] += 1
        contact_id, match_kind = _match_row(
            row, by_phone=by_phone, by_email=by_email, by_external=by_external
        )
        if match_kind == "unmatched":
            unmatched += 1
            continue
        if match_kind == "ambiguous":
            ambiguous += 1
            continue
        assert contact_id is not None
        matched_active_ids.add(contact_id)
        if stage:
            asama_by_contact[contact_id][row.source_file] = stage
        if row.bitrix_id:
            asama_by_contact[contact_id].setdefault("_external", f"{row.source_file}:{row.bitrix_id}")
        if row.responsible and contact_id not in responsible_by_contact:
            responsible_by_contact[contact_id] = row.responsible

    plans: list[PipelineContactPlan] = []
    for contact_id in matched_active_ids:
        contact = by_id[contact_id]
        by_source = {
            key: value
            for key, value in asama_by_contact.get(contact.id, {}).items()
            if key != "_external"
        }
        original = _preferred_asama(by_source) or normalize_bitrix_stage(
            _bitrix_meta(contact).get("original_asama")
        )
        junk_current = _is_current_junk(contact)
        mapped = map_bitrix_stage(original) if original else None
        existing = _already_in_sales(
            contact, by_code=by_code, by_contact=by_contact, by_lead=by_lead
        )
        responsible = responsible_by_contact.get(contact.id) or (
            (_bitrix_meta(contact).get("source_extras") or {}).get("responsible")
            if isinstance(_bitrix_meta(contact).get("source_extras"), dict)
            else None
        )
        plans.append(
            PipelineContactPlan(
                contact_id=contact.id,
                display_name=contact.display_name,
                status=contact.status.value,
                original_asama=original,
                asama_by_source=by_source,
                mapped_stage=mapped.value if mapped else None,
                current_stage=OpportunityStage.NEW.value,
                pipeline_excluded=junk_current,
                already_in_sales=existing is not None,
                unmapped_review=bool(
                    original and original in UNMAPPED_REVIEW_STAGES and not junk_current
                ),
                junk_current=junk_current,
                opportunity_code=_opportunity_code_for(contact.id),
                existing_opportunity_id=existing.id if existing else None,
                bitrix_external_id=asama_by_contact.get(contact.id, {}).get("_external")
                or next(iter(_external_ids(contact)), None),
                responsible=str(responsible) if responsible else None,
                assigned_sales_user_id=_map_responsible_user(
                    db, str(responsible) if responsible else None
                ),
            )
        )

    stats = {
        "active_source_rows": active_source_rows,
        "active_bitrix_contacts": sum(
            1 for contact in bitrix_contacts if contact.status == CrmContactStatus.ACTIVE
        ),
        "canonical_active_customers": len(matched_active_ids),
        "contacts_with_stage": sum(1 for plan in plans if plan.original_asama),
        "stage_counts": dict(active_stage_counts),
        "junk_stage_counts": dict(junk_stage_counts),
        "unmatched_source_rows": unmatched,
        "ambiguous_source_rows": ambiguous,
    }
    return plans, stats


def _apply_metadata(contact: CrmContact, plan: PipelineContactPlan) -> bool:
    merged = dict(contact.metadata_json or {})
    bitrix = dict(merged.get(_METADATA_KEY) or {})
    desired = {
        "original_asama": plan.original_asama,
        "asama_by_source": plan.asama_by_source,
        "mapped_sales_stage": plan.mapped_stage,
        "current_pipeline_stage": plan.current_stage,
        "historical_asama_only": True,
    }
    changed = False
    for key, value in desired.items():
        if bitrix.get(key) != value:
            bitrix[key] = value
            changed = True
    if not changed:
        return False
    merged[_METADATA_KEY] = bitrix
    contact.metadata_json = merged
    attributes.flag_modified(contact, "metadata_json")
    return True


def _create_opportunity(
    db: Session,
    contact: CrmContact,
    plan: PipelineContactPlan,
    *,
    actor: User,
) -> SalesOpportunity:
    stage = OpportunityStage.NEW
    opportunity = SalesOpportunity(
        opportunity_code=plan.opportunity_code,
        display_id=(contact.display_name or "")[:50] or None,
        crm_contact_id=contact.id,
        party_id=contact.id,
        party_type=OpportunityPartyType.CRM_CONTACT,
        stage=stage,
        probability=0,
        expected_revenue=None,
        priority=OpportunityPriority.MEDIUM,
        source=_SOURCE,
        assigned_sales_user_id=plan.assigned_sales_user_id,
        notes=(
            f"Bitrix historical Aşama: {plan.original_asama}. "
            "Current Investhome pipeline stage: Yeni."
        ),
        created_by_id=actor.id if db.get(User, actor.id) else None,
    )
    db.add(opportunity)
    db.flush()
    db.add(
        OpportunityTimeline(
            opportunity_id=opportunity.id,
            event_type="sales.opportunity.bitrix_historical_import",
            to_stage=stage.value,
            actor_user_id=actor.id,
            notes=plan.original_asama,
            metadata_json={
                "source": _SOURCE,
                "crm_contact_id": str(contact.id),
                "bitrix_external_id": plan.bitrix_external_id,
                "original_asama": plan.original_asama,
                "mapped_sales_stage": plan.mapped_stage,
                "current_pipeline_stage": OpportunityStage.NEW.value,
                "asama_by_source": plan.asama_by_source,
            },
        )
    )
    return opportunity


def run_bitrix_pipeline(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User | None,
    dry_run: bool,
) -> BitrixPipelineReport:
    if not dry_run:
        if actor is None:
            raise BitrixCommitPermissionError("authorized actor required")
        if not user_has_permission(actor, "crm", "import", db=db):
            raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    plans, stats = build_pipeline_plans(db, bundle)
    planned_sales = [
        plan for plan in plans if not plan.pipeline_excluded and not plan.junk_current
    ]
    already = [plan for plan in planned_sales if plan.already_in_sales]
    to_create = [plan for plan in planned_sales if not plan.already_in_sales]
    metadata_plans = [plan for plan in plans if plan.original_asama or plan.asama_by_source]
    unmapped_counts: Counter[str] = Counter(
        plan.original_asama
        for plan in plans
        if plan.unmapped_review and plan.original_asama
    )
    junk_excluded = sum(1 for plan in plans if plan.junk_current)
    notes = [
        "Pipeline is driven by Sales Opportunity records, not Leads.",
        "Every canonical Active Bitrix customer is placed in Yeni.",
        "Original Bitrix Aşama is preserved as historical metadata only.",
        "Deal value and probability are not invented.",
        "Junk current contacts are excluded from Pipeline.",
        "Owner is assigned only when Bitrix Sorumlu matches exactly one OS user.",
    ]

    created = 0
    reused = 0
    updated = 0
    metadata_written = 0
    if not dry_run:
        assert actor is not None
        with db.begin_nested():
            _acquire_lock(db)
            contacts = {
                contact.id: contact
                for contact in db.scalars(select(CrmContact)).all()
            }
            for plan in metadata_plans:
                contact = contacts.get(plan.contact_id)
                if contact is None:
                    continue
                if _apply_metadata(contact, plan):
                    metadata_written += 1
            for plan in already:
                existing = db.scalar(
                    select(SalesOpportunity).where(
                        SalesOpportunity.opportunity_code == plan.opportunity_code
                    )
                ) or db.get(SalesOpportunity, plan.existing_opportunity_id)
                if existing is None:
                    continue
                changed = False
                old_stage = existing.stage
                if old_stage != OpportunityStage.NEW:
                    existing.stage = OpportunityStage.NEW
                    changed = True
                    db.add(
                        OpportunityTimeline(
                            opportunity_id=existing.id,
                            event_type="sales.opportunity.bitrix_initial_yeni",
                            from_stage=old_stage.value if old_stage else None,
                            to_stage=OpportunityStage.NEW.value,
                            actor_user_id=actor.id,
                            notes=plan.original_asama,
                            metadata_json={
                                "source": _SOURCE,
                                "original_asama": plan.original_asama,
                                "current_pipeline_stage": OpportunityStage.NEW.value,
                            },
                        )
                    )
                if existing.crm_contact_id is None:
                    existing.crm_contact_id = plan.contact_id
                    changed = True
                if (
                    plan.assigned_sales_user_id
                    and existing.assigned_sales_user_id is None
                ):
                    existing.assigned_sales_user_id = plan.assigned_sales_user_id
                    changed = True
                if existing.expected_revenue is not None:
                    existing.expected_revenue = None
                    changed = True
                if changed:
                    updated += 1
                reused += 1
            for plan in to_create:
                contact = contacts.get(plan.contact_id)
                if contact is None or _is_current_junk(contact):
                    continue
                existing = db.scalar(
                    select(SalesOpportunity).where(
                        SalesOpportunity.opportunity_code == plan.opportunity_code
                    )
                )
                if existing is not None:
                    reused += 1
                    continue
                _create_opportunity(db, contact, plan, actor=actor)
                created += 1
            db.flush()
        db.commit()

    after = _db_counts(db)
    return BitrixPipelineReport(
        dry_run=dry_run,
        active_source_rows=stats["active_source_rows"],
        active_bitrix_contacts=stats["active_bitrix_contacts"],
        canonical_active_customers=stats["canonical_active_customers"],
        contacts_with_stage=stats["contacts_with_stage"],
        stage_counts=stats["stage_counts"],
        pipeline_yeni_count=len(planned_sales),
        safe_stage_mappings={
            key: value.value for key, value in SAFE_BITRIX_STAGE_TO_SALES.items()
        },
        unmapped_review_stages=dict(unmapped_counts),
        junk_stage_counts=stats["junk_stage_counts"],
        historical_sales_records_planned=len(to_create) if dry_run else created,
        historical_sales_records_created=0 if dry_run else created,
        historical_sales_records_reused=len(already) if dry_run else reused,
        historical_sales_records_updated=0 if dry_run else updated,
        contacts_already_represented_in_sales=len(already),
        duplicates_avoided=len(already),
        junk_excluded_from_pipeline=junk_excluded,
        unmatched_source_rows=stats["unmatched_source_rows"],
        ambiguous_source_rows=stats["ambiguous_source_rows"],
        metadata_updates_planned=len(metadata_plans),
        metadata_updates_written=0 if dry_run else metadata_written,
        contacts_count_before=before["crm_contacts"],
        contacts_count_after=after["crm_contacts"],
        leads_count_before=before["leads"],
        leads_count_after=after["leads"],
        opportunities_count_before=before["sales_opportunities"],
        opportunities_count_after=after["sales_opportunities"],
        notes=notes,
    )
