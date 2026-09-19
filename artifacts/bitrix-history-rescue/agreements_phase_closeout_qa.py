"""Read-only final QA of agreement customers and all purchases. Does not write Bitrix or OS."""

from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document
from investhome_api.services.crm.agreement_service import (
    _document_notes,
    get_purchase_card,
    is_purchase_owner_contact,
    list_contact_purchases,
)
from investhome_api.services.crm.identity import is_agent_advisor_name, normalize_full_name
from investhome_api.services.crm.nedim_purchase_card import (
    AGREEMENT_720,
    IZZET_CANONICAL_ID,
    NEDIM_CANONICAL_ID,
    deal_id_for_agreement,
)

from agreement_customers_final_model import (
    BitrixClient,
    LEGACY_NAMES,
    bitrix_contact_ids,
    contact_address_parts,
    field_label,
    labeled_from_entity,
    scalar,
    webhook_base,
)

OUT = Path("/tmp/AGREEMENTS_PHASE_CLOSEOUT")
LALE_ID = UUID("0f966583-13c5-4ca4-a90b-2763383973ae")
MUSA_ID = UUID("6f809981-a5a7-4956-a0e8-2f1a7ba4f510")
MUJGAN_ID = UUID("5a2c45ab-65dd-48ca-998c-57396b974bff")
ALP_ID = UUID("aeac43c5-2356-4c0b-97db-5a721c6afd57")
ECE_ID = UUID("2738b31c-256d-4feb-8d00-74de6d808878")
OZAN_ID = UUID("d4613fb1-8e34-4251-b3ff-6e525194e01e")
BURCU_ID = UUID("bb5c71e8-12e2-4d77-8650-f8fbbb577f89")
YESIM_ID = UUID("a58b0466-7744-48b8-9532-2a449dc81709")
MURAT_ID = UUID("1d728311-01c6-4858-9853-48afe5ba176d")
PHONE_DIGITS = re.compile(r"\D+")
DOC_HINT = re.compile(
    r"s[oö]zle[sş]me|agreement|signed|tapu|dekont|swift|llc|pasaport|passport|teklif|operating|"
    r"reservation|kimlik|invoice|fatura|wire|certificate|cert\b",
    re.I,
)


def money(value: Any) -> Decimal | None:
    text = str(value or "").replace(",", "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def phone_key(value: str | None) -> str | None:
    digits = PHONE_DIGITS.sub("", value or "")
    if len(digits) < 10:
        return None
    return digits[-10:]


def file_ids_from(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        fid = str(value.get("id") or value.get("ID") or value.get("fileId") or "")
        if fid.isdigit() and len(fid) >= 4:
            found.append(fid)
        for nested in value.values():
            found.extend(file_ids_from(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(file_ids_from(item))
            if isinstance(item, (str, int)) and str(item).isdigit() and len(str(item)) >= 4:
                found.append(str(item))
    return list(dict.fromkeys(found))


def flatten_filter(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if isinstance(value, dict):
            for inner_key, inner_val in value.items():
                out[f"{key}[{inner_key}]"] = inner_val
        else:
            out[key] = value
    return out


def issue(bucket: list[dict[str, Any]], **row: Any) -> None:
    bucket.append(row)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    raw = (os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or "").strip()
    if not raw:
        raise SystemExit("MISSING_BITRIX_ADMIN_WEBHOOK_URL")
    client = BitrixClient(webhook_base(raw))
    db = SessionLocal()
    people_issues: list[dict[str, Any]] = []
    purchase_issues: list[dict[str, Any]] = []
    document_gaps: list[dict[str, Any]] = []
    history_gaps: list[dict[str, Any]] = []
    identity_conflicts: list[dict[str, Any]] = []
    special: dict[str, Any] = {}
    try:
        agreements = list(db.scalars(select(CrmAgreement).order_by(CrmAgreement.created_at.asc())).all())
        participants = list(db.scalars(select(CrmAgreementParticipant)).all())
        contacts: dict[UUID, CrmContact] = {}
        wanted = {row.contact_id for row in agreements} | {item.contact_id for item in participants} | {
            LALE_ID,
            MUSA_ID,
            NEDIM_CANONICAL_ID,
            IZZET_CANONICAL_ID,
            MUJGAN_ID,
            ALP_ID,
            ECE_ID,
            OZAN_ID,
            BURCU_ID,
            YESIM_ID,
            MURAT_ID,
        }
        for person in db.scalars(select(CrmContact).where(CrmContact.id.in_(wanted))).all():
            contacts[person.id] = person
        owners = {
            cid
            for cid in ({row.contact_id for row in agreements} | {item.contact_id for item in participants})
            if cid in contacts and is_purchase_owner_contact(contacts[cid])
        }
        parts_by_agreement: dict[UUID, list[CrmAgreementParticipant]] = defaultdict(list)
        for item in participants:
            parts_by_agreement[item.agreement_id].append(item)

        deal_fields = client.call("crm.deal.fields", {}).get("result") or {}
        file_fields = {
            key
            for key, spec in (deal_fields.items() if isinstance(deal_fields, dict) else [])
            if isinstance(spec, dict) and str(spec.get("type") or "").lower() == "file"
        }
        statuses: dict[str, str] = {}
        for entity in ("DEAL_STAGE", "DEAL_STAGE_0", "DEAL_STAGE_1", "DEAL_STAGE_2", "DEAL_STAGE_3", "DEAL_STAGE_4"):
            body = client.call("crm.status.list", flatten_filter({"filter": {"ENTITY_ID": entity}}))
            for item in body.get("result") or []:
                if isinstance(item, dict) and item.get("STATUS_ID"):
                    statuses[str(item.get("STATUS_ID"))] = str(item.get("NAME") or item.get("STATUS_ID"))

        contact_cache: dict[str, dict[str, Any]] = {}
        deal_cache: dict[str, dict[str, Any]] = {}
        items_cache: dict[str, list[dict[str, Any]]] = {}

        def live_contact(cid: str) -> dict[str, Any]:
            if cid not in contact_cache:
                body = client.call("crm.contact.get", {"id": cid})
                contact_cache[cid] = body.get("result") if isinstance(body.get("result"), dict) else {}
            return contact_cache[cid]

        def live_deal(did: str) -> dict[str, Any]:
            if did not in deal_cache:
                body = client.call("crm.deal.get", {"id": did})
                deal_cache[did] = body.get("result") if isinstance(body.get("result"), dict) else {}
            return deal_cache[did]

        def live_items(did: str) -> list[dict[str, Any]]:
            if did not in items_cache:
                body = client.call("crm.deal.contact.items.get", {"id": did})
                rows = body.get("result") if isinstance(body.get("result"), list) else []
                items_cache[did] = [item for item in rows if isinstance(item, dict)]
            return items_cache[did]

        os_by_bitrix: dict[str, list[CrmContact]] = defaultdict(list)
        for person in contacts.values():
            if person.id not in owners:
                continue
            for cid in bitrix_contact_ids(person):
                os_by_bitrix[cid].append(person)

        phone_index: dict[str, list[CrmContact]] = defaultdict(list)
        email_index: dict[str, list[CrmContact]] = defaultdict(list)
        for person in (contacts[cid] for cid in owners):
            key = phone_key(person.primary_phone)
            if key:
                phone_index[key].append(person)
            if person.primary_email:
                email_index[person.primary_email.lower()].append(person)
        for key, rows in phone_index.items():
            unique = {row.id: row for row in rows if not row.archived_at}
            if len(unique) > 1:
                issue(
                    identity_conflicts,
                    kind="duplicate_active_phone",
                    phone_key=key,
                    people=[{"id": str(row.id), "name": row.display_name} for row in unique.values()],
                )
        for key, rows in email_index.items():
            unique = {row.id: row for row in rows if not row.archived_at}
            if len(unique) > 1:
                issue(
                    identity_conflicts,
                    kind="duplicate_active_email",
                    email=key,
                    people=[{"id": str(row.id), "name": row.display_name} for row in unique.values()],
                )

        for person_id in sorted(owners, key=lambda item: contacts[item].display_name or ""):
            person = contacts[person_id]
            cids = sorted(bitrix_contact_ids(person))
            if len(cids) > 1:
                issue(identity_conflicts, kind="multiple_bitrix_contact_ids", name=person.display_name, ids=cids, contact_id=str(person.id))
            live = live_contact(cids[0]) if len(cids) == 1 else {}
            phones = []
            emails = []
            if live:
                phones = [str(item.get("VALUE") or "") for item in (live.get("PHONE") or []) if isinstance(item, dict) and item.get("VALUE")]
                emails = [str(item.get("VALUE") or "").lower() for item in (live.get("EMAIL") or []) if isinstance(item, dict) and item.get("VALUE")]
                addr = contact_address_parts(live)
                if phones and not person.primary_phone:
                    issue(people_issues, name=person.display_name, field="phone", problem="bitrix_has_phone_os_blank")
                if phones and person.primary_phone and phone_key(phones[0]) != phone_key(person.primary_phone):
                    issue(identity_conflicts, kind="phone_mismatch", name=person.display_name, os=person.primary_phone, bitrix=phones[0])
                if emails and not person.primary_email:
                    issue(people_issues, name=person.display_name, field="email", problem="bitrix_has_email_os_blank")
                if emails and person.primary_email and emails[0] != person.primary_email.lower() and emails[0] not in [str(x).lower() for x in (person.secondary_emails or [])]:
                    issue(identity_conflicts, kind="email_mismatch", name=person.display_name, os=person.primary_email, bitrix=emails[0])
                if (addr.get("address_line1") or addr.get("city")) and not (person.address_line1 or person.city):
                    issue(people_issues, name=person.display_name, field="address", problem="bitrix_has_address_os_blank")
            purchases = list_contact_purchases(db, person.id)
            if not purchases:
                issue(people_issues, name=person.display_name, field="purchases", problem="owner_has_no_purchase_rows")

        for row in agreements:
            person = contacts.get(row.contact_id)
            meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            deal_id = deal_id_for_agreement(row.id, meta)
            card = get_purchase_card(db, row.id, viewer_contact_id=row.contact_id)
            legacy = bool(person and normalize_full_name(person.display_name) in LEGACY_NAMES)
            if not deal_id:
                issue(
                    purchase_issues,
                    name=person.display_name if person else "",
                    agreement_id=str(row.id),
                    project=row.project_group,
                    unit=row.unit_number,
                    problem="no_verified_bitrix_deal",
                    legacy=legacy,
                )
                continue
            deal = live_deal(deal_id)
            if not deal:
                issue(
                    purchase_issues,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="live_deal_empty",
                    agreement_id=str(row.id),
                )
                continue
            os_amount = money(card.amount if card else meta.get("opportunity"))
            live_amount = money(deal.get("OPPORTUNITY"))
            if os_amount is not None and live_amount is not None and os_amount != live_amount:
                issue(
                    purchase_issues,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="amount_mismatch",
                    os=str(os_amount),
                    bitrix=str(live_amount),
                )
            os_ccy = str((card.currency if card else meta.get("currency")) or "").upper()
            live_ccy = str(deal.get("CURRENCY_ID") or "").upper()
            if os_ccy and live_ccy and os_ccy != live_ccy:
                issue(purchase_issues, name=person.display_name if person else "", deal_id=deal_id, problem="currency_mismatch", os=os_ccy, bitrix=live_ccy)
            if row.project_group == "reit" and row.unit_number:
                issue(purchase_issues, name=person.display_name if person else "", deal_id=deal_id, problem="reit_has_invented_unit", unit=row.unit_number)
            if row.project_group != "reit" and not row.unit_number:
                live_unit = scalar(deal.get("UF_CRM_UNIT")) or scalar(meta.get("unit_number"))
                if live_unit:
                    issue(purchase_issues, name=person.display_name if person else "", deal_id=deal_id, problem="missing_unit_present_in_bitrix", bitrix_unit=live_unit)
            items = live_items(deal_id)
            live_owner_ids = [str(item.get("CONTACT_ID") or "") for item in items if item.get("CONTACT_ID")]
            os_owner_ids = {
                str(part.contact_id)
                for part in parts_by_agreement.get(row.id, [])
                if part.contact_id in contacts and is_purchase_owner_contact(contacts[part.contact_id])
            }
            if not os_owner_ids and person and is_purchase_owner_contact(person):
                os_owner_ids.add(str(person.id))
            mapped_live_owners = []
            for cid in live_owner_ids:
                matches = [item for item in os_by_bitrix.get(cid, []) if is_purchase_owner_contact(item)]
                if matches:
                    mapped_live_owners.extend(matches)
                elif cid:
                    live_name = ""
                    live = live_contact(cid)
                    live_name = " ".join(part for part in (live.get("NAME"), live.get("LAST_NAME")) if part).strip()
                    if live_name and not is_agent_advisor_name(live_name):
                        issue(
                            purchase_issues,
                            name=person.display_name if person else "",
                            deal_id=deal_id,
                            problem="live_owner_not_in_os_purchase",
                            bitrix_contact_id=cid,
                            bitrix_name=live_name,
                        )
            for owner in mapped_live_owners:
                if str(owner.id) not in os_owner_ids:
                    issue(
                        purchase_issues,
                        name=person.display_name if person else "",
                        deal_id=deal_id,
                        problem="missing_co_owner_on_os_purchase",
                        owner=owner.display_name,
                    )
            payment, llc, _extra = labeled_from_entity(deal, deal_fields if isinstance(deal_fields, dict) else {})
            if payment and card and not card.payment_fields:
                issue(purchase_issues, name=person.display_name if person else "", deal_id=deal_id, problem="payment_fields_in_bitrix_not_on_card")
            if llc and card and not (card.llc_fields or card.llc_name):
                issue(purchase_issues, name=person.display_name if person else "", deal_id=deal_id, problem="llc_fields_in_bitrix_not_on_card")
            for part in parts_by_agreement.get(row.id, []):
                if part.ownership_pct is None:
                    continue
                # only flag invented 100% on multi-owner live deals
                if len(mapped_live_owners) > 1 and part.ownership_pct == Decimal("100.00"):
                    issue(
                        purchase_issues,
                        name=person.display_name if person else "",
                        deal_id=deal_id,
                        problem="unverified_100_percent_on_joint_purchase",
                        owner=contacts[part.contact_id].display_name if part.contact_id in contacts else str(part.contact_id),
                    )

            uf_ids: list[str] = []
            for key in file_fields:
                uf_ids.extend(file_ids_from(deal.get(key)))
            uf_ids = list(dict.fromkeys(uf_ids))
            card_file_ids = {str(doc.bitrix_file_id) for doc in (card.documents if card else []) if doc.bitrix_file_id}
            missing_uf = [fid for fid in uf_ids if fid not in card_file_ids]
            if missing_uf:
                issue(
                    document_gaps,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="deal_uf_files_missing_from_os",
                    file_ids=missing_uf,
                    field_count=len(uf_ids),
                )
            checksums: dict[str, list[str]] = defaultdict(list)
            for doc in card.documents if card else []:
                document = db.get(Document, doc.id)
                if document and document.checksum:
                    checksums[document.checksum].append(doc.original_file_name or doc.title)
            for digest, names in checksums.items():
                if len(names) > 1:
                    issue(
                        document_gaps,
                        name=person.display_name if person else "",
                        deal_id=deal_id,
                        problem="duplicate_visible_file_bytes",
                        files=names,
                        sha256=digest,
                    )
            names = [((doc.original_file_name or doc.title or "").casefold()) for doc in (card.documents if card else [])]
            dup_names = [name for name, count in Counter(names).items() if name and count > 1]
            if dup_names:
                issue(
                    document_gaps,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="duplicate_visible_filename",
                    files=dup_names,
                )

            history_ids = [entry.id for entry in (card.history if card else [])]
            if len(history_ids) != len(set(history_ids)):
                issue(history_gaps, name=person.display_name if person else "", deal_id=deal_id, problem="duplicate_history_entry_ids")
            titles = [
                str(getattr(entry, "title", "") or "") + "|" + str(getattr(entry, "created_at", "") or "")
                for entry in (card.history if card else [])
            ]
            dup_hist = [title for title, count in Counter(titles).items() if count > 1]
            if dup_hist:
                issue(
                    history_gaps,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="duplicate_history_title_timestamp",
                    samples=dup_hist[:5],
                )

            live_acts: list[dict[str, Any]] = []
            start = 0
            while True:
                payload = flatten_filter({"filter": {"OWNER_TYPE_ID": "2", "OWNER_ID": deal_id}})
                payload["select[]"] = ["ID", "SUBJECT", "TYPE_ID", "FILES"]
                if start:
                    payload["start"] = start
                acts = client.call("crm.activity.list", payload)
                chunk = acts.get("result") if isinstance(acts.get("result"), list) else []
                live_acts.extend(item for item in chunk if isinstance(item, dict))
                nxt = acts.get("next")
                if nxt in (None, "") or not chunk:
                    break
                start = int(nxt)
            live_act_files: list[str] = []
            for act in live_acts:
                if not isinstance(act, dict):
                    continue
                subject = str(act.get("SUBJECT") or "")
                files = file_ids_from(act.get("FILES"))
                if files and DOC_HINT.search(subject):
                    live_act_files.extend(files)
            missing_act = [fid for fid in dict.fromkeys(live_act_files) if fid not in card_file_ids]
            if missing_act:
                issue(
                    document_gaps,
                    name=person.display_name if person else "",
                    deal_id=deal_id,
                    problem="deal_activity_document_files_missing_from_os",
                    file_ids=missing_act,
                )

        def purchases_of(cid: UUID) -> list[Any]:
            return list_contact_purchases(db, cid)

        musa = contacts.get(MUSA_ID)
        special["musa"] = {
            "present": musa is not None,
            "name": musa.display_name if musa else None,
            "type": musa.contact_type.value if musa and hasattr(musa.contact_type, "value") else None,
            "is_purchase_owner": is_purchase_owner_contact(musa) if musa else None,
            "advisor_name": is_agent_advisor_name(musa.display_name) if musa else None,
            "in_agreement_owners": MUSA_ID in owners,
            "purchases": len(purchases_of(MUSA_ID)) if musa else 0,
        }
        if musa is None:
            issue(people_issues, name="Musa", problem="musa_contact_missing")
        elif MUSA_ID in owners or special["musa"]["is_purchase_owner"] or special["musa"]["purchases"]:
            issue(people_issues, name=musa.display_name, problem="musa_still_treated_as_buyer")

        lale = contacts.get(LALE_ID)
        lale_purchases = purchases_of(LALE_ID)
        special["lale"] = {
            "name": lale.display_name if lale else None,
            "purchase_count": len(lale_purchases),
            "rows": [
                {
                    "project": item.project_group,
                    "unit": item.unit_number,
                    "deal": item.bitrix_deal_id,
                    "amount": item.amount_label,
                }
                for item in lale_purchases
            ],
        }
        groups = {item.project_group: item for item in lale_purchases}
        if len(lale_purchases) != 2:
            issue(purchase_issues, name="Lale Şenyol", problem="expected_two_investments", count=len(lale_purchases))
        if groups.get("1812_h_pl") is None or groups["1812_h_pl"].unit_number != "B08" or groups["1812_h_pl"].bitrix_deal_id != "116":
            issue(purchase_issues, name="Lale Şenyol", problem="1812_b08_incorrect", row=special["lale"]["rows"])
        if groups.get("reit") is None or groups["reit"].unit_number or groups["reit"].bitrix_deal_id != "206":
            issue(purchase_issues, name="Lale Şenyol", problem="reit_incorrect", row=special["lale"]["rows"])

        nedim_purchases = purchases_of(NEDIM_CANONICAL_ID)
        izzet_purchases = purchases_of(IZZET_CANONICAL_ID)
        special["nedim_izzet"] = {
            "nedim_purchases": [
                {"project": item.project_group, "unit": item.unit_number, "deal": item.bitrix_deal_id, "owners": item.owners_label}
                for item in nedim_purchases
            ],
            "izzet_purchases": [
                {"project": item.project_group, "unit": item.unit_number, "deal": item.bitrix_deal_id, "owners": item.owners_label}
                for item in izzet_purchases
            ],
        }
        card_720 = get_purchase_card(db, AGREEMENT_720, viewer_contact_id=NEDIM_CANONICAL_ID)
        owner_ids_720 = {str(item.contact_id) for item in (card_720.participants if card_720 else [])}
        pcts = {str(item.contact_id): item.ownership_pct for item in (card_720.participants if card_720 else [])}
        if str(NEDIM_CANONICAL_ID) not in owner_ids_720 or str(IZZET_CANONICAL_ID) not in owner_ids_720:
            issue(purchase_issues, name="Nedim Kondu", problem="uniloft_403_missing_shared_owners", owners=list(owner_ids_720))
        elif {pcts.get(str(NEDIM_CANONICAL_ID)), pcts.get(str(IZZET_CANONICAL_ID))} != {"50.00", "50.00"} and {
            str(pcts.get(str(NEDIM_CANONICAL_ID)) or "").replace(".00", ""),
            str(pcts.get(str(IZZET_CANONICAL_ID)) or "").replace(".00", ""),
        } != {"50", "50"}:
            issue(
                purchase_issues,
                name="Nedim Kondu",
                problem="uniloft_403_ownership_not_50_50",
                pcts=pcts,
            )

        def shared_ok(label: str, ids: list[UUID], deal_id: str) -> None:
            names = []
            found = None
            for cid in ids:
                person = contacts.get(cid)
                names.append(person.display_name if person else str(cid))
                rows = [item for item in purchases_of(cid) if item.bitrix_deal_id == deal_id]
                if not rows:
                    issue(purchase_issues, name=person.display_name if person else label, problem="missing_shared_deal", deal_id=deal_id)
                else:
                    found = rows[0]
            if found:
                owner_ids = {str(item.contact_id) for item in found.participants}
                missing = [str(cid) for cid in ids if str(cid) not in owner_ids]
                if missing:
                    issue(purchase_issues, name=label, problem="shared_purchase_missing_participant", deal_id=deal_id, missing=missing)

        shared_ok("Müjgan/Alp/Ece", [MUJGAN_ID, ALP_ID, ECE_ID], "196")
        shared_ok("Ozan/Burcu", [OZAN_ID, BURCU_ID], "212")
        shared_ok("Yeşim/Murat Zengin", [YESIM_ID, MURAT_ID], "414")

        checks = max(1, len(owners) + len(agreements))
        real_issues = people_issues + purchase_issues + document_gaps + history_gaps + identity_conflicts
        completeness = round(100 * (1 - (len(real_issues) / checks)), 1)
        report = {
            "bitrix_modified": False,
            "agreement_people_checked": len(owners),
            "purchases_checked": len(agreements),
            "people_issues": people_issues,
            "purchase_issues": purchase_issues,
            "document_gaps": document_gaps,
            "history_gaps": history_gaps,
            "identity_conflicts": identity_conflicts,
            "special_cases": special,
            "real_open_issues": real_issues,
            "real_open_issue_count": len(real_issues),
            "final_completeness_percentage": completeness,
            "bitrix_calls": client.call_count,
            "backup_path": "data/Bitrix_Export/2026-09-final/AGREEMENTS_PHASE_CLOSEOUT/backups/investhome-agreements-phase-closeout-20260919.dump",
            "final_report_path": "data/Bitrix_Export/2026-09-final/AGREEMENTS_PHASE_CLOSEOUT/INDEX.md",
        }
    finally:
        db.close()
    (OUT / "reports" / "CLOSEOUT.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(
        json.dumps(
            {
                "people": report["agreement_people_checked"],
                "purchases": report["purchases_checked"],
                "issues": report["real_open_issue_count"],
                "completeness": report["final_completeness_percentage"],
                "people_issues": len(people_issues),
                "purchase_issues": len(purchase_issues),
                "document_gaps": len(document_gaps),
                "history_gaps": len(history_gaps),
                "identity_conflicts": len(identity_conflicts),
                "calls": client.call_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
