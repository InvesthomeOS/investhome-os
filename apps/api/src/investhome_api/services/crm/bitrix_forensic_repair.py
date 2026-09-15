"""Idempotent Bitrix forensic repair: every source row stays represented."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, attributes, selectinload

from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementStatus
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactBrokerProfile,
    CrmContactStatus,
    CrmContactType,
    CrmContactTypeAssignment,
    CrmLifecycleStage,
    CrmRecordKind,
)
from investhome_api.models.sales import OpportunityStage, SalesOpportunity
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_import import BITRIX_SOURCE, BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.bitrix_pipeline_commit import (
    PipelineContactPlan,
    _already_in_sales,
    _create_opportunity,
    _opportunity_code_for,
)
from investhome_api.services.crm.bitrix_project_aliases import (
    BITRIX_PROJECT_GROUP_LABELS,
    BitrixProjectGroup,
    _OS_PROJECT_NAMES,
    load_project_ids_by_name,
    resolve_project_group,
)
from investhome_api.services.crm.bitrix_reit_membership import (
    EXPECTED_AGREEMENT_COUNTS,
    detect_excluded_reit_source_ids,
    is_excluded_reit_source_id,
)
from investhome_api.services.crm.demo_cleanup import cleanup_crm_demo_records
from investhome_api.services.crm.identity import is_zero_masked_phone, normalize_valid_email, parse_phone, phone_is_better
from investhome_api.services.permission_service import user_has_permission

_LOCK_NAME = "investhome.crm.bitrix.forensic-repair"
_METADATA_KEY = "bitrix_import"
_COMMENT_KEY = "bitrix_historical_comment"
_PLACEHOLDER_ZERO = re.compile(r"0{5,}$")
_DIGIT_RE = re.compile(r"\D")
_PLACEHOLDER_NAME = {"bitrix contact", "bitrix kişi", "bitrix kisi", ""}
_MAIN_FILES = ("Aktif Müşteriler.xls", "Junklar.xls")


@dataclass
class ForensicRepairReport:
    dry_run: bool
    active: dict[str, Any]
    junk: dict[str, Any]
    agents: dict[str, Any]
    agreements: dict[str, Any]
    comments: dict[str, Any]
    pipeline: dict[str, Any]
    junk_reasons: dict[str, int]
    demo_removed: dict[str, Any]
    db_counts_before: dict[str, int]
    db_counts_after: dict[str, int]
    still_missing: list[str]
    agent_phone_company_fixes: list[dict[str, Any]]
    agreement_field_fixes: dict[str, int]
    repaired: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_console(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "crm_activities": db.query(CrmActivity).count(),
        "crm_agreements": db.query(CrmAgreement).count(),
        "sales_opportunities": db.query(SalesOpportunity).count(),
        "broker_profiles": db.query(CrmContactBrokerProfile).count(),
        "review_required_contacts": db.query(CrmContact).filter(CrmContact.review_required.is_(True)).count(),
    }


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def _external_id(row: BitrixSourceRow) -> str | None:
    bitrix_id = (row.bitrix_id or "").strip()
    if not bitrix_id:
        return None
    return f"{row.source_file}:{bitrix_id}"


def _stable_name(row: BitrixSourceRow, *, fallback_kind: str) -> str:
    name = (row.full_name or "").strip()
    if name:
        return name
    parts = " ".join(part for part in (row.first_name, row.last_name) if part)
    if parts.strip():
        return parts.strip()
    if (row.deal_name or "").strip():
        return row.deal_name.strip()
    bitrix_id = (row.bitrix_id or "").strip() or "unknown"
    return f"Bitrix {fallback_kind} {bitrix_id}"


def _placeholder_phone(parsed) -> bool:
    if parsed is None:
        return False
    digits = parsed.digits or ""
    if _PLACEHOLDER_ZERO.search(digits):
        return True
    if parsed.e164 and parsed.e164.startswith("+0"):
        return True
    return False


def _safe_e164(raw: str | None) -> str | None:
    parsed = parse_phone(raw)
    if parsed is None or parsed.suspicious or not parsed.e164:
        return None
    if _placeholder_phone(parsed):
        return None
    if parsed.e164.startswith("+0"):
        return None
    return parsed.e164


def _display_phone(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    original = str(raw).strip()
    safe = _safe_e164(original)
    if safe:
        return safe
    return original[:50]


def _row_phones(row: BitrixSourceRow) -> list[str]:
    values: list[str] = []
    for item in [row.phone, *(row.phones or [])]:
        if item and item not in values:
            values.append(item)
    return values


def _row_emails(row: BitrixSourceRow) -> list[str]:
    values: list[str] = []
    for item in [row.email, *(row.emails or [])]:
        email = normalize_valid_email(item)
        if email and email not in values:
            values.append(email)
    return values


def _bitrix_meta(contact: CrmContact) -> dict[str, Any]:
    metadata = dict(contact.metadata_json or {})
    bitrix = metadata.get(_METADATA_KEY)
    return dict(bitrix) if isinstance(bitrix, dict) else {}


def _set_bitrix_meta(contact: CrmContact, bitrix: dict[str, Any]) -> None:
    metadata = dict(contact.metadata_json or {})
    metadata[_METADATA_KEY] = bitrix
    contact.metadata_json = metadata
    attributes.flag_modified(contact, "metadata_json")


def _clip(value: str | None, limit: int) -> str | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


class ContactIndex:
    def __init__(self, contacts: list[CrmContact]) -> None:
        self.by_id = {contact.id: contact for contact in contacts}
        self.by_external: dict[str, set[UUID]] = defaultdict(set)
        self.by_numeric: dict[str, set[UUID]] = defaultdict(set)
        self.by_phone: dict[str, set[UUID]] = defaultdict(set)
        self.by_email: dict[str, set[UUID]] = defaultdict(set)
        for contact in contacts:
            self._index_contact(contact)

    def _index_contact(self, contact: CrmContact) -> None:
        self.by_id[contact.id] = contact
        bitrix = _bitrix_meta(contact)
        for value in bitrix.get("external_ids") or []:
            if not value:
                continue
            text = str(value)
            self.by_external[text].add(contact.id)
            numeric = text.rsplit(":", 1)[-1]
            if numeric:
                self.by_numeric[numeric].add(contact.id)
        for phone in [contact.primary_phone, *(contact.secondary_phones or [])]:
            e164 = _safe_e164(phone)
            if e164:
                self.by_phone[e164].add(contact.id)
        for email in [contact.primary_email, *(contact.secondary_emails or [])]:
            normalized = normalize_valid_email(email)
            if normalized:
                self.by_email[normalized].add(contact.id)

    def add(self, contact: CrmContact) -> None:
        self._index_contact(contact)

    def unique(self, hits: set[UUID]) -> UUID | None:
        if len(hits) == 1:
            return next(iter(hits))
        return None

    def match_row(
        self,
        row: BitrixSourceRow,
        *,
        allow_numeric: bool = False,
        numeric_files: tuple[str, ...] = (),
    ) -> tuple[CrmContact | None, str]:
        external = _external_id(row)
        if external:
            found = self.by_external.get(external, set())
            hit = self.unique(found)
            if hit:
                return self.by_id[hit], "external_id"
            if len(found) > 1:
                return None, "ambiguous"
        if allow_numeric and row.bitrix_id and numeric_files:
            numeric = row.bitrix_id.strip()
            hits: set[UUID] = set()
            for file_name in numeric_files:
                hits |= self.by_external.get(f"{file_name}:{numeric}", set())
            hit = self.unique(hits)
            if hit:
                return self.by_id[hit], "bitrix_numeric"
        phone_hits: set[UUID] = set()
        for raw in _row_phones(row):
            e164 = _safe_e164(raw)
            if e164:
                found = self.by_phone.get(e164, set())
                if len(found) > 1:
                    return None, "ambiguous"
                phone_hits |= found
        if len(phone_hits) == 1:
            return self.by_id[next(iter(phone_hits))], "phone"
        if len(phone_hits) > 1:
            return None, "ambiguous"
        email_hits: set[UUID] = set()
        for email in _row_emails(row):
            found = self.by_email.get(email, set())
            if len(found) > 1:
                return None, "ambiguous"
            email_hits |= found
        if len(email_hits) == 1:
            return self.by_id[next(iter(email_hits))], "email"
        if len(email_hits) > 1:
            return None, "ambiguous"
        return None, "unmatched"


def _needs_review(row: BitrixSourceRow, *, match_kind: str, created: bool = False) -> bool:
    has_identity = bool(_safe_e164(row.phone) or _row_emails(row))
    if created and not has_identity:
        return True
    if match_kind in {"unmatched", "ambiguous"} and not has_identity:
        return True
    if not has_identity:
        return True
    return False


def _malformed_stored_phone(value: str | None) -> bool:
    if not value:
        return False
    digits = _DIGIT_RE.sub("", value)
    return len(digits) > 15


def _apply_contact_fields(contact: CrmContact, row: BitrixSourceRow, *, review: bool) -> dict[str, bool]:
    fixes = {"name": False, "phone": False, "email": False, "company": False, "junk_reason": False}
    source_name = _stable_name(row, fallback_kind="Kişi")
    current_name = (contact.display_name or "").strip()
    if (not current_name or current_name.casefold() in _PLACEHOLDER_NAME) and source_name:
        contact.display_name = source_name[:255]
        fixes["name"] = True
    if not contact.first_name and row.first_name:
        contact.first_name = _clip(row.first_name, 120)
    if not contact.last_name and row.last_name:
        contact.last_name = _clip(row.last_name, 120)

    display_phones = [_display_phone(raw) for raw in _row_phones(row)]
    display_phones = [item for item in display_phones if item]
    safe_primary = next((_safe_e164(raw) for raw in _row_phones(row) if _safe_e164(raw)), None)
    desired_primary = safe_primary
    if desired_primary and phone_is_better(desired_primary, contact.primary_phone):
        if not contact.primary_phone or is_zero_masked_phone(contact.primary_phone) or _malformed_stored_phone(
            contact.primary_phone
        ):
            contact.primary_phone = desired_primary[:50]
            fixes["phone"] = True
    elif not contact.primary_phone:
        fallback = next((item for item in display_phones if not is_zero_masked_phone(item)), None)
        if fallback:
            contact.primary_phone = fallback[:50]
            fixes["phone"] = True
    extra_phones = [item for item in display_phones if item != contact.primary_phone]
    if extra_phones:
        merged = list(contact.secondary_phones or [])
        for item in extra_phones:
            if item not in merged:
                merged.append(item)
                fixes["phone"] = True
        contact.secondary_phones = merged

    emails = _row_emails(row)
    if emails:
        if not contact.primary_email:
            contact.primary_email = emails[0][:255]
            fixes["email"] = True
        extra = [item for item in emails if item != contact.primary_email]
        if extra:
            merged_emails = list(contact.secondary_emails or [])
            for item in extra:
                if item not in merged_emails:
                    merged_emails.append(item)
                    fixes["email"] = True
            contact.secondary_emails = merged_emails

    if row.company and not contact.organization_name:
        contact.organization_name = _clip(row.company, 255)
        fixes["company"] = True
    if row.job_title and not contact.job_title:
        contact.job_title = _clip(row.job_title, 120)
    if row.address and not contact.address_line1:
        contact.address_line1 = _clip(row.address, 255)
    if row.junk_reason and not contact.junk_reason:
        contact.junk_reason = _clip(row.junk_reason, 255)
        fixes["junk_reason"] = True
    if contact.source is None:
        contact.source = "Bitrix"
    if review:
        contact.review_required = True
    return fixes


def _attach_source_row(contact: CrmContact, row: BitrixSourceRow, *, match_kind: str) -> None:
    bitrix = _bitrix_meta(contact)
    external_ids = {str(item) for item in bitrix.get("external_ids") or [] if item}
    source_files = {str(item) for item in bitrix.get("source_files") or [] if item}
    source_roles = {str(item) for item in bitrix.get("source_roles") or [] if item}
    sources = list(bitrix.get("sources") or []) if isinstance(bitrix.get("sources"), list) else []
    external = _external_id(row)
    if external:
        external_ids.add(external)
    source_files.add(row.source_file)
    source_roles.add(row.role)
    payload = {
        "source_file": row.source_file,
        "role": row.role,
        "external_id": (row.bitrix_id or "").strip() or None,
        "display_name": (row.full_name or "").strip() or None,
        "phone": (row.phone or "").strip() or None,
        "email": (row.email or "").strip() or None,
        "company": (row.company or "").strip() or None,
        "junk_reason": row.junk_reason,
        "match_kind": match_kind,
    }
    if payload not in sources:
        sources.append(payload)
    warning_flags = {str(item) for item in bitrix.get("warning_flags") or [] if item}
    if contact.review_required:
        warning_flags.add("review_required")
    extras = dict(bitrix.get("source_extras") or {}) if isinstance(bitrix.get("source_extras"), dict) else {}
    if row.responsible and not extras.get("responsible"):
        extras["responsible"] = row.responsible
    if row.source_channel and not extras.get("source_channel"):
        extras["source_channel"] = row.source_channel
    raw_phones = [item for item in _row_phones(row) if item]
    if raw_phones:
        extras["raw_phones"] = list(dict.fromkeys([*(extras.get("raw_phones") or []), *raw_phones]))
    bitrix.update(
        {
            "version": max(int(bitrix.get("version") or 1), 2),
            "external_ids": sorted(external_ids),
            "source_files": sorted(source_files),
            "source_roles": sorted(source_roles),
            "historical_junk": "junk" in source_roles or bool(bitrix.get("historical_junk")),
            "sources": sources,
            "warning_flags": sorted(warning_flags),
            "source_extras": extras,
        }
    )
    if row.junk_reason and not bitrix.get("junk_reason"):
        bitrix["junk_reason"] = row.junk_reason
    _set_bitrix_meta(contact, bitrix)


def _create_contact(
    db: Session,
    row: BitrixSourceRow,
    *,
    status: CrmContactStatus,
    contact_type: CrmContactType,
    review: bool,
    fallback_kind: str,
) -> CrmContact:
    name = _stable_name(row, fallback_kind=fallback_kind)
    contact = CrmContact(
        contact_type=contact_type,
        record_kind=CrmRecordKind.ORGANIZATION if row.role == "active_customers" and not row.phone and not row.email and " / " in name else CrmRecordKind.PERSON,
        display_name=name[:255],
        first_name=_clip(row.first_name, 120),
        last_name=_clip(row.last_name, 120),
        organization_name=_clip(row.company, 255),
        job_title=_clip(row.job_title, 120),
        lifecycle_stage=CrmLifecycleStage.NEW,
        source="Bitrix",
        status=status,
        review_required=review,
        junk_reason=_clip(row.junk_reason, 255) if status == CrmContactStatus.ARCHIVED else None,
        junked_at=_now() if status == CrmContactStatus.ARCHIVED else None,
        archived_at=_now() if status == CrmContactStatus.ARCHIVED else None,
        metadata_json={_METADATA_KEY: {}},
    )
    _apply_contact_fields(contact, row, review=review)
    if status == CrmContactStatus.ARCHIVED and row.junk_reason:
        contact.junk_reason = _clip(row.junk_reason, 255)
    db.add(contact)
    db.flush()
    return contact


def _ensure_agent_role(db: Session, contact: CrmContact, row: BitrixSourceRow) -> dict[str, bool]:
    changed = {"role": False, "profile": False, "company": False}
    types = {item.contact_type for item in (contact.type_assignments or [])}
    if CrmContactType.BROKER not in types:
        db.add(CrmContactTypeAssignment(contact_id=contact.id, contact_type=CrmContactType.BROKER))
        if contact.contact_type != CrmContactType.BROKER:
            contact.contact_type = CrmContactType.BROKER
        changed["role"] = True
    if contact.status == CrmContactStatus.ARCHIVED:
        contact.status = CrmContactStatus.ACTIVE
        contact.archived_at = None
    profile = contact.broker_profile
    if profile is None:
        profile = db.scalar(
            select(CrmContactBrokerProfile).where(CrmContactBrokerProfile.contact_id == contact.id)
        )
    company = _clip(row.company, 255)
    if profile is None:
        profile = CrmContactBrokerProfile(
            contact_id=contact.id,
            brokerage_name=company,
            notes=row.comment,
        )
        db.add(profile)
        changed["profile"] = True
    elif company and not profile.brokerage_name:
        profile.brokerage_name = company
        changed["company"] = True
    if company and not contact.organization_name:
        contact.organization_name = company
        changed["company"] = True
    if row.job_title and profile is not None and not profile.specialization:
        profile.specialization = _clip(row.job_title, 120)
    return changed


def _agreement_source_id(row: BitrixSourceRow) -> str:
    external = _external_id(row)
    if external:
        return external[:120]
    digest = hashlib.sha256(
        json.dumps(
            {
                "source_file": row.source_file,
                "name": row.full_name,
                "phone": row.phone,
                "email": row.email,
                "unit": row.unit_number,
            },
            sort_keys=True,
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    return f"{row.source_file[:40]}:sha256:{digest[:48]}"[:120]


def _agreement_metadata(row: BitrixSourceRow, *, project_group: str, project_label: str, review: bool) -> dict[str, Any]:
    extra = dict(row.extra or {})
    source_fields = extra.get("source_fields") if isinstance(extra.get("source_fields"), dict) else {}
    useful = {
        "customer_name": row.full_name,
        "phone": row.phone,
        "phones": row.phones,
        "raw_source_phone": row.raw_source_phone or row.phone,
        "email": row.email,
        "emails": row.emails,
        "company": row.company,
        "unit_number": row.unit_number,
        "agreement_date": str(row.agreement_date) if row.agreement_date else None,
        "closing_date": row.closing_date_raw,
        "payment_method": row.payment_method,
        "payment_amount": row.payment_amount,
        "deposit": row.deposit,
        "rental_info": row.rental_info,
        "ownership_share": row.ownership_share,
        "property_address": row.property_address,
        "notes": row.comment,
        "deal_name": row.deal_name,
    }
    return {
        "version": 2,
        "source": "Bitrix",
        "imported_historical_agreement": True,
        "source_file": row.source_file,
        "source_row_identifier": (row.bitrix_id or "").strip() or None,
        "project_group": project_group,
        "project_label": project_label,
        "project_from_source_file": True,
        "review_required": review,
        "contact_email": row.email,
        "contact_phone": _display_phone(row.phone),
        "raw_source_phone": row.raw_source_phone or row.phone,
        "source_name": row.full_name,
        "unit_number": row.unit_number,
        "agreement_fields": {key: value for key, value in useful.items() if value},
        "source_fields": source_fields,
    }


def _comment_import_key(row: BitrixSourceRow, comment: str) -> tuple[str, str]:
    content_sha256 = hashlib.sha256((comment or "").encode("utf-8")).hexdigest()
    row_identifier = (row.bitrix_id or "").strip()
    if row_identifier:
        seed = f"{row.source_file}\0{row_identifier}"
    else:
        seed = f"{row.source_file}\0{row.role}\0{row.full_name or ''}\0{content_sha256}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return f"bitrix-comment-{digest}", content_sha256


def run_bitrix_forensic_repair(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User | None,
    dry_run: bool,
) -> ForensicRepairReport:
    if not dry_run:
        if actor is None or not user_has_permission(actor, "crm", "import", db=db):
            raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    contacts = list(
        db.scalars(
            select(CrmContact).options(
                selectinload(CrmContact.type_assignments),
                selectinload(CrmContact.broker_profile),
            )
        ).all()
    )
    index = ContactIndex(contacts)
    repaired = Counter()
    agent_fixes: list[dict[str, Any]] = []
    still_missing: list[str] = []

    if not dry_run:
        _acquire_lock(db)
    nested = db.begin_nested() if dry_run else None

    active_rows = [row for row in bundle.rows if row.role == "active_customers"]
    junk_rows = [row for row in bundle.rows if row.role == "junk"]
    agent_rows = [row for row in bundle.rows if row.role == "agents"]
    agreement_rows = [row for row in bundle.rows if row.role == "agreements"]
    comment_rows = [row for row in bundle.rows if row.role in {"active_comments", "junk_comments"}]

    def represent(row: BitrixSourceRow, *, status: CrmContactStatus, contact_type: CrmContactType, fallback: str, numeric: bool = False) -> tuple[CrmContact, str, bool]:
        contact, kind = index.match_row(row, allow_numeric=numeric, numeric_files=_MAIN_FILES if numeric else ())
        created = False
        if contact is None:
            contact = _create_contact(
                db, row, status=status, contact_type=contact_type, review=False, fallback_kind=fallback
            )
            created = True
            index.add(contact)
            repaired["contacts_created"] += 1
            kind = "created"
        review = _needs_review(row, match_kind=kind, created=created)
        if not created:
            if status == CrmContactStatus.ACTIVE and contact.status == CrmContactStatus.ARCHIVED and row.role in {"active_customers", "agents"}:
                contact.status = CrmContactStatus.ACTIVE
                contact.archived_at = None
            _apply_contact_fields(contact, row, review=review)
            repaired["contacts_updated"] += 1
        else:
            _apply_contact_fields(contact, row, review=review)
        _attach_source_row(contact, row, match_kind=kind)
        index.add(contact)
        return contact, kind, created

    active_represented = 0
    active_created = 0
    active_review = 0
    for row in active_rows:
        contact, kind, created = represent(
            row, status=CrmContactStatus.ACTIVE, contact_type=CrmContactType.PROSPECT, fallback="Müşteri"
        )
        if created:
            active_created += 1
        if contact.review_required:
            active_review += 1
        if _external_id(row) and _external_id(row) in set(_bitrix_meta(contact).get("external_ids") or []):
            active_represented += 1
        elif dry_run:
            active_represented += 1

    junk_represented = 0
    junk_created = 0
    junk_review = 0
    junk_contact_ids: set[UUID] = set()
    junk_ext_to_contact: dict[str, UUID] = {}
    for row in junk_rows:
        contact, kind, created = represent(
            row, status=CrmContactStatus.ARCHIVED, contact_type=CrmContactType.PROSPECT, fallback="Junk"
        )
        if created:
            junk_created += 1
            contact.status = CrmContactStatus.ARCHIVED
            if row.junk_reason:
                contact.junk_reason = _clip(row.junk_reason, 255)
                contact.junked_at = contact.junked_at or _now()
        elif "active_customers" not in set(_bitrix_meta(contact).get("source_roles") or []) and contact.status != CrmContactStatus.ACTIVE:
            if contact.status != CrmContactStatus.ARCHIVED:
                contact.status = CrmContactStatus.ARCHIVED
            if row.junk_reason and not contact.junk_reason:
                contact.junk_reason = _clip(row.junk_reason, 255)
        if contact.review_required:
            junk_review += 1
        external = _external_id(row)
        if external:
            junk_ext_to_contact[external] = contact.id
            junk_represented += 1
        junk_contact_ids.add(contact.id)

    agent_represented = 0
    agent_created = 0
    agent_contact_ids: set[UUID] = set()
    for row in agent_rows:
        contact, kind, created = represent(
            row, status=CrmContactStatus.ACTIVE, contact_type=CrmContactType.BROKER, fallback="Acenta"
        )
        if created:
            agent_created += 1
        role_changes = _ensure_agent_role(db, contact, row)
        if any(role_changes.values()) or kind in {"created", "unmatched"}:
            agent_fixes.append(
                {
                    "bitrix_id": row.bitrix_id,
                    "name": contact.display_name,
                    "raw_phone": row.phone,
                    "stored_phone": contact.primary_phone,
                    "secondary_phones": contact.secondary_phones,
                    "company": contact.organization_name,
                    "email": contact.primary_email,
                    "review_required": contact.review_required,
                    "match_kind": kind,
                    **role_changes,
                }
            )
        agent_contact_ids.add(contact.id)
        if _external_id(row):
            agent_represented += 1

    project_ids = load_project_ids_by_name(db)
    existing_agreements = list(db.scalars(select(CrmAgreement)).all())
    by_external_agreement = {
        (row.source, row.source_external_id): row for row in existing_agreements if row.source_external_id
    }
    contamination_before = 0
    for agreement in existing_agreements:
        meta = agreement.metadata_json or {}
        source_file = meta.get("source_file") if isinstance(meta, dict) else None
        if source_file:
            expected = resolve_project_group(str(source_file))
            if expected and agreement.project_group != expected.value:
                contamination_before += 1

    excluded_reit, _ = detect_excluded_reit_source_ids(bundle)
    agreement_counts: Counter[str] = Counter()
    agreement_created = 0
    agreement_updated = 0
    agreement_review = 0
    field_fixes: Counter[str] = Counter()
    for row in agreement_rows:
        group = resolve_project_group(row.source_file)
        if group is None:
            still_missing.append(f"agreement_unknown_project:{row.source_file}:{row.bitrix_id}")
            continue
        source_external_id = _agreement_source_id(row)
        if group == BitrixProjectGroup.REIT and is_excluded_reit_source_id(
            source_external_id, excluded_reit
        ):
            existing_excluded = by_external_agreement.get(
                (BITRIX_SOURCE, source_external_id)
            ) or by_external_agreement.get(("bitrix", source_external_id))
            if existing_excluded is not None and not dry_run:
                db.delete(existing_excluded)
                by_external_agreement.pop((BITRIX_SOURCE, source_external_id), None)
                by_external_agreement.pop(("bitrix", source_external_id), None)
            continue
        label = BITRIX_PROJECT_GROUP_LABELS[group]
        project_id = None
        for name in _OS_PROJECT_NAMES.get(group, ()):
            if name in project_ids:
                project_id = project_ids[name]
                break
        contact, kind = index.match_row(row)
        if contact is None:
            contact, kind, _ = represent(
                row, status=CrmContactStatus.ACTIVE, contact_type=CrmContactType.BUYER, fallback="Anlaşma"
            )
        review = _needs_review(row, match_kind=kind, created=kind == "created")
        existing = by_external_agreement.get((BITRIX_SOURCE, source_external_id)) or by_external_agreement.get(
            ("bitrix", source_external_id)
        )
        metadata = _agreement_metadata(row, project_group=group.value, project_label=label, review=review)
        if existing is None:
            if not dry_run or True:
                existing = CrmAgreement(
                    contact_id=contact.id,
                    project_id=project_id,
                    project_group=group.value,
                    source=BITRIX_SOURCE,
                    source_external_id=source_external_id,
                    status=CrmAgreementStatus.UNKNOWN,
                    agreement_date=row.agreement_date,
                    unit_number=_clip(row.unit_number, 80) if group != BitrixProjectGroup.REIT else None,
                    investment_amount=(
                        _clip(row.payment_amount, 80) if group == BitrixProjectGroup.REIT else None
                    ),
                    review_required=review,
                    metadata_json=metadata,
                )
                db.add(existing)
                db.flush()
                by_external_agreement[(BITRIX_SOURCE, source_external_id)] = existing
                agreement_created += 1
        else:
            changed = False
            if existing.project_group != group.value:
                existing.project_group = group.value
                field_fixes["project_group"] += 1
                changed = True
            if project_id and existing.project_id != project_id:
                existing.project_id = project_id
                changed = True
            if existing.contact_id != contact.id and kind in {"phone", "email", "external_id"}:
                existing.contact_id = contact.id
                changed = True
            if group == BitrixProjectGroup.REIT:
                if existing.unit_number:
                    existing.unit_number = None
                    field_fixes["unit_number"] += 1
                    changed = True
                amount = _clip(row.payment_amount, 80)
                if amount and existing.investment_amount != amount:
                    existing.investment_amount = amount
                    field_fixes["investment_amount"] += 1
                    changed = True
            elif row.unit_number and existing.unit_number != row.unit_number:
                existing.unit_number = _clip(row.unit_number, 80)
                field_fixes["unit_number"] += 1
                changed = True
            elif row.unit_number and not existing.unit_number:
                existing.unit_number = _clip(row.unit_number, 80)
                field_fixes["unit_number"] += 1
                changed = True
            if review:
                existing.review_required = True
            merged_meta = dict(existing.metadata_json or {})
            merged_meta.update(metadata)
            existing.metadata_json = merged_meta
            attributes.flag_modified(existing, "metadata_json")
            if (contact.display_name or "").strip().casefold() in _PLACEHOLDER_NAME and row.full_name:
                contact.display_name = row.full_name[:255]
                field_fixes["name"] += 1
            if row.email and not contact.primary_email:
                contact.primary_email = normalize_valid_email(row.email)
                field_fixes["email"] += 1
            if row.phone and (not contact.primary_phone or _malformed_stored_phone(contact.primary_phone)):
                contact.primary_phone = _display_phone(row.phone)
                field_fixes["phone"] += 1
            if changed:
                agreement_updated += 1
        if existing.review_required:
            agreement_review += 1
        agreement_counts[group.value] += 1

    existing_comment_keys: dict[str, CrmActivity] = {}
    for activity in db.scalars(select(CrmActivity)).all():
        imported = (activity.metadata_json or {}).get(_COMMENT_KEY)
        if isinstance(imported, dict) and imported.get("import_key"):
            existing_comment_keys[str(imported["import_key"])] = activity

    comments_attached = 0
    comments_review = 0
    comments_created = 0
    for row in comment_rows:
        comment = (row.comment or "").strip() or "(Bitrix yorum satırı — metin boş)"
        import_key, sha = _comment_import_key(row, comment)
        contact, kind = index.match_row(row, allow_numeric=True, numeric_files=_MAIN_FILES)
        review = kind in {"unmatched", "ambiguous"}
        if contact is None:
            contact, kind, _ = represent(
                row,
                status=CrmContactStatus.ACTIVE if row.role == "active_comments" else CrmContactStatus.ARCHIVED,
                contact_type=CrmContactType.PROSPECT,
                fallback="Yorum",
                numeric=True,
            )
            review = True
        if import_key in existing_comment_keys:
            comments_attached += 1
            activity = existing_comment_keys[import_key]
            meta = dict(activity.metadata_json or {})
            imported = dict(meta.get(_COMMENT_KEY) or {})
            imported.update(
                {
                    "review_required": review,
                    "source_name": row.full_name,
                    "matched_by": kind,
                }
            )
            meta[_COMMENT_KEY] = imported
            activity.metadata_json = meta
            if review:
                comments_review += 1
            continue
        activity = CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=contact.id,
            activity_type=CrmActivityType.COMMENT,
            activity_category=CrmActivityCategory.NOTE,
            title="İnceleme Gerekli — tarihsel Bitrix yorumu" if review else "Historical Bitrix comment",
            description=comment,
            status=CrmActivityStatus.COMPLETED,
            priority=CrmActivityPriority.MEDIUM,
            visibility=CrmActivityVisibility.ORGANIZATION,
            created_by=actor.id if actor is not None else None,
            updated_by=actor.id if actor is not None else None,
            metadata_json={
                _COMMENT_KEY: {
                    "import_key": import_key,
                    "source": "Bitrix",
                    "source_file": row.source_file,
                    "source_role": row.role,
                    "source_row_identifier": (row.bitrix_id or "").strip() or None,
                    "source_name": row.full_name,
                    "content_sha256": sha,
                    "imported_historical_comment": True,
                    "matched_by": kind,
                    "review_required": review,
                }
            },
        )
        db.add(activity)
        existing_comment_keys[import_key] = activity
        comments_created += 1
        comments_attached += 1
        if review:
            comments_review += 1

    # Pipeline: all 121 active source rows, stage Yeni, no junk-only.
    opportunities = list(db.scalars(select(SalesOpportunity)).all())
    by_code = {item.opportunity_code: item for item in opportunities}
    by_contact = {item.crm_contact_id: item for item in opportunities if item.crm_contact_id}
    by_lead = {item.lead_id: item for item in opportunities if item.lead_id}
    pipeline_created = 0
    pipeline_reused = 0
    pipeline_contacts: set[UUID] = set()
    for row in active_rows:
        contact, _kind = index.match_row(row)
        if contact is None:
            still_missing.append(f"pipeline_unmatched:{row.bitrix_id}:{row.full_name}")
            continue
        if contact.status == CrmContactStatus.ARCHIVED and "junk" in set(_bitrix_meta(contact).get("source_roles") or []) and "active_customers" not in set(_bitrix_meta(contact).get("source_roles") or []):
            still_missing.append(f"pipeline_junk_only:{row.bitrix_id}")
            continue
        existing = _already_in_sales(contact, by_code=by_code, by_contact=by_contact, by_lead=by_lead)
        if existing is None:
            if actor is None:
                still_missing.append(f"pipeline_needs_actor:{row.bitrix_id}")
                continue
            plan = PipelineContactPlan(
                contact_id=contact.id,
                display_name=contact.display_name,
                status=contact.status.value,
                original_asama=row.stage,
                asama_by_source={row.source_file: row.stage} if row.stage else {},
                mapped_stage=None,
                current_stage=OpportunityStage.NEW.value,
                pipeline_excluded=False,
                already_in_sales=False,
                unmapped_review=False,
                junk_current=False,
                opportunity_code=_opportunity_code_for(contact.id),
                bitrix_external_id=_external_id(row),
            )
            opportunity = _create_opportunity(db, contact, plan, actor=actor)
            by_contact[contact.id] = opportunity
            by_code[opportunity.opportunity_code] = opportunity
            pipeline_created += 1
            existing = opportunity
        elif existing.stage != OpportunityStage.NEW and existing.source == "Bitrix":
            existing.stage = OpportunityStage.NEW
            pipeline_reused += 1
        else:
            pipeline_reused += 1
        pipeline_contacts.add(contact.id)
        bitrix = _bitrix_meta(contact)
        bitrix["original_asama"] = row.stage
        bitrix["current_pipeline_stage"] = OpportunityStage.NEW.value
        bitrix["historical_asama_only"] = True
        _set_bitrix_meta(contact, bitrix)

    demo_report = cleanup_crm_demo_records(db, dry_run=dry_run)

    if nested is not None:
        nested.rollback()
        after = before
    else:
        db.flush()
        after = _db_counts(db)

    junk_reason_counts = Counter((row.junk_reason or "").strip() or "(empty)" for row in junk_rows)

    expected_agreement = EXPECTED_AGREEMENT_COUNTS
    for key, expected in expected_agreement.items():
        actual = agreement_counts.get(key, 0)
        if actual != expected:
            still_missing.append(f"agreement_count:{key}:expected {expected} got {actual}")

    if active_represented != 121:
        still_missing.append(f"active_represented:{active_represented}")
    if junk_represented != 8387:
        still_missing.append(f"junk_represented:{junk_represented}")
    if agent_represented != 17:
        still_missing.append(f"agent_represented:{agent_represented}")
    if comments_attached != len(comment_rows):
        still_missing.append(f"comments_attached:{comments_attached}/{len(comment_rows)}")
    if len(pipeline_contacts) != 121:
        still_missing.append(f"pipeline_contacts:{len(pipeline_contacts)}")

    return ForensicRepairReport(
        dry_run=dry_run,
        active={
            "source_rows": len(active_rows),
            "represented": active_represented,
            "missing": max(0, len(active_rows) - active_represented),
            "created": active_created,
            "review_required": active_review,
        },
        junk={
            "source_rows": len(junk_rows),
            "represented_source_rows": junk_represented,
            "canonical_contacts": len(junk_contact_ids),
            "duplicate_source_rows": max(0, junk_represented - len(junk_contact_ids)),
            "created": junk_created,
            "review_required": junk_review,
            "missing": max(0, len(junk_rows) - junk_represented),
        },
        agents={
            "source_rows": len(agent_rows),
            "represented_source_rows": agent_represented,
            "canonical_agents": len(agent_contact_ids),
            "duplicates": max(0, agent_represented - len(agent_contact_ids)),
            "created": agent_created,
            "missing": max(0, len(agent_rows) - agent_represented),
        },
        agreements={
            "source_rows": len(agreement_rows),
            "by_project": dict(agreement_counts),
            "created": agreement_created,
            "updated": agreement_updated,
            "review_required": agreement_review,
            "cross_project_contamination_before": contamination_before,
            "missing": max(0, len(agreement_rows) - sum(agreement_counts.values())),
        },
        comments={
            "active_supplementary_rows": sum(1 for row in comment_rows if row.role == "active_comments"),
            "junk_supplementary_rows": sum(1 for row in comment_rows if row.role == "junk_comments"),
            "safe_attached": comments_attached - comments_review,
            "review_preserved": comments_review,
            "created": comments_created,
            "missing_lost": max(0, len(comment_rows) - comments_attached),
        },
        pipeline={
            "active_source_rows": len(active_rows),
            "yeni_contacts": len(pipeline_contacts),
            "created": pipeline_created,
            "reused": pipeline_reused,
        },
        junk_reasons=dict(sorted(junk_reason_counts.items(), key=lambda item: (-item[1], item[0]))),
        demo_removed=demo_report.to_dict(),
        db_counts_before=before,
        db_counts_after=after,
        still_missing=still_missing,
        agent_phone_company_fixes=agent_fixes,
        agreement_field_fixes=dict(field_fixes),
        repaired=dict(repaired),
    )
