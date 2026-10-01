"""Stage 4.1 one-shot 9:16 recomposition tests."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.premium_format_recomposer_v1 import (
    CANVAS,
    execute_ornek_00013_story,
    prepare_format_recomposition,
)
from investhome_api.services.creative_director.premium_story_recomposer_v1 import is_simple_resize
from investhome_api.services.creative_director.project_creative_master_library import empty_library
from investhome_api.services.creative_director.stage4_1_recompose import (
    STATUS_PENDING,
    generate_stage4_1_recomposition,
)


def _fake_master() -> Image.Image:
    image = Image.new("RGB", (1080, 1350), (40, 47, 56))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 360, 460, 1350), fill=(160, 160, 160))
    draw.text((620, 240), "DÜZENLİ.", fill=(244, 239, 228))
    draw.text((620, 360), "GÜVENLİ.", fill=(244, 239, 228))
    draw.text((620, 480), "PRESTİJLİ.", fill=(201, 168, 92))
    draw.text((640, 640), "Planli sehir", fill=(236, 230, 218))
    draw.rectangle((640, 760, 980, 800), fill=(90, 90, 90))
    draw.text((650, 768), "yatirim lokasyonu yapiyor.", fill=(236, 230, 218))
    draw.text((760, 1220), "investhome", fill=(244, 239, 228))
    return image


def test_recomposition_is_native_story_not_resize() -> None:
    original = _fake_master()
    packed = execute_ornek_00013_story(original)
    story = packed["story"]
    assert tuple(story.size) == CANVAS
    assert packed["simple_resize"] is False
    assert packed["photo_pastes"] == 1
    assert packed["generated_architecture_pixels"] == 0
    assert is_simple_resize(original, story) is False
    validation = packed["validation"]
    assert validation["PHOTO_OBJECT_COUNT"] == 1
    assert validation["SEMANTIC_LAYER_DUPLICATION_COUNT"] == 0
    assert validation["ORPHAN_TEXT_FRAGMENT_COUNT"] == 0
    assert validation["SOURCE_TYPE_LEAKAGE"] == 0


def test_stage4_0_prepare_still_refuses_execute() -> None:
    try:
        prepare_format_recomposition(empty_library(project_id="p", project_name="x"), execute=True)
        raise AssertionError("Stage 4.0 prepare must still refuse execute")
    except RuntimeError as exc:
        assert "must not execute a Story in Stage 4.0" in str(exc)


def test_stage4_1_does_not_generate_or_self_approve() -> None:
    src = inspect.getsource(generate_stage4_1_recomposition)
    assert "openai" not in src.lower()
    assert STATUS_PENDING == "PREMIUM_RECOMPOSED_STORY_PENDING_HUMAN_REVIEW"
    assert "auto_approved" in src
    assert "WAIT FOR HUMAN VISUAL REVIEW" in src
