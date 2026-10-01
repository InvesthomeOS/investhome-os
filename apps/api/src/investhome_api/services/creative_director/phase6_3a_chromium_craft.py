"""Phase 6.3A — Chromium scene-graph craft calibration.

Calibrates aperture, type-in-field, integration, and brand closure.
Proof B arc remains locked from Phase 6.3. No Temple Master. GPT Image = 0.
"""

from __future__ import annotations

import json
import math
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
from investhome_api.services.creative_director.phase6_3_renderer_capability_gap import _HISTORY_KEYS as _H63
from investhome_api.services.creative_director.phase6_3_renderer_capability_gap import _preserve as _preserve_63
from investhome_api.services.creative_director.phase6_3_scene_graph import proof_b_html, render_proof
from investhome_api.services.creative_director.phase6_3a_craft import (
    APERTURE_KEYS,
    APERTURE_TREATMENTS,
    D2_KEYS,
    E2_KEYS,
    TYPE_KEYS,
    TYPE_TREATMENTS,
    aperture_html,
    format_compatibility,
    proof_d2_html,
    proof_e2_html,
    revision_compatibility,
    scene_graph_properties,
    type_in_aperture_html,
    type_neutral_html,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_63A = "phase6_3a_chromium_craft_calibration"
SELECTED_RENDERER = "HTML_CSS_SVG_SCENE_GRAPH_CHROMIUM"
_HISTORY_KEYS = _H63 + (("renderer_capability_63_tests", "quality63"),)
PROOF_B_LOCKED = {
    "status": "LOCKED PASS",
    "scores": {"CRAFT_FIDELITY": 9, "GRAPHIC_PRECISION": 9, "REFERENCE_BEHAVIOR_MATCH": 9},
    "note": "Phase 6.3 Proof B. Not redesigned.",
}

_CRITIC_SYSTEM = (
    "You are a production graphic-design critic, not a coverage counter. "
    "Score visual craft against Concept 3 DESIGN BEHAVIOR only. "
    "Do not reward occupancy, element count, or canvas coverage. "
    "Do not penalize the real Day_007 photograph for not being Concept 3's invented skyline. "
    "9 means production-grade for that isolated behavior. 8 is still a renderer gap. Do not inflate. JSON only."
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_63(blob)
    preserved["quality63"] = list(blob.get("renderer_capability_63_tests") or [])
    return preserved


def _empty_block(keys: tuple[str, ...], *, reason: str) -> dict[str, Any]:
    scores = {k: 0.0 for k in keys}
    return {
        "scores": scores,
        "failed": list(keys),
        "pass": False,
        "diagnosis": reason,
        "status": "FAIL",
    }


def _normalize_block(raw: dict[str, Any], keys: tuple[str, ...], *, diagnosis: str = "") -> dict[str, Any]:
    src = raw.get("scores") if isinstance(raw.get("scores"), dict) else raw
    scores = {k: round(_num(src.get(k), 0), 2) for k in keys}
    failed = [k for k in keys if scores.get(k, 0) < 9]
    note = str(raw.get("diagnosis") or raw.get("notes") or diagnosis or "")
    passed = bool(scores) and not failed and all(scores.get(k, 0) > 0 for k in keys)
    return {
        "scores": scores,
        "failed": failed,
        "pass": passed,
        "diagnosis": note,
        "status": "PASS" if passed else "FAIL",
    }


def _pick_passing(blocks: dict[str, dict[str, Any]], order: tuple[str, ...]) -> str | None:
    passing = [k for k in order if (blocks.get(k) or {}).get("pass")]
    if not passing:
        return None

    def _min_score(key: str) -> float:
        scores = (blocks.get(key) or {}).get("scores") or {}
        return min((float(v) for v in scores.values()), default=0.0)

    return max(passing, key=_min_score)


def _best_min(blocks: dict[str, dict[str, Any]], order: tuple[str, ...]) -> str:
    def _min_score(key: str) -> float:
        scores = (blocks.get(key) or {}).get("scores") or {}
        return min((float(v) for v in scores.values()), default=0.0)

    return max(order, key=_min_score)


def _vision_json(content: list[Any]) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _CRITIC_SYSTEM},
                {"role": "user", "content": content},
            ],
        }
    )
    return parsed if isinstance(parsed, dict) else {}, calls


def request_aperture_critic(concept: Image.Image, treatments: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    ref = concept.crop((0, 0, int(concept.width * 0.52), concept.height))
    blocks: dict[str, Any] = {}
    calls = 0
    batches = (("A1", "A2", "A3"), ("A4", "A5", "A6"))
    for batch in batches:
        content: list[Any] = [
            _text(
                "IMAGE 1 is the LEFT aperture of Concept 3 (cropped). Ignore invented skyline. "
                "Following images are isolated aperture treatments on real Day_007. No type. "
                "Score EACH treatment independently 0-10 for: " + ", ".join(APERTURE_KEYS) + ". "
                "Pass requires a layered charcoal COLUMN with photographic texture still visible, "
                "a continuous anti-aliased elliptical curve, and a decisive edge. "
                "A grey stain, a wedge collapsing to a corner, or identical scores across visibly different treatments fail. "
                "Do not copy scores between treatments. JSON {A?:{scores:{...},diagnosis:one sentence}}."
            ),
            _text("IMAGE 1 — CONCEPT 3 LEFT APERTURE"),
            _img(ref, quality=86),
        ]
        for key in batch:
            content.append(_text(f"TREATMENT {key}"))
            content.append(_img(treatments[key], quality=86))
        parsed, n = _vision_json(content)
        calls += n
        for key in batch:
            raw = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
            blocks[key] = _normalize_block(raw, APERTURE_KEYS)
    return {"schema": "ApertureCalibrationV1", "treatments": blocks}, calls


def request_type_board_critic(concept: Image.Image, treatments: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    keys = tuple(k for k in TYPE_KEYS if k != "REFERENCE_BEHAVIOR_MATCH")
    content: list[Any] = [
        _text(
            "IMAGE 1 is Concept 3 typographic grouping. Images 2-5 are T1-T4 on a NEUTRAL charcoal field. "
            "Live Cormorant / Source Sans 3. Score grouping, not occupancy. Metrics: " + ", ".join(keys) + ". "
            "ALIRKEN smaller than KAZAN; %35 is major gold; LANSMAN AVANTAJI tracked sans; "
            "675.000 USD as a pair; 2+1 stacked above DAİRE; hairline gold rules between groups. "
            "HTML labels / unrelated absolute lines fail. JSON {T1:{scores:{...},diagnosis:''},...}."
        ),
        _text("IMAGE 1 — CONCEPT 3 TYPE BEHAVIOR"),
        _img(concept, quality=84),
    ]
    for key in ("T1", "T2", "T3", "T4"):
        content.append(_text(f"IMAGE — TYPE {key}"))
        content.append(_img(treatments[key], quality=84))
    parsed, calls = _vision_json(content)
    blocks = {}
    for key in ("T1", "T2", "T3", "T4"):
        raw = parsed.get(key) if isinstance(parsed.get(key), dict) else {}
        blocks[key] = _normalize_block(raw, keys)
    return {"schema": "TypographyCalibrationV1", "treatments": blocks, "select_keys": list(keys)}, calls


def request_named_critic(
    *,
    name: str,
    brief: str,
    keys: tuple[str, ...],
    concept: Image.Image,
    proof: Image.Image,
) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            f"{name}. {brief} Score 0-10 for: " + ", ".join(keys) + ". "
            "Every metric must be independently >=9. Do not average. One short visual diagnosis. "
            "JSON {scores:{...},diagnosis:''}."
        ),
        _text("IMAGE 1 — CONCEPT 3 REFERENCE BEHAVIOR"),
        _img(concept, quality=84),
        _text(f"IMAGE 2 — {name}"),
        _img(proof, quality=86),
    ]
    parsed, calls = _vision_json(content)
    block = _normalize_block(parsed, keys, diagnosis=str(parsed.get("diagnosis") or ""))
    return block, calls


def _contact_sheet(title: str, tiles: list[tuple[str, Image.Image]], *, cols: int) -> Image.Image:
    n = max(len(tiles), 1)
    rows = math.ceil(n / cols)
    tw, th = 340, 425
    canvas = Image.new("RGB", (40 + cols * (tw + 20), 64 + rows * (th + 36)), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    for i, (label, image) in enumerate(tiles):
        r, c = divmod(i, cols)
        x = 28 + c * (tw + 20)
        y = 52 + r * (th + 36)
        tile = image.copy()
        tile.thumbnail((tw, th), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + tile.height + 4), label[:42], font=_font(13), fill=(226, 222, 214))
    return canvas


def _caption(image: Image.Image, title: str) -> Image.Image:
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    draw.rectangle((0, 0, out.width, 32), fill=(12, 14, 20))
    draw.text((14, 7), title, font=_font(14), fill=(201, 168, 92))
    return out


def _skipped(title: str, reason: str) -> Image.Image:
    return _text_board(title, [reason, "STOP RULE — not rendered as a product design"], size=(1088, 1360))


def _human_board(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    n = max(len(tiles), 1)
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 14), title, font=_font(18), fill=(201, 168, 92))
    slot = min(360, int((1920 - 48) / n) - 12)
    x = 28
    for label, image in tiles:
        tile = image.copy()
        tile.thumbnail((slot, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 910), label[:36], font=_font(13), fill=(226, 222, 214))
        x += slot + 16
    return canvas


def generate_phase6_3a_chromium_craft(
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

    apertures = {
        spec["id"]: render_proof(aperture_html(photo_uri, structure, spec, font_css))
        for spec in APERTURE_TREATMENTS
    }
    locked_b = render_proof(proof_b_html(structure, font_css))
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3A forbids GPT Image production calls")

    aperture_cal, n = request_aperture_critic(concept, apertures)
    vision_calls += n
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3A forbids GPT Image production calls")

    a_ids = tuple(s["id"] for s in APERTURE_TREATMENTS)
    selected_a_id = _pick_passing(aperture_cal["treatments"], a_ids)
    aperture_pass = selected_a_id is not None
    if selected_a_id is None:
        selected_a_id = _best_min(aperture_cal["treatments"], a_ids)
    selected_a_spec = next(s for s in APERTURE_TREATMENTS if s["id"] == selected_a_id)
    selected_a_img = apertures[selected_a_id]
    selected_a_block = aperture_cal["treatments"][selected_a_id]
    aperture_cal["selected"] = selected_a_id
    aperture_cal["selected_pass"] = aperture_pass
    aperture_cal["selected_note"] = selected_a_spec["note"]

    type_cal: dict[str, Any] = {"schema": "TypographyCalibrationV1", "skipped": True}
    types: dict[str, Image.Image] = {}
    selected_t_id = None
    selected_t_spec = None
    selected_t_img = None
    type_pass = False
    c2_img = None
    c2_block = _empty_block(TYPE_KEYS, reason="Typography not run — aperture did not pass")
    d2_img = None
    d2_block = _empty_block(D2_KEYS, reason="D2 not run")
    e2_img = None
    e2_block = _empty_block(E2_KEYS, reason="E2 not run")
    stop_at = None

    if not aperture_pass:
        stop_at = "APERTURE"
        c2_img = _skipped("05  SELECTED TYPOGRAPHY  —  NOT RUN", "Aperture failed all A1–A6 floors.")
        d2_img = _skipped("07  PROOF D2  —  NOT RUN", "Stopped after aperture.")
        e2_img = _skipped("08  PROOF E2  —  NOT RUN", "Stopped after aperture.")
    else:
        types = {spec["id"]: render_proof(type_neutral_html(spec, font_css)) for spec in TYPE_TREATMENTS}
        type_cal, n = request_type_board_critic(concept, types)
        vision_calls += n
        t_ids = tuple(s["id"] for s in TYPE_TREATMENTS)
        selected_t_id = _pick_passing(type_cal["treatments"], t_ids) or _best_min(type_cal["treatments"], t_ids)
        selected_t_spec = next(s for s in TYPE_TREATMENTS if s["id"] == selected_t_id)
        selected_t_img = types[selected_t_id]
        type_cal["selected"] = selected_t_id
        type_cal["selected_note"] = selected_t_spec["note"]
        c2_img = render_proof(type_in_aperture_html(photo_uri, structure, selected_a_spec, selected_t_spec, font_css))
        c2_block, n = request_named_critic(
            name="C2 SELECTED TYPOGRAPHY IN APERTURE",
            brief=(
                "Typography must feel embedded in the calibrated charcoal aperture, not pasted on the photo "
                "and not floating as HTML labels. Live type. Evaluate Concept 3 grouping behavior."
            ),
            keys=TYPE_KEYS,
            concept=concept,
            proof=c2_img,
        )
        vision_calls += n
        type_pass = bool(c2_block.get("pass"))
        type_cal["c2"] = c2_block
        type_cal["selected_pass"] = type_pass
        type_cal["skipped"] = False
        if not type_pass:
            stop_at = "TYPOGRAPHY"
            d2_img = _skipped("07  PROOF D2  —  NOT RUN", "Typography did not pass.")
            e2_img = _skipped("08  PROOF E2  —  NOT RUN", "Typography did not pass.")
        else:
            d2_img = render_proof(proof_d2_html(photo_uri, structure, selected_a_spec, selected_t_spec, font_css))
            d2_block, n = request_named_critic(
                name="PROOF D2 INTEGRATED",
                brief=(
                    "Contains ONLY real Day_007, the selected aperture, the LOCKED Phase 6.3 arc, "
                    "and the selected campaign typography. No logo, no CTA, no bottom closure. "
                    "Ask: do type, aperture, arc, and photograph behave as ONE art-directed composition?"
                ),
                keys=D2_KEYS,
                concept=concept,
                proof=d2_img,
            )
            vision_calls += n
            if not d2_block.get("pass"):
                stop_at = "D2"
                e2_img = _skipped("08  PROOF E2  —  NOT RUN", "Proof D2 did not pass.")
            else:
                e2_img = render_proof(
                    proof_e2_html(photo_uri, structure, selected_a_spec, selected_t_spec, logo_markup, font_css)
                )
                e2_block, n = request_named_critic(
                    name="PROOF E2 BRAND / CTA / CLOSURE",
                    brief=(
                        "Real Temple SVG logo with a designed THE TEMPLE caption (do not double-print SVG text). "
                        "CTA is an editorial hairline inscription, not a pill. "
                        "TARİHİN RUHU, GELECEĞİN DEĞERİ. is tertiary canvas closure, not a footer."
                    ),
                    keys=E2_KEYS,
                    concept=concept,
                    proof=e2_img,
                )
                vision_calls += n
                if not e2_block.get("pass"):
                    stop_at = "E2"

    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.3A forbids GPT Image production calls")

    all_pass = bool(aperture_pass and type_pass and d2_block.get("pass") and e2_block.get("pass"))
    decision = "CHROMIUM_CRAFT_READY_FOR_MASTER" if all_pass else "CHROMIUM_CRAFT_NOT_READY"
    status = decision
    objects = scene_graph_properties()
    rev = revision_compatibility()
    fmt = format_compatibility()

    scores_pack = {
        "schema": "MicroProofScoresV1",
        "proof_b": PROOF_B_LOCKED,
        "aperture": selected_a_block,
        "aperture_id": selected_a_id,
        "typography": c2_block,
        "typography_id": selected_t_id,
        "d2": d2_block,
        "e2": e2_block,
        "all_pass": all_pass,
        "stop_at": stop_at,
    }

    critic_rows = [
        f"PROOF B ARC  LOCKED PASS  {PROOF_B_LOCKED['scores']}",
        f"APERTURE {selected_a_id}  {selected_a_block.get('status')}  failed={selected_a_block.get('failed')}",
        f"  {selected_a_block.get('scores')}",
        f"  {selected_a_block.get('diagnosis')}",
        f"TYPOGRAPHY {selected_t_id}  {c2_block.get('status')}  failed={c2_block.get('failed')}",
        f"  {c2_block.get('scores')}",
        f"  {c2_block.get('diagnosis')}",
        f"D2  {d2_block.get('status')}  failed={d2_block.get('failed')}",
        f"  {d2_block.get('scores')}",
        f"  {d2_block.get('diagnosis')}",
        f"E2  {e2_block.get('status')}  failed={e2_block.get('failed')}",
        f"  {e2_block.get('scores')}",
        f"  {e2_block.get('diagnosis')}",
        f"FINAL {decision}",
    ]

    type_board = (
        _contact_sheet(
            "04  TYPOGRAPHY CALIBRATION  T1–T4  —  charcoal, no photo",
            [(f"{k}  {next(s['note'] for s in TYPE_TREATMENTS if s['id']==k)}", types[k]) for k in ("T1", "T2", "T3", "T4")],
            cols=2,
        )
        if types
        else _skipped("04  TYPOGRAPHY CALIBRATION  —  NOT RUN", "Aperture failed.")
    )
    selected_type_proof = c2_img if c2_img is not None else _skipped("05  SELECTED TYPOGRAPHY", "Not run")
    human_tiles = [
        ("CONCEPT 3", concept),
        (f"APERTURE {selected_a_id}", selected_a_img),
        ("LOCKED B ARC", locked_b),
        (f"C2 {selected_t_id or '-'}", selected_type_proof),
        ("D2", d2_img if d2_img is not None else _skipped("D2", "Not run")),
        ("E2", e2_img if e2_img is not None else _skipped("E2", "Not run")),
    ]

    images = {
        "reference": _caption(concept, "01  CONCEPT 3  —  craft target, not a skyline to copy"),
        "aperture_board": _contact_sheet(
            "02  APERTURE CALIBRATION  A1–A6  —  same Day_007, no type",
            [(f"{s['id']}  {s['note']}", apertures[s["id"]]) for s in APERTURE_TREATMENTS],
            cols=3,
        ),
        "aperture_selected": _caption(selected_a_img, f"03  SELECTED APERTURE  {selected_a_id}  {selected_a_block.get('status')}"),
        "type_board": type_board,
        "type_selected": _caption(selected_type_proof, f"05  SELECTED TYPOGRAPHY  {selected_t_id or 'NOT RUN'}  {c2_block.get('status')}"),
        "locked_b": _caption(locked_b, "06  PROOF B  —  LOCKED ARC  —  do not recalibrate"),
        "d2": _caption(d2_img if d2_img is not None else _skipped("D2", "Not run"), f"07  PROOF D2  {d2_block.get('status')}"),
        "e2": _caption(e2_img if e2_img is not None else _skipped("E2", "Not run"), f"08  PROOF E2  {e2_block.get('status')}"),
        "objects": _text_board(
            "09  SCENE GRAPH PROPERTIES",
            [f"kinds {objects['object_kinds']}"]
            + [f"prop  {p}" for p in objects["rendering_properties"]]
            + [f"{o['id']}  {o['kind']}" for o in objects["objects"]]
            + [f"invariants {objects['invariants']}"],
            size=(1280, 1700),
        ),
        "critic": _text_board("10  MICRO-PROOF CRITIC  —  craft, not occupancy", critic_rows, size=(1280, 1700)),
        "revision": _text_board(
            "11  REVISION COMPATIBILITY  —  architectural, not executed",
            [f"{k}: {v.get('status') if isinstance(v, dict) else v}" for k, v in rev.items() if k != "schema"],
        ),
        "format": _text_board(
            "12  FORMAT COMPATIBILITY  —  not implemented",
            [f"{k}: {v}" for k, v in (fmt.get("formats") or {}).items()] + [f"status {fmt.get('status')}"],
        ),
        "review": _human_board(f"13  HUMAN REVIEW BOARD  —  {decision}", human_tiles),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_63A,
        "created_at": _now(),
        "status": status,
        "final_decision": decision,
        "renderer": SELECTED_RENDERER,
        "proof_b": PROOF_B_LOCKED,
        "aperture_calibration": aperture_cal,
        "typography_calibration": type_cal,
        "integrated_proof": d2_block,
        "brand_closure_proof": e2_block,
        "scene_graph_properties": objects,
        "micro_proof_scores": scores_pack,
        "revision_compatibility": rev,
        "format_compatibility": fmt,
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
        "next_decision": "HUMAN VISUAL REVIEW OF MICRO-PROOFS",
    }
    tests = list(blob.get("chromium_craft_63a_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["chromium_craft_63a_tests"] = tests
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
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.3A refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
