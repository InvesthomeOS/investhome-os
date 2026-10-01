"""Phase 5.1A — PROJECT_ARCHITECTURE_LOCK and crop-aware ArchitectureIntegrityQA."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageEnhance

from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    PRODUCTION_COVER_V2,
)
from investhome_api.services.creative_director.project_architecture_lock import (
    LOCK_METHOD,
    POLICY_NAME,
    architecture_integrity_qa,
    architecture_lock_policy,
    derive_architecture_mask,
    lock_generated_creative,
    should_apply_architecture_lock,
    source_has_architecture_structure,
)
from investhome_api.services.creative_director.phase5_video import video_architecture_lock_interface


def _temple(size: tuple[int, int] = (400, 500), *, spire_w: int = 28, floors: int = 8, cols: int = 4) -> Image.Image:
    w, h = size
    im = Image.new("RGB", size, (176, 196, 214))
    draw = ImageDraw.Draw(im)
    body_x0 = int(w * 0.42)
    body_x1 = int(w * 0.88)
    body_y0 = int(h * 0.38)
    body_y1 = int(h * 0.88)
    draw.rectangle((body_x0, body_y0, body_x1, body_y1), fill=(214, 204, 186))
    ww = max(6, (body_x1 - body_x0) // (cols * 2))
    wh = max(8, (body_y1 - body_y0) // (floors * 2))
    for r in range(floors):
        for c in range(cols):
            x = body_x0 + 12 + c * (ww + 10)
            y = body_y0 + 12 + r * (wh + 8)
            draw.rectangle((x, y, x + ww, y + wh), fill=(42, 48, 58))
    spire_x = (body_x0 + body_x1) // 2
    top = int(h * 0.06)
    draw.rectangle((spire_x - spire_w // 2, int(h * 0.18), spire_x + spire_w // 2, body_y0), fill=(208, 198, 180))
    draw.polygon(
        [
            (spire_x, top),
            (spire_x - spire_w // 2, int(h * 0.18)),
            (spire_x + spire_w // 2, int(h * 0.18)),
        ],
        fill=(200, 188, 168),
    )
    draw.rectangle((0, int(h * 0.86), w, h), fill=(36, 90, 48))
    return im


def _grade(img: Image.Image, factor: float = 1.35) -> Image.Image:
    warm = ImageEnhance.Color(img).enhance(factor)
    return ImageEnhance.Contrast(warm).enhance(1.15)


def test_policy_names_source_and_video_hook() -> None:
    policy = architecture_lock_policy(
        source_asset_id=LOCKED_HERO_ASSET_ID,
        source_filename="IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
    )
    assert policy["policy_name"] == POLICY_NAME
    assert policy["project_locked"] is True
    assert policy["project_architecture_lock"] is True
    assert policy["architecture_lock_method"] == LOCK_METHOD
    assert "source_pixel" in policy["architecture_lock_method"]
    assert policy["user_drawn_mask_required"] is False
    assert policy["ai_remains_primary_advertisement_designer"] is True
    assert policy["phase4_renderer_is_not_primary"] is True
    assert policy["fail_closed"] is True
    assert policy["max_retries"] == 2
    assert policy["video"]["video_started"] is False
    video = video_architecture_lock_interface()
    assert video["video_started"] is False
    assert video["architecture_lock_policy"] == POLICY_NAME


def test_brand_market_skips_architecture_lock() -> None:
    src = _temple()
    apply, reason = should_apply_architecture_lock(campaign_mode="general", source=src)
    assert apply is False
    apply_b, reason_b = should_apply_architecture_lock(campaign_mode="project", brand_market_ad=True, source=src)
    assert apply_b is False
    apply_p, _ = should_apply_architecture_lock(campaign_mode="project", source=src)
    assert apply_p is True
    assert source_has_architecture_structure(src) is True
    solid = Image.new("RGB", (400, 500), (30, 40, 50))
    assert source_has_architecture_structure(solid) is False


def test_crop_and_grade_do_not_fail_architecture_qa() -> None:
    src = _temple()
    crop = Image.new("RGB", (480, 560), (12, 16, 24))
    piece = src.crop((80, 0, 400, 500)).resize((300, 420))
    crop.paste(piece, (160, 80))
    cropped = architecture_integrity_qa(src, crop, source_asset_id=LOCKED_HERO_ASSET_ID)
    graded = architecture_integrity_qa(src, _grade(src), source_asset_id=LOCKED_HERO_ASSET_ID)
    assert cropped["architecture_integrity_status"] == "pass"
    assert graded["architecture_integrity_status"] == "pass"
    assert cropped["mean_color_not_used"] is True
    assert cropped["comparison_method"]


def test_mutated_tower_and_windows_fail_architecture_qa() -> None:
    src = _temple(spire_w=28, floors=8, cols=4)
    mutated = _temple(spire_w=90, floors=5, cols=7)
    # Flatten the tower — a redesigned building, not a grade/crop.
    draw = ImageDraw.Draw(mutated)
    draw.rectangle((int(400 * 0.42), 0, int(400 * 0.88), int(500 * 0.38)), fill=(176, 196, 214))
    draw.rectangle((int(400 * 0.42), int(500 * 0.30), int(400 * 0.88), int(500 * 0.38)), fill=(90, 110, 130))
    qa = architecture_integrity_qa(src, mutated, source_asset_id=LOCKED_HERO_ASSET_ID)
    assert qa["architecture_integrity_status"] == "fail"
    assert qa["detected_mutation_regions"]
    other = Image.new("RGB", (400, 500), (210, 40, 40))
    ImageDraw.Draw(other).rectangle((40, 40, 360, 460), fill=(80, 90, 200))
    other_qa = architecture_integrity_qa(src, other, source_asset_id=LOCKED_HERO_ASSET_ID)
    assert other_qa["architecture_integrity_status"] == "fail"


def test_lock_restores_source_pixels_and_over_preserves_rather_than_redesign() -> None:
    src = _temple()
    mutated = _temple(spire_w=64, floors=5, cols=7)
    pack = lock_generated_creative(
        src,
        mutated,
        campaign_mode="project",
        source_asset_id=LOCKED_HERO_ASSET_ID,
    )
    assert pack["status"] == "pass"
    assert pack["skipped"] is False
    assert pack["changed"] is True
    qa = architecture_integrity_qa(src, pack["image"], source_asset_id=LOCKED_HERO_ASSET_ID)
    assert qa["architecture_integrity_status"] == "pass"
    mask = derive_architecture_mask(src)
    coverage = sum(1 for p in mask.resize((32, 32)).tobytes() if p > 40) / 1024
    assert coverage > 0.08


def test_tiny_or_flat_images_skip_lock_so_existing_phase5_tests_stay_green() -> None:
    tiny = Image.new("RGB", (64, 80), (10, 20, 30))
    pack = lock_generated_creative(tiny, tiny, campaign_mode="project", source_asset_id="x")
    assert pack["status"] == "skipped"
    assert PRODUCTION_COVER_V2
