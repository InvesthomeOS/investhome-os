"""Phase 5.1C — AI creative design over the locked 5.1B photo foundation.

Architecture preservation is not revisited. This module designs the advertisement.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.creative_art_direction import (
    CreativeArtDirectionPlan,
    SceneAnalysis,
    placement_box,
    protect_from_spire,
    quality_gate,
    request_creative_art_direction,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    WORKFLOW_ID_51B,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
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
from investhome_api.services.gpt_image_design.compose import resolve_turkish_font
from investhome_api.services.gpt_image_design.editorial_compose import (
    apply_feathered_gradient_field,
    apply_local_blur_field,
    apply_local_tonal_field,
    apply_logo_ground,
    contrast_ratio,
    draw_rule,
    draw_tracked_text,
    inspect_font_inventory,
    opaque_panel_coverage,
    paste_logo,
    region_mean_rgb,
)
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_51C = "phase5_1c_creative_design"
GOLD = "#C4A35A"
IVORY = "#F4EFE6"


def _facts() -> dict[str, str]:
    return dict(REQUIRED_FACTS)


def _px_png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def _ink_or_ivory(image: Image.Image, box: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    mean = region_mean_rgb(image, box)
    if contrast_ratio(mean, (22, 28, 40)) >= contrast_ratio(mean, (244, 239, 230)):
        return (22, 28, 40, 255)
    return (244, 239, 230, 255)


def _ensure_min_logo_box(box: tuple[int, int, int, int], canvas: tuple[int, int], column: str) -> tuple[int, int, int, int]:
    cw, ch = canvas
    x0, y0, x1, y1 = box
    min_w = int(cw * 0.24)
    min_h = int(ch * 0.09)
    if x1 - x0 < min_w or y1 - y0 < min_h:
        if column == "right":
            x1 = cw - 48
            x0 = x1 - min_w
        else:
            x0 = 48
            x1 = x0 + min_w
        y0 = max(36, y0)
        y1 = y0 + min_h
    if y0 > ch * 0.45:
        y0 = 40
        y1 = y0 + max(min_h, y1 - y0)
        if column == "right":
            x1 = cw - 48
            x0 = x1 - max(min_w, x1 - x0)
        else:
            x0 = 48
            x1 = x0 + max(min_w, x1 - x0)
    return x0, y0, x1, y1


def render_creative_plan(
    foundation: Image.Image,
    *,
    plan: CreativeArtDirectionPlan,
    scene: SceneAnalysis,
    logo: ResolvedSourceImage,
    facts: dict[str, str],
) -> dict[str, Any]:
    """Execute the art-direction plan. Does not invent a competing design."""
    canvas_size = (foundation.width, foundation.height)
    graded = apply_photographic_grade(foundation, plan.photographic_grade or {})
    work = graded.convert("RGBA")
    used: list[str] = []

    headline_box = protect_from_spire(placement_box(plan, "headline", canvas_size), scene, canvas_size)
    commercial_box = protect_from_spire(placement_box(plan, "commercial", canvas_size), scene, canvas_size)
    logo_box = _ensure_min_logo_box(
        protect_from_spire(placement_box(plan, "logo", canvas_size), scene, canvas_size),
        canvas_size,
        plan.type_column,
    )
    cta_box = protect_from_spire(placement_box(plan, "cta", canvas_size), scene, canvas_size)
    boxes = {"headline": headline_box, "commercial": commercial_box, "logo": logo_box, "cta": cta_box}

    # Execute readability/negative-space strategy: a dissolving type-column field,
    # not a template panel. Side comes from THIS photograph's plan.
    work = apply_feathered_gradient_field(
        work,
        side=plan.type_column or "left",
        color="#12161E",
        width_frac=0.44,
        max_alpha=0.38,
        feather=0.72,
    )
    used.append("feathered_gradient")
    work = apply_local_tonal_field(
        work, headline_box, color="#10141C", max_alpha=0.22, feather=0.65
    )
    work = apply_local_blur_field(work, commercial_box, radius=10, strength=0.42, feather=0.62)
    work = apply_local_tonal_field(
        work, commercial_box, color="#10141C", max_alpha=0.30, feather=0.58
    )
    work = apply_logo_ground(work, logo_box, color=IVORY, max_alpha=0.24)
    used.extend(["local_tonal", "local_blur", "logo_ground"])
    hx0, hy0, hx1, _ = headline_box
    work = draw_rule(work, x=hx0, y=hy0 - 8, length=min(180, hx1 - hx0), color=GOLD, width=1)
    used.append("rule")

    for surface in plan.surfaces or []:
        kind = str(surface.get("kind") or "")
        if kind in {"feathered_gradient", "local_blur", "logo_ground"}:
            continue
        if kind == "local_tonal":
            region = str(surface.get("region") or "commercial")
            work = apply_local_tonal_field(
                work,
                boxes.get(region) or commercial_box,
                color=str(surface.get("color") or "#10141C"),
                max_alpha=min(0.42, float(surface.get("max_alpha") or 0.28)),
                feather=float(surface.get("feather") or 0.6),
            )
            used.append("local_tonal")
        elif kind == "logo_ground":
            work = apply_logo_ground(
                work,
                logo_box,
                color=str(surface.get("color") or IVORY),
                max_alpha=min(0.3, float(surface.get("max_alpha") or 0.22)),
            )
            used.append("logo_ground")
        elif kind == "rule":
            x0, y0, x1, _y1 = commercial_box
            work = draw_rule(
                work, x=x0, y=y0 - 10, length=min(220, x1 - x0), color=str(surface.get("color") or GOLD), width=1
            )
            used.append("rule")

    work, logo_meta = paste_logo(work, logo, logo_box)
    if logo_meta.get("placed"):
        used.append("real_logo")

    draw = ImageDraw.Draw(work)
    hx0, hy0, hx1, _hy1 = headline_box
    headline_w = max(80, hx1 - hx0)
    line1 = resolve_turkish_font(bold=True, size=min(78, max(52, headline_w // 7)), family="serif")
    line2 = resolve_turkish_font(bold=True, size=min(96, max(64, headline_w // 6)), family="serif")
    words = str(facts.get("headline") or "ALIRKEN KAZAN").split()
    first = words[0] if words else "ALIRKEN"
    second = " ".join(words[1:]) if len(words) > 1 else ""
    w1, h1 = draw_tracked_text(
        draw, first, font=line1, xy=(hx0, hy0), fill=_ink_or_ivory(work, headline_box), tracking_em=0.04
    )
    if second:
        draw_tracked_text(
            draw,
            second,
            font=line2,
            xy=(hx0, hy0 + h1 + 4),
            fill=(196, 163, 90, 255),
            tracking_em=0.08,
        )

    cx0, cy0, _cx1, _cy1 = commercial_box
    unit = f"{facts.get('unit')} {facts.get('unit_label')}"
    price = facts.get("list_price") or ""
    advantage = f"{facts.get('discount')} {facts.get('discount_label')}"
    unit_font = resolve_turkish_font(bold=False, size=22, family="sans")
    price_font = resolve_turkish_font(bold=True, size=44, family="serif")
    adv_font = resolve_turkish_font(bold=True, size=26, family="sans")
    ivory = (244, 239, 230, 255)
    gold = (196, 163, 90, 255)
    _uw, uh = draw_tracked_text(draw, unit, font=unit_font, xy=(cx0, cy0), fill=ivory, tracking_em=0.18)
    _pw, ph = draw_tracked_text(draw, price, font=price_font, xy=(cx0, cy0 + uh + 10), fill=ivory, tracking_em=0.02)
    draw_tracked_text(draw, advantage, font=adv_font, xy=(cx0, cy0 + uh + ph + 22), fill=gold, tracking_em=0.12)

    tx0, ty0, _tx1, _ty1 = cta_box
    cta_font = resolve_turkish_font(bold=True, size=22, family="sans")
    label = facts.get("cta") or ""
    pad_x, pad_y = 22, 14
    tw, th = draw_tracked_text(draw, label, font=cta_font, xy=(tx0 + pad_x, ty0 + pad_y), fill=gold, tracking_em=0.14)
    box = (tx0, ty0, tx0 + tw + pad_x * 2, ty0 + th + pad_y * 2)
    ImageDraw.Draw(work).rounded_rectangle(box, radius=2, outline=(196, 163, 90, 220), width=1)
    boxes["cta"] = box

    coverage = opaque_panel_coverage(work, graded)
    fonts = inspect_font_inventory()
    return {
        "image": work.convert("RGB"),
        "graded": graded.convert("RGB"),
        "boxes": boxes,
        "logo_meta": logo_meta,
        "capabilities_used": used,
        "panel_coverage": coverage,
        "fonts": fonts,
        "headline_metrics": {"line1_w": w1, "line1_h": h1},
    }


def generate_creative_design_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
) -> dict[str, Any]:
    """One 4:5 design proof. Does not overwrite 5.0 / 5.1 / 5.1A / 5.1B / production cover."""
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved_session = blob.get("current_session_id")
    preserved_family = blob.get("current_format_family_id")
    preserved_lock_tests = list(blob.get("architecture_lock_tests") or [])
    preserved_photo = list(blob.get("photo_foundation_tests") or [])
    preserved_masters = {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()}
    preserved_sessions = dict(blob.get("sessions") or {})
    before["phase5_current_session_id"] = preserved_session
    before["phase5_current_format_family_id"] = preserved_family
    before["architecture_lock_tests_count"] = len(preserved_lock_tests)
    before["photo_foundation_tests_count"] = len(preserved_photo)

    source_bytes = _read_bytes(db, UUID(LOCKED_HERO_ASSET_ID))
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    source = Image.open(io.BytesIO(source_bytes)).convert("RGB")
    centering = _centering_from_mass(source)
    foundation, transform = cover_fit_canvas(source, CANVAS_4X5, centering=centering)
    facts = _facts()
    logo = ResolvedSourceImage(
        asset_id=UUID(LOCKED_LOGO_ASSET_ID),
        filename="IH_DC_TMP_001_Logo_Primary.svg",
        content_type="image/svg+xml",
        folder_category=None,
        tags=[],
        image_bytes=logo_bytes,
        role="project_logo",
    )

    provider_calls = 0
    scene, plan, calls = request_creative_art_direction(foundation, facts=facts)
    provider_calls += calls
    if plan.created_before_render is not True:
        raise RuntimeError("Art direction plan must exist before composition")
    rendered = render_creative_plan(foundation, plan=plan, scene=scene, logo=logo, facts=facts)
    provenance = architecture_provenance_qa(
        source=source,
        foundation=foundation,
        final=rendered["image"],
        transform=transform,
    )
    gate = quality_gate(
        image=rendered["image"],
        foundation=rendered["graded"],
        plan=plan,
        scene=scene,
        boxes=rendered["boxes"],
        logo_meta=rendered["logo_meta"],
        facts=facts,
        panel_coverage=rendered["panel_coverage"],
    )
    retries = 0
    if gate["status"] != "pass":
        retries = 1
        scene2, plan2, calls2 = request_creative_art_direction(
            foundation, facts=facts, retry_feedback="; ".join(gate.get("failures") or [])
        )
        provider_calls += calls2
        rendered2 = render_creative_plan(foundation, plan=plan2, scene=scene2, logo=logo, facts=facts)
        gate2 = quality_gate(
            image=rendered2["image"],
            foundation=rendered2["graded"],
            plan=plan2,
            scene=scene2,
            boxes=rendered2["boxes"],
            logo_meta=rendered2["logo_meta"],
            facts=facts,
            panel_coverage=rendered2["panel_coverage"],
        )
        pick_second = gate2["status"] == "pass" or len(gate2.get("failures") or []) < len(gate.get("failures") or [])
        if pick_second:
            scene, plan, rendered, gate = scene2, plan2, rendered2, gate2

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_px_png(rendered["image"]),
        content_type="image/png",
        campaign_mode="project-creative-design",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.1C AI creative design over Day_004 4:5",
    )

    record = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_51C,
        "created_at": _now(),
        "source_asset_id": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "architecture_generation_used": False,
        "photo_foundation_method": "phase5_1b_locked_cover_fit_grade",
        "locked_51b_workflow": WORKFLOW_ID_51B,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "final_asset_id": str(asset.id),
        "final_asset_url": asset_url(asset.id),
        "final_size": list(rendered["image"].size),
        "second_photo_patch": False,
        "duplicated_architecture": False,
        "non_uniform_scale": False,
        "phase4_renderer_primary": False,
        "video_started": False,
        "publishing_started": False,
        "gpt_image_2_calls": 0,
        "art_direction_retries": retries,
        "transform": transform,
        "plan": plan.to_dict(),
        "scene": scene.to_dict(),
        "gate": gate,
        "provenance_qa": provenance,
        "ai_design_provider": "openai-vision",
        "ai_design_model": VISION_MODEL,
        "art_direction_plan_id": plan.plan_id,
        "capabilities_used": rendered["capabilities_used"],
        "fonts": rendered["fonts"],
        "provider_call_count": provider_calls,
        "boxes": {k: list(v) for k, v in rendered["boxes"].items()},
    }

    tests = [
        t
        for t in list(blob.get("creative_design_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_51C)
    ]
    tests.append(record)
    blob["creative_design_tests"] = tests
    blob["current_session_id"] = preserved_session
    blob["current_format_family_id"] = preserved_family
    blob["architecture_lock_tests"] = preserved_lock_tests
    blob["photo_foundation_tests"] = preserved_photo
    blob["approved_masters"] = preserved_masters
    blob["sessions"] = preserved_sessions
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after["architecture_lock_tests_count"] = len(list(blob.get("architecture_lock_tests") or []))
    after["photo_foundation_tests_count"] = len(list(blob.get("photo_foundation_tests") or []))
    _production_guard(before, after)
    if blob.get("current_session_id") != preserved_session:
        raise RuntimeError("Phase 5.1C refused to change current_session_id")
    if blob.get("current_format_family_id") != preserved_family:
        raise RuntimeError("Phase 5.1C refused to change current_format_family_id")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.1C refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "foundation": foundation,
        "graded": rendered["graded"],
        "final": rendered["image"],
        "scene": scene,
        "plan": plan,
    }
    _ = language
    return record
