"""Phase 9.0-R2 — typographic completion. Same Master. No new concept."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r1_compose import CONCEPT
from investhome_api.services.creative_director.phase9_0_r2_compose import PARENT_R1_ASSET, html_copy_ok, r2_html
from investhome_api.services.creative_director.phase9_0_r2_master import WORKFLOW_ID_90_R2, generate_phase9_0_r2_premium_master_02


def test_locks() -> None:
    assert PARENT_R1_ASSET == "5d0a6e9e-f87e-4dcc-bd6d-c6d520baf283"
    assert MASTER_NAME_02 == "The Temple — Premium Campaign 02"
    assert TEMPLE_PREMIUM_MASTER_02_ID != APPROVED_MASTER_ID
    assert WORKFLOW_ID_90_R2 == "phase9_0_r2_premium_master_02_editorial_completion"
    assert CONCEPT["concept_name"] == "SPIRE_CUT_PAGE"
    assert generate_phase9_0_r2_premium_master_02


def test_html_recomposed_not_centered_stack() -> None:
    html = r2_html(scene_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert html_copy_ok(html)
    assert "line-height:1.0" in html
    assert "text-align:center" not in html
    assert "designed_canvas" not in html
    assert "LANSMAN" in html and "AVANTAJI" in html


def test_no_new_master_or_format() -> None:
    import investhome_api.services.creative_director.phase9_0_r2_compose as compose
    import investhome_api.services.creative_director.phase9_0_r2_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "empty_master(" not in inspect.getsource(workflow)
    assert "designed_canvas" in inspect.getsource(compose)
    assert "attach_format_child" not in src
    assert "approve_and_lock_master" not in src
    assert "creative_concept_changed" in inspect.getsource(workflow)
