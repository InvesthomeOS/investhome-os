"""Phase 5.4I — Day_002 × EDITORIAL_DARK_FIELD production proof gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from investhome_api.services.creative_director.adaptive_composition_engine import MAX_SOLVE_ITERS
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.phase5_best_pair_proof import (
    DAY002_ASSET_ID,
    DAY002_FILENAME,
    IDENTITY_SCALES,
    PROOF_FAMILY_ID,
    WORKFLOW_ID_54I,
    generate_best_pair_proof_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID


def test_identity_scale_never_below_family_floor() -> None:
    assert min(IDENTITY_SCALES) >= 0.78
    assert MAX_SOLVE_ITERS == 10
    assert PROOF_FAMILY_ID == "EDITORIAL_DARK_FIELD"
    assert DAY002_FILENAME.endswith("Day_002.jpg")


def test_eligibility_runs_before_compose() -> None:
    import investhome_api.services.creative_director.phase5_best_pair_proof as workflow

    source = inspect.getsource(workflow.generate_best_pair_proof_4x5)
    assert source.find("evaluate_family_eligibility") < source.find("compose_adaptive")
    assert "ELIGIBILITY_FAIL_NO_RENDER" in source
    assert "Day_004" not in source or "day004_used" in source


def test_no_image_model() -> None:
    import investhome_api.services.creative_director.phase5_best_pair_proof as workflow
    import investhome_api.services.creative_director.adaptive_composition_engine as engine

    assert "edit_image" not in inspect.getsource(workflow)
    assert "generate_image" not in inspect.getsource(workflow)
    assert "images/generations" not in inspect.getsource(workflow)
    assert "edit_image" not in inspect.getsource(engine)
    assert "generate_image" not in inspect.getsource(engine)


def test_eligibility_fail_does_not_compose(monkeypatch) -> None:
    import investhome_api.services.creative_director.phase5_best_pair_proof as pm
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from PIL import Image

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54I-{uuid4().hex[:6]}",
                project_name="The Temple",
                project_type=ProjectType.RESIDENTIAL,
                project_status=ProjectStatus.CONSTRUCTION,
            )
        )
        db.flush()
    user = db.query(User).first()
    assert user is not None
    ctx = {
        "current_cover_asset_id": PRODUCTION_COVER_V2,
        "phase5": {
            "current_session_id": "5a51b242-374d-4b5f-b69c-ccd29ae410d6",
            "current_format_family_id": "2f29711d-285c-4e6d-a1b8-5b058eeb58b4",
            "approved_creative_masters": {MASTER_COMMERCIAL_R1_ID: {"approval_status": "HUMAN_APPROVED"}},
            "premium_commercial_r1_tests": [{"keep": True}],
            "master_revision_tests": [{"keep": True}],
            "photo_family_eligibility_tests": [{"workflow": "phase5_4h_photo_family_eligibility", "keep": True}],
            "final_composition_tests": [{"keep": True}],
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4i eligibility fail",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    monkeypatch.setattr(pm, "_read_bytes", lambda *_a, **_k: Image.new("RGB", (200, 200), (20, 20, 20)).tobytes())
    monkeypatch.setattr(
        pm,
        "occupancy_aware_crop",
        lambda source, family: (
            Image.new("RGB", (1088, 1360), (30, 32, 36)),
            {"centering": [0.5, 0.3]},
            {"coverage": {"hard_protected": 0.9}, "pockets": {}, "sky_area": 0.0, "layers": {}, "size": [1088, 1360]},
        ),
    )
    monkeypatch.setattr(
        pm,
        "evaluate_family_eligibility",
        lambda **_k: {"status": "NOT_ELIGIBLE", "primary_reason": "forced", "checks": {}},
    )
    composed = {"called": False}

    def _boom(**_k):
        composed["called"] = True
        raise AssertionError("compose must not run")

    monkeypatch.setattr(pm, "compose_adaptive", _boom)
    from io import BytesIO

    def _png_bytes(*_a, **_k):
        buf = BytesIO()
        Image.new("RGB", (64, 64), (10, 10, 10)).save(buf, format="JPEG")
        return buf.getvalue()

    monkeypatch.setattr(pm, "_read_bytes", _png_bytes)
    result = generate_best_pair_proof_4x5(db, user, row, language="tr")
    assert result["status"] == "ELIGIBILITY_FAIL_NO_RENDER"
    assert composed["called"] is False
    assert result["candidate_asset_id"] is None
    assert result["gpt_image_calls"] == 0
    db.rollback()
    db.close()


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_best_pair_proof as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54I-{uuid4().hex[:6]}",
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
    h54 = [{"workflow": "phase5_4h_photo_family_eligibility", "keep": True}]
    g54 = [{"workflow": "phase5_4g_final_composition", "keep": True}]
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
            "graphic_field_master_tests": [{"keep": True}],
            "master_family_tests": [{"keep": True}],
            "final_composition_tests": g54,
            "photo_family_eligibility_tests": h54,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4i test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    monkeypatch.setattr(pm, "_read_bytes", lambda *_a, **_k: (_ for _ in ()).throw(FileNotFoundError("missing day002")))
    result = generate_best_pair_proof_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54I
    assert result["status"] == "FAIL_FAST_MISSING_DAY002"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["day004_used"] is False
    assert result["new_family_created"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("photo_family_eligibility_tests") == h54
    assert phase5.get("final_composition_tests") == g54
    assert phase5.get("approved_creative_masters") == approved
    assert DAY002_ASSET_ID
    db.rollback()
    db.close()
