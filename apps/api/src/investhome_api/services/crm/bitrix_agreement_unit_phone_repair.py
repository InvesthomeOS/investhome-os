"""Targeted agreement unit + phone repair from original Bitrix Excel.

Does not create contacts or agreements. Does not change project assignments.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, attributes

from investhome_api.models.crm_agreement import CrmAgreement
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.bitrix_import import BitrixBundle, BitrixSourceRow
from investhome_api.services.crm.identity import (
    is_zero_masked_phone,
    normalize_valid_email,
    parse_phone,
    phone_digits,
    phone_is_better,
    prefer_better_phone,
)


def _external_id(row: BitrixSourceRow) -> str | None:
    bitrix_id = (row.bitrix_id or "").strip()
    if not bitrix_id:
        return None
    return f"{row.source_file}:{bitrix_id}"


def _safe_display_phone(raw: str | None) -> str | None:
    if not raw or not str(raw).strip():
        return None
    original = str(raw).strip()
    parsed = parse_phone(original)
    if parsed and parsed.e164 and not parsed.suspicious and not is_zero_masked_phone(original):
        return parsed.e164
    return original[:50]


def _best_phones_by_email(bundle: BitrixBundle) -> dict[str, str]:
    best: dict[str, str] = {}
    for row in bundle.rows:
        emails = [row.email, *(row.emails or [])]
        phones = [row.phone, row.raw_source_phone, *(row.phones or [])]
        for email in emails:
            key = normalize_valid_email(email)
            if not key:
                continue
            for raw in phones:
                if not raw or is_zero_masked_phone(raw):
                    continue
                if phone_is_better(raw, best.get(key)):
                    best[key] = raw
    return best


def _row_label(row: BitrixSourceRow) -> dict[str, Any]:
    return {
        "source_file": row.source_file,
        "bitrix_id": row.bitrix_id,
        "name": row.full_name,
        "deal_name": row.deal_name,
        "email": row.email,
        "unit_number": row.unit_number,
        "raw_source_phone": row.raw_source_phone or row.phone,
    }


@dataclass
class AgreementUnitPhoneRepairReport:
    dry_run: bool
    agreement_count: int
    units_found: list[dict[str, Any]] = field(default_factory=list)
    units_missing_in_source: list[dict[str, Any]] = field(default_factory=list)
    phones_affected: list[dict[str, Any]] = field(default_factory=list)
    phones_repaired: list[dict[str, Any]] = field(default_factory=list)
    phones_unresolved: list[dict[str, Any]] = field(default_factory=list)
    phones_ambiguous_source: list[dict[str, Any]] = field(default_factory=list)
    contacts_before: int = 0
    contacts_after: int = 0
    contacts_created: int = 0
    project_groups_before: dict[str, int] = field(default_factory=dict)
    project_groups_after: dict[str, int] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["units_found_count"] = len(self.units_found)
        payload["units_missing_count"] = len(self.units_missing_in_source)
        payload["phones_affected_count"] = len(self.phones_affected)
        payload["phones_repaired_count"] = len(self.phones_repaired)
        payload["phones_unresolved_count"] = len(self.phones_unresolved)
        payload["phones_ambiguous_source_count"] = len(self.phones_ambiguous_source)
        return payload

    def format_console(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)


def _project_counts(agreements: list[CrmAgreement]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in agreements:
        counts[row.project_group] += 1
    return dict(counts)


def repair_agreement_units_and_phones(
    db: Session,
    bundle: BitrixBundle,
    *,
    dry_run: bool,
) -> AgreementUnitPhoneRepairReport:
    agreements = list(db.query(CrmAgreement).all())
    contacts = {row.id: row for row in db.query(CrmContact).all()}
    by_external: dict[str, CrmAgreement] = {
        f"{row.source}:{row.source_external_id}": row
        for row in agreements
        if row.source_external_id
    }
    by_source_id: dict[str, CrmAgreement] = {
        row.source_external_id: row for row in agreements if row.source_external_id
    }
    best_by_email = _best_phones_by_email(bundle)
    report = AgreementUnitPhoneRepairReport(
        dry_run=dry_run,
        agreement_count=len(agreements),
        contacts_before=len(contacts),
        project_groups_before=_project_counts(agreements),
        notes=[
            "Does not create contacts or agreements.",
            "Does not change project assignments.",
            "Phone cells are read as lossless text; masked trailing zeros are not inferred.",
        ],
    )

    agreement_rows = [row for row in bundle.rows if row.role == "agreements"]
    seen_agreements: set[UUID] = set()

    for row in agreement_rows:
        external = _external_id(row)
        existing = None
        if external:
            existing = by_source_id.get(external) or by_external.get(f"bitrix:{external}")
        if existing is None:
            report.notes.append(f"unmatched_source_row:{row.source_file}:{row.bitrix_id}")
            continue
        seen_agreements.add(existing.id)
        contact = contacts.get(existing.contact_id)
        label = _row_label(row)
        label["agreement_id"] = str(existing.id)
        label["project_group"] = existing.project_group

        if existing.project_group == "reit":
            if not dry_run and existing.unit_number:
                existing.unit_number = None
        elif row.unit_number:
            report.units_found.append({**label, "unit_number": row.unit_number})
            if not dry_run and existing.unit_number != row.unit_number:
                existing.unit_number = row.unit_number[:80]
        else:
            report.units_missing_in_source.append(label)

        raw_source = row.raw_source_phone or row.phone
        row_email = normalize_valid_email(row.email)
        contact_email = normalize_valid_email(contact.primary_email) if contact else None
        emails_match = True
        if row_email and contact_email:
            emails_match = row_email == contact_email
        email_key = row_email or (contact_email if emails_match else None)
        recovered = best_by_email.get(email_key) if email_key else None
        if recovered and is_zero_masked_phone(recovered):
            recovered = None
        chosen_raw = recovered if phone_is_better(recovered, raw_source) else raw_source
        chosen_display = _safe_display_phone(chosen_raw)
        current_contact_phone = contact.primary_phone if contact else None
        current_meta = existing.metadata_json if isinstance(existing.metadata_json, dict) else {}
        current_meta_phone = current_meta.get("contact_phone") if isinstance(current_meta, dict) else None
        displayed_now = prefer_better_phone(current_contact_phone, str(current_meta_phone) if current_meta_phone else None)

        source_ambiguous = is_zero_masked_phone(raw_source)
        affected = source_ambiguous or is_zero_masked_phone(displayed_now) or is_zero_masked_phone(
            str(current_meta_phone) if current_meta_phone else None
        )
        if affected:
            report.phones_affected.append(
                {
                    **label,
                    "raw_source_phone": raw_source,
                    "stored_contact_phone": current_contact_phone,
                    "stored_metadata_phone": current_meta_phone,
                }
            )
        if source_ambiguous:
            report.phones_ambiguous_source.append({**label, "raw_source_phone": raw_source})

        repaired = False
        contact_phone_for_agreement = current_contact_phone if emails_match else None
        if not dry_run and contact is not None and emails_match:
            if (
                chosen_display
                and not is_zero_masked_phone(chosen_display)
                and phone_is_better(chosen_display, contact.primary_phone)
            ):
                if not contact.primary_phone or is_zero_masked_phone(contact.primary_phone):
                    contact.primary_phone = chosen_display[:50]
                    repaired = True
            elif (
                contact.primary_phone
                and is_zero_masked_phone(contact.primary_phone)
                and raw_source
                and phone_digits(contact.primary_phone) != phone_digits(raw_source)
            ):
                contact.primary_phone = raw_source[:50]
                repaired = True
            contact_phone_for_agreement = contact.primary_phone
        metadata = dict(existing.metadata_json or {})
        fields = dict(metadata.get("agreement_fields") or {}) if isinstance(metadata.get("agreement_fields"), dict) else {}
        display_for_meta = prefer_better_phone(chosen_display, contact_phone_for_agreement if emails_match else None)
        would_repair_meta = bool(
            display_for_meta
            and (
                is_zero_masked_phone(str(metadata.get("contact_phone") or ""))
                or not metadata.get("contact_phone")
            )
            and metadata.get("contact_phone") != display_for_meta
        )
        if not dry_run:
            metadata["raw_source_phone"] = raw_source
            if row.unit_number:
                metadata["unit_number"] = row.unit_number
                fields["unit_number"] = row.unit_number
            if row.deal_name:
                metadata["deal_name"] = row.deal_name
                fields["deal_name"] = row.deal_name
            if row.product:
                metadata["product"] = row.product
                fields["product"] = row.product
            if not emails_match:
                metadata["contact_phone"] = chosen_display
            elif would_repair_meta:
                metadata["contact_phone"] = display_for_meta
                repaired = True
            elif display_for_meta:
                metadata["contact_phone"] = prefer_better_phone(
                    str(metadata.get("contact_phone") or ""), display_for_meta
                ) or display_for_meta
            fields["phone"] = metadata.get("contact_phone")
            fields["raw_source_phone"] = raw_source
            metadata["agreement_fields"] = {key: value for key, value in fields.items() if value}
            existing.metadata_json = metadata
            attributes.flag_modified(existing, "metadata_json")
        elif would_repair_meta or (
            contact is not None
            and emails_match
            and chosen_display
            and not is_zero_masked_phone(chosen_display)
            and phone_is_better(chosen_display, contact.primary_phone)
            and (not contact.primary_phone or is_zero_masked_phone(contact.primary_phone))
        ):
            repaired = True

        final_display = prefer_better_phone(
            contact.primary_phone if contact else None,
            str(metadata.get("contact_phone") or "") or None,
            chosen_display,
        )
        if repaired:
            report.phones_repaired.append(
                {
                    **label,
                    "raw_source_phone": raw_source,
                    "repaired_phone": final_display,
                    "recovered_from_email_match": bool(recovered and recovered != raw_source),
                }
            )
        if affected and (not final_display or is_zero_masked_phone(final_display)):
            report.phones_unresolved.append(
                {
                    **label,
                    "raw_source_phone": raw_source,
                    "final_phone": final_display,
                    "reason": "source_masked_or_missing_no_better_email_match",
                }
            )

    missing_source = [row for row in agreements if row.id not in seen_agreements]
    if missing_source:
        report.notes.append(f"db_agreements_without_source_row:{len(missing_source)}")

    if dry_run:
        report.contacts_after = report.contacts_before
        report.project_groups_after = report.project_groups_before
        return report

    db.flush()
    report.contacts_after = db.query(CrmContact).count()
    report.project_groups_after = _project_counts(list(db.query(CrmAgreement).all()))
    report.agreement_count = db.query(CrmAgreement).count()
    report.contacts_created = report.contacts_after - report.contacts_before
    return report
