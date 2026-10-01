"""Phase 5.4F — reference-derived master family gates."""

from __future__ import annotations

import inspect
from uuid import UUID, uuid4

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.creative_family_adapter import (
    adapt_family_to_project,
    choose_type_region,
)
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    FAMILY_CLUSTERS,
    build_family_library,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_family_router import rank_families
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
from investhome_api.services.creative_director.phase5_master_families import (
    WORKFLOW_ID_54F,
    generate_master_families_4x5,
)
from investhome_api.services.creative_director.phase5_workflow import (
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
)
from investhome_api.services.creative_director.reference_quality_filter import GRADE_A, GRADE_B, GRADE_C, filter_references


def test_grade_a_only_and_four_families() -> None:
    entries = (
        [{"reference_id": rid, "filename": name} for rid, name in GRADE_A.items()]
        + [{"reference_id": rid, "filename": name} for rid, name in GRADE_B.items()]
        + [{"reference_id": rid, "filename": name} for rid, name in GRADE_C.items()]
    )
    filtered = filter_references(entries, minimum_grade="A")
    assert filtered["a_count"] == 6
    assert all(item["filename"] not in GRADE_B.values() for item in filtered["allowed"])
    catalog = {name: seeded_reference_family(name) for name in GRADE_A.values()}
    library = build_family_library(catalog)
    ids = [f["family_id"] for f in library["families"]]
    assert library["family_count"] == 4
    assert library["user_facing_template_picker"] is False
    assert "EDITORIAL_DARK_FIELD" in ids
    assert "SKY_EDITORIAL" in ids
    assert "MINIMAL_TOP_FIELD" in ids
    assert "TYPE_IN_PLANE" in ids
    assert len(FAMILY_CLUSTERS) == 4
    members = [m for c in FAMILY_CLUSTERS for m in c["members"]]
    assert set(members) == set(GRADE_A.values())


def test_families_are_not_adjective_dna() -> None:
    family = seeded_reference_family("ORNEK_00013.jpg")
    assert family["schema"] == "ReferenceMasterFamilyV1"
    assert family["headline"]["alignment"] in {"left", "right", "center"}
    assert isinstance(family["headline"]["scale_ratio"], float)
    blob = json_dump_family()
    assert "balanced composition" not in blob
    assert "bold typography" not in blob
    assert "premium negative space" not in blob


def json_dump_family() -> str:
    import json

    catalog = {name: seeded_reference_family(name) for name in GRADE_A.values()}
    return json.dumps(build_family_library(catalog), default=str).casefold()


def test_adapter_mirrors_off_the_spire_and_emits_turkish() -> None:
    photo = Image.new("RGB", (1088, 1360), (180, 190, 200))
    draw = ImageDraw.Draw(photo)
    draw.rectangle((280, 20, 540, 680), fill=(168, 158, 148))
    protection = {"regions": {"SPIRE": {"x": 0.28, "y": 0.02, "w": 0.24, "h": 0.48}}}
    catalog = {name: seeded_reference_family(name) for name in GRADE_A.values()}
    library = build_family_library(catalog)
    sky = next(f for f in library["families"] if f["family_id"] == "SKY_EDITORIAL")
    placement = choose_type_region(sky, protection, photo.size)
    spire_right = 0.28 + 0.24
    # Either sits left of the spire or uses a permitted right/top-right alternate.
    assert placement["slot"] in {"top_left", "top_right", "top_band", "right_column", "mid_right"}
    assert float(placement["region"]["w"]) >= 0.18
    if placement["slot"] != "top_left":
        assert float(placement["region"]["x"]) >= spire_right - 0.08
    fonts = build_font_registry()
    dark = next(f for f in library["families"] if f["family_id"] == "EDITORIAL_DARK_FIELD")
    pack = adapt_family_to_project(
        source=photo,
        family=dark,
        protection=protection,
        protect_l=None,
        fonts=fonts,
        logo_rgba=None,
        facts=dict(REQUIRED_FACTS),
    )
    assert pack["facts"]["headline"] == "ALIRKEN KAZAN"
    assert pack["facts"]["price"] == "675.000 USD"
    assert "İ" in pack["facts"]["unit_type"]
    assert "Ş" in pack["facts"]["cta"]
    assert pack["adapter"]["architecture_forced_into_reference"] is False
    assert pack["objects"]["price"]["bounds"]["w"] >= 0.10


def test_router_ranks_three_and_is_not_a_picker() -> None:
    photo = Image.new("RGB", (1088, 1360), (170, 185, 205))
    ImageDraw.Draw(photo).rectangle((280, 20, 540, 680), fill=(160, 150, 140))
    protection = {"regions": {"SPIRE": {"x": 0.28, "y": 0.02, "w": 0.24, "h": 0.48}}}
    catalog = {name: seeded_reference_family(name) for name in GRADE_A.values()}
    library = build_family_library(catalog)
    ranking = rank_families(library, photo=photo, protection=protection, commercial_density=6)
    assert ranking["schema"] == "CreativeMasterFamilyRouterV1"
    assert ranking["user_facing_picker"] is False
    assert len(ranking["selected"]) == 3
    assert ranking["selected"][0] in {f["family_id"] for f in library["families"]}


def test_54f_has_zero_image_generation() -> None:
    import investhome_api.services.creative_director.creative_family_adapter as adapter
    import investhome_api.services.creative_director.phase5_master_families as prod

    assert "edit_image" not in inspect.getsource(adapter)
    assert "generate_image" not in inspect.getsource(adapter)
    assert "images/generations" not in inspect.getsource(prod)
    assert "edit_image" not in inspect.getsource(prod)
    assert WORKFLOW_ID_54F in inspect.getsource(prod)
    assert "graphic_field_master_tests" in inspect.getsource(prod)
    assert generate_master_families_4x5.__name__ == "generate_master_families_4x5"


def test_generate_fail_fast_does_not_touch_master_or_cover(monkeypatch) -> None:
    from investhome_api.db.session import SessionLocal
    from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
    from investhome_api.models.project import Project, ProjectStatus, ProjectType
    from investhome_api.models.user_auth import User
    from investhome_api.services.creative_director import phase5_master_families as pm

    db = SessionLocal()
    if db.get(Project, UUID(TEMPLE_PROJECT_ID)) is None:
        db.add(
            Project(
                id=UUID(TEMPLE_PROJECT_ID),
                project_code=f"P54F-{uuid4().hex[:6]}",
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
    gf54e = [{"workflow": "phase5_4e_graphic_field_master", "keep": True}]
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
            "graphic_field_master_tests": gf54e,
            "sessions": {"5a51b242-374d-4b5f-b69c-ccd29ae410d6": {}},
        },
    }
    row = CreativeDirectorCampaign(
        linked_project_id=UUID(TEMPLE_PROJECT_ID),
        created_by_user_id=user.id,
        mode="project",
        original_brief="phase5.4f test",
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
    result = generate_master_families_4x5(db, user, row, language="tr")
    db.refresh(row)
    after = dict(row.context_json or {})
    phase5 = dict(after.get("phase5") or {})
    assert result["workflow"] == WORKFLOW_ID_54F
    assert result["status"] == "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    assert result["promoted_to_master"] is False
    assert result["gpt_image_calls"] == 0
    assert result["phase55_executed"] is False
    assert str(after.get("current_cover_asset_id")) == PRODUCTION_COVER_V2
    assert phase5.get("premium_commercial_r1_tests") == r1
    assert phase5.get("master_revision_tests") == revision
    assert phase5.get("graphic_field_master_tests") == gf54e
    assert phase5.get("approved_creative_masters") == approved
    assert result["candidates"] == []
    db.rollback()
    db.close()
