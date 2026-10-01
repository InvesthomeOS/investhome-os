"""Phase 5.4 — production master library. Not live-routed."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_library import (
    MASTER_COMMERCIAL_ID,
    MASTER_EDITORIAL_ID,
    MASTER_MINIMAL_ID,
    build_creative_master_library,
    families_are_distinct,
    markup_has_semantic_slots,
    route_creative_master,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_production_masters import (
    WORKFLOW_ID_54,
    generate_production_masters_4x5,
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


def test_library_has_three_distinct_editable_masters() -> None:
    library = build_creative_master_library()
    families = [m["creative_family"] for m in library["masters"]]
    assert families == ["EDITORIAL_ARCHITECTURAL", "PREMIUM_COMMERCIAL", "MINIMAL_LUXURY"]
    assert families_are_distinct(library) is True
    assert library["live_routing_active"] is False
    assert library["user_facing_templates"] is False
    for master in library["masters"]:
        assert master["approval_status"] == "CANDIDATE_PENDING_HUMAN_REVIEW"
        assert master["scene_type"] == "HTML_SVG"
        assert markup_has_semantic_slots(master["scene_markup"])
        assert "{{PHOTO_SRC}}" in master["scene_markup"]
        assert "{{LOGO_MARKUP}}" in master["scene_markup"]
        assert "ALIRKEN KAZAN" in master["scene_markup"]
        assert "675.000 USD" in master["scene_markup"]
        assert "dejavu" not in master["scene_markup"].casefold()
    ref = library["reference_library"]
    assert ref["schema"] == "CreativeReferenceLibraryV1"
    assert ref["forbidden_use"] == "do_not_generate_production_scenes_from_zero"
    assert library["learning_store"]["ml_training_active"] is False


def test_router_is_internal_and_selects_by_brief() -> None:
    editorial = route_creative_master(user_brief="The Temple için ALIRKEN KAZAN reklamı hazırla.")
    assert editorial["selected_master_id"] == MASTER_EDITORIAL_ID
    assert editorial["user_visible"] is False
    assert editorial["live_routing_active"] is False
    commercial = route_creative_master(user_brief="Lansman fiyatını ve %35 avantajı öne çıkar.")
    assert commercial["selected_master_id"] == MASTER_COMMERCIAL_ID
    minimal = route_creative_master(user_brief="Sade, marka odaklı, az metinli bir tasarım.")
    assert minimal["selected_master_id"] == MASTER_MINIMAL_ID


def test_modules_do_not_use_gpt_image_or_live_generate() -> None:
    import investhome_api.services.creative_director.creative_master_library as lib
    import investhome_api.services.creative_director.phase5_production_masters as prod

    for mod in (lib, prod):
        src = inspect.getsource(mod)
        assert "generate_image" not in src
        assert "edit_image" not in src
        assert "generate_ad_phase5" not in src


def test_generate_does_not_touch_history_or_activate_routing(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_production_masters as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    scene = [{"workflow": "phase5_3_ai_design_scene", "keep": True}]
    vad = [{"workflow": "phase5_2b_visual_art_director", "keep": True}]
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
            "photo_foundation_tests": [{"workflow": "phase5_1b_photo_foundation", "keep": True}],
            "creative_design_tests": [{"keep": True}],
            "creative_overlay_tests": [{"keep": True}],
            "creative_master_tests": [{"keep": True}],
            "production_creative_tests": [{"keep": True}],
            "visual_art_director_tests": vad,
            "design_scene_tests": scene,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {"approved_master": {"master_id": "x"}}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4 test",
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
    monkeypatch.setattr(pm, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))

    result = generate_production_masters_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54
    assert result["live_routing_active"] is False
    assert result["gpt_image_calls"] == 0
    assert result["architecture_generation_used"] is False
    assert len(result["masters_created"]) == 3
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("current_session_id") == "5a51b242-374d-4b5f-b69c-ccd29ae410d6"
    assert phase5.get("design_scene_tests") == scene
    assert phase5.get("visual_art_director_tests") == vad
    db.rollback()
    db.close()
