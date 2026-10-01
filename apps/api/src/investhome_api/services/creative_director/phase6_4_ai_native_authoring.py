"""Phase 6.4 — AI-native structured design authoring.

AI authors AICreativeSceneV2. The compiler validates and Chromium renders.
No compositor reconstruction. No Master. GPT Image = 0.
"""

from __future__ import annotations

import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw, ImageOps
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
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
    _extract_json,
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
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase6_3b_integrated_craft import _HISTORY_KEYS as _H63B
from investhome_api.services.creative_director.phase6_3b_integrated_craft import _preserve as _preserve_63b
from investhome_api.services.creative_director.phase6_4_scene_v2 import (
    OBJECT_KINDS,
    SCENE_SCHEMA,
    bind_real_assets,
    coerce_scene,
    compile_scene_html,
    format_structure,
    render_scene,
    revision_structure,
    validate_scene,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

logger = logging.getLogger(__name__)

WORKFLOW_ID_64 = "phase6_4_ai_native_structured_authoring"
ARCHITECTURE = "AI_CREATIVE_SCENE_AUTHOR → SCENE_COMPILER → CHROMIUM"
SCENE_IDS = ("A", "B", "C")
AUTHOR_TEMPERATURES = {"A": 0.75, "B": 0.88, "C": 0.95}
CRITIC_KEYS = (
    "AGENCY_CAMPAIGN_FEEL",
    "ART_DIRECTION",
    "COMPOSITION",
    "PHOTO_GRAPHIC_INTEGRATION",
    "TYPOGRAPHIC_AUTHORITY",
    "COMMERCIAL_STORYTELLING",
    "BRAND_INTEGRATION",
    "GRAPHIC_DEPTH",
    "NEGATIVE_SPACE",
    "WHOLE_CANVAS_CHARACTER",
    "PREMIUM_CHARACTER",
    "READABILITY",
    "ARCHITECTURE_FIDELITY",
    "PUBLISHABILITY",
)
FLOORS = {
    "AGENCY_CAMPAIGN_FEEL": 8,
    "ART_DIRECTION": 8,
    "COMPOSITION": 8,
    "PHOTO_GRAPHIC_INTEGRATION": 8,
    "TYPOGRAPHIC_AUTHORITY": 8,
    "COMMERCIAL_STORYTELLING": 8,
    "BRAND_INTEGRATION": 8,
    "GRAPHIC_DEPTH": 8,
    "NEGATIVE_SPACE": 8,
    "WHOLE_CANVAS_CHARACTER": 8,
    "PREMIUM_CHARACTER": 8,
    "READABILITY": 8,
    "ARCHITECTURE_FIDELITY": 9,
    "PUBLISHABILITY": 8,
}
_HISTORY_KEYS = _H63B + (("integrated_craft_63b_tests", "quality63b"),)

_AUTHOR_SYSTEM = (
    "You are AICreativeSceneAuthorV2. You author a complete structured design as AICreativeSceneV2 JSON. "
    "You are the designer. Chromium will only render what you write. "
    "Do not describe a layout. Do not choose a template. Do not give advice. Return the scene definition."
)
_AUTHOR_BRIEF = (
    "Create a sophisticated premium architectural campaign composition inspired "
    "by the approved Concept 3 art direction.\n\n"
    "Use the real project photograph as the photographic truth.\n\n"
    "The result must feel art-directed across the entire canvas, not like text "
    "placed beside a property photo."
)
_CRITIC_SYSTEM = (
    "You are a production graphic-design critic. Score each authored scene independently. "
    "Judge campaign art direction, not canvas occupancy. "
    "Do not penalize real Day_007 for not being Concept 3's invented skyline. "
    "Do not inflate. JSON only."
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_63b(blob)
    preserved["quality63b"] = list(blob.get("integrated_craft_63b_tests") or [])
    return preserved


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _logo_preview(logo_bytes: bytes) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (12, 14, 18))
    rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    if rgba is None:
        return canvas
    rgba.thumbnail((720, 720), Image.Resampling.LANCZOS)
    x = (1088 - rgba.width) // 2
    y = (1360 - rgba.height) // 2
    canvas.paste(rgba, (x, y), rgba)
    return canvas


def _empty_render(reason: str) -> Image.Image:
    return _text_board("AUTHOR RETURNED NO SCENE", [reason], size=CANVAS_4X5)


def _author_prompt() -> str:
    copy = {
        "headline": REQUIRED_FACTS["headline"],
        "discount": REQUIRED_FACTS["discount"],
        "discount_label": REQUIRED_FACTS["discount_label"],
        "price": REQUIRED_FACTS["list_price"],
        "unit": f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
        "cta": REQUIRED_FACTS["cta"],
        "editorial": APPROVED_BOTTOM_COPY,
    }
    schema = {
        "schema": "AICreativeSceneV2",
        "canvas": {"width": 1088, "height": 1360, "aspect": "4:5"},
        "objects": [
            {
                "id": "stable.id",
                "kind": "|".join(OBJECT_KINDS),
                "semantic": "project_photo|project_logo|headline|discount|discount_label|price|unit_type|cta|editorial_closure",
                "geometry": {"x": 0, "y": 0, "w": 0, "h": 0},
                "z_index": 0,
                "relationships": [],
                "render": {},
            }
        ],
        "defs": {"gradients": [], "masks": [], "filters": [], "clip_paths": []},
    }
    return (
        f"{_AUTHOR_BRIEF}\n\n"
        f"Canvas: 1088 x 1360, 4:5.\n"
        f"PHOTO asset_id: {DAY007_ASSET_ID}\n"
        f"LOGO asset_id: {LOCKED_LOGO_ASSET_ID}\n"
        f"Fonts: Cormorant Garamond, Source Sans 3.\n"
        f"Approved copy: {json.dumps(copy, ensure_ascii=False)}\n\n"
        "Author a complete scene. Every object needs a stable id, kind, semantic, geometry in pixels, "
        "z_index, relationships, and render properties. Keep JSON compact. "
        "You may use SVG paths, Bezier curves, SVG/CSS masks, clip-paths, linear and radial gradients, "
        "layered gradients, blend modes, opacity, filters, transform, letter-spacing, line-height, "
        "font variation, stroke gradients, hairlines, nested groups, overlap, and optical offsets. "
        "PHOTO must reference the real Day_007 asset. LOGO must reference the real Temple logo. "
        "TEXT must be live structured strings, not raster. "
        "Do not invent architecture. Do not generate a logo.\n\n"
        f"Return JSON matching this shape:\n{json.dumps(schema)}"
    )


def _author_vision(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    api_key = openai_api_key()
    if not api_key:
        return {}, 0
    url = f"{resolve_base_url(get_settings()).rstrip('/')}/chat/completions"
    try:
        with httpx.Client(timeout=300.0) as client:
            resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
            resp.raise_for_status()
        text = ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
        return (parsed if isinstance(parsed, dict) else {}), 1
    except Exception:
        logger.info("phase6.4 author vision failed", exc_info=True)
        return {}, 0


def author_scene(
    *,
    scene_id: str,
    concept: Image.Image,
    photo: Image.Image,
    logo: Image.Image,
) -> tuple[dict[str, Any], int]:
    parsed, calls = _author_vision(
        {
            "model": VISION_MODEL,
            "temperature": AUTHOR_TEMPERATURES[scene_id],
            "max_tokens": 8000,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _AUTHOR_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        _text(
                            f"Independent authorship for SCENE {scene_id}. "
                            "Compose freely. Return the complete AICreativeSceneV2."
                        ),
                        _text(_author_prompt()),
                        _text("Approved Concept 3 art direction:"),
                        _img(concept, quality=82),
                        _text("Real Day_007 photograph:"),
                        _img(photo, quality=82),
                        _text("Real Temple logo:"),
                        _img(logo, quality=88),
                    ],
                },
            ],
        }
    )
    scene = bind_real_assets(coerce_scene(parsed))
    scene["scene_id"] = scene_id
    scene["structure_id"] = str(uuid4())
    scene["schema"] = "AICreativeSceneV2"
    return scene, calls


def _scores(raw: Any) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in CRITIC_KEYS}


def _eligible(scores: dict[str, float]) -> tuple[bool, list[str]]:
    failed = [k for k, floor in FLOORS.items() if scores.get(k, 0) < floor]
    return (not failed), failed


def request_visual_critic(
    concept: Image.Image,
    renders: dict[str, Image.Image],
) -> tuple[dict[str, Any], int]:
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 2400,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": _CRITIC_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        _text(
                            "Score SCENE A, SCENE B, and SCENE C against Concept 3 as campaign art direction. "
                            f"Keys: {', '.join(CRITIC_KEYS)}. Integers 1-10. "
                            "Architecture fidelity is whether the real building is intact, not whether invented landmarks appear. "
                            "Do not use occupancy as quality. JSON: "
                            '{"A": {"AGENCY_CAMPAIGN_FEEL": n, ...}, "B": {...}, "C": {...}, '
                            '"ranking": ["A","B","C"], "notes": ""}'
                        ),
                        _text("Concept 3:"),
                        _img(concept, quality=80),
                        _text("Scene A:"),
                        _img(renders["A"], quality=80),
                        _text("Scene B:"),
                        _img(renders["B"], quality=80),
                        _text("Scene C:"),
                        _img(renders["C"], quality=80),
                    ],
                },
            ],
        }
    )
    blocks = {}
    for sid in SCENE_IDS:
        scores = _scores(parsed.get(sid))
        ok, failed = _eligible(scores)
        avg = round(sum(scores.values()) / max(len(scores), 1), 2)
        blocks[sid] = {
            "scores": scores,
            "failed": failed,
            "eligible": ok,
            "average": avg,
            "status": "ELIGIBLE" if ok else "NOT_ELIGIBLE",
        }
    return {
        "schema": "Phase64VisualCriticV1",
        "scenes": blocks,
        "ranking": parsed.get("ranking") or [],
        "notes": str(parsed.get("notes") or parsed.get("diagnosis") or ""),
        "vision_model": VISION_MODEL,
    }, calls


def _pick_best(blocks: dict[str, dict[str, Any]]) -> str:
    def rank(sid: str) -> tuple[int, float, float]:
        block = blocks[sid]
        scores = block.get("scores") or {}
        mn = min((float(v) for v in scores.values()), default=0.0)
        return (1 if block.get("eligible") else 0, mn, float(block.get("average") or 0))

    return max(SCENE_IDS, key=rank)


def _quad(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (2200, 1180), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    slot_w, slot_h = 510, 980
    x = 28
    for label, image in tiles[:4]:
        tile = image.copy()
        tile.thumbnail((slot_w, slot_h), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 1050), label[:42], font=_font(16), fill=(226, 222, 214))
        x += slot_w + 24
    return canvas


def generate_phase6_4_ai_native_authoring(
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

    concept = load_approved_concept3(db)
    if concept.size != CANVAS_4X5:
        concept = ImageOps.fit(concept, CANVAS_4X5, method=Image.Resampling.LANCZOS)
    source = load_day007(db)
    photo_preview, _ = cover_fit_canvas(source, CANVAS_4X5, centering=(0.68, 0.20))
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    logo_preview = _logo_preview(logo_bytes)
    fonts = build_font_registry()
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(logo_bytes)
    photo_for_render = source.convert("RGB")
    photo_for_render.thumbnail((2400, 2400), Image.Resampling.LANCZOS)
    photo_uri = _jpeg_data_uri(photo_for_render, quality=92)
    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.4 forbids GPT Image production calls")

    scenes: dict[str, dict[str, Any]] = {}
    htmls: dict[str, str] = {}
    renders: dict[str, Image.Image] = {}
    validations: dict[str, dict[str, Any]] = {}
    assets: dict[str, str] = {}

    for sid in SCENE_IDS:
        scene, n = author_scene(scene_id=sid, concept=concept, photo=photo_preview, logo=logo_preview)
        vision_calls += n
        scenes[sid] = scene
        objects = scene.get("objects") or []
        if not objects:
            htmls[sid] = ""
            renders[sid] = _empty_render(f"Scene {sid} had no objects. Compiler did not reconstruct.")
            validations[sid] = validate_scene(scene, "")
            validations[sid]["status"] = "FAIL"
            validations[sid]["pass"] = False
            continue
        html = compile_scene_html(scene, photo_uri=photo_uri, logo_markup=logo_markup, font_css=font_css)
        html2 = compile_scene_html(scene, photo_uri=photo_uri, logo_markup=logo_markup, font_css=font_css)
        htmls[sid] = html
        try:
            renders[sid] = render_scene(scene, photo_uri=photo_uri, logo_markup=logo_markup, font_css=font_css)
        except Exception as exc:
            renders[sid] = _empty_render(f"Scene {sid} render failed: {exc}")
        validation = validate_scene(scene, html)
        validation["checks"]["re_render_deterministic"] = html == html2
        if html != html2:
            validation["failed"] = list(validation.get("failed") or []) + ["re_render_deterministic"]
            validation["pass"] = False
            validation["status"] = "FAIL"
        validations[sid] = validation

    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.4 forbids GPT Image production calls")

    critic, n = request_visual_critic(concept, renders)
    vision_calls += n
    for sid in SCENE_IDS:
        critic["scenes"][sid]["structural"] = validations[sid].get("status")
        stored = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(renders[sid]),
            content_type="image/png",
            campaign_mode=f"project-v3-64-scene-{sid.lower()}",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 6.4 AI-authored scene {sid} — not a Master",
        )
        assets[sid] = str(stored.id)
        scenes[sid]["asset_id"] = assets[sid]

    if provider_call_count() != 0:
        raise RuntimeError("Phase 6.4 forbids GPT Image production calls")

    best = _pick_best(critic["scenes"])
    best_eligible = bool(critic["scenes"][best].get("eligible"))
    decision = "AI_NATIVE_STRUCTURED_AUTHORING_READY" if best_eligible else "AI_NATIVE_STRUCTURED_AUTHORING_NOT_READY"
    rev = revision_structure(scenes[best])
    fmt = format_structure(scenes[best])
    day_status = "PASS" if all(validations[s]["checks"].get("real_day007") for s in SCENE_IDS) else "FAIL"
    logo_status = "PASS" if all(validations[s]["checks"].get("real_temple_logo") for s in SCENE_IDS) else "FAIL"

    tiles = [
        ("CONCEPT 3", concept),
        ("SCENE A", renders["A"]),
        ("SCENE B", renders["B"]),
        ("SCENE C", renders["C"]),
    ]
    images = {
        "concept": concept.convert("RGB"),
        "day007": photo_preview.convert("RGB"),
        "logo": logo_preview.convert("RGB"),
        "A": renders["A"],
        "B": renders["B"],
        "C": renders["C"],
        "compare": _quad("07  SCENE COMPARISON", tiles),
        "critic": _text_board(
            "08  VISUAL CRITIC",
            [
                f"SCENE {sid}: {critic['scenes'][sid]['status']}  avg {critic['scenes'][sid]['average']}  "
                + "  ".join(f"{k}={v}" for k, v in (critic["scenes"][sid]["scores"] or {}).items())
                for sid in SCENE_IDS
            ]
            + [f"notes {critic.get('notes')}", f"ranking {critic.get('ranking')}"],
            size=(1600, 2100),
        ),
        "review": _quad("09  HUMAN REVIEW BOARD", tiles),
        "best_structure": _text_board(
            f"10  BEST SCENE {best} STRUCTURE",
            [
                f"structure_id {scenes[best].get('structure_id')}",
                f"asset_id {assets[best]}",
                *[
                    f"{o.get('id')}  {o.get('kind')}  {o.get('semantic')}  z={o.get('z_index')}  {o.get('geometry')}"
                    for o in (scenes[best].get("objects") or [])[:40]
                ],
            ],
        ),
        "revision": _text_board(
            "11  REVISION STRUCTURE CHECK  —  not rendered",
            [
                f"PRICE_EDIT_ONLY {(rev.get('PRICE_EDIT_ONLY') or {}).get('status')} ids={(rev.get('PRICE_EDIT_ONLY') or {}).get('object_ids')}",
                f"COPY_EDIT_ONLY {(rev.get('COPY_EDIT_ONLY') or {}).get('status')} ids={(rev.get('COPY_EDIT_ONLY') or {}).get('object_ids')}",
                f"VISUAL_REPLACE_ONLY {(rev.get('VISUAL_REPLACE_ONLY') or {}).get('status')} ids={(rev.get('VISUAL_REPLACE_ONLY') or {}).get('object_ids')}",
            ],
        ),
        "format": _text_board(
            "12  FORMAT STRUCTURE CHECK  —  not rendered",
            [f"status {fmt.get('status')}", str(fmt.get("reason") or "")]
            + [f"{k}: {v}" for k, v in (fmt.get("formats") or {}).items()],
        ),
        "architecture": _text_board(
            "13  ARCHITECTURE DECISION",
            [
                ARCHITECTURE,
                "AI authors the structured scene. Chromium only renders.",
                "GraphicDesignCompositorV4 is not the creative renderer.",
                "No aperture calibration. No pixel matching. No V5.",
                f"FINAL DECISION {decision}",
                "NEW APPROVED MASTER NO",
                "PROMOTED NO",
            ],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_64,
        "created_at": _now(),
        "status": decision,
        "final_decision": decision,
        "architecture": ARCHITECTURE,
        "scenes": {
            sid: {
                "structure_id": scenes[sid].get("structure_id"),
                "asset_id": assets[sid],
                "scores": critic["scenes"][sid]["scores"],
                "eligible": critic["scenes"][sid]["eligible"],
                "structural": validations[sid].get("status"),
                "average": critic["scenes"][sid]["average"],
            }
            for sid in SCENE_IDS
        },
        "visual_critic": critic,
        "validations": validations,
        "best_scene": best,
        "best_scene_asset_id": assets[best],
        "best_scene_structure_id": scenes[best].get("structure_id"),
        "revision_structure_check": rev,
        "format_structure_check": fmt,
        "real_day007": day_status,
        "real_temple_logo": logo_status,
        "generated_architecture": 0,
        "generated_logo": 0,
        "generated_text_raster": 0,
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
    tests = list(blob.get("ai_native_authoring_64_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["ai_native_authoring_64_tests"] = tests
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
    blob["integrated_craft_63b_tests"] = preserved.get("quality63b")
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.4 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["scene_payloads"] = scenes
    record["schema"] = SCENE_SCHEMA
    record["identity"] = {"before": before, "after": after}
    return record
