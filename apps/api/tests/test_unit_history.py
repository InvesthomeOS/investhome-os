from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from investhome_api.services.crm.unit_change import unit_history_steps


def _row(**kwargs):
    values = {
        "id": uuid4(),
        "contact_id": uuid4(),
        "project_group": "1812_h_pl",
        "source": "bitrix",
        "unit_number": None,
        "agreement_date": None,
        "created_at": None,
        "metadata_json": {},
    }
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_two_step_history_uses_stored_agreements():
    contact_id = uuid4()
    current_id = uuid4()
    historical_id = uuid4()
    current = _row(
        id=current_id,
        contact_id=contact_id,
        unit_number="307",
        metadata_json={
            "historical_unit_change": False,
            "unit_change_status": "DAİRE DEĞİŞİMİ",
            "original_unit": "B07",
            "final_unit": "307",
            "previous_agreement_id": str(historical_id),
            "unit_change_sequence": ["B07", "307"],
        },
    )
    historical = _row(
        id=historical_id,
        contact_id=contact_id,
        source="bitrix_unit_change_history",
        unit_number="B07",
        metadata_json={
            "historical_unit_change": True,
            "original_unit": "B07",
            "final_unit": "307",
            "replaced_by_agreement_id": str(current_id),
        },
    )
    steps = unit_history_steps(current, [current, historical])
    assert [step.unit_number for step in steps] == ["B07", "307"]
    assert steps[0].is_historical_unit_change is True
    assert steps[0].is_current is False
    assert steps[1].is_current is True


def test_sequence_order_beats_missing_dates():
    contact_id = uuid4()
    current_id = uuid4()
    first_id = uuid4()
    second_id = uuid4()
    current = _row(
        id=current_id,
        contact_id=contact_id,
        unit_number="304",
        metadata_json={
            "previous_units": ["105", "305"],
            "final_unit": "304",
            "unit_change_sequence": ["105", "305", "304"],
        },
    )
    first = _row(
        id=first_id,
        contact_id=contact_id,
        unit_number="105",
        agreement_date=date(2023, 7, 28),
        metadata_json={"historical_unit_change": True, "final_unit": "304", "replaced_by_agreement_id": str(current_id)},
    )
    second = _row(
        id=second_id,
        contact_id=contact_id,
        unit_number="305",
        metadata_json={"historical_unit_change": True, "final_unit": "304", "replaced_by_agreement_id": str(current_id)},
    )
    steps = unit_history_steps(current, [second, current, first])
    assert [step.unit_number for step in steps] == ["105", "305", "304"]


def test_no_section_without_historical_agreements():
    current = _row(unit_number="401")
    assert unit_history_steps(current, [current]) == []


def test_other_project_rows_are_ignored():
    contact_id = uuid4()
    current = _row(contact_id=contact_id, unit_number="307", metadata_json={"original_unit": "B07", "final_unit": "307"})
    other = _row(
        contact_id=contact_id,
        project_group="reit",
        source="bitrix_unit_change_history",
        unit_number="B07",
        metadata_json={"historical_unit_change": True, "final_unit": "307"},
    )
    assert unit_history_steps(current, [current, other]) == []
