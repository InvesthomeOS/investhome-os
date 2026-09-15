"""Bitrix CRM import dry-run engine. Zero database writes."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from sqlalchemy.orm import Session

from investhome_api.services.crm.bitrix_project_aliases import (
    BITRIX_PROJECT_GROUP_LABELS,
    load_project_ids_by_name,
    resolve_project_alias,
    resolve_project_group,
)
from investhome_api.services.crm.identity import (
    IdentityIndex,
    IdentityMatchKind,
    IdentityRecord,
    is_valid_email,
    is_zero_masked_phone,
    normalize_email,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
    split_multi_values,
)

BitrixFileRole = Literal[
    "active_customers",
    "junk",
    "active_comments",
    "junk_comments",
    "agents",
    "agreements",
    "unknown",
]

BITRIX_SOURCE = "bitrix"
COMMENT_ROLES: frozenset[str] = frozenset({"active_comments", "junk_comments"})
CONTACT_LIST_ROLES: frozenset[str] = frozenset({"active_customers", "junk", "agents"})
MAIN_CONTACT_ROLES: frozenset[str] = frozenset({"active_customers", "junk"})


@dataclass
class BitrixSourceRow:
    source_file: str
    role: BitrixFileRole
    bitrix_id: str | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    comment: str | None = None
    stage: str | None = None
    project_hint: str | None = None
    agreement_date: date | None = None
    company: str | None = None
    job_title: str | None = None
    address: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    website: str | None = None
    whatsapp: str | None = None
    open_channel: str | None = None
    responsible: str | None = None
    source_channel: str | None = None
    bitrix_created_at: str | None = None
    last_contact_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    parse_error: str | None = None
    junk_reason: str | None = None
    unit_number: str | None = None
    payment_method: str | None = None
    payment_amount: str | None = None
    deposit: str | None = None
    ownership_share: str | None = None
    rental_info: str | None = None
    property_address: str | None = None
    closing_date_raw: str | None = None
    deal_name: str | None = None
    product: str | None = None
    raw_source_phone: str | None = None

    @property
    def row_key(self) -> str:
        return f"{self.source_file}:{self.bitrix_id or ''}:{self.full_name or ''}:{self.phone or ''}:{self.email or ''}"


@dataclass
class BitrixBundle:
    rows: list[BitrixSourceRow] = field(default_factory=list)
    file_headers: dict[str, list[str]] = field(default_factory=dict)
    file_mapped_fields: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ExistingContactSnapshot:
    id: UUID
    display_name: str
    primary_phone: str | None
    primary_email: str | None
    types: list[str]
    status: str


@dataclass
class PlannedContact:
    identity_key: str
    display_name: str
    phone: str | None
    email: str | None
    lists: set[str] = field(default_factory=set)
    bitrix_ids: set[str] = field(default_factory=set)
    files: set[str] = field(default_factory=set)
    existing_id: UUID | None = None
    resolved_status: str = "unset"
    agent: bool = False
    comments: list[str] = field(default_factory=list)

    def apply_row(self, row: BitrixSourceRow) -> None:
        self.files.add(row.source_file)
        if row.bitrix_id:
            self.bitrix_ids.add(row.bitrix_id)
        if row.role == "active_customers":
            self.lists.add("active")
        elif row.role == "junk":
            self.lists.add("junk")
        elif row.role == "agents":
            self.agent = True
        if "active" in self.lists:
            self.resolved_status = "active"
        elif "junk" in self.lists:
            self.resolved_status = "archived"


@dataclass
class BitrixDryRunReport:
    contacts: dict[str, Any]
    active_junk: dict[str, Any]
    comments: dict[str, Any]
    agents: dict[str, Any]
    agreements: dict[str, Any]
    data_quality: dict[str, Any]
    writes: dict[str, Any]
    files: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        quality = payload.get("data_quality") or {}
        for key in (
            "invalid_email_samples",
            "suspicious_phone_samples",
            "duplicate_bitrix_id_samples",
            "parsing_error_samples",
        ):
            quality.pop(key, None)
        return payload

    def format_console(self) -> str:
        payload = self.to_dict()
        lines = ["BITRIX DRY-RUN (zero DB writes)", ""]
        for section, body in payload.items():
            if section == "notes":
                continue
            lines.append(section.upper().replace("_", " "))
            if isinstance(body, dict):
                for key, value in body.items():
                    if key.endswith("_samples"):
                        continue
                    lines.append(f"  {key}: {value}")
            elif isinstance(body, list):
                for item in body:
                    lines.append(f"  - {item}")
            lines.append("")
        if self.notes:
            lines.append("NOTES")
            lines.extend(f"  - {note}" for note in self.notes)
        return "\n".join(lines)


def classify_bitrix_filename(filename: str) -> tuple[BitrixFileRole, str | None]:
    from investhome_api.services.crm.bitrix_project_aliases import fold_alias

    stem = Path(filename).name
    folded = fold_alias(stem)
    if "acenta" in folded:
        return "agents", None
    if "junk" in folded and "yorum" in folded:
        return "junk_comments", None
    if folded.startswith("junklar") or folded.startswith("junk "):
        return "junk", None
    if "aktif" in folded and "yorum" in folded:
        return "active_comments", None
    if "aktif" in folded and "musteri" in folded:
        return "active_customers", None
    group = resolve_project_group(Path(stem).stem)
    if group is not None:
        return "agreements", group.value
    if "anlasma" in folded:
        return "agreements", None
    return "unknown", None


def _session_identity(db: Session) -> tuple[frozenset[int], frozenset[int], frozenset[int]]:
    return (
        frozenset(id(obj) for obj in db.new),
        frozenset(id(obj) for obj in db.dirty),
        frozenset(id(obj) for obj in db.deleted),
    )


def load_existing_contacts(db: Session) -> list[ExistingContactSnapshot]:
    from investhome_api.models.crm_contact import CrmContact

    snapshots: list[ExistingContactSnapshot] = []
    for row in db.query(CrmContact).all():
        types = [row.contact_type.value]
        if row.type_assignments:
            types = [item.contact_type.value for item in row.type_assignments]
        snapshots.append(
            ExistingContactSnapshot(
                id=row.id,
                display_name=row.display_name,
                primary_phone=row.primary_phone,
                primary_email=row.primary_email,
                types=types,
                status=row.status.value if hasattr(row.status, "value") else str(row.status),
            )
        )
    return snapshots


def _identity_record(row: BitrixSourceRow) -> IdentityRecord:
    phone = parse_phone(row.phone)
    safe_phone = phone if phone and phone.e164 and not phone.suspicious else None
    return IdentityRecord(
        key=row.row_key,
        display_name=(row.full_name or "").strip() or "(unnamed)",
        phone=safe_phone,
        email=normalize_valid_email(row.email),
        name_key=normalize_full_name(row.full_name),
        origin=row.role,
    )


def _plan_key(record: IdentityRecord) -> str:
    if record.contact_id:
        return f"os:{record.contact_id}"
    if record.phone:
        return f"phone:{record.phone.match_key}"
    if record.email:
        return f"email:{record.email}"
    return f"row:{record.key}"


def _phone_value(record: IdentityRecord) -> str | None:
    if record.phone is None:
        return None
    return record.phone.e164 or record.phone.digits


def run_bitrix_dry_run(
    bundle: BitrixBundle,
    *,
    existing_contacts: list[ExistingContactSnapshot] | None = None,
    project_ids_by_name: dict[str, UUID] | None = None,
    db: Session | None = None,
) -> BitrixDryRunReport:
    """Analyze Bitrix rows. Never writes. ``db`` is read-only if provided."""
    session_before = _session_identity(db) if db is not None else None
    if existing_contacts is None and db is not None:
        existing_contacts = load_existing_contacts(db)
    if project_ids_by_name is None and db is not None:
        project_ids_by_name = load_project_ids_by_name(db)
    existing_contacts = existing_contacts or []
    project_ids_by_name = project_ids_by_name or {}

    os_index = IdentityIndex()
    for contact in existing_contacts:
        os_index.add(
            IdentityRecord(
                key=str(contact.id),
                display_name=contact.display_name,
                phone=parse_phone(contact.primary_phone),
                email=normalize_email(contact.primary_email),
                name_key=normalize_full_name(contact.display_name),
                origin="os",
                contact_id=contact.id,
            )
        )

    source_index = IdentityIndex()
    planned: dict[str, PlannedContact] = {}
    row_to_plan: dict[str, str] = {}

    quality: dict[str, Any] = {
        "invalid_emails": 0,
        "suspicious_phones": 0,
        "empty_names": 0,
        "duplicate_bitrix_ids": 0,
        "parsing_errors": 0,
        "unknown_files": 0,
        "header_mapping_gaps": 0,
    }
    seen_bitrix_ids: dict[str, int] = defaultdict(int)
    main_no_identity = 0
    main_name_review = 0
    main_valid = 0
    matched_existing_phone = 0
    matched_existing_email = 0
    main_ambiguous_review = 0
    main_suspicious_phone_review = 0
    main_same_name_collision_warnings = 0
    main_same_name_warnings = 0
    quarantined_main_names: set[str] = set()

    main_rows = [row for row in bundle.rows if row.role in MAIN_CONTACT_ROLES]
    contact_rows = [row for row in bundle.rows if row.role in CONTACT_LIST_ROLES]
    comment_rows = [row for row in bundle.rows if row.role in COMMENT_ROLES]
    agreement_rows = [row for row in bundle.rows if row.role == "agreements"]

    for row in bundle.rows:
        if row.parse_error:
            quality["parsing_errors"] += 1
        if row.email and not is_valid_email(row.email):
            quality["invalid_emails"] += 1
        phone = parse_phone(row.phone)
        if phone and phone.suspicious:
            quality["suspicious_phones"] += 1
        if row.role in CONTACT_LIST_ROLES and not (row.full_name or "").strip():
            quality["empty_names"] += 1
        if row.bitrix_id:
            seen_bitrix_ids[f"{row.role}:{row.bitrix_id}"] += 1
        if row.role == "unknown":
            quality["unknown_files"] += 1

    quality["duplicate_bitrix_ids"] = sum(1 for count in seen_bitrix_ids.values() if count > 1)

    def resolve_contact_row(row: BitrixSourceRow) -> tuple[str | None, IdentityMatchKind]:
        os_match = os_index.match(row.phone, row.email, row.full_name)
        src_match = source_index.match(row.phone, row.email, row.full_name)
        if os_match.kind in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL} and os_match.record:
            return _plan_key(os_match.record), os_match.kind
        if src_match.kind in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL} and src_match.record:
            return row_to_plan.get(src_match.record.key), src_match.kind
        if os_match.kind == IdentityMatchKind.AMBIGUOUS or src_match.kind == IdentityMatchKind.AMBIGUOUS:
            return None, IdentityMatchKind.AMBIGUOUS
        if os_match.kind == IdentityMatchKind.NO_IDENTITY and src_match.kind in {
            IdentityMatchKind.NO_IDENTITY,
            IdentityMatchKind.NONE,
        }:
            return None, IdentityMatchKind.NO_IDENTITY
        if os_match.kind == IdentityMatchKind.NAME_REVIEW or src_match.kind == IdentityMatchKind.NAME_REVIEW:
            if os_match.kind not in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL} and src_match.kind not in {
                IdentityMatchKind.PHONE,
                IdentityMatchKind.EMAIL,
            }:
                return None, IdentityMatchKind.NAME_REVIEW
        return None, IdentityMatchKind.NONE

    for row in contact_rows:
        record = _identity_record(row)
        os_match = os_index.match(row.phone, row.email, row.full_name)
        src_match = source_index.match(row.phone, row.email, row.full_name)
        key, kind = resolve_contact_row(row)
        is_main = row.role in MAIN_CONTACT_ROLES
        parsed_phone = parse_phone(row.phone)
        suspicious_phone_only = bool(
            parsed_phone
            and parsed_phone.suspicious
            and normalize_valid_email(row.email) is None
        )
        if is_main and (
            src_match.reason == "deterministic_unmatched_same_name_warning"
            or (suspicious_phone_only and src_match.kind == IdentityMatchKind.NAME_REVIEW)
        ):
            main_same_name_collision_warnings += 1
        if (
            is_main
            and record.name_key in quarantined_main_names
            and (record.phone or record.email or suspicious_phone_only)
        ):
            main_same_name_warnings += 1
        if is_main and os_match.kind == IdentityMatchKind.PHONE:
            matched_existing_phone += 1
        elif is_main and os_match.kind == IdentityMatchKind.EMAIL:
            matched_existing_email += 1
        if is_main and suspicious_phone_only:
            main_suspicious_phone_review += 1
            source_index.add(record)
            continue
        if kind == IdentityMatchKind.NO_IDENTITY:
            if is_main:
                main_no_identity += 1
                if record.name_key:
                    quarantined_main_names.add(record.name_key)
            source_index.add(record)
            continue
        if kind == IdentityMatchKind.NAME_REVIEW:
            if is_main:
                main_name_review += 1
            source_index.add(record)
            continue
        if kind == IdentityMatchKind.AMBIGUOUS:
            if is_main:
                main_ambiguous_review += 1
            continue
        if is_main:
            main_valid += 1
        if key is None:
            key = _plan_key(record)
            if key not in planned:
                planned[key] = PlannedContact(
                    identity_key=key,
                    display_name=record.display_name,
                    phone=_phone_value(record),
                    email=record.email,
                )
        elif key not in planned:
            source = os_match.record or record
            planned[key] = PlannedContact(
                identity_key=key,
                display_name=source.display_name,
                phone=_phone_value(source),
                email=source.email,
                existing_id=source.contact_id,
            )
        planned[key].apply_row(row)
        source_index.add(record)
        row_to_plan[record.key] = key

    def _comment_bucket() -> dict[str, int]:
        return {
            "total_supplementary_comment_rows": 0,
            "matched_by_phone": 0,
            "matched_by_email": 0,
            "name_only_candidates": 0,
            "unmatched_comments": 0,
            "ambiguous_matches": 0,
        }

    comments_by_file = {
        "active_comments": _comment_bucket(),
        "junk_comments": _comment_bucket(),
    }
    for row in comment_rows:
        bucket = comments_by_file.get(row.role) or _comment_bucket()
        bucket["total_supplementary_comment_rows"] += 1
        key, kind = resolve_contact_row(row)
        if kind == IdentityMatchKind.PHONE and key:
            bucket["matched_by_phone"] += 1
        elif kind == IdentityMatchKind.EMAIL and key:
            bucket["matched_by_email"] += 1
        elif kind == IdentityMatchKind.AMBIGUOUS:
            bucket["ambiguous_matches"] += 1
        elif kind == IdentityMatchKind.NAME_REVIEW:
            bucket["name_only_candidates"] += 1
        else:
            bucket["unmatched_comments"] += 1
        if row.role in comments_by_file:
            comments_by_file[row.role] = bucket

    comments_totals = _comment_bucket()
    for bucket in comments_by_file.values():
        for key, value in bucket.items():
            comments_totals[key] += value

    agent_rows = [row for row in contact_rows if row.role == "agents"]
    agent_plans = [plan for plan in planned.values() if plan.agent]
    agent_matched = sum(1 for plan in agent_plans if plan.existing_id is not None)
    agent_new = sum(1 for plan in agent_plans if plan.existing_id is None and not plan.lists)
    agent_enrich = sum(1 for plan in agent_plans if plan.existing_id is not None or bool(plan.lists))

    agreements_matched = 0
    agreements_unmatched = 0
    alias_matches = 0
    unknown_projects = 0
    seen_agreement_ids: dict[str, int] = defaultdict(int)
    seen_agreement_ids_by_group: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_project: dict[str, dict[str, Any]] = {}
    for group, label in BITRIX_PROJECT_GROUP_LABELS.items():
        by_project[group.value] = {
            "label": label,
            "source_rows": 0,
            "matched_contacts": 0,
            "unmatched_contacts": 0,
            "duplicate_agreement_candidates": 0,
            "alias_resolved": True,
        }
    by_project["unknown"] = {
        "label": "unknown",
        "source_rows": 0,
        "matched_contacts": 0,
        "unmatched_contacts": 0,
        "duplicate_agreement_candidates": 0,
        "alias_resolved": False,
    }
    for row in agreement_rows:
        alias = resolve_project_alias(row.project_hint or row.source_file, project_ids_by_name=project_ids_by_name)
        group_key = alias.group.value if alias.group is not None else "unknown"
        bucket = by_project[group_key]
        bucket["source_rows"] += 1
        if row.bitrix_id:
            seen_agreement_ids[row.bitrix_id] += 1
            seen_agreement_ids_by_group[group_key][row.bitrix_id] += 1
        if alias.group is None:
            unknown_projects += 1
        else:
            alias_matches += 1
            bucket["alias_resolved"] = True
        key, kind = resolve_contact_row(row)
        if kind in {IdentityMatchKind.PHONE, IdentityMatchKind.EMAIL} and key:
            agreements_matched += 1
            bucket["matched_contacts"] += 1
        else:
            agreements_unmatched += 1
            bucket["unmatched_contacts"] += 1
    for group_key, counts in seen_agreement_ids_by_group.items():
        by_project[group_key]["duplicate_agreement_candidates"] = sum(1 for count in counts.values() if count > 1)
    duplicate_agreements = sum(1 for count in seen_agreement_ids.values() if count > 1)

    active_only = sum(1 for plan in planned.values() if plan.lists == {"active"})
    junk_only = sum(1 for plan in planned.values() if plan.lists == {"junk"})
    both = sum(1 for plan in planned.values() if "active" in plan.lists and "junk" in plan.lists)

    if session_before is not None and db is not None:
        session_after = _session_identity(db)
        writes_detected = session_before != session_after
    else:
        writes_detected = False

    notes = [
        "Dry-run never creates contacts, comments, or agreements.",
        "Supplementary comment files are match-only.",
        "Active overrides Junk for resolved contact status; Junk history is retained.",
        "Name-only hits are review-only and never auto-linked.",
        "CrmContact.company_id still points at org companies — left untouched.",
        "Sales Lead/Opportunity/Pipeline ownership is unchanged.",
        "REIT is a canonical agreement project group; project_id stays null until an OS project exists.",
        "Report contains counts only; phone/email/comment samples are omitted.",
    ]

    files: list[dict[str, Any]] = []
    file_roles: dict[str, str] = {}
    file_rows: dict[str, int] = defaultdict(int)
    file_errors: dict[str, int] = defaultdict(int)
    for row in bundle.rows:
        file_roles[row.source_file] = row.role
        if row.parse_error:
            file_errors[row.source_file] += 1
        else:
            file_rows[row.source_file] += 1
    for name in sorted(set(file_roles) | set(bundle.file_headers)):
        mapped = bundle.file_mapped_fields.get(name, [])
        role = file_roles.get(name, "unknown")
        files.append(
            {
                "name": name,
                "role": role,
                "rows": file_rows.get(name, 0),
                "parse_errors": file_errors.get(name, 0),
                "mapped_fields": mapped,
            }
        )
        if role in MAIN_CONTACT_ROLES | COMMENT_ROLES | {"agents", "agreements"}:
            if not ({"phone", "email", "full_name", "first_name", "last_name"} & set(mapped)):
                quality["header_mapping_gaps"] += 1

    return BitrixDryRunReport(
        contacts={
            "total_main_source_rows": len(main_rows),
            "valid_identities": main_valid,
            "new_contact_candidates": sum(
                1 for plan in planned.values() if plan.existing_id is None and bool(plan.lists)
            ),
            "matched_existing_by_phone": matched_existing_phone,
            "matched_existing_by_email": matched_existing_email,
            "name_only_review_candidates": main_name_review,
            "ambiguous_review_candidates": main_ambiguous_review,
            "suspicious_phone_review_candidates": main_suspicious_phone_review,
            "same_name_collision_warnings": main_same_name_collision_warnings,
            "same_name_quarantined_warnings": main_same_name_warnings,
            "rows_with_no_usable_identity": main_no_identity,
            "cross_file_duplicate_identities": both,
        },
        active_junk={
            "active_only": active_only,
            "junk_only": junk_only,
            "present_in_both": both,
            "resolved_final_state_active": sum(
                1 for plan in planned.values() if plan.lists and plan.resolved_status == "active"
            ),
            "resolved_final_state_junk": sum(
                1 for plan in planned.values() if plan.resolved_status == "archived"
            ),
        },
        comments={
            **comments_totals,
            "active_comments": comments_by_file["active_comments"],
            "junk_comments": comments_by_file["junk_comments"],
        },
        agents={
            "total_agents": len(agent_rows),
            "matched_existing_contacts": agent_matched,
            "new_contact_candidates": agent_new,
            "role_profile_enrichments": agent_enrich,
        },
        agreements={
            "total_agreement_rows": len(agreement_rows),
            "matched_contacts": agreements_matched,
            "unmatched_contacts": agreements_unmatched,
            "project_alias_matches": alias_matches,
            "unknown_project_values": unknown_projects,
            "duplicate_agreement_candidates": duplicate_agreements,
            "by_project": {key: value for key, value in by_project.items() if value["source_rows"] or key != "unknown"},
        },
        data_quality=quality,
        writes={
            "db_writes": 0,
            "session_mutated": writes_detected,
        },
        files=files,
        notes=notes,
    )


_PHONE_HEADER_TOKENS = ("telefon", "phone", "gsm", "mobile", "mobil", "cep")
_PHONE_PRIORITY = ("cep", "mobil", "mobile", "gsm", "is telefon", "work phone", "telefon", "phone")


def _fold_header(value: str) -> str:
    from investhome_api.services.crm.bitrix_project_aliases import fold_alias

    return fold_alias(value)


def _person_header(folded: str) -> str:
    # fold_alias strips punctuation, so "Kişi: Mobil" becomes "kisi mobil".
    if folded.startswith("sirket "):
        return ""
    if folded.startswith("kisi "):
        return folded[5:]
    return folded


def _is_phone_header(folded: str) -> bool:
    if not folded:
        return False
    return any(token in folded for token in _PHONE_HEADER_TOKENS)


def _phone_header_rank(folded: str) -> int:
    for index, token in enumerate(_PHONE_PRIORITY):
        if token in folded:
            return index
    return len(_PHONE_PRIORITY)


def _email_header_rank(folded: str) -> int:
    if folded.endswith(" r") or "(r)" in folded or folded.startswith("is e-posta"):
        return 0
    if folded.startswith("ev e-posta"):
        return 2
    return 1


_EXTRA_HEADER_KEYS: dict[str, str] = {
    "sirket adi": "company",
    "sirket": "company",
    "company": "company",
    "company name": "company",
    "acente ofis ismi - sirket": "company",
    "acente ofis ismi": "company",
    "kisi acente ofis ismi - sirket": "company",
    "kisi acente ofis ismi": "company",
    "pozisyon": "job_title",
    "position": "job_title",
    "unvan": "job_title",
    "meslek": "job_title",
    "adres": "address",
    "address": "address",
    "apartman ofis oda kat": "address_line2",
    "sehir": "city",
    "city": "city",
    "posta kodu": "postal_code",
    "postal code": "postal_code",
    "ulke": "country",
    "country": "country",
    "sirket web sitesi": "website",
    "website": "website",
    "whatsapp": "whatsapp",
    "whats app": "whatsapp",
    "acik kanal hesabi": "open_channel",
    "sorumlu": "responsible",
    "responsible": "responsible",
    "kaynak": "source_channel",
    "olusturulma tarihi": "bitrix_created_at",
    "created": "bitrix_created_at",
    "created date": "bitrix_created_at",
    "son iletisim": "last_contact_at",
    "last contact": "last_contact_at",
    "junk sebebi": "junk_reason",
    "junk reason": "junk_reason",
    "daire no": "unit_number",
    "daire": "unit_number",
    "unit": "unit_number",
    "unit number": "unit_number",
    "unit no": "unit_number",
    "apartment": "unit_number",
    "apartment number": "unit_number",
    "apartment no": "unit_number",
    "urun": "product",
    "product": "product",
    "urun adi": "product",
    "odeme sekli": "payment_method",
    "payment method": "payment_method",
    "gelir": "payment_amount",
    "payment amount": "payment_amount",
    "pesinat": "deposit",
    "on odeme tutari": "deposit",
    "deposit": "deposit",
    "hisse orani": "ownership_share",
    "kira tutari": "rental_info",
    "kampanya kira bedeli": "rental_info",
    "alinan ev proje adresi": "property_address",
    "varsayilan kapanis tarihi": "closing_date",
    "kapanis tarihi": "closing_date",
    "closing date": "closing_date",
    "anlasma adi": "deal_name",
    "iletisim": "contact_label",
}

_COMPANY_HEADER_RANK = {
    "acente ofis ismi - sirket": 0,
    "kisi acente ofis ismi - sirket": 0,
    "acente ofis ismi": 1,
    "kisi acente ofis ismi": 1,
    "sirket adi": 2,
    "sirket": 3,
    "company": 3,
    "company name": 3,
}


def _map_headers(headers: list[str]) -> dict[str, int | list[int]]:
    folded = [_fold_header(h) for h in headers]
    mapping: dict[str, int | list[int]] = {}
    phone_indexes: list[tuple[int, int]] = []
    email_indexes: list[tuple[int, int]] = []
    company_indexes: list[tuple[int, int]] = []
    for index, header in enumerate(folded):
        extra_key = _EXTRA_HEADER_KEYS.get(header)
        if extra_key == "company":
            company_indexes.append((_COMPANY_HEADER_RANK.get(header, 9), index))
            continue
        if extra_key:
            mapping.setdefault(extra_key, index)
            continue
        if header in {
            "anlasma tarihi",
            "sozlesme tarihi",
            "agreement date",
            "contract date",
        }:
            mapping.setdefault("agreement_date", index)
            continue
        person = _person_header(header)
        if not person:
            continue
        if person == "id":
            mapping.setdefault("bitrix_id", index)
            continue
        if _is_phone_header(person):
            phone_indexes.append((_phone_header_rank(person), index))
            continue
        if person in {"email", "e-mail", "mail"} or "e-posta" in person or "eposta" in person or "e posta" in person:
            email_indexes.append((_email_header_rank(person), index))
            continue
        if person in {"ilk adi", "adi", "first name", "first_name", "firstname", "name"} or person == "ad":
            mapping.setdefault("first_name", index)
            continue
        if person in {"soyadi", "soyad", "last name", "last_name", "lastname", "surname"}:
            mapping.setdefault("last_name", index)
            continue
        if person in {"ad soyad", "adi soyadi", "full name", "full_name", "fullname", "display name"}:
            mapping.setdefault("full_name", index)
            continue
        if person == "musteri adayi ismi":
            mapping.setdefault("full_name", index)
            continue
        if person == "musteri yorumu":
            mapping["comment"] = index
            continue
        if person in {"yorum", "yorumlar", "comment", "comments", "notes", "not", "notlar", "aciklama", "aciklamalar"}:
            mapping.setdefault("comment", index)
            continue
        if person in {"asama", "stage"}:
            mapping.setdefault("stage", index)
    if phone_indexes:
        phone_indexes.sort()
        mapping["phone"] = phone_indexes[0][1]
        mapping["phones"] = [item[1] for item in phone_indexes]
    if email_indexes:
        email_indexes.sort()
        mapping["email"] = email_indexes[0][1]
        mapping["emails"] = [item[1] for item in email_indexes]
    if company_indexes:
        company_indexes.sort()
        mapping["company"] = company_indexes[0][1]
        mapping["companies"] = [item[1] for item in company_indexes]
    return mapping


_MAX_SAFE_EXCEL_INT = 2**53
_SCI_NOTATION = re.compile(r"^[+-]?\d+(?:\.\d+)?[eE][+-]?\d+$")
_UNIT_TOKEN = re.compile(
    r"(?i)^(Unit\s+\d+[A-Za-z]?|Unit\d+[A-Za-z]?|[A-Z]\d{2,4}|\d{2,4})\b"
)
_OTHER_UNIT_TOKEN = re.compile(r"(?i)\b(?:Unit\s*\d+[A-Za-z]?|[A-Z]\d{2,4}|\d{2,4})\b")
_DEAL_PREFIXES = (
    re.compile(r"(?i)^1307\s+K\s+ST\s+"),
    re.compile(r"(?i)^1313\s+Penn\s+"),
    re.compile(r"(?i)^1812\s+H\s+PL\s+"),
    re.compile(r"(?i)^1820\s+H\s+PL\s+"),
    re.compile(r"(?i)^2319\s+Ontario\s+"),
    re.compile(r"(?i)^Uniloft\s+"),
)
_NO_UNIT_PROJECTS = frozenset({"reit", "the_temple"})


def excel_number_as_text(value: Any) -> str:
    """Convert an Excel numeric cell to text without scientific notation or float rounding.

    Integer-valued floats below 2^53 are exact in IEEE-754. Larger values cannot be
    recovered from a Python float; they are formatted without rounding via int().
    Scientific-notation strings are parsed with Decimal, never float.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return format(value, "d")
    if isinstance(value, float):
        if value.is_integer() and abs(value) < _MAX_SAFE_EXCEL_INT:
            return format(int(value), "d")
        if value.is_integer():
            return format(value, ".0f")
        return format(value, "f").rstrip("0").rstrip(".")
    text = str(value).strip()
    if not text:
        return ""
    if _SCI_NOTATION.fullmatch(text):
        try:
            decimal_value = Decimal(text)
        except InvalidOperation:
            return text
        integral = decimal_value.to_integral_value()
        if decimal_value == integral:
            return format(integral, "f").split(".")[0]
        return format(decimal_value, "f").rstrip("0").rstrip(".")
    return text


def _cell(row: list[Any], index: int | None) -> str | None:
    if index is None or not isinstance(index, int) or index >= len(row):
        return None
    value = row[index]
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        text = excel_number_as_text(value)
    else:
        text = excel_number_as_text(value) if isinstance(value, str) and _SCI_NOTATION.fullmatch(value.strip()) else str(value).strip()
    return text or None


def _copy_source_token(source: str, token: str | None) -> str | None:
    if not token:
        return None
    if token in source:
        return token
    return None


def _unit_from_product(product: str | None) -> str | None:
    if not product:
        return None
    last = product.strip().split()[-1]
    match = _UNIT_TOKEN.match(last)
    if not match:
        return None
    return _copy_source_token(product, match.group(1))


def _unit_from_deal_name(deal_name: str | None) -> str | None:
    if not deal_name:
        return None
    remainder = deal_name.strip()
    matched_prefix = False
    for prefix in _DEAL_PREFIXES:
        updated = prefix.sub("", remainder, count=1)
        if updated != remainder:
            remainder = updated.strip()
            matched_prefix = True
            break
    if not matched_prefix:
        return None
    match = _UNIT_TOKEN.match(remainder)
    if not match:
        return None
    token = match.group(1)
    after = remainder[match.end() :]
    after = re.sub(r"(?i)\b(LLC|L\.L\.C\.|Inc)\b", " ", after)
    if _OTHER_UNIT_TOKEN.search(after):
        return None
    return _copy_source_token(deal_name, token)


def extract_unit_number(
    *,
    daire_no: str | None = None,
    product: str | None = None,
    deal_name: str | None = None,
    project_hint: str | None = None,
) -> str | None:
    """Copy a unit identifier that already exists in source cells. Never invent a number."""
    dedicated = (daire_no or "").strip() or None
    if dedicated:
        return dedicated
    from_product = _unit_from_product(product)
    if from_product:
        return from_product
    if project_hint in _NO_UNIT_PROJECTS:
        return None
    return _unit_from_deal_name(deal_name)


def _mapped_int(mapping: dict[str, int | list[int]], key: str) -> int | None:
    value = mapping.get(key)
    return value if isinstance(value, int) else None


def _json_cell(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return excel_number_as_text(value)
    return value


def _parse_agreement_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _agreement_extra(headers: list[str], record: list[Any]) -> dict[str, Any]:
    source_fields: dict[str, Any] = {}
    for index, raw_value in enumerate(record):
        if raw_value is None or raw_value == "":
            continue
        header = headers[index].strip() if index < len(headers) else ""
        source_fields[f"{index}:{header or 'column'}"] = _json_cell(raw_value)
    return {"source_fields": source_fields}


def rows_from_table(
    *,
    source_file: str,
    headers: list[str],
    records: list[list[Any]],
    role: BitrixFileRole | None = None,
    project_hint: str | None = None,
) -> list[BitrixSourceRow]:
    classified_role, classified_hint = classify_bitrix_filename(source_file)
    role = role or classified_role
    project_hint = project_hint or classified_hint
    mapping = _map_headers(headers)
    first_idx = _mapped_int(mapping, "first_name")
    last_idx = _mapped_int(mapping, "last_name")
    name_idx = _mapped_int(mapping, "full_name")
    phone_indexes = mapping.get("phones")
    if not isinstance(phone_indexes, list):
        phone_one = _mapped_int(mapping, "phone")
        phone_indexes = [phone_one] if phone_one is not None else []
    out: list[BitrixSourceRow] = []
    for record in records:
        first = _cell(record, first_idx)
        last = _cell(record, last_idx)
        full = _cell(record, name_idx)
        deal_name = _cell(record, _mapped_int(mapping, "deal_name"))
        contact_label = _cell(record, _mapped_int(mapping, "contact_label"))
        if not full:
            full = " ".join(part for part in (first, last) if part) or None
        if not full:
            full = deal_name or contact_label
        phones: list[str] = []
        for phone_idx in phone_indexes:
            for part in split_multi_values(_cell(record, phone_idx)):
                if part not in phones:
                    phones.append(part)
        raw_source_phone = phones[0] if phones else None
        phone = next((item for item in phones if not is_zero_masked_phone(item)), None) or raw_source_phone
        email_indexes = mapping.get("emails")
        if not isinstance(email_indexes, list):
            email_one = _mapped_int(mapping, "email")
            email_indexes = [email_one] if email_one is not None else []
        emails: list[str] = []
        for email_idx in email_indexes:
            for part in split_multi_values(_cell(record, email_idx)):
                if part and part not in emails:
                    emails.append(part)
        email = emails[0] if emails else None
        company_indexes = mapping.get("companies")
        if not isinstance(company_indexes, list):
            company_one = _mapped_int(mapping, "company")
            company_indexes = [company_one] if company_one is not None else []
        company = None
        for company_idx in company_indexes:
            value = _cell(record, company_idx)
            if value:
                company = value
                break
        agreement_date_idx = _mapped_int(mapping, "agreement_date")
        daire_no = _cell(record, _mapped_int(mapping, "unit_number"))
        product = _cell(record, _mapped_int(mapping, "product"))
        unit_number = extract_unit_number(
            daire_no=daire_no,
            product=product,
            deal_name=deal_name,
            project_hint=project_hint,
        )
        extra = _agreement_extra(headers, record) if role == "agreements" else {}
        if role == "agreements":
            extra.update(
                {
                    key: value
                    for key, value in {
                        "unit_number": unit_number,
                        "daire_no": daire_no,
                        "product": product,
                        "payment_method": _cell(record, _mapped_int(mapping, "payment_method")),
                        "payment_amount": _cell(record, _mapped_int(mapping, "payment_amount")),
                        "deposit": _cell(record, _mapped_int(mapping, "deposit")),
                        "ownership_share": _cell(record, _mapped_int(mapping, "ownership_share")),
                        "rental_info": _cell(record, _mapped_int(mapping, "rental_info")),
                        "property_address": _cell(record, _mapped_int(mapping, "property_address")),
                        "closing_date": _cell(record, _mapped_int(mapping, "closing_date")),
                        "deal_name": deal_name,
                        "source_name": full,
                        "source_phone": phone,
                        "raw_source_phone": raw_source_phone,
                        "source_email": email,
                        "source_company": company,
                    }.items()
                    if value
                }
            )
        out.append(
            BitrixSourceRow(
                source_file=source_file,
                role=role,
                bitrix_id=_cell(record, _mapped_int(mapping, "bitrix_id")),
                full_name=full,
                first_name=first,
                last_name=last,
                phone=phone,
                email=email,
                phones=phones,
                emails=emails,
                comment=_cell(record, _mapped_int(mapping, "comment")),
                stage=_cell(record, _mapped_int(mapping, "stage")),
                project_hint=project_hint,
                agreement_date=(
                    _parse_agreement_date(record[agreement_date_idx])
                    if agreement_date_idx is not None and agreement_date_idx < len(record)
                    else None
                ),
                company=company,
                job_title=_cell(record, _mapped_int(mapping, "job_title")),
                address=_cell(record, _mapped_int(mapping, "address")),
                address_line2=_cell(record, _mapped_int(mapping, "address_line2")),
                city=_cell(record, _mapped_int(mapping, "city")),
                postal_code=_cell(record, _mapped_int(mapping, "postal_code")),
                country=_cell(record, _mapped_int(mapping, "country")),
                website=_cell(record, _mapped_int(mapping, "website")),
                whatsapp=_cell(record, _mapped_int(mapping, "whatsapp")),
                open_channel=_cell(record, _mapped_int(mapping, "open_channel")),
                responsible=_cell(record, _mapped_int(mapping, "responsible")),
                source_channel=_cell(record, _mapped_int(mapping, "source_channel")),
                bitrix_created_at=_cell(record, _mapped_int(mapping, "bitrix_created_at")),
                last_contact_at=_cell(record, _mapped_int(mapping, "last_contact_at")),
                junk_reason=_cell(record, _mapped_int(mapping, "junk_reason")),
                extra=extra,
                unit_number=unit_number,
                payment_method=_cell(record, _mapped_int(mapping, "payment_method")),
                payment_amount=_cell(record, _mapped_int(mapping, "payment_amount")),
                deposit=_cell(record, _mapped_int(mapping, "deposit")),
                ownership_share=_cell(record, _mapped_int(mapping, "ownership_share")),
                rental_info=_cell(record, _mapped_int(mapping, "rental_info")),
                property_address=_cell(record, _mapped_int(mapping, "property_address")),
                closing_date_raw=_cell(record, _mapped_int(mapping, "closing_date")),
                deal_name=deal_name,
                product=product,
                raw_source_phone=raw_source_phone,
            )
        )
    return out


def load_spreadsheet_rows(path: Path) -> tuple[list[str], list[list[Any]], str | None]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        import csv

        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.reader(handle)
            rows = list(reader)
        if not rows:
            return [], [], "empty_csv"
        return rows[0], rows[1:], None
    if suffix == ".xlsx":
        from openpyxl import load_workbook

        workbook = load_workbook(path, read_only=True, data_only=True)
        sheet = workbook.active
        rows = []
        for row in sheet.iter_rows(values_only=True):
            converted: list[Any] = []
            for cell in row:
                if cell is None:
                    converted.append("")
                elif isinstance(cell, float) and not isinstance(cell, bool):
                    converted.append(excel_number_as_text(cell))
                else:
                    converted.append(cell)
            rows.append(converted)
        workbook.close()
        if not rows:
            return [], [], "empty_xlsx"
        headers = [str(item) if item is not None else "" for item in rows[0]]
        body = [list(item) for item in rows[1:]]
        return headers, body, None
    if suffix == ".xls":
        try:
            import xlrd  # type: ignore
        except ImportError:
            return [], [], "xlrd_missing_for_xls"
        book = xlrd.open_workbook(str(path))
        sheet = book.sheet_by_index(0)
        headers = [str(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
        body = []
        for row in range(1, sheet.nrows):
            values: list[Any] = []
            for col in range(sheet.ncols):
                cell = sheet.cell(row, col)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    values.append(xlrd.xldate_as_datetime(cell.value, book.datemode))
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    values.append(excel_number_as_text(cell.value))
                elif cell.ctype == xlrd.XL_CELL_TEXT:
                    values.append(cell.value)
                else:
                    values.append(cell.value)
            body.append(values)
        return headers, body, None
    return [], [], f"unsupported_extension:{suffix}"


def load_bundle_from_directory(source_dir: Path) -> BitrixBundle:
    bundle = BitrixBundle()
    if not source_dir.exists():
        return bundle
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".xls", ".xlsx", ".csv"}:
            continue
        headers, records, error = load_spreadsheet_rows(path)
        header_names = [str(item) for item in headers]
        bundle.file_headers[path.name] = header_names
        mapped = _map_headers(header_names)
        bundle.file_mapped_fields[path.name] = sorted(
            key for key in mapped if key != "phones"
        )
        if error:
            bundle.rows.append(
                BitrixSourceRow(
                    source_file=path.name,
                    role="unknown",
                    parse_error=error,
                )
            )
            continue
        bundle.rows.extend(rows_from_table(source_file=path.name, headers=header_names, records=records))
    return bundle


def console_main(argv: list[str] | None = None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(prog="investhome-bitrix", description="Bitrix CRM safe import")
    sub = parser.add_subparsers(dest="command", required=True)
    dry = sub.add_parser("dry-run", help="Parse Bitrix files and report matches. Zero DB writes.")
    dry.add_argument("--source-dir", default="data/bitrix-import", help="Directory of .xls/.xlsx/.csv extracts")
    dry.add_argument("--json-out", default=None, help="Write JSON report path")
    dry.add_argument("--read-db", action="store_true", help="Match against existing CRM contacts (read-only)")
    commit = sub.add_parser("commit", help="Commit safe deterministic main contacts only.")
    commit.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    commit.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    commit.add_argument("--limit", required=True, type=int, help="Maximum safe canonical contacts")
    commit.add_argument("--offset", default=0, type=int, help="Safe canonical contact offset")
    commit.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    commit.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_CONTACTS_ONLY",),
        help="Explicit safe-write confirmation",
    )
    comments = sub.add_parser(
        "commit-comments",
        help="Commit safe deterministic historical comments only.",
    )
    comments.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    comments.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    comments.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    comments.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_COMMENTS_ONLY",),
        help="Explicit safe-write confirmation",
    )
    agents = sub.add_parser(
        "commit-agents",
        help="Enrich existing safe canonical contacts with Acentalar roles only.",
    )
    agents.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    agents.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    agents.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    agents.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_AGENT_ROLES_ONLY",),
        help="Explicit safe-write confirmation",
    )
    agreements = sub.add_parser(
        "commit-agreements",
        help="Commit safe historical agreements for existing canonical contacts only.",
    )
    agreements.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    agreements.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    agreements.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    agreements.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_AGREEMENTS_ONLY",),
        help="Explicit safe-write confirmation",
    )
    pipeline_dry = sub.add_parser(
        "dry-run-pipeline",
        help="Report Bitrix Aşama → Sales pipeline plans. Zero Sales writes.",
    )
    pipeline_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    pipeline_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    pipeline = sub.add_parser(
        "commit-pipeline",
        help="Commit safe historical Sales opportunities for mapped Bitrix stages.",
    )
    pipeline.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    pipeline.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    pipeline.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    pipeline.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_PIPELINE_ONLY",),
        help="Explicit safe-write confirmation",
    )
    forensic_dry = sub.add_parser(
        "dry-run-forensic",
        help="Source-vs-DB forensic reconciliation. Nested writes are rolled back.",
    )
    forensic_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    forensic_dry.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    forensic_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    forensic = sub.add_parser(
        "commit-forensic",
        help="Preserve every Bitrix source row; repair review/quarantine gaps idempotently.",
    )
    forensic.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    forensic.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    forensic.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    forensic.add_argument(
        "--confirm",
        required=True,
        choices=("FORENSIC_REPAIR",),
        help="Explicit forensic-write confirmation",
    )
    fields_dry = sub.add_parser(
        "dry-run-junk-fields",
        help="Report Junklar.xls fields missing from existing CrmContact rows. Zero writes.",
    )
    fields_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    fields_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    fields = sub.add_parser(
        "commit-junk-fields",
        help="Backfill missing Junk contact fields onto existing CrmContact rows.",
    )
    fields.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    fields.add_argument("--actor-user-id", required=True, help="Authorized user UUID")
    fields.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    fields.add_argument(
        "--confirm",
        required=True,
        choices=("SAFE_JUNK_FIELDS_ONLY",),
        help="Explicit safe-write confirmation",
    )
    unit_phone_dry = sub.add_parser(
        "dry-run-agreement-fields",
        help="Report agreement unit numbers and lossless phone repair. Zero writes.",
    )
    unit_phone_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    unit_phone_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    unit_phone = sub.add_parser(
        "commit-agreement-fields",
        help="Backfill agreement unit_number and repair masked phones from original Excel.",
    )
    unit_phone.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    unit_phone.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    unit_phone.add_argument(
        "--confirm",
        required=True,
        choices=("AGREEMENT_UNIT_PHONE_ONLY",),
        help="Explicit agreement unit/phone repair confirmation",
    )
    final_dry = sub.add_parser(
        "dry-run-final-normalization",
        help="Phase 6E dry-run: rescue, REIT Gelir, junk reasons, project audit. Nested writes rolled back.",
    )
    final_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    final_dry.add_argument("--rescue-xlsx", default=None, help="Manually corrected rescue workbook")
    final_dry.add_argument("--xlsx-out", default=None, help="Write project reconciliation workbook")
    final_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    final_norm = sub.add_parser(
        "commit-final-normalization",
        help="Phase 6E: apply rescue, REIT Gelir, junk reasons, and Bitrix project repairs.",
    )
    final_norm.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    final_norm.add_argument("--rescue-xlsx", default=None, help="Manually corrected rescue workbook")
    final_norm.add_argument("--xlsx-out", required=True, help="Write project reconciliation workbook")
    final_norm.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    final_norm.add_argument(
        "--confirm",
        required=True,
        choices=("BITRIX_FINAL_NORMALIZATION",),
        help="Explicit Phase 6E confirmation",
    )
    cleanup_dry = sub.add_parser(
        "dry-run-crm-demo",
        help="Report deterministically marked CRM/Sales demo records. Zero writes.",
    )
    cleanup_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    cleanup = sub.add_parser(
        "cleanup-crm-demo",
        help="Delete deterministically marked CRM/Sales demo records only.",
    )
    cleanup.add_argument("--json-out", required=True, help="Write aggregate JSON result")
    cleanup.add_argument(
        "--confirm",
        required=True,
        choices=("REMOVE_DEMO_CRM_ONLY",),
        help="Explicit demo-cleanup confirmation",
    )
    wb_dry = sub.add_parser(
        "dry-run-workbook-correction",
        help="Dry-run user-corrected Bitrix rescue workbook (phones, units, identity links).",
    )
    wb_dry.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    wb_dry.add_argument("--rescue-xlsx", required=True, help="User-corrected rescue workbook")
    wb_dry.add_argument("--original-xlsx", default=None, help="Originally generated rescue workbook")
    wb_dry.add_argument("--json-out", default=None, help="Write JSON report path")
    wb_commit = sub.add_parser(
        "commit-workbook-correction",
        help="Apply user-corrected Bitrix rescue workbook.",
    )
    wb_commit.add_argument("--source-dir", required=True, help="Directory of validated Bitrix extracts")
    wb_commit.add_argument("--rescue-xlsx", required=True, help="User-corrected rescue workbook")
    wb_commit.add_argument("--original-xlsx", default=None, help="Originally generated rescue workbook")
    wb_commit.add_argument("--json-out", required=True, help="Write JSON report path")
    wb_commit.add_argument(
        "--confirm",
        required=True,
        choices=("BITRIX_WORKBOOK_CORRECTION",),
        help="Explicit workbook-correction confirmation",
    )
    args = parser.parse_args(argv)

    source_dir = Path(args.source_dir) if hasattr(args, "source_dir") else None
    bundle = load_bundle_from_directory(source_dir) if source_dir is not None else BitrixBundle()
    if args.command in {
        "commit",
        "commit-comments",
        "commit-agents",
        "commit-agreements",
        "commit-pipeline",
        "dry-run-pipeline",
        "commit-forensic",
        "dry-run-forensic",
        "commit-junk-fields",
        "dry-run-junk-fields",
        "cleanup-crm-demo",
        "dry-run-crm-demo",
        "commit-agreement-fields",
        "dry-run-agreement-fields",
        "commit-final-normalization",
        "dry-run-final-normalization",
        "commit-workbook-correction",
        "dry-run-workbook-correction",
    }:
        from uuid import UUID

        from investhome_api.db.session import SessionLocal
        from investhome_api.services.permission_service import load_user_with_roles

        db = SessionLocal()
        try:
            from investhome_api.services.crm.bitrix_field_backfill import (
                run_bitrix_junk_field_backfill,
            )
            from investhome_api.services.crm.bitrix_pipeline_commit import run_bitrix_pipeline

            if args.command in {"dry-run-forensic", "commit-forensic"}:
                from investhome_api.services.crm.bitrix_forensic_repair import (
                    run_bitrix_forensic_repair,
                )

                actor = load_user_with_roles(db, UUID(args.actor_user_id))
                if actor is None:
                    raise ValueError("authorized actor not found")
                result = run_bitrix_forensic_repair(
                    db,
                    bundle,
                    actor=actor,
                    dry_run=args.command == "dry-run-forensic",
                )
                if args.command == "commit-forensic":
                    db.commit()
            elif args.command == "dry-run-pipeline":
                result = run_bitrix_pipeline(db, bundle, actor=None, dry_run=True)
            elif args.command == "dry-run-junk-fields":
                result = run_bitrix_junk_field_backfill(db, bundle, actor=None, dry_run=True)
            elif args.command in {"dry-run-crm-demo", "cleanup-crm-demo"}:
                from investhome_api.services.crm.demo_cleanup import cleanup_crm_demo_records

                result = cleanup_crm_demo_records(
                    db, dry_run=args.command == "dry-run-crm-demo"
                )
                if args.command == "cleanup-crm-demo":
                    db.commit()
            elif args.command in {"dry-run-agreement-fields", "commit-agreement-fields"}:
                from investhome_api.services.crm.bitrix_agreement_unit_phone_repair import (
                    repair_agreement_units_and_phones,
                )

                result = repair_agreement_units_and_phones(
                    db,
                    bundle,
                    dry_run=args.command == "dry-run-agreement-fields",
                )
                if args.command == "commit-agreement-fields":
                    db.commit()
            elif args.command in {"dry-run-final-normalization", "commit-final-normalization"}:
                from investhome_api.services.crm.bitrix_final_normalization import (
                    run_bitrix_final_normalization,
                )

                result = run_bitrix_final_normalization(
                    db,
                    bundle,
                    rescue_xlsx=Path(args.rescue_xlsx) if getattr(args, "rescue_xlsx", None) else None,
                    reconciliation_xlsx=Path(args.xlsx_out) if getattr(args, "xlsx_out", None) else None,
                    dry_run=args.command == "dry-run-final-normalization",
                )
                if args.command == "commit-final-normalization":
                    db.commit()
            elif args.command in {"dry-run-workbook-correction", "commit-workbook-correction"}:
                from investhome_api.services.crm.bitrix_workbook_correction import (
                    run_bitrix_workbook_correction,
                )

                result = run_bitrix_workbook_correction(
                    db,
                    bundle,
                    rescue_xlsx=Path(args.rescue_xlsx),
                    original_xlsx=Path(args.original_xlsx) if getattr(args, "original_xlsx", None) else None,
                    dry_run=args.command == "dry-run-workbook-correction",
                )
                if args.command == "commit-workbook-correction":
                    db.commit()
            else:
                actor = load_user_with_roles(db, UUID(args.actor_user_id))
                if actor is None:
                    raise ValueError("authorized actor not found")
                if args.command == "commit":
                    from investhome_api.services.crm.bitrix_commit import commit_safe_bitrix_contacts

                    result = commit_safe_bitrix_contacts(
                        db,
                        bundle,
                        actor=actor,
                        limit=args.limit,
                        offset=args.offset,
                    )
                elif args.command == "commit-comments":
                    from investhome_api.services.crm.bitrix_comment_commit import (
                        commit_safe_historical_comments,
                    )

                    result = commit_safe_historical_comments(db, bundle, actor=actor)
                elif args.command == "commit-agents":
                    from investhome_api.services.crm.bitrix_agent_commit import (
                        commit_safe_agent_roles,
                    )

                    result = commit_safe_agent_roles(db, bundle, actor=actor)
                elif args.command == "commit-pipeline":
                    result = run_bitrix_pipeline(db, bundle, actor=actor, dry_run=False)
                elif args.command == "commit-junk-fields":
                    result = run_bitrix_junk_field_backfill(db, bundle, actor=actor, dry_run=False)
                else:
                    from investhome_api.services.crm.bitrix_agreement_commit import (
                        commit_safe_agreements,
                    )

                    result = commit_safe_agreements(db, bundle, actor=actor)
                if args.command not in {
                    "commit-pipeline",
                    "dry-run-pipeline",
                    "dry-run-junk-fields",
                    "dry-run-crm-demo",
                    "cleanup-crm-demo",
                    "commit-forensic",
                    "dry-run-forensic",
                    "commit-agreement-fields",
                    "dry-run-agreement-fields",
                }:
                    db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        print(result.format_console())
        if getattr(args, "json_out", None):
            out = Path(args.json_out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(
                json.dumps(result.to_dict(), indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            print(f"Wrote {out}")
        return 0

    db = None
    if args.read_db:
        from investhome_api.db.session import SessionLocal

        db = SessionLocal()
    try:
        report = run_bitrix_dry_run(bundle, db=db)
    finally:
        if db is not None:
            db.close()
    print(report.format_console())
    if args.json_out:
        out = Path(args.json_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report.to_dict(), indent=2, default=str) + "\n", encoding="utf-8")
        print(f"Wrote {out}")
    if not source_dir.exists():
        print(f"No source directory at {source_dir} — empty dry-run.")
    return 0


def cli_entry() -> None:
    raise SystemExit(console_main())
