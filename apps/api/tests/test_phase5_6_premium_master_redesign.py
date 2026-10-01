"""Phase 5.6 — premium redesign. No GPT Image. Existing Master unchanged."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.graphic_design_compositor_v3 import apply_premium_field, compose_premium_structured
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_ASSET_ID, PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import WORKFLOW_ID_56, generate_premium_master_redesign_56
from investhome_api.services.creative_director.phase5_workflow import PRODUCTION_COVER_V2
from investhome_api.services.creative_director.premium_art_direction import (
    blueprint_v2_pass,
    creative_canvas_balance,
    programmatic_feel,
    split_panel_language,
)
from investhome_api.services.creative_director.visual_draft_reconstruction import DAY007_ASSET_ID


def test_locks_existing_masters() -> None:
    assert PARENT_MASTER_ID == "0c8f5fa6-4894-402c-8056-7ff7712a8ff7"
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert PRICE_R1_REVISION_ID == "9c93f0cb-4f4d-429b-bfd0-cfdd3c9e3f76"
    assert PRICE_R1_ASSET_ID == "3790af4c-2561-4845-a4c7-8ba3d478139d"
    assert DAY007_ASSET_ID == "c0afa1bf-b487-410c-be3d-91c31852550d"
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"
    assert WORKFLOW_ID_56 == "phase5_6_premium_master_redesign"
    assert generate_premium_master_redesign_56


def test_no_gpt_image_or_master_overwrite() -> None:
    import investhome_api.services.creative_director.phase5_6_premium_master_redesign as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "must not call GPT Image" in src
    assert "existing_master_changed" in src
    assert "PARENT_MASTER_ID" in src
    assert "PRICE_R1_ASSET_ID" in src


def test_split_panel_language_fails_blueprint() -> None:
    bad = {
        "concept_name": "Navy Split",
        "visual_thesis": "photo on one side, information on the other in a navy column",
        "whole_canvas_strategy": "giant left information panel",
    }
    good = {
        "concept_name": "Sky Veil",
        "visual_thesis": "full-bleed architecture with a designed sky veil and ground fade",
        "whole_canvas_strategy": "type participates in the photograph across the canvas",
        "why_this_is_not_a_template": "asymmetric sky/ground roles, not a listing stack",
    }
    assert split_panel_language(bad) is True
    assert split_panel_language(good) is False
    feels = programmatic_feel(bad)
    assert feels["SPLIT_PANEL_FEEL"] > 2
    assert blueprint_v2_pass({k: 9 for k in (
        "professional_art_direction",
        "reference_craft_transfer",
        "originality",
        "whole_canvas_composition",
        "architecture_integration",
        "typographic_composition",
        "commercial_storytelling",
        "brand_integration",
        "negative_space_quality",
        "premium_character",
        "structured_feasibility",
    )}, feels) is False


def test_canvas_balance_flags_dead_navy_column() -> None:
    image = Image.new("RGB", (200, 300), (20, 30, 40))
    ImageDraw.Draw(image).rectangle((100, 0, 200, 300), fill=(90, 100, 80))
    objects = {"headline": {"bounds": {"x": 0.02, "y": 0.02, "w": 0.3, "h": 0.08}}}
    field = Image.new("L", (200, 300), 0)
    ImageDraw.Draw(field).rectangle((0, 0, 100, 300), fill=220)
    occupancy = {"layers": {"hard_protected": Image.new("L", (200, 300), 0), "sky": Image.new("L", (200, 300), 0)}}
    ImageDraw.Draw(occupancy["layers"]["hard_protected"]).rectangle((110, 40, 190, 260), fill=255)
    dead = creative_canvas_balance(image, objects, field, occupancy)
    assert dead["dead_space_score"] > 2
    live = Image.new("RGB", (200, 300), (80, 90, 70))
    ImageDraw.Draw(live).rectangle((0, 0, 200, 80), fill=(30, 35, 45))
    ImageDraw.Draw(live).rectangle((0, 240, 200, 300), fill=(30, 35, 45))
    objects2 = {
        "headline": {"bounds": {"x": 0.05, "y": 0.04, "w": 0.4, "h": 0.1}},
        "price": {"bounds": {"x": 0.4, "y": 0.82, "w": 0.35, "h": 0.08}},
        "cta": {"bounds": {"x": 0.05, "y": 0.9, "w": 0.3, "h": 0.04}},
    }
    field2 = Image.new("L", (200, 300), 0)
    ImageDraw.Draw(field2).rectangle((0, 0, 200, 70), fill=180)
    ImageDraw.Draw(field2).rectangle((0, 230, 200, 300), fill=180)
    occ2 = {"layers": {"hard_protected": Image.new("L", (200, 300), 0), "sky": Image.new("L", (200, 300), 0)}}
    ImageDraw.Draw(occ2["layers"]["hard_protected"]).rectangle((40, 70, 170, 230), fill=255)
    ImageDraw.Draw(occ2["layers"]["sky"]).rectangle((0, 0, 200, 70), fill=200)
    ok = creative_canvas_balance(live, objects2, field2, occ2)
    assert ok["dead_space_score"] <= 2


def test_premium_field_is_not_a_hard_split() -> None:
    photo = Image.new("RGB", (108, 136), (120, 130, 140))
    occ = {"layers": {"hard_protected": Image.new("L", (108, 136), 0)}}
    sky = apply_premium_field(photo, occ, "SKY_VEIL")
    corner = apply_premium_field(photo, occ, "CORNER_INGRESS")
    assert sky["geometry_modified"] is False
    assert "split" not in " ".join(sky["treatments"])
    sample = corner["mask"].getpixel((8, 8))
    far = corner["mask"].getpixel((100, 120))
    assert sample > far
    assert compose_premium_structured
