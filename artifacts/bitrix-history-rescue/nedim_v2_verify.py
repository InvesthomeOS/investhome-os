import json

from investhome_api.db.session import SessionLocal
from investhome_api.models.crm_contact import CrmContact
from investhome_api.services.crm.agreement_service import get_purchase_card, list_contact_purchases
from investhome_api.services.crm.contact_service import get_contact_or_none, get_contact_timeline, serialize_contact_detail
from investhome_api.services.crm.nedim_purchase_card import AGREEMENT_198, AGREEMENT_656, AGREEMENT_720, NEDIM_CANONICAL_ID
from investhome_api.models.user_auth import User
from sqlalchemy import select
from uuid import UUID

IZZET_ID = UUID("339559ed-0d11-4e7c-a021-a07b388a817b")

db = SessionLocal()
try:
    user = db.scalar(select(User).order_by(User.created_at.asc()))
    contact = get_contact_or_none(db, NEDIM_CANONICAL_ID)
    detail = serialize_contact_detail(db, contact, user=user)
    timeline = get_contact_timeline(db, NEDIM_CANONICAL_ID, user)
    izzet = db.get(CrmContact, IZZET_ID)
    cards = {
        "198": get_purchase_card(db, AGREEMENT_198),
        "656": get_purchase_card(db, AGREEMENT_656),
        "720": get_purchase_card(db, AGREEMENT_720),
    }
    report = {
        "nedim": {
            "id": str(contact.id),
            "name": contact.display_name,
            "phone": contact.primary_phone,
            "email": contact.primary_email,
            "purchases": [
                {
                    "deal": p.bitrix_deal_id,
                    "label": p.project_label,
                    "unit": p.unit_number,
                    "amount": p.amount_label,
                    "owners": p.owners_label,
                    "participants": [
                        {"name": x.display_name, "pct": x.ownership_pct, "primary": x.is_primary}
                        for x in p.participants
                    ],
                }
                for p in (detail.purchases or [])
            ],
            "person_history_count": len(timeline),
        },
        "izzet": {
            "id": str(izzet.id) if izzet else None,
            "name": izzet.display_name if izzet else None,
            "phone": izzet.primary_phone if izzet else None,
            "email": izzet.primary_email if izzet else None,
            "source": izzet.source if izzet else None,
        },
        "purchases": {
            deal: {
                "agreement_id": str(card.agreement_id),
                "amount": card.amount_label,
                "unit": card.unit_number,
                "project": card.project_label,
                "stage": card.stage,
                "owners": [
                    {"name": p.display_name, "pct": p.ownership_pct, "primary": p.is_primary}
                    for p in card.participants
                ],
                "history_count": card.history_count,
                "document_count": card.document_count,
                "uf_file_ids": [d.bitrix_file_id for d in card.documents if d.bitrix_file_id],
            }
            for deal, card in cards.items()
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
finally:
    db.close()
