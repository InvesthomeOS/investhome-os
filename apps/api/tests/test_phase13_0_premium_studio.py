"""Phase 13.0 — live Creative Studio Premium Campaigns. No generation."""

from __future__ import annotations

import inspect

from investhome_api.services.creative_director.creative_master_router_v2 import (
    COPY_EDIT_ONLY,
    FAMILY_WIDE_REVISION,
    FORMAT_ADAPTATION,
    PRICE_EDIT_ONLY,
    classify_production_intent,
)
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.phase12_3_family_ingest import FAMILY_ID, FILE_1X1, FILE_4X5, FILE_9X16
from investhome_api.services.creative_director.phase12_3_lock import selected_family_record
from investhome_api.services.creative_director.phase12_4_approve_lock import apply_human_approval
from investhome_api.services.creative_director.premium_creative_family_v1 import (
    FEED_PORTRAIT,
    LANDSCAPE,
    SQUARE,
    STORY_REEL,
    lookup_format_master,
    ornek_00013_family,
)
from investhome_api.services.creative_director.premium_studio import (
    DISPLAY_FORMATS,
    MSG_FORMAT_MASTER_MISSING,
    MSG_REVISION_FAIL,
    MSG_TARGET_NOT_PRESENT,
    format_missing_message,
    is_proven_copy_command,
    is_proven_price_command,
    plan_studio_revision,
    present_card,
    present_family,
)
from investhome_api.services.creative_director.project_creative_master_library import empty_library


def _catalog() -> dict:
    return {
        FILE_4X5: {"filename": FILE_4X5, "asset_id": "f73556b5-e8a7-4c20-b874-0a6aef2a5570", "sha256": "a", "width": 4252, "height": 5315, "format": FEED_PORTRAIT, "folder": "DESIGN_REFERENCE"},
        FILE_9X16: {"filename": FILE_9X16, "asset_id": "c83ba58e-063f-4118-8df1-b8787082187b", "sha256": "b", "width": 1080, "height": 1920, "format": STORY_REEL, "folder": "DESIGN_REFERENCE"},
        FILE_1X1: {"filename": FILE_1X1, "asset_id": "4de0deeb-49f0-4936-9db4-9e6deb0d6cb7", "sha256": "c", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
        "ORNEK_00004.jpg": {"filename": "ORNEK_00004.jpg", "asset_id": "5ce5e26d-d1fd-4802-a6e6-7c0eecfb3279", "sha256": "d", "width": 1080, "height": 1080, "format": SQUARE, "folder": "DESIGN_REFERENCE"},
    }


def _family() -> dict:
    return apply_human_approval(selected_family_record(_catalog()))


def test_uniloft_card_hides_missing_16x9() -> None:
    card = present_card(_family())
    assert card["id"] == FAMILY_ID
    assert "UniLoft" in card["title"]
    assert card["subtitle"] == "Son Daireler"
    assert card["available_formats"] == [FEED_PORTRAIT, STORY_REEL, SQUARE]
    assert LANDSCAPE not in card["available_formats"]
    assert card["preview_asset_id"] == "f73556b5-e8a7-4c20-b874-0a6aef2a5570"


def test_campaign_defaults_to_story() -> None:
    payload = present_family(_family())
    assert payload["selected_format"] == STORY_REEL
    assert payload["selected"]["preview_asset_id"] == "c83ba58e-063f-4118-8df1-b8787082187b"
    assert [item["format"] for item in payload["formats"]] == list(DISPLAY_FORMATS)
    assert payload["formats"][0]["available"] is True
    assert payload["publishing"]["available"] is False
    assert "semantic" not in str(payload).lower()


def test_16x9_request_does_not_generate() -> None:
    classified = classify_production_intent("16:9 yap.")
    assert classified["intent"] == FORMAT_ADAPTATION
    assert classified["target_format"] == LANDSCAPE
    plan = plan_studio_revision(
        family=_family(),
        instruction="16:9 yap.",
        scope="selected",
        fmt=STORY_REEL,
    )
    assert plan["ok"] is False
    assert plan["execute"] is False
    assert plan["code"] == "FORMAT_MASTER_MISSING"
    assert plan["message"] == format_missing_message(LANDSCAPE)
    assert "16:9" in plan["message"]


def test_single_format_price_on_feed_is_target_not_present() -> None:
    plan = plan_studio_revision(
        family=_family(),
        instruction="Fiyatı 375.000 USD yap.",
        scope="selected",
        fmt=FEED_PORTRAIT,
    )
    assert classify_production_intent("Fiyatı 375.000 USD yap.")["intent"] == PRICE_EDIT_ONLY
    assert plan["execute"] is False
    assert plan["code"] == "TARGET_NOT_PRESENT"
    assert plan["message"] == MSG_TARGET_NOT_PRESENT


def test_single_format_price_routes_to_story() -> None:
    plan = plan_studio_revision(
        family=_family(),
        instruction="Fiyatı 375.000 USD yap.",
        scope="selected",
        fmt=STORY_REEL,
    )
    assert plan["ok"] is True
    assert plan["execute"] is True
    assert plan["family_wide"] is False
    assert plan["members"] == [{"format": STORY_REEL, "action": "REVISE"}]


def test_family_wide_price_uses_family_router() -> None:
    plan = plan_studio_revision(
        family=_family(),
        instruction="Fiyatı 375.000 USD yap.",
        scope="campaign",
        fmt=STORY_REEL,
    )
    assert plan["ok"] is True
    assert plan["execute"] is True
    assert plan["family_wide"] is True
    by_format = {item["format"]: item["action"] for item in plan["members"]}
    assert by_format[FEED_PORTRAIT] != "REVISE"
    assert by_format[STORY_REEL] == "REVISE"
    assert by_format[SQUARE] == "REVISE"
    assert by_format[LANDSCAPE] != "REVISE"


def test_copy_command_and_family_wide_copy() -> None:
    command = "Son Daireler yazısını Son Fırsatlar olarak değiştir."
    assert classify_production_intent(command)["intent"] == COPY_EDIT_ONLY
    assert is_proven_copy_command(command)
    selected = plan_studio_revision(family=_family(), instruction=command, scope="selected", fmt=STORY_REEL)
    assert selected["execute"] is True
    assert selected["family_wide"] is False
    wide = plan_studio_revision(family=_family(), instruction=command, scope="campaign", fmt=STORY_REEL)
    assert wide["family_wide"] is True
    by_format = {item["format"]: item["action"] for item in wide["members"]}
    assert by_format[FEED_PORTRAIT] == "REVISE"
    assert by_format[STORY_REEL] == "REVISE"
    assert by_format[SQUARE] == "REVISE"
    assert by_format[LANDSCAPE] != "REVISE"


def test_visual_and_unknown_commands_fail_closed() -> None:
    visual = plan_studio_revision(
        family=_family(),
        instruction="Bu görsel yerine diğer onaylı dış cephe görselini kullan.",
        scope="selected",
        fmt=STORY_REEL,
    )
    assert visual["execute"] is False
    assert visual["message"] == MSG_REVISION_FAIL
    unknown = plan_studio_revision(
        family=_family(),
        instruction="Yeni bir reklam hazırla.",
        scope="selected",
        fmt=STORY_REEL,
    )
    assert unknown["execute"] is False
    assert unknown["code"] == "REVISION_FAIL"


def test_source_does_not_call_image_providers() -> None:
    import investhome_api.api.routes.premium_studio as routes
    import investhome_api.services.creative_director.premium_studio as studio

    for module in (studio, routes):
        source = inspect.getsource(module)
        assert "generate_image(" not in source
        assert "generate_gpt_image_creatives" not in source
        assert "generate_ideogram" not in source
        assert "revise_ad_from_campaign" not in source


def test_ornek_family_is_not_uniloft() -> None:
    family = ornek_00013_family()
    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    library["premium_creative_families"] = [family, _family()]
    uniloft = present_card(_family())
    assert uniloft["id"] == FAMILY_ID
    assert lookup_format_master(_family(), LANDSCAPE)["status"] != "HUMAN_APPROVED"
    assert is_proven_price_command("Fiyatı 375.000 USD yap.")
    assert FAMILY_WIDE_REVISION
    assert MSG_FORMAT_MASTER_MISSING
