from PIL import Image, ImageDraw

from investhome_api.services.creative_director.semantic_layer_exclusivity_v1 import (
    orphan_text_fragment_count,
    refuse_if_unclean,
    strip_source_typography_from_photo,
    validate_semantic_exclusivity,
)


def test_strip_removes_source_type_inside_photo_crop() -> None:
    original = Image.new("RGB", (100, 100), (40, 47, 56))
    draw = ImageDraw.Draw(original)
    draw.rectangle((0, 40, 40, 99), fill=(160, 160, 160))
    draw.text((48, 10), "D", fill=(240, 240, 240))
    photo_box = {"x": 0.0, "y": 0.0, "w": 0.7, "h": 1.0}
    type_box = {"x": 0.45, "y": 0.05, "w": 0.5, "h": 0.3}
    photo = original.crop((0, 0, 70, 100)).convert("RGBA")
    cleaned = strip_source_typography_from_photo(original, photo, photo_box, [type_box], (40, 47, 56))
    # Glyph column that overlapped the photo crop must now be navy.
    pixel = cleaned.getpixel((50, 14))
    assert pixel[0] < 80 and pixel[1] < 80 and pixel[2] < 90
    # Architecture on the left stays.
    stone = cleaned.getpixel((10, 70))
    assert stone[0] > 120


def test_refuse_if_unclean() -> None:
    report = {
        "SEMANTIC_LAYER_DUPLICATION_COUNT": 2,
        "ORPHAN_TEXT_FRAGMENT_COUNT": 2,
        "PHOTO_OBJECT_COUNT": 1,
        "pass": False,
    }
    try:
        refuse_if_unclean(report)
        raise AssertionError("expected refuse")
    except RuntimeError as exc:
        assert "PREMIUM_FORMAT_RENDER_BUG_REMAINS" in str(exc)


def test_orphan_count_ignores_type_inside_final_rect() -> None:
    story = Image.new("RGB", (200, 200), (40, 47, 56))
    draw = ImageDraw.Draw(story)
    draw.rectangle((120, 20, 180, 80), fill=(240, 240, 240))
    draw.rectangle((10, 120, 40, 160), fill=(240, 240, 240))
    placements = {"HEADLINE": {"xy": [120, 20], "size": [60, 60]}}
    orphans = orphan_text_fragment_count(story, placements, (40, 47, 56), min_pixels=20)
    assert orphans == 1
    report = validate_semantic_exclusivity(
        story=story,
        placements=placements,
        navy=(40, 47, 56),
        photo_pastes=1,
        layer_roles=["PROJECT_PHOTO", "HEADLINE"],
    )
    assert report["PHOTO_OBJECT_COUNT"] == 1
    assert report["ORPHAN_TEXT_FRAGMENT_COUNT"] == 1
    assert report["pass"] is False
