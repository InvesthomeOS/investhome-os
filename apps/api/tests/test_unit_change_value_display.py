from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from investhome_api.schemas.crm_contacts import CrmPurchaseSummary
from investhome_api.services.crm.agreement_service import (
    _apply_unit_change_value_display,
    _coalesce_purchase_amount,
    _merge_labeled_value_fields,
    _unit_change_source_rows,
)
from investhome_api.schemas.crm_agreements import CrmLabeledValue


def _row(**kwargs):
    values = {
        "id": uuid4(),
        "contact_id": uuid4(),
        "project_group": "1812_h_pl",
        "source": "bitrix",
        "unit_number": None,
        "agreement_date": None,
        "created_at": None,
        "investment_amount": None,
        "metadata_json": {},
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


def _summary(**kwargs):
    payload = {
        "agreement_id": uuid4(),
        "bitrix_deal_id": None,
        "project_group": "1812_h_pl",
        "project_label": "1812 H Pl",
        "unit_number": "305",
        "amount": None,
        "currency": None,
        "amount_label": None,
        "stage": None,
        "begin_date": None,
        "close_date": None,
        "owners_label": None,
        "participants": [],
        "opens_purchase_card": True,
    }
    payload.update(kwargs)
    return CrmPurchaseSummary(**payload)


def test_empty_current_uses_original_b08_values():
    contact_id = uuid4()
    current_id = uuid4()
    historical_id = uuid4()
    current = _row(
        id=current_id,
        contact_id=contact_id,
        unit_number="305",
        source="manual_business_confirmation",
        metadata_json={
            "previous_units": ["B08"],
            "original_unit": "B08",
            "final_unit": "305",
        },
    )
    historical = _row(
        id=historical_id,
        contact_id=contact_id,
        unit_number="B08",
        source="bitrix_unit_change_history",
        agreement_date=date(2024, 2, 13),
        metadata_json={
            "historical_unit_change": True,
            "opportunity": "232687.00",
            "currency": "USD",
            "begin_date": "2024-02-13",
            "close_date": "2024-12-31",
            "final_unit": "305",
            "replaced_by_agreement_id": str(current_id),
        },
    )
    summary = _summary(agreement_id=current_id, unit_number="305")
    sources = _apply_unit_change_value_display(summary, current, [current, historical])
    assert [row.unit_number for row in sources] == ["B08"]
    assert summary.amount == "232687.00"
    assert summary.amount_label == "$232,687 USD"
    assert summary.begin_date == "2024-02-13"
    assert summary.close_date == "2024-12-31"


def test_filled_current_is_not_overwritten():
    contact_id = uuid4()
    current_id = uuid4()
    historical_id = uuid4()
    current = _row(
        id=current_id,
        contact_id=contact_id,
        unit_number="307",
        metadata_json={
            "previous_agreement_id": str(historical_id),
            "original_unit": "B07",
            "final_unit": "307",
            "opportunity": "244719.00",
            "currency": "USD",
            "begin_date": "2023-10-31",
            "close_date": "2023-11-07",
        },
    )
    historical = _row(
        id=historical_id,
        contact_id=contact_id,
        unit_number="B07",
        source="bitrix_unit_change_history",
        metadata_json={
            "historical_unit_change": True,
            "opportunity": "111.00",
            "currency": "USD",
            "begin_date": "2000-01-01",
            "close_date": "2000-01-02",
            "final_unit": "307",
            "replaced_by_agreement_id": str(current_id),
        },
    )
    summary = _summary(
        agreement_id=current_id,
        unit_number="307",
        amount="244719.00",
        currency="USD",
        amount_label="$244,719 USD",
        begin_date="2023-10-31",
        close_date="2023-11-07",
    )
    _apply_unit_change_value_display(summary, current, [current, historical])
    assert summary.amount == "244719.00"
    assert summary.begin_date == "2023-10-31"
    assert summary.close_date == "2023-11-07"


def test_distinct_historical_amounts_are_both_shown():
    first = _row(
        unit_number="105",
        metadata_json={"opportunity": "224454.00", "currency": "USD", "historical_unit_change": True},
    )
    second = _row(
        unit_number="305",
        metadata_json={"opportunity": "227500.00", "currency": "USD", "historical_unit_change": True},
    )
    amount, currency, label = _coalesce_purchase_amount(None, None, [first, second])
    assert amount == "224454.00 + 227500.00"
    assert currency == "USD"
    assert label == "$224,454 USD + $227,500 USD"


def test_unit_identifying_extras_are_not_copied():
    current = [CrmLabeledValue(label="Önceki daire", value="B08 → 305")]
    source = [
        CrmLabeledValue(label="Daire No", value="B08"),
        CrmLabeledValue(label="Ödeme Şekli", value="%25 Peşinat"),
        CrmLabeledValue(label="Kira Tutarı", value="909 USD"),
    ]
    merged = _merge_labeled_value_fields(current, [source])
    labels = [item.label for item in merged]
    assert "Daire No" not in labels
    assert "Ödeme Şekli" in labels
    assert "Kira Tutarı" in labels


def test_historical_focus_does_not_borrow_current_values():
    contact_id = uuid4()
    current_id = uuid4()
    historical_id = uuid4()
    current = _row(
        id=current_id,
        contact_id=contact_id,
        unit_number="401",
        metadata_json={
            "previous_agreement_id": str(historical_id),
            "original_unit": "408",
            "final_unit": "401",
            "opportunity": "366064.00",
            "currency": "USD",
        },
    )
    historical = _row(
        id=historical_id,
        contact_id=contact_id,
        unit_number="408",
        source="bitrix_unit_change_history",
        metadata_json={"historical_unit_change": True, "final_unit": "401", "replaced_by_agreement_id": str(current_id)},
    )
    assert _unit_change_source_rows(historical, [current, historical]) == []
    summary = _summary(agreement_id=historical_id, unit_number="408")
    _apply_unit_change_value_display(summary, historical, [current, historical])
    assert summary.amount is None


if __name__ == "__main__":
    test_empty_current_uses_original_b08_values()
    test_filled_current_is_not_overwritten()
    test_distinct_historical_amounts_are_both_shown()
    test_unit_identifying_extras_are_not_copied()
    test_historical_focus_does_not_borrow_current_values()
    print("ok")
