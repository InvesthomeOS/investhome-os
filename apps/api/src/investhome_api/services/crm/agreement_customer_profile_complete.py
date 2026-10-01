"""Fill blank agreement-customer CRM profile fields from Bitrix. Contacts only.

Never creates people. Never overwrites existing OS values. Never touches
purchases, ownership, amounts, documents, activities, or unit history.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.identity import (
    is_zero_masked_phone,
    normalize_full_name,
    normalize_valid_email,
    parse_phone,
)

OYA_EMAIL = "oyanerminuyan@gmail.com"
OYA_NAME_KEY = normalize_full_name("Oya Nermin Uyan")
OYA_ADDRESS = "Yeşiltepe Mah. Modern Sanayi Sitesi 8043 Sok. No:5 Erenler / Sakarya"
PROVENANCE = "Bitrix customer profile / delivery address"
_METADATA_KEY = "bitrix_profile_complete"
_BITRIX_CONTACT_RE = re.compile(r"bitrix_contact:(\d+)")
_COLUMN_LIMITS = {
    "address_line1": 255,
    "address_line2": 255,
    "city": 120,
    "state_province": 120,
    "postal_code": 30,
    "country": 100,
    "organization_name": 255,
    "job_title": 120,
    "primary_email": 255,
    "primary_phone": 50,
}
_PROFILE_LABELS = {
    "adres": "address_line1",
    "address": "address_line1",
    "delivery address": "address_line1",
    "teslimat adresi": "address_line1",
    "şehir": "city",
    "sehir": "city",
    "city": "city",
    "bölge": "state_province",
    "bolge": "state_province",
    "region": "state_province",
    "il": "state_province",
    "ülke": "country",
    "ulke": "country",
    "country": "country",
    "pozisyon": "job_title",
    "position": "job_title",
    "şirket": "organization_name",
    "sirket": "organization_name",
    "company": "organization_name",
}


def _clip(value: Any, limit: int | None) -> str | None:
    if value is None or not str(value).strip():
        return None
    text = str(value).strip()
    if text in {"—", "-", "none", "null", "N/A", "n/a"}:
        return None
    if limit is not None and len(text) > limit:
        return None
    return text


def _blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not any(str(item).strip() for item in value if item is not None)
    return False


def _scalar(value: Any) -> str | None:
    if value in (None, "", [], {}, 0, "0"):
        return None
    if isinstance(value, list):
        parts = [_scalar(item) for item in value]
        text = ", ".join(part for part in parts if part)
        return text or None
    if isinstance(value, dict):
        for key in ("VALUE", "value", "label", "NAME", "title"):
            if value.get(key):
                return str(value.get(key)).strip() or None
        return None
    text = str(value).strip()
    return text or None


def _safe_phone(value: str | None) -> str | None:
    if not value or is_zero_masked_phone(value):
        return None
    parsed = parse_phone(value)
    if parsed and parsed.e164 and not parsed.suspicious:
        return parsed.e164
    text = str(value).strip()
    return text or None


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


def _flatten(payload: dict[str, Any] | None) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in (payload or {}).items():
        if isinstance(value, dict):
            for inner_k, inner_v in value.items():
                if isinstance(inner_v, list):
                    flat[f"{key}[{inner_k}][]"] = inner_v
                else:
                    flat[f"{key}[{inner_k}]"] = inner_v
        else:
            flat[key] = value
    return flat


class BitrixClient:
    def __init__(self, base: str) -> None:
        self.base = base if base.endswith("/") else base + "/"
        self.call_count = 0
        self._last = 0.0

    def call(self, method: str, payload: dict | None = None) -> dict[str, Any]:
        url = urllib.parse.urljoin(self.base, method + ".json")
        last = "unknown"
        for attempt in range(5):
            delta = time.time() - self._last
            if delta < 0.35:
                time.sleep(0.35 - delta)
            self.call_count += 1
            data = urllib.parse.urlencode(_flatten(payload), doseq=True).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    parsed = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError:
                    parsed = {"error": f"HTTP {exc.code}", "error_description": raw[:400]}
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


def _bitrix_contact_ids(contact: CrmContact) -> set[str]:
    ids: set[str] = set()
    blob = json.dumps(contact.metadata_json or {}, ensure_ascii=False)
    ids.update(_BITRIX_CONTACT_RE.findall(blob))
    live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
    if isinstance(live, dict) and live.get("contact_id"):
        ids.add(str(live.get("contact_id")).strip())
    return {item for item in ids if item.isdigit()}


def _fill_if_empty(contact: CrmContact, field_name: str, value: Any) -> bool:
    clipped = _clip(value, _COLUMN_LIMITS.get(field_name))
    if clipped is None:
        return False
    current = getattr(contact, field_name)
    if not _blank(current):
        return False
    setattr(contact, field_name, clipped)
    return True


def _fill_secondary(contact: CrmContact, field_name: str, incoming: list[str], skip: set[str]) -> int:
    if not incoming or not _blank(getattr(contact, field_name)):
        return 0
    extra: list[str] = []
    seen = set(skip)
    for item in incoming:
        if item and item not in seen:
            extra.append(item)
            seen.add(item)
    if not extra:
        return 0
    setattr(contact, field_name, extra)
    flag_modified(contact, field_name)
    return len(extra)


def _record_provenance(contact: CrmContact, filled: dict[str, str]) -> None:
    if not filled:
        return
    meta = dict(contact.metadata_json or {}) if isinstance(contact.metadata_json, dict) else {}
    payload = dict(meta.get(_METADATA_KEY) or {}) if isinstance(meta.get(_METADATA_KEY), dict) else {}
    fields = dict(payload.get("fields") or {}) if isinstance(payload.get("fields"), dict) else {}
    fields.update(filled)
    payload["source"] = PROVENANCE
    payload["fields"] = fields
    payload["updated_at"] = datetime.now(UTC).isoformat()
    meta[_METADATA_KEY] = payload
    contact.metadata_json = meta
    flag_modified(contact, "metadata_json")


def _merge_live(contact: CrmContact, payload: dict[str, Any]) -> None:
    meta = dict(contact.metadata_json or {}) if isinstance(contact.metadata_json, dict) else {}
    live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
    changed = False
    for key, value in payload.items():
        if value in (None, "", [], {}):
            continue
        current = live.get(key)
        if current in (None, "", [], {}) or current != value:
            live[key] = value
            changed = True
    if not changed:
        return
    meta["bitrix_live"] = live
    contact.metadata_json = meta
    flag_modified(contact, "metadata_json")


def _stored_bitrix_values(contact: CrmContact) -> dict[str, str]:
    values: dict[str, str] = {}
    meta = contact.metadata_json if isinstance(contact.metadata_json, dict) else {}
    live = meta.get("bitrix_live") if isinstance(meta.get("bitrix_live"), dict) else {}
    address = _clip(live.get("address"), 255)
    if address:
        values["address_line1"] = address
    for row in live.get("profile_fields") or []:
        if not isinstance(row, dict):
            continue
        label = str(row.get("label") or "").strip().casefold()
        field = _PROFILE_LABELS.get(label)
        value = _clip(row.get("value"), _COLUMN_LIMITS.get(field or "", 255))
        if field and value and field not in values:
            values[field] = value
    extras = meta.get("bitrix_import") if isinstance(meta.get("bitrix_import"), dict) else {}
    source_extras = extras.get("source_extras") if isinstance(extras.get("source_extras"), dict) else {}
    if source_extras.get("responsible") and not live.get("assigned_name"):
        values["assigned_name"] = str(source_extras.get("responsible")).strip()
    return values


def _multivalues(entity: dict[str, Any], key: str) -> list[str]:
    raw = entity.get(key)
    items = raw if isinstance(raw, list) else []
    out: list[str] = []
    for item in items:
        text = None
        if isinstance(item, dict):
            text = str(item.get("VALUE") or "").strip()
        elif item:
            text = str(item).strip()
        if text:
            out.append(text)
    return out


def _address_from_rows(rows: list[dict[str, Any]]) -> dict[str, str]:
    parts: dict[str, str] = {}
    ranked = sorted(
        (row for row in rows if isinstance(row, dict)),
        key=lambda row: 0 if str(row.get("TYPE_ID") or "") == "11" else (1 if str(row.get("TYPE_ID") or "") == "1" else 2),
    )
    for row in ranked:
        line = " ".join(
            str(row.get(key) or "").strip()
            for key in ("ADDRESS_1", "ADDRESS_2")
            if row.get(key)
        ).strip()
        if line and "address_line1" not in parts:
            clipped = _clip(line, 255)
            if clipped:
                parts["address_line1"] = clipped
        if row.get("CITY") and "city" not in parts:
            clipped = _clip(row.get("CITY"), 120)
            if clipped:
                parts["city"] = clipped
        region = row.get("REGION") or row.get("PROVINCE")
        if region and "state_province" not in parts:
            clipped = _clip(region, 120)
            if clipped:
                parts["state_province"] = clipped
        if row.get("POSTAL_CODE") and "postal_code" not in parts:
            clipped = _clip(row.get("POSTAL_CODE"), 30)
            if clipped:
                parts["postal_code"] = clipped
        if row.get("COUNTRY") and "country" not in parts:
            clipped = _clip(row.get("COUNTRY"), 100)
            if clipped:
                parts["country"] = clipped
        if parts.get("address_line1"):
            break
    return parts


def _live_contact_values(live: dict[str, Any], address_parts: dict[str, str]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    phones = [_safe_phone(item) for item in _multivalues(live, "PHONE")]
    emails = [normalize_valid_email(item) or (item.lower() if "@" in item else None) for item in _multivalues(live, "EMAIL")]
    values["phones"] = [item for item in phones if item]
    values["emails"] = [item for item in emails if item]
    post = _clip(live.get("POST"), 120)
    if post:
        values["job_title"] = post
    company = _clip(live.get("COMPANY_TITLE"), 255)
    if company:
        values["organization_name"] = company
    line = " ".join(item for item in (_scalar(live.get("ADDRESS")), _scalar(live.get("ADDRESS_2"))) if item)
    if line and "address_line1" not in address_parts:
        clipped = _clip(line, 255)
        if clipped:
            address_parts["address_line1"] = clipped
    city = _clip(live.get("ADDRESS_CITY"), 120)
    if city and "city" not in address_parts:
        address_parts["city"] = city
    region = _clip(live.get("ADDRESS_REGION") or live.get("ADDRESS_PROVINCE"), 120)
    if region and "state_province" not in address_parts:
        address_parts["state_province"] = region
    postal = _clip(live.get("ADDRESS_POSTAL_CODE"), 30)
    if postal and "postal_code" not in address_parts:
        address_parts["postal_code"] = postal
    country = _clip(live.get("ADDRESS_COUNTRY"), 100)
    if country and "country" not in address_parts:
        address_parts["country"] = country
    values.update(address_parts)
    return values


def _fetch_bitrix_profile(client: BitrixClient, contact_id: str, users: dict[str, str]) -> dict[str, Any]:
    body = client.call("crm.contact.get", {"id": contact_id})
    live = body.get("result") if isinstance(body.get("result"), dict) else {}
    if not live:
        return {}
    req = client.call(
        "crm.requisite.list",
        {"filter": {"ENTITY_TYPE_ID": 3, "ENTITY_ID": contact_id}, "select": ["ID", "NAME", "RQ_COMPANY_NAME"]},
    )
    req_rows = req.get("result") if isinstance(req.get("result"), list) else []
    address_parts: dict[str, str] = {}
    for requisite in req_rows:
        if not isinstance(requisite, dict) or not requisite.get("ID"):
            continue
        company = _clip(requisite.get("RQ_COMPANY_NAME"), 255)
        addr = client.call("crm.address.list", {"filter": {"ENTITY_ID": requisite.get("ID")}})
        addr_rows = addr.get("result") if isinstance(addr.get("result"), list) else []
        if not addr_rows and isinstance(addr.get("result"), dict):
            addr_rows = [addr.get("result")]
        parts = _address_from_rows([row for row in addr_rows if isinstance(row, dict)])
        for key, value in parts.items():
            address_parts.setdefault(key, value)
        if company and "organization_name" not in address_parts:
            address_parts["organization_name"] = company
        if address_parts.get("address_line1"):
            break
    values = _live_contact_values(live, address_parts)
    assigned_id = str(live.get("ASSIGNED_BY_ID") or "").strip()
    if assigned_id and users.get(assigned_id):
        values["assigned_name"] = users[assigned_id]
    return values


def _is_oya(contact: CrmContact) -> bool:
    email = (contact.primary_email or "").strip().lower()
    if email == OYA_EMAIL:
        return True
    return normalize_full_name(contact.display_name) == OYA_NAME_KEY


def _apply_values(contact: CrmContact, values: dict[str, Any], *, oya: bool) -> dict[str, str]:
    filled: dict[str, str] = {}
    phones = list(values.get("phones") or [])
    emails = list(values.get("emails") or [])
    if phones and _fill_if_empty(contact, "primary_phone", phones[0]):
        filled["primary_phone"] = PROVENANCE
    added = _fill_secondary(contact, "secondary_phones", phones[1:], {contact.primary_phone or "", *phones[:1]})
    if added:
        filled["secondary_phones"] = PROVENANCE
    if emails and _fill_if_empty(contact, "primary_email", emails[0]):
        filled["primary_email"] = PROVENANCE
    added = _fill_secondary(contact, "secondary_emails", emails[1:], {str(contact.primary_email or "").lower(), *emails[:1]})
    if added:
        filled["secondary_emails"] = PROVENANCE
    for field in ("organization_name", "job_title", "city", "state_province", "postal_code", "country", "address_line2"):
        if values.get(field) and _fill_if_empty(contact, field, values.get(field)):
            filled[field] = PROVENANCE
    address = OYA_ADDRESS if oya else values.get("address_line1")
    if address and _fill_if_empty(contact, "address_line1", address):
        filled["address_line1"] = PROVENANCE
    assigned = _clip(values.get("assigned_name"), 255)
    if assigned:
        live = (contact.metadata_json or {}).get("bitrix_live") if isinstance(contact.metadata_json, dict) else None
        if not (isinstance(live, dict) and str(live.get("assigned_name") or "").strip()):
            _merge_live(contact, {"assigned_name": assigned})
            filled["assigned_name"] = PROVENANCE
    if oya and address:
        _merge_live(
            contact,
            {
                "address": OYA_ADDRESS,
                "has_address": True,
                "profile_fields": [{"label": "Adres", "value": OYA_ADDRESS}],
            },
        )
    _record_provenance(contact, filled)
    return filled


def _table_fingerprint(db: Session, sql: str) -> str:
    rows = [list(row) for row in db.execute(text(sql)).fetchall()]
    return hashlib.sha256(json.dumps(rows, default=str, ensure_ascii=False).encode("utf-8")).hexdigest()


def agreement_safety_fingerprint(db: Session) -> dict[str, str]:
    return {
        "agreements": _table_fingerprint(
            db,
            "select id::text, contact_id::text, project_group, unit_number, "
            "investment_amount::text, status::text, source, source_external_id, "
            "updated_at::text from crm_agreements order by id",
        ),
        "participants": _table_fingerprint(
            db,
            "select id::text, agreement_id::text, contact_id::text, role, "
            "is_primary::text, ownership_pct::text from crm_agreement_participants order by id",
        ),
        "documents": _table_fingerprint(db, "select count(*)::text, coalesce(max(updated_at)::text,'') from documents"),
        "activities": _table_fingerprint(
            db, "select count(*)::text, coalesce(max(updated_at)::text,'') from crm_activities"
        ),
    }


def load_users(client: BitrixClient) -> dict[str, str]:
    users: dict[str, str] = {}
    start = 0
    while True:
        body = client.call("user.get", {"start": start})
        chunk = body.get("result") if isinstance(body.get("result"), list) else []
        if not chunk:
            break
        for user in chunk:
            if not isinstance(user, dict) or not user.get("ID"):
                continue
            name = " ".join(part for part in (user.get("NAME"), user.get("LAST_NAME")) if part).strip()
            users[str(user.get("ID"))] = name or str(user.get("ID"))
        nxt = body.get("next")
        if nxt in (None, ""):
            break
        start = int(nxt)
    return users


def agreement_customer_ids(db: Session) -> list[UUID]:
    agreements = list(db.scalars(select(CrmAgreement)).all())
    participants = list(db.scalars(select(CrmAgreementParticipant)).all())
    ids = {row.contact_id for row in agreements} | {item.contact_id for item in participants}
    return sorted(ids, key=str)


def run_agreement_customer_profile_complete(db: Session) -> dict[str, Any]:
    before = agreement_safety_fingerprint(db)
    customer_ids = agreement_customer_ids(db)
    people = list(db.scalars(select(CrmContact).where(CrmContact.id.in_(customer_ids))).all())
    by_id = {row.id: row for row in people}
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    client = BitrixClient(webhook_base(raw)) if raw else None
    users = load_users(client) if client else {}
    contact_cache: dict[str, dict[str, Any]] = {}

    summary: dict[str, Any] = {
        "customers_checked": 0,
        "customers_completed": 0,
        "addresses_added": 0,
        "phone_additions": 0,
        "email_additions": 0,
        "fields_filled": Counter(),
        "still_missing_because_bitrix_empty": [],
        "oya": None,
        "overwritten_verified_values": 0,
        "people_created": 0,
        "webhook_used": bool(client),
        "bitrix_calls": 0,
        "safety_before": before,
    }
    oya_matches = [row for row in people if _is_oya(row)]
    if len(oya_matches) != 1:
        summary["oya_error"] = f"expected 1 Oya person, found {len(oya_matches)}"
        return summary

    for contact_id in customer_ids:
        contact = by_id.get(contact_id)
        if contact is None:
            continue
        summary["customers_checked"] += 1
        oya = _is_oya(contact)
        values: dict[str, Any] = dict(_stored_bitrix_values(contact))
        stored_phones = values.pop("phones", None)
        stored_emails = values.pop("emails", None)
        if stored_phones:
            values["phones"] = stored_phones
        if stored_emails:
            values["emails"] = stored_emails
        cids = _bitrix_contact_ids(contact)
        bitrix_values: dict[str, Any] = {}
        if client and len(cids) == 1:
            cid = next(iter(cids))
            if cid not in contact_cache:
                contact_cache[cid] = _fetch_bitrix_profile(client, cid, users)
            bitrix_values = dict(contact_cache.get(cid) or {})
        for key, value in bitrix_values.items():
            if key in {"phones", "emails"}:
                existing = list(values.get(key) or [])
                for item in value or []:
                    if item not in existing:
                        existing.append(item)
                values[key] = existing
            elif value and key not in values:
                values[key] = value
        before_fields = {
            "address_line1": contact.address_line1,
            "city": contact.city,
            "state_province": contact.state_province,
            "country": contact.country,
            "primary_phone": contact.primary_phone,
            "primary_email": contact.primary_email,
            "organization_name": contact.organization_name,
            "job_title": contact.job_title,
            "secondary_phones": list(contact.secondary_phones or []),
            "secondary_emails": list(contact.secondary_emails or []),
        }
        filled = _apply_values(contact, values, oya=oya)
        if filled:
            summary["customers_completed"] += 1
            for field in filled:
                summary["fields_filled"][field] += 1
            if "address_line1" in filled:
                summary["addresses_added"] += 1
            if "primary_phone" in filled or "secondary_phones" in filled:
                summary["phone_additions"] += 1
            if "primary_email" in filled or "secondary_emails" in filled:
                summary["email_additions"] += 1
        for field, previous in before_fields.items():
            current = getattr(contact, field)
            if not _blank(previous) and current != previous:
                summary["overwritten_verified_values"] += 1
        missing: list[str] = []
        bitrix_had = {
            "address": bool(values.get("address_line1") or (oya and OYA_ADDRESS)),
            "city": bool(values.get("city")),
            "region": bool(values.get("state_province")),
            "country": bool(values.get("country")),
            "phone": bool(values.get("phones") or contact.primary_phone),
            "email": bool(values.get("emails") or contact.primary_email),
            "company": bool(values.get("organization_name")),
            "position": bool(values.get("job_title")),
        }
        if _blank(contact.address_line1) and not bitrix_had["address"]:
            missing.append("address")
        if _blank(contact.city) and not bitrix_had["city"]:
            missing.append("city")
        if _blank(contact.state_province) and not bitrix_had["region"]:
            missing.append("region")
        if _blank(contact.country) and not bitrix_had["country"]:
            missing.append("country")
        if _blank(contact.primary_phone) and not bitrix_had["phone"]:
            missing.append("phone")
        if _blank(contact.primary_email) and not bitrix_had["email"]:
            missing.append("email")
        if _blank(contact.organization_name) and not bitrix_had["company"]:
            missing.append("company")
        if _blank(contact.job_title) and not bitrix_had["position"]:
            missing.append("position")
        if missing:
            summary["still_missing_because_bitrix_empty"].append(
                {"name": contact.display_name, "missing": missing}
            )
        if oya:
            summary["oya"] = {
                "contact_id": str(contact.id),
                "name": contact.display_name,
                "phone": contact.primary_phone,
                "email": contact.primary_email,
                "address": contact.address_line1,
                "filled": filled,
                "created_new_person": False,
            }

    db.flush()
    db.commit()
    after = agreement_safety_fingerprint(db)
    summary["safety_after"] = after
    summary["purchases_unchanged"] = before == after
    summary["fields_filled"] = dict(summary["fields_filled"])
    if client:
        summary["bitrix_calls"] = client.call_count
    summary["still_missing_count"] = len(summary["still_missing_because_bitrix_empty"])
    return summary
