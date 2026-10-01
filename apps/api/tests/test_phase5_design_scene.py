"""Phase 5.3 — AI design scene. Browser renders; GPT Image is not the designer."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.phase5_design_scene import (
    MAX_ATTEMPTS,
    WORKFLOW_ID_53,
    assemble_scene,
    critic_pass,
    generate_design_scene_4x5,
    validate_scene,
    wrap_html,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
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


def _fixture_markup() -> str:
    return """
    <svg xmlns="http://www.w3.org/2000/svg" width="1088" height="1360" viewBox="0 0 1088 1360">
      <image data-semantic="project_photo" href="{{PHOTO_SRC}}" x="0" y="0" width="1088" height="1360" preserveAspectRatio="xMidYMid slice"/>
      <g transform="translate(48,48)">{{LOGO_MARKUP}}</g>
      <text data-semantic="headline" x="620" y="180" font-family="Cormorant Garamond" font-size="72" fill="#F6F1E8">ALIRKEN KAZAN</text>
      <text data-semantic="price" x="620" y="280" font-family="Cormorant Garamond" font-size="48" fill="#F6F1E8">675.000 USD</text>
      <text data-semantic="discount" x="620" y="340" font-family="Source Sans 3" font-size="22" fill="#C9A85C">%35</text>
      <text data-semantic="discount_label" x="690" y="340" font-family="Source Sans 3" font-size="18" fill="#F6F1E8">LANSMAN AVANTAJI</text>
      <text data-semantic="unit_type" x="620" y="390" font-family="Source Sans 3" font-size="18" fill="#F6F1E8">2+1 DAİRE</text>
      <text data-semantic="cta" x="620" y="460" font-family="Source Sans 3" font-size="16" fill="#F6F1E8">PROJEYİ KEŞFET</text>
    </svg>
    """


def test_module_does_not_use_gpt_image() -> None:
    import investhome_api.services.creative_director.phase5_design_scene as ds

    src = inspect.getsource(ds)
    assert "generate_image" not in src
    assert "edit_image" not in src


def test_assemble_and_validate_real_photo_and_semantics() -> None:
    photo = "data:image/jpeg;base64,QUJD"
    logo = '<svg data-semantic="project_logo" xmlns="http://www.w3.org/2000/svg"></svg>'
    assembled = assemble_scene(_fixture_markup(), photo_uri=photo, logo_markup=logo, font_css="@font-face{}")
    html = wrap_html(assembled, "@font-face{}")
    gate = validate_scene(html, dict(REQUIRED_FACTS), photo)
    assert photo in assembled
    assert "data-semantic=\"project_photo\"" in assembled
    assert "data-semantic=\"project_logo\"" in assembled
    assert gate["pass"] is True
    assert gate["semantic_editability"] is True
    assert gate["text_accuracy"] is True


def test_validate_rejects_missing_photo_and_remote_image() -> None:
    bad = '<img data-semantic="headline" src="https://example.com/fake-tower.jpg"/>'
    gate = validate_scene(bad, dict(REQUIRED_FACTS), "data:image/jpeg;base64,XXX")
    assert gate["pass"] is False
    assert "project_photo_src_missing" in gate["flags"]
    assert "remote_image_forbidden" in gate["flags"]


def test_critic_gates() -> None:
    passing = {
        "architecture_truth": 10,
        "professional_design_quality": 8,
        "photo_design_integration": 8,
        "typographic_sophistication": 8,
        "visual_hierarchy": 8,
        "commercial_readability": 8,
        "premium_character": 8,
        "text_on_photo_likeness": 3,
        "template_likeness": 3,
        "visual_clutter": 4,
        "ornament_overuse": 3,
    }
    assert critic_pass(passing) is True
    failing = dict(passing)
    failing["ornament_overuse"] = 4
    assert critic_pass(failing) is False
    failing2 = dict(passing)
    failing2["professional_design_quality"] = 7
    assert critic_pass(failing2) is False


def _history_ctx() -> dict:
    return {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {"current_version": 2, "current_cover_asset_id": PRODUCTION_COVER_V2},
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {"5765e350-06f5-45d6-9e70-a63cd4dd2072": {"master_asset_id": "3647f302-325a-4f12-b3e6-07b005131485"}},
            "photo_foundation_tests": [{"workflow": "phase5_1b_photo_foundation", "keep": True}],
            "creative_design_tests": [{"workflow": "phase5_1c_creative_design", "keep": True}],
            "creative_overlay_tests": [{"workflow": "phase5_1d_r2_photo_aware", "keep": True}],
            "creative_master_tests": [{"workflow": "phase5_1e_final_master", "keep": True}],
            "production_creative_tests": [{"workflow": "phase5_2_production_creative", "keep": True}],
            "visual_art_director_tests": [{"workflow": "phase5_2b_visual_art_director", "keep": True}],
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }


def test_generate_does_not_touch_history_or_call_gpt_image(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_design_scene as ds

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P53-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    ctx = _history_ctx()
    vad = list(ctx["phase5"]["visual_art_director_tests"])
    production = list(ctx["phase5"]["production_creative_tests"])
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.3 test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    ImageDraw.Draw(hero).rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    logo = _png(Image.new("RGBA", (200, 80), (201, 168, 92, 255)))
    scene_calls = {"n": 0}

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="32"></svg>'
        return _png(hero)

    def fake_scene(**_k):
        scene_calls["n"] += 1
        return (
            {
                "schema": "AICreativeSceneV1",
                "scene_id": str(uuid4()),
                "scene_type": "SVG",
                "markup": _fixture_markup(),
                "mode": "vision",
                "concept": "test",
                "semantic_elements": [],
                "relationships": {},
                "layers": [],
            },
            1,
        )

    monkeypatch.setattr(ds, "_read_bytes", fake_read)
    monkeypatch.setattr(ds, "analyze_reference_dna", lambda *_a, **_k: ({"schema": "CreativeReferenceAnalysisV1", "mode": "mock"}, 0))
    monkeypatch.setattr(ds, "request_protection_map", lambda *_a, **_k: ({"schema": "ProtectedArchitectureMapV1", "regions": {}, "mode": "mock"}, 0))
    monkeypatch.setattr(ds, "request_photo_analysis", lambda *_a, **_k: ({"schema": "PhotoAnalysisV1", "reading": "spire left", "mode": "mock"}, 0))
    monkeypatch.setattr(ds, "request_scene", fake_scene)
    monkeypatch.setattr(ds, "render_html_to_png", lambda *_a, **_k: Image.new("RGB", CANVAS_4X5, (40, 50, 60)))
    monkeypatch.setattr(
        ds,
        "request_design_critic",
        lambda **_k: (
            {
                "architecture_truth": 10,
                "professional_design_quality": 8,
                "photo_design_integration": 8,
                "typographic_sophistication": 8,
                "visual_hierarchy": 8,
                "commercial_readability": 8,
                "premium_character": 8,
                "text_on_photo_likeness": 2,
                "template_likeness": 2,
                "visual_clutter": 2,
                "ornament_overuse": 1,
                "mode": "vision",
                "pass": True,
            },
            0,
        ),
    )
    monkeypatch.setattr(ds, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(ds, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(ds, "font_face_css", lambda *_a, **_k: "")

    result = generate_design_scene_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_53
    assert result["architecture_generation_used"] is False
    assert result["gpt_image_calls"] == 0
    assert result["gpt_image_edit_calls"] == 0
    assert result["final_size"] == list(CANVAS_4X5)
    assert result["scene_attempts"] == 1
    assert scene_calls["n"] == 1
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("visual_art_director_tests") == vad
    assert phase5.get("production_creative_tests") == production
    assert any(t.get("workflow") == WORKFLOW_ID_53 for t in phase5.get("design_scene_tests") or [])
    db.rollback()
    db.close()


def test_generate_stops_after_three_failed_attempts(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_design_scene as ds

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P53F-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.3 fail loop",
        context_json=_history_ctx(),
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    scene_calls = {"n": 0}

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return b'<svg xmlns="http://www.w3.org/2000/svg"></svg>'
        return _png(hero)

    def fake_scene(**_k):
        scene_calls["n"] += 1
        return (
            {
                "schema": "AICreativeSceneV1",
                "scene_id": str(uuid4()),
                "scene_type": "SVG",
                "markup": _fixture_markup(),
                "mode": "vision",
                "concept": "retry",
                "semantic_elements": [],
                "relationships": {},
                "layers": [],
            },
            1,
        )

    monkeypatch.setattr(ds, "_read_bytes", fake_read)
    monkeypatch.setattr(ds, "analyze_reference_dna", lambda *_a, **_k: ({}, 0))
    monkeypatch.setattr(ds, "request_protection_map", lambda *_a, **_k: ({"regions": {}}, 0))
    monkeypatch.setattr(ds, "request_photo_analysis", lambda *_a, **_k: ({"reading": "x"}, 0))
    monkeypatch.setattr(ds, "request_scene", fake_scene)
    monkeypatch.setattr(ds, "render_html_to_png", lambda *_a, **_k: Image.new("RGB", CANVAS_4X5, (40, 50, 60)))
    monkeypatch.setattr(
        ds,
        "request_design_critic",
        lambda **_k: (
            {
                "architecture_truth": 10,
                "professional_design_quality": 6,
                "photo_design_integration": 6,
                "typographic_sophistication": 6,
                "visual_hierarchy": 6,
                "commercial_readability": 6,
                "premium_character": 6,
                "text_on_photo_likeness": 6,
                "template_likeness": 5,
                "visual_clutter": 5,
                "ornament_overuse": 5,
                "critique": "Still text on a photo. Rebuild the commercial system as one editorial mass.",
                "mode": "vision",
                "pass": False,
            },
            0,
        ),
    )
    monkeypatch.setattr(ds, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))
    monkeypatch.setattr(ds, "asset_url", lambda _id: f"/media/{_id}")
    monkeypatch.setattr(ds, "font_face_css", lambda *_a, **_k: "")

    result = generate_design_scene_4x5(db, user, row, language="tr")
    assert scene_calls["n"] == MAX_ATTEMPTS
    assert result["scene_attempts"] == 3
    assert result["campaign_plausible"] is False
    assert result["stopped_after_critic_failure"] is True
    assert result["gpt_image_calls"] == 0
    db.rollback()
    db.close()
