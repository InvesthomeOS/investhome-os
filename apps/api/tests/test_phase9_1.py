"""Phase 9.1 — one Temple Premium Campaign 03 from ORNEK_00006. No promotion. No format work."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.phase8_3_approve_lock import APPROVED_MASTER_ID
from investhome_api.services.creative_director.phase9_0_master import TEMPLE_PREMIUM_MASTER_02_ID
from investhome_api.services.creative_director.phase9_1_compose import (
    CONCEPT,
    DISTINCTNESS_PRE,
    INTERIOR_ASSET_ID,
    ORNEK_FILENAME,
    html_copy_ok,
    master_html,
)
from investhome_api.services.creative_director.phase9_1_master import (
    MASTER_NAME_03,
    TEMPLE_PREMIUM_MASTER_03_ID,
    WORKFLOW_ID_91,
    generate_phase9_1_premium_master_03,
)


def test_locks() -> None:
    assert ORNEK_FILENAME == "ORNEK_00006.jpg"
    assert MASTER_NAME_03 == "The Temple — Premium Campaign 03"
    assert TEMPLE_PREMIUM_MASTER_03_ID != APPROVED_MASTER_ID
    assert TEMPLE_PREMIUM_MASTER_03_ID != TEMPLE_PREMIUM_MASTER_02_ID
    assert CONCEPT["concept_name"] == "LOOKING_CHAMBER"
    assert "dark designed lid" in CONCEPT["concept_sentence"]
    assert all(v == "YES" for v in DISTINCTNESS_PRE.values())
    assert WORKFLOW_ID_91 == "phase9_1_premium_master_03_looking_chamber"
    assert INTERIOR_ASSET_ID == "c3d11c35-d8b7-485c-b216-0a4da68b751a"
    assert generate_phase9_1_premium_master_03


def test_html_is_lid_not_sky_or_parchment_stack() -> None:
    html = master_html(scene_uri="data:image/jpeg;base64,xx", logo_markup="<svg></svg>", font_css="")
    assert html_copy_ok(html)
    assert "text-align:center" not in html
    assert "#ead3b3" not in html
    assert "THE TEMPLE" not in html
    assert "uniloft" not in html.lower()


def test_no_format_or_approval() -> None:
    import investhome_api.services.creative_director.phase9_1_compose as compose
    import investhome_api.services.creative_director.phase9_1_master as workflow

    src = inspect.getsource(workflow) + inspect.getsource(compose)
    assert "attach_format_child" not in src
    assert "approve_and_lock_master" not in inspect.getsource(workflow)
    assert 'router_eligible"] = False' in inspect.getsource(workflow)
    assert "LOOKING_CHAMBER" in inspect.getsource(compose)
    assert "ORNEK_00006" in inspect.getsource(workflow)
