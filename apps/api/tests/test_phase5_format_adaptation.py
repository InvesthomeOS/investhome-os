"""Phase 5.1 — format adaptation from approved Master. Phase 5.0 path must still pass."""

from __future__ import annotations

from copy import deepcopy
from io import BytesIO
from uuid import UUID, uuid4

from PIL import Image

from investhome_api.schemas.creative_director import CreativeDirectorReviseRequest
from investhome_api.schemas.gpt_image_design import (
    GptImageDesignResponse,
    GptImageOutput,
    GptImageSourceImage,
)
from investhome_api.services.creative_director.phase5_format_adaptation import (
    adaptation_qa,
    approved_semantic_content,
    format_utilization_qa,
    validate_required_text,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    interpret_user_turn,
    revise_ad_phase5,
)


def _png(color: tuple[int, int, int], size: tuple[int, int] = (64, 80)) -> bytes:
    buf = BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_format_command_intent() -> None:
    turn = interpret_user_turn("Diğer ölçülere uyarla.")
    assert turn["intent"] == "FORMAT_ADAPTATION_ALL"
    assert turn["targets"] == ["1:1", "9:16", "16:9"]


def test_approved_facts_come_from_approved_version_not_initial() -> None:
    session = {
        "approved_version_id": "v3",
        "approved_master": {"approved_version_id": "v3", "master_asset_id": "m"},
        "user_request": "Fiyat 675.000 USD",
        "versions": [
            {
                "version_id": "v1",
                "creative_context": {"required_factual_content": {"list_price": "675.000 USD", "headline": "ALIRKEN KAZAN"}},
            },
            {
                "version_id": "v3",
                "creative_context": {
                    "required_factual_content": {
                        "headline": "ALIRKEN KAZAN",
                        "unit": "2+1",
                        "unit_label": "DAİRE",
                        "list_price": "438.750 USD",
                        "discount": "%35",
                        "discount_label": "LANSMAN AVANTAJI",
                        "cta": "PROJEYİ KEŞFET",
                    }
                },
            },
        ],
    }
    facts = approved_semantic_content(session)
    assert facts["list_price"] == "438.750 USD"
    ocr_facts = approved_semantic_content(session, "PRICE 438.750 USD ALIRKEN KAZAN")
    assert ocr_facts["list_price"] == "438.750 USD"


def test_text_validation_rejects_old_price_and_missing_headline() -> None:
    facts = {"headline": "ALIRKEN KAZAN", "list_price": "438.750 USD", "discount": "%35", "cta": "PROJEYİ KEŞFET"}
    ok = validate_required_text("ALIRKEN KAZAN 2+1 438.750 USD %35 PROJEYİ KEŞFET", facts)
    assert ok["status"] == "pass"
    leaked = validate_required_text("ALIRKEN KAZAN 2+1 675.000 USD %35 PROJEYİ KEŞFET", facts)
    assert leaked["status"] == "fail"
    assert leaked["leaked_old_or_wrong_price"]
    missing = validate_required_text("2+1 438.750 USD %35 CTA", facts)
    assert missing["status"] == "fail"
    assert "headline" in missing["missing"]


def test_format_utilization_rejects_bad_canvas() -> None:
    landscape = {"key": "landscape", "width": 1920, "height": 1088}
    filled = Image.new("RGB", (1920, 1088), (90, 70, 50))
    ok = format_utilization_qa(filled, landscape)
    assert ok["status"] == "pass"
    square_ok = format_utilization_qa(
        Image.new("RGB", (1024, 1024), (20, 20, 20)),
        {"key": "square", "width": 1024, "height": 1024},
    )
    assert square_ok["status"] == "pass"
    cropped_portrait_as_square = format_utilization_qa(
        Image.new("RGB", (1024, 1280), (20, 20, 20)),
        {"key": "square", "width": 1024, "height": 1024},
    )
    assert cropped_portrait_as_square["status"] == "fail"


def test_adaptation_qa_flags_unrelated_redesign() -> None:
    master = Image.new("RGB", (200, 250), (30, 40, 50))
    same = Image.new("RGB", (1024, 1024), (32, 42, 52))
    other = Image.new("RGB", (1024, 1024), (220, 20, 20))
    hero = Image.new("RGB", (200, 200), (28, 38, 48))
    target = {"key": "square", "width": 1024, "height": 1024}
    facts = {"headline": "ALIRKEN KAZAN", "list_price": "675.000 USD", "discount": "%35", "cta": "PROJEYİ KEŞFET"}
    ocr = "ALIRKEN KAZAN 2+1 675.000 USD %35 PROJEYİ KEŞFET"
    good = adaptation_qa(
        master=master,
        derivative=same,
        hero=hero,
        target=target,
        facts=facts,
        ocr_text=ocr,
        hero_id=LOCKED_HERO_ASSET_ID,
        logo_id=LOCKED_LOGO_ASSET_ID,
    )
    bad = adaptation_qa(
        master=master,
        derivative=other,
        hero=hero,
        target=target,
        facts=facts,
        ocr_text=ocr,
        hero_id=LOCKED_HERO_ASSET_ID,
        logo_id=LOCKED_LOGO_ASSET_ID,
    )
    assert good["unexpected_redesign"] is False
    assert bad["unexpected_redesign"] is True


def test_phase51_adapts_three_formats_without_touching_master_or_production(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_format_adaptation as fa
    from investhome_api.services.creative_director import phase5_workflow as wf

    db = SessionLocal()
    existing = db.get(Project, UUID(TEMPLE_PROJECT_ID))
    if existing is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"PH51-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    hero_id = UUID(LOCKED_HERO_ASSET_ID)
    logo_id = UUID(LOCKED_LOGO_ASSET_ID)
    master_asset = uuid4()
    square_id, story_id, land_id = uuid4(), uuid4(), uuid4()
    session_id = str(uuid4())
    version_id = str(uuid4())
    master_id = str(uuid4())
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {
            "current_version": 2,
            "current_cover_asset_id": PRODUCTION_COVER_V2,
            "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        },
        "phase5": {
            "current_session_id": session_id,
            "sessions": {
                session_id: {
                    "session_id": session_id,
                    "project_id": TEMPLE_PROJECT_ID,
                    "status": "APPROVED",
                    "current_version_id": version_id,
                    "approved_version_id": version_id,
                    "user_request": "The Temple için ALIRKEN KAZAN. Fiyat 675.000 USD.",
                    "creative_type": "social_advertisement",
                    "target_format": "instagram_feed_4:5",
                    "format_preset": "portrait",
                    "aspect_ratio": "4:5",
                    "versions": [
                        {
                            "version_id": version_id,
                            "asset_id": str(master_asset),
                            "version_number": 3,
                            "project_asset_ids": [LOCKED_HERO_ASSET_ID],
                            "logo_asset_id": LOCKED_LOGO_ASSET_ID,
                            "creative_context": {
                                "required_factual_content": {
                                    "headline": "ALIRKEN KAZAN",
                                    "unit": "2+1",
                                    "unit_label": "DAİRE",
                                    "list_price": "438.750 USD",
                                    "discount": "%35",
                                    "discount_label": "LANSMAN AVANTAJI",
                                    "cta": "PROJEYİ KEŞFET",
                                }
                            },
                        }
                    ],
                    "approved_master": {
                        "master_id": master_id,
                        "session_id": session_id,
                        "approved_version_id": version_id,
                        "master_asset_id": str(master_asset),
                        "base_format": "instagram_feed_4:5",
                    },
                    "format_adaptation_started": False,
                    "video_started": False,
                    "publishing_started": False,
                    "next_hooks": {"format_adaptation": "unstarted", "video": "unstarted", "publishing": "unstarted"},
                }
            },
            "approved_masters": {master_id: {"master_id": master_id, "master_asset_id": str(master_asset)}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="placeholder",
        context_json=ctx,
        status="ready",
    )
    db.add(row)
    db.flush()

    def fake_prep(db, campaign_id, body):
        return (
            row,
            dict(row.context_json or {}),
            {},
            {},
            {},
            "brief",
            False,
            [],
            "tr",
            "portrait",
            "4:5",
            hero_id,
            logo_id,
            {"asset_id": str(hero_id)},
            {"asset_id": str(logo_id)},
            {},
            [],
            {},
            {},
        )

    sizes = {"1:1": (1024, 1024), "9:16": (1088, 1920), "16:9": (1920, 1088)}
    ids = {"1:1": square_id, "9:16": story_id, "16:9": land_id}
    seen_aspects: list[str] = []

    def fake_generate(db, user, body):
        aspect = str(body.aspect_ratio)
        seen_aspects.append(aspect)
        assert body.builder_context["phase5_format_adaptation"] is True
        assert body.builder_context["revision_visual_reference_asset_id"] == str(master_asset)
        assert body.selected_asset_ids == [hero_id]
        assert "new campaign" in (body.instruction or "").lower() or "already approved" in (body.instruction or "").lower()
        assert "438.750 USD" in (body.instruction or "")
        assert "675.000 USD" not in (body.instruction or "")
        assert "top panel" not in (body.instruction or "").lower()
        oid = ids[aspect]
        w, h = sizes[aspect]
        return GptImageDesignResponse(
            provider="gpt-image",
            model="gpt-image-2",
            endpoint="https://api.openai.com/v1/images/edits",
            campaign_mode="project",
            session_id=session_id,
            linked_project_id=UUID(TEMPLE_PROJECT_ID),
            generation_context_id=str(uuid4()),
            aspect_ratio=aspect,
            format_preset=str(body.format_preset),
            source_image=GptImageSourceImage(
                asset_id=hero_id,
                filename="IH_DC_TMP_001_Render_Exterior_Day_004.jpg",
                content_type="image/jpeg",
                role="source",
            ),
            outputs=[
                GptImageOutput(
                    local_asset_id=oid,
                    local_asset_url=f"/creative-studio/media/assets/{oid}/content",
                    canvas_width=w,
                    canvas_height=h,
                )
            ],
            provider_call_count=1,
            latency_ms=11,
        )

    pngs = {
        str(master_asset): _png((30, 40, 50), (1088, 1360)),
        str(hero_id): _png((28, 38, 48), (200, 200)),
        str(square_id): _png((32, 42, 52), (1024, 1024)),
        str(story_id): _png((31, 41, 51), (1088, 1920)),
        str(land_id): _png((33, 43, 53), (1920, 1088)),
    }

    monkeypatch.setattr(wf, "_prepare_campaign_ad_context", fake_prep)
    monkeypatch.setattr(fa, "generate_gpt_image_creatives", fake_generate)
    monkeypatch.setattr(
        fa,
        "provider_capability_record",
        lambda: {
            "provider": "gpt-image",
            "model": "gpt-image-2",
            "available": True,
            "usable_for_project_locked": True,
            "reference_image_support": True,
            "revision_reference_workflow": True,
            "project_asset_fidelity": "edits_with_locked_project_references",
            "reason": None,
        },
    )
    monkeypatch.setattr(fa, "assert_image_provider_available", lambda route: None)
    monkeypatch.setattr(
        fa,
        "route_ad_social_image",
        lambda **kwargs: type("R", (), {"to_dict": lambda self: {"provider_id": "gpt_image", "model": "gpt-image-2"}})(),
    )
    monkeypatch.setattr(fa, "_read_bytes", lambda db, asset_id: pngs[str(asset_id)])
    monkeypatch.setattr(
        fa,
        "_ocr_image_bytes",
        lambda content: "ALIRKEN KAZAN 2+1 438.750 USD %35 PROJEYİ KEŞFET",
    )

    out = revise_ad_phase5(
        db,
        user,
        row.id,
        CreativeDirectorReviseRequest(
            instruction="Diğer ölçülere uyarla.",
            current_final_asset_id=master_asset,
        ),
    )
    assert seen_aspects == ["1:1", "9:16", "16:9"]
    assert out.revision_intents == ["FORMAT_ADAPTATION_ALL"]
    assert out.quality_guard["approved_master_changed"] is False
    assert out.quality_guard["phase4_renderer_used"] is False
    assert out.quality_guard["simple_resize_crop_used"] is False
    assert out.quality_guard["video_started"] is False
    assert out.quality_guard["publishing_started"] is False
    assert str(out.master_asset_id) == str(master_asset)
    family = out.campaign_context["format_family"]
    assert len(family["derivatives"]) == 3
    db.refresh(row)
    final = dict(row.context_json or {})
    assert final["current_cover_asset_id"] == PRODUCTION_COVER_V2
    assert final["master_creative"]["current_version"] == 2
    sess = final["phase5"]["sessions"][session_id]
    assert sess["approved_master"]["master_asset_id"] == str(master_asset)
    assert sess["status"] == "FORMAT_ADAPTATION_READY"
    assert len(sess["versions"]) == 1
    assert copied_ok(final)
    db.rollback()
    db.close()


def copied_ok(ctx: dict) -> bool:
    copied = deepcopy(ctx)
    return copied["current_cover_asset_id"] == PRODUCTION_COVER_V2
