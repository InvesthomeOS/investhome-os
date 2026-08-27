"""AI-first Master Creative v1 — classifier, record, generate-path helpers."""

from __future__ import annotations

from investhome_api.services.creative_director.generate_ad import (
    _use_v2_editable_layers,
    build_master_creative_record,
)
from investhome_api.services.creative_director.master_revision_controller import (
    classify_revision_command,
)


def test_classify_visual_replace_only() -> None:
    plan = classify_revision_command(
        "Bu görsel yerine Drive'daki diğer dış cepheyi kullan. Başka hiçbir şeyi değiştirme."
    )
    assert plan["intent"] == "VISUAL_REPLACE_ONLY"
    assert "headline" in plan["locked"]
    assert plan["pixel_surgery_allowed"] is False
    assert plan["executed"] is False


def test_classify_price_edit_only() -> None:
    plan = classify_revision_command(
        "675.000 USD'yi 438.750 USD yap. Başka hiçbir şeyi değiştirme."
    )
    assert plan["intent"] == "PRICE_EDIT_ONLY"
    assert "hero_visual" in plan["locked"]
    assert plan["fail_closed"] is True


def test_classify_logo_edit_only() -> None:
    plan = classify_revision_command("Logoyu %15 küçült.")
    assert plan["intent"] == "LOGO_EDIT_ONLY"
    assert plan["mutable"] == ["logo_geometry"]


def test_classify_creative_recompose() -> None:
    plan = classify_revision_command("Bu tasarımı daha lüks ve dramatik yap.")
    assert plan["intent"] == "CREATIVE_RECOMPOSE"


TEMPLE_PRICE_EDIT = (
    "Liste fiyatı 675.000 USD aynı kalsın ve üzeri çizili gösterilsin.\n"
    "%35 lansman indirimi sonrası satış fiyatını 438.750 USD olarak ekle.\n"
    "Ayrıca 'Kazancınız 236.250 USD' bilgisini ekle.\n"
    "Bunun dışında tasarımda hiçbir şeyi değiştirme.\n"
    "Dış cephe görseli, ALIRKEN KAZAN başlığı, 2+1 bilgisi, %35,\n"
    "The Temple logosu, CTA, renkler, tipografi, görsel yerleşimi\n"
    "ve genel tasarım birebir aynı kalsın."
)


def test_preservation_phrases_do_not_create_visual_replace() -> None:
    from investhome_api.services.creative_director.master_revision_controller import (
        is_visual_replace_command,
    )
    from investhome_api.services.creative_director.revision import interpret_revision_intents

    phrases = (
        "dış cephe görseli aynı kalsın",
        "dış cepheyi değiştirme",
        "görseli değiştirme",
        "mevcut görsel aynı kalsın",
        "arka planı değiştirme",
        "fotoğraf aynı kalsın",
        "birebir aynı kalsın",
        "başka hiçbir şeyi değiştirme",
        "dış cephe görseli birebir aynı kalsın",
        "bu görseli koru",
    )
    for phrase in phrases:
        assert not is_visual_replace_command(phrase), phrase
        plan = classify_revision_command(phrase)
        assert plan["intent"] != "VISUAL_REPLACE_ONLY", phrase
        intents = interpret_revision_intents(phrase)
        assert "ASSET_CHANGE" not in intents, phrase
        assert "VISUAL_CHANGE" not in intents, phrase


def test_positive_replace_phrases_still_visual_replace() -> None:
    from investhome_api.services.creative_director.master_revision_controller import (
        is_visual_replace_command,
    )

    phrases = (
        "görseli değiştir",
        "başka dış cephe kullan",
        "bu görsel yerine diğer dış cepheyi kullan",
        "Sadece görseli değiştir.",
    )
    for phrase in phrases:
        assert is_visual_replace_command(phrase), phrase
        plan = classify_revision_command(phrase)
        assert plan["intent"] == "VISUAL_REPLACE_ONLY", phrase


def test_live_temple_price_command_is_price_edit_only() -> None:
    from investhome_api.services.creative_director.design_spec import route_revision
    from investhome_api.services.creative_director.master_revision_controller import (
        is_visual_replace_command,
    )
    from investhome_api.services.creative_director.revision import (
        build_revision_diff,
        interpret_revision_intents,
    )

    plan = classify_revision_command(TEMPLE_PRICE_EDIT)
    assert plan["intent"] == "PRICE_EDIT_ONLY"
    assert "hero_visual" in plan["locked"]
    assert "source_visual" in plan["locked"]
    assert not is_visual_replace_command(TEMPLE_PRICE_EDIT)
    intents = interpret_revision_intents(TEMPLE_PRICE_EDIT)
    assert "ASSET_CHANGE" not in intents
    assert "VISUAL_CHANGE" not in intents
    assert "COMMERCIAL_EMPHASIS" in intents
    diff = build_revision_diff(instruction=TEMPLE_PRICE_EDIT, production_brief={})
    route = route_revision(
        instruction=TEMPLE_PRICE_EDIT,
        revision_diff=diff,
        intents=intents,
    )
    assert route == "PRICE_EDIT_ONLY"


def test_ana_mesaj_locks_alirken_kazan() -> None:
    from investhome_api.services.creative_director.generate_ad import extract_labeled_brief_copy

    labeled = extract_labeled_brief_copy(
        "The Temple için reklam.\nAna mesaj:\nALIRKEN KAZAN\nCTA:\nPROJEYİ KEŞFET"
    )
    assert labeled["headline"] == "ALIRKEN KAZAN"
    assert labeled["cta"] == "PROJEYİ KEŞFET"


def test_new_finished_ad_is_not_v2_layers() -> None:
    assert _use_v2_editable_layers("finished_ad", {}) is False
    assert _use_v2_editable_layers("editable_finished_ad", {}) is True
    assert _use_v2_editable_layers("finished_ad", {"revision_engine_v2": True}) is True


def test_master_creative_record_shape() -> None:
    rec = build_master_creative_record(
        campaign_id="11111111-1111-1111-1111-111111111111",
        project_id="d50708cb-60b3-465a-8b16-6d30f802af8d",
        source_visual={
            "asset_id": "c3d11c35-d8b7-485c-b216-0a4da68b751a",
            "filename": "IH_DC_TMP_001_Render_Living_Room_001.jpg",
            "folder_category": "02_RENDER",
            "provenance_source": "media_library",
            "approved": True,
            "approved_status": "approved",
        },
        logo_meta={
            "asset_id": "7b58877e-efca-4e9a-9027-6fd18fb1b345",
            "filename": "IH_DC_TMP_001_Logo_Primary.svg",
        },
        format_preset="portrait",
        aspect_ratio="4:5",
        ad_scope="project",
        texts={"headline": "ALIRKEN KAZAN", "cta": "PROJEYİ KEŞFET"},
        creative_direction={"first_notice": "headline"},
        master_asset_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        original_brief="The Temple için premium bir lansman reklamı hazırla.",
    )
    assert rec["workflow"] == "ai_first_master_v1"
    assert rec["format"] == "4:5"
    assert rec["ad_scope"] == "project"
    assert rec["current_version"] == 1
    assert rec["revision_history"] == []
    assert rec["pixel_surgery_fallback"] is False
    assert rec["source_visual_approval"] == "approved"
    assert rec["logo_filename"] == "IH_DC_TMP_001_Logo_Primary.svg"
    assert rec["current_cover_asset_id"] == rec["master_asset_id"]
    assert rec["current_edit_map_id"] is None


TEMPLE_VISUAL_REPLACE = (
    "Bu iç mekan görseli yerine The Temple projesinin Drive klasöründeki onaylı dış cephe "
    "görsellerinden en uygun olanını kullan.\n"
    "Tasarımın geri kalanını kesinlikle değiştirme.\n"
    "Başlık, metinler, 2+1, 675.000 USD, %35, logo, CTA, fontlar, renkler, boyutlar, "
    "konumlar, hizalamalar ve genel kompozisyon birebir aynı kalsın.\n"
    "Sadece ana proje görselini değiştir."
)


def test_sadece_does_not_classify_simplify() -> None:
    from investhome_api.services.creative_director.revision import interpret_revision_intents
    from investhome_api.services.creative_director.revision_intelligence import parse_subjective_ops

    for instruction in (
        "Sadece görseli değiştir.",
        "Sadece ana proje görselini değiştir.",
        "Başka hiçbir şeyi değiştirme.",
        TEMPLE_VISUAL_REPLACE,
    ):
        intents = interpret_revision_intents(instruction)
        assert "SIMPLIFY" not in intents, instruction
        ops = parse_subjective_ops(instruction, existing=[])
        assert not any(
            o.target == "support_message" and o.action == "remove" for o in ops
        ), instruction


def test_sade_word_still_simplifies() -> None:
    from investhome_api.services.creative_director.revision import interpret_revision_intents

    intents = interpret_revision_intents("Tasarımı daha sade yap.")
    assert "SIMPLIFY" in intents


def test_visual_replace_phrases_are_asset_change() -> None:
    from investhome_api.services.creative_director.master_revision_controller import (
        classify_revision_command,
    )
    from investhome_api.services.creative_director.revision import interpret_revision_intents

    phrases = (
        "görseli değiştir",
        "görselini değiştir",
        "bu görsel yerine başka bir foto kullan",
        "bu görselin yerine Drive görseli koy",
        "başka görsel kullan",
        "başka fotoğraf kullan",
        "dış cephe görselini kullan",
        "Drive'daki dış cepheyi kullan",
        "ana proje görselini değiştir",
    )
    for phrase in phrases:
        plan = classify_revision_command(phrase)
        assert plan["intent"] == "VISUAL_REPLACE_ONLY", phrase
        intents = interpret_revision_intents(phrase)
        assert "ASSET_CHANGE" in intents, phrase
        assert "SIMPLIFY" not in intents, phrase


def test_live_temple_command_is_visual_replace_only() -> None:
    from investhome_api.services.creative_director.design_spec import route_revision
    from investhome_api.services.creative_director.master_revision_controller import (
        classify_revision_command,
    )
    from investhome_api.services.creative_director.revision import (
        build_revision_diff,
        interpret_revision_intents,
    )

    plan = classify_revision_command(TEMPLE_VISUAL_REPLACE)
    assert plan["intent"] == "VISUAL_REPLACE_ONLY"
    assert "SIMPLIFY" not in interpret_revision_intents(TEMPLE_VISUAL_REPLACE)
    diff = build_revision_diff(instruction=TEMPLE_VISUAL_REPLACE, production_brief={})
    route = route_revision(
        instruction=TEMPLE_VISUAL_REPLACE,
        revision_diff=diff,
        intents=interpret_revision_intents(TEMPLE_VISUAL_REPLACE),
    )
    assert route == "VISUAL_REPLACE_ONLY"
    assert not any(o.target == "support_message" for o in diff.operations)


def _visual_replace_ad_png(*, bright_hero: bool, cta: bool, logo: bool) -> bytes:
    import io

    from PIL import Image, ImageDraw

    img = Image.new("RGB", (400, 500), (18, 22, 32))
    draw = ImageDraw.Draw(img)
    draw.rectangle((20, 20, 250, 90), fill=(240, 236, 228))
    draw.rectangle((20, 100, 180, 140), fill=(196, 163, 90))
    draw.rectangle((0, 180, 400, 500), fill=(70, 80, 70))
    if bright_hero:
        # Bright stone only in the leftover left-rail CTA crop — not the centered button.
        draw.rectangle((0, 390, 60, 500), fill=(210, 190, 150))
    if cta:
        draw.rectangle((110, 390, 290, 440), fill=(196, 163, 90))
    if logo:
        draw.rectangle((150, 455, 250, 490), fill=(220, 200, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_visual_replace_fidelity_allows_bright_exterior_in_left_cta_box() -> None:
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    result = compare_recompose_composition_fidelity(
        master_bytes=_visual_replace_ad_png(bright_hero=False, cta=True, logo=True),
        revised_bytes=_visual_replace_ad_png(bright_hero=True, cta=True, logo=True),
        revision_diff={"operations": [{"target": "background", "action": "minimum_change"}]},
        hero_visual_replace=True,
    )
    assert result["status"] == "pass", result["composition_failures"]
    assert result.get("hero_visual_replace") is True


def test_visual_replace_fidelity_rejects_cta_overlay_loss() -> None:
    from investhome_api.services.creative_director.revision import (
        compare_recompose_composition_fidelity,
    )

    result = compare_recompose_composition_fidelity(
        master_bytes=_visual_replace_ad_png(bright_hero=False, cta=True, logo=True),
        revised_bytes=_visual_replace_ad_png(bright_hero=True, cta=False, logo=True),
        revision_diff={"operations": [{"target": "background", "action": "minimum_change"}]},
        hero_visual_replace=True,
    )
    assert result["status"] == "fail"
    assert any("cta" in f for f in result["composition_failures"])


def test_pick_real_interior_rejects_workspace_screenshot() -> None:
    from uuid import uuid4

    from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate
    from investhome_api.services.creative_director.research import pick_real_interior

    project_id = uuid4()
    living = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="IH_DC_TMP_001_Render_Living_Room_001.jpg",
        content_type="image/jpeg",
        folder_category="02_RENDER",
        tags=["interior", "living"],
        score=8.0,
        linked_project_id=project_id,
        visual_subject="INTERIOR",
        source_type="google_drive",
    )
    shot = SocialDesignMediaCandidate(
        asset_id=uuid4(),
        filename="screencapture-localhost-3000-workspaces-creative-studio-ai-chat.png",
        content_type="image/png",
        folder_category="",
        tags=["lifestyle", "interior"],
        score=99.0,
        linked_project_id=project_id,
        visual_subject="INTERIOR",
        source_type="upload",
    )
    picked, _score, _reason = pick_real_interior([shot, living], brief="The Temple lansman")
    assert picked is not None
    assert picked.asset_id == living.asset_id


def test_architecture_truth_guard_fails_closed_on_screenshot() -> None:
    from investhome_api.services.creative_director.quality_lock.architecture_truth import (
        architecture_truth_guard,
    )

    report = architecture_truth_guard(
        hero_meta={
            "asset_id": "1c5281a8-e518-442c-839f-6cdbc22c1837",
            "filename": "screencapture-localhost-3000-workspaces-creative-studio-ai-chat.png",
            "folder_category": "",
            "visual_subject": "AMENITY",
            "provenance_source": "upload",
            "approved": True,
        },
        source_asset_id="1c5281a8-e518-442c-839f-6cdbc22c1837",
        campaign_intent="lifestyle",
    )
    assert report["fail_closed"] is True
    assert "workspace_screenshot_not_project_visual" in report["failures"]


def test_art_direction_does_not_invent_300k_when_list_only() -> None:
    from investhome_api.services.creative_director.art_direction_translator import (
        translate_campaign_art_direction,
    )

    plan = translate_campaign_art_direction(
        ctx={
            "cd_strategy": {"first_2_seconds": "ALIRKEN KAZAN"},
            "campaign_copy": {"big_idea": "ALIRKEN KAZAN"},
            "pricing": {
                "price_presentation": {
                    "list": "675.000 USD",
                    "offer": "",
                    "discount": {"display": "%35"},
                }
            },
        },
        texts={
            "headline": "ALIRKEN KAZAN",
            "unit": "2+1",
            "list_price": "675.000 USD",
            "offer_price": "",
            "value_badge": "%35",
            "cta": "PROJEYİ KEŞFET",
            "supporting": "The Temple'da yerinizi lansman döneminde alın.",
        },
        interior_meta={"filename": "living.jpg", "asset_id": "x"},
        logo_meta={"filename": "logo.svg", "asset_id": "y"},
        language="tr",
        lifestyle=False,
    )
    blob = f"{plan.first_notice} {plan.second_notice} {plan.price_hierarchy}"
    assert "300,000" not in blob
    assert "400,000" not in blob
    assert "ALIRKEN KAZAN" in (plan.first_notice or "")
