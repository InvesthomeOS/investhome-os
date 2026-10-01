"""CRM identity match review — live duplicate candidates, no destructive merge."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact, CrmContactDuplicateCandidate
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_matches import (
    CrmMatchDecisionRequest,
    CrmMatchDetail,
    CrmMatchEvidence,
    CrmMatchItem,
    CrmMatchKpis,
    CrmMatchListResponse,
    CrmMatchPerson,
    CrmMatchPurchase,
)
from investhome_api.services.crm.identity import (
    is_zero_masked_phone,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
)
from investhome_api.services.crm.unit_change import is_historical_unit_change

OPEN_STATUSES = ("pending", "in_review")
DECISIONS = ("same_person", "different", "in_review")
STRONG_REASONS = ("phone", "email", "secondary_email", "bitrix")
REASON_ORDER = ("phone", "email", "secondary_email", "bitrix", "name_review")
BUCKET_CAP = 12
_BITRIX_CONTACT_RE = re.compile(r"bitrix_contact:(\d+)")
GOKHAN = "gokhan bulbul"
LEVI_PAIR = frozenset({"selim levi beceren", "levi sunny"})


class MatchNotFoundError(Exception):
    pass


class MatchValidationError(Exception):
    pass


def _live_people(db: Session) -> list[CrmContact]:
    return list(
        db.scalars(
            select(CrmContact).where(
                CrmContact.archived_at.is_(None),
                CrmContact.is_demo.is_(False),
            )
        ).all()
    )


def _bitrix_ids(contact: CrmContact) -> set[str]:
    ids: set[str] = set()
    meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    blob = json.dumps(meta, ensure_ascii=False)
    ids.update(_BITRIX_CONTACT_RE.findall(blob))
    bitrix = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    for value in bitrix.get("external_ids") or []:
        if value:
            ids.add(str(value).strip())
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    if live.get("contact_id"):
        ids.add(str(live.get("contact_id")).strip())
    return {item for item in ids if item}


def _phone_keys(contact: CrmContact) -> set[str]:
    keys: set[str] = set()
    values = [contact.primary_phone, contact.whatsapp, *(contact.secondary_phones or [])]
    for raw in values:
        parsed = parse_phone(raw)
        if parsed is None or parsed.suspicious or is_zero_masked_phone(raw):
            continue
        digits = parsed.digits
        if len(digits) < 10:
            continue
        keys.add(digits[-10:])
        if parsed.e164:
            keys.add(parsed.e164)
    return keys


def _email_entries(contact: CrmContact) -> tuple[set[str], set[str]]:
    primary = set()
    secondary = set()
    email = normalize_valid_email(contact.primary_email)
    if email:
        primary.add(email)
    for raw in contact.secondary_emails or []:
        item = normalize_valid_email(str(raw) if raw else None)
        if item:
            secondary.add(item)
    return primary, secondary


def _name_key(contact: CrmContact) -> str | None:
    key = normalize_full_name(contact.display_name)
    if not key or len(key.split()) < 2:
        return None
    return key


def _review_flag(contact: CrmContact) -> bool:
    notes = contact.notes or ""
    return bool(contact.review_required) or "INCELEME_GEREKLI" in notes.upper()


def _has_1812_306(purchases: list[CrmAgreement]) -> bool:
    for row in purchases:
        project = (row.project_group or "").lower()
        unit = (row.unit_number or "").replace(" ", "").lower()
        if "1812" in project and "306" in unit:
            return True
    return False


def _protection(a: CrmContact, b: CrmContact, purchases: dict[UUID, list[CrmAgreement]]) -> tuple[bool, str | None]:
    if _review_flag(a) or _review_flag(b):
        return True, "inceleme_gerekli"
    na = _name_key(a)
    nb = _name_key(b)
    if na and nb and frozenset({na, nb}) == LEVI_PAIR:
        return True, "selim_levi_sunny"
    if na == GOKHAN and nb == GOKHAN:
        if _has_1812_306(purchases.get(a.id, [])) or _has_1812_306(purchases.get(b.id, [])):
            return True, "gokhan_bulbul_1812_306"
        return True, "gokhan_bulbul"
    return False, None


def _pair_ids(left: UUID, right: UUID) -> tuple[UUID, UUID]:
    return (left, right) if left.hex < right.hex else (right, left)


def _load_purchases(db: Session, contact_ids: list[UUID]) -> dict[UUID, list[CrmAgreement]]:
    if not contact_ids:
        return {}
    owned = list(db.scalars(select(CrmAgreement).where(CrmAgreement.contact_id.in_(contact_ids))).all())
    parts = list(
        db.scalars(select(CrmAgreementParticipant).where(CrmAgreementParticipant.contact_id.in_(contact_ids))).all()
    )
    extra_ids = {item.agreement_id for item in parts}
    extra = list(db.scalars(select(CrmAgreement).where(CrmAgreement.id.in_(extra_ids))).all()) if extra_ids else []
    agreements = {row.id: row for row in [*owned, *extra]}
    by_contact: dict[UUID, list[CrmAgreement]] = defaultdict(list)
    seen: dict[UUID, set[UUID]] = defaultdict(set)

    def _put(contact_id: UUID, row: CrmAgreement) -> None:
        if contact_id not in contact_ids or row.id in seen[contact_id]:
            return
        seen[contact_id].add(row.id)
        by_contact[contact_id].append(row)

    for row in agreements.values():
        _put(row.contact_id, row)
    for part in parts:
        row = agreements.get(part.agreement_id)
        if row is not None:
            _put(part.contact_id, row)
    return by_contact


def _add_pair(
    pairs: dict[tuple[UUID, UUID], dict[str, Any]],
    left: CrmContact,
    right: CrmContact,
    reason: str,
    value: str,
) -> None:
    if left.id == right.id:
        return
    key = _pair_ids(left.id, right.id)
    bucket = pairs.setdefault(
        key,
        {"a": left if key[0] == left.id else right, "b": right if key[0] == left.id else left, "reasons": []},
    )
    evidence = {"reason": reason, "value": value}
    if evidence not in bucket["reasons"]:
        bucket["reasons"].append(evidence)


def refresh_crm_matches(db: Session) -> int:
    people = _live_people(db)
    by_id = {row.id: row for row in people}
    purchases = _load_purchases(db, list(by_id.keys()))
    pairs: dict[tuple[UUID, UUID], dict[str, Any]] = {}

    phone_index: dict[str, list[CrmContact]] = defaultdict(list)
    email_index: dict[str, list[tuple[CrmContact, str]]] = defaultdict(list)
    bitrix_index: dict[str, list[CrmContact]] = defaultdict(list)
    name_index: dict[str, list[CrmContact]] = defaultdict(list)

    for person in people:
        for key in _phone_keys(person):
            phone_index[key].append(person)
        primary, secondary = _email_entries(person)
        for email in primary:
            email_index[email].append((person, "email"))
        for email in secondary:
            email_index[email].append((person, "secondary_email"))
        for bitrix_id in _bitrix_ids(person):
            bitrix_index[bitrix_id].append(person)
        name = _name_key(person)
        if name:
            name_index[name].append(person)

    def _walk(rows: list[CrmContact], reason: str, value: str) -> None:
        unique: list[CrmContact] = []
        seen: set[UUID] = set()
        for row in rows:
            if row.id in seen:
                continue
            seen.add(row.id)
            unique.append(row)
        if len(unique) < 2 or len(unique) > BUCKET_CAP:
            return
        for index, left in enumerate(unique):
            for right in unique[index + 1 :]:
                _add_pair(pairs, left, right, reason, value)

    for key, rows in phone_index.items():
        _walk(rows, "phone", key)
    for email, entries in email_index.items():
        people_for_email = [item[0] for item in entries]
        kinds = {item[1] for item in entries}
        reason = "secondary_email" if "secondary_email" in kinds else "email"
        _walk(people_for_email, reason, email)
    for bitrix_id, rows in bitrix_index.items():
        _walk(rows, "bitrix", bitrix_id)
    for name, rows in name_index.items():
        _walk(rows, "name_review", name)

    existing = {
        (row.contact_id_a, row.contact_id_b): row
        for row in db.scalars(select(CrmContactDuplicateCandidate)).all()
    }
    live_keys = set(pairs)
    for key, payload in pairs.items():
        reasons = payload["reasons"]
        reason_names = [item["reason"] for item in reasons]
        primary = next((item for item in REASON_ORDER if item in reason_names), "name_review")
        kind = "strong" if any(item in STRONG_REASONS for item in reason_names) else "possible"
        left: CrmContact = payload["a"]
        right: CrmContact = payload["b"]
        protected, protected_reason = _protection(left, right, purchases)
        sources = [item for item in (left.source, right.source) if item]
        source = "bitrix" if _bitrix_ids(left) or _bitrix_ids(right) else (sources[0] if sources else "crm")
        evidence = {
            "reasons": reasons,
            "shared_phone": next((item["value"] for item in reasons if item["reason"] == "phone"), None),
            "shared_email": next(
                (item["value"] for item in reasons if item["reason"] in {"email", "secondary_email"}),
                None,
            ),
        }
        row = existing.get(key)
        if row is None:
            row = CrmContactDuplicateCandidate(
                contact_id_a=key[0],
                contact_id_b=key[1],
                status="pending",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(row)
        row.match_reason = primary
        row.match_kind = kind
        row.match_score = 0
        row.source = source
        row.evidence_json = evidence
        row.protected = protected
        row.protected_reason = protected_reason
        if row.status == "same_person" and protected:
            row.merge_queued = False
        if key not in live_keys:
            continue
    for key, row in existing.items():
        if key in live_keys:
            continue
        if row.status in OPEN_STATUSES:
            db.delete(row)
    db.flush()
    return len(pairs)


def _purchase_items(rows: list[CrmAgreement]) -> list[CrmMatchPurchase]:
    items: list[CrmMatchPurchase] = []
    for row in rows:
        items.append(
            CrmMatchPurchase(
                id=row.id,
                project=row.project_group,
                unit=row.unit_number,
                source_id=row.source_external_id,
                historical=is_historical_unit_change(row),
            )
        )
    return items


def _person_card(contact: CrmContact, purchases: list[CrmAgreement]) -> CrmMatchPerson:
    primary, secondary = _email_entries(contact)
    return CrmMatchPerson(
        id=contact.id,
        name=contact.display_name,
        phone=contact.primary_phone,
        email=contact.primary_email,
        secondary_emails=sorted(secondary - primary),
        source=contact.source,
        source_ids=sorted(_bitrix_ids(contact)),
        notes=contact.notes,
        review_required=_review_flag(contact),
        href=f"/workspaces/crm/contacts/{contact.id}",
        purchases=_purchase_items(purchases),
    )


def _conflicts(left: CrmMatchPerson, right: CrmMatchPerson) -> list[str]:
    conflicts: list[str] = []
    if left.name and right.name and normalize_full_name(left.name) != normalize_full_name(right.name):
        conflicts.append("name")
    if left.phone and right.phone and left.phone != right.phone:
        conflicts.append("phone")
    if left.email and right.email and normalize_valid_email(left.email) != normalize_valid_email(right.email):
        conflicts.append("email")
    if left.source and right.source and left.source != right.source:
        conflicts.append("source")
    return conflicts


def _to_item(
    row: CrmContactDuplicateCandidate,
    left: CrmContact,
    right: CrmContact,
) -> CrmMatchItem:
    evidence = row.evidence_json if isinstance(row.evidence_json, dict) else {}
    reasons = list(
        dict.fromkeys(
            str(item.get("reason"))
            for item in evidence.get("reasons") or []
            if item.get("reason")
        )
    )
    if not reasons:
        reasons = [row.match_reason]
    return CrmMatchItem(
        id=row.id,
        person_a_id=left.id,
        person_a_name=left.display_name,
        person_b_id=right.id,
        person_b_name=right.display_name,
        reasons=reasons,
        match_kind=row.match_kind,  # type: ignore[arg-type]
        shared_phone=evidence.get("shared_phone"),
        shared_email=evidence.get("shared_email"),
        source=row.source,
        status=row.status,  # type: ignore[arg-type]
        protected=bool(row.protected),
        protected_reason=row.protected_reason,
        merge_queued=bool(row.merge_queued),
        review_notes=row.review_notes,
        created_at=row.created_at,
    )


def _kpis(rows: list[CrmContactDuplicateCandidate]) -> CrmMatchKpis:
    kpis = CrmMatchKpis()
    for row in rows:
        if row.status in OPEN_STATUSES:
            kpis.pending += 1
            if row.match_kind == "strong":
                kpis.strong += 1
            else:
                kpis.possible += 1
        elif row.status == "different":
            kpis.rejected += 1
        elif row.status == "same_person":
            kpis.same_person += 1
    return kpis


def list_crm_matches(
    db: Session,
    *,
    search: str | None = None,
    match_type: str | None = None,
    status: str | None = None,
    source: str | None = None,
    refresh: bool = True,
) -> CrmMatchListResponse:
    if refresh:
        refresh_crm_matches(db)
    rows = list(db.scalars(select(CrmContactDuplicateCandidate)).all())
    people = {row.id: row for row in _live_people(db)}
    items: list[CrmMatchItem] = []
    sources: set[str] = set()
    needle = (search or "").strip().lower()
    for row in rows:
        left = people.get(row.contact_id_a) or db.get(CrmContact, row.contact_id_a)
        right = people.get(row.contact_id_b) or db.get(CrmContact, row.contact_id_b)
        if left is None or right is None:
            continue
        if row.source:
            sources.add(row.source)
        item = _to_item(row, left, right)
        if match_type and match_type not in item.reasons and match_type != item.match_kind:
            continue
        if status and item.status != status:
            if not (status == "pending" and item.status in OPEN_STATUSES):
                continue
        if source and (item.source or "").lower() != source.lower():
            continue
        if needle:
            blob = " ".join(
                [
                    item.person_a_name,
                    item.person_b_name,
                    item.shared_phone or "",
                    item.shared_email or "",
                    left.primary_phone or "",
                    right.primary_phone or "",
                    left.primary_email or "",
                    right.primary_email or "",
                ]
            ).lower()
            if needle not in blob:
                continue
        items.append(item)
    items.sort(key=lambda item: (item.protected, item.match_kind != "strong", item.person_a_name.lower()))
    return CrmMatchListResponse(
        items=items,
        total=len(items),
        kpis=_kpis(rows),
        sources=sorted(sources),
        reasons=list(REASON_ORDER),
    )


def get_crm_match(db: Session, match_id: UUID) -> CrmMatchDetail:
    row = db.get(CrmContactDuplicateCandidate, match_id)
    if row is None:
        raise MatchNotFoundError()
    left = db.get(CrmContact, row.contact_id_a)
    right = db.get(CrmContact, row.contact_id_b)
    if left is None or right is None:
        raise MatchNotFoundError()
    purchases = _load_purchases(db, [left.id, right.id])
    person_a = _person_card(left, purchases.get(left.id, []))
    person_b = _person_card(right, purchases.get(right.id, []))
    evidence_raw = row.evidence_json if isinstance(row.evidence_json, dict) else {}
    evidence = [
        CrmMatchEvidence(reason=str(item.get("reason")), value=str(item.get("value") or "") or None)
        for item in evidence_raw.get("reasons") or []
        if item.get("reason")
    ]
    linked = [*person_a.purchases, *person_b.purchases]
    return CrmMatchDetail(
        **_to_item(row, left, right).model_dump(),
        person_a=person_a,
        person_b=person_b,
        evidence=evidence,
        conflicts=_conflicts(person_a, person_b),
        linked_purchases=linked,
        merge_blocked=True,
        merge_message=(
            "Korumalı kayıt. Otomatik birleştirme yok; karar inceleme için saklanır."
            if row.protected
            else "Güvenli kanonik birleştirme yok. Karar kaydedilir, kayıtlar birleştirilmez."
        ),
    )


def decide_crm_match(
    db: Session,
    match_id: UUID,
    payload: CrmMatchDecisionRequest,
    *,
    actor: User | None,
) -> CrmMatchDetail:
    row = db.get(CrmContactDuplicateCandidate, match_id)
    if row is None:
        raise MatchNotFoundError()
    if payload.action not in DECISIONS:
        raise MatchValidationError("Geçersiz karar")
    left = db.get(CrmContact, row.contact_id_a)
    right = db.get(CrmContact, row.contact_id_b)
    if left is None or right is None or left.archived_at or right.archived_at:
        raise MatchValidationError("Kişi kaydı incelenemez")
    purchases = _load_purchases(db, [left.id, right.id])
    protected, protected_reason = _protection(left, right, purchases)
    row.protected = protected
    row.protected_reason = protected_reason
    row.status = payload.action
    row.reviewed_at = datetime.now(UTC)
    row.reviewed_by_user_id = actor.id if actor else None
    note = (payload.notes or "").strip()
    if note:
        row.review_notes = f"{row.review_notes}\n{note}".strip() if row.review_notes else note
    if payload.action == "same_person":
        row.merge_queued = False
        flag = (
            "Aynı kişi kararı kaydedildi. Korumalı kayıt — kontrollü birleştirme yapılmaz."
            if protected
            else "Aynı kişi kararı kaydedildi. Kayıtlar birleştirilmedi; kontrollü birleştirme bekleniyor."
        )
        row.review_notes = f"{row.review_notes}\n{flag}".strip() if row.review_notes else flag
    elif payload.action == "different":
        row.merge_queued = False
    else:
        row.merge_queued = False
    db.flush()
    return get_crm_match(db, match_id)
