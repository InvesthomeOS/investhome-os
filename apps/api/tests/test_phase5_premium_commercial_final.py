"""Phase 5.4A — PREMIUM_COMMERCIAL finalization. Not live-routed."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_library import (
    MASTER_COMMERCIAL_FINAL_ID,
    MASTER_COMMERCIAL_ID,
    build_creative_master_library,
    build_premium_commercial_final_master,
    markup_has_semantic_slots,
    scene_premium_commercial,
    scene_premium_commercial_final,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_premium_commercial_final import (
    WORKFLOW_ID_54A,
    critic_fail_reasons,
    critic_pass_54a,
    generate_premium_commercial_final_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
)


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_final_is_child_of_master_b_not_a_new_family() -> None:
    library = build_creative_master_library()
    families = [m["creative_family"] for m in library["masters"]]
    assert families == ["EDITORIAL_ARCHITECTURAL", "PREMIUM_COMMERCIAL", "MINIMAL_LUXURY"]
    parent = scene_premium_commercial()
    child = scene_premium_commercial_final()
    assert parent != child
    assert "cta-wrap" in child
    assert "cta-wrap" not in parent
    assert "54px" in child or "font-size:54px" in child
    master = build_premium_commercial_final_master()
    assert master["master_id"] == MASTER_COMMERCIAL_FINAL_ID
    assert master["master_id"] != MASTER_COMMERCIAL_ID
    assert master["creative_family"] == "PREMIUM_COMMERCIAL"
    assert master["approval_status"] == "CANDIDATE_PENDING_HUMAN_REVIEW"
    assert markup_has_semantic_slots(child)
    assert "438.750" not in child
    assert "ALIRKEN KAZAN" in child
    assert "675.000 USD" in child
    assert "dejavu" not in child.casefold()


def test_critic_gate_matches_phase_54a_thresholds() -> None:
    passing = {
        "professional_design_quality": 8,
        "photo_design_integration": 8,
        "visual_hierarchy": 8,
        "typographic_sophistication": 8,
        "commercial_hierarchy": 8,
        "premium_character": 8,
        "readability": 8,
        "architecture_respect": 9,
        "text_on_photo_likeness": 3,
        "template_likeness": 3,
        "visual_clutter": 3,
    }
    assert critic_pass_54a(passing) is True
    failing = dict(passing)
    failing["commercial_hierarchy"] = 7
    assert critic_pass_54a(failing) is False
    assert "commercial_hierarchy=7.0 < 8" in critic_fail_reasons(failing)


def test_modules_do_not_use_gpt_image_or_live_generate() -> None:
    import investhome_api.services.creative_director.phase5_premium_commercial_final as prod

    src = inspect.getsource(prod)
    assert "generate_image" not in src
    assert "edit_image" not in src
    assert "generate_ad_phase5" not in src
    assert '"live_routing_active": False' in src


def test_generate_does_not_touch_history_or_activate_routing(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_premium_commercial_final as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54A-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    library = [{"workflow": "phase5_4_production_masters", "keep": True}]
    scene = [{"workflow": "phase5_3_ai_design_scene", "keep": True}]
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
            "photo_foundation_tests": [{"keep": True}],
            "creative_design_tests": [{"keep": True}],
            "creative_overlay_tests": [{"keep": True}],
            "creative_master_tests": [{"keep": True}],
            "production_creative_tests": [{"keep": True}],
            "visual_art_director_tests": [{"keep": True}],
            "design_scene_tests": scene,
            "creative_master_library_tests": library,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4a test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    ImageDraw.Draw(hero).rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="32"></svg>'
        return _png(hero)

    monkeypatch.setattr(pm, "_read_bytes", fake_read)
    monkeypatch.setattr(pm, "render_html_to_png", lambda *_a, **_k: Image.new("RGB", CANVAS_4X5, (30, 40, 50)))
    monkeypatch.setattr(pm, "font_face_css", lambda *_a, **_k: "")
    monkeypatch.setattr(pm, "request_final_critic", lambda **_k: ({"professional_design_quality": 8, "pass": True, "mode": "vision", "fail_reasons": []}, 1))
    monkeypatch.setattr(pm, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))

    result = generate_premium_commercial_final_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54A
    assert result["live_routing_active"] is False
    assert result["gpt_image_calls"] == 0
    assert result["architecture_generation_used"] is False
    assert result["design_family"] == "PREMIUM_COMMERCIAL"
    assert result["parent_master_id"] == MASTER_COMMERCIAL_ID
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("creative_master_library_tests") == library
    assert phase5.get("design_scene_tests") == scene
    db.rollback()
    db.close()
