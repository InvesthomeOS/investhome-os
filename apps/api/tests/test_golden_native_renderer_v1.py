"""Golden Native Renderer v1 POC — 4 real layers, GPT Image = 0."""

from __future__ import annotations

from investhome_api.schemas.creative_director import CreativeDirectorGenerateAdRequest
from investhome_api.services.creative_director.design_spec import (
    GOLDEN_NATIVE_V1_LAYER_IDS,
    analyze_native_photograph,
    apply_layer_operations,
    build_golden_native_v1_spec,
    design_spec_to_smb_elements,
    project_golden_native_structured_data,
    route_revision,
)
from investhome_api.services.creative_director.generate_ad import _resolve_production_mode
from investhome_api.services.creative_director.revision_intelligence import (
    interpret_revision_plan,
    snapshot_elements,
)


BG = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
LOGO = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"


def _brief() -> dict:
    return {
        "campaign_intent": "lifestyle",
        "hero": "Tarihi karakter, modern yaşam",
        "cta": "The Temple'ı Keşfet",
        "final_copy": {
            "headline": "Tarihi karakter, modern yaşam",
            "cta": "The Temple'ı Keşfet",
        },
        "design_direction": {"visual_mood": "editorial", "hierarchy": "headline_first"},
    }


def _texts() -> dict[str, str]:
    return {
        "headline": "Tarihi karakter, modern yaşam",
        "cta": "The Temple'ı Keşfet",
    }


def _spec() -> dict:
    return build_golden_native_v1_spec(
        production_brief=_brief(),
        texts=_texts(),
        master_background_asset_id=BG,
        logo_asset_id=LOGO,
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="lifestyle",
    )


def test_default_production_mode_stays_finished_ad():
    body = CreativeDirectorGenerateAdRequest()
    assert body.production_mode == "finished_ad"
    assert _resolve_production_mode(body) == "finished_ad"
    native = CreativeDirectorGenerateAdRequest(production_mode="golden_native_v1")
    assert _resolve_production_mode(native) == "golden_native_v1"


def test_native_spec_has_exactly_four_real_layers():
    spec = _spec()
    ids = [el["id"] for el in spec["elements"] if isinstance(el, dict)]
    assert tuple(ids) == GOLDEN_NATIVE_V1_LAYER_IDS
    types = {el["id"]: el["type"] for el in spec["elements"]}
    assert types["master_background"] == "image"
    assert types["logo"] == "logo"
    assert types["headline"] == "text"
    assert types["cta"] == "cta"
    forbidden = {"gradient", "overlay", "badge", "shape", "icon"}
    assert not {el["type"] for el in spec["elements"]} & forbidden
    support_ids = {el["id"] for el in spec["elements"]}
    assert "support-message-1" not in support_ids
    assert spec["mode"] == "golden_native_v1"
    assert spec["master_background_asset_id"] == BG
    assert spec["logo_asset_id"] == LOGO
    assert spec["elements"][0]["asset_id"] == BG
    headline = next(el for el in spec["elements"] if el["id"] == "headline")
    logo = next(el for el in spec["elements"] if el["id"] == "logo")
    cta = next(el for el in spec["elements"] if el["id"] == "cta")
    assert headline["asset_id"] != BG if "asset_id" in headline else True
    assert logo["asset_id"] == LOGO
    assert logo["asset_id"] != BG
    assert cta.get("type") == "cta"
    assert spec["creative_director_recipe"]["headline"]["color"]
    assert spec["creative_director_recipe"]["background_asset_id"] == BG


def test_native_layers_are_not_baked_into_background():
    spec = _spec()
    bg = next(el for el in spec["elements"] if el["id"] == "master_background")
    headline = next(el for el in spec["elements"] if el["id"] == "headline")
    logo = next(el for el in spec["elements"] if el["id"] == "logo")
    cta = next(el for el in spec["elements"] if el["id"] == "cta")
    assert bg["type"] == "image"
    assert headline["type"] == "text"
    assert "Tarihi karakter" in str(headline.get("content") or "")
    assert logo["type"] == "logo"
    assert cta["type"] == "cta"
    smb = design_spec_to_smb_elements(spec)
    kinds = {el["id"]: el["type"] for el in smb}
    assert kinds["master_background"] == "IMAGE"
    assert kinds["headline"] == "TEXT"
    assert kinds["logo"] == "IMAGE"
    assert kinds["cta"] == "BUTTON"


def test_native_structured_projection_four_slots():
    spec = _spec()
    data = project_golden_native_structured_data(spec, production_brief=_brief())
    assert data["mode"] == "golden_native_v1"
    assert data["visual_source_of_truth"] == "native_layers"
    assert data["rebuild_from_layers"] is True
    present = set(data["present_slots"])
    assert present >= {"background", "project-logo", "headline", "cta-primary"}
    assert data["missing_slots"] == []


def test_native_headline_logo_cta_are_micro_edit():
    spec = _spec()
    for instruction in (
        "Başlığı Zamansız Bir Yaşam yap.",
        "Logoyu %20 küçült.",
        "CTA'yı kaldır.",
    ):
        plan = interpret_revision_plan(instruction=instruction, design_spec=spec)
        assert (
            route_revision(
                instruction=instruction,
                revision_diff=plan,
                has_structured_design=True,
            )
            == "MICRO_EDIT"
        )


def test_native_headline_replace_mutates_text_layer_only():
    spec = _spec()
    plan = interpret_revision_plan(
        instruction="Başlığı Zamansız Bir Yaşam yap.",
        design_spec=spec,
    )
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    headline = next(el for el in after["elements"] if el["id"] == "headline")
    assert "Zamansız Bir Yaşam" in str(headline.get("content") or "")
    assert "Tarihi karakter" not in str(headline.get("content") or "")
    bg = next(el for el in after["elements"] if el["id"] == "master_background")
    assert bg["asset_id"] == BG
    logo = next(el for el in after["elements"] if el["id"] == "logo")
    assert logo["width"] == before["logo"]["width"]
    smb = design_spec_to_smb_elements(after)
    texts = [el for el in smb if el.get("type") == "TEXT"]
    assert len(texts) == 1
    assert "Zamansız Bir Yaşam" in str(texts[0].get("content") or "")


def test_native_logo_scale_keeps_single_logo():
    spec = _spec()
    plan = interpret_revision_plan(instruction="Logoyu %20 küçült.", design_spec=spec)
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    logos = [el for el in after["elements"] if el.get("id") == "logo"]
    assert len(logos) == 1
    assert logos[0].get("visible") is not False
    assert logos[0]["width"] < before["logo"]["width"]
    assert logos[0]["height"] < before["logo"]["height"]
    bg = next(el for el in after["elements"] if el["id"] == "master_background")
    assert bg["asset_id"] == BG


def test_native_cta_hide_drops_cta_from_smb_layers():
    spec = _spec()
    plan = interpret_revision_plan(instruction="CTA'yı kaldır.", design_spec=spec)
    after = apply_layer_operations(spec, plan.operations)
    cta = next(el for el in after["elements"] if el["id"] == "cta")
    assert cta.get("visible") is False
    smb = design_spec_to_smb_elements(after)
    ids = {el.get("id") for el in smb}
    assert "cta" not in ids
    assert "headline" in ids
    assert "logo" in ids
    assert "master_background" in ids
    bg = next(el for el in after["elements"] if el["id"] == "master_background")
    assert bg["asset_id"] == BG


def _png_bytes(image) -> bytes:
    from io import BytesIO

    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _bright_interior_png(width: int = 1080, height: int = 1350) -> bytes:
    from PIL import Image, ImageDraw

    im = Image.new("RGB", (width, height), (236, 228, 216))
    d = ImageDraw.Draw(im)
    d.rectangle([int(width * 0.24), 0, int(width * 0.76), int(height * 0.42)], fill=(248, 246, 240))
    d.rectangle(
        [int(width * 0.18), int(height * 0.40), int(width * 0.82), int(height * 0.74)],
        fill=(92, 78, 64),
        outline=(28, 22, 16),
        width=10,
    )
    d.rectangle(
        [int(width * 0.34), int(height * 0.48), int(width * 0.66), int(height * 0.62)],
        outline=(18, 14, 10),
        width=8,
    )
    d.rectangle([0, int(height * 0.78), width, height], fill=(46, 34, 26))
    return _png_bytes(im)


def test_native_art_direction_v2_reads_photograph_not_template():
    photo = _bright_interior_png()
    spec = build_golden_native_v1_spec(
        production_brief=_brief(),
        texts=_texts(),
        master_background_asset_id=BG,
        logo_asset_id=LOGO,
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="lifestyle",
        image_bytes=photo,
    )
    canvas = spec["canvas"]
    width, height = int(canvas["width"]), int(canvas["height"])
    headline = next(el for el in spec["elements"] if el["id"] == "headline")
    logo = next(el for el in spec["elements"] if el["id"] == "logo")
    cta = next(el for el in spec["elements"] if el["id"] == "cta")
    analysis = spec["image_analysis"]
    recipe = spec["creative_director_recipe"]

    assert spec["art_direction"] == "v2_image_aware"
    assert analysis["available"] is True
    assert analysis["do_not_cover"]
    assert headline["x"] < width * 0.18
    assert headline["width"] < width * 0.62
    assert headline["typography"]["align"] == "left"
    assert "\n" in str(headline["content"])
    assert headline["typography"]["letter_spacing"] is not None
    assert headline["typography"]["line_height"] <= 1.16
    assert logo["x"] > width * 0.55
    assert logo["width"] < width * 0.16
    assert cta["x"] == headline["x"] or abs(cta["x"] - headline["x"]) <= 8
    assert cta["width"] < width * 0.42
    assert cta["style"]["background_color"] == "transparent"
    assert cta["style"]["cta_style"] == "MINIMAL_BUTTON"
    assert cta["style"]["text_color"] == "#C4A35A"
    assert str(cta["content"]).endswith("→")
    assert recipe["cta"]["style"] == "minimal_outlined"
    smb = design_spec_to_smb_elements(spec)
    cta_smb = next(el for el in smb if el["id"] == "cta")
    assert cta_smb["ctaStyle"] == "MINIMAL_BUTTON"
    assert cta_smb["backgroundColor"] == "transparent"
    headline_smb = next(el for el in smb if el["id"] == "headline")
    assert headline_smb["letterSpacing"] is not None
    ids = [el["id"] for el in spec["elements"]]
    assert tuple(ids) == GOLDEN_NATIVE_V1_LAYER_IDS
    assert not {el["type"] for el in spec["elements"]} & {"gradient", "overlay", "shape"}


def test_native_honors_explicit_image_analysis_zones():
    analysis = {
        "available": True,
        "safe_headline_zone": {"x": 0.07, "y": 0.62, "width": 0.50, "height": 0.24},
        "safe_logo_zone": {"x": 0.72, "y": 0.04, "width": 0.20, "height": 0.08},
        "safe_cta_zone": {"x": 0.07, "y": 0.88, "width": 0.34, "height": 0.05},
        "headline_ink": "#F4EFE6",
        "headline_align": "left",
        "headline_family": "serif",
        "headline_zone_name": "lower_left",
        "do_not_cover": [
            {"role": "furniture_building_focal", "x": 0.2, "y": 0.3, "width": 0.6, "height": 0.35}
        ],
    }
    spec = build_golden_native_v1_spec(
        production_brief=_brief(),
        texts=_texts(),
        master_background_asset_id=BG,
        logo_asset_id=LOGO,
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        image_analysis=analysis,
    )
    headline = next(el for el in spec["elements"] if el["id"] == "headline")
    assert headline["y"] > 700
    assert headline["typography"]["color"] == "#F4EFE6"
    assert headline["typography"]["align"] == "left"
    assert spec["image_analysis"]["headline_zone_name"] == "lower_left"


def test_analyze_native_photograph_marks_view_and_furniture():
    photo = _bright_interior_png()
    analysis = analyze_native_photograph(photo, canvas_width=1080, canvas_height=1350)
    assert analysis["available"] is True
    roles = {row.get("role") for row in analysis["do_not_cover"]}
    assert "furniture_building_focal" in roles
    assert analysis["safe_headline_zone"]["x"] < 0.2
    assert analysis["headline_align"] == "left"