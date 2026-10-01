"""Phase 3.2 — Hybrid Master price revision. Preview only, master pixels locked."""

from __future__ import annotations

from investhome_api.services.creative_director.hybrid_revision import (
    build_hybrid_revision_plan,
    compose_hybrid_revision,
    pixel_lock_report,
    validate_hybrid_preview,
)
from investhome_api.services.creative_director.master_design_spec import persist_master_design_spec, snapshot_identity
from investhome_api.services.creative_director.master_revision_controller import classify_revision_command
from investhome_api.services.creative_director.price_block_revision import parse_price_block
from test_master_design_spec_v1 import COPY_CTX
from test_structured_reconstruction import _v1

COMMAND = (
    "Liste fiyatı 675.000 USD aynı kalsın ve üzeri çizilsin.\n"
    "Lansman fiyatı 438.750 USD olsun.\n"
    "Kazancınız 236.250 USD bilgisini ekle.\n"
    "Başka hiçbir şeyi değiştirme."
)


def test_command_is_price_edit_only() -> None:
    plan = classify_revision_command(COMMAND)
    assert plan["intent"] == "PRICE_EDIT_ONLY"
    intent = parse_price_block(COMMAND)
    assert intent is not None
    assert intent.list_amount == 675_000
    assert intent.launch_amount == 438_750
    assert intent.savings_amount == 236_250


def test_plan_keeps_headline_and_hero_outside_surface() -> None:
    cover, spec = _v1()
    intent = parse_price_block(COMMAND)
    plan = build_hybrid_revision_plan(spec, intent, master_size=cover.size)
    hero_y = int(plan["hero_boundary"])
    surface = plan["recomposition_surface"]
    assert surface["y1"] <= hero_y
    assert plan["headline_inside_surface"] is False
    assert "headline" in plan["preserved_semantics"]
    assert "hero_visual" in plan["preserved_semantics"]
    assert "cta" in plan["preserved_semantics"]
    assert "logo" in plan["preserved_semantics"]
    assert "commercial_group" in plan["affected_semantics"]
    assert plan["hero_visual_preservation"] == "MASTER_PIXELS_LOCKED"
    assert plan["layout_model"] != "three_column_row"


def test_compose_preserves_outside_pixels_and_price_facts() -> None:
    cover, spec = _v1()
    intent = parse_price_block(COMMAND)
    plan = build_hybrid_revision_plan(spec, intent, master_size=cover.size)
    preview, report = compose_hybrid_revision(cover, spec, plan)
    assert preview.size == cover.size
    assert report["provider_image_calls"] == 0
    assert report["full_reconstruction"] is False
    assert report["image_provider"] is False
    blob = " ".join(report["drawn_content"])
    for token in ("438.750", "675.000", "236.250", "%35", "2+1", "DAİRE", "LANSMAN FİYATI", "KAZANCINIZ"):
        assert token in blob
    struck = [b for b in report["drawn_boxes"] if b.get("struck")]
    assert struck
    lock = pixel_lock_report(cover, preview, plan)
    assert lock["outside_surface_changed_pixel_count"] == 0
    assert lock["outside_surface_max_channel_delta"] == 0
    assert lock["hero_pixel_lock"] == "PASS"
    assert lock["headline_pixel_lock"] == "PASS"
    validated = validate_hybrid_preview(preview, plan, report, master=cover)
    assert validated["status"] == "pass", validated
    ctx = dict(COPY_CTX)
    ctx["master_creative"] = dict(COPY_CTX["master_creative"])
    persist_master_design_spec(ctx, spec)
    before = snapshot_identity(ctx)
    current = ctx["current_master_design_spec_id"]
    compose_hybrid_revision(cover, spec, plan)
    after = snapshot_identity(ctx)
    assert after == before
    assert ctx["current_master_design_spec_id"] == current
    assert lock["pixels_changed_inside_surface"] > 0
    assert preview.tobytes() != cover.convert("RGB").tobytes()
