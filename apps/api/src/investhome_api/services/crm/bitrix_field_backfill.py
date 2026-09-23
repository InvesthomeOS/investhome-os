"""Idempotent Bitrix Junk field backfill onto existing CrmContact rows.

Never creates contacts. Never overwrites existing non-empty values.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session, attributes

import investhome_api.models  # noqa: F401

from investhome_api.models.crm_contact import CrmContact, CrmContactStatus
from investhome_api.models.lead import Lead
from investhome_api.models.sales import SalesOpportunity
from investhome_api.models.user_auth import User
from investhome_api.services.crm.bitrix_commit import BitrixCommitPermissionError
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.identity import normalize_valid_email, parse_phone
from investhome_api.services.permission_service import user_has_permission

_METADATA_KEY = "bitrix_import"
_LOCK_NAME = "bitrix-junk-field-backfill"
_SOURCE = "Bitrix"


@dataclass
class FieldCompleteness:
    excel_filled: int = 0
    in_db: int = 0
    missing_from_db: int = 0
    empty_in_excel: int = 0
    hidden_by_ui: int = 0


@dataclass
class BitrixFieldBackfillReport:
    dry_run: bool
    junk_source_rows: int
    matched_rows: int
    unmatched_rows: int
    ambiguous_rows: int
    contacts_updated: int
    contacts_skipped: int
    fields_backfilled: dict[str, int]
    completeness: dict[str, FieldCompleteness]
    contacts_count_before: int
    contacts_count_after: int
    leads_count_before: int
    leads_count_after: int
    opportunities_count_before: int
    opportunities_count_after: int
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["completeness"] = {
            key: asdict(value) for key, value in self.completeness.items()
        }
        return payload

    def format_console(self) -> str:
        payload = self.to_dict()
        lines = [
            "BITRIX JUNK FIELD " + ("DRY-RUN (zero writes)" if self.dry_run else "BACKFILL"),
            "",
        ]
        for key, value in payload.items():
            if key in {"notes", "completeness"}:
                continue
            lines.append(f"{key}: {value}")
        lines.append("completeness:")
        for field_name, stats in (payload.get("completeness") or {}).items():
            lines.append(f"  {field_name}: {stats}")
        if self.notes:
            lines.append("notes:")
            lines.extend(f"  - {note}" for note in self.notes)
        return "\n".join(lines)


def _db_counts(db: Session) -> dict[str, int]:
    return {
        "crm_contacts": db.query(CrmContact).count(),
        "leads": db.query(Lead).count(),
        "sales_opportunities": db.query(SalesOpportunity).count(),
    }


def _acquire_lock(db: Session) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:name))"), {"name": _LOCK_NAME})


def _safe_phone(value: str | None) -> str | None:
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    return None


def _unique_phones(*groups: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group or []:
            phone = _safe_phone(value) or (value.strip() if value and value.strip() else None)
            if phone and phone not in seen:
                seen.add(phone)
                out.append(phone)
    return out


def _unique_emails(*groups: list[str] | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for value in group or []:
            email = normalize_valid_email(value) or (
                value.strip().lower() if value and "@" in value else None
            )
            if email and email not in seen:
                seen.add(email)
                out.append(email)
    return out


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y",
        "%d/%m/%Y",
    ):
        try:
            parsed = datetime.strptime(text[:19] if "T" in text or " " in text else text[:10], fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _row_phones(row: BitrixSourceRow) -> list[str]:
    return _unique_phones([row.phone] if row.phone else [], row.phones)


def _row_emails(row: BitrixSourceRow) -> list[str]:
    return _unique_emails([row.email] if row.email else [], row.emails)


def _contact_phones(contact: CrmContact) -> list[str]:
    return _unique_phones(
        [contact.primary_phone] if contact.primary_phone else [],
        contact.secondary_phones,
        [contact.whatsapp] if contact.whatsapp else [],
    )


def _contact_emails(contact: CrmContact) -> list[str]:
    return _unique_emails(
        [contact.primary_email] if contact.primary_email else [],
        contact.secondary_emails,
    )


def _bitrix_meta(contact: CrmContact) -> dict[str, Any]:
    metadata = contact.metadata_json or {}
    bitrix = metadata.get(_METADATA_KEY)
    return dict(bitrix) if isinstance(bitrix, dict) else {}


def _index_contacts(contacts: list[CrmContact]) -> tuple[
    dict[str, set[UUID]],
    dict[str, set[UUID]],
    dict[str, set[UUID]],
]:
    by_phone: dict[str, set[UUID]] = defaultdict(set)
    by_email: dict[str, set[UUID]] = defaultdict(set)
    by_external: dict[str, set[UUID]] = defaultdict(set)
    for contact in contacts:
        for phone in _contact_phones(contact):
            by_phone[phone].add(contact.id)
        for email in _contact_emails(contact):
            by_email[email].add(contact.id)
        values = _bitrix_meta(contact).get("external_ids")
        if isinstance(values, list):
            for item in values:
                if item:
                    by_external[str(item)].add(contact.id)
    return by_phone, by_email, by_external


def match_source_row(
    row: BitrixSourceRow,
    *,
    by_phone: dict[str, set[UUID]],
    by_email: dict[str, set[UUID]],
    by_external: dict[str, set[UUID]],
) -> tuple[UUID | None, str]:
    if row.bitrix_id and row.bitrix_id.strip():
        external_ref = f"{row.source_file}:{row.bitrix_id.strip()}"
        found = by_external.get(external_ref, set())
        if len(found) == 1:
            return next(iter(found)), "matched"
        if len(found) > 1:
            return None, "ambiguous"

    hits: set[UUID] = set()
    for phone in _row_phones(row):
        found = by_phone.get(phone, set())
        if len(found) > 1:
            return None, "ambiguous"
        hits |= found
    for email in _row_emails(row):
        found = by_email.get(email, set())
        if len(found) > 1:
            return None, "ambiguous"
        hits |= found
    if not hits:
        return None, "unmatched"
    if len(hits) > 1:
        return None, "ambiguous"
    return next(iter(hits)), "matched"


_COLUMN_LIMITS = {
    "first_name": 120,
    "last_name": 120,
    "organization_name": 255,
    "job_title": 120,
    "address_line1": 255,
    "address_line2": 255,
    "city": 120,
    "postal_code": 30,
    "country": 100,
    "website": 500,
    "primary_email": 255,
    "primary_phone": 50,
    "whatsapp": 50,
    "junk_reason": 255,
}


def _clip(value: Any, limit: int | None) -> Any:
    if value is None or limit is None or not isinstance(value, str):
        return value
    text = value.strip()
    if not text:
        return None
    if len(text) <= limit:
        return text
    return None


def _fill_if_empty(contact: CrmContact, field_name: str, value: Any) -> bool:
    clipped = _clip(value, _COLUMN_LIMITS.get(field_name))
    if clipped in (None, "", []):
        return False
    current = getattr(contact, field_name)
    if current in (None, "", []):
        setattr(contact, field_name, clipped)
        return True
    return False


def _merge_list(existing: list[str] | None, incoming: list[str], *, skip: set[str]) -> list[str]:
    out = list(existing or [])
    seen = {item for item in out}
    seen.update(skip)
    changed = False
    for item in incoming:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
            changed = True
    return out if changed or existing else out


def _apply_row(contact: CrmContact, row: BitrixSourceRow) -> dict[str, int]:
    written: dict[str, int] = defaultdict(int)
    phones = _row_phones(row)
    emails = _row_emails(row)
    existing_phones = set(_contact_phones(contact))
    existing_emails = set(_contact_emails(contact))

    if phones and _fill_if_empty(contact, "primary_phone", phones[0]):
        written["primary_phone"] += 1
        existing_phones.add(phones[0])
    extra_phones = [item for item in phones[1:] if item not in existing_phones]
    if extra_phones:
        merged = _merge_list(contact.secondary_phones, extra_phones, skip=existing_phones)
        if merged != (contact.secondary_phones or []):
            contact.secondary_phones = merged
            written["secondary_phones"] += len(extra_phones)
            attributes.flag_modified(contact, "secondary_phones")

    if emails and _fill_if_empty(contact, "primary_email", emails[0]):
        written["primary_email"] += 1
        existing_emails.add(emails[0])
    extra_emails = [item for item in emails[1:] if item not in existing_emails]
    if extra_emails:
        merged = _merge_list(contact.secondary_emails, extra_emails, skip=existing_emails)
        if merged != (contact.secondary_emails or []):
            contact.secondary_emails = merged
            written["secondary_emails"] += len(extra_emails)
            attributes.flag_modified(contact, "secondary_emails")

    whatsapp = _safe_phone(row.whatsapp)
    if whatsapp and _fill_if_empty(contact, "whatsapp", whatsapp):
        written["whatsapp"] += 1

    if _fill_if_empty(contact, "organization_name", row.company):
        written["company"] += 1
    if _fill_if_empty(contact, "job_title", row.job_title):
        written["job_title"] += 1
    if _fill_if_empty(contact, "address_line1", row.address):
        written["address"] += 1
    if _fill_if_empty(contact, "address_line2", row.address_line2):
        written["address_line2"] += 1
    if _fill_if_empty(contact, "city", row.city):
        written["city"] += 1
    if _fill_if_empty(contact, "postal_code", row.postal_code):
        written["postal_code"] += 1
    if _fill_if_empty(contact, "country", row.country):
        written["country"] += 1
    if _fill_if_empty(contact, "website", row.website):
        written["website"] += 1
    if _fill_if_empty(contact, "first_name", row.first_name):
        written["first_name"] += 1
    if _fill_if_empty(contact, "last_name", row.last_name):
        written["last_name"] += 1
    if row.comment and _fill_if_empty(contact, "notes", row.comment):
        written["notes"] += 1

    last_contact = _parse_datetime(row.last_contact_at)
    if last_contact and contact.last_contact_at is None:
        contact.last_contact_at = last_contact
        written["last_contact_at"] += 1

    if row.junk_reason and _fill_if_empty(contact, "junk_reason", row.junk_reason):
        written["junk_reason"] += 1
        if contact.junked_at is None and contact.status == CrmContactStatus.ARCHIVED:
            contact.junked_at = last_contact or datetime.now(timezone.utc)
            written["junked_at"] += 1

    metadata = dict(contact.metadata_json or {})
    bitrix = dict(metadata.get(_METADATA_KEY) or {})
    extras = dict(bitrix.get("source_extras") or {})
    extra_changed = False
    for key, value in {
        "source_channel": row.source_channel,
        "responsible": row.responsible,
        "bitrix_created_at": row.bitrix_created_at,
        "open_channel": row.open_channel,
        "original_asama": row.stage or extras.get("original_asama"),
        "junk_reason": row.junk_reason or extras.get("junk_reason"),
        "position_raw": row.job_title if row.job_title and len(row.job_title) > 120 else extras.get("position_raw"),
    }.items():
        if value and extras.get(key) != value:
            extras[key] = value
            extra_changed = True
    if extra_changed:
        bitrix["source_extras"] = extras
        if row.source_channel:
            bitrix["source_channel"] = row.source_channel
        if row.stage and not bitrix.get("original_asama"):
            bitrix["original_asama"] = row.stage
        metadata[_METADATA_KEY] = bitrix
        contact.metadata_json = metadata
        attributes.flag_modified(contact, "metadata_json")
        written["metadata"] += 1
    return dict(written)


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return any(_present(item) for item in value)
    return True


def _classify_row(
    *,
    excel_value: Any,
    db_value: Any,
    hidden: bool,
    stats: FieldCompleteness,
) -> None:
    if not _present(excel_value):
        stats.empty_in_excel += 1
        return
    stats.excel_filled += 1
    if _present(db_value):
        stats.in_db += 1
        if hidden:
            stats.hidden_by_ui += 1
    else:
        stats.missing_from_db += 1


def run_bitrix_junk_field_backfill(
    db: Session,
    bundle: BitrixBundle,
    *,
    actor: User | None,
    dry_run: bool,
) -> BitrixFieldBackfillReport:
    if not dry_run:
        if actor is None:
            raise BitrixCommitPermissionError("authorized actor required")
        if not user_has_permission(actor, "crm", "import", db=db):
            raise BitrixCommitPermissionError("crm.import permission required")

    before = _db_counts(db)
    junk_rows = [row for row in bundle.rows if row.role == "junk"]
    contacts = list(db.scalars(select(CrmContact)).all())
    by_phone, by_email, by_external = _index_contacts(contacts)
    by_id = {contact.id: contact for contact in contacts}

    completeness = {
        "display_name": FieldCompleteness(),
        "primary_phone": FieldCompleteness(),
        "additional_phone": FieldCompleteness(),
        "primary_email": FieldCompleteness(),
        "additional_email": FieldCompleteness(),
        "whatsapp": FieldCompleteness(),
        "company": FieldCompleteness(),
        "position": FieldCompleteness(),
        "source_channel": FieldCompleteness(),
        "responsible": FieldCompleteness(),
        "created_date": FieldCompleteness(),
        "last_contact": FieldCompleteness(),
        "stage": FieldCompleteness(),
        "junk_reason": FieldCompleteness(),
        "address": FieldCompleteness(),
    }

    matched = 0
    unmatched = 0
    ambiguous = 0
    updated_ids: set[UUID] = set()
    skipped = 0
    fields_backfilled: dict[str, int] = defaultdict(int)
    plans: list[tuple[CrmContact, BitrixSourceRow]] = []

    for row in junk_rows:
        contact_id, status = match_source_row(
            row,
            by_phone=by_phone,
            by_email=by_email,
            by_external=by_external,
        )
        if status == "unmatched":
            unmatched += 1
            continue
        if status == "ambiguous":
            ambiguous += 1
            continue
        contact = by_id[contact_id]
        matched += 1
        phones = _row_phones(row)
        emails = _row_emails(row)
        db_phones = _contact_phones(contact)
        db_emails = _contact_emails(contact)
        extras = (_bitrix_meta(contact).get("source_extras") or {}) if isinstance(
            _bitrix_meta(contact).get("source_extras"), dict
        ) else {}
        _classify_row(
            excel_value=row.full_name,
            db_value=contact.display_name,
            hidden=False,
            stats=completeness["display_name"],
        )
        _classify_row(
            excel_value=phones[:1],
            db_value=contact.primary_phone,
            hidden=False,
            stats=completeness["primary_phone"],
        )
        _classify_row(
            excel_value=phones[1:],
            db_value=contact.secondary_phones,
            hidden=_present(contact.secondary_phones),
            stats=completeness["additional_phone"],
        )
        _classify_row(
            excel_value=emails[:1],
            db_value=contact.primary_email,
            hidden=False,
            stats=completeness["primary_email"],
        )
        _classify_row(
            excel_value=emails[1:],
            db_value=contact.secondary_emails,
            hidden=_present(contact.secondary_emails),
            stats=completeness["additional_email"],
        )
        _classify_row(
            excel_value=row.whatsapp,
            db_value=contact.whatsapp,
            hidden=_present(contact.whatsapp),
            stats=completeness["whatsapp"],
        )
        _classify_row(
            excel_value=row.company,
            db_value=contact.organization_name,
            hidden=_present(contact.organization_name),
            stats=completeness["company"],
        )
        _classify_row(
            excel_value=row.job_title,
            db_value=contact.job_title,
            hidden=_present(contact.job_title),
            stats=completeness["position"],
        )
        _classify_row(
            excel_value=row.source_channel,
            db_value=extras.get("source_channel") or _bitrix_meta(contact).get("source_channel"),
            hidden=True,
            stats=completeness["source_channel"],
        )
        _classify_row(
            excel_value=row.responsible,
            db_value=extras.get("responsible"),
            hidden=True,
            stats=completeness["responsible"],
        )
        _classify_row(
            excel_value=row.bitrix_created_at,
            db_value=extras.get("bitrix_created_at"),
            hidden=True,
            stats=completeness["created_date"],
        )
        _classify_row(
            excel_value=row.last_contact_at,
            db_value=contact.last_contact_at,
            hidden=_present(contact.last_contact_at),
            stats=completeness["last_contact"],
        )
        _classify_row(
            excel_value=row.stage,
            db_value=_bitrix_meta(contact).get("original_asama"),
            hidden=False,
            stats=completeness["stage"],
        )
        _classify_row(
            excel_value=row.junk_reason,
            db_value=contact.junk_reason,
            hidden=False,
            stats=completeness["junk_reason"],
        )
        _classify_row(
            excel_value=row.address,
            db_value=contact.address_line1,
            hidden=_present(contact.address_line1),
            stats=completeness["address"],
        )
        plans.append((contact, row))

    if not dry_run:
        with db.begin_nested():
            _acquire_lock(db)
            for contact, row in plans:
                written = _apply_row(contact, row)
                if written:
                    updated_ids.add(contact.id)
                    for key, count in written.items():
                        fields_backfilled[key] += count
                else:
                    skipped += 1
            db.flush()
        db.commit()
    else:
        for contact, row in plans:
            probe = CrmContact(
                contact_type=contact.contact_type,
                display_name=contact.display_name,
                primary_phone=contact.primary_phone,
                secondary_phones=list(contact.secondary_phones or []),
                primary_email=contact.primary_email,
                secondary_emails=list(contact.secondary_emails or []),
                whatsapp=contact.whatsapp,
                organization_name=contact.organization_name,
                job_title=contact.job_title,
                address_line1=contact.address_line1,
                address_line2=contact.address_line2,
                city=contact.city,
                postal_code=contact.postal_code,
                country=contact.country,
                website=contact.website,
                first_name=contact.first_name,
                last_name=contact.last_name,
                notes=contact.notes,
                last_contact_at=contact.last_contact_at,
                junk_reason=contact.junk_reason,
                junked_at=contact.junked_at,
                status=contact.status,
                metadata_json=dict(contact.metadata_json or {}),
            )
            written = _apply_row(probe, row)
            if written:
                updated_ids.add(contact.id)
                for key, count in written.items():
                    fields_backfilled[key] += count
            else:
                skipped += 1

    after = before if dry_run else _db_counts(db)
    return BitrixFieldBackfillReport(
        dry_run=dry_run,
        junk_source_rows=len(junk_rows),
        matched_rows=matched,
        unmatched_rows=unmatched,
        ambiguous_rows=ambiguous,
        contacts_updated=len(updated_ids),
        contacts_skipped=skipped,
        fields_backfilled=dict(fields_backfilled),
        completeness=completeness,
        contacts_count_before=before["crm_contacts"],
        contacts_count_after=after["crm_contacts"],
        leads_count_before=before["leads"],
        leads_count_after=after["leads"],
        opportunities_count_before=before["sales_opportunities"],
        opportunities_count_after=after["sales_opportunities"],
        notes=[
            "Backfill targets existing CrmContact rows only.",
            "Empty CRM fields are filled from Junklar.xls; existing values are kept.",
            "Junk Sebebi is preserved exactly from the Excel column.",
            "WhatsApp is only written from an explicit WhatsApp source column.",
            "Bitrix Kaynak / Sorumlu / created date are stored on contact metadata when missing.",
        ],
    )
