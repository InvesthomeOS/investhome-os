"""Phase 9.0-R1 — composition rebuild of Premium Campaign 02. Not a new Master."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_ASSET_ID, APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_compose import SUNSET_ASSET_ID, SUNSET_FILENAME
from investhome_api.services.creative_director.phase9_0_master import MASTER_NAME_02, TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_0_r1_compose import CONCEPT, PARENT_MASTER_02_ASSET, html_copy_ok, r1_html
from investhome_api.services.creative_director.phase9_0_r1_master import WORKFLOW_ID_90_R1, generate_phase9_0_r1_premium_master_02


def test_locks() -> None:
    assert SUNSET_FILENAME == "IH_DC_TMP_001_Render_Exterior_Sunset_001.jpg"
    assert SUNSET_ASSET_ID == "65f68756-a006-43d4-9c86-2c0ec25ad229"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert APPROVED_MASTER_ID == "30b8d880-61d3-556a-b6c3-329e3632ed69"
    assert APPROVED_ASSET_ID == "a6c87a3c-835e-4e8b-9179-b247720fe61b"
    assert PARENT_MASTER_02_ASSET == "90e8dd65-1593-444f-9dc6-4a8c1d19bc78"
    assert MASTER_NAME_02 == "The Temple — Premium Campaign 02"
    assert TEMPLE_PREMIUM_MASTER_02_ID == "d0116373-51a9-57aa-bbc1-ea7307ad812e"
    assert WORKFLOW_ID_90_R1 == "phase9_0_r1_premium_master_02_composition_rebuild"
    assert generate_phase9_0_r1_premium_master_02
    assert CONCEPT["concept_name"] == "SPIRE_CUT_PAGE"
    assert "typography is placed over the sunset" not in CONCEPT["concept_sentence"].lower()


def test_html_is_page_cut_not_centered_sky_type() -> None:
    html = r1_html(scene_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert html_copy_ok(html)
    assert "ALIRKEN" in html and "KAZAN" in html
    assert "%35" in html and "LANSMAN AVANTAJI" in html
    assert "675.000 USD" in html
    assert APPROVED_BOTTOM_COPY in html
    assert "text-align:center" not in html
    assert "spire_axis" in html
    assert "#1A2330" not in html
    assert "THE TEMPLE" not in html
    assert "UniLoft" not in html


def test_same_master_not_new_and_no_format() -> None:
    import investhome_api.services.creative_director.phase9_0_r1_compose as compose
    import investhome_api.services.creative_director.phase9_0_r1_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "empty_master(" not in inspect.getsource(workflow)
    assert "TEMPLE_PREMIUM_MASTER_02_ID" in inspect.getsource(workflow)
    assert "visual_history" in inspect.getsource(workflow)
    assert "PARENT_MASTER_02_ASSET" in src
    assert "attach_format_child" not in src
    assert "approve_and_lock_master" not in src
    assert "CANDIDATE_IDS" not in src
    assert "designed_canvas" in inspect.getsource(compose)
    assert "photo_page_mask" in inspect.getsource(compose)
