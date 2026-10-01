"""Phase 5.4H — photo-to-family eligibility gate."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.phase5_photo_family_eligibility import (
    WORKFLOW_ID_54H,
    generate_photo_family_eligibility_4x5,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID
from investhome_api.services.creative_director.photo_family_eligibility import (
    ALL_MASTER_FAMILIES,
    campaign_density_profile,
    classify_photo_composition,
    evaluate_all_families,
    evaluate_family_eligibility,
    family_compatibility_rules,
    is_approved_exterior_filename,
    occupancy_for_family,
    rank_eligible_families,
)
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map


def _library():
    catalog = {name: seeded_reference_family(name) for name in GRADE_A_ORDER}
    return build_family_library(catalog)


def _families():
    library = _library()
    return [family_by_id(library, family_id) for family_id in ALL_MASTER_FAMILIES]


def test_temple_campaign_density_is_high() -> None:
    fonts = build_font_registry()
    family = family_by_id(_library(), "EDITORIAL_DARK_FIELD")
    profile = campaign_density_profile(fonts=fonts, family=family, canvas=CANVAS_4X5, scale=1.0)
    assert profile["schema"] == "CampaignDensityProfileV1"
    assert profile["level"] == "HIGH"
    assert profile["semantic_groups"] == 6
    assert "ALIRKEN KAZAN" in profile["copy_units"]
    assert any("DAİRE" in str(u) or "DAIRE" in str(u).upper() for u in profile["copy_units"])
    assert profile["measured_lockup"]["width"] > 0.2
    assert profile["measured_lockup"]["height"] > 0.2


def test_full_frame_architecture_rejects_editorial_dark_field() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (158, 148, 138))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((20, 20, 1068, 1340), fill=(152, 142, 132))
    fonts = build_font_registry()
    family = family_by_id(_library(), "EDITORIAL_DARK_FIELD")
    occupancy = build_photo_occupancy_map(photo)
    result = evaluate_family_eligibility(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert result["schema"] == "FamilyEligibilityResultV1"
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["checks"]["required_negative_space"]["pass"] is False or result["checks"]["architecture_clearance"]["pass"] is False


def test_large_dark_right_field_allows_editorial_dark_field() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (186, 198, 214))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((180, 280, 620, 1280), fill=(150, 140, 128))
    draw.rectangle((700, 0, 1088, 1360), fill=(16, 20, 28))
    fonts = build_font_registry()
    family = family_by_id(_library(), "EDITORIAL_DARK_FIELD")
    occupancy = build_photo_occupancy_map(photo)
    result = evaluate_family_eligibility(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert result["status"] in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}


def test_sky_family_cannot_take_high_density_without_sky() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (40, 42, 46))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((80, 80, 1000, 1280), fill=(150, 140, 128))
    fonts = build_font_registry()
    family = family_by_id(_library(), "SKY_EDITORIAL")
    occupancy = build_photo_occupancy_map(photo)
    result = evaluate_family_eligibility(photo=photo, occupancy=occupancy, family=family, fonts=fonts)
    assert result["status"] == "NOT_ELIGIBLE"
    assert result["checks"]["content_density"]["family_max"] == "MEDIUM" or result["checks"]["required_negative_space"]["pass"] is False


def test_composition_class_on_synthetic_photo() -> None:
    photo = Image.new("RGB", CANVAS_4X5, (176, 190, 210))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((360, 80, 720, 1200), fill=(150, 140, 128))
    occupancy = build_photo_occupancy_map(photo)
    composition = classify_photo_composition(photo, occupancy)
    assert composition["schema"] == "ProjectPhotoCompositionClassV1"
    assert composition["primary_class"]
    assert "CENTERED_ARCHITECTURE" in composition["traits"] or abs(float(occupancy.get("architecture_centroid_x") or 0.5) - 0.5) < 0.2


def test_compatibility_rules_are_executable() -> None:
    rules = family_compatibility_rules()
    assert rules["schema"] == "FamilyPhotoCompatibilityRulesV1"
    for family_id in ALL_MASTER_FAMILIES:
        spec = rules["families"][family_id]
        assert spec["min_contiguous_width"] > 0
        assert spec["min_contiguous_height"] > 0
        assert spec["max_campaign_density"] in {"LOW", "MEDIUM", "HIGH"}
        assert spec["requires"]


def test_eligibility_comes_before_ranking() -> None:
    import investhome_api.services.creative_director.phase5_photo_family_eligibility as workflow

    source = inspect.getsource(workflow.generate_photo_family_eligibility_4x5)
    assert "FAMILY ELIGIBILITY" in source
    assert source.find("evaluate_all_families") < source.find("rank_eligible_families")
    assert source.find("rank_eligible_families") < source.find("compose_adaptive")


def test_no_existing_family_fits_is_valid_on_full_frame() -> None:
    photo = Image.new("RGB", (1600, 2000), (150, 142, 134))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((10, 10, 1590, 1990), fill=(148, 138, 128))
    fonts = build_font_registry()
    report = evaluate_all_families(source=photo, families=_families(), fonts=fonts)
    ranking = rank_eligible_families(_library(), report, photo=photo, protection={"regions": {}})
    assert report["no_existing_family_fits"] is True
    assert report["eligible_count"] == 0
    assert report["missing_family_requirement"]
    assert ranking["selected"] == []
    assert ranking["eligibility_before_preference"] is True


def test_low_density_family_rejected_for_high_campaign() -> None:
    rules = family_compatibility_rules()["families"]["SKY_EDITORIAL"]
    assert rules["max_campaign_density"] == "MEDIUM"
    rules_min = family_compatibility_rules()["families"]["MINIMAL_TOP_FIELD"]
    assert rules_min["max_campaign_density"] == "MEDIUM"


def test_exterior_filename_filter() -> None:
    assert is_approved_exterior_filename("IH_DC_TMP_001_Render_Exterior_Day_004.jpg", "image/jpeg") is True
    assert is_approved_exterior_filename("IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml") is False
    assert is_approved_exterior_filename("ORNEK_00013.jpg", "image/jpeg") is False
    assert is_approved_exterior_filename("Living_Room_Interior.jpg", "image/jpeg") is False
    assert is_approved_exterior_filename("IH_DC_TMP_001_Render_Bathroom_008.jpeg", "image/jpeg") is False


def test_no_image_model_in_eligibility() -> None:
    import investhome_api.services.creative_director.phase5_photo_family_eligibility as workflow
    import investhome_api.services.creative_director.photo_family_eligibility as engine

    assert "edit_image" not in inspect.getsource(engine)
    assert "generate_image" not in inspect.getsource(engine)
    assert "edit_image" not in inspect.getsource(workflow)
    assert "generate_image" not in inspect.getsource(workflow)
    assert "images/generations" not in inspect.getsource(workflow)
    assert occupancy_for_family


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_photo_family_eligibility as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54H-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    r1 = [{"workflow": "phase5_4a_r1_final_polish", "keep": True}]
    revision = [{"workflow": "phase5_5_master_revision", "keep": True}]
    gf54e = [{"workflow": "phase5_4e_graphic_field_master", "keep": True}]
    fam54f = [{"workflow": "phase5_4f_master_families", "keep": True}]
    fam54g = [{"workflow": "phase5_4g_final_composition", "keep": True}]
    approved = {MASTER_COMMERCIAL_R1_ID: {"approval_status": "HUMAN_APPROVED"}}
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
            "approved_creative_masters": approved,
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
            "master_revision_tests": revision,
            "architecture_lock_tests": [{"keep": True}],
            "creative_quality_tests": [{"keep": True}],
            "creative_quality_r1_tests": [{"keep": True}],
            "generative_master_tests": [{"keep": True}],
            "graphic_field_master_tests": gf54e,
            "master_family_tests": fam54f,
            "final_composition_tests": fam54g,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4h test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    monkeypatch.setattr(pm, "_read_bytes", lambda *_a, **_k: (_ for _ in ()).throw(FileNotFoundError("missing hero")))
    result = generate_photo_family_eligibility_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54H
    assert result["status"] == "FAIL_FAST_MISSING_HERO"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["phase55_executed"] is False
    assert result["image_replacement_executed"] is False
    assert result["new_family_created"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("graphic_field_master_tests") == gf54e
    assert phase5.get("master_family_tests") == fam54f
    assert phase5.get("final_composition_tests") == fam54g
    assert phase5.get("approved_creative_masters") == approved
    db.rollback()
    db.close()
