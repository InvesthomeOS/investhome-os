"""Phase 5.4E — graphic-field master gates (Architecture B)."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.executable_reference_system import (
    E_ASSIGNMENTS,
    FORBIDDEN_PRIMARY,
    seeded_system,
    systems_for_candidate,
)
from investhome_api.services.creative_director.graphic_field_director import (
    apply_graphic_field_to_foundation,
    architecture_protection_mask_v2,
    openai_mask_png,
    protected_pixels_unchanged,
)
from investhome_api.services.creative_director.phase5_graphic_field_master import (
    WORKFLOW_ID_54E,
    generate_graphic_field_master_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import (
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)
from investhome_api.services.creative_director.reference_quality_filter import (
    GRADE_A,
    GRADE_B,
    GRADE_C,
    filter_references,
)
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    build_master_spec,
    compose_typography_v2,
    revision_readiness,
)


def test_grade_a_filter_excludes_b_and_c() -> None:
    entries = (
        [{"reference_id": rid, "filename": name} for rid, name in GRADE_A.items()]
        + [{"reference_id": rid, "filename": name} for rid, name in GRADE_B.items()]
        + [{"reference_id": rid, "filename": name} for rid, name in GRADE_C.items()]
        + [{"reference_id": "unknown", "filename": "ORNEK_99999.jpg"}]
    )
    filtered = filter_references(entries, minimum_grade="A")
    assert filtered["schema"] == "ReferenceQualityFilterV1"
    assert filtered["minimum_grade"] == "A"
    assert filtered["a_count"] == 6
    assert filtered["b_count"] == 5
    assert filtered["c_count"] == 4
    allowed_names = {item["filename"] for item in filtered["allowed"]}
    stored_names = {item["filename"] for item in filtered["stored_not_used"]}
    excluded_names = {item["filename"] for item in filtered["excluded"]}
    assert "ORNEK_00013.jpg" in allowed_names
    assert "ORNEK_00004.jpg" in stored_names
    assert "ORNEK_00003.jpg" in excluded_names
    assert "ORNEK_99999.jpg" in excluded_names
    assert "ORNEK_00004.jpg" not in allowed_names
    assert "ORNEK_00003.jpg" not in allowed_names


def test_executable_systems_are_not_adjective_dna() -> None:
    for name in ("ORNEK_00013.jpg", "ORNEK_00008.jpg", "ORNEK_00006.jpg"):
        system = seeded_system(name)
        assert system["schema"] == "ExecutableReferenceSystemV1"
        assert system["system_id"]
        assert isinstance(system["canvas_system"], dict)
        assert isinstance(system["alignment_system"], dict)
        joined = " ".join(str(v) for v in system["alignment_system"].values()).casefold()
        for phrase in FORBIDDEN_PRIMARY:
            assert joined != phrase
            assert system["alignment_system"].get("alignment") not in FORBIDDEN_PRIMARY
    e1 = systems_for_candidate("E1", {})
    e2 = systems_for_candidate("E2", {})
    e3 = systems_for_candidate("E3", {})
    ids = {e1["system_id"], e2["system_id"], e3["system_id"]}
    assert ids == {"DARK_FIELD_STACKED_DISPLAY", "TYPE_IN_ARCHITECTURAL_SHADOW", "BREATHING_ROOM_TOP_FIELD"}
    assert e1["primary_filename"] != e2["primary_filename"] != e3["primary_filename"]


def test_protected_pixels_unchanged_after_graphic_composite() -> None:
    foundation = Image.new("RGB", (200, 250), (170, 190, 220))
    draw = ImageDraw.Draw(foundation)
    draw.rectangle((50, 40, 150, 210), fill=(168, 158, 148))
    mask = architecture_protection_mask_v2(
        foundation,
        {"regions": {"SPIRE": {"x": 0.25, "y": 0.08, "w": 0.28, "h": 0.42}}},
    )
    assert mask["schema"] == "ArchitectureProtectionMaskV2"
    assert mask["composite_rule"] == "generated_pixels_only_where_protect_is_0"
    png = openai_mask_png(mask)
    assert png.startswith(b"\x89PNG")
    generated = Image.new("RGB", (200, 250), (12, 14, 20))
    applied = apply_graphic_field_to_foundation(foundation, generated, mask["mask_l"])
    assert protected_pixels_unchanged(foundation, applied, mask["mask_l"])
    assert applied.size == foundation.size


def test_compositor_emits_exact_turkish_and_distinct_systems() -> None:
    field = Image.new("RGB", (1088, 1360), (18, 20, 26))
    fonts = build_font_registry()
    protection = {"regions": {"SPIRE": {"x": 0.28, "y": 0.02, "w": 0.24, "h": 0.48}}}
    packs = []
    for key in ("E1", "E2", "E3"):
        pack = compose_typography_v2(
            field,
            systems=systems_for_candidate(key, {}),
            fonts=fonts,
            logo_rgba=None,
            protection=protection,
        )
        packs.append(pack)
        facts = pack["facts"]
        assert facts["headline"] == REQUIRED_FACTS["headline"]
        assert facts["unit_type"] == f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}"
        assert facts["price"] == "675.000 USD"
        assert facts["discount"] == "%35"
        assert facts["discount_label"] == "LANSMAN AVANTAJI"
        assert facts["cta"] == "PROJEYİ KEŞFET"
        assert "İ" in facts["unit_type"]
        assert "Ş" in facts["cta"]
        spec = build_master_spec(
            key=key,
            pack=pack,
            systems=systems_for_candidate(key, {}),
            crop={"canvas": [1088, 1360]},
            photo_asset="299bd265-a0ea-486d-866d-1947f103fd57",
            logo_asset="7b58877e-efca-4e9a-9027-6fd18fb1b345",
            graphic_field_asset_id=str(uuid4()),
            architecture_lock={"schema": "ArchitectureProtectionMaskV2", "protected_coverage": 0.4, "composite_rule": "generated_pixels_only_where_protect_is_0"},
        )
        assert spec["schema"] == "GraphicFieldMasterDesignSpecV1"
        assert spec["project_logo"]["ai_redrawn"] is False
        ready = revision_readiness(spec)
        assert ready["executed"] is False
        assert ready["checks"]["PRICE_EDIT_ONLY"] == "PASS"
        assert ready["checks"]["COPY_EDIT_ONLY"] == "PASS"
        assert ready["checks"]["VISUAL_REPLACE_ONLY"] == "PASS"
    assert packs[0]["system_id"] != packs[1]["system_id"] != packs[2]["system_id"]
    e1_price = packs[0]["objects"]["price"]["bounds"]
    e2_price = packs[1]["objects"]["price"]["bounds"]
    e3_price = packs[2]["objects"]["price"]["bounds"]
    assert (e1_price["y"], e1_price["h"]) != (e2_price["y"], e2_price["h"]) or e1_price["x"] != e2_price["x"]
    assert e3_price["h"] < e2_price["h"]


def test_54e_uses_edits_not_unrestricted_generations() -> None:
    import investhome_api.services.creative_director.graphic_field_director as director
    import investhome_api.services.creative_director.phase5_graphic_field_master as prod

    assert "edit_image" in inspect.getsource(director)
    assert "generate_graphic_field" in inspect.getsource(director)
    assert "images/generations" not in inspect.getsource(director)
    assert "generate_image(" not in inspect.getsource(director)
    assert "lock_architecture_pixels" not in inspect.getsource(director)
    assert WORKFLOW_ID_54E in inspect.getsource(prod)
    assert "master_revision_tests" in inspect.getsource(prod)
    assert "generative_master_tests" in inspect.getsource(prod)
    assert "retrieve_references" not in inspect.getsource(prod)
    assert generate_graphic_field_master_4x5.__name__ == "generate_graphic_field_master_4x5"


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_graphic_field_master as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54E-{uuid4().hex[:6]}",
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
    gen54c = [{"workflow": "phase5_4c_generative_master", "keep": True}]
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
            "generative_master_tests": gen54c,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4e test",
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
    result = generate_graphic_field_master_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54E
    assert result["status"] == "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["phase55_executed"] is False
    assert result["price_revision_executed"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("creative_quality_tests") == quality
    assert phase5.get("creative_quality_r1_tests") == quality_r1
    assert phase5.get("generative_master_tests") == gen54c
    assert phase5.get("approved_creative_masters") == approved
    assert result["candidates"] == []
    db.rollback()
    db.close()
