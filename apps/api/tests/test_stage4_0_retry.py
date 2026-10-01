"""Stage 4.0 RETRY tests — brand Story render, no Temple, no GPT Image, no simple resize."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase12_0_ingestion import PRODUCTION_MASTER_ID
from investhome_api.services.creative_director.phase5_workflow import TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.premium_format_adapter_v1 import select_production_premium_master
from investhome_api.services.creative_director.premium_story_recomposer_v1 import CANVAS, is_simple_resize, recompose_ornek_00013_to_story
from investhome_api.services.creative_director.stage4_0_retry import NEXT_PHASE, STATUS_PENDING, generate_stage4_0_retry


def _fake_master() -> Image.Image:
    image = Image.new("RGB", (1080, 1350), (20, 24, 32))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 500, 540, 1350), fill=(90, 90, 90))
    draw.text((620, 80), "DÜZENLİ.", fill=(244, 239, 228))
    draw.text((620, 160), "GÜVENLİ.", fill=(244, 239, 228))
    draw.text((620, 240), "PRESTİJLİ.", fill=(201, 168, 92))
    draw.text((620, 1180), "investhome", fill=(244, 239, 228))
    return image


def test_recomposer_is_native_story_not_resize() -> None:
    original = _fake_master()
    packed = recompose_ornek_00013_to_story(original)
    story = packed["story"]
    assert tuple(story.size) == CANVAS
    assert packed["simple_resize"] is False
    assert is_simple_resize(original, story) is False
    assert is_simple_resize(original, original.resize(CANVAS, Image.Resampling.LANCZOS)) is True


def test_retry_does_not_generate_or_approve() -> None:
    src = inspect.getsource(generate_stage4_0_retry)
    assert "openai" not in src.lower()
    assert STATUS_PENDING == "PREMIUM_STORY_PENDING_HUMAN_REVIEW"
    assert "auto_approved" in src
    assert NEXT_PHASE == "WAIT FOR HUMAN VISUAL REVIEW"
    assert "TEMPLE_PROJECT_ID" in src


def test_brand_selector_still_excludes_temple() -> None:
    from investhome_api.services.creative_director.phase12_1_approve_lock import apply_brand_approval
    from investhome_api.services.creative_director.project_creative_master_library import add_master, empty_library, empty_master

    library = empty_library(project_id=TEMPLE_PROJECT_ID, project_name="The Temple")
    master = empty_master(
        project_id=TEMPLE_PROJECT_ID,
        master_name="brand",
        master_type="PREMIUM_CAMPAIGN",
        approval_status="DRAFT",
        master_id=PRODUCTION_MASTER_ID,
    )
    master["source"] = "INVESTHOME_APPROVED"
    master["canonical_format"] = "4:5"
    apply_brand_approval(master)
    add_master(library, master)
    assert select_production_premium_master(library, project_id=TEMPLE_PROJECT_ID) is None
    brand = select_production_premium_master(library, scope="BRAND", brand_id="INVESTHOME")
    assert brand is not None
    assert brand["master_id"] == PRODUCTION_MASTER_ID
