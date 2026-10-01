"""Phase 5.4C — generative design master gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.generative_master_director import (
    G_DIRECTIONS,
    architecture_protection_mask_v1,
    build_generative_master_design_spec,
    contains_mojibake,
    hard_reject_reasons,
    openai_mask_png,
    revision_readiness,
)
from investhome_api.services.creative_director.phase5_generative_master import (
    WORKFLOW_ID_54C,
    generate_generative_master_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2, TEMPLE_PROJECT_ID


def test_three_distinct_generative_directions() -> None:
    keys = [item["key"] for item in G_DIRECTIONS]
    concepts = [item["concept"] for item in G_DIRECTIONS]
    assert keys == ["G1", "G2", "G3"]
    assert len(set(concepts)) == 3
    assert "PREMIUM_EDITORIAL_CAMPAIGN" in concepts
    assert "HIGH_IMPACT_INVESTMENT_CAMPAIGN" in concepts
    assert "CONTEMPORARY_ARCHITECTURAL_LUXURY" in concepts


def test_protection_mask_uses_openai_transparent_edit_convention() -> None:
    im = Image.new("RGB", (200, 250), (170, 190, 220))
    draw = ImageDraw.Draw(im)
    draw.rectangle((50, 40, 150, 210), fill=(168, 158, 148))
    pack = architecture_protection_mask_v1(
        im,
        {"regions": {"SPIRE": {"x": 0.25, "y": 0.08, "w": 0.28, "h": 0.42}}},
    )
    assert pack["schema"] == "ArchitectureProtectionMaskV1"
    rgba = pack["mask_rgba"]
    assert rgba.mode == "RGBA"
    alphas = [p[3] for p in rgba.getdata()]
    assert min(alphas) < 40
    assert max(alphas) > 200
    assert 0.05 <= float(pack["protected_coverage"]) <= 0.95
    png = openai_mask_png(pack)
    assert png.startswith(b"\x89PNG")


def test_mojibake_and_fake_logo_hard_reject() -> None:
    assert contains_mojibake("2+1 DAÄ°RE")
    assert contains_mojibake("PROJEYÄ° KEÅžFET")
    reasons = hard_reject_reasons(
        inspect={
            "architecture_changed": False,
            "fake_logo": True,
            "mojibake": True,
            "observed_text": ["DAÄ°RE"],
            "property_card": True,
            "dashboard": False,
            "spire_collision": True,
            "text_on_photo": False,
            "missing_required": [],
            "typography_needs_replacement": False,
        },
        architecture_qa={"architecture_integrity_status": "pass"},
    )
    assert "fake_logo" in reasons
    assert "malformed_turkish_text" in reasons
    assert "obvious_property_card" in reasons
    assert "text_collision_with_spire" in reasons


def test_revision_readiness_requires_editable_boxes() -> None:
    empty = build_generative_master_design_spec(
        key="G1",
        brief={"zones": {}, "reference_ids": []},
        inspect={"zones": {}},
        crop={},
        architecture_mask={"protected_coverage": 0.3, "openai_convention": "transparent=edit opaque=preserve", "protected": []},
        decorative_locked=True,
        text_replaced=True,
        logo_composited=True,
    )
    fail = revision_readiness(empty)
    assert fail["revision_readiness"] == "FAIL"
    assert fail["executed"] is False

    ready_spec = build_generative_master_design_spec(
        key="G2",
        brief={"zones": {}, "reference_ids": ["r1"], "photographic_treatment": "keep"},
        inspect={
            "zones": {
                "headline": {"x": 0.06, "y": 0.06, "w": 0.5, "h": 0.12},
                "unit_type": {"x": 0.06, "y": 0.18, "w": 0.3, "h": 0.05},
                "price": {"x": 0.06, "y": 0.24, "w": 0.42, "h": 0.08},
                "discount": {"x": 0.06, "y": 0.33, "w": 0.18, "h": 0.06},
                "discount_label": {"x": 0.26, "y": 0.33, "w": 0.3, "h": 0.05},
                "cta": {"x": 0.06, "y": 0.88, "w": 0.36, "h": 0.05},
                "logo": {"x": 0.68, "y": 0.05, "w": 0.26, "h": 0.09},
            }
        },
        crop={"canvas": [1088, 1360], "centering": [0.7, 0.4]},
        architecture_mask={"protected_coverage": 0.4, "openai_convention": "transparent=edit opaque=preserve", "protected": ["spire"]},
        decorative_locked=True,
        text_replaced=True,
        logo_composited=True,
    )
    ready = revision_readiness(ready_spec)
    assert ready["schema"] == "GenerativeRevisionReadinessV1"
    assert ready["checks"]["PRICE_EDIT_ONLY"] == "PASS"
    assert ready["checks"]["COPY_EDIT_ONLY"] == "PASS"
    assert ready["checks"]["VISUAL_REPLACE_ONLY"] == "PASS"
    assert ready["revision_readiness"] == "PASS"
    assert ready_spec["schema"] == "GenerativeMasterDesignSpecV1"
    assert ready_spec["logo"]["ai_redrawn"] is False


def test_54c_uses_gpt_image_edits_not_unrestricted_generations() -> None:
    import investhome_api.services.creative_director.generative_master_director as director
    import investhome_api.services.creative_director.phase5_generative_master as prod

    assert "edit_image" in inspect.getsource(director)
    assert "run_generative_edit" in inspect.getsource(prod)
    assert "images/generations" not in inspect.getsource(director)
    assert "generate_image(" not in inspect.getsource(director)
    assert WORKFLOW_ID_54C in inspect.getsource(prod)
    assert "master_revision_tests" in inspect.getsource(prod)
    assert generate_generative_master_4x5.__name__ == "generate_generative_master_4x5"


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_generative_master as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54C-{uuid4().hex[:6]}",
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
    quality = [{"workflow": "phase5_4b_creative_quality", "keep": True}]
    quality_r1 = [{"workflow": "phase5_4b_r1_reference_grounded", "keep": True}]
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
            "creative_quality_tests": quality,
            "creative_quality_r1_tests": quality_r1,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4c test",
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
    result = generate_generative_master_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54C
    assert result["status"] == "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["phase55_executed"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("creative_quality_tests") == quality
    assert phase5.get("creative_quality_r1_tests") == quality_r1
    assert phase5.get("approved_creative_masters") == approved
    assert result["candidates"] == []
    db.rollback()
    db.close()
