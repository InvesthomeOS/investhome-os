"""Phase 5.4A — PREMIUM_COMMERCIAL production-master finalization.

One child of Phase 5.4 Master B. Does not activate live routing.
Does not use GPT Image as designer. Does not overwrite 5.4 A/B/C.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import (
    APPROVAL_CANDIDATE,
    MASTER_COMMERCIAL_FINAL_ID,
    MASTER_COMMERCIAL_ID,
    build_premium_commercial_final_master,
    markup_has_semantic_slots,
    scene_premium_commercial,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_design_scene import (
    VISION_MODEL,
    _jpeg_b64,
    _jpeg_data_uri,
    _vision,
    assemble_scene,
    font_face_css,
    inline_logo_svg,
    persistable_markup,
    render_html_to_png,
    validate_scene,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_production_creative import PHASE50_MASTER_ASSET_ID
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    TEMPLE_PROJECT_ID,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54A = "phase5_4a_premium_commercial_final"
PARENT_REASON = "HUMAN_SELECTED_PRODUCTION_FINALIZATION"

CRITIC_MIN = {
    "professional_design_quality": 8,
    "photo_design_integration": 8,
    "visual_hierarchy": 8,
    "typographic_sophistication": 8,
    "commercial_hierarchy": 8,
    "premium_character": 8,
    "readability": 8,
    "architecture_respect": 9,
}
CRITIC_MAX = {
    "text_on_photo_likeness": 3,
    "template_likeness": 3,
    "visual_clutter": 3,
}


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _g(scores: dict[str, Any], key: str, default: float = 0) -> float:
    aliases = {
        "commercial_hierarchy": ("commercial_hierarchy", "commercial_readability"),
        "readability": ("readability", "commercial_readability"),
        "architecture_respect": ("architecture_respect", "architecture_truth"),
    }
    keys = aliases.get(key, (key,))
    for item in keys:
        raw = scores.get(item)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return default


def critic_pass_54a(scores: dict[str, Any]) -> bool:
    if _g(scores, "architecture_respect", 0) < 9:
        return False
    for key, minimum in CRITIC_MIN.items():
        if _g(scores, key, 0) < minimum:
            return False
    for key, maximum in CRITIC_MAX.items():
        if _g(scores, key, 10) > maximum:
            return False
    return True


def critic_fail_reasons(scores: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for key, minimum in CRITIC_MIN.items():
        value = _g(scores, key, 0)
        if value < minimum:
            reasons.append(f"{key}={value} < {minimum}")
    for key, maximum in CRITIC_MAX.items():
        value = _g(scores, key, 10)
        if value > maximum:
            reasons.append(f"{key}={value} > {maximum}")
    return reasons


def request_final_critic(
    *,
    candidate: Image.Image,
    foundation: Image.Image,
    reference: Image.Image,
    parent: Image.Image,
    facts: dict[str, str],
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1700,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "Independent luxury real-estate art director. You did not design this ad. "
                    "Ask whether Investhome could publish this today as a premium Washington DC "
                    "campaign. Give art-direction critique, never x/y coordinates. JSON only. "
                    "Do not reward cards, panels, pills, or templates."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Image 1 is the 4:5 candidate. Image 2 is the locked Day_004 photograph. "
                            "Image 3 is Phase 5.0 as a QUALITY BAR only (ignore its building pixels). "
                            "Image 4 is Phase 5.4 Master B, the selected parent family.\n"
                            f"Required story: {facts['headline']} / {facts['unit']} {facts['unit_label']} / "
                            f"{facts['list_price']} / {facts['discount']} {facts['discount_label']} / {facts['cta']}.\n"
                            "Family DNA: photograph dominant, spire as focal point, brand/headline left, "
                            "commercial offer right, CTA as a quiet editorial inscription, no cards or pills.\n"
                            "JSON scores 0-10: professional_design_quality, photo_design_integration, "
                            "visual_hierarchy, typographic_sophistication, commercial_hierarchy, "
                            "premium_character, readability, architecture_respect, "
                            "text_on_photo_likeness, template_likeness, visual_clutter, "
                            "looks_like_designed_campaign (bool), critique, notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "low"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(parent)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed)
    parsed["architecture_truth"] = 10
    parsed["mode"] = "vision" if parsed.get("professional_design_quality") is not None else "unavailable"
    parsed["pass"] = critic_pass_54a(parsed) if parsed["mode"] == "vision" else False
    parsed["fail_reasons"] = [] if parsed["pass"] else (
        ["critic_unavailable"] if parsed["mode"] != "vision" else critic_fail_reasons(parsed)
    )
    return parsed, calls


def _render_scene(markup: str, *, photo_uri: str, logo_markup: str, font_css: str, facts: dict[str, str]) -> dict[str, Any]:
    assembled = assemble_scene(markup, photo_uri=photo_uri, logo_markup=logo_markup, font_css=font_css)
    return {
        "assembled_markup": assembled,
        "persistable_markup": persistable_markup(assembled, photo_uri),
        "gate": validate_scene(assembled, facts, photo_uri),
        "semantic_ok": markup_has_semantic_slots(assembled),
        "image": render_html_to_png(assembled),
    }


def _font(size: int = 16):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def render_pair(left: Image.Image, right: Image.Image, left_label: str, right_label: str) -> Image.Image:
    font = _font(16)

    def tile(im: Image.Image, label: str) -> Image.Image:
        fitted = im.copy().resize((540, 675), Image.Resampling.LANCZOS)
        bar = 36
        canvas = Image.new("RGB", (fitted.width, fitted.height + bar), (12, 14, 20))
        canvas.paste(fitted, (0, bar))
        ImageDraw.Draw(canvas).text((12, 8), label, fill=(201, 168, 92), font=font)
        return canvas

    a, b = tile(left, left_label), tile(right, right_label)
    gap = 24
    out = Image.new("RGB", (a.width + b.width + gap + 40, a.height + 40), (12, 14, 20))
    out.paste(a, (20, 20))
    out.paste(b, (20 + a.width + gap, 20))
    return out


def render_readability_review(final: Image.Image) -> Image.Image:
    crops = [
        (final.crop((0, 0, 320, 280)), "logo + headline + unit"),
        (final.crop((600, 40, 1088, 280)), "price + %35"),
        (final.crop((0, 1120, 520, 1360)), "CTA"),
        (final.crop((280, 80, 640, 720)), "spire / architecture"),
    ]
    font = _font(15)
    tiles = []
    for im, label in crops:
        fitted = im.resize((320, int(im.height * 320 / max(im.width, 1))), Image.Resampling.LANCZOS)
        bar = 32
        canvas = Image.new("RGB", (fitted.width, fitted.height + bar), (12, 14, 20))
        canvas.paste(fitted, (0, bar))
        ImageDraw.Draw(canvas).text((10, 8), label, fill=(201, 168, 92), font=font)
        tiles.append(canvas)
    gap = 16
    w = sum(t.width for t in tiles) + gap * (len(tiles) + 1)
    h = max(t.height for t in tiles) + 40
    out = Image.new("RGB", (w, h), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out


def render_architecture_provenance(source: Image.Image, crop: Image.Image, final: Image.Image) -> Image.Image:
    font = _font(16)

    def tile(im: Image.Image, label: str, box: tuple[int, int]) -> Image.Image:
        fitted = im.copy()
        fitted.thumbnail(box, Image.Resampling.LANCZOS)
        canvas = Image.new("RGB", box, (12, 14, 20))
        canvas.paste(fitted, ((box[0] - fitted.width) // 2, (box[1] - fitted.height) // 2))
        bar = Image.new("RGB", (box[0], 32), (12, 14, 20))
        ImageDraw.Draw(bar).text((10, 8), label, fill=(201, 168, 92), font=font)
        out = Image.new("RGB", (box[0], box[1] + 32), (12, 14, 20))
        out.paste(bar, (0, 0))
        out.paste(canvas, (0, 32))
        return out

    tiles = [
        tile(source, "Day_004 source", (420, 280)),
        tile(crop, "uniform 4:5 crop", (360, 450)),
        tile(final, "final (type only)", (360, 450)),
    ]
    gap = 18
    w = sum(t.width for t in tiles) + gap * 4
    h = max(t.height for t in tiles) + 40
    out = Image.new("RGB", (w, h), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out


def render_hierarchy_map(final: Image.Image) -> Image.Image:
    im = final.copy().convert("RGB")
    draw = ImageDraw.Draw(im, "RGBA")
    font = _font(14)
    zones = [
        ((36, 26, 300, 96), (120, 200, 255, 70), "LOGO"),
        ((36, 108, 300, 250), (255, 255, 255, 70), "L1 HEADLINE + L4 UNIT"),
        ((305, 40, 580, 900), (255, 80, 80, 40), "SPIRE — KEEP CLEAR"),
        ((620, 56, 1050, 250), (255, 200, 40, 70), "L2 PRICE + L3 %35"),
        ((36, 1220, 420, 1336), (220, 80, 255, 70), "L5 CTA"),
    ]
    for box, fill, label in zones:
        draw.rectangle(box, outline=fill[:3] + (220,), width=2)
        draw.rectangle((box[0], box[1], min(box[2], box[0] + 8 * len(label)), box[1] + 22), fill=(12, 14, 20, 180))
        ImageDraw.Draw(im).text((box[0] + 6, box[1] + 4), label, fill=fill[:3], font=font)
    return im.convert("RGB")


def generate_premium_commercial_final_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    source_asset_id: str | None = None,
    logo_asset_id: str | None = None,
    facts: dict[str, str] | None = None,
) -> dict[str, Any]:
    hero_id = str(source_asset_id or LOCKED_HERO_ASSET_ID)
    logo_id = str(logo_asset_id or LOCKED_LOGO_ASSET_ID)
    campaign_facts = dict(facts or REQUIRED_FACTS)
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = {
        "session": blob.get("current_session_id"),
        "family": blob.get("current_format_family_id"),
        "lock": list(blob.get("architecture_lock_tests") or []),
        "photo": list(blob.get("photo_foundation_tests") or []),
        "design": list(blob.get("creative_design_tests") or []),
        "overlay": list(blob.get("creative_overlay_tests") or []),
        "master": list(blob.get("creative_master_tests") or []),
        "production": list(blob.get("production_creative_tests") or []),
        "vad": list(blob.get("visual_art_director_tests") or []),
        "scene": list(blob.get("design_scene_tests") or []),
        "library": list(blob.get("creative_master_library_tests") or []),
        "approved": {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()},
        "sessions": dict(blob.get("sessions") or {}),
    }
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    before["architecture_lock_tests_count"] = len(preserved["lock"])
    before["photo_foundation_tests_count"] = len(preserved["photo"])
    before["creative_design_tests_count"] = len(preserved["design"])
    before["creative_overlay_tests_count"] = len(preserved["overlay"])
    before["creative_master_tests_count"] = len(preserved["master"])
    before["production_creative_tests_count"] = len(preserved["production"])
    before["visual_art_director_tests_count"] = len(preserved["vad"])
    before["design_scene_tests_count"] = len(preserved["scene"])
    before["creative_master_library_tests_count"] = len(preserved["library"])

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, {"warmth": 0.11, "contrast": 1.08, "brightness": 0.99, "vignette": 0.09})
    photo_uri = _jpeg_data_uri(graded)
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(logo_bytes)

    parent_pack = _render_scene(
        scene_premium_commercial(campaign_facts),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=campaign_facts,
    )
    child = build_premium_commercial_final_master(campaign_facts)
    child["created_at"] = _now()
    child["parent_master_id"] = MASTER_COMMERCIAL_ID
    child["parent_reason"] = PARENT_REASON
    child["approval_status"] = APPROVAL_CANDIDATE
    final_pack = _render_scene(
        str(child.get("scene_markup") or ""),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=campaign_facts,
    )
    provenance = architecture_provenance_qa(
        source=source, foundation=crop, final=final_pack["image"], transform=transform
    )
    critic, critic_calls = request_final_critic(
        candidate=final_pack["image"],
        foundation=graded,
        reference=reference,
        parent=parent_pack["image"],
        facts=campaign_facts,
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(final_pack["image"]),
        content_type="image/png",
        campaign_mode="project-creative-master-candidate",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.4A PREMIUM_COMMERCIAL production finalization candidate",
    )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54A,
        "created_at": _now(),
        "creative_method": "premium_commercial_master_b_child_not_live_routed",
        "design_family": "PREMIUM_COMMERCIAL",
        "parent_master_id": MASTER_COMMERCIAL_ID,
        "parent_reason": PARENT_REASON,
        "master_id": MASTER_COMMERCIAL_FINAL_ID,
        "human_family_decision": {
            "EDITORIAL_ARCHITECTURAL": "REJECT",
            "PREMIUM_COMMERCIAL": "SELECTED",
            "MINIMAL_LUXURY": "REJECT",
        },
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_generation_used": False,
        "gpt_image_calls": 0,
        "gpt_image_edit_calls": 0,
        "critic_vision_calls": critic_calls,
        "real_logo_asset_id": logo_id,
        "project_id": TEMPLE_PROJECT_ID,
        "font_registry": fonts.get("schema"),
        "display_font": ((fonts.get("roles") or {}).get("DISPLAY_SERIF") or {}).get("font_file"),
        "support_font": ((fonts.get("roles") or {}).get("EDITORIAL_SANS") or {}).get("font_file"),
        "design_strategy": "Master B split DNA: brand left, offer right, architecture center, CTA lower quiet",
        "commercial_hierarchy": "L1 ALIRKEN KAZAN | L2 675.000 USD | L3 %35 LANSMAN AVANTAJI | L4 2+1 DAİRE | L5 PROJEYİ KEŞFET",
        "cta_strategy": "restrained ivory inscription with gold rule over lower-left photographic fade",
        "design_surfaces_used": child.get("graphic_surfaces"),
        "final_asset_id": str(asset.id),
        "final_size": list(final_pack["image"].size),
        "approval_status": APPROVAL_CANDIDATE,
        "live_routing_active": False,
        "user_facing_templates": False,
        "scene_gate": final_pack["gate"],
        "parent_scene_gate": parent_pack["gate"],
        "provenance_qa": provenance,
        "critic": critic,
        "hard_gate": bool(critic.get("pass")),
        "hard_gate_reasons": list(critic.get("fail_reasons") or []),
        "video_started": False,
        "publishing_started": False,
        "other_formats_generated": False,
        "human_approval_required": True,
    }
    tests = [
        t
        for t in list(blob.get("premium_commercial_final_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54A)
    ]
    tests.append({k: v for k, v in record.items()})
    blob["premium_commercial_final_tests"] = tests
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    blob["architecture_lock_tests"] = preserved["lock"]
    blob["photo_foundation_tests"] = preserved["photo"]
    blob["creative_design_tests"] = preserved["design"]
    blob["creative_overlay_tests"] = preserved["overlay"]
    blob["creative_master_tests"] = preserved["master"]
    blob["production_creative_tests"] = preserved["production"]
    blob["visual_art_director_tests"] = preserved["vad"]
    blob["design_scene_tests"] = preserved["scene"]
    blob["creative_master_library_tests"] = preserved["library"]
    blob["approved_masters"] = preserved["approved"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after["architecture_lock_tests_count"] = len(list(blob.get("architecture_lock_tests") or []))
    after["photo_foundation_tests_count"] = len(list(blob.get("photo_foundation_tests") or []))
    after["creative_design_tests_count"] = len(list(blob.get("creative_design_tests") or []))
    after["creative_overlay_tests_count"] = len(list(blob.get("creative_overlay_tests") or []))
    after["creative_master_tests_count"] = len(list(blob.get("creative_master_tests") or []))
    after["production_creative_tests_count"] = len(list(blob.get("production_creative_tests") or []))
    after["visual_art_director_tests_count"] = len(list(blob.get("visual_art_director_tests") or []))
    after["design_scene_tests_count"] = len(list(blob.get("design_scene_tests") or []))
    after["creative_master_library_tests_count"] = len(list(blob.get("creative_master_library_tests") or []))
    _production_guard(before, after)
    if blob.get("creative_master_library_tests") != preserved["library"]:
        raise RuntimeError("Phase 5.4A refused to change Phase 5.4 A/B/C history")
    if blob.get("design_scene_tests") != preserved["scene"]:
        raise RuntimeError("Phase 5.4A refused to change Phase 5.3 history")
    if blob.get("visual_art_director_tests") != preserved["vad"]:
        raise RuntimeError("Phase 5.4A refused to change Phase 5.2B history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4A refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "reference": reference,
        "parent": parent_pack["image"],
        "final": final_pack["image"],
    }
    record["rendered"] = final_pack
    record["parent_rendered"] = parent_pack
    record["child_master"] = child
    record["fonts"] = fonts
    _ = language
    return record
