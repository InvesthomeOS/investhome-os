from decimal import Decimal
from uuid import UUID

from investhome_api.services.crm.agreement_service import format_money
from investhome_api.services.crm.nedim_purchase_card import (
    AGREEMENT_198,
    AGREEMENT_656,
    AGREEMENT_720,
    DEAL_198,
    DEAL_656,
    DEAL_720,
    DEAL_UF_FILES,
    activity_deal_id,
    is_deal_owned_activity,
    is_nedim_pilot_contact,
    is_nedim_purchase_agreement,
    is_person_owned_activity,
)


def test_nedim_canonical_is_pilot() -> None:
    assert is_nedim_pilot_contact(UUID("811c6aed-5f58-4c89-a9b1-0eebed64b9cf"))
    assert is_nedim_pilot_contact(UUID("ee093070-b3a4-4fb3-b3ca-3aa92379a187"))
    assert not is_nedim_pilot_contact(UUID("00000000-0000-0000-0000-000000000001"))


def test_purchase_agreements_are_deal_scoped() -> None:
    assert is_nedim_purchase_agreement(AGREEMENT_198)
    assert is_nedim_purchase_agreement(AGREEMENT_656)
    assert is_nedim_purchase_agreement(AGREEMENT_720)
    assert not is_nedim_purchase_agreement(UUID("00000000-0000-0000-0000-000000000002"))


def test_deal_owned_history_stays_on_purchase() -> None:
    deal_720 = {"bitrix_history": {"bitrix_entity_type": "deal", "bitrix_entity_id": DEAL_720}}
    contact_wa = {"bitrix_history": {"bitrix_entity_type": "contact", "bitrix_entity_id": "588"}}
    lead_note = {"bitrix_history": {"bitrix_entity_type": "lead", "bitrix_entity_id": "12512"}}
    assert activity_deal_id(deal_720) == DEAL_720
    assert is_deal_owned_activity(deal_720, DEAL_720)
    assert not is_deal_owned_activity(deal_720, DEAL_198)
    assert is_person_owned_activity(contact_wa)
    assert is_person_owned_activity(lead_note)
    assert not is_person_owned_activity(deal_720)


def test_uniloft_403_whatsapp_is_person_owned() -> None:
    metadata = {
        "bitrix_history": {
            "bitrix_entity_type": "contact",
            "bitrix_entity_id": "588",
            "kind": "whatsapp_message",
        }
    }
    assert is_person_owned_activity(metadata)
    assert not is_deal_owned_activity(metadata, DEAL_720)


def test_whatsapp_kind_detection() -> None:
    from investhome_api.services.crm.nedim_purchase_card import is_whatsapp_activity

    assert is_whatsapp_activity({"bitrix_history": {"kind": "whatsapp_message"}}, "note")
    assert is_whatsapp_activity({"bitrix_history": {"kind": "whatsapp_session"}})
    assert is_whatsapp_activity({"bitrix_history": {"open_channel_summary": True}})
    assert is_whatsapp_activity({}, "whatsapp")
    assert not is_whatsapp_activity({"bitrix_history": {"kind": "comment"}}, "comment")


def test_uf_file_ids_are_deal_explicit() -> None:
    assert DEAL_UF_FILES[DEAL_198] == ["58484", "58488", "58490"]
    assert "92370" in DEAL_UF_FILES[DEAL_656]
    assert "96546" in DEAL_UF_FILES[DEAL_720]


def test_money_format() -> None:
    assert format_money("470000.00", "USD") == "$470,000 USD"
    assert format_money("800250.00", "USD") == "$800,250 USD"
    assert format_money(str(Decimal("330757.00")), "USD") == "$330,757 USD"
