"""Phase 5.5C — master lock + PRICE_EDIT_ONLY. No GPT Image. No production cover change."""

from __future__ import annotations

import inspect

from PIL import Image, ImageDraw

from investhome_api.services.creative_director.approved_creative_master import HUMAN_APPROVED
from investhome_api.services.creative_director.approved_master_lock import (
    APPROVED_R2_ASSET_ID,
    APPROVED_R2_SPEC_ID,
    LOCKED_MASTER,
    PRICE_INSTRUCTION,
    append_child_revision,
    build_approved_master_lock,
    restore_approved_master,
    unlock_for_intent,
)
from investhome_api.services.creative_director.commercial_number_renderer import render_struck_price
from investhome_api.services.creative_director.creative_revision_controller import PRICE_REVISION, classify_revision_intent, parse_price_revision
from investhome_api.services.creative_director.phase5_5c_master_lock_price_proof import (
    WORKFLOW_ID_55C,
    compare_master_preservation,
    generate_master_lock_price_proof_55c,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_workflow import LOCKED_LOGO_ASSET_ID, PRODUCTION_COVER_V2


def test_locks_r2_master_and_real_logo() -> None:
    assert APPROVED_R2_ASSET_ID == "7c2a9436-e5c8-499f-9f8b-d720ebe4997b"
    assert APPROVED_R2_SPEC_ID == "544cfcd6-d7cd-410a-984a-d5cb8050252d"
    assert LOCKED_LOGO_ASSET_ID == "7b58877e-efca-4e9a-9027-6fd18fb1b345"
    assert WORKFLOW_ID_55C == "phase5_5c_master_lock_price_proof"
    assert generate_master_lock_price_proof_55c
    assert PRODUCTION_COVER_V2 == "19ed9f2c-3378-4eb4-9387-ed78b9f3768f"


def test_instruction_is_price_edit_only() -> None:
    assert classify_revision_intent(PRICE_INSTRUCTION) == PRICE_REVISION
    values = parse_price_revision(PRICE_INSTRUCTION)
    assert values["launch_price"] == "438.750 USD"
    assert values["list_price_struck"] == "675.000 USD"
    assert values["savings"] == "236.250 USD"
    assert values["savings_label"] == "KAZANCINIZ"
    assert "Başka hiçbir şeyi değiştirme" in PRICE_INSTRUCTION
    assert unlock_for_intent("PRICE_EDIT_ONLY") == ("price", "old_price", "savings", "savings_label", "currency")
    assert "headline" not in unlock_for_intent("PRICE_EDIT_ONLY")


def test_no_gpt_image_or_cover_change() -> None:
    import investhome_api.services.creative_director.phase5_5c_master_lock_price_proof as workflow

    src = inspect.getsource(workflow)
    assert "edit_image" not in src
    assert "generate_image" not in src
    assert "must not call GPT Image" in src
    assert "production_cover_changed" in src
    assert "PRICE_EDIT_ONLY" in src


def test_master_lock_schema_and_reversibility() -> None:
    spec = {
        "spec_id": APPROVED_R2_SPEC_ID,
        "navy_field": {"bounds": {"x": 0, "y": 0, "w": 0.3438, "h": 1}, "px": [0, 0, 374, 1360]},
        "project_photo": {"asset_id": "c0afa1bf-b487-410c-be3d-91c31852550d", "bounds": {"x": 0.3438, "y": 0, "w": 0.6562, "h": 1}},
        "headline": {"bounds": {"x": 0.02, "y": 0.07, "w": 0.3, "h": 0.09}},
        "discount": {"bounds": {"x": 0.02, "y": 0.24, "w": 0.09, "h": 0.04}},
        "discount_label": {"bounds": {"x": 0.02, "y": 0.29, "w": 0.26, "h": 0.02}},
        "price": {"bounds": {"x": 0.02, "y": 0.37, "w": 0.17, "h": 0.04}},
        "project_logo": {"bounds": {"x": 0.02, "y": 0.44, "w": 0.18, "h": 0.08}},
        "unit_type": {"bounds": {"x": 0.02, "y": 0.53, "w": 0.1, "h": 0.02}},
        "cta": {"bounds": {"x": 0.02, "y": 0.57, "w": 0.2, "h": 0.02}},
        "source_asset_provenance": {"photo_asset_id": "c0afa1bf-b487-410c-be3d-91c31852550d", "crop": {"locked": True}},
    }
    master = build_approved_master_lock(spec=spec, master_id="master-55c")
    assert master["status"] == HUMAN_APPROVED
    assert master["lock_status"] == LOCKED_MASTER
    assert master["approved_asset_id"] == APPROVED_R2_ASSET_ID
    assert master["lock_groups"]["PHOTO_LOCK"] is True
    child = append_child_revision(
        master,
        {
            "revision_id": "child-1",
            "parent_master_id": "master-55c",
            "parent_asset_id": APPROVED_R2_ASSET_ID,
            "parent_semantic_content": {"list_price": "675.000 USD"},
        },
    )
    restored = restore_approved_master(child, "child-1")
    assert restored["restored_asset_id"] == APPROVED_R2_ASSET_ID
    assert restored["semantic_content"]["list_price"] == "675.000 USD"


def test_preservation_fails_when_headline_moves() -> None:
    spec = {
        "navy_field": {"px": [0, 0, 374, 1360]},
        "headline": {"bounds": {"x": 0.02, "y": 0.07, "w": 0.3, "h": 0.09}},
        "discount": {"bounds": {"x": 0.02, "y": 0.24, "w": 0.09, "h": 0.04}},
        "discount_label": {"bounds": {"x": 0.02, "y": 0.29, "w": 0.26, "h": 0.02}},
        "price": {"bounds": {"x": 0.02, "y": 0.37, "w": 0.17, "h": 0.04}},
        "project_logo": {"bounds": {"x": 0.02, "y": 0.44, "w": 0.18, "h": 0.08}},
        "unit_type": {"bounds": {"x": 0.02, "y": 0.53, "w": 0.1, "h": 0.02}},
        "cta": {"bounds": {"x": 0.02, "y": 0.57, "w": 0.2, "h": 0.02}},
        "project_photo": {"bounds": {"x": 0.3438, "y": 0, "w": 0.6562, "h": 1}},
    }
    parent = Image.new("RGB", CANVAS_4X5, (40, 50, 60))
    ImageDraw.Draw(parent).rectangle((30, 100, 300, 200), fill=(240, 240, 230))
    ok = parent.copy()
    ImageDraw.Draw(ok).rectangle((20, 450, 360, 580), fill=(200, 180, 90))
    report = compare_master_preservation(parent, ok, spec)
    assert report["pass"] is True
    bad = parent.copy()
    ImageDraw.Draw(bad).rectangle((30, 100, 300, 200), fill=(10, 10, 10))
    failed = compare_master_preservation(parent, bad, spec)
    assert failed["pass"] is False
    assert "headline_geometry_delta" in failed["failed"]


def test_struck_price_records_line() -> None:
    from PIL import ImageFont

    im = Image.new("RGB", (400, 120), (40, 50, 60))
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default()
    parts: dict = {}
    box = render_struck_price(
        draw,
        origin=(10, 20),
        text="675.000 USD",
        number_font=font,
        currency_font=font,
        fill=(240, 240, 230),
        strike_fill=(201, 168, 92),
        parts=parts,
    )
    assert box[2] > box[0]
    assert "strikethrough" in parts
    assert "number" in parts
