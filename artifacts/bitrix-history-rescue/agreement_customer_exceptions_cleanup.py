"""Clean remaining agreement-customer exceptions. Bitrix is read-only."""
from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_activity import (
    CrmActivity,
    CrmActivityCategory,
    CrmActivityEntityType,
    CrmActivityPriority,
    CrmActivityStatus,
    CrmActivityType,
    CrmActivityVisibility,
)
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import (
    CrmContact,
    CrmContactBrokerProfile,
    CrmContactType,
    CrmContactTypeAssignment,
)
from investhome_api.services.crm.agreement_service import is_purchase_owner_contact
from investhome_api.services.crm.identity import is_agent_advisor_name, normalize_full_name
from investhome_api.services.crm.nedim_purchase_card import deal_id_for_agreement

from agreement_customers_final_model import (
    BitrixClient,
    bitrix_contact_ids,
    contact_address_parts,
    fill_empty,
    merge_live,
    scalar,
    webhook_base,
)

OUT = Path("/tmp/AGREEMENT_CUSTOMER_EXCEPTIONS")
MUSA_ID = UUID("6f809981-a5a7-4956-a0e8-2f1a7ba4f510")
PEOPLE = {
    "mujgan": UUID("5a2c45ab-65dd-48ca-998c-57396b974bff"),
    "alp": UUID("aeac43c5-2356-4c0b-97db-5a721c6afd57"),
    "ece": UUID("2738b31c-256d-4feb-8d00-74de6d808878"),
    "ozan": UUID("d4613fb1-8e34-4251-b3ff-6e525194e01e"),
    "burcu": UUID("bb5c71e8-12e2-4d77-8650-f8fbbb577f89"),
    "can": UUID("fb5e39ee-e27c-440b-90c4-cfaafbeb1b02"),
    "yesim": UUID("a58b0466-7744-48b8-9532-2a449dc81709"),
    "murat": UUID("1d728311-01c6-4858-9853-48afe5ba176d"),
}
DEALS = {
    "ozdarendeli": "196",
    "savas": "212",
    "aydemir": "426",
    "zengin": "414",
}


def snapshot(person: CrmContact) -> dict[str, Any]:
    return {
        "contact_id": str(person.id),
        "name": person.display_name,
        "phone": person.primary_phone,
        "email": person.primary_email,
        "address": person.address_line1,
        "city": person.city,
        "state": person.state_province,
        "postal": person.postal_code,
        "country": person.country,
        "company": person.organization_name,
        "position": person.job_title,
        "source": person.source,
        "status": person.status.value if hasattr(person.status, "value") else str(person.status),
        "contact_type": person.contact_type.value if hasattr(person.contact_type, "value") else str(person.contact_type),
        "investor_id": str(person.investor_id) if person.investor_id else None,
        "live": {
            k: (person.metadata_json or {}).get("bitrix_live", {}).get(k)
            for k in ("contact_id", "source_name", "assigned_name", "address")
        }
        if isinstance(person.metadata_json, dict)
        else None,
    }


def live_bits(entity: dict[str, Any]) -> dict[str, Any]:
    phones = entity.get("PHONE") if isinstance(entity.get("PHONE"), list) else []
    emails = entity.get("EMAIL") if isinstance(entity.get("EMAIL"), list) else []
    return {
        "id": entity.get("ID"),
        "name": " ".join(part for part in (entity.get("NAME"), entity.get("LAST_NAME")) if part).strip(),
        "phones": [str(item.get("VALUE") or "").strip() for item in phones if isinstance(item, dict) and item.get("VALUE")],
        "emails": [str(item.get("VALUE") or "").strip() for item in emails if isinstance(item, dict) and item.get("VALUE")],
        "address": contact_address_parts(entity),
        "company": scalar(entity.get("COMPANY_TITLE")),
        "position": scalar(entity.get("POST")),
        "source_id": str(entity.get("SOURCE_ID") or "") or None,
        "assigned_by_id": str(entity.get("ASSIGNED_BY_ID") or "") or None,
        "comments": scalar(entity.get("COMMENTS")),
    }


def apply_live_person(
    person: CrmContact,
    live: dict[str, Any],
    *,
    users: dict[str, str],
    sources: dict[str, str],
    recovered: list[str],
) -> None:
    bits = live_bits(live)
    if bits["phones"] and fill_empty(person, "primary_phone", bits["phones"][0]):
        recovered.append("primary_phone")
    extra_phones = [item for item in bits["phones"][1:] if item and item != person.primary_phone]
    if extra_phones and not person.secondary_phones:
        person.secondary_phones = extra_phones
        recovered.append("secondary_phones")
    if bits["emails"] and fill_empty(person, "primary_email", bits["emails"][0].lower()):
        recovered.append("primary_email")
    extra_emails = [item.lower() for item in bits["emails"][1:] if item]
    if extra_emails and not person.secondary_emails:
        person.secondary_emails = extra_emails
        recovered.append("secondary_emails")
    if bits["position"] and fill_empty(person, "job_title", bits["position"][:120]):
        recovered.append("job_title")
    if bits["company"] and fill_empty(person, "organization_name", bits["company"][:255]):
        recovered.append("organization_name")
    if bits["comments"] and fill_empty(person, "notes", bits["comments"][:4000]):
        recovered.append("notes")
    addr = bits["address"]
    if addr.get("address_line1") and fill_empty(person, "address_line1", addr["address_line1"]):
        recovered.append("address_line1")
    for field in ("city", "state_province", "postal_code", "country"):
        if addr.get(field) and fill_empty(person, field, addr[field]):
            recovered.append(field)
    assigned = users.get(bits["assigned_by_id"] or "")
    source_name = sources.get(bits["source_id"] or "") or bits["source_id"]
    merge_live(
        person,
        {
            "contact_id": bits["id"],
            "assigned_name": assigned,
            "source_id": bits["source_id"],
            "source_name": source_name,
            "address": addr.get("address_line1") or addr.get("city"),
            "has_phone": bool(bits["phones"]),
            "has_email": bool(bits["emails"]),
            "has_address": bool(addr.get("address_line1") or addr.get("city")),
        },
    )


def ensure_participant(db: Session, agreement: CrmAgreement, person: CrmContact, *, primary: bool, deal_id: str) -> str:
    existing = db.scalar(
        select(CrmAgreementParticipant).where(
            CrmAgreementParticipant.agreement_id == agreement.id,
            CrmAgreementParticipant.contact_id == person.id,
        )
    )
    if existing is not None:
        if primary and not existing.is_primary:
            existing.is_primary = True
            return "updated_primary"
        return "already"
    db.add(
        CrmAgreementParticipant(
            id=uuid4(),
            agreement_id=agreement.id,
            contact_id=person.id,
            role="owner",
            ownership_pct=None,
            is_primary=primary,
            source="bitrix_live",
            metadata_json={"bitrix_deal_id": deal_id, "linked_by": "exceptions_cleanup"},
        )
    )
    return "added"


def agreement_for_deal(db: Session, deal_id: str) -> CrmAgreement | None:
    rows = list(db.scalars(select(CrmAgreement)).all())
    for row in rows:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        if deal_id_for_agreement(row.id, meta) == deal_id or str(meta.get("bitrix_deal_id") or "") == deal_id:
            return row
    return None


def convert_musa(db: Session, musa: CrmContact) -> dict[str, Any]:
    removed = []
    for part in list(db.scalars(select(CrmAgreementParticipant).where(CrmAgreementParticipant.contact_id == musa.id)).all()):
        removed.append({"agreement_id": str(part.agreement_id), "role": part.role, "source": part.source})
        db.delete(part)
    musa.contact_type = CrmContactType.BROKER
    musa.investor_id = None
    for assignment in list(musa.type_assignments or []):
        db.delete(assignment)
    db.flush()
    db.add(CrmContactTypeAssignment(id=uuid4(), contact_id=musa.id, contact_type=CrmContactType.BROKER, is_primary=True))
    if musa.broker_profile is None:
        db.add(
            CrmContactBrokerProfile(
                id=uuid4(),
                contact_id=musa.id,
                brokerage_name="Investhome Acenta",
                specialization="Yatırım danışmanı",
                notes="Bitrix deal participant was an agency advisor, not a buyer. Kept under Acentalar.",
            )
        )
    meta = dict(musa.metadata_json or {}) if isinstance(musa.metadata_json, dict) else {}
    meta["not_a_buyer"] = True
    meta["exceptions_cleanup"] = {"reason": "acenta_danismani", "removed_from_purchases": removed}
    musa.metadata_json = meta
    db.add(
        CrmActivity(
            entity_type=CrmActivityEntityType.CONTACT,
            entity_id=musa.id,
            activity_type=CrmActivityType.SYSTEM_EVENT,
            activity_category=CrmActivityCategory.SYSTEM,
            title="Acenta olarak sınıflandırıldı",
            description="Alıcı/yatırımcı listelerinden çıkarıldı. Ham geçmiş kayıtları korundu.",
            status=CrmActivityStatus.COMPLETED,
            priority=CrmActivityPriority.MEDIUM,
            visibility=CrmActivityVisibility.ORGANIZATION,
            completed_at=datetime.now(UTC),
            metadata_json={"event": "reclassified_agent_advisor", "removed_participants": removed},
        )
    )
    return {"removed_participants": removed, "kept_as": "Acentalar", "archived": False}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    client = BitrixClient(webhook_base(raw)) if raw else None
    db = SessionLocal()
    recovered: dict[str, list[str]] = {}
    report: dict[str, Any] = {"webhook_used": bool(client), "bitrix_calls": 0, "fields_newly_recovered": {}}
    try:
        users: dict[str, str] = {}
        sources: dict[str, str] = {}
        if client:
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
            src = client.call("crm.status.list", {"filter": {"ENTITY_ID": "SOURCE"}})
            for item in src.get("result") or []:
                if isinstance(item, dict) and item.get("STATUS_ID"):
                    sources[str(item.get("STATUS_ID"))] = str(item.get("NAME") or item.get("STATUS_ID"))

        musa = db.get(CrmContact, MUSA_ID)
        report["musa_before"] = snapshot(musa) if musa else None
        if musa is not None:
            report["musa"] = convert_musa(db, musa)
            report["musa"]["name"] = musa.display_name
            report["musa"]["final_type"] = musa.contact_type.value
            report["musa"]["is_purchase_owner"] = is_purchase_owner_contact(musa)
            report["musa"]["advisor_name_match"] = is_agent_advisor_name(musa.display_name)

        def get_contact(cid: str) -> dict[str, Any]:
            if not client:
                return {}
            body = client.call("crm.contact.get", {"id": cid})
            return body.get("result") if isinstance(body.get("result"), dict) else {}

        def get_deal(did: str) -> dict[str, Any]:
            if not client:
                return {}
            body = client.call("crm.deal.get", {"id": did})
            return body.get("result") if isinstance(body.get("result"), dict) else {}

        def get_items(did: str) -> list[dict[str, Any]]:
            if not client:
                return []
            body = client.call("crm.deal.contact.items.get", {"id": did})
            items = body.get("result") if isinstance(body.get("result"), list) else []
            return [item for item in items if isinstance(item, dict)]

        deal_audit: dict[str, Any] = {}
        os_by_bitrix: dict[str, CrmContact] = {}
        watched = list(PEOPLE.values()) + ([musa.id] if musa else [])
        for person in db.scalars(select(CrmContact).where(CrmContact.id.in_(watched))).all():
            for cid in bitrix_contact_ids(person):
                os_by_bitrix[cid] = person

        for key, deal_id in DEALS.items():
            deal = get_deal(deal_id)
            items = get_items(deal_id)
            people = []
            for item in items:
                cid = str(item.get("CONTACT_ID") or "").strip()
                live = get_contact(cid) if cid else {}
                os_contact = os_by_bitrix.get(cid)
                people.append(
                    {
                        "bitrix_contact_id": cid,
                        "is_primary": str(item.get("IS_PRIMARY") or "").upper() in {"Y", "1", "TRUE"},
                        "live": live_bits(live) if live else None,
                        "os_contact_id": str(os_contact.id) if os_contact else None,
                        "os_name": os_contact.display_name if os_contact else None,
                    }
                )
            agreement = agreement_for_deal(db, deal_id)
            deal_audit[key] = {
                "deal_id": deal_id,
                "title": deal.get("TITLE") if deal else None,
                "opportunity": deal.get("OPPORTUNITY") if deal else None,
                "currency": deal.get("CURRENCY_ID") if deal else None,
                "agreement_id": str(agreement.id) if agreement else None,
                "participants": people,
            }

        recovered_counter: dict[str, int] = {}

        def recover_named(label: str, person: CrmContact | None) -> None:
            if person is None:
                return
            cids = bitrix_contact_ids(person)
            if not client or len(cids) != 1:
                recovered[label] = []
                return
            live = get_contact(next(iter(cids)))
            fields: list[str] = []
            if live:
                apply_live_person(person, live, users=users, sources=sources, recovered=fields)
            recovered[label] = fields
            for field in fields:
                recovered_counter[field] = recovered_counter.get(field, 0) + 1

        for label, pid in PEOPLE.items():
            recover_named(label, db.get(CrmContact, pid))

        links: dict[str, list[str]] = {}
        oz = agreement_for_deal(db, "196")
        if oz is not None:
            mujgan = db.get(CrmContact, PEOPLE["mujgan"])
            alp = db.get(CrmContact, PEOPLE["alp"])
            ece = db.get(CrmContact, PEOPLE["ece"])
            links["ozdarendeli"] = [
                ensure_participant(db, oz, mujgan, primary=True, deal_id="196") if mujgan else "missing",
                ensure_participant(db, oz, alp, primary=False, deal_id="196") if alp else "missing",
                ensure_participant(db, oz, ece, primary=False, deal_id="196") if ece else "missing",
            ]
        savas = agreement_for_deal(db, "212")
        if savas is not None:
            burcu = db.get(CrmContact, PEOPLE["burcu"])
            ozan = db.get(CrmContact, PEOPLE["ozan"])
            links["savas"] = [
                ensure_participant(db, savas, burcu, primary=True, deal_id="212") if burcu else "missing",
                ensure_participant(db, savas, ozan, primary=False, deal_id="212") if ozan else "missing",
            ]
        zengin = agreement_for_deal(db, "414")
        if zengin is not None:
            murat = db.get(CrmContact, PEOPLE["murat"])
            yesim = db.get(CrmContact, PEOPLE["yesim"])
            links["zengin"] = [
                ensure_participant(db, zengin, murat, primary=True, deal_id="414") if murat else "missing",
                ensure_participant(db, zengin, yesim, primary=False, deal_id="414") if yesim else "missing",
            ]

        db.commit()
        report["bitrix_calls"] = client.call_count if client else 0
        report["deal_audit"] = deal_audit
        report["participant_links"] = links
        report["fields_recovered_by_person"] = recovered
        report["fields_newly_recovered"] = recovered_counter
        report["musa_after"] = snapshot(db.get(CrmContact, MUSA_ID)) if musa else None
        for label, pid in PEOPLE.items():
            person = db.get(CrmContact, pid)
            report[f"{label}_after"] = snapshot(person) if person else None
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    (OUT / "reports" / "EXCEPTIONS.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "musa": report.get("musa"),
        "fields_newly_recovered": report.get("fields_newly_recovered"),
        "participant_links": report.get("participant_links"),
        "bitrix_calls": report.get("bitrix_calls"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
