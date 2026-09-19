"""Nedim Kondu project-context card pilot.

One canonical person. Project cards are contextual views, not split contacts.
Classification uses deterministic deal/project/unit evidence only.
"""
from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from investhome_api.services.crm.bitrix_project_aliases import BITRIX_PROJECT_GROUP_LABELS, BitrixProjectGroup

NEDIM_CANONICAL_ID = UUID("811c6aed-5f58-4c89-a9b1-0eebed64b9cf")
NEDIM_ALIAS_IDS = {
    UUID("ee093070-b3a4-4fb3-b3ca-3aa92379a187"): NEDIM_CANONICAL_ID,
}

UNILOFT = BitrixProjectGroup.UNILOFT.value
ONTARIO = BitrixProjectGroup.ONTARIO_2319.value
GENERAL = "general"
ALL_PROJECTS = "all"

DEAL_TO_PROJECT: dict[str, str] = {
    "198": ONTARIO,
    "656": UNILOFT,
    "720": UNILOFT,
}

PROJECT_LABELS: dict[str, str] = {
    UNILOFT: BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup.UNILOFT],
    ONTARIO: BITRIX_PROJECT_GROUP_LABELS[BitrixProjectGroup.ONTARIO_2319],
}

UNILOFT_RE = re.compile(r"uniloft", re.I)
ONTARIO_RE = re.compile(r"2319\s*ontario|\bontario\b", re.I)
UNIT_209_RE = re.compile(r"(?<!\d)209(?!\d)")


def resolve_nedim_contact_id(contact_id: UUID) -> UUID:
    return NEDIM_ALIAS_IDS.get(contact_id, contact_id)


def is_nedim_pilot_contact(contact_id: UUID) -> bool:
    return resolve_nedim_contact_id(contact_id) == NEDIM_CANONICAL_ID


def normalize_project_context(value: str | None) -> str:
    text = (value or ALL_PROJECTS).strip().lower().replace(" ", "_")
    if text in {UNILOFT, "uni_loft"}:
        return UNILOFT
    if text in {ONTARIO, "ontario", "2319", "2319ontario"}:
        return ONTARIO
    if text in {ALL_PROJECTS, "tum", "tüm", "tum_gecmis", "tüm_geçmiş", ""}:
        return ALL_PROJECTS
    return ALL_PROJECTS


def classify_text(*parts: str | None) -> set[str]:
    blob = " ".join(str(part or "") for part in parts)
    found: set[str] = set()
    if UNILOFT_RE.search(blob):
        found.add(UNILOFT)
    if ONTARIO_RE.search(blob):
        found.add(ONTARIO)
    if UNIT_209_RE.search(blob):
        found.add(UNILOFT)
    return found


def _history_blob(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    history = metadata.get("bitrix_history")
    return history if isinstance(history, dict) else {}


def classify_activity_projects(
    *,
    title: str | None = None,
    description: str | None = None,
    summary: str | None = None,
    metadata: dict[str, Any] | None = None,
    agreement_project_group: str | None = None,
) -> list[str]:
    projects: set[str] = set()
    if agreement_project_group in {UNILOFT, ONTARIO}:
        projects.add(agreement_project_group)
    history = _history_blob(metadata)
    entity_type = str(history.get("bitrix_entity_type") or "").lower()
    entity_id = str(history.get("bitrix_entity_id") or history.get("related_entity_id") or "")
    if entity_type == "deal" and entity_id in DEAL_TO_PROJECT:
        projects.add(DEAL_TO_PROJECT[entity_id])
    deal_id = ""
    if isinstance(metadata, dict):
        deal_id = str(history.get("deal_id") or metadata.get("deal_id") or "")
    if deal_id in DEAL_TO_PROJECT:
        projects.add(DEAL_TO_PROJECT[deal_id])
    projects |= classify_text(title, description, summary)
    return sorted(projects)


def assignment_label(projects: list[str]) -> str:
    if not projects:
        return GENERAL
    if len(projects) == 1:
        return projects[0]
    return "multiple"


def matches_selected_project(projects: list[str], selected: str) -> bool:
    if selected == ALL_PROJECTS:
        return True
    return selected in projects


def filter_tutars_for_project(items: list[dict[str, Any]] | None, selected: str) -> list[dict[str, Any]]:
    rows = [item for item in (items or []) if isinstance(item, dict) and str(item.get("amount") or "").strip()]
    if selected == ALL_PROJECTS:
        return rows
    deal_ids = {deal_id for deal_id, group in DEAL_TO_PROJECT.items() if group == selected}
    return [
        item
        for item in rows
        if str(item.get("deal_id") or item.get("related_entity_id") or "") in deal_ids
    ]


def format_tutars(items: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    amounts = [str(item.get("amount")).strip() for item in items if str(item.get("amount") or "").strip()]
    currencies = list(
        dict.fromkeys(str(item.get("currency") or "").strip() for item in items if str(item.get("currency") or "").strip())
    )
    if not amounts:
        return None, None
    return " | ".join(amounts), " | ".join(currencies) or None


def classify_document_projects(title: str | None, file_name: str | None = None) -> list[str]:
    return sorted(classify_text(title, file_name))


def available_projects() -> list[dict[str, str]]:
    return [{"id": key, "label": label} for key, label in PROJECT_LABELS.items()]
