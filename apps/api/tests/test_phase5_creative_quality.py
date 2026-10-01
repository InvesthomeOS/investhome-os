"""Phase 5.4B — DESIGN_REFERENCES locator + fail-fast creative quality gate."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image

from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_quality_doctrine import build_quality_doctrine
from investhome_api.services.creative_director.creative_reference_library import (
    CANONICAL_FOLDER_NAME,
    DesignReferencesNotFound,
    build_reference_library,
    classify_reference_filename,
    is_canonical_reference_folder_name,
    locate_design_references,
    retrieve_references,
)
from investhome_api.services.creative_director.generative_creative_director_v2 import request_concept_set
from investhome_api.services.creative_director.phase5_creative_quality import (
    WORKFLOW_ID_54B,
    generate_creative_quality_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID


def test_canonical_folder_name_is_exact() -> None:
    assert is_canonical_reference_folder_name("DESIGN_REFERENCES")
    assert is_canonical_reference_folder_name("design_references")
    assert is_canonical_reference_folder_name("DESIGN_REFERENCE")
    assert not is_canonical_reference_folder_name("12_DESIGN_REFERENCES")
    assert not is_canonical_reference_folder_name("12_DESIGN_REFERENCE")


def test_filename_classifier_does_not_treat_os_experiments_as_references() -> None:
    temple = classify_reference_filename("IH_DC_TMP_001_campaign.jpg", width=1080, height=1350)
    assert temple["project_affinity"] == "THE_TEMPLE"
    assert temple["orientation"] == "portrait"
    uni = classify_reference_filename("UniLoft-poster.png")
    assert uni["project_affinity"] == "UNILOFT"


def test_doctrine_contains_core_rules() -> None:
    doctrine = build_quality_doctrine([])
    assert doctrine["schema"] == "CreativeQualityDoctrineV1"
    assert "A_image_design_integration" in doctrine["core_rules"]
    assert "H_no_dashboard_language" in doctrine["core_rules"]
    assert doctrine["status"] == "READY"


def test_retriever_diversifies_away_from_temple_only() -> None:
    library = {
        "references": [
            {"reference_id": "t1", "project_affinity": "THE_TEMPLE", "orientation": "portrait"},
            {"reference_id": "u1", "project_affinity": "UNILOFT", "orientation": "portrait"},
            {"reference_id": "b1", "brand_affinity": "INVESHOME", "orientation": "landscape"},
        ],
        "dna": [{"reference_id": "u1", "visual_analysis_status": "ANALYZED"}],
    }
    picked = retrieve_references(library, limit=3)
    ids = {item["reference_id"] for item in picked}
    assert "u1" in ids
    assert len(picked) == 3


def test_director_refuses_without_reference_dna() -> None:
    try:
        request_concept_set(
            foundation=Image.new("RGB", (64, 80), (20, 20, 20)),
            photo_analysis={},
            doctrine=build_quality_doctrine([]),
            retrieved=[],
            fonts={"roles": {}},
            facts={"headline": "ALIRKEN KAZAN", "unit": "2+1", "unit_label": "DAİRE", "list_price": "675.000 USD", "discount": "%35", "discount_label": "LANSMAN AVANTAJI", "cta": "PROJEYİ KEŞFET"},
        )
        raise AssertionError("expected DesignReferencesNotFound")
    except DesignReferencesNotFound:
        pass


def test_modules_do_not_use_gpt_image_as_designer() -> None:
    import investhome_api.services.creative_director.phase5_creative_quality as prod
    import investhome_api.services.creative_director.generative_creative_director_v2 as director

    assert "generate_image" not in inspect.getsource(prod)
    assert "edit_image" not in inspect.getsource(prod)
    assert "generate_image" not in inspect.getsource(director)
    assert "FAIL_FAST_MISSING_DESIGN_REFERENCES" in inspect.getsource(prod)


def test_live_locator_does_not_invent_folder() -> None:
    from investhome_api.db.session import SessionLocal

    db = SessionLocal()
    try:
        location = locate_design_references(db)
        assert location["canonical_folder_name"] == CANONICAL_FOLDER_NAME
        assert location["previous_search_root"]["id"] == "1opwsQlV8kehhbOscXpPAILWH1m_cc7Le"
        assert "full drive" in str(location.get("correct_search_root") or "").casefold()
        assert "drive_full_scope" in location
        if not location["found"]:
            assert location["fail_fast"] is True
            try:
                build_reference_library(db, location)
                raise AssertionError("empty location must not build a fake library")
            except DesignReferencesNotFound:
                pass
    finally:
        db.close()


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_creative_quality as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54B-{uuid4().hex[:6]}",
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
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4b test",
        context_json=ctx,
    )
    db.add(row)
    db.flush()
    monkeypatch.setattr(
        pm,
        "locate_design_references",
        lambda *_a, **_k: {
            "found": False,
            "fail_fast": True,
            "reason": "missing",
            "canonical_folder_name": CANONICAL_FOLDER_NAME,
            "media_library_search": {"folder_count_scanned": 0},
            "drive_walk": {"root_name": "Investhome OS", "root_folder_id": "x", "visited": 1},
            "drive_name_query": {"matches": []},
        },
    )
    result = generate_creative_quality_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54B
    assert result["status"] == "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("approved_creative_masters") == approved
    assert result["candidates"] == []
    db.rollback()
    db.close()
