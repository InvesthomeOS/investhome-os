"""Shared helpers for historical unit-change purchases. Not Bitrix-verified."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_

from investhome_api.models.crm_agreement import CrmAgreement

HISTORICAL_UNIT_CHANGE_SOURCE = "bitrix_unit_change_history"
MANUAL_CONFIRMATION_SOURCE = "manual_business_confirmation"
MANUAL_PROVENANCE = "MANUEL DOĞRULAMA — Kullanıcı tarafından güncel mülkiyet bilgisi"


@dataclass(frozen=True)
class UnitHistoryStep:
    agreement_id: UUID
    unit_number: str
    is_current: bool
    is_historical_unit_change: bool
    contact_id: UUID


def is_historical_unit_change(row: CrmAgreement) -> bool:
    if row.source == HISTORICAL_UNIT_CHANGE_SOURCE:
        return True
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return bool(meta.get("historical_unit_change"))


def historical_unit_change_clause():
    flag = func.lower(func.coalesce(CrmAgreement.metadata_json["historical_unit_change"].as_string(), "false"))
    return or_(CrmAgreement.source == HISTORICAL_UNIT_CHANGE_SOURCE, flag == "true")


def _meta(row: Any) -> dict[str, Any]:
    value = getattr(row, "metadata_json", None)
    return value if isinstance(value, dict) else {}


def _as_uuid(value: Any) -> UUID | None:
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _string_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                return []
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
    return []


def _single_unit(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text or "+" in text or "," in text:
        return None
    return text


def unit_history_steps(focus: Any, siblings: list[Any]) -> list[UnitHistoryStep]:
    """Build a clickable unit chain from stored historical agreement rows only."""
    project = getattr(focus, "project_group", None)
    by_id: dict[UUID, Any] = {}
    for row in siblings:
        if getattr(row, "project_group", None) != project:
            continue
        row_id = getattr(row, "id", None)
        if row_id is not None:
            by_id[row_id] = row
    focus_id = getattr(focus, "id", None)
    if focus_id is not None:
        by_id[focus_id] = focus
    rows = list(by_id.values())
    historical = [row for row in rows if is_historical_unit_change(row)]
    currents = [row for row in rows if not is_historical_unit_change(row)]
    focus_meta = _meta(focus)

    current = None if is_historical_unit_change(focus) else focus
    if current is None:
        replaced = _as_uuid(focus_meta.get("replaced_by_agreement_id"))
        if replaced is not None:
            current = by_id.get(replaced)
        if current is None:
            final_unit = _single_unit(focus_meta.get("final_unit"))
            current = next((row for row in currents if getattr(row, "unit_number", None) == final_unit), None)
        if current is None:
            current = next(
                (
                    row
                    for row in currents
                    if _as_uuid(_meta(row).get("previous_agreement_id")) == focus_id
                ),
                None,
            )
    if current is None:
        return []

    current_meta = _meta(current)
    previous_id = _as_uuid(current_meta.get("previous_agreement_id"))
    previous_units = set(_string_list(current_meta.get("previous_units")))
    original = _single_unit(current_meta.get("original_unit"))
    if original:
        previous_units.add(original)
    sequence = _string_list(current_meta.get("unit_change_sequence"))
    for unit in sequence:
        if unit and unit != getattr(current, "unit_number", None):
            previous_units.add(unit)

    chain_hist: list[Any] = []
    seen: set[UUID] = set()
    for row in historical:
        row_id = getattr(row, "id", None)
        if row_id is None or row_id == getattr(current, "id", None) or row_id in seen:
            continue
        row_meta = _meta(row)
        linked = (
            _as_uuid(row_meta.get("replaced_by_agreement_id")) == getattr(current, "id", None)
            or row_id == previous_id
            or (getattr(row, "unit_number", None) and row.unit_number in previous_units)
            or _single_unit(row_meta.get("final_unit")) == getattr(current, "unit_number", None)
        )
        if not linked:
            continue
        seen.add(row_id)
        chain_hist.append(row)
    if not chain_hist:
        return []

    sequence_index = {unit: index for index, unit in enumerate(sequence)}

    def sort_key(row: Any) -> tuple:
        unit = str(getattr(row, "unit_number", "") or "")
        if unit in sequence_index:
            return (0, sequence_index[unit], "", "")
        stored_date = getattr(row, "agreement_date", None)
        stored_created = getattr(row, "created_at", None)
        date_key = stored_date.isoformat() if stored_date is not None else "9999-12-31"
        created_key = stored_created.isoformat() if stored_created is not None else "9999-12-31T00:00:00"
        return (1, date_key, created_key, unit)

    chain_hist.sort(key=sort_key)
    steps: list[UnitHistoryStep] = []
    for row in chain_hist:
        unit = str(getattr(row, "unit_number", "") or "").strip()
        contact_id = getattr(row, "contact_id", None)
        row_id = getattr(row, "id", None)
        if not unit or row_id is None or contact_id is None:
            continue
        steps.append(
            UnitHistoryStep(
                agreement_id=row_id,
                unit_number=unit,
                is_current=False,
                is_historical_unit_change=True,
                contact_id=contact_id,
            )
        )
    current_unit = str(getattr(current, "unit_number", "") or "").strip()
    current_contact = getattr(current, "contact_id", None)
    current_id = getattr(current, "id", None)
    if current_unit and current_id is not None and current_contact is not None:
        steps.append(
            UnitHistoryStep(
                agreement_id=current_id,
                unit_number=current_unit,
                is_current=True,
                is_historical_unit_change=False,
                contact_id=current_contact,
            )
        )
    if len(steps) < 2 or not any(step.is_current for step in steps):
        return []
    return steps
