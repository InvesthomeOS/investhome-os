"""Verify Nedim/Izzet person+purchase payloads. Read-only."""
from __future__ import annotations

from sqlalchemy import select

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_agreement import CrmAgreementParticipant
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.agreement_service import get_purchase_card, list_contact_purchases
from investhome_api.services.crm.contact_service import serialize_contact_detail
from investhome_api.services.crm.nedim_purchase_card import (
    AGREEMENT_198,
    AGREEMENT_656,
    AGREEMENT_720,
    IZZET_CANONICAL_ID,
    NEDIM_CANONICAL_ID,
)


def main() -> None:
    db = SessionLocal()
    try:
        nedim_row = db.get(CrmContact, NEDIM_CANONICAL_ID)
        izzet_row = db.get(CrmContact, IZZET_CANONICAL_ID)
        nedim = serialize_contact_detail(db, nedim_row)
        izzet = serialize_contact_detail(db, izzet_row)
        print(
            "NEDIM",
            nedim.display_name,
            nedim.primary_phone,
            nedim.primary_email,
            nedim.address_line1,
            nedim.job_title,
            nedim.bitrix_source_channel,
            nedim.bitrix_responsible,
        )
        print("NEDIM profile", [(item.label, item.value[:80]) for item in nedim.profile_fields])
        print(
            "NEDIM purchases",
            [
                (
                    item.project_label,
                    item.unit_number,
                    item.amount_label,
                    item.bitrix_deal_id,
                    [(part.display_name, part.ownership_pct) for part in item.participants],
                )
                for item in nedim.purchases
            ],
        )
        print(
            "IZZET",
            izzet.display_name,
            izzet.primary_phone,
            izzet.primary_email,
            izzet.address_line1,
            izzet.bitrix_source_channel,
            izzet.bitrix_responsible,
        )
        print(
            "IZZET purchases",
            [
                (item.project_label, item.unit_number, item.amount_label, str(item.agreement_id), item.bitrix_deal_id)
                for item in izzet.purchases
            ],
        )
        for agreement_id, viewer in (
            (AGREEMENT_198, NEDIM_CANONICAL_ID),
            (AGREEMENT_656, NEDIM_CANONICAL_ID),
            (AGREEMENT_720, NEDIM_CANONICAL_ID),
            (AGREEMENT_720, IZZET_CANONICAL_ID),
        ):
            card = get_purchase_card(db, agreement_id, viewer_contact_id=viewer)
            assert card is not None
            print(
                "CARD",
                card.bitrix_deal_id,
                "viewer",
                str(viewer)[:8],
                card.project_label,
                card.unit_number,
                card.amount_label,
                card.stage,
                "docs",
                card.document_count,
                "hist",
                card.history_count,
                "llc",
                card.llc_name,
                "pay",
                [item.label for item in card.payment_fields],
                "owners",
                [(part.display_name, part.ownership_pct, part.address) for part in card.participants],
                "related",
                len(card.related_purchases),
            )
            print("  files", [doc.bitrix_file_id for doc in card.documents])
        rows = db.scalars(select(CrmAgreementParticipant).where(CrmAgreementParticipant.agreement_id == AGREEMENT_720)).all()
        print("720 participants", [(str(row.contact_id), row.is_primary, str(row.ownership_pct)) for row in rows])
        print("counts", len(list_contact_purchases(db, NEDIM_CANONICAL_ID)), len(list_contact_purchases(db, IZZET_CANONICAL_ID)))
    finally:
        db.close()


if __name__ == "__main__":
    main()
