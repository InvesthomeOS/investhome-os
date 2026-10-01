"""Phase 5.4I — Day_002 × EDITORIAL_DARK_FIELD production proof.

One eligible pair. No new family. No Day_004. Does not promote.
GPT Image calls = 0.
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
from investhome_api.services.creative_director.adaptive_composition_engine import compose_adaptive, occupancy_aware_crop
from investhome_api.services.creative_director.commercial_offer_composer import render_commercial_proof
from investhome_api.services.creative_director.creative_collision_engine import render_collision_proof
from investhome_api.services.creative_director.creative_contrast_engine import render_contrast_map
from investhome_api.services.creative_director.creative_family_adapter import build_family_master_spec, family_revision_readiness
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _font,
    _wrap,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_final_composition import flatten_critic
from investhome_api.services.creative_director.phase5_photo_family_eligibility import _HISTORY_KEYS as _BASE_HISTORY
from investhome_api.services.creative_director.phase5_photo_family_eligibility import _preserve as _preserve_base
from investhome_api.services.creative_director.phase5_photo_foundation import architecture_provenance_qa
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_creative import _jpeg_b64
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
from investhome_api.services.creative_director.photo_family_eligibility import (
    analyze_creative_composition,
    classify_photo_composition,
    evaluate_family_eligibility,
)
from investhome_api.services.creative_director.photo_occupancy_map import occupancy_to_json, render_occupancy_map
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_54I = "phase5_4i_best_pair_proof"
DAY002_ASSET_ID = "543aeb03-c4c9-46f9-9d9f-81bf53f45438"
DAY002_FILENAME = "IH_DC_TMP_001_Render_Exterior_Day_002.jpg"
PROOF_FAMILY_ID = "EDITORIAL_DARK_FIELD"
REF_00013 = "8ee69d5b-b734-57e8-a9dd-06b8a15a4e57"
REF_00015 = "b57f0ba1-3cc7-583c-98a8-c4330a7e4cdd"
IDENTITY_SCALES = (1.0, 0.92, 0.86, 0.82, 0.78)
_HISTORY_KEYS = _BASE_HISTORY + (("photo_family_eligibility_tests", "quality54h"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54h"] = list(blob.get("photo_family_eligibility_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {
            k: _jsonable(v)
            for k, v in value.items()
            if not str(k).startswith("_") and k not in {"layers", "occupancy", "foundation", "image", "fielded"}
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _library() -> dict[str, Any]:
    catalog = {name: seeded_reference_family(name) for name in GRADE_A_ORDER}
    return build_family_library(catalog)


def technical_preflight_54i(
    *,
    eligibility: dict[str, Any],
    pack: dict[str, Any],
    ready: dict[str, Any],
    provenance: dict[str, Any],
) -> dict[str, Any]:
    pf = dict(pack.get("preflight") or {})
    checks_in = dict(pf.get("checks") or {})
    identity_ok = str(pack.get("family_id") or "") == PROOF_FAMILY_ID and float(pack.get("scale") or 0) >= 0.78
    checks = {
        "photo_family_eligibility": "PASS" if eligibility.get("status") == "ELIGIBLE" else "FAIL",
        "architecture_source_integrity": "PASS"
        if provenance.get("status") == "pass" and pf.get("architecture_pixels_unchanged")
        else "FAIL",
        "architecture_clearance": checks_in.get("architecture_clearance") or "FAIL",
        "headline_collision": checks_in.get("text_collision") or "FAIL",
        "commercial_collision": checks_in.get("text_collision") or "FAIL",
        "logo_collision": checks_in.get("logo_collision") or "FAIL",
        "cta_collision": checks_in.get("cta_collision") or "FAIL",
        "contrast": checks_in.get("contrast") or "FAIL",
        "UTF8": checks_in.get("utf8") or "FAIL",
        "font_availability": checks_in.get("font_availability") or "FAIL",
        "commercial_hierarchy": checks_in.get("commercial_hierarchy") or "FAIL",
        "canvas_bounds": checks_in.get("canvas_bounds") or "FAIL",
        "family_identity": "PASS" if identity_ok else "FAIL",
        "revision_readiness": ready.get("revision_readiness") or "FAIL",
    }
    if not turkish_copy_is_valid(pack.get("facts") or {}):
        checks["UTF8"] = "FAIL"
    return {
        "schema": "BestPairTechnicalPreflightV1",
        "checks": checks,
        "pass": all(v == "PASS" for v in checks.values()),
        "scale": pack.get("scale"),
        "flex_mode": pack.get("flex_mode"),
        "iterations": pack.get("iterations"),
        "solved": pack.get("solved"),
    }


def request_best_pair_critic(*, candidate: Image.Image, foundation: Image.Image) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1600,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": "Independent luxury real-estate art director. Score the FINAL compositor output. Do not inflate. JSON only.",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Family EDITORIAL_DARK_FIELD on Temple Day_002. Image 1 = candidate. Image 2 = photographic foundation. "
                            "Scores 0-10: professional_art_direction, family_fidelity, composition, image_design_integration, "
                            "typography, hierarchy, commercial_clarity, logo_integration, cta_integration, premium_character, "
                            "readability, architecture_fidelity, publishability. "
                            "Undesirable 0-10 (lower better): TEXT_ON_PHOTO_FEEL, TEMPLATE_FEEL, LISTING_CARD_FEEL, UI_FEEL, CLUTTER. "
                            "Also booleans: spire_collision, unreadable, listing_card, dashboard, malformed_turkish, architecture_modified, notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    return flatten_critic(parsed), calls


def render_analysis_board(foundation: Image.Image, occupancy: dict[str, Any], analysis: dict[str, Any]) -> Image.Image:
    board = render_occupancy_map(foundation, occupancy)
    draw = ImageDraw.Draw(board)
    plane = dict(analysis.get("dark_contiguous_plane") or {})
    draw.text((36, 910), "DAY_002 CREATIVE COMPOSITION ANALYSIS", fill=(201, 168, 92), font=_font(16))
    draw.text(
        (36, 938),
        f"dark plane  {plane.get('width')} x {plane.get('height')}  area {plane.get('area')}  luma {plane.get('mean_luma')}  edge {plane.get('edge')}",
        fill=(236, 230, 218),
        font=_font(14),
    )
    arch = dict(analysis.get("architecture_silhouette") or {})
    draw.text(
        (36, 964),
        f"hard {arch.get('hard_protected')}  centroid {arch.get('centroid_x')}  class {dict(analysis.get('composition_class') or {}).get('primary_class')}",
        fill=(180, 176, 168),
        font=_font(13),
    )
    return board.crop((0, 0, board.size[0], min(board.size[1], 1080)))


def render_eligibility_proof(result: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    status = str(result.get("status") or "")
    color = (80, 200, 120) if status == "ELIGIBLE" else (220, 80, 80)
    draw.text((36, 28), "PHOTO × FAMILY ELIGIBILITY", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 70), "Day_002  ×  EDITORIAL_DARK_FIELD", fill=(236, 230, 218), font=_font(18))
    draw.text((36, 110), status, fill=color, font=_font(36))
    y = 170
    for name, item in dict(result.get("checks") or {}).items():
        ok = bool(item.get("pass")) if isinstance(item, dict) else bool(item)
        draw.text((36, y), f"{name}  {'PASS' if ok else 'FAIL'}", fill=(80, 200, 120) if ok else (220, 80, 80), font=_font(15))
        y += 28
    draw.text((36, 660), str(result.get("primary_reason") or ""), fill=(180, 176, 168), font=_font(13))
    return canvas


def render_family_reference(ref13: Image.Image | None, ref15: Image.Image | None) -> Image.Image:
    canvas = Image.new("RGB", (1280, 780), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "EDITORIAL_DARK_FIELD  —  ORNEK_00013 + ORNEK_00015", fill=(201, 168, 92), font=_font(18))
    x = 36
    for img, label in ((ref13, "ORNEK_00013"), (ref15, "ORNEK_00015")):
        if isinstance(img, Image.Image):
            tile = img.copy()
            tile.thumbnail((580, 640), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 60))
        draw.text((x, 720), label, fill=(236, 230, 218), font=_font(14))
        x += 620
    return canvas


def render_composition_plan(foundation: Image.Image, pack: dict[str, Any]) -> Image.Image:
    src = foundation.convert("RGB").resize((540, 675), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (1280, 760), (12, 14, 20))
    canvas.paste(src, (36, 50))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 16), "COMPOSITION PLAN  —  type lives in the photo's dark plane", fill=(201, 168, 92), font=_font(16))
    region = dict(pack.get("region") or {})
    sx, sy = 540 / 1088, 675 / 1360
    box = (
        36 + int(float(region.get("x") or 0) * 540),
        50 + int(float(region.get("y") or 0) * 675),
        36 + int((float(region.get("x") or 0) + float(region.get("w") or 0)) * 540),
        50 + int((float(region.get("y") or 0) + float(region.get("h") or 0)) * 675),
    )
    draw.rectangle(box, outline=(201, 168, 92), width=2)
    _ = sx, sy
    y = 50
    lines = [
        f"family  {pack.get('family_id')}",
        f"flex  {pack.get('flex_mode')}  scale {pack.get('scale')}",
        f"alignment  {pack.get('alignment')}",
        f"field_source  {region.get('field_source')}",
        f"region  {region.get('x')} {region.get('y')} {region.get('w')} {region.get('h')}",
        f"origin  {pack.get('origin')}",
        f"iterations  {pack.get('iterations')}  solved {pack.get('solved')}",
        "No manufactured full-bleed navy panel when the plane already works.",
    ]
    for line in lines:
        for chunk in _wrap(str(line), 48):
            draw.text((600, y), chunk, fill=(180, 176, 168), font=_font(14))
            y += 24
    return canvas


def render_structure_map(candidate: Image.Image, objects: dict[str, Any]) -> Image.Image:
    src = candidate.convert("RGB")
    overlay = src.copy()
    draw = ImageDraw.Draw(overlay)
    colors = {
        "headline": (201, 168, 92),
        "unit_type": (140, 190, 220),
        "price": (236, 230, 218),
        "discount": (201, 168, 92),
        "discount_label": (180, 176, 168),
        "cta": (80, 200, 120),
        "project_logo": (90, 210, 190),
    }
    w, h = src.size
    for role, item in objects.items():
        px = item.get("px") if isinstance(item, dict) else None
        if not (isinstance(px, (list, tuple)) and len(px) == 4):
            bounds = item.get("bounds") if isinstance(item, dict) else None
            if isinstance(bounds, dict):
                px = (
                    float(bounds.get("x") or 0) * w,
                    float(bounds.get("y") or 0) * h,
                    (float(bounds.get("x") or 0) + float(bounds.get("w") or 0)) * w,
                    (float(bounds.get("y") or 0) + float(bounds.get("h") or 0)) * h,
                )
        if not px:
            continue
        color = colors.get(role, (180, 180, 180))
        draw.rectangle(tuple(int(v) for v in px), outline=color, width=2)
        draw.text((int(px[0]) + 4, int(px[1]) + 2), role, fill=color, font=_font(12))
    canvas = Image.new("RGB", (src.width + 40, src.height + 80), (12, 14, 20))
    canvas.paste(overlay, (20, 50))
    ImageDraw.Draw(canvas).text((20, 16), "STRUCTURE MAP  —  semantic objects", fill=(201, 168, 92), font=_font(16))
    return canvas


def render_preflight_board(preflight: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 820), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    ok = bool(preflight.get("pass"))
    draw.text((36, 24), "HARD TECHNICAL PREFLIGHT", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 64), "PASS" if ok else "FAIL", fill=(80, 200, 120) if ok else (220, 80, 80), font=_font(32))
    y = 120
    for name, value in dict(preflight.get("checks") or {}).items():
        draw.text((36, y), f"{name}  {value}", fill=(80, 200, 120) if value == "PASS" else (220, 80, 80), font=_font(16))
        y += 32
    return canvas


def render_critic_scorecard(critic: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "VISUAL CRITIC  —  do not inflate", fill=(201, 168, 92), font=_font(20))
    y = 80
    keys = (
        "professional_art_direction",
        "family_fidelity",
        "composition",
        "image_design_integration",
        "typography",
        "hierarchy",
        "commercial_clarity",
        "logo_integration",
        "cta_integration",
        "premium_character",
        "readability",
        "architecture_fidelity",
        "publishability",
    )
    for key in keys:
        draw.text((36, y), f"{key}  {critic.get(key)}", fill=(236, 230, 218), font=_font(16))
        y += 28
    y += 12
    draw.text((36, y), "UNDESIRABLE (lower better)", fill=(201, 168, 92), font=_font(16))
    y += 32
    for key in ("TEXT_ON_PHOTO_FEEL", "TEMPLATE_FEEL", "LISTING_CARD_FEEL", "UI_FEEL", "CLUTTER"):
        draw.text((36, y), f"{key}  {critic.get(key)}", fill=(180, 176, 168), font=_font(16))
        y += 28
    return canvas


def render_human_review(candidate: Image.Image, preflight: dict[str, Any], critic: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 20), "HUMAN REVIEW  —  5.4I BEST PAIR PROOF", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 52), "CANDIDATE. DO NOT PROMOTE. GPT IMAGE 0.", fill=(236, 230, 218), font=_font(16))
    tile = candidate.copy()
    tile.thumbnail((700, 875), Image.Resampling.LANCZOS)
    canvas.paste(tile, (36, 90))
    draw.text((760, 90), f"technical  {'PASS' if preflight.get('pass') else 'FAIL'}", fill=(180, 176, 168), font=_font(16))
    draw.text((760, 124), f"art  {critic.get('professional_art_direction')}", fill=(180, 176, 168), font=_font(16))
    draw.text((760, 158), f"publish  {critic.get('publishability')}", fill=(180, 176, 168), font=_font(16))
    draw.text((760, 192), f"arch  {critic.get('architecture_fidelity')}", fill=(180, 176, 168), font=_font(16))
    draw.text((760, 240), "HUMAN REVIEW REQUIRED  YES", fill=(201, 168, 92), font=_font(16))
    draw.text((760, 280), "PROMOTED  NO", fill=(236, 230, 218), font=_font(16))
    return canvas


def generate_best_pair_proof_4x5(
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
    lock_failed: list[str] = []
    status = "FAIL_FAST_MISSING_DAY002"
    images: dict[str, Any] = {}
    library_blob = _library()
    fonts = build_font_registry()
    family = family_by_id(library_blob, PROOF_FAMILY_ID)
    eligibility: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    pack: dict[str, Any] | None = None
    spec: dict[str, Any] | None = None
    preflight: dict[str, Any] | None = None
    critic: dict[str, Any] = {}
    ready: dict[str, Any] | None = None
    candidate_asset_id: str | None = None
    field_asset_id: str | None = None

    try:
        source = Image.open(io.BytesIO(_read_bytes(db, UUID(DAY002_ASSET_ID)))).convert("RGB")
    except Exception as exc:
        lock_failed.append(f"DAY002_UNREADABLE:{exc}")
        source = None

    if source is not None:
        foundation, crop, occupancy = occupancy_aware_crop(source, family)
        composition = classify_photo_composition(foundation, occupancy)
        eligibility = evaluate_family_eligibility(
            photo=foundation,
            occupancy=occupancy,
            family=family,
            fonts=fonts,
            composition=composition,
        )
        analysis = analyze_creative_composition(foundation, occupancy)
        images["analysis"] = render_analysis_board(foundation, occupancy, analysis)
        images["eligibility"] = render_eligibility_proof(eligibility)
        ref13 = ref15 = None
        try:
            ref13 = Image.open(io.BytesIO(_read_bytes(db, UUID(REF_00013)))).convert("RGB")
        except Exception:
            ref13 = None
        try:
            ref15 = Image.open(io.BytesIO(_read_bytes(db, UUID(REF_00015)))).convert("RGB")
        except Exception:
            ref15 = None
        images["reference"] = render_family_reference(ref13, ref15)

        if eligibility.get("status") != "ELIGIBLE":
            status = "ELIGIBILITY_FAIL_NO_RENDER"
        else:
            logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
            logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
            pack = compose_adaptive(
                source=source,
                family=family,
                fonts=fonts,
                logo_rgba=logo_rgba,
                scale_order=IDENTITY_SCALES,
            )
            field_asset = persist_gpt_image(
                db,
                actor=user,
                linked_project_id=row.linked_project_id,
                content=_png(pack["fielded"]),
                content_type="image/png",
                campaign_mode="project-best-pair-graphic-field",
                session_id=str(uuid4()),
                provider_generation_id=None,
                campaign_context_id=str(row.id),
                brief_excerpt="PHASE 5.4I Day_002 EDITORIAL_DARK_FIELD graphic_field",
            )
            field_asset_id = str(field_asset.id)
            pack["graphic_field_asset_id"] = field_asset_id
            asset = persist_gpt_image(
                db,
                actor=user,
                linked_project_id=row.linked_project_id,
                content=_png(pack["image"]),
                content_type="image/png",
                campaign_mode="project-best-pair-candidate",
                session_id=str(uuid4()),
                provider_generation_id=None,
                campaign_context_id=str(row.id),
                brief_excerpt="PHASE 5.4I Day_002 EDITORIAL_DARK_FIELD candidate",
            )
            candidate_asset_id = str(asset.id)
            spec = build_family_master_spec(
                key="BP-1",
                pack=pack,
                family=family,
                crop=pack.get("crop") or crop,
                photo_asset=DAY002_ASSET_ID,
                logo_asset=LOCKED_LOGO_ASSET_ID,
                candidate_asset_id=candidate_asset_id,
                architecture_lock={"schema": "PhotoOccupancyMapV1", "protected_coverage": (occupancy.get("coverage") or {}).get("hard_protected")},
            )
            spec["schema"] = "ProductionMasterCandidateV1"
            spec["graphic_field"]["asset_id"] = field_asset_id
            spec["graphic_field"]["semantic_role"] = "graphic_field"
            spec["graphic_devices"] = dict(family.get("graphic_devices") or {})
            spec["grade"] = dict(LOCKED_GRADE)
            spec["relationships"] = {
                "headline_to_offer": "stacked_editorial_column",
                "offer_is_one_system": True,
                "cta_is_inscription": True,
                "field_source": (pack.get("region") or {}).get("field_source"),
            }
            spec["visual_replace_requires_eligibility"] = True
            spec["visual_replace_pipeline"] = ["NEW PHOTO", "PhotoFamilyEligibilityEngineV1", "AdaptiveCompositionEngineV1"]
            spec["contrast_variant"] = pack.get("fills")
            spec["adaptive_plan"] = {
                "flex_mode": pack.get("flex_mode"),
                "scale": pack.get("scale"),
                "alignment": pack.get("alignment"),
                "solved": pack.get("solved"),
                "iterations": pack.get("iterations"),
            }
            ready = family_revision_readiness(spec)
            provenance = architecture_provenance_qa(
                source=source,
                foundation=pack["foundation"],
                final=pack["image"],
                transform={"centering": list((pack.get("crop") or {}).get("centering") or [0.5, 0.32]), "source_crop": (pack.get("crop") or {}).get("source_crop") or [0, 0, 1, 1]},
            )
            preflight = technical_preflight_54i(eligibility=eligibility, pack=pack, ready=ready, provenance=provenance)
            critic, n = request_best_pair_critic(candidate=pack["image"], foundation=pack["foundation"])
            vision_calls += n
            images["plan"] = render_composition_plan(pack["foundation"], pack)
            images["candidate"] = pack["image"]
            images["structure"] = render_structure_map(pack["image"], dict(pack.get("objects") or {}))
            images["preflight"] = render_preflight_board(preflight)
            images["critic"] = render_critic_scorecard(critic)
            images["human"] = render_human_review(pack["image"], preflight, critic)
            images["contrast"] = render_contrast_map(pack["fielded"], dict(pack.get("preflight", {}).get("contrast") or {}), dict(pack.get("objects") or {}))
            images["collision"] = render_collision_proof(pack["foundation"], occupancy, [("BP-1", dict(pack.get("objects") or {}))])
            images["commercial"] = render_commercial_proof(pack["image"], dict(pack.get("objects") or {}), "BP-1")
            status = "CANDIDATE_PENDING_HUMAN_REVIEW" if preflight.get("pass") else "TECHNICAL_PREFLIGHT_FAIL"

    gpt_calls = provider_call_count()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54I,
        "created_at": _now(),
        "status": status,
        "photo": {"asset_id": DAY002_ASSET_ID, "filename": DAY002_FILENAME, "creative_suitability": "HIGH"},
        "family": PROOF_FAMILY_ID,
        "eligibility_status": (eligibility or {}).get("status"),
        "eligibility": _jsonable(eligibility),
        "analysis": _jsonable(analysis),
        "candidate_asset_id": candidate_asset_id,
        "graphic_field_asset_id": field_asset_id,
        "spec_id": (spec or {}).get("spec_id"),
        "spec": spec,
        "solver_iterations": (pack or {}).get("iterations"),
        "flex_mode": (pack or {}).get("flex_mode"),
        "scale": (pack or {}).get("scale"),
        "alignment": (pack or {}).get("alignment"),
        "solved": (pack or {}).get("solved"),
        "technical_preflight": preflight,
        "revision_readiness": ready,
        "critic": critic,
        "lock_failed": lock_failed,
        "generation_model": None,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "new_family_created": False,
        "day004_used": False,
        "phase55_executed": False,
        "formats_created": False,
        "video_started": False,
        "project_id": TEMPLE_PROJECT_ID,
        "occupancy_map": occupancy_to_json(dict((pack or {}).get("occupancy") or {})) if pack else None,
        "human_review_required": True,
    }
    tests = [
        t
        for t in list(blob.get("best_pair_proof_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54I)
    ]
    stored = json.loads(json.dumps(record, default=str))
    tests.append(stored)
    blob["best_pair_proof_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["approved_creative_masters"] = preserved["approved_creative"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    _production_guard(before, after)
    if blob.get("premium_commercial_r1_tests") != preserved["r1"]:
        raise RuntimeError("Phase 5.4I refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4I refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4I refused to modify approved creative masters")
    if blob.get("photo_family_eligibility_tests") != preserved.get("quality54h"):
        raise RuntimeError("Phase 5.4I refused to overwrite Phase 5.4H history")
    if blob.get("final_composition_tests") != preserved.get("quality54g"):
        raise RuntimeError("Phase 5.4I refused to overwrite Phase 5.4G history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4I refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library_blob
    record["pack"] = pack
    _ = language
    return record
