"""Phase 5.7 — compositor quality breakthrough.

Replay Phase 5.6 blueprints through old vs new compositor.
Do not generate a new Temple Master. GPT Image = 0.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.blueprint_render_fidelity import (
    apply_critic_calibration,
    blueprint_render_fidelity,
    craft_gap_report,
    detect_layout_faults,
    reference_craft_gap,
    score_calibration_render,
)
from investhome_api.services.creative_director.creative_canvas_balance_v2 import creative_canvas_balance_v2
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_relationship_system import (
    compositional_gravity,
    graph_from_reference_map,
    groups_from_objects,
    reading_flow,
    temple_relationship_graph,
)
from investhome_api.services.creative_director.full_frame_architectural_family import full_frame_family_spec
from investhome_api.services.creative_director.graphic_design_compositor_v3 import compose_premium_structured
from investhome_api.services.creative_director.compositor_relational_v4 import _facts, compose_relational_v4, reconstruct_reference_grammar
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import (
    DAY007_ASSET_ID,
    DAY007_FILENAME,
    load_grade_a_reference_images,
)
from investhome_api.services.creative_director.phase5_5c_master_lock_price_proof import render_side_by_side
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_ASSET_ID, PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import (
    WORKFLOW_ID_56,
    _HISTORY_KEYS as _H56,
)
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _preserve as _preserve_56
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font, _wrap
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    apply_photographic_grade,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.photo_occupancy_map import build_photo_occupancy_map
from investhome_api.services.creative_director.reference_composition_map import (
    build_reference_composition_map,
    overlay_composition_map,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba

WORKFLOW_ID_57 = "phase5_7_compositor_quality"
LOCKED_CENTERING = (0.50, 0.42)
_HISTORY_KEYS = _H56 + (("premium_master_redesign_56_tests", "quality56"),)

AD1 = {
    "blueprint_id": "2ed9a212-1f3c-48f0-a71d-e8dee04b6fd8",
    "concept_name": "Skyward Harmony",
    "reconstruction_mode": "SKY_VEIL",
    "visual_thesis": "architecture+sky verticality; text in sky veils",
}
AD2 = {
    "blueprint_id": "a8539ce4-3164-422a-8a11-7a6b5c3cc624",
    "concept_name": "Grounded Elegance",
    "reconstruction_mode": "GROUND_PLANE",
    "visual_thesis": "architecture from the ground up; commercial on ground plane",
}

PHASE56_CRITIC = {
    "professional_art_direction": 8,
    "whole_canvas_composition": 8,
    "image_design_integration": 8,
    "typography": 8,
    "hierarchy": 8,
    "commercial_storytelling": 8,
    "premium_character": 8,
}

OLD_LIMITATIONS = [
    "StructuredPremiumPlanV1 stored only reconstruction_mode",
    "compose_premium_structured placed independent elements at hardcoded corners",
    "offer/price/discount/CTA/logo had no group bbox or internal grid",
    "whole-canvas occupancy confused with compositional unity",
    "logo placement used a free rectangle",
    "CTA treated as a detached bottom inscription",
    "critic scored occupancy as craft",
]
NEW_CAPABILITIES = [
    "ReferenceCompositionMapV1 measurable geometry",
    "CreativeRelationshipGraphV1",
    "CreativeGroupV2 group-first placement",
    "CompositionalGravityEngineV1",
    "CreativeReadingFlowV1 island reject",
    "TypographicCompositionEngineV1",
    "GraphicFieldEngineV1 structured fields",
    "CommercialOfferComposerV2 one statement",
    "BrandIntegrationEngineV1",
    "EditorialCTAComposerV1 closure",
    "CreativeCanvasBalanceV2 negative vs dead space",
    "BlueprintRenderFidelityV1",
    "ReferenceCraftGapV1",
    "critic calibration hard penalties",
]


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_56(blob)
    preserved["quality56"] = list(blob.get("premium_master_redesign_56_tests") or [])
    preserved["human_master"] = dict(blob.get("human_approved_master_55c") or preserved.get("human_master") or {})
    preserved["human_master_id"] = blob.get("human_approved_master_55c_id") or preserved.get("human_master_id")
    return preserved


def _field_mass(mask: Image.Image | None) -> float:
    if not isinstance(mask, Image.Image):
        return 0.0
    hist = mask.convert("L").histogram()
    return round(sum(hist[40:]) / max(1, sum(hist)), 4)


def _plan(blueprint: dict[str, Any], *, schema: str) -> dict[str, Any]:
    return {
        "schema": schema,
        "blueprint_id": blueprint["blueprint_id"],
        "concept_name": blueprint["concept_name"],
        "reconstruction_mode": blueprint["reconstruction_mode"],
        "scale": 1.0,
        "visual_thesis": blueprint.get("visual_thesis"),
        "brand_anchor": {},
    }


def _text_board(title: str, rows: list[str], size: tuple[int, int] = (1600, 2100)) -> Image.Image:
    image = Image.new("RGB", size, (10, 12, 16))
    draw = ImageDraw.Draw(image)
    draw.text((40, 28), title, font=_font(22), fill=(232, 214, 170))
    y = 80
    for row in rows:
        for line in _wrap(str(row), 92):
            if y > size[1] - 36:
                return image
            draw.text((40, y), line, font=_font(16), fill=(226, 222, 214))
            y += 22
        y += 8
    return image


def _grid(images: list[tuple[str, Image.Image]], *, cols: int, cell: tuple[int, int], title: str) -> Image.Image:
    cw, ch = cell
    rows = (len(images) + cols - 1) // max(1, cols)
    canvas = Image.new("RGB", (cols * cw + 48, rows * (ch + 36) + 80), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 18), title, font=_font(20), fill=(232, 214, 170))
    for i, (label, im) in enumerate(images):
        gx, gy = i % cols, i // cols
        tile = im.convert("RGB").copy()
        tile.thumbnail((cw - 16, ch - 8), Image.Resampling.LANCZOS)
        x = 24 + gx * cw
        y = 64 + gy * (ch + 36)
        canvas.paste(tile, (x, y))
        draw.text((x, y + tile.size[1] + 4), label, font=_font(13), fill=(180, 176, 168))
    return canvas


def _score_pack(pack: dict[str, Any], mode: str) -> dict[str, Any]:
    objects = pack.get("objects") or {}
    groups = pack.get("groups_v2") or groups_from_objects(objects, mode=mode)
    flow = pack.get("reading_flow") or reading_flow(objects)
    mass = _field_mass(pack.get("field_mask"))
    fid = blueprint_render_fidelity(objects, groups, flow, field_mass=mass, intended_mode=mode)
    faults = detect_layout_faults(objects, field_mass=mass, islands=bool(flow.get("commercial_islands")))
    return {"fidelity": fid, "faults": faults, "flow": flow, "groups": groups, "field_mass": mass}


def generate_compositor_quality_57(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    _ = WORKFLOW_ID_56
    family = full_frame_family_spec()
    fonts = build_font_registry()
    logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    src = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY007_ASSET_ID)))).convert("RGB")
    crop, _transform = cover_fit_canvas(src, CANVAS_4X5, centering=LOCKED_CENTERING)
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    occupancy = build_photo_occupancy_map(graded)
    facts = _facts(None)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    maps = []
    graphs = []
    overlays = []
    for name, image in references:
        cmap = build_reference_composition_map(image, filename=name)
        maps.append(cmap)
        graphs.append(graph_from_reference_map(cmap))
        overlays.append((name.replace(".jpg", ""), overlay_composition_map(image, cmap)))

    def replay(blueprint: dict[str, Any]) -> dict[str, Any]:
        mode = blueprint["reconstruction_mode"]
        old = compose_premium_structured(
            graded,
            occupancy=occupancy,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            art_plan=_plan(blueprint, schema="StructuredPremiumPlanV1"),
            family=family,
            scale=1.0,
        )
        new = compose_relational_v4(
            graded,
            occupancy=occupancy,
            fonts=fonts,
            logo_rgba=logo_rgba,
            facts=facts,
            art_plan=_plan(blueprint, schema="RelationalCompositionPlanV1"),
            family=family,
            scale=1.0,
        )
        old_scored = _score_pack(old, mode)
        new_scored = _score_pack(new, mode)
        old_map = build_reference_composition_map(old["image"], filename=f"old-{mode}")
        new_map = build_reference_composition_map(new["image"], filename=f"new-{mode}")
        return {
            "blueprint": blueprint,
            "old": old,
            "new": new,
            "old_scored": old_scored,
            "new_scored": new_scored,
            "old_map": old_map,
            "new_map": new_map,
        }

    if provider_call_count() != 0:
        raise RuntimeError("Phase 5.7 must not call GPT Image")
    ad1 = replay(AD1)
    ad2 = replay(AD2)
    if provider_call_count() != 0:
        raise RuntimeError("Phase 5.7 must not call GPT Image")

    old_gap_a = reference_craft_gap(maps, ad1["old_map"])
    new_gap_a = reference_craft_gap(maps, ad1["new_map"])
    old_gap_b = reference_craft_gap(maps, ad2["old_map"])
    new_gap_b = reference_craft_gap(maps, ad2["new_map"])
    gap = craft_gap_report(
        {
            k: round((float(old_gap_a.get(k) or 0) + float(old_gap_b.get(k) or 0)) / 2, 4)
            for k in set(old_gap_a) | set(old_gap_b)
        },
        {
            k: round((float(new_gap_a.get(k) or 0) + float(new_gap_b.get(k) or 0)) / 2, 4)
            for k in set(new_gap_a) | set(new_gap_b)
        },
    )

    critic_a = apply_critic_calibration(dict(PHASE56_CRITIC), ad1["old_scored"]["faults"])
    critic_b = apply_critic_calibration(dict(PHASE56_CRITIC), ad2["old_scored"]["faults"])
    critic_new_a = apply_critic_calibration(dict(PHASE56_CRITIC), ad1["new_scored"]["faults"])
    critic_new_b = apply_critic_calibration(dict(PHASE56_CRITIC), ad2["new_scored"]["faults"])

    cal_refs = [item for item in references if item[0] in {"ORNEK_00013.jpg", "ORNEK_00006.jpg"}]
    if len(cal_refs) < 2:
        cal_refs = references[:2]
    cal_a_map = next(m for m in maps if m.get("filename") == cal_refs[0][0])
    cal_b_map = next(m for m in maps if m.get("filename") == cal_refs[1][0])
    cal_a = reconstruct_reference_grammar(cal_refs[0][1], cal_a_map, fonts=fonts, family=family, logo_rgba=logo_rgba)
    cal_b = reconstruct_reference_grammar(cal_refs[1][1], cal_b_map, fonts=fonts, family=family, logo_rgba=logo_rgba)
    cal_a_scores = score_calibration_render(cal_a["objects"], cal_a.get("groups_v2") or [], cal_a.get("reading_flow") or {}, _field_mass(cal_a.get("field_mask")))
    cal_b_scores = score_calibration_render(cal_b["objects"], cal_b.get("groups_v2") or [], cal_b.get("reading_flow") or {}, _field_mass(cal_b.get("field_mask")))
    cal_pass = all(v >= 8 for v in cal_a_scores.values()) and all(v >= 8 for v in cal_b_scores.values())
    fid_pass = bool(ad1["new_scored"]["fidelity"].get("pass") and ad2["new_scored"]["fidelity"].get("pass"))
    ready = bool(cal_pass and fid_pass)
    status = "COMPOSITOR_READY" if ready else "COMPOSITOR_NOT_READY"
    if provider_call_count() != 0:
        raise RuntimeError("Phase 5.7 must not call GPT Image")

    images = {
        "maps": _grid(overlays, cols=3, cell=(520, 640), title="01  REFERENCE COMPOSITION MAPS"),
        "graphs": _text_board(
            "02  CREATIVE RELATIONSHIP GRAPHS",
            [
                f"{g.get('filename')}  axis={g.get('axis')}"
                + " | "
                + "; ".join(f"{e['source_element']} {e['relationship_type']} {e['target_element']}" for e in (g.get('edges') or [])[:6])
                for g in graphs
            ],
        ),
        "capabilities": _text_board(
            "03  OLD VS NEW CAPABILITIES",
            ["OLD COMPOSITOR LIMITATIONS"] + [f"- {x}" for x in OLD_LIMITATIONS] + ["NEW COMPOSITOR CAPABILITIES"] + [f"- {x}" for x in NEW_CAPABILITIES],
        ),
        "ad1": render_side_by_side(ad1["old"]["image"], ad1["new"]["image"], left_label="AD1 OLD GraphicDesignCompositorV3", right_label="AD1 NEW group-first compositor", title="04  PHASE 5.6 AD1 SKYWARD HARMONY  —  OLD VS NEW"),
        "ad2": render_side_by_side(ad2["old"]["image"], ad2["new"]["image"], left_label="AD2 OLD GraphicDesignCompositorV3", right_label="AD2 NEW group-first compositor", title="05  PHASE 5.6 AD2 GROUNDED ELEGANCE  —  OLD VS NEW"),
        "fidelity": _text_board(
            "06  BLUEPRINT → RENDER FIDELITY",
            [
                f"AD1 old {ad1['old_scored']['fidelity']['scores']}",
                f"AD1 new {ad1['new_scored']['fidelity']['scores']} pass={ad1['new_scored']['fidelity']['pass']}",
                f"AD2 old {ad2['old_scored']['fidelity']['scores']}",
                f"AD2 new {ad2['new_scored']['fidelity']['scores']} pass={ad2['new_scored']['fidelity']['pass']}",
            ],
        ),
        "craft_gap": _text_board(
            "07  REFERENCE CRAFT GAP",
            [f"OLD {gap['OLD_GAP']}", f"NEW {gap['NEW_GAP']}", f"IMPROVEMENT {gap['IMPROVEMENT']}"],
        ),
        "critic": _text_board(
            "08  CRITIC CALIBRATION",
            [
                f"5.6 claimed {PHASE56_CRITIC}",
                f"AD1 faults {ad1['old_scored']['faults']}",
                f"AD1 after { {k: critic_a.get(k) for k in ('professional_art_direction','whole_canvas_composition','image_design_integration','calibration_capped')} }",
                f"AD2 faults {ad2['old_scored']['faults']}",
                f"AD2 after { {k: critic_b.get(k) for k in ('professional_art_direction','whole_canvas_composition','image_design_integration','calibration_capped')} }",
            ],
        ),
        "cal_a": cal_a["image"],
        "cal_b": cal_b["image"],
        "cal_compare": render_side_by_side(cal_a["image"], cal_b["image"], left_label=str(cal_refs[0][0]), right_label=str(cal_refs[1][0]), title="11  REFERENCE CALIBRATION COMPARISON"),
        "review": _text_board(
            "12  HUMAN REVIEW BOARD  —  PHASE 5.7",
            [
                f"STATUS {status}",
                "Do not promote Phase 5.6 A/B. Do not create a new Temple Master.",
                f"ROOT LOSS  Blueprint→Plan stored only mode; compositor placed independent corners.",
                f"AD1 fidelity old→new {ad1['old_scored']['fidelity']['scores'].get('whole_canvas_fidelity')} → {ad1['new_scored']['fidelity']['scores'].get('whole_canvas_fidelity')}",
                f"AD2 fidelity old→new {ad2['old_scored']['fidelity']['scores'].get('whole_canvas_fidelity')} → {ad2['new_scored']['fidelity']['scores'].get('whole_canvas_fidelity')}",
                f"Calibration A {cal_a_scores}",
                f"Calibration B {cal_b_scores}",
                f"COMPOSITOR READY FOR NEW MASTER: {'YES' if ready else 'NO'}",
                "GPT IMAGE CALLS 0",
                "EXISTING MASTER CHANGED NO",
                "PRODUCTION COVER CHANGED NO",
            ],
        ),
    }
    _ = creative_canvas_balance_v2(ad1["new"]["image"], ad1["new"]["objects"], ad1["new"].get("field_mask"), occupancy, ad1["new"].get("groups_v2"))
    _ = compositional_gravity(occupancy, ad1["new"]["objects"])
    _ = temple_relationship_graph(mode="SKY_VEIL")
    _ = user
    _ = language
    _ = uuid4

    record = {
        "workflow": WORKFLOW_ID_57,
        "status": status,
        "compositor_ready": ready,
        "promoted_to_master": False,
        "new_temple_master_created": False,
        "gpt_image_calls": provider_call_count(),
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "price_revision_asset_id": PRICE_R1_ASSET_ID,
        "price_revision_child_changed": False,
        "visual_replace_child_id": "6f18ae33-72fb-4506-ab49-24f8d90b6c2d",
        "production_cover_changed": False,
        "photo_filename": DAY007_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "references_ok": refs_ok,
        "reference_maps": maps,
        "relationship_graphs": graphs,
        "ad1": {
            "old_fidelity": ad1["old_scored"]["fidelity"],
            "new_fidelity": ad1["new_scored"]["fidelity"],
            "old_faults": ad1["old_scored"]["faults"],
            "new_faults": ad1["new_scored"]["faults"],
        },
        "ad2": {
            "old_fidelity": ad2["old_scored"]["fidelity"],
            "new_fidelity": ad2["new_scored"]["fidelity"],
            "old_faults": ad2["old_scored"]["faults"],
            "new_faults": ad2["new_scored"]["faults"],
        },
        "craft_gap": gap,
        "critic_calibration": {"before": PHASE56_CRITIC, "ad1_after": critic_a, "ad2_after": critic_b, "new_ad1": critic_new_a, "new_ad2": critic_new_b},
        "reference_calibration": {"a": cal_a_scores, "b": cal_b_scores, "pass": cal_pass, "a_file": cal_refs[0][0], "b_file": cal_refs[1][0]},
        "root_quality_loss": [
            "Blueprint → Plan translation (StructuredPremiumPlanV1 stored only reconstruction_mode)",
            "GraphicDesignCompositorV3 compose_premium_structured (independent corner placement)",
            "PremiumBlueprintCriticV2 / final critic (occupancy scored as whole-canvas craft)",
        ],
        "old_limitations": OLD_LIMITATIONS,
        "new_capabilities": NEW_CAPABILITIES,
        "ref_provenance": ref_provenance,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "created_at": _now(),
    }
    tests = [t for t in list(blob.get("compositor_quality_57_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_57)]
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["compositor_quality_57_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 5.7 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["ad1_images"] = {"old": ad1["old"]["image"], "new": ad1["new"]["image"]}
    record["ad2_images"] = {"old": ad2["old"]["image"], "new": ad2["new"]["image"]}
    return record
