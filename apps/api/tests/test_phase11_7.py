"""Phase 11.7 tests — finish pass, same concept, no old compiler, no new photo."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase11_6_strategy import CONCEPT_NAME, DAY003_ASSET_ID
from investhome_api.services.creative_director.phase11_7_compose import html_copy_ok_r1
from investhome_api.services.creative_director.phase11_7_master import generate_phase11_7_hybrid_finish
from investhome_api.services.creative_director.phase11_7_object import CROP_BOX


def test_same_concept_and_source() -> None:
    assert CONCEPT_NAME == "THE_LEDGER"
    assert DAY003_ASSET_ID == "7346e259-f999-4fbb-a8d5-63708d4e0c81"
    assert CROP_BOX["width"] <= 0.50


def test_r1_is_not_old_compiler() -> None:
    src = inspect.getsource(generate_phase11_7_hybrid_finish)
    assert "phase11_4_compose" not in src
    assert "attach_format_child" not in src
    assert "add_master" not in src
    assert "generate_non_project_field" not in src


def test_copy_gate_rejects_vertical_spine() -> None:
    good = (
        "<svg>TAŞ TEMİNAT THE TEMPLE WASHINGTON D.C. %35 LANSMAN AVANTAJI "
        "675.000 USD 2+1 DAİRE PROJEYİ KEŞFET TARİHİN RUHU, GELECEĞİN DEĞERİ.</svg>"
    )
    assert html_copy_ok_r1(good) is True
    assert html_copy_ok_r1(good.replace("<svg>", "<svg> rotate(90) ")) is False
