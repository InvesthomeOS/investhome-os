"""Phase 5.4K — FULL_FRAME_ARCHITECTURAL_CAMPAIGN gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.contiguous_content_fit import evaluate_family_eligibility_v2
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import build_family_library, family_by_id, seeded_reference_family, GRADE_A_ORDER
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.full_frame_architectural_family import (
    CALIBRATION_FACTS,
    FAMILY_ID,
    family_brief,
    full_frame_family_spec,
    run_full_frame_calibration,
    synthetic_full_frame_architecture,
)
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_graphic_design_v3
from investhome_api.services.creative_director.phase5_full_frame_family import WORKFLOW_ID_54K, generate_full_frame_family_4x5
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.photo_family_eligibility import ALL_MASTER_FAMILIES, family_compatibility_rules
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map


def test_existing_four_families_unchanged() -> None:
    assert FAMILY_ID not in ALL_MASTER_FAMILIES
    assert len(ALL_MASTER_FAMILIES) == 4
    library = build_family_library({name: seeded_reference_family(name) for name in GRADE_A_ORDER})
    assert library["family_count"] == 4
    spec = family_by_id(library, FAMILY_ID)
    assert spec["family_id"] == FAMILY_ID
    assert spec["schema"] == "CreativeMasterFamilySpecV1"


def test_family_brief_and_forbidden_ui() -> None:
    brief = family_brief()
    assert brief["schema"] == "FullFrameArchitecturalFamilyBriefV1"
    assert brief["photo_occupancy"] == "HIGH"
    assert brief["architecture_modification"] == "NONE"
    assert "property_card" in brief["forbidden"]
    spec = full_frame_family_spec()
    forbidden = spec["graphic_devices"]["forbidden"]
    for item in ("cards", "header_bar", "footer_bar", "web_buttons"):
        assert item in forbidden
    assert spec["occupancy_compatibility"]["requires_large_dark_field"] is False
    assert spec["density_compatibility"]["HIGH"] is True


def test_compatibility_rules_include_full_frame() -> None:
    rules = family_compatibility_rules()["families"][FAMILY_ID]
    assert rules["max_campaign_density"] == "HIGH"
    assert rules["multi_zone"] is True
    assert "FULL_FRAME_ARCHITECTURE" in rules["compatible_traits"]


def test_multi_zone_can_fit_synthetic_full_frame() -> None:
    photo = synthetic_full_frame_architecture()
    occupancy = build_photo_occupancy_map(photo)
    fonts = build_font_registry()
    family = full_frame_family_spec()
    result = evaluate_family_eligibility_v2(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert result["schema"] == "FamilyEligibilityResultV2"
    assert result["contiguous_fit"] == "FIT"
    assert result["status"] == "ELIGIBLE"
    assert (result.get("fit") or {}).get("multi_zone") is True


def test_compositor_does_not_render_when_no_perimeter_fit() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (168, 156, 140))
    hard = Image.new("L", CANVAS_4X5, 255)
    occupancy = {"layers": {"hard_protected": hard}, "size": [1088, 1360]}
    pack = compose_graphic_design_v3(
        photo,
        occupancy=occupancy,
        family=full_frame_family_spec(),
        fonts=build_font_registry(),
        logo_rgba=None,
        facts=CALIBRATION_FACTS,
    )
    assert pack["solved"] is False
    assert (pack.get("fit") or {}).get("status") == "NO_FIT"
    assert pack.get("objects") == {}


def test_compositor_v3_executes_full_frame_family() -> None:
    photo = synthetic_full_frame_architecture()
    occupancy = build_photo_occupancy_map(photo)
    pack = compose_graphic_design_v3(
        photo,
        occupancy=occupancy,
        family=full_frame_family_spec(),
        fonts=build_font_registry(),
        logo_rgba=None,
        facts=CALIBRATION_FACTS,
    )
    assert pack["schema"] == "GraphicDesignCompositorV3"
    assert pack["family_id"] == FAMILY_ID
    assert pack["solved"] is True
    assert pack["objects"]
    assert "headline" in pack["objects"]
    assert "price" in pack["objects"]


def test_calibration_placeholder_is_not_temple() -> None:
    assert "ALIRKEN" not in CALIBRATION_FACTS["headline"]
    assert "675.000" not in CALIBRATION_FACTS["price"]
    report = run_full_frame_calibration(fonts=build_font_registry(), logo_rgba=None)
    assert report["copied_temple_content"] is False
    assert report["pass"] is True
    for key, value in dict(report.get("scores") or {}).items():
        assert value >= 8.0, f"{key}={value}"


def test_no_image_model_and_no_compositor_redesign() -> None:
    import investhome_api.services.creative_director.full_frame_architectural_family as family
    import investhome_api.services.creative_director.phase5_full_frame_family as workflow
    import investhome_api.services.creative_director.graphic_design_compositor_v3 as compositor

    for source in (inspect.getsource(family), inspect.getsource(workflow)):
        assert "edit_image" not in source
        assert "generate_image" not in source
        assert "images/generations" not in source
    assert "compose_full_frame_campaign" in inspect.getsource(compositor)
    assert "GraphicDesignCompositorV3" in inspect.getsource(compositor)


def test_calibration_fail_does_not_scan_temple(monkeypatch) -> None:
    import investhome_api.services.creative_director.phase5_full_frame_family as pm
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User

    dummy = Image.new("RGB", CANVAS_4X5, (20, 20, 20))
    monkeypatch.setattr(
        pm,
        "run_full_frame_calibration",
        lambda **_k: {
            "schema": "FullFrameFamilyCalibrationV1",
            "pass": False,
            "solved": False,
            "scores": {"overall_craft": 4.0},
            "pack": {"image": dummy, "solved": False, "objects": {}},
            "photo": dummy,
        },
    )
    scanned = {"called": False}

    def _boom(*_a, **_k):
        scanned["called"] = True
        raise AssertionError("Temple scan must not run")

    monkeypatch.setattr(pm, "list_temple_exterior_assets", _boom)
    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54K-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    j54 = [{"workflow": "phase5_4j_production_compositor", "keep": True}]
    i54 = [{"workflow": "phase5_4i_best_pair_proof", "keep": True}]
    approved = {MASTER_COMMERCIAL_R1_ID: {"approval_status": "HUMAN_APPROVED"}}
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_creative_masters": approved,
            "production_compositor_tests": j54,
            "best_pair_proof_tests": i54,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4k calibration fail",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    result = generate_full_frame_family_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["status"] == "CALIBRATION_FAIL"
    assert result["temple_rendered"] is False
    assert scanned["called"] is False
    assert result["gpt_image_calls"] == 0
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("production_compositor_tests") == j54
    assert phase5.get("best_pair_proof_tests") == i54
    assert WORKFLOW_ID_54K
    db.rollback()
    db.close()
