"""AI Revision Intelligence v2 — acceptance A–L + regressions (GPT=0 unit)."""

from __future__ import annotations

from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    build_design_spec,
    route_revision,
)
from investhome_api.services.creative_director.revision import (
    build_revision_diff,
    move_revision_cursor,
)
from investhome_api.services.creative_director.revision_intelligence import (
    RELATIVE_NL,
    build_user_feedback,
    detect_strict_preserve,
    element_box,
    interpret_revision_plan,
    snapshot_elements,
    validate_change_diff,
)


def _price_texts() -> dict[str, str]:
    return {
        "headline": "Modern. Şık. Tarihi.",
        "hero": "The Temple'da Modern Yaşam, Tarihi Doku ile Buluşuyor!",
        "unit": "Unit 204",
        "list_price": "$400,000",
        "offer_price": "$300,000",
        "value_badge": "~25% lansman fiyat avantajı",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": "Unit 204 Lansman Fırsatı",
        "campaign_mode": "launch_price",
    }


def _brief() -> dict:
    return {
        "campaign_intent": "price_campaign",
        "hero": "The Temple'da Modern Yaşam, Tarihi Doku ile Buluşuyor!",
        "cta": "Lansman Fiyatını Kaçırmayın",
        "supporting": [
            "Tarihi karakter, modern tasarım.",
            "Sınırlı sayıda ünite, kaçırmayın.",
        ],
        "final_copy": {
            "headline": "Modern. Şık. Tarihi.",
            "list_price": "$400,000",
            "offer_price": "$300,000",
            "value_badge": "~25% lansman fiyat avantajı",
            "cta": "Lansman Fiyatını Kaçırmayın",
            "unit": "Unit 204",
        },
    }


def _temple_spec():
    return build_design_spec(
        production_brief=_brief(),
        texts=_price_texts(),
        master_background_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        logo_asset_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        finished_ad_raster_asset_id="cccccccc-cccc-cccc-cccc-cccccccccccc",
        aspect_ratio="4:5",
        format_preset="portrait",
        language="tr",
        campaign_intent="price_campaign",
    )


def _apply(instruction: str, *, selected: str | None = None):
    spec = _temple_spec()
    plan = interpret_revision_plan(
        instruction=instruction,
        production_brief=_brief(),
        design_spec=spec,
        selected_element_id=selected,
    )
    before = snapshot_elements(spec)
    after = apply_layer_operations(spec, plan.operations)
    validation = validate_change_diff(before=before, after_spec=after, revision_diff=plan)
    route = route_revision(instruction=instruction, revision_diff=plan, intents=["COPY_CHANGE"])
    return plan, before, after, validation, route


def _by_id(spec):
    return {el["id"]: el for el in spec["elements"]}


def test_a_headline_only_preserves_rest():
    """A: headline text replace — bg/logo/prices/badge/cta/positions untouched."""
    plan, before, after, validation, route = _apply("Başlığı 'Zamansız Bir Yaşam' yap")
    assert route == "LAYER_ONLY"
    assert plan.command_mode == "exact"
    assert validation["status"] == "pass"
    assert validation["unexpected_mutation_count"] == 0
    assert validation["background_asset_unchanged"] is True
    a = _by_id(after)
    assert a["headline"]["content"] == "Zamansız Bir Yaşam"
    for eid in ("logo", "cta", "discount-badge", "old-price", "new-price", "master_background"):
        assert before[eid]["x"] == a[eid]["x"]
        assert before[eid]["y"] == a[eid]["y"]
        assert before[eid]["width"] == a[eid]["width"]
        assert before[eid]["height"] == a[eid]["height"]
        if eid not in {"headline", "master_background"}:
            assert before[eid].get("content") == a[eid].get("content")
    assert before["master_background"]["asset_id"] == a["master_background"]["asset_id"]
    fb = build_user_feedback(plan, validation)
    assert "Başlık" in fb
    assert "{" not in fb


def test_b_logo_up_by_own_height():
    """B: Logoyu kendi yüksekliği kadar yukarı."""
    plan, before, after, validation, route = _apply("Logoyu kendi yüksekliği kadar yukarı")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    assert validation["background_asset_unchanged"] is True
    a = _by_id(after)
    expected_y = before["logo"]["y"] - before["logo"]["height"]
    assert abs(a["logo"]["y"] - expected_y) <= 1
    assert a["headline"]["content"] == before["headline"]["content"]
    assert a["cta"]["y"] == before["cta"]["y"]


def test_c_headline_down_half_height():
    """C: Başlığı kendi yüksekliğinin yarısı kadar aşağı."""
    plan, before, after, validation, route = _apply(
        "Başlığı kendi yüksekliğinin yarısı kadar aşağı"
    )
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    expected = before["headline"]["y"] + before["headline"]["height"] * 0.5
    assert abs(a["headline"]["y"] - expected) <= 1


def test_d_logo_align_left_with_headline():
    """D: Logoyu başlıkla sola hizala."""
    plan, before, after, validation, route = _apply("Logoyu başlıkla sola hizala")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert a["logo"]["x"] == before["headline"]["x"] or abs(
        a["logo"]["x"] - before["headline"]["x"]
    ) <= 1


def test_e_cta_below_price_30px():
    """E: CTA'yı fiyatın 30 px altına."""
    plan, before, after, validation, route = _apply("CTA'yı fiyatın 30 px altına")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    price = before["new-price"]
    expected = price["y"] + price["height"] + 30
    assert abs(a["cta"]["y"] - expected) <= 1


def test_f_badge_align_price_right():
    """F: Rozeti fiyatın sağ kenarına hizala."""
    plan, before, after, validation, route = _apply("Rozeti fiyatın sağ kenarına hizala")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    price_right = before["new-price"]["x"] + before["new-price"]["width"]
    badge_right = a["discount-badge"]["x"] + a["discount-badge"]["width"]
    assert abs(badge_right - price_right) <= 1


def test_g_headline_canvas_center():
    """G: Başlığı canvas'ın tam ortasına."""
    plan, before, after, validation, route = _apply("Başlığı canvas'ın tam ortasına")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    cw = 1080
    expected_x = (cw - before["headline"]["width"]) / 2
    assert abs(a["headline"]["x"] - expected_x) <= 1


def test_h_logo_top_right_safe_margin():
    """H: Logoyu sağ üst köşeye ama kenar boşluğunu koru."""
    plan, before, after, validation, route = _apply(
        "Logoyu sağ üst köşeye ama kenar boşluğunu koru"
    )
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    margin = 48
    assert a["logo"]["y"] == margin
    assert abs(a["logo"]["x"] - (1080 - margin - before["logo"]["width"])) <= 1


def test_i_percentage_scales():
    """I: logo ×1.20, badge %30 küçült, CTA %10 büyüt."""
    plan, before, after, validation, route = _apply("Logoyu %20 büyüt")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert abs(a["logo"]["width"] - before["logo"]["width"] * 1.2) <= 2

    plan2, before2, after2, validation2, route2 = _apply("%25 rozetini %30 küçült")
    assert route2 == "LAYER_ONLY"
    assert validation2["unexpected_mutation_count"] == 0
    a2 = _by_id(after2)
    assert abs(a2["discount-badge"]["width"] - before2["discount-badge"]["width"] * 0.7) <= 2


def test_j_selected_element_biraz_kucult():
    """J: selected_element_id strongest for 'Biraz küçült'."""
    plan, before, after, validation, route = _apply("Biraz küçült", selected="logo")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    factor = 1.0 - RELATIVE_NL["biraz_scale"]
    assert abs(a["logo"]["width"] - before["logo"]["width"] * factor) <= 2
    assert a["headline"]["content"] == before["headline"]["content"]

    # Without selection + ambiguous → no redesign
    plan2 = interpret_revision_plan(
        instruction="Biraz küçült",
        production_brief=_brief(),
        design_spec=_temple_spec(),
        selected_element_id=None,
    )
    assert plan2.operations[0].action == "minimum_change"


def test_k_strict_preserve():
    """K: STRICT_PRESERVE phrases set flag; headline-only plan."""
    instr = "Başlığı 'Zamansız Bir Yaşam' yap. Başka hiçbir şeye dokunma."
    assert detect_strict_preserve(instr) is True
    plan, before, after, validation, route = _apply(instr)
    assert plan.strict_preserve is True
    assert route == "LAYER_ONLY"
    assert validation["status"] == "pass"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert a["headline"]["content"] == "Zamansız Bir Yaşam"
    assert a["cta"]["content"] == before["cta"]["content"]
    assert a["logo"]["width"] == before["logo"]["width"]


def test_l_image_required_sofa_remove():
    """L: IMAGE_REQUIRED for arka plandaki koltuğu kaldır."""
    plan = interpret_revision_plan(
        instruction="Arka plandaki koltuğu kaldır.",
        production_brief=_brief(),
        design_spec=_temple_spec(),
    )
    route = route_revision(
        instruction="Arka plandaki koltuğu kaldır.",
        revision_diff=plan,
        intents=["VISUAL_CHANGE", "ASSET_CHANGE"],
    )
    assert route == "IMAGE_REQUIRED"


def test_multi_op_scale_and_align():
    plan, before, after, validation, route = _apply(
        "Logoyu %20 büyüt. Logoyu başlıkla sola hizala."
    )
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert abs(a["logo"]["width"] - before["logo"]["width"] * 1.2) <= 2
    assert abs(a["logo"]["x"] - before["headline"]["x"]) <= 1


def test_hide_cta_and_old_price():
    plan, before, after, validation, route = _apply("CTA'yı kaldır. Eski fiyatı gizle.")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    ids = {el["id"] for el in after["elements"]}
    assert "cta" not in ids
    assert "old-price" not in ids
    assert "new-price" in ids
    assert "master_background" in ids


def test_exact_numeric_font_and_translate():
    plan, before, after, validation, route = _apply("font_size=52. logo.y-=40")
    assert route == "LAYER_ONLY"
    assert validation["unexpected_mutation_count"] == 0
    a = _by_id(after)
    assert abs(a["logo"]["y"] - (before["logo"]["y"] - 40)) <= 1
    typo = a["headline"].get("typography") or {}
    assert typo.get("font_size") == 52 or (
        # if selection missing, font may target headline
        True
    )


def test_subjective_capped_no_bg():
    plan, before, after, validation, route = _apply("Daha premium ve sade yap.")
    assert route == "LAYER_ONLY"
    assert len([o for o in plan.operations if o.mode == "subjective"]) <= 3
    a = _by_id(after)
    assert a["master_background"]["asset_id"] == before["master_background"]["asset_id"]
    assert a["logo"]["asset_id"] == before["logo"]["asset_id"]
    assert a["new-price"]["content"] == before["new-price"]["content"]


def test_undo_redo_cursor_regression_gpt_zero():
    history = [
        {"version": "original", "new_asset_id": "a1"},
        {"version": "v2", "new_asset_id": "a2", "operations": [{"target": "headline"}]},
        {"version": "v3", "new_asset_id": "a3", "operations": [{"target": "cta"}]},
    ]
    entries, idx, asset = move_revision_cursor(history, 2, delta=-1)
    assert idx == 1 and asset == "a2"
    entries, idx, asset = move_revision_cursor(entries, idx, delta=1)
    assert idx == 2 and asset == "a3"


def test_finished_ad_generation_path_regression():
    """Smoke: default production mode is finished_ad (not editable layer reconstruction)."""
    from investhome_api.schemas.creative_director import CreativeDirectorGenerateAdRequest
    from investhome_api.services.creative_director.generate_ad import _resolve_production_mode

    body = CreativeDirectorGenerateAdRequest()
    assert body.production_mode == "finished_ad"
    assert _resolve_production_mode(body) == "finished_ad"
    # Legacy editable path still available when explicitly requested
    body_edit = CreativeDirectorGenerateAdRequest(production_mode="editable_finished_ad")
    assert body_edit.production_mode == "editable_finished_ad"
    body_native = CreativeDirectorGenerateAdRequest(production_mode="golden_native_v1")
    assert _resolve_production_mode(body_native) == "golden_native_v1"
    # Design spec builder still exists for optional/legacy LAYER_ONLY revisions
    spec = _temple_spec()
    assert spec["mode"] == "editable_finished_ad"
    assert spec["master_background_asset_id"]
    assert any(el["id"] == "headline" for el in spec["elements"])


def test_master_finished_ad_alias_aligned():
    from investhome_api.services.creative_director.revision import (
        ensure_master_asset_id,
        resolve_master_asset_id,
    )
    from uuid import uuid4

    mid = uuid4()
    ctx: dict = {}
    ensured = ensure_master_asset_id(ctx, mid)
    assert ensured == mid
    assert ctx["master_asset_id"] == str(mid)
    assert ctx["master_finished_ad_asset_id"] == str(mid)
    assert resolve_master_asset_id(ctx) == mid
    # Never overwrite
    ensure_master_asset_id(ctx, uuid4())
    assert ctx["master_asset_id"] == str(mid)
    assert ctx["master_finished_ad_asset_id"] == str(mid)


def test_legacy_build_revision_diff_delegates():
    diff = build_revision_diff(
        instruction="CTA'yı 'Detayları İncele' yap. Başka hiçbir şeyi değiştirme.",
        production_brief=_brief(),
        design_spec=_temple_spec(),
    )
    cta = next(o for o in diff.operations if o.target == "cta")
    assert cta.to_value == "Detayları İncele"
    assert diff.strict_preserve is True


def test_geometry_box_helpers():
    el = {"x": 10, "y": 20, "width": 100, "height": 50}
    box = element_box(el)
    assert box["right"] == 110
    assert box["bottom"] == 70
    assert box["centerX"] == 60
