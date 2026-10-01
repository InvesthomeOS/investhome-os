"""Phase 5.2B — visual art director. GPT Image designs; Day_004 never goes to edits."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_visual_art_director import (
    WORKFLOW_ID_52B,
    critic_pass,
    generate_visual_art_director_4x5,
    graphic_layer_prompt,
    overlay_has_architecture,
    request_graphic_layer,
    select_blueprints,
    validate_graphic_layer,
)
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


def _graphic_overlay() -> Image.Image:
    ov = Image.new("RGBA", CANVAS_4X5, (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle((820, 90, 1050, 1180), fill=(18, 24, 32, 170))
    return ov


def _photo_overlay() -> Image.Image:
    ov = Image.new("RGBA", CANVAS_4X5, (0, 0, 0, 0))
    r = Image.effect_noise((440, 720), 90)
    g = Image.effect_noise((440, 720), 55)
    b = Image.effect_noise((440, 720), 110)
    rgb = Image.merge("RGB", (r, g, b))
    ov.paste(rgb.convert("RGBA"), (int(CANVAS_4X5[0] * 0.30), int(CANVAS_4X5[1] * 0.10)))
    return ov


def _blueprints() -> list[dict]:
    return [
        {
            "schema": "VisualCreativeBlueprintV1",
            "label": "A",
            "pre_score": 8.4,
            "mode": "vision",
            "concept": "editorial mass in the right sky",
            "execution_regions": {
                "headline": {"x": 0.58, "y": 0.12, "w": 0.36, "h": 0.10},
                "price": {"x": 0.58, "y": 0.28, "w": 0.34, "h": 0.08},
                "commercial": {"x": 0.58, "y": 0.38, "w": 0.34, "h": 0.10},
                "cta": {"x": 0.58, "y": 0.52, "w": 0.28, "h": 0.06},
                "logo": {"x": 0.58, "y": 0.04, "w": 0.22, "h": 0.06},
            },
        },
        {
            "schema": "VisualCreativeBlueprintV1",
            "label": "B",
            "pre_score": 7.9,
            "mode": "vision",
            "concept": "cinematic lower-left lockup",
            "execution_regions": {
                "headline": {"x": 0.06, "y": 0.62, "w": 0.40, "h": 0.10},
                "price": {"x": 0.06, "y": 0.74, "w": 0.34, "h": 0.08},
                "commercial": {"x": 0.06, "y": 0.84, "w": 0.34, "h": 0.08},
                "cta": {"x": 0.06, "y": 0.92, "w": 0.26, "h": 0.05},
                "logo": {"x": 0.06, "y": 0.05, "w": 0.22, "h": 0.06},
            },
        },
        {
            "schema": "VisualCreativeBlueprintV1",
            "label": "C",
            "pre_score": 5.1,
            "mode": "vision",
            "concept": "held third concept",
            "execution_regions": {},
        },
    ]


def test_module_never_calls_images_edits() -> None:
    import investhome_api.services.creative_director.phase5_visual_art_director as vad

    src = inspect.getsource(vad)
    assert "edit_image" not in src
    assert "from investhome_api.services.gpt_image_design.client import" in src
    assert "generate_image" in src


def test_graphic_prompt_forbids_architecture() -> None:
    prompt = graphic_layer_prompt(_blueprints()[0], dict(REQUIRED_FACTS), chroma=False)
    folded = prompt.casefold()
    assert "do not draw buildings" in folded
    assert "transparent" in folded
    assert "alirken kazan" in folded
    assert "day_004" not in folded or "already exists underneath" in folded


def test_select_blueprints_renders_only_top_two() -> None:
    chosen = select_blueprints(_blueprints(), 2)
    assert [c["label"] for c in chosen] == ["A", "B"]


def test_overlay_architecture_reject() -> None:
    graphic = _graphic_overlay()
    photo = _photo_overlay()
    assert overlay_has_architecture(graphic)["detected"] is False
    assert overlay_has_architecture(photo)["detected"] is True
    assert validate_graphic_layer(photo)["pass"] is False
    assert "architecture_in_overlay" in validate_graphic_layer(photo)["flags"]
    assert validate_graphic_layer(graphic)["architecture_detected"] is False


def test_critic_gates() -> None:
    passing = {
        "architecture_truth": 10,
        "professional_design_quality": 8,
        "photo_design_integration": 8,
        "visual_hierarchy": 8,
        "typographic_sophistication": 8,
        "commercial_hierarchy": 8,
        "premium_character": 8,
        "text_on_photo_likeness": 3,
        "template_likeness": 3,
        "visual_clutter": 4,
    }
    assert critic_pass(passing) is True
    failing = dict(passing)
    failing["text_on_photo_likeness"] = 4
    assert critic_pass(failing) is False
    failing2 = dict(passing)
    failing2["professional_design_quality"] = 7
    assert critic_pass(failing2) is False
    failing3 = dict(passing)
    failing3["architecture_truth"] = 9
    assert critic_pass(failing3) is False


def test_request_graphic_layer_uses_generations_only(monkeypatch) -> None:
    import investhome_api.services.creative_director.phase5_visual_art_director as vad

    captured = []

    def fake_generate(**kwargs):
        captured.append(kwargs)
        raise AssertionError("generated")

    monkeypatch.setattr(vad, "generate_image", fake_generate)
    monkeypatch.setattr(vad, "openai_api_key", lambda: "sk-test")
    try:
        request_graphic_layer(
            _blueprints()[0],
            dict(REQUIRED_FACTS),
            SimpleNamespace(model="gpt-image-2", quality="high", base_url="http://example.invalid"),
        )
    except AssertionError:
        pass
    assert captured
    assert captured[0].get("background") == "transparent"
    assert captured[0].get("size") == "1088x1360"
    assert "images" not in captured[0]


def test_generate_does_not_touch_history_and_renders_two(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_visual_art_director as vad

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P52B-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    production = [{"workflow": "phase5_2_production_creative", "keep": True}]
    master_51e = [{"workflow": "phase5_1e_final_master", "keep": True}]
    overlay = [{"workflow": "phase5_1d_r2_photo_aware", "keep": True}]
    photo = [{"workflow": "phase5_1b_photo_foundation", "keep": True}]
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {"current_version": 2, "current_cover_asset_id": PRODUCTION_COVER_V2},
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {"5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}},
            "photo_foundation_tests": photo,
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": overlay,
            "creative_master_tests": master_51e,
            "production_creative_tests": production,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.2b test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    ImageDraw.Draw(hero).rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))
    graphic_calls = {"n": 0}

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return logo
        return _png(hero)

    def fake_graphic(blueprint, facts, availability):
        graphic_calls["n"] += 1
        return _png(_graphic_overlay()), "generations_transparent_png", 1

    monkeypatch.setattr(vad, "_read_bytes", fake_read)
    monkeypatch.setattr(vad, "analyze_reference_dna", lambda *_a, **_k: ({"schema": "CreativeReferenceAnalysisV1", "mode": "mock"}, 0))
    monkeypatch.setattr(
        vad,
        "request_protection_map",
        lambda *_a, **_k: ({"schema": "ProtectedArchitectureMapV1", "regions": {}, "mode": "mock"}, 0),
    )
    monkeypatch.setattr(vad, "request_visual_blueprints", lambda **_k: (_blueprints(), 1))
    monkeypatch.setattr(vad, "request_graphic_layer", fake_graphic)
    monkeypatch.setattr(
        vad,
        "request_design_critic",
        lambda **_k: (
            {
                "architecture_truth": 10,
                "professional_design_quality": 8,
                "photo_design_integration": 8,
                "visual_hierarchy": 8,
                "typographic_sophistication": 8,
                "commercial_hierarchy": 8,
                "premium_character": 8,
                "text_on_photo_likeness": 2,
                "template_likeness": 2,
                "visual_clutter": 2,
                "mode": "vision",
                "pass": True,
            },
            0,
        ),
    )
    monkeypatch.setattr(vad, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(vad, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(
        vad,
        "provider_availability",
        lambda: SimpleNamespace(model="gpt-image-2", quality="high", base_url="http://example.invalid", available=True),
    )

    result = generate_visual_art_director_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_52B
    assert result["architecture_generation_used"] is False
    assert result["gpt_image_edit_calls"] == 0
    assert result["graphic_generation_count"] == 2
    assert graphic_calls["n"] == 2
    assert result["candidates_rendered"] == 2
    assert result["final_size"] == list(CANVAS_4X5)
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("creative_master_tests") == master_51e
    assert phase5.get("creative_overlay_tests") == overlay
    assert phase5.get("photo_foundation_tests") == photo
    assert phase5.get("production_creative_tests") == production
    assert any(t.get("workflow") == WORKFLOW_ID_52B for t in phase5.get("visual_art_director_tests") or [])
    db.rollback()
    db.close()
