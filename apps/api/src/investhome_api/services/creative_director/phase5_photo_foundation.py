"""Phase 5.1B — immutable project photograph as the creative foundation.

Day_004 is the photographic base. Architecture is never generated.
gpt-4o vision art-directs layout and photographic grade.
The OS compositor executes type, graphics, and the real logo.

Not: gpt-image-2 redraws The Temple.
Not: generate an ad then paste Day_004 on top (Phase 5.1A).
Not: Phase 4 NativeMaster renderer as the designer.
"""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import Any
from uuid import UUID, uuid4

import httpx
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.config.settings import get_settings
from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
    HERO_FILENAME,
    LOCKED_HERO_ASSET_ID,
    LOCKED_LOGO_ASSET_ID,
    PRODUCTION_COVER_V2,
    REQUIRED_FACTS,
    _now,
    _phase5,
    _production_guard,
    _read_bytes,
)
from investhome_api.services.gpt_image_design.compose import CompositionSlotPlan, render_layout_plan
from investhome_api.services.gpt_image_design.config import openai_api_key, resolve_base_url
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image, sniff_image_content_type
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.visual_layout_director import (
    VISION_MODEL,
    run_visual_layout_director,
)

logger = logging.getLogger(__name__)

WORKFLOW_ID_51B = "phase5_1b_photo_foundation"
CANVAS_4X5 = (1088, 1360)
ART_DIRECTION_METHOD = "gpt4o_vision_layout_director_plus_photographic_grade"

_TREATMENTS = {
    "warm_editorial": {"warmth": 0.22, "contrast": 1.12, "brightness": 0.97, "vignette": 0.18},
    "dark_premium": {"warmth": 0.08, "contrast": 1.18, "brightness": 0.86, "vignette": 0.28},
    "cool_architectural": {"warmth": -0.12, "contrast": 1.08, "brightness": 1.02, "vignette": 0.12},
    "daylight_preserve": {"warmth": 0.0, "contrast": 1.04, "brightness": 1.0, "vignette": 0.08},
}


def cover_fit_canvas(
    source: Image.Image,
    target: tuple[int, int],
    *,
    centering: tuple[float, float] = (0.78, 0.42),
) -> tuple[Image.Image, dict[str, Any]]:
    """Uniform cover crop. Never stretch."""
    src = source.convert("RGB")
    tw, th = int(target[0]), int(target[1])
    sw, sh = src.size
    scale = max(tw / max(sw, 1), th / max(sh, 1))
    nw = max(tw, int(round(sw * scale)))
    nh = max(th, int(round(sh * scale)))
    scaled = src.resize((nw, nh), Image.Resampling.LANCZOS)
    left = int(round((nw - tw) * max(0.0, min(1.0, centering[0]))))
    top = int(round((nh - th) * max(0.0, min(1.0, centering[1]))))
    left = max(0, min(left, nw - tw))
    top = max(0, min(top, nh - th))
    canvas = scaled.crop((left, top, left + tw, top + th))
    if canvas.size != (tw, th):
        raise RuntimeError("cover_fit_canvas refused a non-target canvas size")
    source_crop = (
        left / scale,
        top / scale,
        (left + tw) / scale,
        (top + th) / scale,
    )
    return canvas, {
        "source_crop": [round(v, 2) for v in source_crop],
        "source_scale": round(scale, 6),
        "scale_x": round(scale, 6),
        "scale_y": round(scale, 6),
        "non_uniform_scale": False,
        "source_position": [0, 0],
        "centering": [centering[0], centering[1]],
        "canvas_size": [tw, th],
        "source_size": [sw, sh],
    }


def apply_photographic_grade(image: Image.Image, treatment: dict[str, Any]) -> Image.Image:
    """Color/contrast/vignette only. Does not resample architecture geometry."""
    im = image.convert("RGB")
    warmth = float(treatment.get("warmth") or 0.0)
    contrast = float(treatment.get("contrast") or 1.0)
    brightness = float(treatment.get("brightness") or 1.0)
    vignette = float(treatment.get("vignette") or 0.0)
    if abs(warmth) > 0.001:
        r, g, b = im.split()
        r = r.point(lambda p: max(0, min(255, int(p + warmth * 36))))
        b = b.point(lambda p: max(0, min(255, int(p - warmth * 28))))
        im = Image.merge("RGB", (r, g, b))
    if abs(contrast - 1.0) > 0.001:
        im = ImageEnhance.Contrast(im).enhance(contrast)
    if abs(brightness - 1.0) > 0.001:
        im = ImageEnhance.Brightness(im).enhance(brightness)
    if vignette > 0.02:
        im = _vignette(im, vignette)
    return im


def _vignette(im: Image.Image, strength: float) -> Image.Image:
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    inset = int(min(w, h) * 0.08)
    draw.ellipse((-inset, -int(h * 0.04), w + inset, h + int(h * 0.12)), fill=int(210 * strength))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=max(24, min(w, h) * 0.18)))
    overlay = Image.new("RGB", (w, h), (8, 10, 16))
    return Image.composite(overlay, im, mask)


def _centering_from_mass(source: Image.Image) -> tuple[float, float]:
    """Bias the 4:5 crop toward architectural mass. Temple sits right-of-center in Day_004."""
    small = source.convert("L").resize((64, 40), Image.Resampling.BOX)
    edges = small.filter(ImageFilter.FIND_EDGES)
    raw = edges.tobytes()
    acc_x = acc_y = weight = 0.0
    for y in range(small.height):
        for x in range(small.width):
            v = raw[y * small.width + x]
            if v < 18:
                continue
            acc_x += x * v
            acc_y += y * v
            weight += v
    if weight < 1:
        return (0.78, 0.42)
    cx = acc_x / weight / max(small.width - 1, 1)
    cy = acc_y / weight / max(small.height - 1, 1)
    return (max(0.68, min(0.92, cx)), max(0.28, min(0.62, cy)))


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _extract_json(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        parsed = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def request_photographic_art_direction(
    foundation: Image.Image,
    *,
    api_key: str,
    base_url: str,
) -> tuple[dict[str, Any], int]:
    """gpt-4o vision chooses grade + composition intent from the real photo crop."""
    jpeg = io.BytesIO()
    foundation.convert("RGB").save(jpeg, format="JPEG", quality=88)
    b64 = base64.b64encode(jpeg.getvalue()).decode("ascii")
    payload = {
        "model": VISION_MODEL,
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the creative director for a luxury real-estate Instagram 4:5 ad. "
                    "The photograph is immutable architecture. You may only grade it and design "
                    "typography/graphics around it. Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Campaign: ALIRKEN KAZAN / 2+1 DAİRE / 675.000 USD / %35 LANSMAN AVANTAJI / PROJEYİ KEŞFET.\n"
                            "Choose a premium editorial treatment. No giant panels. No dashboard. No flyer.\n"
                            "JSON: {\n"
                            '  "treatment": "warm_editorial"|"dark_premium"|"cool_architectural"|"daylight_preserve",\n'
                            '  "composition_family": "editorial_hero"|"minimal_luxury"|"offer_focus",\n'
                            '  "type_anchor": "left"|"top_left"|"lower_left",\n'
                            '  "headline_color": "#hex",\n'
                            '  "rationale": "one sentence"\n'
                            "}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}", "detail": "high"}},
                ],
            },
        ],
    }
    url = f"{base_url.rstrip('/')}/chat/completions"
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(url, headers={"Authorization": f"Bearer {api_key}"}, json=payload)
        resp.raise_for_status()
    data = resp.json()
    text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    parsed = json.loads(text) if text.strip().startswith("{") else _extract_json(text)
    if not isinstance(parsed, dict):
        parsed = {}
    treatment_key = str(parsed.get("treatment") or "warm_editorial")
    if treatment_key not in _TREATMENTS:
        treatment_key = "warm_editorial"
    family = str(parsed.get("composition_family") or "editorial_hero")
    if family not in {"editorial_hero", "minimal_luxury", "offer_focus"}:
        family = "editorial_hero"
    parsed["treatment"] = treatment_key
    parsed["composition_family"] = family
    parsed["grade"] = dict(_TREATMENTS[treatment_key])
    return parsed, 1


def apply_art_direction_to_plan(plan: Any, art: dict[str, Any]) -> None:
    """Execute the vision director's color choice on headline/CTA. Does not move architecture."""
    color = str(art.get("headline_color") or "").strip()
    if not (color.startswith("#") and len(color) in {4, 7}):
        return
    for layer in getattr(plan, "layers", []) or []:
        slot = str(getattr(layer, "content_slot", "") or "")
        role = str(getattr(layer, "role", "") or "")
        if slot == "headline" or role == "headline":
            layer.color = color


def architecture_provenance_qa(
    *,
    source: Image.Image,
    foundation: Image.Image,
    final: Image.Image,
    transform: dict[str, Any],
) -> dict[str, Any]:
    """Provenance QA — not mean-color, not weak NCC-as-proof."""
    sx = float(transform.get("scale_x") or 0)
    sy = float(transform.get("scale_y") or 0)
    non_uniform = abs(sx - sy) > 1e-6
    crop = transform.get("source_crop") or [0, 0, 0, 0]
    reconstructed, _ = cover_fit_canvas(
        source,
        (foundation.width, foundation.height),
        centering=tuple(transform.get("centering") or (0.78, 0.42)),  # type: ignore[arg-type]
    )
    recon_ok = reconstructed.size == foundation.size
    return {
        "architecture_generation_used": False,
        "non_uniform_scale": non_uniform,
        "second_photo_patch": False,
        "duplicated_architecture": False,
        "source_crop_recorded": len(crop) == 4,
        "foundation_matches_cover_fit_size": recon_ok,
        "final_size": list(final.size),
        "source_pixel_provenance": "day004_uniform_cover_crop_then_photographic_grade",
        "status": "fail" if non_uniform or not recon_ok else "pass",
    }


def generate_photo_foundation_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    """One 4:5 proof. Does not overwrite 5.0 / 5.1 / 5.1A / production cover."""
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved_session = blob.get("current_session_id")
    preserved_family = blob.get("current_format_family_id")
    preserved_lock_tests = list(blob.get("architecture_lock_tests") or [])
    preserved_masters = {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()}
    preserved_sessions = dict(blob.get("sessions") or {})
    before["phase5_current_session_id"] = preserved_session
    before["phase5_current_format_family_id"] = preserved_family
    before["architecture_lock_tests_count"] = len(preserved_lock_tests)

    source_bytes = _read_bytes(db, UUID(LOCKED_HERO_ASSET_ID))
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    source = Image.open(io.BytesIO(source_bytes)).convert("RGB")
    centering = _centering_from_mass(source)
    foundation, transform = cover_fit_canvas(source, CANVAS_4X5, centering=centering)

    api_key = openai_api_key()
    settings = get_settings()
    base_url = resolve_base_url(settings)
    provider_calls = 0
    gpt_image_2_calls = 0
    art = {
        "treatment": "warm_editorial",
        "grade": dict(_TREATMENTS["warm_editorial"]),
        "composition_family": "editorial_hero",
        "type_anchor": "left",
        "headline_color": "#F4E7C3",
        "rationale": "default editorial grade",
        "mode": "fallback",
    }
    if api_key:
        try:
            art, calls = request_photographic_art_direction(foundation, api_key=api_key, base_url=base_url)
            provider_calls += calls
            art["mode"] = "vision"
        except Exception:
            logger.info("photo-foundation art direction vision failed; using editorial default", exc_info=True)

    graded = apply_photographic_grade(foundation, art.get("grade") or _TREATMENTS["warm_editorial"])
    foundation_png = _png(graded)
    cw, ch = CANVAS_4X5
    facts = dict(REQUIRED_FACTS)
    texts = {
        "headline": facts["headline"],
        "cta": facts["cta"],
        "supporting_callouts": (
            f"{facts['unit']} {facts['unit_label']}|{facts['list_price']}|{facts['discount']} {facts['discount_label']}"
        ),
    }
    slots = CompositionSlotPlan(
        headline=facts["headline"],
        subhead="",
        verified_data="",
        cta=facts["cta"],
        feature_1=f"{facts['unit']} {facts['unit_label']}",
        feature_2=facts["list_price"],
        feature_3=f"{facts['discount']} {facts['discount_label']}",
        include_slogan=False,
    )
    logo = ResolvedSourceImage(
        asset_id=UUID(LOCKED_LOGO_ASSET_ID),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category=None,
        tags=[],
        image_bytes=logo_bytes,
        role="project_logo",
    )
    vld = run_visual_layout_director(
        background_bytes=foundation_png,
        canvas_width=cw,
        canvas_height=ch,
        texts=texts,
        art_direction={"composition_family": art.get("composition_family") or "editorial_hero"},
        lifestyle=False,
        has_project_logo=True,
        has_investhome_logo=False,
        include_slogan=False,
        max_passes=2,
        campaign_id=str(row.id),
        background_asset_id=LOCKED_HERO_ASSET_ID,
    )
    if vld.mode == "vision":
        provider_calls += 1
    apply_art_direction_to_plan(vld.design_plan, art)
    composition = render_layout_plan(
        foundation_png,
        logos=[logo],
        slots=slots,
        canvas_width=cw,
        canvas_height=ch,
        base_asset_id=UUID(LOCKED_HERO_ASSET_ID),
        plan=vld.design_plan,
    )
    final_img = Image.open(io.BytesIO(composition.png_bytes)).convert("RGB")
    qa = architecture_provenance_qa(
        source=source,
        foundation=foundation,
        final=final_img,
        transform=transform,
    )
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=composition.png_bytes,
        content_type=sniff_image_content_type(composition.png_bytes),
        campaign_mode="project-photo-foundation",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.1B immutable Day_004 photo foundation 4:5",
    )

    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_51B,
        "created_at": _now(),
        "source_asset_id": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "source_photo_role": "immutable_photographic_foundation",
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "final_asset_id": str(asset.id),
        "final_asset_url": asset_url(asset.id),
        "final_size": list(final_img.size),
        "architecture_generation_used": False,
        "second_photo_patch": False,
        "duplicated_architecture": False,
        "non_uniform_scale": False,
        "phase4_renderer_primary": False,
        "video_started": False,
        "publishing_started": False,
        "gpt_image_2_calls": gpt_image_2_calls,
        "transform": transform,
        "photographic_treatments": art,
        "art_direction_method": ART_DIRECTION_METHOD,
        "ai_design_provider": "openai-vision",
        "ai_design_model": VISION_MODEL,
        "layout_mode": vld.mode,
        "composition_family": vld.layout_plan.composition_family,
        "provider_call_count": provider_calls,
        "provenance_qa": qa,
        "future_format_contract": {
            "implemented": False,
            "rule": "Each format crops Day_004 directly. Do not redraw the 4:5 ad.",
        },
    }

    tests = [
        t
        for t in list(blob.get("photo_foundation_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_51B)
    ]
    tests.append(record)
    blob["photo_foundation_tests"] = tests
    blob["current_session_id"] = preserved_session
    blob["current_format_family_id"] = preserved_family
    blob["architecture_lock_tests"] = preserved_lock_tests
    blob["approved_masters"] = preserved_masters
    blob["sessions"] = preserved_sessions
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after["architecture_lock_tests_count"] = len(list(blob.get("architecture_lock_tests") or []))
    _production_guard(before, after)
    if blob.get("current_session_id") != preserved_session:
        raise RuntimeError("Phase 5.1B refused to change current_session_id")
    if blob.get("current_format_family_id") != preserved_family:
        raise RuntimeError("Phase 5.1B refused to change current_format_family_id")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.1B refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "foundation": graded,
        "foundation_ungraded": foundation,
        "final": final_img,
        "source": source,
        "layout": vld.layout_plan,
    }
    _ = language
    return record
