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
