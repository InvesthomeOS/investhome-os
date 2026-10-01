"""Phase 5.1D — AI overlay on locked Day_004. OS compositor is not the designer."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_creative_overlay import (
    CANVAS_4X5,
    DIRECTION_R1,
    DIRECTION_R2,
    PARENT_51D_ASSET_ID,
    PARENT_R1_ASSET_ID,
    WORKFLOW_ID_51D,
    WORKFLOW_ID_51D_R1,
    WORKFLOW_ID_51D_R2,
    composite_overlay,
    generate_creative_overlay_4x5,
    magenta_to_alpha,
    overlay_center_clear_ratio,
    overlay_prompt,
    overlay_quality_ok,
    overlay_transparency_ratio,
    plan_to_spatial_brief,
    prepare_overlay,
    render_photo_awareness_map,
)
from investhome_api.services.creative_director.phase5_photo_foundation import cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _day004_like() -> Image.Image:
    im = Image.new("RGB", (2268, 1234), (176, 196, 214))
    draw = ImageDraw.Draw(im)
    draw.rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    draw.rectangle((1680, 80, 1820, 280), fill=(208, 198, 180))
    return im


def test_chroma_key_clears_magenta_and_keeps_graphics() -> None:
    im = Image.new("RGB", (200, 200), (255, 0, 255))
    ImageDraw.Draw(im).rectangle((20, 20, 80, 80), fill=(196, 163, 90))
    keyed = magenta_to_alpha(im)
    assert keyed.getpixel((10, 10))[3] < 40
    assert keyed.getpixel((40, 40))[3] > 180
    assert overlay_transparency_ratio(keyed) > 0.5


def test_composite_preserves_foundation_where_overlay_is_empty() -> None:
    foundation = Image.new("RGB", CANVAS_4X5, (40, 80, 120))
    overlay_rgb = Image.new("RGB", CANVAS_4X5, (255, 0, 255))
    ImageDraw.Draw(overlay_rgb).rectangle((0, 0, 200, 300), fill=(20, 20, 20))
    overlay = magenta_to_alpha(overlay_rgb)
    final = composite_overlay(foundation, overlay).convert("RGB")
    assert final.getpixel((400, 400))[:3] == (40, 80, 120)
    assert final.getpixel((40, 40))[:3] != (40, 80, 120)
    canvas, transform = cover_fit_canvas(_day004_like(), CANVAS_4X5)
    assert transform["scale_x"] == transform["scale_y"]
    assert canvas.size == CANVAS_4X5
    assert overlay_center_clear_ratio(overlay) > 0.8
    assert overlay_quality_ok(overlay, {"pass": True}) is True


def test_opaque_overlay_fails_quality() -> None:
    opaque = Image.new("RGBA", CANVAS_4X5, (12, 12, 18, 255))
    assert overlay_quality_ok(opaque, {"pass": True}) is False


def test_prepare_overlay_uses_native_alpha_when_present() -> None:
    im = Image.new("RGBA", (64, 80), (255, 0, 255, 0))
    ImageDraw.Draw(im).rectangle((4, 4, 20, 30), fill=(200, 160, 80, 255))
    prepared = prepare_overlay(_png(im), method="generations_transparent_png")
    assert prepared.mode == "RGBA"
    assert prepared.size == CANVAS_4X5


def test_overlay_generate_does_not_touch_history(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_overlay as ov

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51D-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    photo_tests = [{"workflow": "phase5_1b_photo_foundation", "keep": True}]
    design_tests = [{"workflow": "phase5_1c_creative_design", "keep": True}]
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
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {
                "5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}
            },
            "photo_foundation_tests": photo_tests,
            "creative_design_tests": design_tests,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1d test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    overlay_im = Image.new("RGB", CANVAS_4X5, (255, 0, 255))
    ImageDraw.Draw(overlay_im).rectangle((30, 40, 280, 220), fill=(201, 168, 92))
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    monkeypatch.setattr(ov, "_read_bytes", fake_read)
    monkeypatch.setattr(ov, "request_overlay_bytes", lambda **k: (_png(overlay_im), "generations_magenta_chroma", 1))
    monkeypatch.setattr(ov, "verify_overlay_facts", lambda *a, **k: ({"pass": True, "mode": "mock"}, 0))
    monkeypatch.setattr(ov, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(ov, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        ov,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )

    result = generate_creative_overlay_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["architecture_generation_used"] is False
    assert result["os_compositor_primary_designer"] is False
    assert result["ai_generated_building_used"] is False
    assert result["gpt_image_edit_calls"] == 0
    assert result["final_size"] == list(CANVAS_4X5)
    assert result["overlay_retries"] == 0
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("photo_foundation_tests") == photo_tests
    assert phase5.get("creative_design_tests") == design_tests
    db.rollback()
    db.close()


def test_r1_prompt_is_editorial_not_ornamental() -> None:
    prompt = overlay_prompt(dict(REQUIRED_FACTS), chroma=False, direction=DIRECTION_R1)
    folded = prompt.casefold()
    assert "ribbon" in folded
    assert "medallion" in folded
    assert "empty frame" in folded or "empty frames" in folded
    assert "jewelry" in folded
    assert "architectural editorial" in folded
    assert "empty plate" not in folded
    assert "do not draw a logo" in folded


def test_r1_does_not_overwrite_51d(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_overlay as ov

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51DR1-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    overlay_51d = {
        "workflow": WORKFLOW_ID_51D,
        "final_asset_id": PARENT_51D_ASSET_ID,
        "keep": True,
    }
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
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {
                "5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}
            },
            "photo_foundation_tests": [{"workflow": "phase5_1b_photo_foundation", "keep": True}],
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": [overlay_51d],
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1d-r1 test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    overlay_im = Image.new("RGB", CANVAS_4X5, (255, 0, 255))
    ImageDraw.Draw(overlay_im).rectangle((30, 200, 240, 520), fill=(201, 168, 92))
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    monkeypatch.setattr(ov, "_read_bytes", fake_read)
    monkeypatch.setattr(ov, "request_overlay_bytes", lambda **k: (_png(overlay_im), "generations_magenta_chroma", 1))
    monkeypatch.setattr(ov, "verify_overlay_facts", lambda *a, **k: ({"pass": True, "mode": "mock"}, 0))
    monkeypatch.setattr(ov, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(ov, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        ov,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )

    result = generate_creative_overlay_4x5(
        db, user, row, language="tr", revision=DIRECTION_R1, parent_asset_id=PARENT_51D_ASSET_ID
    )
    db.refresh(row)
    phase5 = dict((row.context_json or {}).get("phase5") or {})
    overlays = list(phase5.get("creative_overlay_tests") or [])
    assert result["workflow"] == WORKFLOW_ID_51D_R1
    assert result["parent_asset_id"] == PARENT_51D_ASSET_ID
    assert result["os_compositor_primary_designer"] is False
    assert any(t.get("workflow") == WORKFLOW_ID_51D and t.get("final_asset_id") == PARENT_51D_ASSET_ID for t in overlays)
    assert any(t.get("workflow") == WORKFLOW_ID_51D_R1 for t in overlays)
    db.rollback()
    db.close()


def _sample_plan() -> dict:
    return {
        "photograph_reading": "gothic spire left-center, sky above right, street below",
        "focal_point": "stone spire",
        "light": "daylight",
        "protected": {
            "spire": {"x": 0.30, "y": 0.02, "w": 0.22, "h": 0.58},
            "architecture": {"x": 0.18, "y": 0.28, "w": 0.52, "h": 0.50},
        },
        "negative_space": [{"name": "upper-right sky", "x": 0.58, "y": 0.04, "w": 0.38, "h": 0.22}],
        "headline": {"x": 0.04, "y": 0.10, "w": 0.26, "h": 0.14},
        "commercial": {"x": 0.04, "y": 0.62, "w": 0.30, "h": 0.22},
        "cta": {"x": 0.04, "y": 0.86, "w": 0.28, "h": 0.08},
        "logo": {"x": 0.04, "y": 0.03, "w": 0.20, "h": 0.07},
        "headline_strategy": "left sky, clear of spire",
        "commercial_strategy": "one group in lower-left quiet ground",
        "mode": "vision",
    }


def test_r2_prompt_is_photo_aware_not_compositor() -> None:
    prompt = overlay_prompt(dict(REQUIRED_FACTS), chroma=False, direction=DIRECTION_R2, plan=_sample_plan())
    folded = prompt.casefold()
    assert "photo-aware" in folded
    assert "do not repeat the failed r1" in folded
    assert "protected spire" in folded
    assert "dejavu" not in folded
    assert "empty plate" not in folded
    brief = plan_to_spatial_brief(_sample_plan())
    assert "PROTECTED SPIRE" in brief
    assert "COMMERCIAL SYSTEM ZONE" in brief


def test_awareness_map_is_debug_not_the_ad() -> None:
    im = Image.new("RGB", CANVAS_4X5, (120, 140, 160))
    mapped = render_photo_awareness_map(im, _sample_plan())
    assert mapped.size == CANVAS_4X5


def test_r2_does_not_overwrite_r1(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_overlay as ov

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51DR2-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    overlay_51d = {"workflow": WORKFLOW_ID_51D, "final_asset_id": PARENT_51D_ASSET_ID, "keep": True}
    overlay_r1 = {"workflow": WORKFLOW_ID_51D_R1, "final_asset_id": PARENT_R1_ASSET_ID, "keep": True}
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
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {
                "5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}
            },
            "photo_foundation_tests": [{"workflow": "phase5_1b_photo_foundation", "keep": True}],
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": [overlay_51d, overlay_r1],
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1d-r2 test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    overlay_im = Image.new("RGB", CANVAS_4X5, (255, 0, 255))
    ImageDraw.Draw(overlay_im).rectangle((40, 180, 260, 500), fill=(201, 168, 92))
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    monkeypatch.setattr(ov, "_read_bytes", fake_read)
    monkeypatch.setattr(ov, "request_photo_aware_plan", lambda *a, **k: (_sample_plan(), 1))
    monkeypatch.setattr(ov, "request_overlay_bytes", lambda **k: (_png(overlay_im), "generations_magenta_chroma", 1))
    monkeypatch.setattr(ov, "verify_overlay_facts", lambda *a, **k: ({"pass": True, "mode": "mock"}, 0))
    monkeypatch.setattr(ov, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(ov, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        ov,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="medium", base_url="https://api.openai.com/v1"),
    )

    result = generate_creative_overlay_4x5(
        db, user, row, language="tr", revision=DIRECTION_R2, parent_asset_id=PARENT_R1_ASSET_ID
    )
    db.refresh(row)
    phase5 = dict((row.context_json or {}).get("phase5") or {})
    overlays = list(phase5.get("creative_overlay_tests") or [])
    assert result["workflow"] == WORKFLOW_ID_51D_R2
    assert result["parent_asset_id"] == PARENT_R1_ASSET_ID
    assert result["photo_awareness_used"] is True
    assert result["plan_executed_by_os"] is False
    assert result["os_compositor_primary_designer"] is False
    assert result["gpt_image_edit_calls"] == 0
    assert any(t.get("workflow") == WORKFLOW_ID_51D_R1 and t.get("final_asset_id") == PARENT_R1_ASSET_ID for t in overlays)
    assert any(t.get("workflow") == WORKFLOW_ID_51D for t in overlays)
    assert any(t.get("workflow") == WORKFLOW_ID_51D_R2 for t in overlays)
    db.rollback()
    db.close()
