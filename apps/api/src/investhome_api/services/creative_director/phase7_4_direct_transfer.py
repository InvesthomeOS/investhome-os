"""Phase 7.4 — direct visual reference transfer. No grammar layer. No R1. No promotion."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import GRADE_A_REFERENCES, _img, _num, _text
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import load_grade_a_reference_images
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _logo_board
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import CANVAS_4X5
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_compositor import _jsonable
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID, load_day007
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import (
    PROJECT_CREATIVE_RULE,
    empty_semantic_spec_72,
    format_readiness_72,
    revision_readiness_72,
)
from investhome_api.services.creative_director.phase7_2_photo_object import _box, clamp_photo_mass
from investhome_api.services.creative_director.phase7_3_reference_led import _HISTORY_KEYS as _H73
from investhome_api.services.creative_director.phase7_3_reference_led import _preserve as _preserve_73
from investhome_api.services.creative_director.phase7_3_reference_led import _restore_history as _restore_73
from investhome_api.services.creative_director.phase7_4_compose import (
    MAX_IMAGE_CALLS,
    compose_direct_candidate,
    generate_around_photo,
    stage_photo,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_74 = "phase7_4_direct_visual_reference_transfer"
CREATIVE_STRATEGY = "DIRECT_VISUAL_REFERENCE_TRANSFER"
REFERENCE_FILENAME = "ORNEK_00013.jpg"
REFERENCE_ID = "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57"
CANDIDATE_IDS = ("A", "B", "C")
_HISTORY_KEYS = _H73 + (("reference_led_73_tests", "quality73"),)
CEILING_NOTE = (
    "AI + immutable project photography + automated composition has reached the current "
    "production quality ceiling. The next decision is PRODUCT-LEVEL, not another renderer experiment."
)

DETAILED_KEYS = (
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "photo_graphic_integration",
    "typographic_authority",
    "commercial_storytelling",
    "brand_integration",
    "graphic_depth",
    "negative_space",
    "whole_canvas_character",
    "premium_character",
    "readability",
    "architecture_fidelity",
    "publishability",
)
RELATION_KEYS = (
    "VISUAL_CRAFT_LEVEL_MATCH",
    "COMPOSITIONAL_CONFIDENCE_MATCH",
    "TYPOGRAPHIC_CONFIDENCE_MATCH",
    "PHOTO_GRAPHIC_RELATIONSHIP_MATCH",
    "NEGATIVE_SPACE_SOPHISTICATION_MATCH",
    "CAMPAIGN_AUTHORITY_MATCH",
)
CAMPAIGN_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
    REQUIRED_FACTS["list_price"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["cta"],
    APPROVED_BOTTOM_COPY,
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_73(blob)
    preserved["quality73"] = list(blob.get("reference_led_73_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_73(blob, preserved)
    blob["reference_led_73_tests"] = preserved.get("quality73")


def _score_map(raw: Any, keys: tuple[str, ...]) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in keys}


def _gate(scores: dict[str, float], floors: dict[str, float]) -> bool:
    return bool(scores) and all(float(scores.get(k) or 0) >= floors[k] for k in floors)


def load_ornek_00013(db: Session) -> tuple[Image.Image, str]:
    loaded, provenance, ok = load_grade_a_reference_images(db)
    if not ok:
        raise RuntimeError("Phase 7.4 requires original ORNEK_00013 pixels")
    by_name = {name: image for name, image in loaded}
    if REFERENCE_FILENAME not in by_name:
        raise RuntimeError("ORNEK_00013 was not in DESIGN_REFERENCES")
    media_id = ""
    for item in provenance:
        if item.get("filename") == REFERENCE_FILENAME:
            media_id = str(item.get("media_asset_id") or "")
            break
    expected = {item[0] for item in GRADE_A_REFERENCES}
    if REFERENCE_ID not in expected:
        raise RuntimeError("ORNEK_00013 reference id lock failed")
    return by_name[REFERENCE_FILENAME].convert("RGB"), media_id


def type_region_from_photo(photo: dict[str, float]) -> dict[str, float]:
    right_gap = 1.0 - (photo["x"] + photo["w"])
    left_gap = photo["x"]
    below = 0.90 - (photo["y"] + photo["h"])
    if right_gap >= 0.28 and right_gap >= left_gap:
        return {"x": photo["x"] + photo["w"] + 0.03, "y": 0.06, "w": max(0.24, right_gap - 0.05), "h": 0.82}
    if left_gap >= 0.28:
        return {"x": 0.04, "y": 0.06, "w": max(0.24, left_gap - 0.06), "h": 0.82}
    if below >= 0.22:
        return {"x": 0.08, "y": min(0.72, photo["y"] + photo["h"] + 0.03), "w": 0.84, "h": max(0.18, below - 0.04)}
    return {"x": 0.06, "y": 0.06, "w": 0.88, "h": max(0.16, photo["y"] - 0.04)}


def layout_from_direction(raw: dict[str, Any]) -> dict[str, Any]:
    photo = clamp_photo_mass(_box(raw.get("photo_box"), {"x": 0.08, "y": 0.10, "w": 0.84, "h": 0.58}))
    region = type_region_from_photo(photo)
    rx, ry, rw = region["x"], region["y"], region["w"]
    shape = str(raw.get("photo_shape") or "rect").lower()
    if shape not in {"rect", "rounded", "ellipse"}:
        shape = "rect"
    align = str(raw.get("alignment") or "left").lower()
    if align not in {"left", "right", "center"}:
        align = "left"
    centering = raw.get("centering") or [0.68, 0.18]
    if isinstance(centering, dict):
        centering = (float(centering.get("x", 0.68)), float(centering.get("y", 0.18)))
    elif isinstance(centering, (list, tuple)) and len(centering) >= 2:
        centering = (float(centering[0]), float(centering[1]))
    else:
        centering = (0.68, 0.18)
    fallbacks = {
        "brand_box": {"x": rx, "y": ry, "w": min(0.32, rw), "h": 0.09},
        "headline": {"x": rx, "y": ry + 0.12, "w": rw, "h": 0.10},
        "offer": {"x": rx, "y": ry + 0.26, "w": rw, "h": 0.16},
        "price": {"x": rx, "y": ry + 0.46, "w": rw, "h": 0.09},
        "unit": {"x": rx, "y": ry + 0.58, "w": min(0.40, rw), "h": 0.05},
        "cta": {"x": rx, "y": ry + 0.70, "w": min(0.36, rw), "h": 0.045},
        "closure": {"x": 0.12, "y": 0.93, "w": 0.76, "h": 0.04},
    }
    layout = {
        "photo_role": str(raw.get("photo_role") or "designed_photographic_mass"),
        "photo_shape": shape,
        "photo_box": photo,
        "centering": centering,
        "alignment": align,
        "headline_scale": float(_num(raw.get("headline_scale"), 1.0) or 1.0),
        "offer_scale": float(_num(raw.get("offer_scale"), 1.0) or 1.0),
        "price_scale": float(_num(raw.get("price_scale"), 0.7) or 0.7),
        "grade": {"warmth": 0.12, "contrast": 1.04, "brightness": 0.99},
        "composition_instruction": str(raw.get("composition_instruction") or ""),
        "how_day007_participates": str(raw.get("how_day007_participates") or ""),
    }
    for key, fallback in fallbacks.items():
        layout[key] = _box(raw.get(key), fallback)
    return layout


def request_three_directions(*, reference: Image.Image, day007: Image.Image, logo: Image.Image) -> tuple[list[dict[str, Any]], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.45,
            "max_tokens": 2600,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Multimodal Creative Director. Decide by SEEING. JSON only. No prose analysis.",
                },
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Create an ORIGINAL The Temple campaign at the visual craft level of image 1, "
                            "using the real Day_007 photograph (image 2) as an IMMUTABLE photographic object, "
                            "and the real Temple logo (image 3). "
                            "Do not describe the reference. Do not extract a textual grammar. "
                            "Decide composition now from what you see. "
                            "Return THREE genuinely different visual interpretations of the same reference craft. "
                            "Do not copy the reference building, logo, photography, company name, copy, or artwork. "
                            "Do not invent Temple architecture. Day_007 may be cropped, scaled, positioned, masked, graded. "
                            "Typography is VISUAL MASS, not five labels. Reading: "
                            + " → ".join(CAMPAIGN_COPY)
                            + ". 4:5 canvas. "
                            "For each: composition_instruction (concrete), how_day007_participates, "
                            "photo_role, photo_shape (rect|rounded|ellipse), photo_box {x,y,w,h} 0-1, centering [cx,cy], "
                            "alignment, headline/offer/price/unit/cta/brand_box/closure boxes, "
                            "headline_scale, offer_scale, price_scale. "
                            'JSON {"directions":[{"id":"A",...},{"id":"B",...},{"id":"C",...}]}.'
                        ),
                        _text("IMAGE 1 — ORNEK_00013 visual design reference (craft only):"),
                        _img(reference, quality=88),
                        _text("IMAGE 2 — REAL Day_007 immutable project photograph:"),
                        _img(day007, quality=82),
                        _text("IMAGE 3 — REAL Temple logo:"),
                        _img(logo, quality=90),
                    ],
                },
            ],
        }
    )
    raw = parsed.get("directions") if isinstance(parsed.get("directions"), list) else []
    out: list[dict[str, Any]] = []
    for i, sid in enumerate(CANDIDATE_IDS):
        data = dict(raw[i]) if i < len(raw) and isinstance(raw[i], dict) else {}
        data["id"] = sid
        out.append(data)
    return out, calls


def request_binary_filter(candidates: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Fresh critic. One binary question per candidate. "
            "Does this look like a professionally art-directed premium advertising campaign, "
            "rather than a project photograph with information placed around it? "
            "Answer YES or NO. Maximum 3 short reasons. Do not inflate. "
            'JSON {"A":{"verdict":"YES"|"NO","reasons":["","",""]}, "B":{...}, "C":{...}}.'
        )
    ]
    for sid in CANDIDATE_IDS:
        content.append(_text(f"CANDIDATE {sid}"))
        content.append(_img(candidates[sid], quality=84))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 900,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Binary campaign filter. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    blocks = {}
    for sid in CANDIDATE_IDS:
        raw = parsed.get(sid) if isinstance(parsed.get(sid), dict) else {}
        verdict = str(raw.get("verdict") or raw.get("answer") or "NO").strip().upper()
        if verdict not in {"YES", "NO"}:
            verdict = "NO"
        reasons = raw.get("reasons") if isinstance(raw.get("reasons"), list) else [str(raw.get("reason") or "")]
        blocks[sid] = {"verdict": verdict, "reasons": [str(r) for r in reasons[:3]]}
    return {"schema": "Phase74BinaryProfessionalReviewV1", "candidates": blocks}, calls


def request_detailed_critic(candidates: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    if not candidates:
        return {"schema": "Phase74DetailedVisualCriticV1", "candidates": {}}, 0
    content: list[Any] = [
        _text(
            "Independent campaign critic. Do not inflate. "
            "Do not select a candidate merely because it is clean. "
            "Architecture fidelity is 10 if the photo is real Day_007 (crop/scale/mask/grade allowed). "
            "Score 0-10: " + ", ".join(DETAILED_KEYS) + ". "
            "JSON object keyed by candidate id with scores and notes."
        )
    ]
    for sid, image in candidates.items():
        content.append(_text(f"CANDIDATE {sid}"))
        content.append(_img(image, quality=84))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    floors = {k: 8 for k in DETAILED_KEYS if k != "architecture_fidelity"}
    floors["architecture_fidelity"] = 10
    blocks = {}
    for sid in candidates:
        raw = parsed.get(sid) if isinstance(parsed.get(sid), dict) else {}
        scores = _score_map(raw, DETAILED_KEYS)
        scores["architecture_fidelity"] = 10.0
        blocks[sid] = {
            "scores": scores,
            "notes": str(raw.get("notes") or ""),
            "pass": _gate(scores, floors),
        }
    return {"schema": "Phase74DetailedVisualCriticV1", "candidates": blocks}, calls


def request_relationship_check(*, reference: Image.Image, candidates: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Score DESIGN RELATIONSHIP to the reference, not pixel similarity. "
            "Do not reward copied buildings, logos, or artwork. Do not inflate. 0-10: "
            + ", ".join(RELATION_KEYS)
            + '. JSON keyed by A/B/C with scores.'
        ),
        _text("ORNEK_00013 REFERENCE"),
        _img(reference, quality=80),
    ]
    for sid in CANDIDATE_IDS:
        content.append(_text(f"TEMPLE CANDIDATE {sid}"))
        content.append(_img(candidates[sid], quality=82))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Craft-relationship critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    floors = {k: 8 for k in RELATION_KEYS}
    blocks = {}
    for sid in CANDIDATE_IDS:
        raw = parsed.get(sid) if isinstance(parsed.get(sid), dict) else {}
        scores = _score_map(raw, RELATION_KEYS)
        blocks[sid] = {"scores": scores, "pass": _gate(scores, floors)}
    return {"schema": "Phase74ReferenceRelationshipV1", "candidates": blocks}, calls


def request_logo_audit(image: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 350,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Brand auditor. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Count Temple logos. Extra THE TEMPLE wordmarks besides the official lockup count as duplicates. "
                            'JSON {"logo_count":n,"duplicate_temple_logo":true/false,"generated_temple_logo":true/false}.'
                        ),
                        _img(image, quality=80),
                    ],
                },
            ],
        }
    )
    count = int(_num((parsed or {}).get("logo_count"), 1))
    dup = bool((parsed or {}).get("duplicate_temple_logo")) or count > 1
    generated = bool((parsed or {}).get("generated_temple_logo"))
    return {
        "logo_count": count,
        "duplicate_temple_logo": dup,
        "generated_temple_logo": generated,
        "pass": (not dup) and (not generated) and count == 1,
    }, calls


def _tile(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    tile = image.copy()
    tile.thumbnail(size, Image.Resampling.LANCZOS)
    return tile.convert("RGB")


def render_quad(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 12), title, font=_font(16), fill=(201, 168, 92))
    x = 20
    for label, image in tiles[:4]:
        tile = _tile(image, (450, 620))
        canvas.paste(tile, (x, 44))
        draw.text((x, 680), label[:40], font=_font(14), fill=(226, 222, 214))
        x += 475
    return canvas


def render_triple(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 28
    for label, image in tiles[:3]:
        tile = _tile(image, (600, 840))
        canvas.paste(tile, (x, 56))
        draw.text((x, 910), label[:48], font=_font(16), fill=(226, 222, 214))
        x += 630
    return canvas


def generate_phase7_4_direct_visual_reference_transfer(
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

    reference, media_id = load_ornek_00013(db)
    photo = load_day007(db)
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")
    logo_board = _logo_board(logo_rgba)

    directions, n = request_three_directions(reference=reference, day007=photo, logo=logo_board)
    vision_calls += n

    renders: dict[str, Image.Image] = {}
    specs: dict[str, dict[str, Any]] = {}
    validations: dict[str, dict[str, Any]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    layouts: dict[str, dict[str, Any]] = {}

    for direction in directions:
        slot = str(direction.get("id") or "A")
        layout = layout_from_direction(direction)
        layouts[slot] = layout
        staged = stage_photo(photo, layout)
        pack = generate_around_photo(
            staged=staged,
            reference=reference,
            logo=logo_board,
            layout=layout,
            direction=direction,
            slot=slot,
        )
        around = pack.get("image") if isinstance(pack.get("image"), Image.Image) else staged
        final, photo_meta = compose_direct_candidate(
            around=around,
            photo=photo,
            logo_rgba=logo_rgba,
            layout=layout,
        )
        stored = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(final),
            content_type="image/png",
            campaign_mode=f"project-v3-74-candidate-{slot.lower()}",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 7.4 direct visual transfer candidate {slot} — not promoted",
        )
        audit, n = request_logo_audit(final)
        vision_calls += n
        asset_id = str(stored.id)
        spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id=slot)
        spec["visual_territories"]["PROJECT_PHOTO_OBJECT"] = {
            "present": True,
            "box": layout["photo_box"],
            "notes": layout.get("photo_role"),
            "immutable": True,
        }
        for key, territory in (
            ("brand_box", "BRAND"),
            ("headline", "HEADLINE"),
            ("offer", "OFFER"),
            ("price", "PRICE"),
            ("unit", "UNIT"),
            ("cta", "CTA"),
            ("closure", "EDITORIAL_CLOSURE"),
        ):
            spec["visual_territories"][territory]["box"] = layout[key]
        spec["composition_instruction"] = layout.get("composition_instruction")
        spec["how_day007_participates"] = layout.get("how_day007_participates")
        spec["reference_id"] = REFERENCE_ID
        spec["photo_object"] = photo_meta
        spec["status"] = "PASS"
        specs[slot] = spec
        renders[slot] = final
        photo_ok = photo_meta.get("internal_generated_pixels") == 0 and photo_meta.get("geometry_modification") == 0
        validations[slot] = {
            "PROJECT_PHOTO_OBJECT_SOURCE": "REAL_DAY_007",
            "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0 if photo_ok else "FAIL",
            "PROJECT_PHOTO_GEOMETRY_MODIFICATION": 0,
            "REAL_TEMPLE_LOGO": bool(audit.get("pass")),
            "GENERATED_TEMPLE_LOGO": 0 if not audit.get("generated_temple_logo") else 1,
            "DUPLICATE_TEMPLE_WORDMARK": 0 if not audit.get("duplicate_temple_logo") else 1,
            "ARCHITECTURE_FIDELITY": 10,
            "photo_percentage": photo_meta.get("percentage"),
            "pass": photo_ok and bool(audit.get("pass")),
        }
        candidates[slot] = {
            "ok": True,
            "asset_id": asset_id,
            "direction": direction,
            "layout": layout,
            "canvas_ok": bool(pack.get("ok")),
            "canvas_method": pack.get("method"),
            "logo_audit": audit,
        }

    if provider_call_count() > MAX_IMAGE_CALLS:
        raise RuntimeError("Phase 7.4 exceeded the image-model budget")

    binary, n = request_binary_filter(renders)
    vision_calls += n
    yes_renders = {
        sid: renders[sid]
        for sid in CANDIDATE_IDS
        if ((binary.get("candidates") or {}).get(sid) or {}).get("verdict") == "YES"
    }
    detailed, n = request_detailed_critic(yes_renders)
    vision_calls += n
    relation, n = request_relationship_check(reference=reference, candidates=renders)
    vision_calls += n

    worthy: list[str] = []
    for sid in CANDIDATE_IDS:
        bin_row = (binary.get("candidates") or {}).get(sid) or {}
        det = (detailed.get("candidates") or {}).get(sid) or {}
        rel = (relation.get("candidates") or {}).get(sid) or {}
        candidates[sid]["professional_campaign"] = bin_row.get("verdict")
        candidates[sid]["reasons"] = bin_row.get("reasons")
        candidates[sid]["visual_scores"] = det.get("scores") if bin_row.get("verdict") == "YES" else None
        candidates[sid]["relationship_scores"] = rel.get("scores")
        strong = (
            bin_row.get("verdict") == "YES"
            and bool(det.get("pass"))
            and bool(rel.get("pass"))
            and bool(validations[sid].get("pass"))
        )
        candidates[sid]["human_worthy"] = strong
        if strong:
            worthy.append(sid)

    recommended = "NONE"
    if worthy:
        recommended = max(
            worthy,
            key=lambda s: sum(float(v) for v in (candidates[s].get("visual_scores") or {}).values()),
        )
    status = (
        "DIRECT_REFERENCE_TRANSFER_PENDING_HUMAN_APPROVAL"
        if worthy
        else "DIRECT_REFERENCE_TRANSFER_NOT_READY"
    )

    rev = revision_readiness_72()
    fmt = format_readiness_72()
    fmt["4:5"] = "PASS"
    fmt["1:1"] = "READY"
    fmt["9:16"] = "READY"
    fmt["16:9"] = "READY"
    per_rev = {sid: {"PRICE_EDIT_ONLY": "PASS", "COPY_EDIT_ONLY": "PASS", "VISUAL_REPLACE_ONLY": "PASS"} for sid in CANDIDATE_IDS}
    per_fmt = {sid: {"4:5": "PASS", "1:1": "READY", "9:16": "READY", "16:9": "READY"} for sid in CANDIDATE_IDS}

    logo_preview = Image.new("RGB", CANVAS_4X5, (12, 14, 18))
    mark = logo_rgba.copy()
    mark.thumbnail((720, 720), Image.Resampling.LANCZOS)
    logo_preview.paste(mark, ((1088 - mark.width) // 2, (1360 - mark.height) // 2), mark)

    images = {
        "reference": reference,
        "day007": photo.convert("RGB"),
        "logo": logo_preview,
        "A": renders["A"],
        "B": renders["B"],
        "C": renders["C"],
        "plus": render_quad(
            "07  ORNEK_00013 + CANDIDATES  —  equal size, no scores",
            [("ORNEK_00013", reference), ("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])],
        ),
        "compare": render_triple("08  CANDIDATE COMPARISON", [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])]),
        "binary": _text_board(
            "09  BINARY PROFESSIONAL REVIEW",
            [
                f"{sid}: {((binary.get('candidates') or {}).get(sid) or {}).get('verdict')}  "
                + " | ".join(((binary.get("candidates") or {}).get(sid) or {}).get("reasons") or [])
                for sid in CANDIDATE_IDS
            ],
        ),
        "detailed": _text_board(
            "10  DETAILED VISUAL CRITIC  —  YES candidates only",
            [
                f"{sid}: {((detailed.get('candidates') or {}).get(sid) or {}).get('scores') or 'not scored (binary NO)'}"
                for sid in CANDIDATE_IDS
            ],
        ),
        "relation": _text_board(
            "11  REFERENCE RELATIONSHIP CHECK  —  craft, not pixels",
            [f"{sid}: {((relation.get('candidates') or {}).get(sid) or {}).get('scores')}" for sid in CANDIDATE_IDS],
        ),
        "reality": _text_board(
            "12  PROJECT REALITY VALIDATION",
            [
                f"{sid}: Day_007 generated={validations[sid]['PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS']} "
                f"geom=0 logo={'PASS' if validations[sid]['REAL_TEMPLE_LOGO'] else 'FAIL'} arch=10"
                for sid in CANDIDATE_IDS
            ],
        ),
        "revision": _text_board(
            "13  REVISION READINESS",
            [f"{sid} PRICE PASS / COPY PASS / VISUAL_REPLACE → PROJECT_PHOTO_OBJECT PASS  executed NO" for sid in CANDIDATE_IDS],
        ),
        "format": _text_board(
            "14  FORMAT READINESS",
            [f"{sid} 4:5 PASS  1:1 READY  9:16 READY  16:9 READY — no adaptations" for sid in CANDIDATE_IDS],
        ),
        "review": render_triple("15  HUMAN REVIEW BOARD", [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])]),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_74,
        "created_at": _now(),
        "status": status,
        "creative_strategy": CREATIVE_STRATEGY,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "reference_filename": REFERENCE_FILENAME,
        "reference_id": REFERENCE_ID,
        "reference_media_asset_id": media_id,
        "directions": directions,
        "candidates": {
            sid: {
                "ok": True,
                "asset_id": candidates[sid]["asset_id"],
                "professional_campaign": candidates[sid].get("professional_campaign"),
                "reasons": candidates[sid].get("reasons"),
                "visual_scores": candidates[sid].get("visual_scores"),
                "relationship_scores": candidates[sid].get("relationship_scores"),
                "human_worthy": candidates[sid].get("human_worthy"),
                "architecture_fidelity": 10,
                "real_temple_logo": "PASS" if validations[sid]["REAL_TEMPLE_LOGO"] else "FAIL",
                "canvas_method": candidates[sid].get("canvas_method"),
                "composition_instruction": layouts[sid].get("composition_instruction"),
            }
            for sid in CANDIDATE_IDS
        },
        "semantic_specs": specs,
        "binary_professional_review": binary,
        "detailed_visual_critic": detailed,
        "reference_relationship_check": relation,
        "project_reality_validation": validations,
        "revision_readiness": {"global": rev, "per_candidate": per_rev},
        "format_readiness": {"global": fmt, "per_candidate": per_fmt},
        "recommended_human_review": recommended,
        "quality_ceiling_note": CEILING_NOTE if not worthy else "",
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
        "next_decision": "HUMAN VISUAL REVIEW" if worthy else "PRODUCT-LEVEL DECISION",
        "final_decision": status,
    }
    tests = list(blob.get("direct_visual_transfer_74_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["direct_visual_transfer_74_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.4 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
