"""Phase 5.5 — approved master lock + natural-language revision proof.

Test A only: PRICE_REVISION. VISUAL_REPLACE architecture is ready, not executed.
Does not redesign 5.4A-R1. Does not use GPT Image. Does not activate routing.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

from PIL import Image, ImageChops, ImageDraw
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.services.creative_director.approved_creative_master import (
    HUMAN_APPROVED,
    append_revision,
    build_approved_creative_master,
    commercial_mutable_box,
    restore_parent_scene,
)
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import (
    APPROVED_R1_ASSET_ID,
    MASTER_COMMERCIAL_R1_ID,
    MASTER_PRICE_REVISION_V2_ID,
    markup_has_semantic_slots,
    scene_premium_commercial_price_revision,
    scene_premium_commercial_r1,
)
from investhome_api.services.creative_director.creative_revision_controller import (
    PRICE_REVISION,
    TEST_A_INSTRUCTION,
    build_revision_intent,
    parse_price_revision,
    plan_visual_replace,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
    font_face_css,
    inline_logo_svg,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import (
    _png,
    _render_scene,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_workflow import (
    CTX_KEY,
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

WORKFLOW_ID_55 = "phase5_5_master_revision"
LOCKED_CROPS = {
    "logo": (40, 30, 200, 100),
    "headline_unit": (40, 112, 300, 252),
    "cta": (40, 1188, 520, 1260),
    "architecture": (360, 360, 720, 980),
}

_VISUAL_REPLACE_INSTRUCTION = (
    "Bu görsel yerine Media Library’deki diğer onaylı dış cephe görselini kullan. "
    "Başka hiçbir şeyi değiştirme."
)
_HISTORY_KEYS = (
    ("architecture_lock_tests", "lock"),
    ("photo_foundation_tests", "photo"),
    ("creative_design_tests", "design"),
    ("creative_overlay_tests", "overlay"),
    ("creative_master_tests", "master"),
    ("production_creative_tests", "production"),
    ("visual_art_director_tests", "vad"),
    ("design_scene_tests", "scene"),
    ("creative_master_library_tests", "library"),
    ("premium_commercial_final_tests", "final54a"),
    ("premium_commercial_r1_tests", "r1"),
)


def _mean_channel_delta(a: Image.Image, b: Image.Image) -> float:
    if a.size != b.size:
        return 255.0
    tiny_a = a.convert("RGB").resize((1, 1), Image.Resampling.BOX)
    tiny_b = b.convert("RGB").resize((1, 1), Image.Resampling.BOX)
    pa, pb = tiny_a.getpixel((0, 0)), tiny_b.getpixel((0, 0))
    return (abs(pa[0] - pb[0]) + abs(pa[1] - pb[1]) + abs(pa[2] - pb[2])) / 3.0


def _changed_fraction(a: Image.Image, b: Image.Image, *, threshold: int = 12) -> float:
    if a.size != b.size:
        return 1.0
    diff = ImageChops.difference(a.convert("RGB"), b.convert("RGB")).convert("L")
    small = diff.resize((max(1, a.width // 4), max(1, a.height // 4)), Image.Resampling.BOX)
    hist = small.histogram()
    changed = sum(hist[threshold:])
    return changed / float(small.width * small.height)


def mask_mutable(image: Image.Image, box: tuple[int, int, int, int], fill=(12, 14, 20)) -> Image.Image:
    out = image.convert("RGB").copy()
    ImageDraw.Draw(out).rectangle(box, fill=fill)
    return out


def compare_preservation(parent: Image.Image, child: Image.Image) -> dict[str, Any]:
    box = commercial_mutable_box()
    masked_parent = mask_mutable(parent, box)
    masked_child = mask_mutable(child, box)
    outside = _mean_channel_delta(masked_parent, masked_child)
    outside_frac = _changed_fraction(masked_parent, masked_child)
    crops: dict[str, Any] = {}
    unexpected: list[str] = []
    for name, crop in LOCKED_CROPS.items():
        delta = _mean_channel_delta(parent.crop(crop), child.crop(crop))
        frac = _changed_fraction(parent.crop(crop), child.crop(crop))
        crops[name] = {"mean_delta": round(delta, 4), "changed_fraction": round(frac, 6)}
        if delta > 3.0 or frac > 0.02:
            unexpected.append(f"{name}_delta={delta:.2f}_frac={frac:.4f}")
    if outside > 2.0 or outside_frac > 0.012:
        unexpected.append(f"outside_commercial_mean_delta={outside:.2f}_frac={outside_frac:.4f}")
    return {
        "mutable_box": list(box),
        "mutable_groups": ["commercial"],
        "immutable_groups": ["project_photo", "architecture", "logo", "headline", "unit_type", "cta"],
        "outside_commercial_mean_delta": round(outside, 4),
        "outside_commercial_changed_fraction": round(outside_frac, 6),
        "locked_crop_deltas": crops,
        "unexpected_changes": unexpected,
        "pass": not unexpected,
    }


def render_preservation_map(parent: Image.Image, child: Image.Image) -> Image.Image:
    box = commercial_mutable_box()
    gray = ImageChops.difference(parent.convert("RGB"), child.convert("RGB")).convert("L")
    overlay = parent.convert("RGB").copy()
    changed = gray.point(lambda p: 180 if p > 10 else 0)
    mutable = Image.new("L", overlay.size, 0)
    ImageDraw.Draw(mutable).rectangle(box, fill=255)
    overlay = Image.composite(Image.new("RGB", overlay.size, (46, 168, 84)), overlay, ImageChops.multiply(changed, mutable))
    overlay = Image.composite(
        Image.new("RGB", overlay.size, (196, 48, 48)),
        overlay,
        ImageChops.subtract(changed, mutable),
    )
    ImageDraw.Draw(overlay).rectangle(box, outline=(46, 168, 84), width=2)
    return overlay


def render_geometry_diff(parent: Image.Image, child: Image.Image) -> Image.Image:
    canvas = Image.new("RGB", (parent.width * 2 + 40, parent.height + 48), (12, 14, 20))
    canvas.paste(parent, (16, 32))
    canvas.paste(child, (parent.width + 24, 32))
    draw = ImageDraw.Draw(canvas)
    box = commercial_mutable_box()
    for ox in (16, parent.width + 24):
        draw.rectangle((ox + box[0], 32 + box[1], ox + box[2], 32 + box[3]), outline=(201, 168, 92), width=2)
        for name, crop in LOCKED_CROPS.items():
            if name == "architecture":
                continue
            draw.rectangle((ox + crop[0], 32 + crop[1], ox + crop[2], 32 + crop[3]), outline=(90, 160, 255), width=1)
    draw.text((16, 8), "gold = mutable commercial     blue = locked groups", fill=(201, 168, 92))
    return canvas


def _count_keys(blob: dict[str, Any]) -> dict[str, int]:
    return {f"{key}_count": len(list(blob.get(key) or [])) for key, _alias in _HISTORY_KEYS}


def generate_master_revision_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    instruction: str = TEST_A_INSTRUCTION,
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = {
        "session": blob.get("current_session_id"),
        "family": blob.get("current_format_family_id"),
        "approved": {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()},
        "sessions": dict(blob.get("sessions") or {}),
    }
    for key, alias in _HISTORY_KEYS:
        preserved[alias] = list(blob.get(key) or [])
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]
    before.update(_count_keys({key: preserved[alias] for key, alias in _HISTORY_KEYS}))

    approved = build_approved_creative_master()
    intent = build_revision_intent(
        approved_master_id=MASTER_COMMERCIAL_R1_ID, instruction=instruction, master=approved
    )
    if intent.get("revision_scope") != PRICE_REVISION:
        raise RuntimeError(f"Phase 5.5 Test A expected PRICE_REVISION, got {intent.get('revision_scope')}")
    prices = parse_price_revision(instruction)
    visual_replace_ready = plan_visual_replace(_VISUAL_REPLACE_INSTRUCTION, approved)

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
    try:
        approved_png = Image.open(io.BytesIO(_read_bytes(db, UUID(APPROVED_R1_ASSET_ID)))).convert("RGB")
    except Exception:
        approved_png = None
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
    photo_uri = _jpeg_data_uri(graded)
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(logo_bytes)
    parent_facts = dict(REQUIRED_FACTS)
    parent_pack = _render_scene(
        scene_premium_commercial_r1(parent_facts),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=parent_facts,
    )
    if approved_png is None:
        approved_png = parent_pack["image"]
    child_facts = dict(parent_facts)
    child_facts.update(
        {
            "list_price": prices["launch_price"],
            "launch_price": prices["launch_price"],
            "list_price_struck": prices["list_price_struck"],
            "savings": prices["savings"],
            "savings_label": prices["savings_label"],
        }
    )
    child_pack = _render_scene(
        scene_premium_commercial_price_revision(child_facts),
        photo_uri=photo_uri,
        logo_markup=logo_markup,
        font_css=font_css,
        facts=child_facts,
    )
    preservation = compare_preservation(parent_pack["image"], child_pack["image"])
    provenance = architecture_provenance_qa(
        source=source, foundation=crop, final=child_pack["image"], transform=transform
    )
    markup = child_pack["assembled_markup"]
    semantic_ok = {
        "primary_price": "438.750 USD" in markup,
        "struck_list": "675.000 USD" in markup and 'data-state="struck"' in markup,
        "savings": "236.250 USD" in markup and "KAZANCINIZ" in markup,
        "discount": "%35" in markup and "LANSMAN AVANTAJI" in markup,
        "headline": "ALIRKEN KAZAN" in markup,
        "unit": "2+1 DAİRE" in markup,
        "cta": "PROJEYİ KEŞFET" in markup,
        "slots": markup_has_semantic_slots(markup),
        "no_cards": not any(token in markup.casefold() for token in ("badge", "pill", "ribbon", "medallion", "kpi-card")),
    }
    lock_failed = [k for k, v in semantic_ok.items() if not v] + list(preservation.get("unexpected_changes") or [])

    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(child_pack["image"]),
        content_type="image/png",
        campaign_mode="project-creative-master-revision",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="PHASE 5.5 PRICE_REVISION Test A",
    )
    revision_rec = {
        "revision_id": MASTER_PRICE_REVISION_V2_ID,
        "parent_master_id": MASTER_COMMERCIAL_R1_ID,
        "revision_number": 2,
        "revision_intent": PRICE_REVISION,
        "natural_language_instruction": instruction,
        "semantic_diff": {
            "list_price": {"from": "675.000 USD", "to": "675.000 USD", "state": "struck"},
            "launch_price": {"from": None, "to": "438.750 USD", "role": "PRIMARY_PRICE"},
            "savings": {"from": None, "to": "236.250 USD", "label": "KAZANCINIZ"},
            "discount": {"from": "%35 LANSMAN AVANTAJI", "to": "%35 LANSMAN AVANTAJI", "unchanged": True},
        },
        "geometry_diff": {
            "commercial_origin_locked": True,
            "commercial_internal_reflow": True,
            "other_groups": "unchanged",
            "changed_geometry": ["commercial"],
            "unchanged_geometry": ["project_photo", "logo", "headline", "unit_type", "cta"],
        },
        "asset_diff": {
            "parent_asset_id": APPROVED_R1_ASSET_ID,
            "child_asset_id": str(asset.id),
            "source_photo": LOCKED_HERO_ASSET_ID,
            "logo": LOCKED_LOGO_ASSET_ID,
            "source_photo_changed": False,
            "logo_changed": False,
        },
        "parent_scene_markup": scene_premium_commercial_r1(parent_facts),
        "parent_semantic_content": dict(parent_facts),
        "child_scene_markup": scene_premium_commercial_price_revision(child_facts),
        "timestamp": _now(),
        "reversible": True,
    }
    approved = append_revision(approved, revision_rec)
    restore = restore_parent_scene(approved, MASTER_PRICE_REVISION_V2_ID)

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_55,
        "created_at": _now(),
        "approved_master_id": MASTER_COMMERCIAL_R1_ID,
        "parent_asset_id": APPROVED_R1_ASSET_ID,
        "new_revision_id": MASTER_PRICE_REVISION_V2_ID,
        "new_asset_id": str(asset.id),
        "revision_intent_name": PRICE_REVISION,
        "original_user_instruction": instruction,
        "semantic_diff": revision_rec["semantic_diff"],
        "geometry_diff": revision_rec["geometry_diff"],
        "asset_diff": revision_rec["asset_diff"],
        "commercial_reflow_method": "update semantic lockup HTML; deterministic Chromium render; no raster patch",
        "unchanged_elements": [
            "Day_004 crop/grade",
            "architecture",
            "logo",
            "ALIRKEN KAZAN",
            "2+1 DAİRE",
            "CTA",
            "typography families",
            "color language",
        ],
        "source_photo_provenance": provenance,
        "architecture_changed": False,
        "logo_changed": False,
        "gpt_image_calls": 0,
        "provider_call_count": 0,
        "reversible": True,
        "restore_check": restore.get("restored_master_id") == MASTER_COMMERCIAL_R1_ID,
        "preservation": preservation,
        "semantic_ok": semantic_ok,
        "lock_failed": lock_failed,
        "acceptance_pass": not lock_failed,
        "scene_gate": child_pack["gate"],
        "visual_replace_architecture": visual_replace_ready,
        "visual_replace_executed": False,
        "live_routing_active": False,
        "approval_status_parent": HUMAN_APPROVED,
        "human_visual_status_parent": "PASS",
        "critic_reopened_art_direction": False,
        "project_id": TEMPLE_PROJECT_ID,
    }
    tests = [
        t
        for t in list(blob.get("master_revision_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_55)
    ]
    tests.append({k: v for k, v in record.items()})
    blob["master_revision_tests"] = tests
    stored = dict(approved)
    blob["approved_creative_masters"] = {MASTER_COMMERCIAL_R1_ID: stored}
    blob["current_session_id"] = preserved["session"]
    blob["current_format_family_id"] = preserved["family"]
    for key, alias in _HISTORY_KEYS:
        blob[key] = preserved[alias]
    blob["approved_masters"] = preserved["approved"]
    blob["sessions"] = preserved["sessions"]
    ctx = dict(original)
    ctx[CTX_KEY] = blob
    after = snapshot_identity(ctx)
    after["current_master_design_spec_id"] = ctx.get("current_master_design_spec_id")
    after["phase5_current_session_id"] = blob.get("current_session_id")
    after["phase5_current_format_family_id"] = blob.get("current_format_family_id")
    after.update(_count_keys(blob))
    _production_guard(before, after)
    if blob.get("premium_commercial_r1_tests") != preserved["r1"]:
        raise RuntimeError("Phase 5.5 refused to overwrite Phase 5.4A-R1")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.5 refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "approved": approved_png,
        "parent_render": parent_pack["image"],
        "revision": child_pack["image"],
    }
    record["approved_master"] = approved
    record["revision_intent"] = intent
    record["revision_plan"] = {
        "schema": "CreativeRevisionPlanV1",
        "intent": PRICE_REVISION,
        "reflow": "commercial lockup internal only",
        "renderer": "approved design language Chromium scene",
        "visual_replace_executed": False,
        "forbidden": ["raster patch", "inpainting", "GPT Image designer", "architecture generation"],
    }
    record["revised_master"] = {
        "revision_id": MASTER_PRICE_REVISION_V2_ID,
        "parent_master_id": MASTER_COMMERCIAL_R1_ID,
        "revision_number": 2,
        "scene_markup": scene_premium_commercial_price_revision(child_facts),
        "semantic_content": child_facts,
        "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
    }
    record["rendered"] = child_pack
    _ = language
    return record

