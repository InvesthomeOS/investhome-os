"""Phase 5.4A-R1 — offer lockup + CTA polish. Does not overwrite 5.4A."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_library import (
    MASTER_COMMERCIAL_FINAL_ID,
    MASTER_COMMERCIAL_R1_ID,
    scene_premium_commercial_final,
    scene_premium_commercial_r1,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import (
    WORKFLOW_ID_54A_R1,
    critic_pass_r1,
    generate_premium_commercial_r1_4x5,
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


def test_r1_only_changes_offer_and_cta() -> None:
    parent = scene_premium_commercial_final()
    child = scene_premium_commercial_r1()
    assert parent != child
    assert "left:40px;top:112px" in child.replace("\n", "")
    assert "right:40px;top:72px" in child.replace("\n", "")
    assert "logo{position:absolute;left:40px;top:30px;width:156px;}" in child.replace("\n", "")
    assert 'class="offer"' in child
    assert 'class="offer"' not in parent
    assert "min-width:420px" in child
    assert "438.750" not in child
    assert child.count("ALIRKEN") >= 1
    assert "675.000 USD" in child
    assert MASTER_COMMERCIAL_R1_ID != MASTER_COMMERCIAL_FINAL_ID


def test_r1_critic_ignores_text_on_photo_metric() -> None:
    scores = {
        "professional_design_quality": 8,
        "photo_design_integration": 8,
        "visual_hierarchy": 8,
        "typographic_sophistication": 8,
        "commercial_hierarchy": 8,
        "premium_character": 8,
        "readability": 8,
        "architecture_respect": 9,
        "text_on_photo_likeness": 8,
        "template_likeness": 3,
        "visual_clutter": 2,
    }
    assert critic_pass_r1(scores) is True


def test_r1_module_does_not_use_gpt_image() -> None:
    import investhome_api.services.creative_director.phase5_premium_commercial_r1 as prod

    src = inspect.getsource(prod)
    assert "generate_image" not in src
    assert "edit_image" not in src
    assert '"live_routing_active": False' in src


def test_r1_does_not_overwrite_54a_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_premium_commercial_r1 as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54AR1-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    final54a = [{"workflow": "phase5_4a_premium_commercial_final", "keep": True}]
    library = [{"workflow": "phase5_4_production_masters", "keep": True}]
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "latest_master_ad_asset_id": PRODUCTION_COVER_V2,
        "finished_ad_raster_asset_id": PRODUCTION_COVER_V2,
        "master_creative": {"current_version": 2, "current_cover_asset_id": PRODUCTION_COVER_V2},
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_masters": {},
            "photo_foundation_tests": [{"keep": True}],
            "creative_design_tests": [{"keep": True}],
            "creative_overlay_tests": [{"keep": True}],
            "creative_master_tests": [{"keep": True}],
            "production_creative_tests": [{"keep": True}],
            "visual_art_director_tests": [{"keep": True}],
            "design_scene_tests": [{"keep": True}],
            "creative_master_library_tests": library,
            "premium_commercial_final_tests": final54a,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4a-r1 test",
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
    monkeypatch.setattr(pm, "_render_scene", lambda *a, **k: {
        "assembled_markup": "",
        "persistable_markup": "",
        "gate": {"pass": True, "flags": []},
        "semantic_ok": True,
        "image": Image.new("RGB", CANVAS_4X5, (30, 40, 50)),
    })
    monkeypatch.setattr(pm, "font_face_css", lambda *_a, **_k: "")
    monkeypatch.setattr(pm, "request_final_critic", lambda **_k: ({
        "professional_design_quality": 8,
        "photo_design_integration": 8,
        "visual_hierarchy": 8,
        "typographic_sophistication": 8,
        "commercial_hierarchy": 8,
        "premium_character": 8,
        "readability": 8,
        "architecture_respect": 9,
        "text_on_photo_likeness": 8,
        "template_likeness": 2,
        "visual_clutter": 2,
        "mode": "vision",
        "pass": False,
        "fail_reasons": ["text_on_photo_likeness=8.0 > 3"],
    }, 1))
    monkeypatch.setattr(pm, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))

    result = generate_premium_commercial_r1_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54A_R1
    assert result["live_routing_active"] is False
    assert result["photo_crop_changed"] is False
    assert result["photo_grade_changed"] is False
    assert result["hard_gate"] is True
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_final_tests") == final54a
    assert phase5.get("creative_master_library_tests") == library
    db.rollback()
    db.close()
