"""Global PERSON → PURCHASE card rollout. Bitrix is read-only. Does not delete data."""
from __future__ import annotations

import csv
import json
import os
import re
import urllib.parse
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact, CrmContactStatus, CrmContactType, CrmRecordKind
from investhome_api.models.document import Document, DocumentLink
from investhome_api.schemas.crm_contacts import CrmContactCreate
from investhome_api.services.crm.bitrix_project_aliases import _ALIAS_TO_GROUP, BitrixProjectGroup
from investhome_api.services.crm.contact_service import create_contact
from investhome_api.services.crm.nedim_purchase_card import (
    NEDIM_CANONICAL_ID,
    is_deal_owned_activity,
)

from link_agreement_documents import BitrixClient, ENV_PATH, load_env, webhook_base  # type: ignore

OUT = Path("/tmp/BITRIX_PURCHASE_CARD_ROLLOUT")
LOCKED_720 = UUID("444f6517-595a-4067-9c0c-3521708d2223")
LOCKED_DEALS = {
    "198": UUID("d30d258a-3b89-458a-bfa0-a2de4f9f0ba2"),
    "656": UUID("bdfd5ca1-e491-4896-b5d4-4b401ef428ac"),
    "720": LOCKED_720,
}
UNIT_RE = re.compile(r"(?:unit|daire|apt)\s*[:#\-]?\s*([a-z0-9]+)", re.I)
NON_ALNUM = re.compile(r"[^a-z0-9]+")
BITRIX_CONTACT_RE = re.compile(r"bitrix_contact:(\d+)")


def fold_unit(value: str | None) -> str:
    text = NON_ALNUM.sub("", (value or "").casefold().replace("unit", "").replace("daire", "").replace("apt", ""))
    text = text.lstrip("0") or ("0" if text else "")
    return text


def bitrix_contact_ids(contact: CrmContact) -> set[str]:
    ids: set[str] = set()
    blob = json.dumps(contact.metadata_json or {}, ensure_ascii=False)
    ids.update(BITRIX_CONTACT_RE.findall(blob))
    live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
    if isinstance(live, dict) and live.get("contact_id"):
        ids.add(str(live.get("contact_id")).strip())
    return {item for item in ids if item}


def project_from_text(*parts: str | None) -> str | None:
    blob = " ".join(str(part or "") for part in parts).casefold()
    blob = blob.replace("ı", "i").replace("ş", "s").replace("ğ", "g").replace("ü", "u").replace("ö", "o").replace("ç", "c")
    for alias, group in _ALIAS_TO_GROUP.items():
        if alias in blob:
            return group.value
    return None


def list_all(client: BitrixClient, method: str, payload: dict[str, Any]) -> list[dict]:
    rows: list[dict] = []
    start = 0
    seen: set[int] = set()
    while start not in seen:
        seen.add(start)
        body = client.call(method, {**payload, "start": start})
        result = body.get("result")
        chunk = result if isinstance(result, list) else (result.get("items") if isinstance(result, dict) else [])
        if body.get("error"):
            break
        if not isinstance(chunk, list) or not chunk:
            break
        rows.extend([row for row in chunk if isinstance(row, dict)])
        nxt = body.get("next")
        start = int(nxt) if nxt not in (None, "") else -1
        if start < 0:
            break
    return rows


def file_ids_from_value(value: Any) -> list[str]:
    found: list[str] = []
    if value in (None, "", [], {}, 0, "0"):
        return found
    if isinstance(value, list):
        for item in value:
            found.extend(file_ids_from_value(item))
        return found
    if isinstance(value, dict):
        for key in ("id", "ID", "fileId", "FILE_ID"):
            if value.get(key):
                found.append(str(value.get(key)))
        url = str(value.get("urlMachine") or value.get("downloadUrl") or "")
        match = re.search(r"[?&]fileId=(\d+)", url)
        if match:
            found.append(match.group(1))
        return found
    text = str(value)
    if text.isdigit():
        found.append(text)
    found.extend(re.findall(r"[?&]fileId=(\d+)", text))
    return found


def deal_unit(deal: dict[str, Any], fields: dict[str, Any]) -> str | None:
    title = str(deal.get("TITLE") or "")
    match = UNIT_RE.search(title)
    if match:
        return match.group(1)
    for key, spec in fields.items():
        if not str(key).startswith("UF_"):
            continue
        label = ""
        if isinstance(spec, dict):
            form = spec.get("formLabel") or spec.get("listLabel") or spec.get("title") or {}
            if isinstance(form, dict):
                label = str(form.get("en") or form.get("tr") or next(iter(form.values()), "") or "")
            else:
                label = str(form or spec.get("listLabel") or "")
        if not re.search(r"unit|daire|apt", f"{key} {label}", re.I):
            continue
        value = deal.get(key)
        if value in (None, "", [], {}):
            continue
        if isinstance(value, list):
            value = value[0] if value else ""
        text = str(value).strip()
        if text:
            return text
    digits = re.findall(r"\b([A-Za-z]?\d{1,4}[A-Za-z]?)\b", title)
    return digits[-1] if digits else None


def candidate_deal_ids(row: CrmAgreement) -> list[str]:
    found: list[str] = []
    for locked_id, agreement_id in LOCKED_DEALS.items():
        if row.id == agreement_id:
            found.append(locked_id)
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    for value in (
        meta.get("bitrix_deal_id"),
        live.get("bitrix_deal_id"),
        live.get("deal_id"),
        live.get("ID"),
    ):
        text = str(value or "").strip()
        if text.isdigit():
            found.append(text)
    ext = str(row.source_external_id or "")
    if ext.startswith("bitrix_deal:"):
        token = ext.split(":", 1)[1].strip()
        if token.isdigit():
            found.append(token)
    tail = ext.rsplit(":", 1)[-1].strip()
    if tail.isdigit():
        found.append(tail)
    uniq: list[str] = []
    for item in found:
        if item not in uniq:
            uniq.append(item)
    return uniq


def notes_dict(document: Document) -> dict[str, Any]:
    raw = document.notes
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def upsert_participant(
    db: Session,
    *,
    agreement_id: UUID,
    contact_id: UUID,
    is_primary: bool,
    ownership_pct: Decimal | None,
    deal_id: str,
    bitrix_contact_id: str,
) -> str:
    existing = db.scalar(
        select(CrmAgreementParticipant).where(
            CrmAgreementParticipant.agreement_id == agreement_id,
            CrmAgreementParticipant.contact_id == contact_id,
        )
    )
    if existing is None:
        db.add(
            CrmAgreementParticipant(
                id=uuid4(),
                agreement_id=agreement_id,
                contact_id=contact_id,
                role="owner",
                ownership_pct=ownership_pct,
                is_primary=is_primary,
                source="bitrix_live",
                metadata_json={"bitrix_deal_id": deal_id, "bitrix_contact_id": bitrix_contact_id, "source": "bitrix_live"},
            )
        )
        return "created"
    if agreement_id == LOCKED_720:
        return "kept_locked"
    existing.is_primary = is_primary
    existing.role = "owner"
    existing.source = existing.source or "bitrix_live"
    if ownership_pct is not None and existing.ownership_pct is None:
        existing.ownership_pct = ownership_pct
    meta = dict(existing.metadata_json or {})
    meta["bitrix_deal_id"] = deal_id
    meta["bitrix_contact_id"] = bitrix_contact_id
    existing.metadata_json = meta
    return "updated"


def ensure_contact_from_bitrix(db: Session, client: BitrixClient, contact_id: str, cache: dict[str, CrmContact]) -> CrmContact | None:
    if contact_id in cache:
        return cache[contact_id]
    body = client.call("crm.contact.get", {"id": contact_id})
    result = body.get("result") if isinstance(body.get("result"), dict) else None
    if not result:
        return None
    phones = result.get("PHONE") if isinstance(result.get("PHONE"), list) else []
    emails = result.get("EMAIL") if isinstance(result.get("EMAIL"), list) else []
    phone = None
    email = None
    if phones and isinstance(phones[0], dict):
        phone = str(phones[0].get("VALUE") or "").strip() or None
    if emails and isinstance(emails[0], dict):
        email = str(emails[0].get("VALUE") or "").strip() or None
    first = str(result.get("NAME") or "").strip()
    last = str(result.get("LAST_NAME") or "").strip()
    display = " ".join(part for part in (first, last) if part).strip() or str(result.get("FULL_NAME") or "").strip()
    if not display:
        display = f"Bitrix contact {contact_id}"
    if email:
        existing = db.scalar(select(CrmContact).where(CrmContact.primary_email == email.lower()))
        if existing is not None:
            cache[contact_id] = existing
            return existing
    contact = create_contact(
        db,
        CrmContactCreate(
            contact_type=CrmContactType.BUYER,
            record_kind=CrmRecordKind.PERSON,
            display_name=display,
            first_name=first or None,
            last_name=last or None,
            primary_phone=phone,
            primary_email=email.lower() if email else None,
            source="bitrix_live",
            status=CrmContactStatus.ACTIVE,
        ),
    )
    contact.metadata_json = {
        "bitrix_import": {
            "external_ids": [f"bitrix_contact:{contact_id}"],
            "source_files": ["bitrix_live"],
            "source_roles": ["contact"],
        },
        "bitrix_live": {"contact_id": contact_id, "lead_id": result.get("LEAD_ID") or None},
    }
    db.flush()
    cache[contact_id] = contact
    return contact


def link_documents(db: Session, agreement_id: UUID, deal_id: str, uf_ids: list[str], by_file: dict[str, list[Document]]) -> int:
    linked = 0
    existing = {
        str(item)
        for item in db.scalars(
            select(DocumentLink.document_id).where(
                DocumentLink.entity_type == "crm_agreement",
                DocumentLink.entity_id == agreement_id,
            )
        ).all()
    }
    wanted = set(uf_ids)
    extras = list(
        db.scalars(
            select(Document).where(
                Document.notes.is_not(None),
                Document.notes.ilike("%bitrix_entity_type%"),
                Document.notes.ilike(f"%{deal_id}%"),
            )
        ).all()
    )
    candidates: list[Document] = []
    for file_id in wanted:
        candidates.extend(by_file.get(file_id, []))
    candidates.extend(extras)
    seen: set[UUID] = set()
    for document in candidates:
        if document.id in seen:
            continue
        seen.add(document.id)
        notes = notes_dict(document)
        file_id = str(notes.get("bitrix_file_id") or "").strip()
        entity_type = str(notes.get("bitrix_entity_type") or "").lower()
        entity_id = str(notes.get("bitrix_entity_id") or "").strip()
        ok = (entity_type == "deal" and entity_id == deal_id) or (file_id and file_id in wanted)
        if not ok:
            continue
        if str(document.id) in existing:
            linked += 1
            continue
        db.add(
            DocumentLink(
                id=uuid4(),
                document_id=document.id,
                entity_type="crm_agreement",
                entity_id=agreement_id,
                relationship_type="bitrix_deal",
            )
        )
        existing.add(str(document.id))
        linked += 1
    return linked


def date_only(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    return text[:10]


def main() -> dict[str, Any]:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(exist_ok=True)
    env = load_env(ENV_PATH) if ENV_PATH.exists() else {}
    webhook = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or env.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    if not webhook:
        raise SystemExit("BITRIX_ADMIN_WEBHOOK_URL missing")
    client = BitrixClient(webhook_base(webhook))
    db: Session = SessionLocal()
    report_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "agreements_checked": 0,
        "purchase_cards_enabled": 0,
        "people_with_multiple_purchases": [],
        "joint_purchases": [],
        "secondary_owners_added": 0,
        "new_canonical_contacts": 0,
        "participant_rows_created": 0,
        "deal_documents_linked": 0,
        "deal_history_linked": 0,
        "ambiguous_not_changed": [],
        "ownership_conflicts": [],
        "duplicate_agreements": [],
        "final_agreement_count": 0,
    }
    try:
        agreements = list(db.scalars(select(CrmAgreement)).all())
        contacts = {row.id: row for row in db.scalars(select(CrmContact).where(CrmContact.id.in_({a.contact_id for a in agreements}))).all()}
        all_with_bitrix = list(
            db.execute(
                text(
                    """
                    SELECT id, display_name, primary_phone, primary_email, metadata_json
                    FROM crm_contacts
                    WHERE metadata_json::text ILIKE '%bitrix_contact:%'
                    """
                )
            ).mappings()
        )
        by_bitrix: dict[str, list[UUID]] = defaultdict(list)
        contact_cache: dict[str, CrmContact] = {}
        for row in all_with_bitrix:
            meta = row["metadata_json"] if isinstance(row["metadata_json"], dict) else {}
            blob = json.dumps(meta, ensure_ascii=False)
            for cid in BITRIX_CONTACT_RE.findall(blob):
                by_bitrix[cid].append(row["id"])
            live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
            if live.get("contact_id"):
                by_bitrix[str(live.get("contact_id"))].append(row["id"])

        statuses = {str(item.get("STATUS_ID")): str(item.get("NAME") or item.get("STATUS_ID")) for item in list_all(client, "crm.status.list", {})}
        categories = {}
        for item in list_all(client, "crm.dealcategory.list", {}):
            categories[str(item.get("ID") or item.get("id") or "")] = str(item.get("NAME") or item.get("name") or "")
        fields_body = client.call("crm.deal.fields", {})
        fields = fields_body.get("result") if isinstance(fields_body.get("result"), dict) else {}

        deal_cache: dict[str, dict[str, Any]] = {}
        items_cache: dict[str, list[dict[str, Any]]] = {}
        uf_cache: dict[str, list[str]] = {}

        def get_deal(deal_id: str) -> dict[str, Any] | None:
            if deal_id in deal_cache:
                return deal_cache[deal_id]
            body = client.call("crm.deal.get", {"id": deal_id})
            result = body.get("result") if isinstance(body.get("result"), dict) else None
            deal_cache[deal_id] = result
            return result

        def get_items(deal_id: str) -> list[dict[str, Any]]:
            if deal_id in items_cache:
                return items_cache[deal_id]
            body = client.call("crm.deal.contact.items.get", {"id": deal_id})
            result = body.get("result")
            rows = result if isinstance(result, list) else []
            items_cache[deal_id] = [row for row in rows if isinstance(row, dict)]
            return items_cache[deal_id]

        def get_uf(deal_id: str, deal: dict[str, Any]) -> list[str]:
            if deal_id in uf_cache:
                return uf_cache[deal_id]
            ids: list[str] = []
            for key, spec in fields.items():
                if not str(key).startswith("UF_"):
                    continue
                ftype = spec.get("type") if isinstance(spec, dict) else None
                if ftype != "file" and "file" not in str(ftype or "").lower():
                    value = deal.get(key)
                    if file_ids_from_value(value):
                        ids.extend(file_ids_from_value(value))
                    continue
                ids.extend(file_ids_from_value(deal.get(key)))
            item = client.call("crm.item.get", {"entityTypeId": 2, "id": deal_id})
            item_result = item.get("result", {}).get("item") if isinstance(item.get("result"), dict) else None
            if isinstance(item_result, dict):
                for key, value in item_result.items():
                    if str(key).lower().startswith("uf") or str(key).startswith("UF"):
                        ids.extend(file_ids_from_value(value))
            uniq: list[str] = []
            for file_id in ids:
                if file_id not in uniq:
                    uniq.append(file_id)
            uf_cache[deal_id] = uniq
            return uniq

        contact_deals: dict[str, set[str]] = defaultdict(set)
        for row in agreements:
            contact = contacts.get(row.contact_id)
            if contact is None:
                continue
            for cid in bitrix_contact_ids(contact):
                if cid in contact_deals:
                    continue
                listed = list_all(client, "crm.deal.list", {"filter[CONTACT_ID]": cid, "select[]": ["ID", "TITLE", "CATEGORY_ID", "STAGE_ID", "CONTACT_ID", "OPPORTUNITY", "CURRENCY_ID", "BEGINDATE", "CLOSEDATE"]})
                contact_deals[cid] = {str(item.get("ID")) for item in listed if item.get("ID")}

        claimed: dict[str, UUID] = {}
        docs = list(db.scalars(select(Document).where(Document.notes.is_not(None))).all())
        by_file: dict[str, list[Document]] = defaultdict(list)
        for document in docs:
            file_id = str(notes_dict(document).get("bitrix_file_id") or "").strip()
            if file_id:
                by_file[file_id].append(document)

        created_contacts = 0
        created_participants = 0
        secondary_added = 0
        docs_linked = 0
        history_linked = 0

        for row in agreements:
            summary["agreements_checked"] += 1
            contact = contacts.get(row.contact_id)
            meta = dict(row.metadata_json or {})
            live_meta = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
            record: dict[str, Any] = {
                "agreement_id": str(row.id),
                "contact_id": str(row.contact_id),
                "contact_name": contact.display_name if contact else "",
                "project_group": row.project_group,
                "unit_number": row.unit_number or "",
                "source_external_id": row.source_external_id or "",
                "candidate_deal_ids": "|".join(candidate_deal_ids(row)),
                "verified_deal_id": "",
                "action": "unchanged",
                "reason": "",
                "participants": "",
                "ownership": "",
                "stage_label": "",
                "documents_linked": 0,
                "history_count": 0,
            }
            if row.id in LOCKED_DEALS.values():
                deal_id = next(key for key, value in LOCKED_DEALS.items() if value == row.id)
                deal = get_deal(deal_id) or {}
                items = get_items(deal_id)
                if not items and deal.get("CONTACT_ID"):
                    items = [{"CONTACT_ID": deal.get("CONTACT_ID"), "IS_PRIMARY": "Y"}]
                uf_ids = get_uf(deal_id, deal) if deal else []
                stage_id = str(deal.get("STAGE_ID") or live_meta.get("stage_id") or "")
                stage_label = statuses.get(stage_id) or live_meta.get("stage_label")
                if stage_label:
                    meta["stage_label"] = stage_label
                    live_meta["stage_label"] = stage_label
                if stage_id:
                    meta["stage_id"] = stage_id
                    live_meta["stage_id"] = stage_id
                meta["purchase_card_verified"] = True
                meta["bitrix_deal_id"] = deal_id
                live_meta["purchase_card_verified"] = True
                live_meta["bitrix_deal_id"] = deal_id
                meta["bitrix_live"] = live_meta
                row.metadata_json = meta
                if row.id != LOCKED_720:
                    os_ids = bitrix_contact_ids(contact) if contact else set()
                    if len(items) == 1 and contact is not None:
                        cid = str(items[0].get("CONTACT_ID") or "")
                        if cid in os_ids or not cid:
                            action = upsert_participant(
                                db,
                                agreement_id=row.id,
                                contact_id=contact.id,
                                is_primary=True,
                                ownership_pct=Decimal("100.00"),
                                deal_id=deal_id,
                                bitrix_contact_id=cid,
                            )
                            if action == "created":
                                created_participants += 1
                linked = link_documents(db, row.id, deal_id, uf_ids, by_file)
                docs_linked += linked
                hist = 0
                if contact is not None:
                    for activity in db.scalars(
                        select(CrmActivity).where(
                            CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                            CrmActivity.entity_id.in_({contact.id, NEDIM_CANONICAL_ID}),
                            CrmActivity.archived_at.is_(None),
                        )
                    ).all():
                        if is_deal_owned_activity(activity.metadata_json if isinstance(activity.metadata_json, dict) else None, deal_id):
                            hist += 1
                history_linked += hist
                claimed[deal_id] = row.id
                record.update(
                    {
                        "verified_deal_id": deal_id,
                        "action": "locked_pilot",
                        "reason": "nedim_pilot_preserved",
                        "documents_linked": linked,
                        "history_count": hist,
                        "stage_label": stage_label or "",
                    }
                )
                summary["purchase_cards_enabled"] += 1
                report_rows.append(record)
                continue

            verified_id = None
            reason = ""
            deal = None
            items: list[dict[str, Any]] = []
            os_ids = bitrix_contact_ids(contact) if contact else set()
            for cand in candidate_deal_ids(row):
                live = get_deal(cand)
                if not live:
                    continue
                live_items = get_items(cand)
                if not live_items and live.get("CONTACT_ID"):
                    live_items = [{"CONTACT_ID": live.get("CONTACT_ID"), "IS_PRIMARY": "Y"}]
                item_cids = {str(item.get("CONTACT_ID") or "") for item in live_items if item.get("CONTACT_ID")}
                contact_ok = bool(os_ids & item_cids) or str(live.get("CONTACT_ID") or "") in os_ids
                unit_live = fold_unit(deal_unit(live, fields))
                unit_os = fold_unit(row.unit_number)
                unit_ok = (not unit_os or not unit_live or unit_os == unit_live)
                cat_name = categories.get(str(live.get("CATEGORY_ID") or ""), "")
                proj = project_from_text(cat_name, str(live.get("TITLE") or ""))
                project_ok = (not proj or proj == row.project_group)
                if contact_ok and unit_ok and project_ok:
                    if cand in claimed and claimed[cand] != row.id:
                        summary["duplicate_agreements"].append(
                            {"deal_id": cand, "agreements": [str(claimed[cand]), str(row.id)]}
                        )
                        reason = "duplicate_deal"
                        continue
                    verified_id = cand
                    deal = live
                    items = live_items
                    reason = "live_deal_match"
                    break
                if live and not contact_ok:
                    summary["ownership_conflicts"].append(
                        {
                            "agreement_id": str(row.id),
                            "candidate_deal_id": cand,
                            "os_contact": str(row.contact_id),
                            "deal_contacts": sorted(item_cids),
                        }
                    )
            if verified_id is None and os_ids:
                leftover: list[tuple[str, dict[str, Any]]] = []
                for cid in os_ids:
                    for deal_id in contact_deals.get(cid, set()):
                        if deal_id in claimed:
                            continue
                        live = get_deal(deal_id)
                        if not live:
                            continue
                        unit_live = fold_unit(deal_unit(live, fields))
                        unit_os = fold_unit(row.unit_number)
                        cat_name = categories.get(str(live.get("CATEGORY_ID") or ""), "")
                        proj = project_from_text(cat_name, str(live.get("TITLE") or ""))
                        if proj and proj != row.project_group:
                            continue
                        if unit_os and unit_live and unit_os != unit_live:
                            continue
                        leftover.append((deal_id, live))
                if len(leftover) == 1:
                    verified_id, deal = leftover[0]
                    items = get_items(verified_id)
                    if not items and deal.get("CONTACT_ID"):
                        items = [{"CONTACT_ID": deal.get("CONTACT_ID"), "IS_PRIMARY": "Y"}]
                    reason = "unique_contact_deal"
                elif leftover:
                    reason = "ambiguous_multiple_live_deals"
                    record["reason"] = reason + ":" + ",".join(item[0] for item in leftover)
                    record["action"] = "skipped_ambiguous"
                    summary["ambiguous_not_changed"].append(record.copy())
                    report_rows.append(record)
                    continue

            if verified_id is None or deal is None:
                record["action"] = "skipped_ambiguous"
                record["reason"] = reason or "no_verified_bitrix_deal"
                summary["ambiguous_not_changed"].append(
                    {"agreement_id": str(row.id), "contact": record["contact_name"], "reason": record["reason"]}
                )
                report_rows.append(record)
                continue

            claimed[verified_id] = row.id
            if not items and deal.get("CONTACT_ID"):
                items = [{"CONTACT_ID": deal.get("CONTACT_ID"), "IS_PRIMARY": "Y"}]
            uf_ids = get_uf(verified_id, deal)
            stage_id = str(deal.get("STAGE_ID") or "")
            stage_label = statuses.get(stage_id)
            if not meta.get("opportunity") and deal.get("OPPORTUNITY") not in (None, ""):
                meta["opportunity"] = str(deal.get("OPPORTUNITY"))
            if not meta.get("currency") and deal.get("CURRENCY_ID"):
                meta["currency"] = str(deal.get("CURRENCY_ID"))
            if not meta.get("begin_date"):
                meta["begin_date"] = date_only(deal.get("BEGINDATE"))
            if not meta.get("close_date"):
                meta["close_date"] = date_only(deal.get("CLOSEDATE"))
            meta["bitrix_deal_id"] = verified_id
            meta["purchase_card_verified"] = True
            meta["stage_id"] = stage_id or meta.get("stage_id")
            if stage_label:
                meta["stage_label"] = stage_label
            live_meta.update(
                {
                    "bitrix_deal_id": verified_id,
                    "purchase_card_verified": True,
                    "stage_id": stage_id,
                    "stage_label": stage_label,
                    "opportunity": str(deal.get("OPPORTUNITY") or live_meta.get("opportunity") or ""),
                    "currency": str(deal.get("CURRENCY_ID") or live_meta.get("currency") or ""),
                    "begin_date": date_only(deal.get("BEGINDATE")),
                    "close_date": date_only(deal.get("CLOSEDATE")),
                    "title": deal.get("TITLE"),
                    "contact_ids": [str(item.get("CONTACT_ID")) for item in items if item.get("CONTACT_ID")],
                    "uf_file_ids": uf_ids,
                    "source": "bitrix_live",
                }
            )
            meta["bitrix_live"] = live_meta
            row.metadata_json = meta

            mapped_os: list[tuple[dict[str, Any], CrmContact, str]] = []
            seen_os: set[UUID] = set()
            for item in items:
                cid = str(item.get("CONTACT_ID") or "").strip()
                if not cid:
                    continue
                os_contact = None
                for os_id in by_bitrix.get(cid, []):
                    os_contact = db.get(CrmContact, os_id)
                    if os_contact is not None:
                        break
                if os_contact is None:
                    os_contact = ensure_contact_from_bitrix(db, client, cid, contact_cache)
                    if os_contact is not None and os_contact.id not in by_bitrix.get(cid, []):
                        created_contacts += 1
                        by_bitrix[cid].append(os_contact.id)
                if os_contact is None or os_contact.id in seen_os:
                    continue
                seen_os.add(os_contact.id)
                mapped_os.append((item, os_contact, cid))

            pct = Decimal("100.00") if len(mapped_os) == 1 else None
            names = []
            for index, (item, os_contact, cid) in enumerate(mapped_os):
                is_primary = str(item.get("IS_PRIMARY") or "").upper() in {"Y", "1", "TRUE"} or (
                    index == 0 and not any(str(x[0].get("IS_PRIMARY") or "").upper() in {"Y", "1", "TRUE"} for x in mapped_os)
                )
                action = upsert_participant(
                    db,
                    agreement_id=row.id,
                    contact_id=os_contact.id,
                    is_primary=is_primary,
                    ownership_pct=pct,
                    deal_id=verified_id,
                    bitrix_contact_id=cid,
                )
                if action == "created":
                    created_participants += 1
                    if not is_primary:
                        secondary_added += 1
                db.flush()
                names.append(f"{os_contact.display_name}{' 100%' if pct else ''}")
            if len(mapped_os) > 1:
                summary["joint_purchases"].append(
                    {
                        "agreement_id": str(row.id),
                        "deal_id": verified_id,
                        "owners": [c.display_name for _, c, _ in mapped_os],
                    }
                )

            linked = link_documents(db, row.id, verified_id, uf_ids, by_file)
            docs_linked += linked
            owner_ids = {row.contact_id, *(c.id for _, c, _ in mapped_os)}
            hist = 0
            for activity in db.scalars(
                select(CrmActivity).where(
                    CrmActivity.entity_type == CrmActivityEntityType.CONTACT,
                    CrmActivity.entity_id.in_(owner_ids),
                    CrmActivity.archived_at.is_(None),
                )
            ).all():
                if is_deal_owned_activity(activity.metadata_json if isinstance(activity.metadata_json, dict) else None, verified_id):
                    hist += 1
            history_linked += hist
            summary["purchase_cards_enabled"] += 1
            record.update(
                {
                    "verified_deal_id": verified_id,
                    "action": "enabled",
                    "reason": reason,
                    "participants": " | ".join(names),
                    "ownership": "100" if pct else "",
                    "stage_label": stage_label or "",
                    "documents_linked": linked,
                    "history_count": hist,
                }
            )
            report_rows.append(record)

        db.commit()
        summary["secondary_owners_added"] = secondary_added
        summary["new_canonical_contacts"] = created_contacts
        summary["participant_rows_created"] = created_participants
        summary["deal_documents_linked"] = docs_linked
        summary["deal_history_linked"] = history_linked
        summary["final_agreement_count"] = len(agreements)
        summary["webhook_used"] = True
        summary["bitrix_calls"] = client.call_count
        summary["backup_path"] = "data/Bitrix_Export/2026-09-final/BITRIX_PURCHASE_CARD_ROLLOUT/backups/investhome-pre-purchase-card-rollout-20260918.dump"
        summary["report_path"] = "data/Bitrix_Export/2026-09-final/BITRIX_PURCHASE_CARD_ROLLOUT/reports"
        by_person: dict[str, list[str]] = defaultdict(list)
        for row in db.scalars(select(CrmAgreement)).all():
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            if meta.get("purchase_card_verified") or row.id in LOCKED_DEALS.values():
                by_person[str(row.contact_id)].append(str(row.id))
        for participant in db.scalars(select(CrmAgreementParticipant)).all():
            by_person[str(participant.contact_id)].append(str(participant.agreement_id))
        multi = []
        for contact_id, agr_ids in by_person.items():
            uniq = sorted(set(agr_ids))
            if len(uniq) > 1:
                person = db.get(CrmContact, UUID(contact_id))
                multi.append({"contact_id": contact_id, "name": person.display_name if person else "", "purchases": len(uniq)})
        summary["people_with_multiple_purchases"] = multi
        summary["final_agreement_count"] = len(agreements)
        summary["webhook_used"] = True
        summary["bitrix_calls"] = client.call_count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    csv_path = OUT / "reports" / "PURCHASE_CARD_ROLLOUT.csv"
    fields = [
        "agreement_id",
        "contact_id",
        "contact_name",
        "project_group",
        "unit_number",
        "source_external_id",
        "candidate_deal_ids",
        "verified_deal_id",
        "action",
        "reason",
        "participants",
        "ownership",
        "stage_label",
        "documents_linked",
        "history_count",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report_rows:
            writer.writerow({key: row.get(key, "") for key in fields})
    json_path = OUT / "reports" / "PURCHASE_CARD_ROLLOUT_SUMMARY.json"
    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in summary if k != "people_with_multiple_purchases"}, ensure_ascii=False))
    print("MULTI", len(summary["people_with_multiple_purchases"]))
    print("JOINT", len(summary["joint_purchases"]))
    print("AMBIGUOUS", len(summary["ambiguous_not_changed"]))
    print("CSV", str(csv_path))
    return summary


if __name__ == "__main__":
    main()
