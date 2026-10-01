"""Phase 11.11 tests — one reconstruction, Hybrid V2 used not modified, no ORNEK_00001 auto-select."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.hybrid_premium_engine_v2 import ENGINE_ID
from investhome_api.services.creative_director.phase11_11_compose import html_copy_ok, type_layout
from investhome_api.services.creative_director.phase11_11_master import REQUIRED_SCORE_FLOORS, generate_phase11_11_reference_guided
from investhome_api.services.creative_director.phase11_11_match import DAY008_ASSET_ID, DAY008_CROP
from investhome_api.services.creative_director.phase11_11_select import SELECTED_FILENAME, reference_score_table
from investhome_api.services.creative_director.phase11_11_structure import RELATIVE, transferable_dna
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY


def test_does_not_auto_select_ornek_00001() -> None:
    table = reference_score_table()
    assert table["auto_select_orneK_00001"] is False
    assert table["selected"] == "ORNEK_00013.jpg"
    assert table["selected"] != "ORNEK_00001.jpg"
    assert SELECTED_FILENAME == "ORNEK_00013.jpg"
    selected = next(item for item in table["records"] if item["selected"])
    first = table["records"][0]
    assert selected["filename"] == first["filename"] or selected["total"] >= next(
        item["total"] for item in table["records"] if item["filename"] == "ORNEK_00001.jpg"
    )


def test_uses_hybrid_v2_engine_id_without_modifying_v2_compose() -> None:
    assert ENGINE_ID == "STAGE3_HYBRID_PREMIUM_ENGINE_V2"
    src = inspect.getsource(generate_phase11_11_reference_guided)
    assert "extract_project_object_v2" in src
    assert "compose_hybrid_v2" not in src
    assert "compose_hybrid_r1" not in src
    assert "add_master" not in src
    assert "attach_format_child" not in src
    assert DAY008_ASSET_ID == "2d44757b-079c-4a78-a4a9-5fe6370466c8"
    assert DAY008_ASSET_ID != "7696df34-0544-44b9-89f5-0d1b2523c412"
    assert DAY008_CROP["width"] <= 0.50


def test_structure_is_relative_and_signature_excluded() -> None:
    assert 0 < RELATIVE["hero_visual_mass_width"] < 1
    assert 0 < RELATIVE["offer_size_vs_canvas_height"] < 0.22
    dna = transferable_dna()
    joined = " ".join(dna["REFERENCE_SIGNATURE_EXCLUDED"]).lower()
    assert "navy" in joined
    assert "colonnade" in joined
    assert "düzenli" in joined or "uniloft" in joined
    layout = type_layout({"x": 0, "y": 400, "w": 500, "h": 800})
    assert layout["offer"]["size"] >= layout["project"]["size"] * 2.4
    assert abs(layout["price"]["y"] - layout["unit"]["y"]) <= 2


def test_copy_gate_and_quality_floors() -> None:
    good = (
        "<svg>THE TEMPLE WASHINGTON D.C. %35 LANSMAN AVANTAJI "
        f"675.000 USD 2+1 DAİRE PROJEYİ KEŞFET {APPROVED_BOTTOM_COPY}</svg>"
    )
    assert html_copy_ok(good) is True
    assert html_copy_ok(good.replace("<svg>", "<svg> Uniloft ")) is False
    assert html_copy_ok(good.replace("<svg>", "<svg button ")) is False
    assert REQUIRED_SCORE_FLOORS["PUBLISHABILITY"] == 9
    assert REQUIRED_SCORE_FLOORS["ART_DIRECTION"] == 9
