"""Phase 5.1C — AI art direction over locked Day_004 photo foundation."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_art_direction import (
    analyze_scene_heuristic,
    plan_from_scene,
    quality_gate,
)
from investhome_api.services.creative_director.phase5_creative_design import (
    CANVAS_4X5,
    generate_creative_design_4x5,
    render_creative_plan,
)
from investhome_api.services.creative_director.phase5_photo_foundation import cover_fit_canvas
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _day004_like() -> Image.Image:
    im = Image.new("RGB", (2268, 1234), (176, 196, 214))
    draw = ImageDraw.Draw(im)
    draw.rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    draw.rectangle((1680, 80, 1820, 280), fill=(208, 198, 180))
    draw.polygon([(1750, 20), (1680, 80), (1820, 80)], fill=(200, 188, 168))
    for r in range(8):
        for c in range(5):
            x = 1460 + c * 110
            y = 360 + r * 80
            draw.rectangle((x, y, x + 48, y + 42), fill=(42, 48, 58))
    return im


def test_photo_foundation_still_uniform() -> None:
    canvas, transform = cover_fit_canvas(_day004_like(), CANVAS_4X5, centering=(0.78, 0.42))
    assert canvas.size == CANVAS_4X5
    assert transform["scale_x"] == transform["scale_y"]
    assert transform["non_uniform_scale"] is False


def test_scene_analysis_is_image_specific_not_a_template() -> None:
    left_tower = Image.new("RGB", CANVAS_4X5, (180, 200, 220))
    ImageDraw.Draw(left_tower).rectangle((80, 40, 220, 900), fill=(210, 200, 180))
    right_tower = Image.new("RGB", CANVAS_4X5, (180, 200, 220))
    ImageDraw.Draw(right_tower).rectangle((820, 40, 1000, 900), fill=(210, 200, 180))
    left = analyze_scene_heuristic(left_tower)
    right = analyze_scene_heuristic(right_tower)
    assert left.spire is not None and right.spire is not None
    assert left.spire.x < right.spire.x
    plan = plan_from_scene(right, facts=dict(REQUIRED_FACTS), mode="heuristic")
    assert plan.created_before_render is True
    assert plan.template_id is None
    assert plan.photograph_role == "immutable_project_foundation"


def test_render_keeps_architecture_and_avoids_spire() -> None:
    src = _day004_like()
    foundation, transform = cover_fit_canvas(src, CANVAS_4X5, centering=(0.78, 0.42))
    scene = analyze_scene_heuristic(foundation)
    plan = plan_from_scene(scene, facts=dict(REQUIRED_FACTS), mode="heuristic")
    logo = ResolvedSourceImage(
        asset_id=UUID(LOCKED_LOGO_ASSET_ID),
        filename="logo.png",
        content_type="image/png",
        folder_category=None,
        tags=[],
        image_bytes=_png(Image.new("RGBA", (200, 80), (201, 168, 92, 255))),
        role="project_logo",
    )
    rendered = render_creative_plan(foundation, plan=plan, scene=scene, logo=logo, facts=dict(REQUIRED_FACTS))
    assert rendered["image"].size == CANVAS_4X5
    assert transform["non_uniform_scale"] is False
    assert rendered["logo_meta"]["placed"] is True
    gate = quality_gate(
        image=rendered["image"],
        foundation=rendered["graded"],
        plan=plan,
        scene=scene,
        boxes=rendered["boxes"],
        logo_meta=rendered["logo_meta"],
        facts=dict(REQUIRED_FACTS),
        panel_coverage=rendered["panel_coverage"],
    )
    assert gate["headline_spire_collision"] is False
    assert gate["template_id"] is None
    assert "feathered_gradient" in rendered["capabilities_used"]


def test_creative_design_does_not_touch_history(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_design as cd

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51C-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    photo_tests = [{"workflow": "phase5_1b_photo_foundation", "keep": True}]
    lock_tests = [{"family_id": "b03ea335-7214-4754-b47a-5e912eb4b7e4", "keep": True}]
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
            "approved_masters": {"5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}},
            "architecture_lock_tests": lock_tests,
            "photo_foundation_tests": photo_tests,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "5765e350-06f5-45d6-9e70-a63cd4dd2072"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1c test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    monkeypatch.setattr(cd, "_read_bytes", fake_read)
    monkeypatch.setattr(
        cd,
        "request_creative_art_direction",
        lambda foundation, facts, retry_feedback=None: (
            analyze_scene_heuristic(foundation),
            plan_from_scene(analyze_scene_heuristic(foundation), facts=facts, mode="heuristic"),
            0,
        ),
    )
    fake_id = uuid4()
    monkeypatch.setattr(cd, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=fake_id))
    monkeypatch.setattr(cd, "asset_url", lambda _id: f"/media/{_id}")

    result = generate_creative_design_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["architecture_generation_used"] is False
    assert result["second_photo_patch"] is False
    assert result["plan"]["created_before_render"] is True
    assert result["plan"]["template_id"] is None
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("current_format_family_id") == "2f29711d-285c-4e6d-a1b8-5b058eeb58b4"
    assert phase5.get("photo_foundation_tests") == photo_tests
    assert phase5.get("architecture_lock_tests") == lock_tests
    db.rollback()
    db.close()
