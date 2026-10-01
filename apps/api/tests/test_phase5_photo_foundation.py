"""Phase 5.1B — immutable Day_004 photo foundation. Uniform crop only. No second patch."""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
    generate_photo_foundation_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
)
from investhome_api.services.gpt_image_design.compose import CompositionResult


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


def test_cover_fit_is_uniform_and_records_crop() -> None:
    src = _day004_like()
    canvas, transform = cover_fit_canvas(src, CANVAS_4X5, centering=(0.78, 0.42))
    assert canvas.size == CANVAS_4X5
    assert transform["scale_x"] == transform["scale_y"]
    assert transform["non_uniform_scale"] is False
    assert transform["source_scale"] == transform["scale_x"]
    crop = transform["source_crop"]
    assert len(crop) == 4
    assert crop[2] > crop[0]
    assert crop[3] > crop[1]
    qa = architecture_provenance_qa(source=src, foundation=canvas, final=canvas, transform=transform)
    assert qa["architecture_generation_used"] is False
    assert qa["non_uniform_scale"] is False
    assert qa["second_photo_patch"] is False
    assert qa["duplicated_architecture"] is False
    assert qa["status"] == "pass"


def test_photographic_grade_does_not_change_geometry() -> None:
    src = Image.new("RGB", CANVAS_4X5, (180, 160, 140))
    graded = apply_photographic_grade(src, {"warmth": 0.2, "contrast": 1.1, "brightness": 0.95, "vignette": 0.2})
    assert graded.size == src.size


def test_provenance_fails_non_uniform_scale() -> None:
    src = _day004_like()
    canvas, transform = cover_fit_canvas(src, CANVAS_4X5)
    transform["scale_x"] = 1.2
    transform["scale_y"] = 0.9
    qa = architecture_provenance_qa(source=src, foundation=canvas, final=canvas, transform=transform)
    assert qa["non_uniform_scale"] is True
    assert qa["status"] == "fail"


def test_photo_foundation_generate_does_not_touch_history(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_photo_foundation as pf

    db = SessionLocal()
    existing = db.get(Project, UUID(TEMPLE_PROJECT_ID))
    if existing is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P51B-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    master_id = "5765e350-06f5-45d6-9e70-a63cd4dd2072"
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
            "approved_masters": {master_id: {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}},
            "architecture_lock_tests": lock_tests,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": master_id}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.1b test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()

    hero = _png(_day004_like())
    logo = _png(Image.new("RGBA", (80, 40), (201, 168, 92, 255)))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return hero

    fake_asset_id = uuid4()

    monkeypatch.setattr(pf, "_read_bytes", fake_read)
    monkeypatch.setattr(
        pf,
        "request_photographic_art_direction",
        lambda *a, **k: (
            {
                "treatment": "warm_editorial",
                "grade": {"warmth": 0.1, "contrast": 1.05, "brightness": 1.0, "vignette": 0.1},
                "composition_family": "editorial_hero",
                "headline_color": "#F4E7C3",
                "mode": "vision",
            },
            1,
        ),
    )
    monkeypatch.setattr(
        pf,
        "run_visual_layout_director",
        lambda **k: SimpleNamespace(
            mode="heuristic",
            design_plan=SimpleNamespace(layers=[]),
            layout_plan=SimpleNamespace(composition_family="editorial_hero"),
        ),
    )
    monkeypatch.setattr(
        pf,
        "render_layout_plan",
        lambda base_bytes, **k: CompositionResult(png_bytes=base_bytes),
    )
    monkeypatch.setattr(
        pf,
        "persist_gpt_image",
        lambda *a, **k: SimpleNamespace(id=fake_asset_id),
    )
    monkeypatch.setattr(pf, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(pf, "openai_api_key", lambda: "test-key")

    result = generate_photo_foundation_4x5(db, user, row, language="tr")
    db.flush()
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["architecture_generation_used"] is False
    assert result["second_photo_patch"] is False
    assert result["duplicated_architecture"] is False
    assert result["non_uniform_scale"] is False
    assert result["gpt_image_2_calls"] == 0
    assert result["final_size"] == list(CANVAS_4X5)
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("current_format_family_id") == "2f29711d-285c-4e6d-a1b8-5b058eeb58b4"
    assert "3647f302-325a-4f12-b3e6-07b005131485" in str(phase5.get("approved_masters"))
    assert phase5.get("architecture_lock_tests") == lock_tests
    assert len(phase5.get("photo_foundation_tests") or []) == 1
    db.rollback()
    db.close()
