"""Phase 5.4B-R1 — reference-grounded Creative Director quality correction.

Does not rebuild Drive, Media Library, reference storage, or Phase 5.5.
Does not promote candidates. Does not modify the approved master.
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
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_quality_doctrine import build_quality_doctrine
from investhome_api.services.creative_director.creative_reference_library import (
    attach_media_library_mapping,
    build_reference_library,
    index_design_references_folder,
    locate_design_references,
    retrieve_references,
)
from investhome_api.services.creative_director.generative_creative_director_v2 import (
    R1_DIRECTIONS,
    assign_moodboards,
    audit_phase54b_reference_influence,
    critic_targets_met,
    inspect_art_direction_draft,
    markup_forbidden_reasons,
    request_composition_blueprint,
    request_critic_v2,
    request_directed_markup,
    request_photo_composition_analysis,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _HISTORY_KEYS as _BASE_HISTORY,
    _analyze_references,
    _font,
    _preserve as _preserve_base,
    _wrap,
)
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, inline_logo_svg, _jpeg_data_uri
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png, _render_scene
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_creative import (
    render_protection_map,
    request_protection_map,
)
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

WORKFLOW_ID_54B_R1 = "phase5_4b_r1_reference_grounded"
MAX_ATTEMPTS = 3
_HISTORY_KEYS = _BASE_HISTORY + (("creative_quality_tests", "quality54b"),)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    return preserved


def _box_px(box: dict[str, Any] | None, size: tuple[int, int]) -> tuple[int, int, int, int] | None:
    if not isinstance(box, dict):
        return None
    try:
        x, y, w, h = float(box["x"]), float(box["y"]), float(box["w"]), float(box["h"])
    except (KeyError, TypeError, ValueError):
        return None
    width, height = size
    x0 = max(0, int(x * width))
    y0 = max(0, int(y * height))
    x1 = min(width, int((x + w) * width))
    y1 = min(height, int((y + h) * height))
    if x1 <= x0 or y1 <= y0:
        return None
    return x0, y0, x1, y1


def render_moodboard(board: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(18)
    small = _font(14)
    draw.text((40, 32), f"MOODBOARD {board.get('candidate_key')}  {board.get('concept')}", fill=(201, 168, 92), font=font)
    refs = list(board.get("references") or [])[:4]
    coords = ((40, 90), (564, 90), (40, 720), (564, 720))
    for item, origin in zip(refs, coords):
        preview = item.get("_preview")
        tile = Image.new("RGB", (484, 580), (22, 24, 32))
        if isinstance(preview, Image.Image):
            fitted = preview.copy()
            fitted.thumbnail((484, 520), Image.Resampling.LANCZOS)
            tile.paste(fitted, ((484 - fitted.width) // 2, 40))
        ImageDraw.Draw(tile).text(
            (12, 10),
            f"{item.get('moodboard_role')}  {item.get('filename')}",
            fill=(201, 168, 92),
            font=small,
        )
        canvas.paste(tile, origin)
    y = 1310
    draw.text((40, y), "References are visual inputs. Do not copy buildings, logos, or copy.", fill=(180, 176, 168), font=small)
    return canvas


def render_composition_preview(foundation: Image.Image, blueprint: dict[str, Any]) -> Image.Image:
    im = foundation.convert("RGB").copy()
    overlay = Image.new("RGBA", im.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    zones = dict(blueprint.get("zones") or {})
    colors = {
        "brand_zone": (201, 168, 92, 70),
        "commercial_zone": (90, 160, 220, 70),
        "cta": (90, 200, 130, 70),
        "graphic_field": (40, 44, 56, 90),
        "protected": (220, 60, 60, 0),
    }
    for name, color in colors.items():
        box = zones.get(name) or blueprint.get(name)
        if isinstance(box, dict) and {"x", "y", "w", "h"} <= set(box):
            px = _box_px(box, im.size)
            if px:
                draw.rectangle(px, outline=color[:3] + (220,), width=4)
                if name == "graphic_field":
                    draw.rectangle(px, fill=color)
    merged = im.convert("RGBA")
    merged.alpha_composite(overlay)
    out = merged.convert("RGB")
    bar = Image.new("RGB", (out.width, 48), (12, 14, 20))
    ImageDraw.Draw(bar).text((16, 14), "CompositionBlueprintV2 — copy not yet inserted", fill=(201, 168, 92), font=_font(16))
    canvas = Image.new("RGB", (out.width, out.height + 48), (12, 14, 20))
    canvas.paste(bar, (0, 0))
    canvas.paste(out, (0, 48))
    return canvas


def render_audit_board(audit: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1400, 1600), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(20)
    small = _font(14)
    y = 36
    draw.text((40, y), "ReferenceInfluenceAuditV1 — Phase 5.4B REJECTED A/B/C", fill=(201, 168, 92), font=font)
    y += 40
    draw.text((40, y), str(audit.get("status")), fill=(220, 80, 80), font=font)
    y += 36
    for chunk in _wrap(str(audit.get("finding") or ""), 108):
        draw.text((40, y), chunk, fill=(236, 230, 218), font=small)
        y += 22
    y += 16
    for row in list(audit.get("rows") or [])[:12]:
        line = (
            f"{row.get('reference')} | {row.get('observed_principle')} | "
            f"{row.get('actual_application')} | {row.get('result')}"
        )
        for chunk in _wrap(line, 108):
            draw.text((40, y), chunk, fill=(200, 196, 188), font=small)
            y += 20
            if y > 1540:
                return canvas
        y += 8
    return canvas


def render_influence_proof(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1600, 1700), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(18)
    small = _font(13)
    draw.text((32, 24), "ReferenceInfluenceProofV1 — application must be visible", fill=(201, 168, 92), font=font)
    y = 70
    for item in candidates:
        draw.text((32, y), f"{item.get('key')}  {item.get('concept')}", fill=(236, 230, 218), font=font)
        y += 28
        cand = item.get("image")
        if isinstance(cand, Image.Image):
            thumb = cand.copy()
            thumb.thumbnail((280, 350), Image.Resampling.LANCZOS)
            canvas.paste(thumb, (32, y))
        x = 330
        for ref in list(item.get("moodboard_refs") or [])[:4]:
            preview = ref.get("_preview")
            if isinstance(preview, Image.Image):
                t = preview.copy()
                t.thumbnail((240, 240), Image.Resampling.LANCZOS)
                canvas.paste(t, (x, y))
            role = str(ref.get("moodboard_role") or "")
            draw.text((x, y + 248), role[:28], fill=(201, 168, 92), font=small)
            x += 260
        apps = list(item.get("reference_applications") or [])[:3]
        ty = y + 280
        for row in apps:
            text = f"{row.get('reference_id', '')[:8]} → {row.get('principle')} → {row.get('planned_application') or row.get('actual_application')}"
            for chunk in _wrap(str(text), 120):
                draw.text((32, ty), chunk, fill=(180, 176, 168), font=small)
                ty += 18
        y = max(y + 380, ty + 24)
        if y > 1600:
            break
    return canvas


def render_human_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(20)
    small = _font(14)
    draw.text((36, 28), "HUMAN REVIEW BOARD — 5.4B-R1  DO NOT PROMOTE", fill=(201, 168, 92), font=font)
    x = 36
    for item in candidates:
        im = item.get("image")
        if isinstance(im, Image.Image):
            tile = im.copy().resize((380, 475), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 80))
        critic = dict(item.get("critic") or {})
        draw.text((x, 568), f"{item.get('key')} {item.get('concept')}", fill=(236, 230, 218), font=small)
        draw.text((x, 590), f"art {critic.get('professional_art_direction')}  pub {critic.get('publishability')}", fill=(180, 176, 168), font=small)
        draw.text((x, 612), "PENDING HUMAN REVIEW", fill=(201, 168, 92), font=small)
        x += 410
    y = 660
    draw.text((36, y), "Approved master and production cover were not modified.", fill=(180, 176, 168), font=small)
    return canvas


def render_three_way(candidates: list[dict[str, Any]]) -> Image.Image:
    tiles = []
    font = _font(16)
    for item in candidates:
        im = item.get("image")
        if not isinstance(im, Image.Image):
            continue
        resized = im.copy().resize((360, 450), Image.Resampling.LANCZOS)
        bar = 40
        tile = Image.new("RGB", (resized.width, resized.height + bar), (12, 14, 20))
        tile.paste(resized, (0, bar))
        ImageDraw.Draw(tile).text((12, 10), f"{item.get('key')}  {str(item.get('concept') or '').lower()}", fill=(201, 168, 92), font=font)
        tiles.append(tile)
    if not tiles:
        return Image.new("RGB", (1088, 400), (12, 14, 20))
    gap = 20
    w = sum(t.width for t in tiles) + gap * (len(tiles) + 1)
    h = tiles[0].height + 40
    out = Image.new("RGB", (w, h), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out


def _generate_one(
    *,
    spec: dict[str, str],
    moodboard: dict[str, Any],
    graded: Image.Image,
    protection_img: Image.Image,
    photo_analysis: dict[str, Any],
    logo_preview: Image.Image,
    fonts: dict[str, Any],
    photo_uri: str,
    logo_markup: str,
    font_css: str,
) -> tuple[dict[str, Any], int, Image.Image]:
    vision = 0
    critique = ""
    last_blueprint: dict[str, Any] = {}
    last_preview = graded
    last_pack: dict[str, Any] | None = None
    last_directed: dict[str, Any] = {}
    last_inspect: dict[str, Any] = {}
    accepted = False
    for attempt in range(1, MAX_ATTEMPTS + 1):
        blueprint, calls = request_composition_blueprint(
            foundation=graded,
            protection=protection_img,
            photo_analysis=photo_analysis,
            moodboard=moodboard,
            concept=str(spec["concept"]),
            intent=str(spec["intent"]),
            critique=critique,
        )
        vision += calls
        last_blueprint = blueprint
        preview = render_composition_preview(graded, blueprint)
        last_preview = preview
        directed, calls = request_directed_markup(
            foundation=graded,
            composition_preview=preview,
            protection=protection_img,
            logo_preview=logo_preview,
            moodboard=moodboard,
            blueprint=blueprint,
            fonts=fonts,
            facts=dict(REQUIRED_FACTS),
            concept=str(spec["concept"]),
            intent=str(spec["intent"]),
            critique=critique,
        )
        vision += calls
        last_directed = directed
        markup = str(directed.get("markup") or "")
        banned = markup_forbidden_reasons(markup)
        if banned or not markup:
            critique = "Forbidden layout in markup: " + ", ".join(banned or ["missing_markup"])
            continue
        pack = _render_scene(
            markup,
            photo_uri=photo_uri,
            logo_markup=logo_markup,
            font_css=font_css,
            facts=dict(REQUIRED_FACTS),
        )
        last_pack = pack
        inspect, calls = inspect_art_direction_draft(
            draft=pack["image"],
            foundation=graded,
            moodboard=moodboard,
            concept=str(spec["concept"]),
        )
        vision += calls
        last_inspect = inspect
        if inspect.get("reject"):
            critique = "; ".join(str(r) for r in list(inspect.get("reasons") or [])[:8]) or "inspector rejected"
            continue
        accepted = True
        break
    if last_pack is None:
        raise RuntimeError(f"{spec['key']} produced no renderable markup after {MAX_ATTEMPTS} attempts")
    return (
        {
            "key": spec["key"],
            "concept": spec["concept"],
            "intent": spec["intent"],
            "blueprint": last_blueprint,
            "directed": last_directed,
            "inspect": last_inspect,
            "accepted_internally": accepted,
            "attempts": attempt if last_pack else MAX_ATTEMPTS,
            "markup": str(last_directed.get("markup") or ""),
            "reference_applications": last_directed.get("reference_applications") or last_blueprint.get("reference_applications") or [],
            "typography_systems": last_directed.get("typography_systems"),
            "moodboard_refs": [
                {k: v for k, v in item.items() if k != "_preview"} | {"_preview": item.get("_preview")}
                for item in list(moodboard.get("references") or [])
            ],
            "reference_ids": [str(item.get("reference_id")) for item in list(moodboard.get("references") or [])],
            "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
            "rendered": last_pack,
            "image": last_pack["image"],
        },
        vision,
        last_preview,
    )


def generate_creative_quality_r1_4x5(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    language: str = "tr",
    previous_candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    original = dict(row.context_json or {})
    before = snapshot_identity(original)
    before["current_master_design_spec_id"] = original.get("current_master_design_spec_id")
    blob = _phase5(dict(original))
    preserved = _preserve(blob)
    before["phase5_current_session_id"] = preserved["session"]
    before["phase5_current_format_family_id"] = preserved["family"]

    location = locate_design_references(db)
    if location.get("found") and (location.get("folder") or {}).get("drive_folder_id"):
        index_result = index_design_references_folder(db, location)
        location = attach_media_library_mapping(db, location)
        location["index_result"] = index_result
    vision_calls = 0
    lock_failed: list[str] = []
    status = "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    images: dict[str, Any] = {}
    candidates: list[dict[str, Any]] = []
    library: dict[str, Any] | None = None
    doctrine = build_quality_doctrine([])
    photo_analysis: dict[str, Any] | None = None
    retrieved: list[dict[str, Any]] = []
    audit = audit_phase54b_reference_influence(previous_candidates or [], retrieved)
    provenance: dict[str, Any] | None = None
    moodboards: dict[str, Any] = {}
    visual_conditioning = False

    if location.get("found"):
        library = build_reference_library(db, location)
        if int(library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            library, previews, dna_calls = _analyze_references(db, library)
            vision_calls += dna_calls
            retrieved = retrieve_references(library, purpose="premium_project_campaign", format_aspect="4:5", limit=10)
            for item in retrieved:
                preview = previews.get(str(item.get("reference_id")))
                if preview is not None:
                    item["_preview"] = preview
            audit = audit_phase54b_reference_influence(previous_candidates or [], retrieved)
            doctrine = build_quality_doctrine(retrieved)
            doctrine["failure_lessons"] = list(doctrine.get("failure_lessons") or []) + [
                "5.4B A REJECT: logo/headline over architecture, tiny commerce, text-on-photo.",
                "5.4B B REJECT: translucent white listing card; graphics detached from photograph.",
                "5.4B C REJECT: bottom-left dump, collapsed hierarchy, leftover unused canvas.",
            ]
            fonts = build_font_registry()
            source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
            logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
            crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
            graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
            photo_uri = _jpeg_data_uri(graded)
            photo_analysis, calls = request_photo_composition_analysis(graded)
            vision_calls += calls
            protection, calls = request_protection_map(graded)
            vision_calls += calls
            protection_img = render_protection_map(graded, protection)
            try:
                logo_preview = Image.open(io.BytesIO(logo_bytes)).convert("RGB")
            except Exception:
                logo_preview = Image.new("RGB", (80, 32), (20, 24, 30))
            moodboards = assign_moodboards(retrieved)
            visual_conditioning = any(
                isinstance(item.get("_preview"), Image.Image)
                for board in moodboards.values()
                for item in list(board.get("references") or [])
            )
            logo_markup = inline_logo_svg(logo_bytes)
            font_css = font_face_css(fonts)
            images["audit"] = render_audit_board(audit)
            for spec in R1_DIRECTIONS:
                board = moodboards[spec["key"]]
                images[f"moodboard_{spec['key']}"] = render_moodboard(board)
                item, more, composition = _generate_one(
                    spec=spec,
                    moodboard=board,
                    graded=graded,
                    protection_img=protection_img,
                    photo_analysis=photo_analysis,
                    logo_preview=logo_preview,
                    fonts=fonts,
                    photo_uri=photo_uri,
                    logo_markup=logo_markup,
                    font_css=font_css,
                )
                vision_calls += more
                images[f"composition_{spec['key']}"] = composition
                critic, calls = request_critic_v2(
                    candidate=item["image"],
                    foundation=graded,
                    concept=str(spec["concept"]),
                )
                vision_calls += calls
                met, reasons = critic_targets_met(critic) if critic.get("mode") == "vision" else (False, ["critic_unavailable"])
                asset = persist_gpt_image(
                    db,
                    actor=user,
                    linked_project_id=row.linked_project_id,
                    content=_png(item["image"]),
                    content_type="image/png",
                    campaign_mode="project-creative-quality-r1-candidate",
                    session_id=str(uuid4()),
                    provider_generation_id=None,
                    campaign_context_id=str(row.id),
                    brief_excerpt=f"PHASE 5.4B-R1 {spec['concept']}",
                )
                item["asset_id"] = str(asset.id)
                item["critic"] = critic
                item["quality_targets_met"] = met
                item["quality_fail_reasons"] = reasons
                candidates.append(item)
            provenance = architecture_provenance_qa(
                source=source,
                foundation=crop,
                final=candidates[0]["image"] if candidates else graded,
                transform=transform,
            )
            images["comparison"] = render_three_way(candidates)
            images["influence_proof"] = render_influence_proof(candidates)
            images["human_board"] = render_human_board(candidates)
            images["foundation"] = graded
            images["protection"] = protection_img
            status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54B_R1,
        "created_at": _now(),
        "status": status,
        "reference_visual_conditioning_active": visual_conditioning,
        "audit": {k: v for k, v in audit.items() if k != "rows"} | {"row_count": len(list(audit.get("rows") or []))},
        "audit_full": audit,
        "moodboards": {
            key: {
                "reference_ids": board.get("roles") and [str(r.get("reference_id")) for r in board.get("references") or []],
                "roles": board.get("roles"),
            }
            for key, board in moodboards.items()
        },
        "candidates": [
            {
                k: v
                for k, v in item.items()
                if k not in {"image", "rendered", "moodboard_refs"}
            }
            for item in candidates
        ],
        "lock_failed": lock_failed,
        "gpt_image_calls": 0,
        "vision_calls": vision_calls,
        "provider_call_count": vision_calls,
        "live_routing_active": False,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "provenance_qa": provenance,
        "library_status": (library or {}).get("status") if library else "NOT_BUILT",
        "doctrine_status": doctrine.get("status"),
        "photo_analysis_id": None if photo_analysis is None else str(uuid4()),
    }
    tests = [
        t
        for t in list(blob.get("creative_quality_r1_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54B_R1)
    ]
    tests.append({k: v for k, v in record.items() if k != "audit_full"})
    blob["creative_quality_r1_tests"] = tests
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
        raise RuntimeError("Phase 5.4B-R1 refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4B-R1 refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4B-R1 refused to modify approved creative masters")
    if blob.get("creative_quality_tests") != preserved.get("quality54b"):
        raise RuntimeError("Phase 5.4B-R1 refused to overwrite Phase 5.4B history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4B-R1 refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library
    record["doctrine"] = doctrine
    record["photo_analysis"] = photo_analysis
    record["candidate_images"] = candidates
    _ = language
    return record
