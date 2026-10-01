"""Phase 5.4J — Graphic Design Compositor V3 + Eligibility V2 gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.contiguous_content_fit import (
    contiguous_content_fit,
    evaluate_family_eligibility_v2,
    largest_safe_rect,
)
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_production_compositor import (
    WORKFLOW_ID_54J,
    generate_production_compositor_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.reference_execution_calibration import (
    CALIBRATION_FACTS,
    run_reference_calibration,
)


def _library():
    return build_family_library({name: seeded_reference_family(name) for name in GRADE_A_ORDER})


def _family(name: str = "EDITORIAL_DARK_FIELD"):
    return family_by_id(_library(), name)


def test_v2_rejects_fat_bbox_when_clear_strip_is_too_narrow() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (18, 22, 28))
    hard = Image.new("L", CANVAS_4X5, 255)
    draw = ImageDraw.Draw(hard)
    x0 = int(0.78 * 1088)
    x1 = int(0.95 * 1088)
    draw.rectangle((x0, int(0.08 * 1360), x1, int(0.92 * 1360)), fill=0)
    occupancy = {"layers": {"hard_protected": hard}, "size": [1088, 1360]}
    safe = largest_safe_rect(occupancy)
    assert safe["w"] < 0.22
    fonts = build_font_registry()
    family = _family()
    result = evaluate_family_eligibility_v2(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert result["schema"] == "FamilyEligibilityResultV2"
    assert result["contiguous_fit"] == "NO_FIT"
    assert result["status"] == "NOT_ELIGIBLE"


def test_v2_fits_wide_architecture_clear_field() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (18, 22, 28))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((0, 420, 360, 1360), fill=(164, 152, 136))
    hard = Image.new("L", CANVAS_4X5, 0)
    hd = ImageDraw.Draw(hard)
    hd.rectangle((0, 420, 360, 1360), fill=255)
    occupancy = {"layers": {"hard_protected": hard}, "size": [1088, 1360]}
    fonts = build_font_registry()
    family = _family()
    fit = contiguous_content_fit(occupancy=occupancy, family=family, fonts=fonts)
    result = evaluate_family_eligibility_v2(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert fit["status"] == "FIT"
    assert result["contiguous_fit"] == "FIT"


def test_v2_does_not_treat_side_sliver_as_minimal_top_field() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (18, 22, 28))
    hard = Image.new("L", CANVAS_4X5, 255)
    draw = ImageDraw.Draw(hard)
    draw.rectangle((0, 0, int(0.20 * 1088), 1360), fill=0)
    occupancy = {"layers": {"hard_protected": hard}, "size": [1088, 1360]}
    result = evaluate_family_eligibility_v2(
        photo=photo,
        occupancy=occupancy,
        family=_family("MINIMAL_TOP_FIELD"),
        fonts=build_font_registry(),
    )
    assert result["contiguous_fit"] != "FIT"
    assert result["status"] == "NOT_ELIGIBLE"


def test_compositor_does_not_draw_lockup_on_no_fit() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (18, 22, 28))
    hard = Image.new("L", CANVAS_4X5, 255)
    occupancy = {"layers": {"hard_protected": hard}, "size": [1088, 1360]}
    pack = compose_graphic_design_v3(
        photo,
        occupancy=occupancy,
        family=_family(),
        fonts=build_font_registry(),
        logo_rgba=None,
    )
    assert pack["schema"] == "GraphicDesignCompositorV3"
    assert pack["solved"] is False
    assert pack["fit"]["status"] == "NO_FIT"
    assert pack["objects"] == {}


def test_no_image_model_and_no_ui_primitives() -> None:
    import investhome_api.services.creative_director.graphic_design_compositor_v3 as compositor
    import investhome_api.services.creative_director.phase5_production_compositor as workflow

    for source in (inspect.getsource(compositor), inspect.getsource(workflow)):
        assert "edit_image" not in source
        assert "generate_image" not in source
        assert "images/generations" not in source
    text = inspect.getsource(compositor).lower()
    for forbidden in ("rounded rectangle card", "kpi box", "dashboard panel", "web button"):
        assert forbidden not in text


def test_reference_calibration_placeholder_is_not_temple_copy() -> None:
    assert "ALIRKEN" not in CALIBRATION_FACTS["headline"]
    assert "675.000" not in CALIBRATION_FACTS["price"]
    assert CALIBRATION_FACTS["cta"] != "PROJEYİ KEŞFET"


def test_reference_calibration_scores_target() -> None:
    report = run_reference_calibration(family=_family(), fonts=build_font_registry(), logo_rgba=None)
    assert report["schema"] == "ReferenceExecutionCalibrationV1"
    assert report["copied_source_content"] is False
    assert report["solved"] is True
    for key, value in dict(report.get("scores") or {}).items():
        assert value >= 8.0, f"{key}={value}"
    assert report["pass"] is True


def test_calibration_fail_does_not_compose_temple(monkeypatch) -> None:
    import investhome_api.services.creative_director.phase5_production_compositor as pm
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User

    composed = {"called": False}

    def _boom(*_a, **_k):
        composed["called"] = True
        raise AssertionError("Temple compose must not run")

    dummy = Image.new("RGB", (1088, 1360), (18, 22, 28))
    monkeypatch.setattr(
        pm,
        "run_reference_calibration",
        lambda **_k: {
            "schema": "ReferenceExecutionCalibrationV1",
            "pass": False,
            "solved": False,
            "scores": {"overall_craft": 4.0},
            "pack": {"image": dummy, "solved": False, "objects": {}},
            "photo": dummy,
        },
    )
    monkeypatch.setattr(pm, "compose_graphic_design_v3", _boom)
    monkeypatch.setattr(pm, "list_temple_exterior_assets", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("Temple scan must not run")))

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54J-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    h54 = [{"workflow": "phase5_4h_photo_family_eligibility", "keep": True}]
    i54 = [{"workflow": "phase5_4i_best_pair_proof", "keep": True}]
    approved = {MASTER_COMMERCIAL_R1_ID: {"approval_status": "HUMAN_APPROVED"}}
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "current_master_design_spec_id": "f07d9813-e1e7-4f71-9996-9ed2203fdfe6",
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_creative_masters": approved,
            "photo_family_eligibility_tests": h54,
            "best_pair_proof_tests": i54,
            "premium_commercial_r1_tests": [{"keep": True}],
            "master_revision_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4j calibration fail",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    result = generate_production_compositor_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["status"] == "CALIBRATION_FAIL"
    assert result["temple_rendered"] is False
    assert composed["called"] is False
    assert result["gpt_image_calls"] == 0
    assert result["existing_master_changed"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("photo_family_eligibility_tests") == h54
    assert phase5.get("best_pair_proof_tests") == i54
    assert phase5.get("approved_creative_masters") == approved
    assert WORKFLOW_ID_54J
    db.rollback()
    db.close()
