"""Phase 9.1-R1 — Looking Chamber spatial reveal. Same Master. No card. No header bar."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase9_1_compose import INTERIOR_ASSET_ID
from investhome_api.services.creative_director.phase9_1_master import TEMPLE_PREMIUM_MASTER_03_ID
from investhome_api.services.creative_director.phase9_1_r1_compose import (
    CONCEPT_R1,
    PARENT_MASTER_03_ASSET,
    html_copy_ok,
    r1_html,
)
from investhome_api.services.creative_director.phase9_1_r1_master import WORKFLOW_ID_91_R1, generate_phase9_1_r1_premium_master_03


def test_locks() -> None:
    assert PARENT_MASTER_03_ASSET == "cdad2256-4b1c-41cc-b340-0d26badd47ab"
    assert INTERIOR_ASSET_ID == "c3d11c35-d8b7-485c-b216-0a4da68b751a"
    assert CONCEPT_R1["concept_name"] == "LOOKING_CHAMBER"
    assert "exterior photo is placed" not in CONCEPT_R1["mechanism_sentence"].lower()
    assert "spatial reveal" in CONCEPT_R1["mechanism_sentence"].lower() or "opens" in CONCEPT_R1["mechanism_sentence"]
    assert WORKFLOW_ID_91_R1 == "phase9_1_r1_premium_master_03_spatial_reveal"
    assert generate_phase9_1_r1_premium_master_03
    assert TEMPLE_PREMIUM_MASTER_03_ID


def test_html_not_card_or_parchment() -> None:
    html = r1_html(scene_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert html_copy_ok(html)
    assert "border-radius" not in html
    assert "#ead3b3" not in html
    assert "text-align:center" not in html


def test_no_new_master_or_format() -> None:
    import investhome_api.services.creative_director.phase9_1_r1_compose as compose
    import investhome_api.services.creative_director.phase9_1_r1_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "empty_master(" not in inspect.getsource(workflow)
    assert "attach_format_child" not in src
    assert "designed_chamber" in inspect.getsource(compose)
    assert "PARENT_MASTER_03_ASSET" in inspect.getsource(workflow)
