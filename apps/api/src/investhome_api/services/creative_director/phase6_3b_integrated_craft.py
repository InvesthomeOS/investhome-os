"""Phase 6.3B — Chromium integrated craft proof.

Locked A3 aperture + locked Proof B arc + EditorialTypographySystemV1.
D2 then E2 as whole compositions. No Temple Master. GPT Image = 0.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    _vision,
    font_face_css,
    inline_logo_svg,
)
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5, cover_fit_canvas
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
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    analyze_concept3_pixels,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_3_scene_graph import render_proof
from investhome_api.services.creative_director.phase6_3a_chromium_craft import _HISTORY_KEYS as _H63A
from investhome_api.services.creative_director.phase6_3a_chromium_craft import _preserve as _preserve_63a
from investhome_api.services.creative_director.phase6_3b_scene import (
    A3_INTEGRATED,
    D2_KEYS,
    E2_KEYS,
    LOCKED_A3,
    TYPE_KEYS,
    TYPE_MUST,
    TYPE_STUDIES,
    aperture_hurts_d2,
    d2_html,
    d2_pass,
    e2_html,
    e2_pass,
    format_compatibility,
    revision_compatibility,
    structured_scene_validation,
    type_continue_ok,
    typography_study_html,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_63B = "phase6_3b_integrated_craft_proof"
SELECTED_RENDERER = "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
_HISTORY_KEYS = _H63A + (("chromium_craft_63a_tests", "quality63a"),)
PROOF_B_LOCKED = {
    "status": "LOCKED PASS",
    "scores": {"CRAFT_FIDELITY": 9, "GRAPHIC_PRECISION": 9, "REFERENCE_BEHAVIOR_MATCH": 9},
}

_CRITIC = (
    "You are a production graphic-design critic. Judge visual craft against Concept 3 DESIGN BEHAVIOR. "
    "Do not reward occupancy, element count, or canvas coverage. "
    "Do not penalize real Day_007 for not being Concept 3's invented skyline. "
    "Do not inflate. JSON only."
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_63a(blob)
    preserved["quality63a"] = list(blob.get("chromium_craft_63a_tests") or [])
    return preserved


def _empty(keys: tuple[str, ...], reason: str) -> dict[str, Any]:
    return {"scores": {k: 0.0 for k in keys}, "failed": list(keys), "pass": False, "diagnosis": reason, "status": "FAIL", "average": 0.0}


def _scores(raw: dict[str, Any], keys: tuple[str, ...]) -> dict[str, float]:
    src = raw.get("scores") if isinstance(raw.get("scores"), dict) else raw
    return {k: round(_num(src.get(k), 0), 2) for k in keys}


def _vision_json(content: list[Any]) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _CRITIC},
                {"role": "user", "content": content},
            ],
        }
    )
    return parsed if isinstance(parsed, dict) else {}, calls


def request_type_critic(concept: Image.Image, studies: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    ref = concept.crop((0, 0, int(concept.width * 0.50), concept.height))
    blocks: dict[str, Any] = {}
    calls = 0
    for batch in (("T1", "T2"), ("T3", "T4")):
        content: list[Any] = [
            _text(
                "IMAGE 1 is Concept 3 LEFT typographic craft (cropped). Following images are live OpenType studies "
                "on a NEUTRAL charcoal field. Score EACH independently 0-10 for: " + ", ".join(TYPE_KEYS) + ". "
                "DISPLAY_HEADLINE is one composition. OFFER_HERO + OFFER_LABEL is one composition. "
                "Price relates to the offer. Unit supports the story. CTA is a hairline inscription. "
                "Closure is tertiary canvas closure. Do not copy scores. "
                "JSON {T?:{scores:{...},diagnosis:one sentence}}."
            ),
            _text("CONCEPT 3 TYPE COLUMN"),
            _img(ref, quality=86),
        ]
        for key in batch:
            content.append(_text(f"STUDY {key}"))
            content.append(_img(studies[key], quality=88))
        parsed, n = _vision_json(content)
        calls += n
        for key in batch:
            raw = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
            scores = _scores(raw, TYPE_KEYS)
            ok = type_continue_ok({"scores": scores})
            blocks[key] = {
                "scores": scores,
                "diagnosis": str(raw.get("diagnosis") or raw.get("notes") or ""),
                "continue_ok": ok,
                "pass": ok,
                "status": "PASS" if ok else "FAIL",
            }
    return {"schema": "TypographyCalibrationV1", "treatments": blocks, "roles": list(TYPE_MUST)}, calls


def request_whole_critic(*, name: str, brief: str, keys: tuple[str, ...], concept: Image.Image, proof: Image.Image) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            f"{name}. {brief} Score the WHOLE composition 0-10 for: " + ", ".join(keys) + ". "
            "Do not independently optimize component scores. One short visual diagnosis. "
            "JSON {scores:{...},diagnosis:''}."
        ),
        _text("CONCEPT 3 CRAFT REFERENCE"),
        _img(concept, quality=84),
        _text(name),
        _img(proof, quality=88),
    ]
    parsed, calls = _vision_json(content)
    scores = _scores(parsed, keys)
    return {
        "scores": scores,
        "diagnosis": str(parsed.get("diagnosis") or parsed.get("notes") or ""),
    }, calls


def _pick_type(blocks: dict[str, Any]) -> str:
    order = ("T1", "T2", "T3", "T4")
    ok = [k for k in order if (blocks.get(k) or {}).get("continue_ok")]

    def _rank(key: str) -> tuple[float, float]:
        scores = (blocks.get(key) or {}).get("scores") or {}
        must = min((float(scores.get(k, 0)) for k in TYPE_MUST), default=0.0)
        avg = sum(float(v) for v in scores.values()) / max(len(scores), 1) if scores else 0.0
        return (must, avg)

    pool = ok or list(order)
    return max(pool, key=_rank)


def _skipped(title: str, reason: str) -> Image.Image:
    return _text_board(title, [reason], size=(1088, 1360))


def _triple(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 14), title, font=_font(18), fill=(201, 168, 92))
    slot = 600
    x = 28
    for label, image in tiles[:3]:
        tile = image.copy()
        tile.thumbnail((slot, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 910), label[:40], font=_font(14), fill=(226, 222, 214))
        x += slot + 20
    return canvas


def _score_rows(title: str, block: dict[str, Any]) -> Image.Image:
    scores = block.get("scores") or {}
    rows = [f"{k}: {scores.get(k)}" for k in scores]
    rows += [
        f"average {block.get('average')}",
        f"failed {block.get('failed')}",
        f"status {block.get('status')}",
        str(block.get("diagnosis") or ""),
    ]
    return _text_board(title, rows, size=(1280, 1700))


def generate_phase6_3b_integrated_craft(
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
    vision_calls = 0
    _ = user

    concept = load_approved_concept3(db)
    if concept.size != CANVAS_4X5:
        concept = ImageOps.fit(concept, CANVAS_4X5, method=Image.Resampling.LANCZOS)
    source = load_day007(db)
    photo, _transform = cover_fit_canvas(source, CANVAS_4X5, centering=(0.68, 0.20))
    structure = analyze_concept3_pixels(concept)
    fonts = build_font_registry()
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)))
    photo_uri = _jpeg_data_uri(photo, quality=92)
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3B forbids GPT Image production calls")

    studies = {spec["id"]: render_proof(typography_study_html(spec, font_css)) for spec in TYPE_STUDIES}
    type_cal, n = request_type_critic(concept, studies)
    vision_calls += n
    selected_t_id = _pick_type(type_cal["treatments"])
    selected_t = next(s for s in TYPE_STUDIES if s["id"] == selected_t_id)
    selected_t_block = type_cal["treatments"][selected_t_id]
    type_cal["selected"] = selected_t_id
    type_cal["selected_note"] = selected_t["note"]
    # Isolated type 9-floors are recorded, but 6.3B's primary test is integrated D2.
    # Continue with the strongest study even if charcoal-only type is short of 9.
    type_cal["continue_to_d2"] = True
    aperture_used = dict(LOCKED_A3)
    integrated_adjustment = False
    e2_img = None
    e2_block = _empty(E2_KEYS, "E2 not run")
    stop_at = None
    decision = "CHROMIUM_INTEGRATED_CRAFT_NOT_READY"

    d2_img = render_proof(d2_html(photo_uri, structure, aperture_used, selected_t, font_css))
    raw, n = request_whole_critic(
        name="PROOF D2 INTEGRATED",
        brief=(
            "REAL Day_007 + locked A3 aperture + locked Proof B arc + selected typography. "
            "No logo, no CTA, no bottom closure. "
            "Do PHOTO + APERTURE + ARC + TYPE behave as ONE designed composition?"
        ),
        keys=D2_KEYS,
        concept=concept,
        proof=d2_img,
    )
    vision_calls += n
    ok, failed, avg = d2_pass(raw)
    d2_block = {**raw, "failed": failed, "average": avg, "pass": ok, "status": "PASS" if ok else "FAIL", "aperture": aperture_used["id"]}
    if (not ok) and aperture_hurts_d2(d2_block):
        integrated_adjustment = True
        aperture_used = dict(A3_INTEGRATED)
        d2_img = render_proof(d2_html(photo_uri, structure, aperture_used, selected_t, font_css))
        raw, n = request_whole_critic(
            name="PROOF D2 A3-INTEGRATED",
            brief=(
                "Same D2 after ONE aperture adjustment: opacity / multiply / vignette / edge only. "
                "Geometry unchanged. Judge the FULL composition, not the isolated aperture."
            ),
            keys=D2_KEYS,
            concept=concept,
            proof=d2_img,
        )
        vision_calls += n
        ok, failed, avg = d2_pass(raw)
        d2_block = {
            **raw,
            "failed": failed,
            "average": avg,
            "pass": ok,
            "status": "PASS" if ok else "FAIL",
            "aperture": aperture_used["id"],
        }
    if not ok:
        stop_at = "D2"
        e2_img = _skipped("10  E2  —  NOT RUN", "D2 did not pass.")
    else:
        e2_img = render_proof(e2_html(photo_uri, structure, aperture_used, selected_t, logo_markup, font_css))
        raw, n = request_whole_critic(
            name="PROOF E2 COMPLETE SCENE",
            brief=(
                "Complete micro-scene: photo, A3 aperture, locked arc, headline, offer, price, unit, "
                "REAL Temple SVG logo, editorial CTA, canvas closure. "
                "Architecture fidelity is about the real Day_007 building, not invented landmarks. "
                "Logo must participate in the column, not sit in leftover space. "
                "CTA is hairline inscription. Closure is tertiary, not a footer."
            ),
            keys=E2_KEYS,
            concept=concept,
            proof=e2_img,
        )
        vision_calls += n
        ok_e, failed_e, avg_e = e2_pass(raw)
        e2_block = {**raw, "failed": failed_e, "average": avg_e, "pass": ok_e, "status": "PASS" if ok_e else "FAIL"}
        if not ok_e:
            stop_at = "E2"
        else:
            decision = "CHROMIUM_INTEGRATED_CRAFT_READY"

    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3B forbids GPT Image production calls")

    scene = structured_scene_validation()
    rev = revision_compatibility()
    fmt = format_compatibility()
    logo_status = "PASS" if (e2_img is not None and stop_at not in {"TYPOGRAPHY", "D2"} and "<svg" in logo_markup.lower()) else "FAIL"
    selected_type_img = studies[selected_t_id]
    e2_for_board = e2_img if (e2_img is not None and stop_at not in {"TYPOGRAPHY", "D2"}) else (e2_img or _skipped("E2", "Not run"))

    images = {
        "reference": concept.convert("RGB"),
        "T1": studies["T1"],
        "T2": studies["T2"],
        "T3": studies["T3"],
        "T4": studies["T4"],
        "type_compare": _type_quad(studies),
        "type_selected": selected_type_img,
        "d2": d2_img if d2_img is not None else _skipped("D2", "Not run"),
        "d2_critic": _score_rows("09  D2 CRITIC", d2_block),
        "e2": e2_for_board,
        "e2_critic": _score_rows("11  E2 CRITIC", e2_block),
        "compare": _triple(
            "12  CONCEPT 3  vs  D2  vs  E2",
            [
                ("CONCEPT 3", concept),
                ("D2", d2_img if d2_img is not None else _skipped("D2", "Not run")),
                ("E2", e2_for_board),
            ],
        ),
        "scene": _text_board(
            "13  STRUCTURED SCENE VALIDATION",
            [f"{o['id']}  {o['kind']}  {o.get('live') or o.get('role') or o.get('locked')} " for o in scene["objects"]]
            + [f"flattened {scene['flattened_campaign_raster']}", f"status {scene['status']}"],
        ),
        "revision": _text_board(
            "14  REVISION COMPATIBILITY  —  not executed",
            [f"{k}: {v.get('status') if isinstance(v, dict) else v}" for k, v in rev.items() if k != "schema"],
        ),
        "format": _text_board(
            "15  FORMAT COMPATIBILITY  —  not rendered",
            [f"{k}: {v}" for k, v in (fmt.get("formats") or {}).items()] + [f"status {fmt.get('status')}"],
        ),
        "review": _triple(
            "16  HUMAN REVIEW BOARD  —  no scores on artwork",
            [
                ("CONCEPT 3", concept),
                ("D2 INTEGRATED", d2_img if d2_img is not None else _skipped("D2", "Not run")),
                ("E2 COMPLETE", e2_for_board),
            ],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_63B,
        "created_at": _now(),
        "status": decision,
        "final_decision": decision,
        "renderer": SELECTED_RENDERER,
        "aperture": {"locked": "A3", "integrated_adjustment": integrated_adjustment, "used": aperture_used["id"]},
        "proof_b": PROOF_B_LOCKED,
        "typography_calibration": type_cal,
        "selected_typography": selected_t_id,
        "d2": d2_block,
        "e2": e2_block,
        "structured_scene_validation": scene,
        "revision_compatibility": rev,
        "format_compatibility": fmt,
        "real_temple_logo": logo_status,
        "stop_at": stop_at,
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "new_master_created": False,
        "promoted_to_master": False,
        "production_cover_changed": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "day007_asset_id": DAY007_ASSET_ID,
        "gold_standard": CONCEPT3_ASSET_ID,
        "language": language,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = list(blob.get("integrated_craft_63b_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["integrated_craft_63b_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    blob["human_approved_master_55c"] = preserved.get("human_master")
    blob["human_approved_master_55c_id"] = preserved.get("human_master_id")
    blob["new_premium_master_58_tests"] = preserved.get("quality58")
    blob["ai_draft_structured_master_59_tests"] = preserved.get("quality59")
    blob["pure_creative_director_60_tests"] = preserved.get("quality60")
    blob["concept3_production_master_61_tests"] = preserved.get("quality61")
    blob["concept3_r1_61_tests"] = preserved.get("quality61r1")
    blob["real_photo_native_62_tests"] = preserved.get("quality62")
    blob["renderer_capability_63_tests"] = preserved.get("quality63")
    blob["chromium_craft_63a_tests"] = preserved.get("quality63a")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.3B refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record


def _type_quad(studies: dict[str, Image.Image]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 14), "06  TYPOGRAPHY COMPARISON  T1–T4", font=_font(18), fill=(201, 168, 92))
    for i, key in enumerate(("T1", "T2", "T3", "T4")):
        tile = studies[key].copy()
        tile.thumbnail((440, 980), Image.Resampling.LANCZOS)
        x = 28 + i * 470
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1048), key, font=_font(14), fill=(226, 222, 214))
    return canvas
