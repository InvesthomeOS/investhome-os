"""Phase 5.5 — approved master lock + PRICE_REVISION. Does not execute Test B."""

from __future__ import annotations

import inspect
from io import BytesIO
from types import SimpleNamespace
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_creative_master import (
    HUMAN_APPROVED,
    build_approved_creative_master,
    restore_parent_scene,
)
from investhome_api.services.creative_director.creative_master_library import (
    APPROVED_R1_ASSET_ID,
    LOCKED_R1_CHROME,
    MASTER_COMMERCIAL_R1_ID,
    MASTER_PRICE_REVISION_V2_ID,
    scene_premium_commercial_price_revision,
    scene_premium_commercial_r1,
)
from investhome_api.services.creative_director.creative_revision_controller import (
    PRICE_REVISION,
    TEST_A_INSTRUCTION,
    VISUAL_REPLACE,
    build_revision_intent,
    classify_revision_intent,
    parse_price_revision,
    plan_visual_replace,
)
from investhome_api.services.creative_director.phase5_master_revision import (
    WORKFLOW_ID_55,
    compare_preservation,
    generate_master_revision_4x5,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import (
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
)


def _png(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _child_markup() -> str:
    return scene_premium_commercial_price_revision(
        {
            "list_price": "438.750 USD",
            "launch_price": "438.750 USD",
            "list_price_struck": "675.000 USD",
            "savings": "236.250 USD",
            "savings_label": "KAZANCINIZ",
        }
    )


def test_test_a_classifies_as_price_revision() -> None:
    assert classify_revision_intent(TEST_A_INSTRUCTION) == PRICE_REVISION
    intent = build_revision_intent(approved_master_id=MASTER_COMMERCIAL_R1_ID, instruction=TEST_A_INSTRUCTION)
    assert intent["revision_scope"] == PRICE_REVISION
    assert intent["groups_requiring_reflow"] == ["commercial"]
    assert "headline" in intent["groups_untouched"]
    assert "logo" in intent["groups_untouched"]
    values = parse_price_revision(TEST_A_INSTRUCTION)
    assert values["launch_price"] == "438.750 USD"
    assert values["list_price_struck"] == "675.000 USD"
    assert values["savings"] == "236.250 USD"


def test_visual_replace_architecture_is_ready_not_executed() -> None:
    instruction = (
        "Bu görsel yerine Media Library’deki diğer onaylı dış cephe görselini kullan. "
        "Başka hiçbir şeyi değiştirme."
    )
    assert classify_revision_intent(instruction) == VISUAL_REPLACE
    plan = plan_visual_replace(instruction, {"master_id": MASTER_COMMERCIAL_R1_ID})
    assert plan["executed"] is False
    assert plan["rules"]["no_ai_generated_building"] is True
    intent = build_revision_intent(approved_master_id=MASTER_COMMERCIAL_R1_ID, instruction=instruction)
    assert intent["new_source_asset_required"] is True
    assert intent.get("execute") is not True


def test_approved_master_is_human_approved_structured_state() -> None:
    master = build_approved_creative_master()
    assert master["approval_status"] == HUMAN_APPROVED
    assert master["approved_asset_id"] == APPROVED_R1_ASSET_ID
    assert master["master_id"] == MASTER_COMMERCIAL_R1_ID
    assert "scene_markup" in master
    assert "675.000 USD" in master["scene_markup"]
    assert master["critic_may_not_reopen_art_direction"] is True
    assert "commercial" in master["editable_groups"]
    assert "logo" in master["immutable_groups"]


def test_price_revision_scene_reflows_commercial_only() -> None:
    parent = scene_premium_commercial_r1()
    child = _child_markup()
    compact_parent = parent.replace("\n", "")
    compact_child = child.replace("\n", "")
    assert "438.750" not in parent
    assert "438.750 USD" in child
    assert 'data-state="struck"' in child
    assert "675.000 USD" in child
    assert "KAZANCINIZ" in child
    assert "236.250 USD" in child
    assert "left:40px;top:30px;width:156px" in compact_child
    assert "left:40px;top:112px;width:252px" in compact_child
    assert "bottom:118px" in compact_child
    assert "right:40px;top:72px;width:456px" in compact_child
    assert LOCKED_R1_CHROME.replace("\n", "") in compact_child
    assert "ALIRKEN" in child and "KAZAN" in child
    assert "2+1" in child and "DAİRE" in child
    assert "PROJEYİ KEŞFET" in child
    assert parent != child
    assert MASTER_PRICE_REVISION_V2_ID != MASTER_COMMERCIAL_R1_ID


def test_revision_is_reversible() -> None:
    master = build_approved_creative_master()
    parent_scene = master["scene_markup"]
    from investhome_api.services.creative_director.approved_creative_master import append_revision

    revised = append_revision(
        master,
        {
            "revision_id": MASTER_PRICE_REVISION_V2_ID,
            "parent_master_id": MASTER_COMMERCIAL_R1_ID,
            "parent_scene_markup": parent_scene,
            "parent_semantic_content": dict(master["semantic_content"]),
            "revision_number": 2,
        },
    )
    restored = restore_parent_scene(revised, MASTER_PRICE_REVISION_V2_ID)
    assert restored["restored_master_id"] == MASTER_COMMERCIAL_R1_ID
    assert restored["scene_markup"] == parent_scene


def test_preservation_fails_on_locked_group_change() -> None:
    parent = Image.new("RGB", CANVAS_4X5, (40, 50, 60))
    ok = parent.copy()
    ImageDraw.Draw(ok).rectangle((600, 80, 1000, 240), fill=(200, 180, 90))
    assert compare_preservation(parent, ok)["pass"] is True
    leaked = ok.copy()
    ImageDraw.Draw(leaked).rectangle((40, 30, 180, 90), fill=(10, 10, 10))
    failed = compare_preservation(parent, leaked)
    assert failed["pass"] is False
    assert any(item.startswith("logo_") for item in failed["unexpected_changes"])


def test_modules_do_not_use_gpt_image() -> None:
    import investhome_api.services.creative_director.phase5_master_revision as prod
    import investhome_api.services.creative_director.creative_revision_controller as ctrl

    assert "generate_image" not in inspect.getsource(prod)
    assert "edit_image" not in inspect.getsource(prod)
    assert "generate_image" not in inspect.getsource(ctrl)
    assert "visual_replace_executed" in inspect.getsource(prod)


def test_generate_does_not_overwrite_r1_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_master_revision as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P55-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    r1 = [{"workflow": "phase5_4a_r1_final_polish", "keep": True}]
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
            "creative_master_library_tests": [{"keep": True}],
            "premium_commercial_final_tests": [{"keep": True}],
            "premium_commercial_r1_tests": r1,
            "architecture_lock_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.5 test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    hero = Image.new("RGB", (2268, 1234), (176, 196, 214))
    ImageDraw.Draw(hero).rectangle((1400, 280, 2100, 1100), fill=(214, 204, 186))
    parent_img = Image.new("RGB", CANVAS_4X5, (40, 50, 60))
    child_img = parent_img.copy()
    ImageDraw.Draw(child_img).rectangle((600, 80, 1000, 240), fill=(200, 180, 90))
    packs = iter(
        [
            {
                "assembled_markup": scene_premium_commercial_r1(),
                "persistable_markup": "",
                "gate": {"pass": True, "flags": []},
                "semantic_ok": True,
                "image": parent_img,
            },
            {
                "assembled_markup": _child_markup(),
                "persistable_markup": "",
                "gate": {"pass": True, "flags": []},
                "semantic_ok": True,
                "image": child_img,
            },
        ]
    )

    def fake_read(_db, asset_id):
        if str(asset_id) == LOCKED_LOGO_ASSET_ID:
            return b'<svg xmlns="http://www.w3.org/2000/svg" width="80" height="32"></svg>'
        return _png(hero)

    monkeypatch.setattr(pm, "_read_bytes", fake_read)
    monkeypatch.setattr(pm, "_render_scene", lambda *a, **k: next(packs))
    monkeypatch.setattr(pm, "font_face_css", lambda *_a, **_k: "")
    monkeypatch.setattr(pm, "persist_gpt_image", lambda *a, **k: SimpleNamespace(id=uuid4()))

    result = generate_master_revision_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_55
    assert result["revision_intent_name"] == PRICE_REVISION
    assert result["visual_replace_executed"] is False
    assert result["gpt_image_calls"] == 0
    assert result["live_routing_active"] is False
    assert result["reversible"] is True
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    stored = dict(phase5.get("approved_creative_masters") or {}).get(MASTER_COMMERCIAL_R1_ID) or {}
    assert stored.get("approval_status") == HUMAN_APPROVED
    db.rollback()
    db.close()
