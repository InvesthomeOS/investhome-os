from investhome_api.services.crm.nedim_purchase_card import (
    AGREEMENT_198,
    is_nedim_purchase_agreement,
    is_person_owned_activity,
)


def test_project_context_is_not_the_purchase_model() -> None:
    assert is_nedim_purchase_agreement(AGREEMENT_198)
    assert is_person_owned_activity({"bitrix_history": {"bitrix_entity_type": "contact", "bitrix_entity_id": "588"}})
