"""Phase 6.0 — Pure Creative Director. Design first. No reconstruction. No promotion."""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_master_lock import APPROVED_R2_ASSET_ID
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_5a_ai_visual_art_director import load_grade_a_reference_images
from investhome_api.services.creative_director.phase5_5c_r1_price_hierarchy import PARENT_MASTER_ID
from investhome_api.services.creative_director.phase5_5d_visual_replace_proof import PRICE_R1_REVISION_ID
from investhome_api.services.creative_director.phase5_6_premium_master_redesign import _logo_board
from investhome_api.services.creative_director.phase5_8_art_direction import render_photo_selection_board
from investhome_api.services.creative_director.phase5_8_new_premium_master import _text_board
from investhome_api.services.creative_director.phase5_9_ai_draft_structured_master import _HISTORY_KEYS as _H59
from investhome_api.services.creative_director.phase5_9_ai_draft_structured_master import _preserve as _preserve_59
from investhome_api.services.creative_director.phase5_9_visual_draft import render_reference_board
from investhome_api.services.creative_director.phase5_creative_quality import APPROVED_R1_ASSET_ID, _font
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
from investhome_api.services.creative_director.phase6_0_creative import (
    CAMPAIGN_COPY,
    CREATIVE_OBJECTIVE,
    CRITIC_KEYS,
    MAX_IMAGE_CALLS,
    generate_concept_image,
    name_concepts,
    overall,
    render_critic_board,
    render_six_board,
    request_fresh_visual_critic,
    request_six_creative_briefs,
    resolve_photo,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.ai_visual_art_director import _img, _text
from investhome_api.services.creative_director.temple_exterior_catalog import load_temple_exteriors
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_60 = "phase6_0_pure_creative_director"
_HISTORY_KEYS = _H59 + (("ai_draft_structured_master_59_tests", "quality59"),)

# Stage B only. Never sent to the Creative Director or the image artist.
_V4_FEASIBILITY_CONTEXT = (
    "A later production engine can composite a real photograph, a real vector logo, "
    "and real fonts with structured typography and a small vocabulary of tonal fields "
    "(veil, ground plane, corner fade, fine rules). It cannot paint custom split shapes, "
    "curved wipes, illustrated architecture, unique chrome buttons, or type that is "
    "sculpted into the building. Judge whether THIS visual idea could be rebuilt with "
    "those tools without losing the idea."
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_59(blob)
    preserved["quality59"] = list(blob.get("ai_draft_structured_master_59_tests") or [])
    return preserved


def request_feasibility(concept: dict[str, Any]) -> tuple[dict[str, Any], int]:
    content = [
        _text(
            "Production feasibility only. Do not redesign. Classify: EASY, MODERATE, DIFFICULT, "
            "or NOT_CURRENTLY_RECONSTRUCTABLE. Also: relationships_to_preserve, required_capabilities, "
            "what_would_be_lost. "
            + _V4_FEASIBILITY_CONTEXT
        ),
        _text(json.dumps({"visual_idea": concept.get("visual_idea"), "brief": concept.get("creative_brief")}, ensure_ascii=False)[:4000]),
        _text("CONCEPT IMAGE"),
        _img(concept["image"], quality=82),
    ]
    parsed, calls = _vision(
        {
            "model": VISION_MODEL,
            "temperature": 0.0,
            "max_tokens": 1600,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Production engineer. JSON only. Do not invent a new design."},
                {"role": "user", "content": content},
            ],
        }
    )
    level = str(parsed.get("classification") or parsed.get("feasibility") or parsed.get("level") or "").upper()
    if level not in {"EASY", "MODERATE", "DIFFICULT", "NOT_CURRENTLY_RECONSTRUCTABLE"}:
        text = json.dumps(parsed, ensure_ascii=False).upper()
        if "NOT_CURRENTLY" in text or "NOT CURRENTLY" in text:
            level = "NOT_CURRENTLY_RECONSTRUCTABLE"
        elif "DIFFICULT" in text:
            level = "DIFFICULT"
        elif "EASY" in text:
            level = "EASY"
        else:
            level = "MODERATE"
    return {
        "index": concept.get("index"),
        "name": concept.get("name"),
        "classification": level,
        "relationships_to_preserve": parsed.get("relationships_to_preserve"),
        "required_capabilities": parsed.get("required_capabilities"),
        "what_would_be_lost": parsed.get("what_would_be_lost"),
        "notes": str(parsed.get("notes") or ""),
    }, calls


def render_top_three(concepts: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1920, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "11  TOP THREE  —  critic ranking  —  not promoted", font=_font(18), fill=(201, 168, 92))
    x = 36
    for item in concepts[:3]:
        image = item.get("image")
        if isinstance(image, Image.Image):
            tile = image.copy()
            tile.thumbnail((580, 820), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, 56))
        draw.text((x, 900), f"{item.get('index')}  {str(item.get('name') or '')[:40]}", font=_font(14), fill=(226, 222, 214))
        x += 620
    return canvas


def render_human_review_board_60(*, concepts: list[dict[str, Any]], ranking: list[int], status: str) -> Image.Image:
    canvas = Image.new("RGB", (1920, 1480), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "13  HUMAN REVIEW BOARD  —  PHASE 6.0  —  ALL SIX VISIBLE", font=_font(18), fill=(201, 168, 92))
    for i, item in enumerate(concepts[:6]):
        gx, gy = i % 3, i // 3
        x, y = 36 + gx * 620, 60 + gy * 640
        image = item.get("image")
        if isinstance(image, Image.Image):
            tile = image.copy()
            tile.thumbnail((580, 560), Image.Resampling.LANCZOS)
            canvas.paste(tile.convert("RGB"), (x, y))
        draw.text((x, y + 570), f"{item.get('index')}  {str(item.get('name') or '')[:36]}", font=_font(14), fill=(226, 222, 214))
    draw.text((36, 1360), f"STATUS  {status}    ranking {ranking}", font=_font(16), fill=(80, 200, 120))
    draw.text((36, 1400), "Find a visual design we actually love. No reconstruction. No promotion.", font=_font(16), fill=(201, 168, 92))
    return canvas


def generate_pure_creative_director_60(
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
    logo_rgba = logo_to_rgba(_read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID)), "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
    logo_board = _logo_board(logo_rgba)
    references, ref_provenance, refs_ok = load_grade_a_reference_images(db)
    catalog = load_temple_exteriors(db)
    briefs, n = request_six_creative_briefs(photos=catalog, references=references, logo=logo_board)
    vision_calls += n
    while len(briefs) < 6:
        briefs.append(
            {
                "index": len(briefs) + 1,
                "selected_project_image": catalog[len(briefs) % len(catalog)]["filename"] if catalog else "",
                "why_this_photograph": "alternate Temple exterior for an independent visual idea",
                "visual_idea": f"Independent campaign idea {len(briefs) + 1} for The Temple as an iconic Washington building.",
                "creative_brief": CREATIVE_OBJECTIVE + " Invent a distinct visual idea. Required copy only: " + " / ".join(CAMPAIGN_COPY) + ".",
            }
        )
    used_photos: set[str] = set()
    concepts: list[dict[str, Any]] = []
    image_model = None
    for brief in briefs[:6]:
        if provider_call_count() >= MAX_IMAGE_CALLS:
            break
        photo = resolve_photo(catalog, str(brief.get("selected_project_image") or ""), used_photos)
        used_photos.add(photo["asset_id"])
        pack = generate_concept_image(photo=photo["preview"], logo=logo_board, references=references, brief=brief)
        image_model = pack.get("model") or image_model
        concept = {
            **brief,
            "selected_photo_asset_id": photo["asset_id"],
            "selected_photo_filename": photo["filename"],
            "ok": pack.get("ok"),
            "reason": pack.get("reason"),
            "image": pack.get("image"),
            "image_calls": pack.get("image_calls") or 0,
            "model": pack.get("model"),
        }
        if pack.get("ok") and isinstance(pack.get("image"), Image.Image):
            asset = persist_gpt_image(
                db,
                actor=user,
                linked_project_id=row.linked_project_id,
                content=_png(pack["image"]),
                content_type="image/png",
                campaign_mode=f"project-v3-60-concept-{brief['index']}",
                session_id=str(uuid4()),
                provider_generation_id=None,
                campaign_context_id=str(row.id),
                brief_excerpt=f"PHASE 6.0 disposable concept {brief['index']}",
            )
            concept["asset_id"] = str(asset.id)
        concepts.append(concept)
    name_concepts(concepts)
    critic, n = request_fresh_visual_critic(concepts=concepts, references=references)
    vision_calls += n
    for item in concepts:
        item["scores"] = (critic.get("scores") or {}).get(str(item.get("index"))) or {}
        item["overall"] = overall(item["scores"])
    ranking = [int(v) for v in (critic.get("ranking") or []) if int(v) >= 1]
    by_index = {int(item.get("index") or 0): item for item in concepts}
    ranked = [by_index[i] for i in ranking if i in by_index]
    if not ranked:
        ranked = sorted(concepts, key=lambda it: -float(it.get("overall") or 0))
    top_three = [item for item in ranked if item.get("ok")][:3]
    feasibility: list[dict[str, Any]] = []
    for item in top_three:
        if not isinstance(item.get("image"), Image.Image):
            continue
        report, n = request_feasibility(item)
        vision_calls += n
        feasibility.append(report)
    if provider_call_count() > MAX_IMAGE_CALLS:
        raise RuntimeError("Phase 6.0 exceeded the image-model budget")
    status = "CONCEPTS_PENDING_HUMAN_REVIEW" if any(c.get("ok") for c in concepts) else "CREATIVE_GENERATION_FAILED"
    images: dict[str, Any] = {
        "photos": render_photo_selection_board(catalog),
        "references": render_reference_board(references, logo_board),
        "six": render_six_board(concepts, "09  SIX CONCEPT BOARD  —  primary human review  —  not production"),
        "critic": render_critic_board(critic, concepts),
        "top_three": render_top_three(top_three),
        "feasibility": _text_board(
            "12  PRODUCTION FEASIBILITY  —  analysis only  —  no reconstruction",
            [json.dumps(item, ensure_ascii=False, default=str) for item in feasibility] or ["no top three"],
        ),
        "review": render_human_review_board_60(concepts=concepts, ranking=ranking, status=status),
    }
    for item in concepts:
        if isinstance(item.get("image"), Image.Image):
            images[f"concept_{item['index']}"] = item["image"]

    def public_concept(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "index": item.get("index"),
            "name": item.get("name"),
            "selected_project_image": item.get("selected_photo_filename"),
            "selected_photo_asset_id": item.get("selected_photo_asset_id"),
            "why_this_photograph": item.get("why_this_photograph"),
            "visual_idea": item.get("visual_idea"),
            "creative_brief": item.get("creative_brief"),
            "scores": item.get("scores"),
            "overall": item.get("overall"),
            "ok": item.get("ok"),
            "asset_id": item.get("asset_id"),
        }

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_60,
        "created_at": _now(),
        "status": status,
        "creative_director_model": VISION_MODEL,
        "image_generation_model": image_model,
        "references_actually_provided": bool(refs_ok and len(references) == 6),
        "project_images_actually_provided": bool(catalog),
        "image_model_calls": provider_call_count(),
        "vision_calls": vision_calls,
        "campaign_copy": list(CAMPAIGN_COPY),
        "photo_selection": [
            {"index": c.get("index"), "filename": c.get("selected_photo_filename"), "asset_id": c.get("selected_photo_asset_id"), "why": c.get("why_this_photograph")}
            for c in concepts
        ],
        "creative_briefs": [
            {k: c.get(k) for k in ("index", "name", "selected_photo_filename", "visual_idea", "creative_brief", "why_this_photograph")}
            for c in concepts
        ],
        "concepts": [public_concept(c) for c in concepts],
        "visual_critic": critic,
        "ranking": ranking,
        "top_three": [c.get("index") for c in top_three],
        "production_feasibility": feasibility,
        "reconstruction_executed": False,
        "promoted_to_master": False,
        "existing_master_id": PARENT_MASTER_ID,
        "existing_master_asset_id": APPROVED_R2_ASSET_ID,
        "existing_master_changed": False,
        "price_revision_child_id": PRICE_R1_REVISION_ID,
        "visual_replace_child_id": "6f18ae33-72fb-4506-ab49-24f8d90b6c2d",
        "phase5_8_rejected": True,
        "phase5_9_rejected": True,
        "production_cover_changed": False,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "existing_54_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_54_master_asset_id": APPROVED_R1_ASSET_ID,
        "project_id": TEMPLE_PROJECT_ID,
        "reference_ids": ref_provenance,
        "language": language,
        "next_decision": "HUMAN VISUAL REVIEW",
    }
    tests = [t for t in list(blob.get("pure_creative_director_60_tests") or []) if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_60)]
    tests.append(json.loads(json.dumps(_jsonable(record), default=str)))
    blob["pure_creative_director_60_tests"] = tests
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
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if str((preserved.get("human_master") or {}).get("approved_asset_id") or APPROVED_R2_ASSET_ID) != APPROVED_R2_ASSET_ID:
        raise RuntimeError("Phase 6.0 refused to change the approved technical Master")
    _ = PRODUCTION_COVER_V2
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    return record
