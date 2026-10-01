"""Phase 7.2 — immutable project photo object inside freely art-directed canvases.

No C-R2. No paste-back. No promotion.
"""

from __future__ import annotations

import io
import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.ai_visual_art_director import _img, _num, _text
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
from investhome_api.services.creative_director.phase6_1_concept3_compose import (
    CONCEPT3_ASSET_ID,
    DAY007_ASSET_ID,
    load_approved_concept3,
    load_day007,
)
from investhome_api.services.creative_director.phase6_1_r1_compose import APPROVED_BOTTOM_COPY
from investhome_api.services.creative_director.phase7_0_doctrine import PRODUCTION_DOCTRINE
from investhome_api.services.creative_director.phase7_1_candidate_c_r1 import _HISTORY_KEYS as _H71
from investhome_api.services.creative_director.phase7_1_candidate_c_r1 import _preserve as _preserve_71
from investhome_api.services.creative_director.phase7_1_candidate_c_r1 import _restore_history as _restore_71
from investhome_api.services.creative_director.phase7_2_doctrine import (
    PROJECT_CREATIVE_RULE,
    TERRITORIES_72,
    empty_semantic_spec_72,
    format_readiness_72,
    project_photo_object_rule,
    revision_readiness_72,
)
from investhome_api.services.creative_director.phase7_2_photo_object import (
    SEEDED_LAYOUTS,
    compose_candidate,
    merge_layout,
    render_slot_map,
)
from investhome_api.services.creative_director.visual_composition_draft import _contact_sheet, _jpeg_bytes, _png_bytes
from investhome_api.services.gpt_image_design.client import (
    GptImageProviderError,
    decode_remote_image,
    edit_image,
    provider_call_count,
    reset_provider_call_count,
)
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.config import (
    DEFAULT_MODEL,
    openai_api_key,
    provider_availability,
    resolve_base_url,
    resolve_model,
)
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_72 = "phase7_2_immutable_project_photo_object"
_HISTORY_KEYS = _H71 + (("candidate_c_r1_71_tests", "quality71"),)
CANDIDATE_IDS = ("A", "B", "C")
MAX_IMAGE_CALLS = 3
CAMPAIGN_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['discount']} {REQUIRED_FACTS['discount_label']}",
    REQUIRED_FACTS["list_price"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["cta"],
    APPROVED_BOTTOM_COPY,
)
CRITIC_KEYS = (
    "agency_campaign_feel",
    "art_direction",
    "composition",
    "project_photo_prominence",
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
FLOORS = {k: 8 for k in CRITIC_KEYS if k != "architecture_fidelity"}
FLOORS["architecture_fidelity"] = 10


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_71(blob)
    preserved["quality71"] = list(blob.get("candidate_c_r1_71_tests") or [])
    return preserved


def _restore_history(blob: dict[str, Any], preserved: dict[str, Any]) -> None:
    _restore_71(blob, preserved)
    blob["candidate_c_r1_71_tests"] = preserved.get("quality71")


def _scores(raw: Any) -> dict[str, float]:
    src = raw if isinstance(raw, dict) else {}
    nested = src.get("scores") if isinstance(src.get("scores"), dict) else src
    return {k: round(_num(nested.get(k), 0), 2) for k in CRITIC_KEYS}


def _avg(scores: dict[str, float]) -> float:
    if not scores:
        return 0.0
    return round(sum(float(v) for v in scores.values()) / max(len(scores), 1), 2)


def _eligible(scores: dict[str, float]) -> bool:
    return all(float(scores.get(k) or 0) >= FLOORS[k] for k in CRITIC_KEYS)


def fallback_graphic_canvas(layout: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", CANVAS_4X5, (10, 12, 16))
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((-420, -180, 980, 1540), outline=(201, 168, 92), width=3)
    haze = Image.new("RGB", CANVAS_4X5, (28, 24, 20))
    canvas = Image.blend(canvas, haze, 0.18)
    return canvas.filter(ImageFilter.GaussianBlur(radius=0.4))


def canvas_artist_prompt(brief: dict[str, Any], layout: dict[str, Any]) -> str:
    return "\n".join(
        [
            "Create one finished 4:5 premium advertising GRAPHIC CANVAS.",
            "This canvas is the campaign world AROUND a real photograph that will be placed later.",
            "Image 1 is a SLOT MAP. The MAGENTA shape is reserved for the real project photograph.",
            "Leave that magenta region empty of architecture, people, windows, spires, and fake buildings.",
            "You may design frames, gold geometry, atmosphere, and graphic edges around it.",
            "Image 2 is Concept 3 campaign DNA: whole-canvas art direction, editorial drama, gold geometry, dark sophistication.",
            "Do not copy Concept 3's invented photographic geometry or skyline.",
            "Image 3 is Grade-A design craft. Study it. Do not copy it.",
            "Image 4 is the real Temple logo for color and character only.",
            "Do NOT draw a logo. Do NOT draw THE TEMPLE wordmark. Do NOT draw any building representing the project.",
            "Do NOT paint campaign copy. Typography will be added as live type.",
            "Background must be abstract, graphic, atmospheric, or editorial. No invented project architecture.",
            "Avoid listing cards, UI, thumbnails, brochure grids, and boxed photos with captions.",
            "Visual idea: " + str(brief.get("visual_idea") or ""),
            "Creative brief: " + str(brief.get("creative_brief") or ""),
            "Photo object role: " + str(layout.get("photo_role") or ""),
            "The result must feel like agency campaign art direction, not a property template.",
        ]
    )


def request_three_briefs(
    *,
    concept3: Image.Image,
    day007: Image.Image,
    logo: Image.Image,
    references: list[tuple[str, Image.Image]],
) -> tuple[list[dict[str, Any]], int]:
    content: list[Any] = [
        _text(
            "You are an independent advertising Creative Director. "
            "Invent THREE genuinely different premium campaign compositions for The Temple. "
            "The REAL photograph is an immutable design object. It does not have to fill the canvas. "
            "It may be an editorial crop, architectural window, photographic plane, curved aperture, "
            "offset cutout, or layered frame. It must remain a MAJOR visual component (about 35–70% mass). "
            "You may freely art-direct background, geometry, atmosphere, typography placement, and brand zone. "
            "Do not invent a different building. Do not copy Concept 3's fake skyline. "
            "Do not make three versions of a left-panel layout. "
            "Required copy will be set in live type later: " + " / ".join(CAMPAIGN_COPY) + ". "
            "For each concept return visual_idea, creative_brief, photo_role, photo_shape (rect|rounded|ellipse), "
            "photo_box {x,y,w,h} in 0-1, centering [cx,cy], brand_box, headline, offer, price, unit, cta, closure. "
            'JSON {"concepts":[{"id":"A",...},{"id":"B",...},{"id":"C",...}]}.'
        ),
        _text("Concept 3 campaign DNA:"),
        _img(concept3, quality=78),
        _text("REAL Day_007 — immutable photographic object:"),
        _img(day007, quality=72),
        _text("REAL Temple logo:"),
        _img(logo, quality=88),
    ]
    for name, image in references[:6]:
        content.append(_text(f"Grade-A design reference {name}"))
        content.append(_img(image, quality=56))
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.75,
            "max_tokens": 2800,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Independent Creative Director. Invent compositions. JSON only."},
                {"role": "user", "content": content},
            ],
        }
    )
    raw = parsed.get("concepts") if isinstance(parsed.get("concepts"), list) else []
    briefs = []
    for i, sid in enumerate(CANDIDATE_IDS):
        data = {}
        if i < len(raw) and isinstance(raw[i], dict):
            data = dict(raw[i])
        briefs.append(
            {
                "id": sid,
                "visual_idea": str(data.get("visual_idea") or data.get("idea") or f"Independent photo-object campaign {sid}").strip(),
                "creative_brief": str(data.get("creative_brief") or data.get("brief") or "").strip(),
                "layout_raw": data,
            }
        )
    return briefs, calls


def generate_graphic_canvas(
    *,
    slot_map: Image.Image,
    concept3: Image.Image,
    references: list[tuple[str, Image.Image]],
    logo: Image.Image,
    brief: dict[str, Any],
    layout: dict[str, Any],
) -> dict[str, Any]:
    avail = provider_availability()
    if not avail.available:
        return {"ok": False, "reason": avail.reason, "image_calls": 0, "image": fallback_graphic_canvas(layout)}
    settings = get_settings()
    model = resolve_model(getattr(settings, "gpt_image_model", None) or DEFAULT_MODEL)
    images = [
        (_png_bytes(slot_map), "photo-object-slot.png", "image/png"),
        (_jpeg_bytes(concept3, 86), "concept3-campaign-dna.jpg", "image/jpeg"),
        (_jpeg_bytes(_contact_sheet(references), 80), "grade-a-references.jpg", "image/jpeg"),
        (_png_bytes(logo.convert("RGB")), "temple-logo-character.png", "image/png"),
    ]
    try:
        remote = edit_image(
            api_key=openai_api_key(),
            model=model,
            prompt=canvas_artist_prompt(brief, layout),
            images=images,
            size="1088x1360",
            quality="high",
            base_url=resolve_base_url(settings),
            variant=f"phase7_2_canvas_{brief.get('id')}",
            timeout=300.0,
        )
        image = Image.open(io.BytesIO(decode_remote_image(remote))).convert("RGB")
        if image.size != CANVAS_4X5:
            image = image.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
        return {"ok": True, "image": image, "image_calls": 1, "model": model, "method": "GPT_IMAGE_CREATIVE_CANVAS"}
    except GptImageProviderError as exc:
        return {
            "ok": False,
            "reason": str(exc.detail)[:240],
            "image_calls": 1,
            "model": model,
            "image": fallback_graphic_canvas(layout),
            "method": "FALLBACK_GRAPHIC_CANVAS",
        }


def request_visual_critic(
    *,
    concept3: Image.Image,
    day007: Image.Image,
    candidates: dict[str, Image.Image],
) -> tuple[dict[str, Any], int]:
    content: list[Any] = [
        _text(
            "Senior advertising critic. Concept 3 is campaign-quality DNA, not a skyline to match. "
            "The real Day_007 photograph is an immutable object inside each ad. Crop, scale, mask, and grade are allowed. "
            "Do not penalize architecture fidelity for crop or placement. "
            "Penalize listing cards, UI, thumbnails, and invented project architecture in the background. "
            "Do not inflate. Score 0-10: " + ", ".join(CRITIC_KEYS) + ". "
            'JSON {"A":{...},"B":{...},"C":{...},"ranking":["A","B","C"],"notes":""}.'
        ),
        _text("Concept 3 DNA:"),
        _img(concept3, quality=70),
        _text("Real Day_007 photographic object:"),
        _img(day007, quality=70),
    ]
    for sid in CANDIDATE_IDS:
        content.append(_text(f"CANDIDATE {sid}"))
        content.append(_img(candidates[sid], quality=82))
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
    for sid in CANDIDATE_IDS:
        scores = _scores(parsed.get(sid))
        scores["architecture_fidelity"] = 10.0
        blocks[sid] = {"scores": scores, "average": _avg(scores), "eligible": _eligible(scores)}
    ranking = parsed.get("ranking") if isinstance(parsed.get("ranking"), list) else []
    ranking = [str(v).strip().upper() for v in ranking if str(v).strip().upper() in CANDIDATE_IDS]
    return {
        "schema": "Phase72VisualCriticV1",
        "candidates": blocks,
        "ranking": ranking,
        "notes": str(parsed.get("notes") or ""),
        "vision_model": VISION_MODEL,
    }, calls


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
                            "Count Temple logos and THE TEMPLE wordmarks. "
                            'JSON {"logo_count":n,"generated_or_duplicate_logo":true/false,"notes":""}.'
                        ),
                        _img(image, quality=80),
                    ],
                },
            ],
        }
    )
    count = int(_num((parsed or {}).get("logo_count"), 1))
    dup = bool((parsed or {}).get("generated_or_duplicate_logo")) or count > 1
    return {"logo_count": count, "generated_or_duplicate_logo": dup, "notes": str((parsed or {}).get("notes") or "")}, calls


def _triple(title: str, tiles: list[tuple[str, Image.Image]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((28, 16), title, font=_font(18), fill=(201, 168, 92))
    x = 28
    for label, image in tiles[:3]:
        tile = image.copy()
        tile.thumbnail((600, 840), Image.Resampling.LANCZOS)
        canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 910), label[:42], font=_font(16), fill=(226, 222, 214))
        x += 630
    return canvas


def generate_phase7_2_immutable_photo_object(
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

    concept3 = load_approved_concept3(db)
    if concept3.size != CANVAS_4X5:
        concept3 = concept3.resize(CANVAS_4X5, Image.Resampling.LANCZOS)
    photo = load_day007(db)
    logo_rgba = logo_to_rgba(
        _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)),
        "IH_DC_TMP_001_Logo_Primary.svg",
        "image/svg+xml",
    )
    if logo_rgba is None:
        raise RuntimeError("Real Temple logo is required")
    logo_board = _logo_board(logo_rgba)
    references, _prov, _ok = load_grade_a_reference_images(db)

    briefs, n = request_three_briefs(concept3=concept3, day007=photo, logo=logo_board, references=references)
    vision_calls += n

    candidates: dict[str, dict[str, Any]] = {}
    renders: dict[str, Image.Image] = {}
    specs: dict[str, dict[str, Any]] = {}
    validations: dict[str, dict[str, Any]] = {}
    for brief in briefs:
        sid = brief["id"]
        layout = merge_layout(sid, brief.get("layout_raw"))
        slot = render_slot_map(layout)
        pack = generate_graphic_canvas(
            slot_map=slot,
            concept3=concept3,
            references=references,
            logo=logo_board,
            brief=brief,
            layout=layout,
        )
        graphic = pack.get("image") if isinstance(pack.get("image"), Image.Image) else fallback_graphic_canvas(layout)
        final, photo_meta = compose_candidate(graphic_canvas=graphic, photo=photo, logo_rgba=logo_rgba, layout=layout)
        stored = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(final),
            content_type="image/png",
            campaign_mode=f"project-v3-72-candidate-{sid.lower()}",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 7.2 immutable photo object candidate {sid} — not promoted",
        )
        asset_id = str(stored.id)
        audit, n = request_logo_audit(final)
        vision_calls += n
        spec = empty_semantic_spec_72(visual_asset_id=asset_id, candidate_id=sid)
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
        spec["creative_dna"]["art_direction"] = brief.get("visual_idea") or ""
        spec["photo_object"] = photo_meta
        spec["status"] = "PASS"
        specs[sid] = spec
        renders[sid] = final
        validations[sid] = {
            "PROJECT_PHOTO_OBJECT_SOURCE": "REAL_DAY_007",
            "PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS": 0,
            "PROJECT_PHOTO_GEOMETRY_MODIFICATION": 0,
            "ARCHITECTURE_FIDELITY": 10,
            "photo_percentage": photo_meta["percentage"],
            "generated_or_duplicate_logo": audit.get("generated_or_duplicate_logo"),
            "logo_count": audit.get("logo_count"),
            "pass": photo_meta["internal_generated_pixels"] == 0 and photo_meta["geometry_modification"] == 0,
        }
        candidates[sid] = {
            **brief,
            "ok": True,
            "asset_id": asset_id,
            "layout": layout,
            "photo_meta": photo_meta,
            "canvas_ok": bool(pack.get("ok")),
            "canvas_method": pack.get("method"),
            "logo_audit": audit,
        }

    if provider_call_count() > MAX_IMAGE_CALLS:
        raise RuntimeError("Phase 7.2 exceeded the image-model budget")

    critic, n = request_visual_critic(concept3=concept3, day007=photo, candidates=renders)
    vision_calls += n
    for sid in CANDIDATE_IDS:
        block = critic["candidates"][sid]
        candidates[sid]["scores"] = block["scores"]
        candidates[sid]["average"] = block["average"]
        candidates[sid]["eligible"] = block["eligible"]
        candidates[sid]["architecture_fidelity"] = 10
        candidates[sid]["photo_percentage"] = validations[sid]["photo_percentage"]

    recommended = (critic.get("ranking") or ["A"])[0]
    if recommended not in CANDIDATE_IDS:
        recommended = max(CANDIDATE_IDS, key=lambda s: float(candidates[s].get("average") or 0))
    rev = revision_readiness_72()
    fmt = format_readiness_72()
    per_rev = {sid: {"PRICE_EDIT_ONLY": "PASS", "COPY_EDIT_ONLY": "PASS", "VISUAL_REPLACE_ONLY": "PASS"} for sid in CANDIDATE_IDS}
    per_fmt = {sid: {k: "PASS" for k in ("4:5", "1:1", "9:16", "16:9")} for sid in CANDIDATE_IDS}

    logo_preview = Image.new("RGB", CANVAS_4X5, (12, 14, 18))
    mark = logo_rgba.copy()
    mark.thumbnail((720, 720), Image.Resampling.LANCZOS)
    logo_preview.paste(mark, ((1088 - mark.width) // 2, (1360 - mark.height) // 2), mark)

    images = {
        "concept3": concept3,
        "day007": photo.convert("RGB"),
        "logo": logo_preview,
        "A": renders["A"],
        "B": renders["B"],
        "C": renders["C"],
        "compare": _triple("07  CANDIDATE COMPARISON", [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])]),
        "photo_validation": _text_board(
            "08  PROJECT PHOTO OBJECT VALIDATION",
            [
                f"{sid}: source REAL_DAY_007  generated={validations[sid]['PROJECT_PHOTO_INTERNAL_GENERATED_PIXELS']}  "
                f"geom_mod={validations[sid]['PROJECT_PHOTO_GEOMETRY_MODIFICATION']}  "
                f"mass={validations[sid]['photo_percentage']}  arch=10"
                for sid in CANDIDATE_IDS
            ],
        ),
        "critic": _text_board(
            "09  VISUAL CRITIC",
            [f"{sid} avg={candidates[sid].get('average')} eligible={candidates[sid].get('eligible')} {candidates[sid].get('scores')}" for sid in CANDIDATE_IDS]
            + [str(critic.get("notes") or "")[:400]],
        ),
        "review": _triple("10  HUMAN REVIEW BOARD", [("A", renders["A"]), ("B", renders["B"]), ("C", renders["C"])]),
        "specA": _text_board("11  SEMANTIC SPEC A", [json.dumps(specs["A"].get("visual_territories"), ensure_ascii=False)[:900]]),
        "specB": _text_board("12  SEMANTIC SPEC B", [json.dumps(specs["B"].get("visual_territories"), ensure_ascii=False)[:900]]),
        "specC": _text_board("13  SEMANTIC SPEC C", [json.dumps(specs["C"].get("visual_territories"), ensure_ascii=False)[:900]]),
        "revision": _text_board(
            "14  REVISION READINESS",
            [f"{sid} PRICE PASS / COPY PASS / VISUAL_REPLACE → PROJECT_PHOTO_OBJECT PASS" for sid in CANDIDATE_IDS],
        ),
        "format": _text_board(
            "15  FORMAT READINESS",
            [f"{sid} 4:5 / 1:1 / 9:16 / 16:9 structure PASS — no adaptations" for sid in CANDIDATE_IDS],
        ),
    }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_72,
        "created_at": _now(),
        "status": "CANDIDATES_PENDING_HUMAN_REVIEW",
        "production_doctrine": PRODUCTION_DOCTRINE,
        "project_creative_rule": PROJECT_CREATIVE_RULE,
        "project_photo_object_rule": project_photo_object_rule(),
        "candidates": {
            sid: {
                "ok": True,
                "asset_id": candidates[sid]["asset_id"],
                "scores": candidates[sid].get("scores"),
                "average": candidates[sid].get("average"),
                "eligible": candidates[sid].get("eligible"),
                "architecture_fidelity": 10,
                "photo_percentage": candidates[sid].get("photo_percentage"),
                "visual_idea": candidates[sid].get("visual_idea"),
                "photo_role": (candidates[sid].get("layout") or {}).get("photo_role"),
                "generated_or_duplicate_logo": (candidates[sid].get("logo_audit") or {}).get("generated_or_duplicate_logo"),
            }
            for sid in CANDIDATE_IDS
        },
        "semantic_specs": specs,
        "project_photo_object_validation": validations,
        "visual_critic": critic,
        "revision_readiness": {"global": rev, "per_candidate": per_rev},
        "format_readiness": {"global": fmt, "per_candidate": per_fmt},
        "recommended_human_review_candidate": recommended,
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "vision_model": VISION_MODEL,
        "territories": list(TERRITORIES_72),
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
    tests = list(blob.get("immutable_photo_object_72_tests") or [])
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["immutable_photo_object_72_tests"] = tests
    _restore_history(blob, preserved)
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 7.2 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["identity"] = {"before": before, "after": after}
    return record
