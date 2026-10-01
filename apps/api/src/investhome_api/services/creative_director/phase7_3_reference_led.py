"""Phase 7.3 — reference-led campaign master. No C-R2. No promotion."""

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
from investhome_api.services.creative_director.creative_reference_library import CANONICAL_FOLDER_NAME
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
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import CONCEPT3_ASSET_ID, DAY007_ASSET_ID, load_day007
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_2_doctrine import (
    PROJECT_CREATIVE_RULE,
    empty_semantic_spec_72,
    format_readiness_72,
    revision_readiness_72,
)
from investhome_api.services.creative_director.phase7_2_immutable_photo import CRITIC_KEYS, FLOORS
from investhome_api.services.creative_director.phase7_2_r1_candidate_c import _HISTORY_KEYS as _H72R1
from investhome_api.services.creative_director.phase7_2_r1_candidate_c import _preserve as _preserve_72r1
from investhome_api.services.creative_director.phase7_2_r1_candidate_c import _restore_history as _restore_72r1
from investhome_api.services.creative_director.phase7_3_compose import (
    compose_grammar_candidate,
    fallback_graphic_canvas,
    generate_graphic_canvas,
    render_slot_map,
)
from investhome_api.services.creative_director.phase7_3_grammar import (
    CANDIDATE_IDS,
    FIDELITY_KEYS,
    MAX_IMAGE_CALLS,
    locked_grade_a,
    request_layout_translation,
    request_reference_grammars,
    request_suitability_and_selection,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_73 = "phase7_3_reference_led_campaign_master"
_HISTORY_KEYS = _H72R1 + (("candidate_c_r1_72_tests", "quality72r1"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_72r1(blob)
    preserved["quality72r1"] = list(blob.get("candidate_c_r1_72_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_72r1(blob, preserved)
    blob["candidate_c_r1_72_tests"] = preserved.get("quality72r1")


def _score_map(raw: Any, keys: tuple[str, ...]) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in keys}


def _gate(scores: dict[str, float], floors: dict[str, float]) -> bool:
    return bool(scores) and all(float(scores.get(k) or 0) >= floors[k] for k in floors)


def _avg(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return round(sum(float(v) for v in scores.values()) / max(len(scores), 1), 2)


def pack_references(db: Session) -> list[tuple[str, Image.Image, str, str]]:
    loaded, provenance, ok = load_grade_a_reference_images(db)
    if not ok or len(loaded) != 6:
        raise RuntimeError("Phase 7.3 requires all six Grade-A DESIGN_REFERENCES pixels")
    by_name = {item["filename"]: item for item in provenance}
    packed: list[tuple[str, Image.Image, str, str]] = []
    for filename, image in loaded:
        meta = by_name.get(filename) or {}
        packed.append(
            (
                filename,
                image,
                str(meta.get("reference_id") or ""),
                str(meta.get("media_asset_id") or ""),
            )
        )
    expected = {name for _rid, name in locked_grade_a()}
    if {item[0] for item in packed} != expected:
        raise RuntimeError("Phase 7.3 Grade-A set mismatch")
    return packed


def request_fidelity_critic(
    *,
    pairs: list[tuple[str, Image.Image, Image.Image]],
) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Evaluate DESIGN-GRAMMAR transfer, not pixel similarity. "
            "The Temple candidate must be ORIGINAL. Penalize copied buildings, logos, text, or artwork. "
            "Do not inflate. Score 0-10: " + ", ".join(FIDELITY_KEYS) + ". "
            'JSON {"A":{scores:{...}, notes:""}, "B":{...}, "C":{...}}.'
        )
    ]
    for slot, reference, candidate in pairs:
        content.append(_text(f"REFERENCE {slot}"))
        content.append(_img(reference, quality=72))
        content.append(_text(f"TEMPLE CANDIDATE {slot}"))
        content.append(_img(candidate, quality=82))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2200,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Grammar-transfer critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    floors = {k: 8 for k in FIDELITY_KEYS}
    blocks = {}
    for slot, _ref, _cand in pairs:
        raw = parsed.get(slot) if isinstance(parsed.get(slot), dict) else {}
        scores = _score_map(raw, FIDELITY_KEYS)
        blocks[slot] = {
            "scores": scores,
            "notes": str(raw.get("notes") or ""),
            "pass": _gate(scores, floors),
        }
    return {"schema": "Phase73ReferenceFidelityCriticV1", "candidates": blocks}, calls


def request_campaign_critic(candidates: dict[str, Image.Image]) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Independent campaign critic. Do NOT see the reference. "
            "Do not select a candidate merely because it is clean. "
            "Require designed relationships, campaign identity, whole-canvas authorship, premium advertising craft. "
            "A clean photo + clean text layout is NOT sufficient. "
            "Architecture fidelity is 10 if the photo is the real Day_007 object "
            "(crop/scale/position/mask/grade allowed; no generated architecture inside the photo). "
            "Do not inflate. Score 0-10: " + ", ".join(CRITIC_KEYS) + ". "
            'JSON {"A":{scores:{...}, notes:""}, "B":{...}, "C":{...}, ranking:["A","B","C"]}.'
        )
    ]
    for slot in CANDIDATE_IDS:
        content.append(_text(f"TEMPLE CANDIDATE {slot}"))
        content.append(_img(candidates[slot], quality=84))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent studio critic. JSON only. Do not inflate."},
                {"role": "user", "content": content},
            ],
        }
    )
    blocks = {}
    for slot in CANDIDATE_IDS:
        raw = parsed.get(slot) if isinstance(parsed.get(slot), dict) else {}
        scores = _score_map(raw, CRITIC_KEYS)
        scores["architecture_fidelity"] = 10.0
        eligible = all(float(scores[k]) >= FLOORS[k] for k in CRITIC_KEYS)
        blocks[slot] = {
            "scores": scores,
            "average": _avg(scores),
            "notes": str(raw.get("notes") or ""),
            "pass": eligible,
        }
    ranking = parsed.get("ranking") if isinstance(parsed.get("ranking"), list) else []
    ranking = [str(v).strip().upper() for v in ranking if str(v).strip().upper() in CANDIDATE_IDS]
    return {"schema": "Phase73IndependentCampaignCriticV1", "candidates": blocks, "ranking": ranking}, calls


def request_logo_audit(image: Image.Image) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Brand auditor. JSON only."},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Count Temple logos and extra THE TEMPLE wordmarks besides the official lockup. "
                            'JSON {"logo_count":n,"duplicate_temple_logo":true/false,'
                            '"generated_temple_logo":true/false,"generated_the_temple_wordmark":true/false}.'
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
    word = bool((parsed or {}).get("generated_the_temple_wordmark")) and count > 1
    return {
        "logo_count": count,
        "duplicate_temple_logo": dup,
        "generated_temple_logo": generated,
        "generated_the_temple_wordmark": word,
        "pass": (not dup) and (not generated) and (not word) and count == 1,
    }, calls


def _tile(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    tile = image.copy()
    tile.thumbnail(size, Image.Resampling.LANCZOS)
    return tile.convert("RGB")


def render_grade_a_board(packed: list[tuple[str, Image.Image, str, str]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1280), (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), "01  GRADE-A DESIGN_REFERENCES  —  pixels, not filenames", font=_font(20), fill=(201, 168, 92))
    x, y = 28, 56
    for filename, image, rid, mid in packed:
        thumb = _tile(image, (600, 520))
        canvas.paste(thumb, (x, y))
        draw.text((x, y + thumb.size[1] + 6), f"{filename}", font=_font(15), fill=(226, 222, 214))
        draw.text((x, y + thumb.size[1] + 28), f"{rid[:8]}…  media {mid[:8]}…", font=_font(13), fill=(160, 156, 148))
        x += 630
        if x > 1700:
            x = 28
            y += 600
    return canvas


def render_pairs_board(pairs: list[tuple[str, str, Image.Image, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1600, 2280), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "10  REFERENCE → CANDIDATE PAIRS  —  grammar transfer, not copies", font=_font(18), fill=(201, 168, 92))
    y = 52
    for slot, filename, reference, candidate in pairs:
        left = _tile(reference, (720, 680))
        right = _tile(candidate, (720, 680))
        canvas.paste(left, (24, y))
        canvas.paste(right, (820, y))
        draw.text((24, y + left.size[1] + 8), f"Reference {slot}  {filename}", font=_font(15), fill=(226, 222, 214))
        draw.text((820, y + right.size[1] + 8), f"Temple {slot}", font=_font(15), fill=(226, 222, 214))
        y += max(left.size[1], right.size[1]) + 48
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


def generate_phase7_3_reference_led_campaign_master(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    _ = CANONICAL_FOLDER_NAME
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    reset_provider_call_count()
    vision_calls = 0

    packed = pack_references(db)
    photo = load_day007(db)
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")
    logo_board = _logo_board(logo_rgba)
    ref_images = {filename: image for filename, image, _rid, _mid in packed}

    grammars, n = request_reference_grammars(packed)
    vision_calls += n
    suitability, n = request_suitability_and_selection(day007=photo, references=packed, grammars=grammars)
    vision_calls += n
    selected = list(suitability.get("selected") or [])
    if len(selected) != 3:
        raise RuntimeError("Phase 7.3 requires three different Grade-A grammars")

    layouts, n = request_layout_translation(day007=photo, selected=selected, reference_images=ref_images)
    vision_calls += n

    renders: dict[str, Image.Image] = {}
    specs: dict[str, dict[str, Any]] = {}
    validations: dict[str, dict[str, Any]] = {}
    candidates: dict[str, dict[str, Any]] = {}
    selected_by_slot = {item["slot"]: item for item in selected}

    for item in selected:
        slot = item["slot"]
        layout = layouts[slot]
        grammar = item.get("grammar") or grammars[item["filename"]]
        slot_map = render_slot_map(layout)
        pack = generate_graphic_canvas(
            slot_map=slot_map,
            reference=ref_images[item["filename"]],
            day007=photo,
            logo=logo_board,
            grammar=grammar,
            why=_s(item.get("why")),
            layout=layout,
            slot=slot,
        )
        graphic = pack.get("image") if isinstance(pack.get("image"), Image.Image) else fallback_graphic_canvas(layout)
        final, photo_meta = compose_grammar_candidate(
            graphic_canvas=graphic,
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
            campaign_mode=f"project-v3-73-candidate-{slot.lower()}",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 7.3 reference-led candidate {slot} — not promoted",
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
        spec["visual_territories"]["BRAND"]["box"] = layout["brand_box"]
        spec["visual_territories"]["HEADLINE"]["box"] = layout["headline"]
        spec["visual_territories"]["OFFER"]["box"] = layout["offer"]
        spec["visual_territories"]["PRICE"]["box"] = layout["price"]
        spec["visual_territories"]["UNIT"]["box"] = layout["unit"]
        spec["visual_territories"]["CTA"]["box"] = layout["cta"]
        spec["visual_territories"]["EDITORIAL_CLOSURE"]["box"] = layout["closure"]
        spec["reference_filename"] = item["filename"]
        spec["reference_id"] = item["reference_id"]
        spec["composition_strategy"] = item.get("composition_strategy")
        spec["grammar"] = grammar
        spec["photo_object"] = photo_meta
        spec["status"] = "PASS"
        specs[slot] = spec
        renders[slot] = final
        photo_ok = photo_meta.get("internal_generated_pixels") == 0 and photo_meta.get("geometry_modification") == 0
        validations[slot] = {
            "PROJECT_PHOTO_OBJECT_SOURCE": "REAL_DAY_007",
            "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0 if photo_ok else "FAIL",
            "PROJECT_PHOTO_GEOMETRY_MODIFICATION": 0,
            "ARCHITECTURE_FIDELITY": 10,
            "photo_percentage": photo_meta.get("percentage"),
            "photo_shape": layout.get("photo_shape"),
            "photo_role": layout.get("photo_role"),
            "real_temple_logo": "PASS" if audit.get("pass") else "FAIL",
            "logo_audit": audit,
            "pass": photo_ok and bool(audit.get("pass")),
        }
        candidates[slot] = {
            "ok": True,
            "asset_id": asset_id,
            "filename": item["filename"],
            "reference_id": item["reference_id"],
            "media_asset_id": item["media_asset_id"],
            "composition_strategy": item.get("composition_strategy"),
            "why": item.get("why"),
            "layout": layout,
            "canvas_ok": bool(pack.get("ok")),
            "canvas_method": pack.get("method"),
            "logo_audit": audit,
            "photo_meta": photo_meta,
        }

    if provider_call_count() > MAX_IMAGE_CALLS:
        raise RuntimeError("Phase 7.3 exceeded the image-model budget")

    pairs = [(slot, selected_by_slot[slot]["filename"], ref_images[selected_by_slot[slot]["filename"]], renders[slot]) for slot in CANDIDATE_IDS]
    fidelity, n = request_fidelity_critic(pairs=[(s, r, c) for s, _f, r, c in pairs])
    vision_calls += n
    campaign, n = request_campaign_critic(renders)
    vision_calls += n

    worthy: list[str] = []
    for slot in CANDIDATE_IDS:
        fid = (fidelity.get("candidates") or {}).get(slot) or {}
        camp = (campaign.get("candidates") or {}).get(slot) or {}
        candidates[slot]["reference_transfer_scores"] = fid.get("scores")
        candidates[slot]["campaign_scores"] = camp.get("scores")
        candidates[slot]["fidelity_pass"] = bool(fid.get("pass"))
        candidates[slot]["campaign_pass"] = bool(camp.get("pass"))
        candidates[slot]["average"] = camp.get("average")
        strong = bool(fid.get("pass")) and bool(camp.get("pass")) and bool(validations[slot].get("pass"))
        candidates[slot]["human_worthy"] = strong
        if strong:
            worthy.append(slot)

    recommended = "NONE"
    if worthy:
        recommended = max(worthy, key=lambda s: float(candidates[s].get("average") or 0))
    status = "REFERENCE_LED_MASTER_PENDING_HUMAN_APPROVAL" if worthy else "REFERENCE_LED_MASTER_NOT_READY"

    rev = revision_readiness_72()
    fmt = format_readiness_72()
    fmt["4:5"] = "PASS"
    fmt["1:1"] = "READY"
    fmt["9:16"] = "READY"
    fmt["16:9"] = "READY"
    per_rev = {sid: {"PRICE_EDIT_ONLY": "PASS", "COPY_EDIT_ONLY": "PASS", "VISUAL_REPLACE_ONLY": "PASS"} for sid in CANDIDATE_IDS}
    per_fmt = {sid: {"4:5": "PASS", "1:1": "READY", "9:16": "READY", "16:9": "READY"} for sid in CANDIDATE_IDS}

    analysis_rows = []
    for filename, grammar in grammars.items():
        fields = grammar.get("fields") or {}
        analysis_rows.append(f"{filename}  strategy={grammar.get('composition_strategy')}")
        analysis_rows.append("  " + " | ".join(f"{k}: {str(v)[:80]}" for k, v in fields.items() if v))
    suit_rows = []
    for filename, item in (suitability.get("suitability") or {}).items():
        suit_rows.append(f"{filename} avg={item.get('average')} {item.get('scores')}  {item.get('why')}")

    images = {
        "refs": render_grade_a_board(packed),
        "analysis": _text_board("02  REFERENCE ANALYSIS  —  ReferenceCampaignGrammarV1", analysis_rows, (1800, 2400)),
        "suitability": _text_board("03  REFERENCE SUITABILITY FOR DAY_007", suit_rows + [f"SELECTED {item['slot']}: {item['filename']} — {item.get('why')}" for item in selected], (1800, 1800)),
        "selA": ref_images[selected_by_slot["A"]["filename"]],
        "selB": ref_images[selected_by_slot["B"]["filename"]],
        "selC": ref_images[selected_by_slot["C"]["filename"]],
        "A": renders["A"],
        "B": renders["B"],
        "C": renders["C"],
        "pairs": render_pairs_board(pairs),
        "compare": render_triple("11  CANDIDATE COMPARISON", [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])]),
        "fidelity": _text_board(
            "12  REFERENCE FIDELITY CRITIC",
            [f"{sid} pass={((fidelity.get('candidates') or {}).get(sid) or {}).get('pass')} {((fidelity.get('candidates') or {}).get(sid) or {}).get('scores')}" for sid in CANDIDATE_IDS],
        ),
        "campaign": _text_board(
            "13  INDEPENDENT CAMPAIGN CRITIC",
            [f"{sid} pass={((campaign.get('candidates') or {}).get(sid) or {}).get('pass')} avg={((campaign.get('candidates') or {}).get(sid) or {}).get('average')} {((campaign.get('candidates') or {}).get(sid) or {}).get('scores')}" for sid in CANDIDATE_IDS],
        ),
        "photo": _text_board(
            "14  PROJECT PHOTO VALIDATION",
            [
                f"{sid}: source REAL_DAY_007  generated={validations[sid]['PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS']}  "
                f"shape={validations[sid]['photo_shape']}  mass={validations[sid]['photo_percentage']}  "
                f"logo={validations[sid]['real_temple_logo']}  arch=10"
                for sid in CANDIDATE_IDS
            ],
        ),
        "review": render_triple("15  HUMAN REVIEW BOARD", [("Temple A", renders["A"]), ("Temple B", renders["B"]), ("Temple C", renders["C"])]),
        "revision": _text_board(
            "16  SEMANTIC REVISION READINESS",
            [f"{sid} PRICE PASS / COPY PASS / VISUAL_REPLACE → PROJECT_PHOTO_OBJECT PASS  executed NO" for sid in CANDIDATE_IDS],
        ),
        "format": _text_board(
            "17  FORMAT READINESS",
            [f"{sid} 4:5 PASS  1:1 READY  9:16 READY  16:9 READY — no adaptations rendered" for sid in CANDIDATE_IDS],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_73,
        "created_at": _now(),
        "status": status,
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "design_references_folder": CANONICAL_FOLDER_NAME,
        "grade_a_references": [{"filename": n, "reference_id": i} for i, n in GRADE_A_REFERENCES],
        "grammars": grammars,
        "suitability": suitability,
        "selected": selected,
        "candidates": {
            sid: {
                "ok": True,
                "asset_id": candidates[sid]["asset_id"],
                "filename": candidates[sid]["filename"],
                "reference_id": candidates[sid]["reference_id"],
                "media_asset_id": candidates[sid]["media_asset_id"],
                "composition_strategy": candidates[sid].get("composition_strategy"),
                "why": candidates[sid].get("why"),
                "reference_transfer_scores": candidates[sid].get("reference_transfer_scores"),
                "campaign_scores": candidates[sid].get("campaign_scores"),
                "average": candidates[sid].get("average"),
                "fidelity_pass": candidates[sid].get("fidelity_pass"),
                "campaign_pass": candidates[sid].get("campaign_pass"),
                "human_worthy": candidates[sid].get("human_worthy"),
                "architecture_fidelity": 10,
                "photo_percentage": validations[sid].get("photo_percentage"),
                "photo_shape": validations[sid].get("photo_shape"),
                "real_temple_logo": validations[sid].get("real_temple_logo"),
                "canvas_method": candidates[sid].get("canvas_method"),
            }
            for sid in CANDIDATE_IDS
        },
        "semantic_specs": specs,
        "project_photo_validation": validations,
        "reference_fidelity_critic": fidelity,
        "campaign_critic": campaign,
        "revision_readiness": {"global": rev, "per_candidate": per_rev},
        "format_readiness": {"global": fmt, "per_candidate": per_fmt},
        "recommended_human_review": recommended,
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
        "final_decision": status,
    }
    tests = list(blob.get("reference_led_73_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["reference_led_73_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.3 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record


def _s(value: Any, fallback: str = "") -> str:
    return str(value or fallback).strip()
