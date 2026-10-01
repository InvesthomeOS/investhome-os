"""Phase 5.4 — production creative master candidates.

Professionally designed editable masters rendered on locked Day_004.
Does not activate live routing. Does not use GPT Image as designer.
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
    build_creative_master_library,
    families_are_distinct,
    markup_has_semantic_slots,
    route_creative_master,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_design_scene import (
    _jpeg_data_uri,
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

WORKFLOW_ID_54 = "phase5_4_production_masters"


def _png(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def render_library_masters(
    *,
    foundation: Image.Image,
    logo_bytes: bytes,
    fonts: dict[str, Any],
    facts: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    photo_uri = _jpeg_data_uri(foundation)
    font_css = font_face_css(fonts)
    logo_markup = inline_logo_svg(logo_bytes)
    library = build_creative_master_library(facts)
    library["created_at"] = _now()
    rendered: list[dict[str, Any]] = []
    for master in library["masters"]:
        assembled = assemble_scene(
            str(master.get("scene_markup") or ""),
            photo_uri=photo_uri,
            logo_markup=logo_markup,
            font_css=font_css,
        )
        gate = validate_scene(assembled, facts, photo_uri)
        image = render_html_to_png(assembled)
        master["created_at"] = library["created_at"]
        rendered.append(
            {
                "master_id": master["master_id"],
                "creative_family": master["creative_family"],
                "name_internal": master["name_internal"],
                "approval_status": master["approval_status"],
                "assembled_markup": assembled,
                "persistable_markup": persistable_markup(assembled, photo_uri),
                "gate": gate,
                "image": image,
                "semantic_ok": markup_has_semantic_slots(assembled),
            }
        )
        master["scene_markup"] = persistable_markup(str(master.get("scene_markup") or ""), photo_uri)
    library["families_distinct"] = families_are_distinct(library)
    return library, rendered


def generate_production_masters_4x5(
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

    fonts = build_font_registry()
    source = Image.open(io.BytesIO(_read_bytes(db, UUID(hero_id)))).convert("RGB")
    logo_bytes = _read_bytes(db, UUID(logo_id))
    try:
        reference = Image.open(io.BytesIO(_read_bytes(db, UUID(PHASE50_MASTER_ASSET_ID)))).convert("RGB")
    except Exception:
        reference = source
    crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
    graded = apply_photographic_grade(crop, {"warmth": 0.10, "contrast": 1.06, "brightness": 0.99, "vignette": 0.08})
    library, rendered = render_library_masters(
        foundation=graded, logo_bytes=logo_bytes, fonts=fonts, facts=campaign_facts
    )
    provenance = architecture_provenance_qa(
        source=source, foundation=crop, final=rendered[0]["image"], transform=transform
    )
    router = route_creative_master(
        user_brief="The Temple için ALIRKEN KAZAN reklamı hazırla.",
        library=library,
        target_ratio="4:5",
        campaign_goal="investment_launch",
    )
    assets: dict[str, str] = {}
    for pack in rendered:
        asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(pack["image"]),
            content_type="image/png",
            campaign_mode="project-creative-master-candidate",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 5.4 master candidate {pack['creative_family']}",
        )
        pack["render_asset_id"] = str(asset.id)
        assets[pack["creative_family"]] = str(asset.id)

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54,
        "created_at": _now(),
        "creative_method": "approved_master_library_candidates_not_live_routed",
        "source_asset_id": hero_id,
        "source_filename": HERO_FILENAME if hero_id == LOCKED_HERO_ASSET_ID else None,
        "architecture_generation_used": False,
        "gpt_image_calls": 0,
        "gpt_image_edit_calls": 0,
        "real_logo_asset_id": logo_id,
        "project_id": TEMPLE_PROJECT_ID,
        "font_registry": fonts.get("schema"),
        "display_font": ((fonts.get("roles") or {}).get("DISPLAY_SERIF") or {}).get("font_file"),
        "support_font": ((fonts.get("roles") or {}).get("EDITORIAL_SANS") or {}).get("font_file"),
        "masters_created": [p["creative_family"] for p in rendered],
        "master_asset_ids": assets,
        "approval_status": APPROVAL_CANDIDATE,
        "live_routing_active": False,
        "user_facing_templates": False,
        "router_preview": router,
        "library_schema": library.get("schema"),
        "families_distinct": library.get("families_distinct"),
        "gates": {p["creative_family"]: p["gate"] for p in rendered},
        "provenance_qa": provenance,
        "video_started": False,
        "publishing_started": False,
        "human_approval_required": True,
    }
    tests = [
        t
        for t in list(blob.get("creative_master_library_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54)
    ]
    tests.append(dict(record))
    blob["creative_master_library_tests"] = tests
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
    _production_guard(before, after)
    if blob.get("design_scene_tests") != preserved["scene"]:
        raise RuntimeError("Phase 5.4 refused to change Phase 5.3 history")
    if blob.get("visual_art_director_tests") != preserved["vad"]:
        raise RuntimeError("Phase 5.4 refused to change Phase 5.2B history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4 refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = {
        "source": source,
        "crop": crop,
        "foundation": graded,
        "reference": reference,
        "masters": {p["creative_family"]: p["image"] for p in rendered},
    }
    record["rendered"] = rendered
    record["library"] = library
    record["fonts"] = fonts
    _ = language
    return record


def render_three_comparison(images: dict[str, Image.Image]) -> Image.Image:
    order = ("EDITORIAL_ARCHITECTURAL", "PREMIUM_COMMERCIAL", "MINIMAL_LUXURY")
    labels = {
        "EDITORIAL_ARCHITECTURAL": "A  editorial architectural",
        "PREMIUM_COMMERCIAL": "B  premium commercial",
        "MINIMAL_LUXURY": "C  minimal luxury",
    }
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except Exception:
        font = ImageFont.load_default()
    tiles = []
    for key in order:
        im = images[key].copy().resize((360, 450), Image.Resampling.LANCZOS)
        bar = 36
        canvas = Image.new("RGB", (im.width, im.height + bar), (12, 14, 20))
        canvas.paste(im, (0, bar))
        ImageDraw.Draw(canvas).text((12, 8), labels[key], fill=(201, 168, 92), font=font)
        tiles.append(canvas)
    gap = 20
    w = sum(t.width for t in tiles) + gap * 4
    h = tiles[0].height + 40
    out = Image.new("RGB", (w, h), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out
