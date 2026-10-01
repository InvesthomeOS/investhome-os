"""Quick Creative first-real-use production safety. No GPT Image. No artwork."""

from __future__ import annotations

import inspect
from types import SimpleNamespace

from PIL import Image

from investhome_api.services.creative_director.phase5_workflow import (
    REQUIRED_FACTS,
    _facts_from_request,
    generate_ad_phase5,
    revise_ad_phase5,
)
from investhome_api.services.creative_director.quick_creative_safety import (
    COMPOSITION_CHECK_KEYS,
    classify_quick_facts,
    composite_real_logo,
    detect_clipped_or_orphan_text,
    detect_template_fact_leakage,
    evaluate_quick_composition,
    quick_generation_prompt,
)
from investhome_api.services.creative_director.generate_ad import adapt_final_turkish_texts

TEMPLE_LIVE_REQUEST = (
    "The Temple için modern, prestijli ve yatırım odaklı bir Instagram reklamı hazırla. "
    "Gerçek proje görsellerini ve The Temple logosunu kullan. "
    "Tasarım sade ve premium görünsün. "
    "Herhangi bir fiyat veya finansal veri uydurma."
)


def test_live_request_does_not_inject_template_facts() -> None:
    project = SimpleNamespace(
        project_name="The Temple",
        city="Washington",
        state="DC",
        address="Massachusetts Ave",
        acquisition_price=9_999_999,
        total_units=48,
    )
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST, project=project)
    blob = " ".join(policy.facts.values())
    assert "675.000" not in blob
    assert "%35" not in blob
    assert "2+1" not in policy.facts.get("unit", "")
    assert not policy.user_provided.get("list_price")
    assert not policy.user_provided.get("discount")
    assert not policy.user_provided.get("unit")
    assert "9999999" not in str(policy.as_public_dict())
    assert "48" not in str(policy.verified)
    assert policy.verified["name"] == "The Temple"
    assert policy.verified["city"] == "Washington"


def test_negative_constraint_does_not_block_generation() -> None:
    from investhome_api.services.creative_director.quick_studio import _needs_missing_fact

    assert _needs_missing_fact(TEMPLE_LIVE_REQUEST) is False
    assert _needs_missing_fact("Herhangi bir fiyat uydurma.") is False
    assert _needs_missing_fact("Finansal veri kullanma.") is False
    assert _needs_missing_fact("Getiri oranı yazma.") is False
    assert _needs_missing_fact("Yatırım odaklı reklam hazırla.") is False
    assert _needs_missing_fact("Lansman avantajını anlat.") is False
    assert _needs_missing_fact("Fiyatı yaz.") is True
    assert _needs_missing_fact("Fiyatı 675.000 USD yaz.") is False
    assert _needs_missing_fact("%35 lansman avantajını yaz.") is False
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    assert not policy.facts["list_price"]
    assert not policy.facts["discount"]
    assert not policy.facts["unit"]


def test_user_provided_price_is_allowed() -> None:
    policy = classify_quick_facts(
        user_request="The Temple için reklam. Fiyatı 450.000 USD olarak yaz.",
        project=SimpleNamespace(project_name="The Temple", city="Washington", state=None, address=None),
    )
    assert "450" in policy.facts["list_price"]
    assert "USD" in policy.facts["list_price"]
    leaked = detect_template_fact_leakage(
        "450.000 USD",
        allowed=policy.allowed_commercial_tokens,
        user_request="Fiyatı 450.000 USD olarak yaz.",
    )
    assert "675.000" not in leaked
    assert all("450" not in token for token in leaked)


def test_template_leak_detector_flags_seed_facts() -> None:
    leaked = detect_template_fact_leakage(
        "675.000 USD  %35 LANSMAN AVANTAJI  2+1 DAİRE  ALIRKEN KAZAN",
        allowed=[],
        user_request=TEMPLE_LIVE_REQUEST,
    )
    assert "675.000" in leaked
    assert "%35" in leaked
    assert "2+1" in leaked
    assert "alirken kazan" in leaked


def test_truncation_detector_flags_alir_kaz() -> None:
    reasons = detect_clipped_or_orphan_text("ALIR KAZ...")
    assert "clipped_headline_fragment" in reasons
    assert "ellipsis_or_hyphen_clip" in reasons


def test_quick_prompt_does_not_instruct_template_facts() -> None:
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST, project=SimpleNamespace(project_name="UniLoft", city="Istanbul", state=None, address=None))
    prompt = quick_generation_prompt(
        user_request=TEMPLE_LIVE_REQUEST,
        policy=policy,
        target_format="instagram_feed_4:5",
    )
    assert "Paint ONLY these approved facts" not in prompt
    assert "Headline: ALIRKEN KAZAN" not in prompt
    assert "Price: 675.000" not in prompt
    assert "2+1 DAİRE" not in prompt
    assert "UNVERIFIED COMMERCIAL FACT" in prompt
    assert "IMAGE 1" in prompt
    assert "IMAGE 2" in prompt
    assert "art-direction reference" in prompt
    assert "ZERO factual authority" in prompt
    assert "DO NOT draw" in prompt
    assert "ALLOWED COPY PACKAGE" in prompt
    assert "8%" in prompt
    assert "SINGLE HERO PHOTO" in prompt
    assert "collage" in prompt.casefold()
    assert "bottom-left" in prompt.casefold()
    assert "investhome" in prompt.casefold()


def test_multi_photo_intent_is_opt_in_only() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import has_multi_photo_intent

    assert has_multi_photo_intent(TEMPLE_LIVE_REQUEST) is False
    assert has_multi_photo_intent("The Temple için modern, prestijli bir Instagram reklamı hazırla.") is False
    assert has_multi_photo_intent("Gerçek proje görsellerini kullan.") is False
    assert has_multi_photo_intent("İki farklı dış cephe görselini kullan.") is True
    assert has_multi_photo_intent("İç ve dış mekanı birlikte göster.") is True
    assert has_multi_photo_intent("Kolaj hazırla.") is True
    assert has_multi_photo_intent("3 proje görselini kullan.") is True


def test_hero_photo_count_detects_split_not_full_bleed() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import estimate_project_hero_photo_count

    def panel(size: tuple[int, int], a: tuple[int, int, int], b: tuple[int, int, int]) -> Image.Image:
        img = Image.new("RGB", size, a)
        px = img.load()
        for y in range(size[1]):
            for x in range(size[0]):
                if (x // 3 + y // 3) % 2:
                    px[x, y] = b
        return img

    split = Image.new("RGB", (400, 500), (40, 40, 40))
    left = panel((160, 460), (30, 30, 30), (230, 220, 200))
    right = panel((160, 460), (25, 28, 32), (200, 210, 230))
    split.paste(left, (8, 20))
    split.paste(right, (232, 20))
    assert estimate_project_hero_photo_count(split) == 2
    from investhome_api.services.creative_director.quick_creative_safety import resolve_project_hero_photo_count

    assert resolve_project_hero_photo_count(split, provenance_count=1, multi_photo_intent=False) == 2
    full = panel((400, 500), (30, 30, 30), (230, 220, 200))
    assert estimate_project_hero_photo_count(full) == 1


def _editorial_single_hero_canvas(size: tuple[int, int] = (400, 500)) -> Image.Image:
    """One photographic hero plus navy type territory and a gold footer. Not two photos."""
    w, h = size
    img = Image.new("RGB", size, (28, 30, 36))
    px = img.load()
    photo_h = int(h * 0.70)
    navy_h = int(h * 0.92)
    for y in range(photo_h):
        for x in range(w):
            if (x // 4 + y // 4) % 2:
                px[x, y] = (176, 154, 128)
            else:
                px[x, y] = (86, 68, 52)
    for y in range(photo_h, navy_h):
        for x in range(w):
            px[x, y] = (16, 26, 52)
    for y in range(navy_h, h):
        for x in range(w):
            px[x, y] = (196, 162, 88)
    return img


def test_editorial_graphic_regions_are_not_a_second_hero() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import (
        estimate_project_hero_photo_count,
        resolve_project_hero_photo_count,
    )

    canvas = _editorial_single_hero_canvas()
    assert estimate_project_hero_photo_count(canvas) == 1
    assert resolve_project_hero_photo_count(canvas, provenance_count=1, multi_photo_intent=False) == 1
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    pack = evaluate_quick_composition(
        canvas,
        policy=policy,
        user_request=TEMPLE_LIVE_REQUEST,
        logo_box={"x": 300, "y": 40, "w": 60, "h": 24},
        photo_valid=True,
        logo_valid=True,
        hero_photo_provenance=1,
    )
    assert pack["hero_photo_count"] == 1
    assert pack["checks"]["PROJECT_HERO_PHOTO_COUNT"] == "pass"


def test_single_hero_skips_default_second_photo_composite() -> None:
    from investhome_api.services.creative_director.project_architecture_lock import lock_architecture_pixels

    src = Image.new("RGB", (400, 500), (18, 18, 18))
    sp = src.load()
    for y in range(500):
        for x in range(400):
            if (x // 5 + y // 5) % 2:
                sp[x, y] = (210, 200, 180)
    cand = Image.new("RGB", (400, 500), (90, 90, 90))
    locked, meta = lock_architecture_pixels(src, cand, single_hero_photo=True)
    assert meta["placement"] == "skipped_second_photo_default"
    assert locked.tobytes() == cand.tobytes()
    pasted, meta2 = lock_architecture_pixels(src, cand, single_hero_photo=False)
    assert meta2["placement"] == "conservative_default_placement"
    assert pasted.tobytes() != cand.tobytes()


def test_non_quick_facts_still_use_required_defaults() -> None:
    facts = _facts_from_request("The Temple için reklam hazırla")
    assert facts["list_price"] == REQUIRED_FACTS["list_price"]
    assert facts["discount"] == REQUIRED_FACTS["discount"]
    assert facts["unit"] == REQUIRED_FACTS["unit"]


def test_quick_texts_do_not_invent_400k_fallbacks() -> None:
    texts = adapt_final_turkish_texts(
        language="tr",
        strategy={"big_idea": "Modern prestij"},
        campaign_copy={},
        pricing={},
        approved_claims=[],
        original_brief=TEMPLE_LIVE_REQUEST,
        invent_commercial_fallbacks=False,
    )
    blob = " ".join(str(v) for v in texts.values())
    assert "$400,000" not in blob
    assert "$300,000" not in blob
    assert "Unit 204" not in blob
    assert "~25%" not in blob
    assert "675.000" not in blob


def test_logo_composite_keeps_full_mark_and_proportions() -> None:
    canvas = Image.new("RGB", (800, 1000), (20, 20, 20))
    logo = Image.new("RGBA", (200, 80), (240, 220, 180, 255))
    out, box = composite_real_logo(canvas, logo)
    assert box["w"] > 0 and box["h"] > 0
    assert abs(box["w"] / box["h"] - 200 / 80) < 0.02
    assert box["x"] >= 0 and box["y"] >= 0
    assert box["x"] + box["w"] <= out.width
    assert box["y"] + box["h"] <= out.height


def test_composition_gate_has_required_checks() -> None:
    canvas = Image.new("RGB", (400, 500), (10, 10, 10))
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    pack = evaluate_quick_composition(
        canvas,
        policy=policy,
        user_request=TEMPLE_LIVE_REQUEST,
        logo_box={"x": 300, "y": 40, "w": 60, "h": 24},
        photo_valid=True,
        logo_valid=True,
    )
    for key in COMPOSITION_CHECK_KEYS:
        assert key in pack["checks"]
    assert "PROJECT_HERO_PHOTO_COUNT" in pack["checks"]
    from investhome_api.services.creative_director.quick_creative_safety import OCR_DEPENDENT_CHECKS

    if not pack.get("ocr_executed"):
        for key in OCR_DEPENDENT_CHECKS:
            assert pack["checks"][key] == "unverified"
            assert pack["checks"][key] != "pass"
        assert set(OCR_DEPENDENT_CHECKS).issubset(set(pack.get("unverified") or []))
    leaked = detect_template_fact_leakage(
        "ALIR KAZ 675.000",
        allowed=[],
        user_request=TEMPLE_LIVE_REQUEST,
    )
    assert leaked
    reasons = detect_clipped_or_orphan_text("ALIR KAZ...")
    assert reasons
    pack["checks"]["NO_TEMPLATE_FACT_LEAKAGE"] = "fail"
    pack["failed"] = ["NO_TEMPLATE_FACT_LEAKAGE"]
    pack["status"] = "fail"
    assert pack["status"] == "fail"


def test_quick_generate_uses_safety_not_required_facts() -> None:
    source = inspect.getsource(generate_ad_phase5)
    assert "classify_quick_facts" in source
    assert "quick_generation_prompt" in source
    assert "_finalize_quick_creative" in source
    assert "should_auto_retry_quick_composition" in source
    assert "describe_recoverable_composition_failure" in source
    assert "quick_composition_user_message" in source
    assert "QUICK_COMPOSITION_MAX_ATTEMPTS" in source
    from investhome_api.services.creative_director import phase5_workflow as p5

    flags = inspect.getsource(p5._quick_builder_flags)
    assert "skip_design_references" in flags
    assert "attach_design_reference" in flags
    assert "skip_logo_edit_input" in flags
    assert "skip_project_logo" in flags
    assert "skip_investhome_logo" in flags
    assert "gpt_image_quality" in flags
    assert "single_hero_photo" in flags
    assert "multi_photo_intent" in flags
    rev = inspect.getsource(revise_ad_phase5)
    assert "quick_revision_prompt" in rev
    assert "classify_quick_facts" in rev


def test_gpt_image_attaches_one_design_reference_for_quick() -> None:
    from investhome_api.services.gpt_image_design import service as gpt_service
    from investhome_api.services.gpt_image_design.source import load_design_reference_image, resolve_project_inputs

    src = inspect.getsource(gpt_service._generate_project)
    assert "attach_design_reference" in src
    assert "image2-design-reference.png" in src
    assert "load_design_reference_image" in src
    assert "QUICK_NO_DESIGN_REFERENCE_MESSAGE" in src
    assert "skip_logo_input = True" in src
    signature = inspect.signature(resolve_project_inputs)
    assert "skip_design_references" in signature.parameters
    assert "skip_investhome_logo" in signature.parameters
    assert inspect.signature(load_design_reference_image)


def test_quick_studio_still_isolated_from_premium() -> None:
    import investhome_api.services.creative_director.quick_studio as qs

    source = inspect.getsource(qs)
    assert "premium_studio" not in source
    assert "phase12_3_family_ingest" not in source
    assert "generate_ad_phase5" in source


def test_reference_selection_uses_grade_a_not_orneK_00001() -> None:
    from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA
    from investhome_api.services.creative_director.quick_creative_safety import (
        classify_quick_reference_style,
        select_quick_design_reference,
    )

    live = select_quick_design_reference(TEMPLE_LIVE_REQUEST)
    assert classify_quick_reference_style(TEMPLE_LIVE_REQUEST) == "editorial"
    assert live["filename"] == "ORNEK_00013.jpg"
    assert live["asset_id"] == GRADE_A_MEDIA["ORNEK_00013.jpg"]
    assert live["filename"] != "ORNEK_00001.jpg"
    assert select_quick_design_reference("Konuma yakınlığını anlat.")["filename"] == "ORNEK_00011.jpg"
    assert select_quick_design_reference("İç mekan lifestyle reklamı hazırla.")["filename"] == "ORNEK_00015.jpg"
    assert select_quick_design_reference("Dusk launch teslim kampanyası.")["filename"] == "ORNEK_00008.jpg"


def test_quick_input_contract_is_reference_guided() -> None:
    from investhome_api.services.creative_director.phase5_workflow import _quick_builder_flags
    from investhome_api.services.creative_director.quick_creative_safety import (
        QUICK_PRODUCTION_QUALITY,
        grade_a_design_reference_ids,
        quick_generation_input_contract,
    )

    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    flags = _quick_builder_flags(policy, TEMPLE_LIVE_REQUEST)
    contract = quick_generation_input_contract(flags)
    assert contract["PROJECT_PHOTO_INPUT"] == 1
    assert contract["DESIGN_REFERENCE_VISUAL_INPUT"] == 1
    assert contract["PROJECT_LOGO_GENERATION_INPUT"] == 0
    assert contract["INVESTHOME_LOGO_GENERATION_INPUT"] == 0
    assert contract["REAL_LOGO_POST_COMPOSITE"] == 1
    assert contract["INVESTHOME_LOGO_POST_COMPOSITE"] == 1
    assert contract["REFERENCE_FACT_AUTHORITY"] == 0
    assert contract["REFERENCE_ARCHITECTURE_AUTHORITY"] == 0
    assert contract["FACT_SAFETY"] == "ACTIVE"
    assert contract["SINGLE_HERO_RULE"] == "ACTIVE"
    assert contract["IMAGE_QUALITY_MODE"] == QUICK_PRODUCTION_QUALITY == "high"
    assert contract["unguided_fallback"] is False
    assert flags["skip_logo_edit_input"] is True
    assert flags["skip_project_logo"] is True
    assert flags["skip_investhome_logo"] is True
    assert flags["attach_design_reference"] is True
    assert flags["design_reference_asset_id"] in grade_a_design_reference_ids()
    revision = quick_generation_input_contract({**flags, "revision_mode": True})
    assert revision["DESIGN_REFERENCE_VISUAL_INPUT"] == 0


def test_reference_fact_leak_and_duplicate_logo_fail_closed() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import (
        detect_duplicate_project_logo,
        detect_reference_fact_leakage,
    )

    leaked = detect_reference_fact_leakage(
        "UNILOFT  $357.000  DÜZENLİ. GÜVENLİ.",
        allowed=[],
        user_request=TEMPLE_LIVE_REQUEST,
    )
    assert "uniloft" in leaked
    assert "357.000" in leaked or "$357" in leaked
    assert "duzenli" in leaked or "düzenli" in leaked
    clean = detect_reference_fact_leakage(
        "The Temple Washington DC",
        allowed=["The Temple", "Washington"],
        user_request=TEMPLE_LIVE_REQUEST,
    )
    assert clean == []
    logo_box = {"x": 320, "y": 20, "w": 60, "h": 24}
    count = detect_duplicate_project_logo(
        [("Temple", 330, 24, 40, 16)],
        project_name="The Temple",
        logo_box=logo_box,
        canvas_size=(400, 500),
    )
    assert count == 1
    dup = detect_duplicate_project_logo(
        [("Temple", 330, 24, 40, 16), ("Temple", 350, 8, 30, 14)],
        project_name="The Temple",
        logo_box=logo_box,
        canvas_size=(400, 500),
    )
    assert dup >= 2


def test_supported_quality_includes_high() -> None:
    from investhome_api.services.gpt_image_design.config import resolve_quality

    assert resolve_quality("high") == "high"
    assert resolve_quality("medium") == "medium"
    source = inspect.getsource(__import__("investhome_api.services.gpt_image_design.service", fromlist=["_generate_project"])._generate_project)
    assert "resolve_quality" in source
    assert "gpt_image_quality" in source


def test_dark_background_uses_approved_white_logo_variant() -> None:
    canvas = Image.new("RGB", (800, 1000), (16, 16, 18))
    primary = Image.new("RGBA", (200, 80), (48, 36, 18, 255))
    white = Image.new("RGBA", (200, 80), (255, 255, 255, 255))
    _out, box = composite_real_logo(canvas, primary, variants={"white": white})
    assert box["variant"] == "white"
    assert box["contrast"] >= 3.0
    pixel = _out.getpixel((box["x"] + box["w"] // 2, box["y"] + box["h"] // 2))
    assert pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200


def test_light_background_does_not_use_white_logo_variant() -> None:
    canvas = Image.new("RGB", (800, 1000), (240, 236, 228))
    primary = Image.new("RGBA", (200, 80), (48, 36, 18, 255))
    white = Image.new("RGBA", (200, 80), (255, 255, 255, 255))
    _out, box = composite_real_logo(canvas, primary, variants={"white": white, "black": primary})
    assert box["variant"] in {"black", "primary"}
    assert box["variant"] != "white"
    assert box["contrast"] >= 3.0


def test_brand_closure_is_smaller_and_lower_than_project_logo() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import composite_brand_closure_logo

    canvas = Image.new("RGB", (800, 1000), (22, 22, 24))
    project = Image.new("RGBA", (200, 80), (255, 255, 255, 255))
    brand = Image.new("RGBA", (400, 90), (210, 170, 90, 255))
    out, project_box = composite_real_logo(canvas, project)
    _out, brand_box = composite_brand_closure_logo(out, brand, avoid_box=project_box)
    assert brand_box["w"] < project_box["w"]
    assert brand_box["h"] <= project_box["h"]
    assert brand_box["y"] > project_box["y"] + project_box["h"]
    assert brand_box["x"] + brand_box["w"] < project_box["x"]
    assert brand_box["contrast"] >= 3.0


def test_brand_logo_uses_backing_plate_when_natural_contrast_fails() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import (
        MIN_LOGO_CONTRAST,
        composite_brand_closure_logo,
    )

    assert MIN_LOGO_CONTRAST == 3.0
    canvas = Image.new("RGB", (800, 1000), (196, 162, 88))
    px = canvas.load()
    for y in range(1000):
        for x in range(800):
            if (x // 5 + y // 5) % 2:
                px[x, y] = (186, 150, 78)
    gold = (210, 170, 90, 255)
    brand = Image.new("RGBA", (400, 90), gold)
    out, box = composite_brand_closure_logo(canvas, brand)
    assert box["contrast"] >= MIN_LOGO_CONTRAST
    assert box["plate"] is True
    ink = out.getpixel((box["x"] + box["w"] // 2, box["y"] + box["h"] // 2))
    assert ink[0] > 150 and ink[1] > 120 and ink[2] < 140
    assert not (ink[0] > 240 and ink[1] > 240 and ink[2] > 240)
    pad_x = max(0, box["x"] - 2)
    plate_px = out.getpixel((pad_x, box["y"]))
    assert plate_px[0] < 40 and plate_px[1] < 40 and plate_px[2] < 40


def test_production_pass_composites_project_and_investhome() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import apply_quick_production_pass

    canvas = Image.new("RGB", (800, 1000), (18, 18, 20))
    project = Image.new("RGBA", (200, 80), (255, 255, 255, 255))
    brand = Image.new("RGBA", (400, 100), (220, 175, 95, 255))
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    pack = apply_quick_production_pass(
        canvas,
        project,
        policy=policy,
        user_request=TEMPLE_LIVE_REQUEST,
        photo_valid=True,
        project_logo_variants={"primary": project, "white": project},
        brand_logo=brand,
        brand_logo_variants={"primary": brand},
    )
    assert pack["project_logo_count"] == 1
    assert pack["investhome_logo_count"] == 1
    assert pack["checks"]["PROJECT_LOGO_COUNT"] == "pass"
    assert pack["checks"]["INVESTHOME_LOGO_COUNT"] == "pass"
    assert pack["checks"]["PROJECT_LOGO_VISIBILITY"] == "pass"
    assert pack["checks"]["BRAND_LOGO_VISIBILITY"] == "pass"
    assert pack["brand_logo_box"]["w"] < pack["logo_box"]["w"]
    assert pack["brand_logo_box"]["y"] > pack["logo_box"]["y"] + pack["logo_box"]["h"]


def test_approved_logo_variant_classifier_rejects_unapproved_marks() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import classify_approved_logo_variant

    assert classify_approved_logo_variant("IH_DC_TMP_001_Logo_White.svg") == "white"
    assert classify_approved_logo_variant("IH_DC_TMP_001_Logo_Black.svg") == "black"
    assert classify_approved_logo_variant("IH_DC_TMP_001_Logo_Primary.svg") == "primary"
    assert classify_approved_logo_variant("Investhome_Logo_Primary.png", ["logo", "primary", "investhome"]) == "primary"
    assert classify_approved_logo_variant("IH_DC_TMP_001_Logo_Addition.svg") is None
    assert classify_approved_logo_variant("IH_DC_TMP_001_Logo_Historic.svg") is None


def test_recoverable_composition_failures_retry_once_with_concrete_guidance() -> None:
    from investhome_api.services.creative_director.quick_creative_safety import (
        QUICK_COMPOSITION_FAIL_MESSAGE,
        QUICK_COMPOSITION_MAX_ATTEMPTS,
        QUICK_COMPOSITION_RETRY_FAIL_MESSAGE,
        describe_recoverable_composition_failure,
        is_recoverable_composition_failure,
        quick_composition_user_message,
        quick_generation_prompt,
        should_auto_retry_quick_composition,
    )

    assert QUICK_COMPOSITION_MAX_ATTEMPTS == 2
    clip_pack = {"failed": ["TEXT_WITHIN_SAFE_BOUNDS", "NO_ORPHAN_TEXT"]}
    overlap_pack = {"failed": ["NO_CRITICAL_TEXT_OVERLAP", "AI_GENERATED_LOGO_COUNT"]}
    fact_pack = {"failed": ["NO_TEMPLATE_FACT_LEAKAGE"]}
    mixed_pack = {"failed": ["TEXT_WITHIN_SAFE_BOUNDS", "NO_TEMPLATE_FACT_LEAKAGE"]}
    missing_logo = {"failed": ["PROJECT_LOGO_VALID", "LOGO_VISIBLE"]}
    missing_photo = {"failed": ["PROJECT_PHOTO_VALID"]}
    brand_only = {"failed": ["BRAND_LOGO_VISIBILITY"]}
    brand_count_only = {"failed": ["INVESTHOME_LOGO_COUNT"]}
    generative_and_brand = {"failed": ["TEXT_WITHIN_SAFE_BOUNDS", "BRAND_LOGO_VISIBILITY"]}
    assert is_recoverable_composition_failure(clip_pack) is True
    assert is_recoverable_composition_failure(overlap_pack) is True
    assert is_recoverable_composition_failure(fact_pack) is False
    assert is_recoverable_composition_failure(mixed_pack) is False
    assert is_recoverable_composition_failure(missing_logo) is False
    assert is_recoverable_composition_failure(missing_photo) is False
    assert is_recoverable_composition_failure(brand_only) is False
    assert is_recoverable_composition_failure(brand_count_only) is False
    assert is_recoverable_composition_failure(generative_and_brand) is True
    assert should_auto_retry_quick_composition(clip_pack, attempt_index=0) is True
    assert should_auto_retry_quick_composition(clip_pack, attempt_index=1) is False
    assert should_auto_retry_quick_composition(fact_pack, attempt_index=0) is False
    assert should_auto_retry_quick_composition(brand_only, attempt_index=0) is False
    guidance = describe_recoverable_composition_failure(clip_pack)
    assert "safe bounds" in guidance
    assert "clipped" in guidance or "incomplete" in guidance
    assert "fresh composition" in guidance
    policy = classify_quick_facts(user_request=TEMPLE_LIVE_REQUEST)
    retry_prompt = quick_generation_prompt(
        user_request=TEMPLE_LIVE_REQUEST,
        policy=policy,
        target_format="instagram_feed_4:5",
        retry=True,
        retry_guidance=guidance,
    )
    assert guidance in retry_prompt
    assert "FRESH" in retry_prompt
    assert "Do not patch" in retry_prompt
    assert "IMAGE 1" in retry_prompt
    assert "IMAGE 2" in retry_prompt
    assert "candidate 1" not in retry_prompt.casefold()
    assert "candidate 2" not in retry_prompt.casefold()
    assert quick_composition_user_message(retried=False) == QUICK_COMPOSITION_FAIL_MESSAGE
    assert quick_composition_user_message(retried=True) == QUICK_COMPOSITION_RETRY_FAIL_MESSAGE
    assert "Yeniden üretmeyi deneyin" in QUICK_COMPOSITION_RETRY_FAIL_MESSAGE
    generate_src = inspect.getsource(generate_ad_phase5)
    assert "retry_guidance" in generate_src
    assert "selected_asset_ids=[interior_id]" in generate_src
    assert generate_src.count("should_auto_retry_quick_composition") >= 1
    assert "QUICK_COMPOSITION_MAX_ATTEMPTS" in generate_src
    rev_src = inspect.getsource(revise_ad_phase5)
    assert "should_auto_retry_quick_composition" in rev_src
    assert "retry_guidance" in rev_src
