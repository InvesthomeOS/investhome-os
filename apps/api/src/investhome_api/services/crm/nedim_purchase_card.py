"""Nedim Kondu purchase-card pilot: PERSON → PURCHASE/DEAL.

Project-context grouping is disabled. History follows Bitrix ownership.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

NEDIM_CANONICAL_ID = UUID("811c6aed-5f58-4c89-a9b1-0eebed64b9cf")
IZZET_CANONICAL_ID = UUID("339559ed-0d11-4e7c-a021-a07b388a817b")
NEDIM_ALIAS_IDS = {
    UUID("ee093070-b3a4-4fb3-b3ca-3aa92379a187"): NEDIM_CANONICAL_ID,
}

DEAL_198 = "198"
DEAL_656 = "656"
DEAL_720 = "720"
NEDIM_DEAL_IDS = {DEAL_198, DEAL_656, DEAL_720}

AGREEMENT_198 = UUID("d30d258a-3b89-458a-bfa0-a2de4f9f0ba2")
AGREEMENT_656 = UUID("bdfd5ca1-e491-4896-b5d4-4b401ef428ac")
AGREEMENT_720 = UUID("444f6517-595a-4067-9c0c-3521708d2223")
NEDIM_AGREEMENT_IDS = {AGREEMENT_198, AGREEMENT_656, AGREEMENT_720}

DEAL_TO_AGREEMENT = {
    DEAL_198: AGREEMENT_198,
    DEAL_656: AGREEMENT_656,
    DEAL_720: AGREEMENT_720,
}
AGREEMENT_TO_DEAL = {value: key for key, value in DEAL_TO_AGREEMENT.items()}

DEAL_UF_FILES: dict[str, list[str]] = {
    DEAL_198: ["58484", "58488", "58490"],
    DEAL_656: ["92370", "92434", "92774", "92776", "92778", "92780"],
    DEAL_720: ["96546", "96552", "96548", "96748", "96750", "96752", "96754", "96554"],
}


def resolve_nedim_contact_id(contact_id: UUID) -> UUID:
    return NEDIM_ALIAS_IDS.get(contact_id, contact_id)


def is_nedim_pilot_contact(contact_id: UUID) -> bool:
    return resolve_nedim_contact_id(contact_id) == NEDIM_CANONICAL_ID


def is_pilot_person_page(contact_id: UUID) -> bool:
    resolved = resolve_nedim_contact_id(contact_id)
    return resolved in {NEDIM_CANONICAL_ID, IZZET_CANONICAL_ID}


def is_nedim_purchase_agreement(agreement_id: UUID) -> bool:
    return agreement_id in NEDIM_AGREEMENT_IDS


def _live_meta(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    live = metadata.get("bitrix_live")
    return live if isinstance(live, dict) else {}


def deal_id_for_agreement(agreement_id: UUID, metadata: dict[str, Any] | None = None) -> str | None:
    if agreement_id in AGREEMENT_TO_DEAL:
        return AGREEMENT_TO_DEAL[agreement_id]
    if not isinstance(metadata, dict):
        return None
    live = _live_meta(metadata)
    for value in (
        metadata.get("bitrix_deal_id"),
        live.get("bitrix_deal_id"),
        live.get("deal_id"),
    ):
        text = str(value or "").strip()
        if text.isdigit():
            return text
    ext = str(metadata.get("source_external_id") or "").strip()
    if ext.startswith("bitrix_deal:"):
        token = ext.split(":", 1)[1].strip()
        if token.isdigit():
            return token
    return None


def is_purchase_card_agreement(agreement_id: UUID, metadata: dict[str, Any] | None = None) -> bool:
    return deal_id_for_agreement(agreement_id, metadata) is not None or is_nedim_purchase_agreement(agreement_id)


def _history(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    history = metadata.get("bitrix_history")
    return history if isinstance(history, dict) else {}


def activity_deal_id(metadata: dict[str, Any] | None) -> str | None:
    history = _history(metadata)
    entity_type = str(history.get("bitrix_entity_type") or "").lower()
    entity_id = str(history.get("bitrix_entity_id") or history.get("related_entity_id") or "").strip()
    if entity_type == "deal" and entity_id:
        return entity_id
    deal_id = str(history.get("deal_id") or (metadata or {}).get("deal_id") or "").strip()
    return deal_id or None


def is_deal_owned_activity(metadata: dict[str, Any] | None, deal_id: str | None = None) -> bool:
    owned = activity_deal_id(metadata)
    if not owned:
        return False
    if deal_id is None:
        return True
    return owned == deal_id


def is_person_owned_activity(metadata: dict[str, Any] | None) -> bool:
    return not is_deal_owned_activity(metadata)


def is_whatsapp_activity(metadata: dict[str, Any] | None, activity_type: str | None = None) -> bool:
    if str(activity_type or "").lower() == "whatsapp":
        return True
    history = _history(metadata)
    kind = str(history.get("kind") or "").lower()
    if kind in {"whatsapp_message", "whatsapp_session"}:
        return True
    return bool(history.get("open_channel_summary"))
