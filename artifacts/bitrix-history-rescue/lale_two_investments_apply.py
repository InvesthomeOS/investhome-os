"""Apply verified live Bitrix deal 116 to Lale 1812 B08. Bitrix read-only."""
from __future__ import annotations

import json
import os
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreement, CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.models.document import Document, DocumentLink
from investhome_api.services.crm.agreement_service import get_purchase_card
from investhome_api.services.crm.nedim_purchase_card import deal_id_for_agreement

from agreement_customers_final_model import (
    BitrixClient,
    field_label,
    fill_empty,
    labeled_from_entity,
    link_deal_documents,
    merge_live,
    scalar,
    webhook_base,
)
from lale_two_investments_search3 import NestedClient, list_all

OUT = Path("/tmp/LALE_TWO_INVESTMENTS")
CANONICAL = UUID("0f966583-13c5-4ca4-a90b-2763383973ae")
B08_ID = UUID("fadfc360-2900-4673-80d0-ffdc88b6763a")
REIT_ID = UUID("03e70fe7-0a49-4cfe-99ed-0a618fe184e7")
DEAL_B08 = "116"
DEAL_REIT = "206"
LEAD_B08 = "6178"
LEAD_REIT = "16400"
CONTACT_ID = "362"
B08_FILE_IDS = {"42558", "42562", "42560", "42798", "42800", "42802", "42804", "42806", "42808"}


def date_only(value) -> str | None:
    text = scalar(value)
    return text[:10] if text else None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "reports").mkdir(parents=True, exist_ok=True)
    client = NestedClient(webhook_base(os.environ.get("BITRIX_ADMIN_WEBHOOK_URL") or ""))
    db = SessionLocal()
    report: dict = {}
    try:
        person = db.get(CrmContact, CANONICAL)
        b08 = db.get(CrmAgreement, B08_ID)
        reit = db.get(CrmAgreement, REIT_ID)
        if person is None or b08 is None or reit is None:
            raise RuntimeError("canonical Lale or agreements missing")

        deal = client.call("crm.deal.get", {"id": DEAL_B08}).get("result") or {}
        reit_deal = client.call("crm.deal.get", {"id": DEAL_REIT}).get("result") or {}
        items = client.call("crm.deal.contact.items.get", {"id": DEAL_B08}).get("result") or []
        fields = client.call("crm.deal.fields", {}).get("result") or {}
        statuses = {}
        for entity in ("DEAL_STAGE", "DEAL_STAGE_0", "DEAL_STAGE_1", "DEAL_STAGE_2", "DEAL_STAGE_3", "DEAL_STAGE_4"):
            body = client.call("crm.status.list", {"filter": {"ENTITY_ID": entity}})
            for item in body.get("result") or []:
                if isinstance(item, dict) and item.get("STATUS_ID"):
                    statuses[str(item.get("STATUS_ID"))] = str(item.get("NAME") or item.get("STATUS_ID"))
        users = {}
        start = 0
        while True:
            body = client.call("user.get", {"start": start} if start else {})
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

        acts = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 2, "OWNER_ID": int(DEAL_B08)}, "order": {"ID": "DESC"}})
        reit_acts = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 2, "OWNER_ID": int(DEAL_REIT)}, "order": {"ID": "DESC"}})
        contact_acts = list_all(client, "crm.activity.list", {"filter": {"OWNER_TYPE_ID": 3, "OWNER_ID": int(CONTACT_ID)}, "order": {"ID": "DESC"}})

        stage_id = str(deal.get("STAGE_ID") or "")
        stage_label = statuses.get(stage_id) or stage_id
        assigned = users.get(str(deal.get("ASSIGNED_BY_ID") or ""))
        payment, llc, extra = labeled_from_entity(deal, fields if isinstance(fields, dict) else {})
        comments = scalar(deal.get("COMMENTS"))
        llc_name = scalar(deal.get("TITLE"))
        if "%100" in str(deal.get("UF_CRM_1690532963438") or ""):
            extra = extra + [{"label": "Sahiplik", "value": "%100"}]

        meta = dict(b08.metadata_json or {}) if isinstance(b08.metadata_json, dict) else {}
        live = dict(meta.get("bitrix_live") or {}) if isinstance(meta.get("bitrix_live"), dict) else {}
        meta["bitrix_deal_id"] = DEAL_B08
        meta["opportunity"] = "232687.00"
        meta["currency"] = "USD"
        meta["begin_date"] = date_only(deal.get("BEGINDATE"))
        meta["close_date"] = date_only(deal.get("CLOSEDATE"))
        meta["stage_label"] = stage_label
        meta["purchase_card_verified"] = True
        live.update(
            {
                "bitrix_deal_id": DEAL_B08,
                "lead_id": LEAD_B08,
                "title": deal.get("TITLE"),
                "stage_id": stage_id,
                "stage_label": stage_label,
                "opportunity": "232687.00",
                "currency": "USD",
                "begin_date": date_only(deal.get("BEGINDATE")),
                "close_date": date_only(deal.get("CLOSEDATE")),
                "assigned_name": assigned,
                "comments": comments,
                "llc_name": llc_name,
                "payment_fields": payment,
                "llc_fields": llc or [{"label": "Şirket / LLC", "value": llc_name}] if llc_name else llc,
                "extra_fields": extra,
                "purchase_card_verified": True,
                "bitrix_title_note": "Bitrix başlığı 1820 H PL B008; OS kanonik proje 1812 H Place birim B08.",
            }
        )
        meta["bitrix_live"] = live
        b08.metadata_json = meta
        b08.unit_number = "B08"
        if b08.agreement_date is None and meta.get("begin_date"):
            b08.agreement_date = date.fromisoformat(meta["begin_date"])
        flag_modified(b08, "metadata_json")

        existing = db.scalar(
            select(CrmAgreementParticipant).where(
                CrmAgreementParticipant.agreement_id == b08.id,
                CrmAgreementParticipant.contact_id == person.id,
            )
        )
        if existing is None:
            db.add(
                CrmAgreementParticipant(
                    id=uuid4(),
                    agreement_id=b08.id,
                    contact_id=person.id,
                    role="owner",
                    ownership_pct=Decimal("100.00"),
                    is_primary=True,
                    source="bitrix_live",
                    metadata_json={"bitrix_deal_id": DEAL_B08, "bitrix_contact_id": CONTACT_ID},
                )
            )
        else:
            existing.is_primary = True
            if existing.ownership_pct is None:
                existing.ownership_pct = Decimal("100.00")

        # REIT: confirm, never invent unit
        reit.unit_number = None
        rmeta = dict(reit.metadata_json or {}) if isinstance(reit.metadata_json, dict) else {}
        rlive = dict(rmeta.get("bitrix_live") or {}) if isinstance(rmeta.get("bitrix_live"), dict) else {}
        rmeta["bitrix_deal_id"] = DEAL_REIT
        rmeta["opportunity"] = str(reit_deal.get("OPPORTUNITY") or rmeta.get("opportunity") or "100000.00")
        rmeta["currency"] = str(reit_deal.get("CURRENCY_ID") or "USD")
        rmeta["begin_date"] = date_only(reit_deal.get("BEGINDATE")) or rmeta.get("begin_date")
        rmeta["close_date"] = date_only(reit_deal.get("CLOSEDATE")) or rmeta.get("close_date")
        r_stage = str(reit_deal.get("STAGE_ID") or "")
        rmeta["stage_label"] = statuses.get(r_stage) or rlive.get("stage_label") or "Kazanıldı"
        rmeta["purchase_card_verified"] = True
        rlive.update(
            {
                "bitrix_deal_id": DEAL_REIT,
                "lead_id": LEAD_REIT,
                "title": reit_deal.get("TITLE"),
                "stage_id": r_stage,
                "stage_label": rmeta["stage_label"],
                "opportunity": rmeta["opportunity"],
                "currency": rmeta["currency"],
                "begin_date": rmeta.get("begin_date"),
                "close_date": rmeta.get("close_date"),
                "assigned_name": users.get(str(reit_deal.get("ASSIGNED_BY_ID") or "")),
                "comments": scalar(reit_deal.get("COMMENTS")),
            }
        )
        rmeta["bitrix_live"] = rlive
        reit.metadata_json = rmeta
        if not reit.investment_amount:
            reit.investment_amount = "100000.00"
        flag_modified(reit, "metadata_json")

        if fill_empty(person, "city", "İzmir"):
            report["city_added"] = True
        live_emails = ["lale.senyol@cakagrup.com.tr"]
        current = [str(item).lower() for item in (person.secondary_emails or [])]
        extra_emails = [item for item in live_emails if item != (person.primary_email or "").lower() and item not in current]
        if extra_emails:
            person.secondary_emails = (person.secondary_emails or []) + extra_emails
            report["secondary_email_added"] = extra_emails

        linked = link_deal_documents(db, b08.id, DEAL_B08)
        linked += link_deal_documents(db, reit.id, DEAL_REIT)
        existing_docs = {
            str(item)
            for item in db.scalars(
                select(DocumentLink.document_id).where(
                    DocumentLink.entity_type == "crm_agreement",
                    DocumentLink.entity_id == b08.id,
                )
            ).all()
        }
        file_linked = 0
        for document in db.scalars(select(Document).where(Document.notes.is_not(None))).all():
            notes = document.notes if isinstance(document.notes, dict) else {}
            fid = str(notes.get("bitrix_file_id") or notes.get("file_id") or "")
            if fid not in B08_FILE_IDS:
                continue
            if str(document.id) in existing_docs:
                continue
            db.add(
                DocumentLink(
                    document_id=document.id,
                    entity_type="crm_agreement",
                    entity_id=b08.id,
                    relationship_type="bitrix_deal_file",
                )
            )
            existing_docs.add(str(document.id))
            file_linked += 1

        db.commit()

        b08_card = get_purchase_card(db, b08.id, viewer_contact_id=person.id)
        reit_card = get_purchase_card(db, reit.id, viewer_contact_id=person.id)
        report.update(
            {
                "canonical_person": {
                    "id": str(person.id),
                    "name": person.display_name,
                    "email": person.primary_email,
                    "phone": person.primary_phone,
                    "bitrix_contact_id": CONTACT_ID,
                    "bitrix_leads": [LEAD_B08, LEAD_REIT],
                    "secondary_emails": person.secondary_emails,
                    "city": person.city,
                },
                "b08": {
                    "agreement_id": str(b08.id),
                    "verified_live_deal": True,
                    "deal_id": DEAL_B08,
                    "lead_id": LEAD_B08,
                    "title": deal.get("TITLE"),
                    "os_project": "1812_h_pl",
                    "os_unit": "B08",
                    "amount": "232687.00",
                    "currency": "USD",
                    "stage_id": stage_id,
                    "stage_label": stage_label,
                    "begin_date": meta.get("begin_date"),
                    "close_date": meta.get("close_date"),
                    "owners": ["Lale Şenyol"],
                    "ownership": "100%",
                    "comments": comments,
                    "assigned": assigned,
                    "llc_name": llc_name,
                    "payment_fields": payment,
                    "deal_items": items,
                    "live_activities": [
                        {"id": a.get("ID"), "type": a.get("TYPE_ID"), "subject": a.get("SUBJECT")} for a in acts[:20]
                    ],
                    "live_activity_count": len(acts),
                    "uf_file_ids": sorted(B08_FILE_IDS),
                    "documents_linked": linked + file_linked,
                    "card_documents": b08_card.document_count if b08_card else 0,
                    "card_history": b08_card.history_count if b08_card else 0,
                    "card_whatsapp": sum(1 for item in (b08_card.history if b08_card else []) if item.activity_type == "whatsapp"),
                },
                "reit": {
                    "agreement_id": str(reit.id),
                    "verified_live_deal": True,
                    "deal_id": DEAL_REIT,
                    "lead_id": LEAD_REIT,
                    "title": reit_deal.get("TITLE"),
                    "amount": rmeta.get("opportunity"),
                    "currency": rmeta.get("currency"),
                    "unit": reit.unit_number,
                    "stage_label": rmeta.get("stage_label"),
                    "begin_date": rmeta.get("begin_date"),
                    "close_date": rmeta.get("close_date"),
                    "assigned": users.get(str(reit_deal.get("ASSIGNED_BY_ID") or "")),
                    "live_activity_count": len(reit_acts),
                    "card_documents": reit_card.document_count if reit_card else 0,
                    "card_history": reit_card.history_count if reit_card else 0,
                    "card_whatsapp": sum(1 for item in (reit_card.history if reit_card else []) if item.activity_type == "whatsapp"),
                },
                "person_page": {
                    "section": "YATIRIMLARI / SATIN ALDIKLARI",
                    "records": ["1812 H Place · B08", "REIT · 100,000 USD"],
                    "duplicate_lale_archived": "160f3e9c-d22f-4744-b174-7ae95d6c9c6e",
                },
                "bitrix_calls": client.call_count,
            }
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    (OUT / "reports" / "LALE.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({
        "deal_116": report.get("b08", {}).get("deal_id"),
        "stage": report.get("b08", {}).get("stage_label"),
        "b08_docs": report.get("b08", {}).get("card_documents"),
        "b08_hist": report.get("b08", {}).get("card_history"),
        "reit_docs": report.get("reit", {}).get("card_documents"),
        "reit_hist": report.get("reit", {}).get("card_history"),
        "calls": report.get("bitrix_calls"),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
