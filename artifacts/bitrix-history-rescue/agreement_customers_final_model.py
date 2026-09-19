"""Apply Nedim person/sales completeness to all agreement customers. Bitrix is read-only."""
from __future__ import annotations

import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import CrmActivity, CrmActivityEntityType
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact, CrmContactType
from investhome_api.models.document import Document, DocumentLink
from investhome_api.services.crm.agreement_service import (
    _document_notes,
    get_purchase_card,
    is_purchase_owner_contact,
    list_contact_purchases,
)
from investhome_api.services.crm.nedim_purchase_card import deal_id_for_agreement, is_deal_owned_activity
from investhome_api.services.crm.identity import is_agent_advisor_name, normalize_full_name

OUT = Path("/tmp/AGREEMENT_CUSTOMERS_FINAL_MODEL")
LEGACY_NAMES = {
    normalize_full_name("Albert Levi"),
    normalize_full_name("Albert Levı"),
    normalize_full_name("Semra Arli"),
}
SKIP_UF_TYPES = {"file", "disk_file", "employee", "crm", "crm_status", "iblock_element", "iblock_section"}
PAYMENT_RE = re.compile(r"kapora|peşinat|pesinat|deposit|down.?pay|mortgage|kredi|ödeme|odeme|remaining|kalan", re.I)
LLC_RE = re.compile(r"llc|şirket|sirket|company|ein|operating", re.I)
TECHNICAL_RE = re.compile(r"^(id|xml_id|originator|origin_id|utm_|moved_by|moved_time|opened|closed|is_manual)", re.I)
BITRIX_CONTACT_RE = re.compile(r"bitrix_contact:(\d+)")
WEBHOOK_RE = re.compile(r"https?://[^\s\"']+", re.I)


def webhook_base(raw: str) -> str:
    value = (raw or "").strip().strip('"').strip("'")
    marker = "BURAYA_BITRIX_URL="
    if marker in value:
        value = value.split(marker, 1)[1].strip()
    parsed = urllib.parse.urlparse(value)
    segs = [s for s in parsed.path.split("/") if s]
    if segs and ("." in segs[-1] or segs[-1].endswith(".json")):
        segs = segs[:-1]
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/" + "/".join(segs) + "/", "", "", ""))


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.call_count = 0
        self._last = 0.0

    def _wait(self) -> None:
        delta = time.time() - self._last
        if delta < 0.35:
            time.sleep(0.35 - delta)

    def call(self, method: str, payload: dict | None = None) -> dict[str, Any]:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last = "unknown"
        for attempt in range(5):
            self._wait()
            self.call_count += 1
            data = urllib.parse.urlencode(payload or {}, doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}"}
            except Exception as exc:  # noqa: BLE001
                last = type(exc).__name__
                time.sleep(min(12, 2**attempt))
                continue
            self._last = time.time()
            err = str(parsed.get("error") or "")
            if err in {"QUERY_LIMIT_EXCEEDED", "INTERNAL_SERVER_ERROR"}:
                last = err
                time.sleep(min(20, 2 ** (attempt + 1)))
                continue
            return parsed
        return {"error": "retry_exhausted", "error_description": last}


def field_label(spec: Any) -> str:
    if not isinstance(spec, dict):
        return ""
    for key in ("formLabel", "listLabel", "editLabel", "title"):
        value = spec.get(key)
        if isinstance(value, dict):
            return str(value.get("tr") or value.get("en") or next(iter(value.values()), "") or "").strip()
        if value:
            return str(value).strip()
    return str(spec.get("listLabel") or "").strip()


def scalar(value: Any) -> str | None:
    if value in (None, "", [], {}, 0, "0"):
        return None
    if isinstance(value, list):
        parts = [scalar(item) for item in value]
        text = ", ".join(part for part in parts if part)
        return text or None
    if isinstance(value, dict):
        for key in ("VALUE", "value", "label", "NAME", "title"):
            if value.get(key):
                return str(value.get(key)).strip() or None
        return None
    text = str(value).strip()
    return text or None


def date_only(value: Any) -> str | None:
    text = scalar(value)
    if not text:
        return None
    return text[:10]


def contact_address_parts(live: dict[str, Any]) -> dict[str, str]:
    parts: dict[str, str] = {}
    line = " ".join(item for item in (scalar(live.get("ADDRESS")), scalar(live.get("ADDRESS_2"))) if item)
    if line:
        parts["address_line1"] = line[:255]
    city = scalar(live.get("ADDRESS_CITY"))
    if city:
        parts["city"] = city[:120]
    region = scalar(live.get("ADDRESS_REGION")) or scalar(live.get("ADDRESS_PROVINCE"))
    if region:
        parts["state_province"] = region[:120]
    postal = scalar(live.get("ADDRESS_POSTAL_CODE"))
    if postal:
        parts["postal_code"] = postal[:30]
    country = scalar(live.get("ADDRESS_COUNTRY"))
    if country:
        parts["country"] = country[:100]
    return parts


def fill_empty(row: Any, field: str, value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    current = getattr(row, field)
    if current not in (None, "", [], {}):
        return False
    setattr(row, field, value)
    return True


def conflict(os_value: Any, bitrix_value: Any) -> bool:
    left = str(os_value or "").strip()
    right = str(bitrix_value or "").strip()
    if not left or not right:
        return False
    return normalize_full_name(left) != normalize_full_name(right) and left.casefold() != right.casefold()


def bitrix_contact_ids(contact: CrmContact) -> set[str]:
    ids: set[str] = set()
    blob = json.dumps(contact.metadata_json or {}, ensure_ascii=False)
    ids.update(BITRIX_CONTACT_RE.findall(blob))
    live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
    if isinstance(live, dict) and live.get("contact_id"):
        ids.add(str(live.get("contact_id")).strip())
    return {item for item in ids if item.isdigit()}


def merge_live(row: CrmContact | CrmAgreement, payload: dict[str, Any]) -> list[str]:
    meta = dict(row.metadata_json or {}) if isinstance(row.metadata_json, dict) else {}
    live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
    changed: list[str] = []
    for key, value in payload.items():
        if value in (None, "", [], {}):
            continue
        current = live.get(key)
        if current in (None, "", [], {}) or current != value:
            live[key] = value
            changed.append(key)
    meta["bitrix_live"] = live
    row.metadata_json = meta
    flag_modified(row, "metadata_json")
    return changed


def labeled_from_entity(entity: dict[str, Any], fields: dict[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    payment: list[dict[str, str]] = []
    llc: list[dict[str, str]] = []
    extra: list[dict[str, str]] = []
    for key, spec in fields.items():
        if not str(key).startswith("UF_"):
            continue
        type_id = str(spec.get("type") or spec.get("userTypeId") or "").lower() if isinstance(spec, dict) else ""
        if type_id in SKIP_UF_TYPES:
            continue
        label = field_label(spec) or key
        if TECHNICAL_RE.search(label) or TECHNICAL_RE.search(key):
            continue
        value = scalar(entity.get(key))
        if not value or value in {"Y", "N"} and type_id == "boolean" and value == "N":
            continue
        if type_id == "boolean":
            value = "Evet" if value in {"Y", "1", "true", "True"} else "Hayır"
        item = {"label": label, "value": value}
        blob = f"{label} {key}"
        if PAYMENT_RE.search(blob):
            payment.append(item)
        elif LLC_RE.search(blob):
            llc.append(item)
        else:
            extra.append(item)
    return payment, llc, extra


def link_deal_documents(db: Session, agreement_id: UUID, deal_id: str) -> int:
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
    candidates = list(
        db.scalars(
            select(Document).where(
                Document.notes.is_not(None),
                Document.notes.ilike("%bitrix_entity_id%"),
                Document.notes.ilike(f"%{deal_id}%"),
            )
        ).all()
    )
    for document in candidates:
        notes = _document_notes(document)
        if str(notes.get("bitrix_entity_type") or "").lower() != "deal":
            continue
        if str(notes.get("bitrix_entity_id") or "") != deal_id:
            continue
        if str(document.id) in existing:
            continue
        db.add(
            DocumentLink(
                document_id=document.id,
                entity_type="crm_agreement",
                entity_id=agreement_id,
                relationship_type="bitrix_deal_file",
            )
        )
        existing.add(str(document.id))
        linked += 1
    return linked


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    client = BitrixClient(webhook_base(raw)) if raw else None
    db = SessionLocal()
    summary: dict[str, Any] = {
        "agreement_customers_checked": 0,
        "purchases_checked": 0,
        "people_with_multiple_purchases": [],
        "joint_purchases": [],
        "missing_person_fields_recovered": Counter(),
        "missing_addresses_recovered": 0,
        "purchase_fields_recovered": Counter(),
        "documents_newly_recovered": 0,
        "documents_newly_linked": 0,
        "purchase_document_counts": [],
        "history_whatsapp_gaps": [],
        "people_still_incomplete": [],
        "purchases_still_incomplete": [],
        "inaccessible_documents": [],
        "legacy_manual_agreements": [],
        "review_required": [],
        "bitrix_calls": 0,
        "webhook_used": bool(client),
    }
    people_rows: list[dict[str, Any]] = []
    purchase_rows: list[dict[str, Any]] = []
    try:
        agreements = list(db.scalars(select(CrmAgreement).order_by(CrmAgreement.created_at.asc())).all())
        summary["purchases_checked"] = len(agreements)
        contacts_by_id = {
            row.id: row
            for row in db.scalars(
                select(CrmContact).where(CrmContact.id.in_({item.contact_id for item in agreements}))
            ).all()
        }
        participants = list(db.scalars(select(CrmAgreementParticipant)).all())
        for part in participants:
            if part.contact_id not in contacts_by_id:
                person = db.get(CrmContact, part.contact_id)
                if person is not None:
                    contacts_by_id[person.id] = person
        customer_ids = {row.contact_id for row in agreements} | {
            item.contact_id for item in participants if item.contact_id in contacts_by_id and is_purchase_owner_contact(contacts_by_id[item.contact_id])
        }
        customer_ids = {
            cid
            for cid in customer_ids
            if cid in contacts_by_id and is_purchase_owner_contact(contacts_by_id[cid])
        }
        summary["agreement_customers_checked"] = len(customer_ids)

        deal_fields: dict[str, Any] = {}
        contact_fields: dict[str, Any] = {}
        statuses: dict[str, str] = {}
        sources: dict[str, str] = {}
        users: dict[str, str] = {}
        if client:
            raw_fields = client.call("crm.deal.fields", {})
            result = raw_fields.get("result")
            if isinstance(result, dict):
                deal_fields = result
            raw_cfields = client.call("crm.contact.fields", {})
            result = raw_cfields.get("result")
            if isinstance(result, dict):
                contact_fields = result
            raw_status = client.call("crm.status.list", {"filter": {"ENTITY_ID": "DEAL_STAGE"}})
            items = raw_status.get("result") if isinstance(raw_status.get("result"), list) else []
            for item in items:
                if isinstance(item, dict) and item.get("STATUS_ID"):
                    statuses[str(item.get("STATUS_ID"))] = str(item.get("NAME") or item.get("STATUS_ID"))
            raw_sources = client.call("crm.status.list", {"filter": {"ENTITY_ID": "SOURCE"}})
            source_items = raw_sources.get("result") if isinstance(raw_sources.get("result"), list) else []
            for item in source_items:
                if isinstance(item, dict) and item.get("STATUS_ID"):
                    sources[str(item.get("STATUS_ID"))] = str(item.get("NAME") or item.get("STATUS_ID"))
            start = 0
            while True:
                body = client.call("user.get", {"start": start})
                chunk = body.get("result") if isinstance(body.get("result"), list) else []
                if not chunk:
                    break
                for user in chunk:
                    if isinstance(user, dict) and user.get("ID"):
                        name = " ".join(part for part in (user.get("NAME"), user.get("LAST_NAME")) if part).strip()
                        users[str(user.get("ID"))] = name or str(user.get("ID"))
                nxt = body.get("next")
                if nxt in (None, ""):
                    break
                start = int(nxt)

        contact_cache: dict[str, dict[str, Any]] = {}
        deal_cache: dict[str, dict[str, Any]] = {}

        def get_contact(cid: str) -> dict[str, Any] | None:
            if cid in contact_cache:
                return contact_cache[cid]
            if not client:
                return None
            body = client.call("crm.contact.get", {"id": cid})
            result = body.get("result") if isinstance(body.get("result"), dict) else None
            contact_cache[cid] = result or {}
            return result

        def get_deal(did: str) -> dict[str, Any] | None:
            if did in deal_cache:
                return deal_cache[did]
            if not client:
                return None
            body = client.call("crm.deal.get", {"id": did})
            result = body.get("result") if isinstance(body.get("result"), dict) else None
            deal_cache[did] = result or {}
            return result

        for person_id in sorted(customer_ids, key=str):
            person = contacts_by_id.get(person_id) or db.get(CrmContact, person_id)
            if person is None:
                continue
            recovered: list[str] = []
            reviews: list[str] = []
            legacy = normalize_full_name(person.display_name) in LEGACY_NAMES
            live_contact = None
            cids = bitrix_contact_ids(person)
            phone_vals: list[str] = []
            email_vals: list[str] = []
            address_parts: dict[str, str] = {}
            if client and len(cids) == 1:
                live_contact = get_contact(next(iter(cids)))
            elif client and len(cids) > 1:
                reviews.append("multiple_bitrix_contact_ids")
            if live_contact:
                phones = live_contact.get("PHONE") if isinstance(live_contact.get("PHONE"), list) else []
                emails = live_contact.get("EMAIL") if isinstance(live_contact.get("EMAIL"), list) else []
                phone_vals = [str(item.get("VALUE") or "").strip() for item in phones if isinstance(item, dict) and item.get("VALUE")]
                email_vals = [str(item.get("VALUE") or "").strip() for item in emails if isinstance(item, dict) and item.get("VALUE")]
                if phone_vals and fill_empty(person, "primary_phone", phone_vals[0]):
                    recovered.append("primary_phone")
                    summary["missing_person_fields_recovered"]["primary_phone"] += 1
                elif phone_vals and conflict(person.primary_phone, phone_vals[0]):
                    reviews.append("phone")
                extra_phones = [item for item in phone_vals[1:] if item and item != person.primary_phone]
                if extra_phones and not person.secondary_phones:
                    person.secondary_phones = extra_phones
                    recovered.append("secondary_phones")
                    summary["missing_person_fields_recovered"]["secondary_phones"] += 1
                if email_vals and fill_empty(person, "primary_email", email_vals[0].lower()):
                    recovered.append("primary_email")
                    summary["missing_person_fields_recovered"]["primary_email"] += 1
                elif email_vals and person.primary_email and email_vals[0].lower() != person.primary_email.lower():
                    reviews.append("email")
                extra_emails = [item.lower() for item in email_vals[1:] if item]
                if extra_emails and not person.secondary_emails:
                    person.secondary_emails = extra_emails
                    recovered.append("secondary_emails")
                    summary["missing_person_fields_recovered"]["secondary_emails"] += 1
                post = scalar(live_contact.get("POST"))
                if post and fill_empty(person, "job_title", post[:120]):
                    recovered.append("job_title")
                    summary["missing_person_fields_recovered"]["job_title"] += 1
                company = scalar(live_contact.get("COMPANY_TITLE"))
                if company and fill_empty(person, "organization_name", company[:255]):
                    recovered.append("organization_name")
                    summary["missing_person_fields_recovered"]["organization_name"] += 1
                assigned = users.get(str(live_contact.get("ASSIGNED_BY_ID") or ""))
                comments = scalar(live_contact.get("COMMENTS"))
                if comments and fill_empty(person, "notes", comments[:4000]):
                    recovered.append("notes")
                    summary["missing_person_fields_recovered"]["notes"] += 1
                address_parts = contact_address_parts(live_contact)
                req = client.call(
                    "crm.requisite.list",
                    {"filter": {"ENTITY_TYPE_ID": 3, "ENTITY_ID": next(iter(cids))}, "select": ["ID", "NAME", "RQ_COMPANY_NAME"]},
                )
                req_rows = req.get("result") if isinstance(req.get("result"), list) else []
                for requisite in req_rows:
                    if not isinstance(requisite, dict) or not requisite.get("ID"):
                        continue
                    addr = client.call("crm.address.list", {"filter": {"ENTITY_ID": requisite.get("ID")}})
                    addr_rows = addr.get("result") if isinstance(addr.get("result"), list) else []
                    if not addr_rows and isinstance(addr.get("result"), dict):
                        addr_rows = [addr.get("result")]
                    for row in addr_rows:
                        if not isinstance(row, dict):
                            continue
                        line = " ".join(
                            str(row.get(key) or "").strip()
                            for key in ("ADDRESS_1", "ADDRESS_2")
                            if row.get(key)
                        ).strip()
                        if line and not address_parts.get("address_line1"):
                            address_parts["address_line1"] = line[:255]
                        if row.get("CITY") and not address_parts.get("city"):
                            address_parts["city"] = str(row.get("CITY"))[:120]
                        if row.get("REGION") and not address_parts.get("state_province"):
                            address_parts["state_province"] = str(row.get("REGION"))[:120]
                        if row.get("POSTAL_CODE") and not address_parts.get("postal_code"):
                            address_parts["postal_code"] = str(row.get("POSTAL_CODE"))[:30]
                        if row.get("COUNTRY") and not address_parts.get("country"):
                            address_parts["country"] = str(row.get("COUNTRY"))[:100]
                        break
                    if address_parts.get("address_line1") or address_parts.get("city"):
                        break
                if address_parts.get("address_line1") and fill_empty(person, "address_line1", address_parts["address_line1"]):
                    recovered.append("address_line1")
                    summary["missing_addresses_recovered"] += 1
                for field in ("city", "state_province", "postal_code", "country"):
                    if address_parts.get(field) and fill_empty(person, field, address_parts[field]):
                        recovered.append(field)
                        summary["missing_person_fields_recovered"][field] += 1
                _, _, extra = labeled_from_entity(live_contact, contact_fields)
                profile = extra[:]
                if address_parts.get("address_line1"):
                    profile.insert(0, {"label": "Adres", "value": address_parts["address_line1"]})
                elif address_parts.get("city"):
                    profile.insert(0, {"label": "Şehir", "value": address_parts["city"]})
                if post:
                    profile.append({"label": "Pozisyon", "value": post})
                source_id = str(live_contact.get("SOURCE_ID") or "").strip()
                source_name = sources.get(source_id) or scalar(live_contact.get("SOURCE_DESCRIPTION")) or source_id or None
                merge_live(
                    person,
                    {
                        "contact_id": next(iter(cids)),
                        "assigned_by_id": str(live_contact.get("ASSIGNED_BY_ID") or "") or None,
                        "assigned_name": assigned,
                        "source_id": source_id or None,
                        "source_name": source_name,
                        "address": address_parts.get("address_line1") or address_parts.get("city"),
                        "has_phone": bool(phone_vals),
                        "has_email": bool(email_vals),
                        "has_address": bool(address_parts.get("address_line1") or address_parts.get("city")),
                        "profile_fields": profile,
                    },
                )
            bitrix_has_phone = bool(live_contact and phone_vals) if live_contact else False
            bitrix_has_email = bool(live_contact and email_vals) if live_contact else False
            bitrix_has_address = False
            if live_contact:
                bitrix_has_address = bool(address_parts.get("address_line1") or address_parts.get("city"))
            missing = []
            if bitrix_has_phone and not person.primary_phone:
                missing.append("phone")
            if bitrix_has_email and not person.primary_email:
                missing.append("email")
            if bitrix_has_address and not (person.address_line1 or person.city):
                missing.append("address")
            if missing:
                summary["people_still_incomplete"].append(
                    {"contact_id": str(person.id), "name": person.display_name, "missing": missing, "legacy": legacy}
                )
            if reviews:
                person.review_required = True
                summary["review_required"].append({"contact": person.display_name, "fields": reviews})
            people_rows.append(
                {
                    "contact_id": str(person.id),
                    "name": person.display_name,
                    "legacy": legacy,
                    "recovered": "|".join(recovered),
                    "missing": "|".join(missing),
                    "bitrix_contact_ids": ",".join(sorted(cids)),
                }
            )

        for row in agreements:
            person = contacts_by_id.get(row.contact_id)
            meta = dict(row.metadata_json or {}) if isinstance(row.metadata_json, dict) else {}
            live_meta = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
            deal_id = deal_id_for_agreement(row.id, meta) or str(live_meta.get("bitrix_deal_id") or meta.get("bitrix_deal_id") or "").strip()
            legacy = bool(person and normalize_full_name(person.display_name) in LEGACY_NAMES)
            recovered: list[str] = []
            if legacy and not deal_id:
                summary["legacy_manual_agreements"].append(
                    {
                        "agreement_id": str(row.id),
                        "name": person.display_name if person else "",
                        "project": row.project_group,
                        "unit": row.unit_number,
                        "source_external_id": row.source_external_id,
                    }
                )
            deal = get_deal(deal_id) if client and deal_id.isdigit() else None
            if deal:
                if fill_empty(row, "unit_number", None):
                    pass
                if not meta.get("opportunity") and deal.get("OPPORTUNITY") not in (None, ""):
                    meta["opportunity"] = str(deal.get("OPPORTUNITY"))
                    recovered.append("opportunity")
                    summary["purchase_fields_recovered"]["opportunity"] += 1
                if not meta.get("currency") and deal.get("CURRENCY_ID"):
                    meta["currency"] = str(deal.get("CURRENCY_ID"))
                    recovered.append("currency")
                    summary["purchase_fields_recovered"]["currency"] += 1
                if not meta.get("begin_date") and deal.get("BEGINDATE"):
                    meta["begin_date"] = date_only(deal.get("BEGINDATE"))
                    recovered.append("begin_date")
                    summary["purchase_fields_recovered"]["begin_date"] += 1
                if not meta.get("close_date") and deal.get("CLOSEDATE"):
                    meta["close_date"] = date_only(deal.get("CLOSEDATE"))
                    recovered.append("close_date")
                    summary["purchase_fields_recovered"]["close_date"] += 1
                stage_id = str(deal.get("STAGE_ID") or "")
                stage_label = statuses.get(stage_id) or live_meta.get("stage_label")
                if stage_label:
                    meta["stage_label"] = stage_label
                    live_meta["stage_label"] = stage_label
                comments = scalar(deal.get("COMMENTS"))
                assigned = users.get(str(deal.get("ASSIGNED_BY_ID") or ""))
                payment, llc, extra = labeled_from_entity(deal, deal_fields)
                if payment and not live_meta.get("payment_fields"):
                    live_meta["payment_fields"] = payment
                    recovered.append("payment_fields")
                    summary["purchase_fields_recovered"]["payment_fields"] += 1
                if llc and not live_meta.get("llc_fields"):
                    live_meta["llc_fields"] = llc
                    recovered.append("llc_fields")
                    summary["purchase_fields_recovered"]["llc_fields"] += 1
                if extra:
                    live_meta["extra_fields"] = extra
                    recovered.append("extra_fields")
                if comments and not live_meta.get("comments") and not meta.get("comments"):
                    live_meta["comments"] = comments
                    recovered.append("comments")
                    summary["purchase_fields_recovered"]["comments"] += 1
                if assigned:
                    live_meta["assigned_name"] = assigned
                live_meta.update(
                    {
                        "bitrix_deal_id": deal_id,
                        "stage_id": stage_id,
                        "opportunity": str(deal.get("OPPORTUNITY") or live_meta.get("opportunity") or "") or None,
                        "currency": str(deal.get("CURRENCY_ID") or live_meta.get("currency") or "") or None,
                        "begin_date": date_only(deal.get("BEGINDATE")) or live_meta.get("begin_date"),
                        "close_date": date_only(deal.get("CLOSEDATE")) or live_meta.get("close_date"),
                        "title": deal.get("TITLE"),
                    }
                )
                meta["bitrix_deal_id"] = deal_id
                meta["bitrix_live"] = live_meta
                if deal_id:
                    meta["purchase_card_verified"] = True
                    live_meta["purchase_card_verified"] = True
                row.metadata_json = meta
                flag_modified(row, "metadata_json")
                items_body = client.call("crm.deal.contact.items.get", {"id": deal_id}) if client else {}
                items = items_body.get("result") if isinstance(items_body.get("result"), list) else []
                if not items and deal.get("CONTACT_ID"):
                    items = [{"CONTACT_ID": deal.get("CONTACT_ID"), "IS_PRIMARY": "Y"}]
                mapped = 0
                for index, item in enumerate(items):
                    cid = str(item.get("CONTACT_ID") or "").strip()
                    if not cid:
                        continue
                    os_contact = None
                    for candidate in contacts_by_id.values():
                        if cid in bitrix_contact_ids(candidate):
                            os_contact = candidate
                            break
                    if os_contact is None or not is_purchase_owner_contact(os_contact):
                        continue
                    mapped += 1
                    existing = db.scalar(
                        select(CrmAgreementParticipant).where(
                            CrmAgreementParticipant.agreement_id == row.id,
                            CrmAgreementParticipant.contact_id == os_contact.id,
                        )
                    )
                    is_primary = str(item.get("IS_PRIMARY") or "").upper() in {"Y", "1", "TRUE"} or index == 0
                    if existing is None:
                        db.add(
                            CrmAgreementParticipant(
                                id=uuid4(),
                                agreement_id=row.id,
                                contact_id=os_contact.id,
                                role="owner",
                                ownership_pct=Decimal("100.00") if len(items) == 1 else None,
                                is_primary=is_primary,
                                source="bitrix_live",
                                metadata_json={"bitrix_deal_id": deal_id, "bitrix_contact_id": cid},
                            )
                        )
                    elif existing.ownership_pct is None and len(items) == 1:
                        existing.ownership_pct = Decimal("100.00")
                if mapped > 1:
                    summary["joint_purchases"].append(
                        {"agreement_id": str(row.id), "deal_id": deal_id, "owners": mapped}
                    )
                linked = link_deal_documents(db, row.id, deal_id)
                summary["documents_newly_linked"] += linked
            elif not deal_id:
                incomplete = ["no_verified_bitrix_deal"]
                if not row.unit_number and row.project_group != "reit":
                    incomplete.append("unit")
                if not row.investment_amount and not meta.get("opportunity"):
                    incomplete.append("amount")
                summary["purchases_still_incomplete"].append(
                    {
                        "agreement_id": str(row.id),
                        "name": person.display_name if person else "",
                        "project": row.project_group,
                        "unit": row.unit_number,
                        "missing": incomplete,
                        "legacy": legacy,
                    }
                )
            card = get_purchase_card(db, row.id, viewer_contact_id=row.contact_id)
            doc_count = card.document_count if card else 0
            hist_count = card.history_count if card else 0
            wa = 0
            if card:
                wa = sum(1 for item in card.history if item.activity_type == "whatsapp")
            if card and wa == 0:
                summary["history_whatsapp_gaps"].append(
                    {
                        "agreement_id": str(row.id),
                        "deal_id": deal_id,
                        "name": person.display_name if person else "",
                        "history_count": hist_count,
                    }
                )
            uf_count = 0
            activity_count = 0
            if card:
                uf_count = sum(1 for item in card.documents if item.source == "Satış belgesi")
                activity_count = sum(1 for item in card.documents if item.source == "E-posta / Aktivite eki")
            summary["purchase_document_counts"].append(
                {
                    "agreement_id": str(row.id),
                    "deal_id": deal_id,
                    "name": person.display_name if person else "",
                    "project": row.project_group,
                    "unit": row.unit_number,
                    "documents": doc_count,
                    "uf": uf_count,
                    "activity": activity_count,
                    "history": hist_count,
                    "whatsapp": wa,
                }
            )
            purchase_rows.append(
                {
                    "agreement_id": str(row.id),
                    "contact": person.display_name if person else "",
                    "project": row.project_group,
                    "unit": row.unit_number or "",
                    "deal_id": deal_id,
                    "legacy": legacy,
                    "recovered": "|".join(recovered),
                    "documents": doc_count,
                    "history": hist_count,
                    "whatsapp": wa,
                    "amount": card.amount_label if card else "",
                    "stage": card.stage if card else "",
                }
            )

        by_person: dict[str, set[str]] = defaultdict(set)
        for row in agreements:
            by_person[str(row.contact_id)].add(str(row.id))
        for part in db.scalars(select(CrmAgreementParticipant)).all():
            by_person[str(part.contact_id)].add(str(part.agreement_id))
        for cid, ids in by_person.items():
            if len(ids) > 1:
                person = db.get(CrmContact, UUID(cid))
                if person is None or not is_purchase_owner_contact(person):
                    continue
                summary["people_with_multiple_purchases"].append(
                    {"contact_id": cid, "name": person.display_name if person else "", "purchases": len(ids)}
                )
        db.commit()
        summary["bitrix_calls"] = client.call_count if client else 0
        summary["missing_person_fields_recovered"] = dict(summary["missing_person_fields_recovered"])
        summary["purchase_fields_recovered"] = dict(summary["purchase_fields_recovered"])
        complete_people = summary["agreement_customers_checked"] - len(summary["people_still_incomplete"])
        complete_purchases = summary["purchases_checked"] - len(summary["purchases_still_incomplete"])
        denom = max(1, summary["agreement_customers_checked"] + summary["purchases_checked"])
        summary["final_completeness_percentage"] = round(
            100.0 * (complete_people + complete_purchases) / denom, 1
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    (OUT / "reports" / "SUMMARY.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    with (OUT / "reports" / "PEOPLE.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["contact_id", "name", "legacy", "recovered", "missing", "bitrix_contact_ids"])
        writer.writeheader()
        writer.writerows(people_rows)
    with (OUT / "reports" / "PURCHASES.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["agreement_id", "contact", "project", "unit", "deal_id", "legacy", "recovered", "documents", "history", "whatsapp", "amount", "stage"],
        )
        writer.writeheader()
        writer.writerows(purchase_rows)
    print(json.dumps({k: summary[k] for k in ("agreement_customers_checked", "purchases_checked", "final_completeness_percentage", "documents_newly_linked", "bitrix_calls")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
