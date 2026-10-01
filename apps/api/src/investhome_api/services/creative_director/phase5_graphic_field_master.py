"""Phase 5.4E — Graphic-Field Master (Architecture B).

AI paints non-text graphic fields. The OS compositor owns all typography,
commercial information, and the real Temple logo.
Does not promote. Does not touch the approved master, production cover, or Phase 5.5.
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
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import (
    attach_media_library_mapping,
    build_reference_library,
    index_design_references_folder,
    locate_design_references,
)
from investhome_api.services.creative_director.executable_reference_system import (
    E_ASSIGNMENTS,
    FORBIDDEN_PRIMARY,
    request_executable_system,
    seeded_system,
    systems_for_candidate,
)
from investhome_api.services.creative_director.graphic_field_director import (
    architecture_protection_mask_v2,
    build_graphic_field_prompt,
    critic_targets_met_54e,
    hard_reject_54e,
    inspect_final_candidate,
    request_graphic_field_critic,
    request_graphic_field_plan,
    run_graphic_field_pass,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _HISTORY_KEYS as _BASE_HISTORY,
    _font,
    _preserve as _preserve_base,
    _wrap,
)
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_production_creative import (
    HEURISTIC_PROTECTION,
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
from investhome_api.services.creative_director.project_architecture_lock import architecture_integrity_qa
from investhome_api.services.creative_director.reference_quality_filter import filter_references
from investhome_api.services.creative_director.structured_typography_compositor_v2 import (
    build_master_spec,
    compose_typography_v2,
    revision_readiness,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54E = "phase5_4e_graphic_field_master"
CANDIDATE_KEYS = ("E1", "E2", "E3")
_HISTORY_KEYS = _BASE_HISTORY + (
    ("creative_quality_tests", "quality54b"),
    ("creative_quality_r1_tests", "quality54b_r1"),
    ("generative_master_tests", "quality54c"),
)
REQUIRED_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["list_price"],
    REQUIRED_FACTS["discount"],
    REQUIRED_FACTS["discount_label"],
    REQUIRED_FACTS["cta"],
)
GRADE_A_ORDER = (
    "ORNEK_00013.jpg",
    "ORNEK_00001.jpg",
    "ORNEK_00006.jpg",
    "ORNEK_00015.jpg",
    "ORNEK_00011.jpg",
    "ORNEK_00008.jpg",
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    preserved["quality54b_r1"] = list(blob.get("creative_quality_r1_tests") or [])
    preserved["quality54c"] = list(blob.get("generative_master_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def render_grade_a_board(allowed: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "PHASE 5.4E — GRADE A REFERENCES ONLY  minimum_grade = A", fill=(201, 168, 92), font=_font(22))
    draw.text((36, 54), "Grade B stored, not used. Grade C excluded.", fill=(180, 176, 168), font=_font(14))
    x, y = 36, 90
    by_name = {str(item.get("filename")): item for item in allowed}
    for name in GRADE_A_ORDER:
        item = by_name.get(name)
        if item is None:
            continue
        preview = item.get("_preview")
        tile = Image.new("RGB", (520, 410), (22, 24, 32))
        if isinstance(preview, Image.Image):
            fitted = preview.copy()
            fitted.thumbnail((500, 350), Image.Resampling.LANCZOS)
            tile.paste(fitted, ((520 - fitted.width) // 2, 36))
        ImageDraw.Draw(tile).text((12, 8), f"A  {name}", fill=(201, 168, 92), font=_font(14))
        canvas.paste(tile, (x, y))
        x += 540
        if x > 1500:
            x = 36
            y += 430
    return canvas


def render_executable_systems(catalog: dict[str, dict[str, Any]], allowed: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "EXECUTABLE REFERENCE SYSTEMS — not adjective DNA", fill=(201, 168, 92), font=_font(22))
    x, y = 36, 70
    by_name = {str(item.get("filename")): item for item in allowed}
    for name in GRADE_A_ORDER:
        system = catalog.get(name) or seeded_system(name)
        preview = (by_name.get(name) or {}).get("_preview")
        tile = Image.new("RGB", (520, 480), (22, 24, 32))
        tdraw = ImageDraw.Draw(tile)
        if isinstance(preview, Image.Image):
            fitted = preview.copy()
            fitted.thumbnail((240, 200), Image.Resampling.LANCZOS)
            tile.paste(fitted, (12, 40))
        tdraw.text((12, 8), str(system.get("system_id") or "")[:34], fill=(201, 168, 92), font=_font(14))
        align = dict(system.get("alignment_system") or {})
        color = dict(system.get("color_system") or {})
        canvas_sys = dict(system.get("canvas_system") or {})
        lines = [
            name,
            f"align {align.get('alignment')}",
            f"origin {canvas_sys.get('content_origin')}",
            f"field {color.get('dominant_field')}",
            f"text {color.get('text_color')}  gold {color.get('accent_color')}",
        ]
        ty = 250
        for line in lines:
            tdraw.text((12, ty), str(line)[:46], fill=(220, 216, 208), font=_font(13))
            ty += 22
        canvas.paste(tile, (x, y))
        x += 540
        if x > 1500:
            x = 36
            y += 500
    draw.text((36, 1040), "Forbidden as primary DNA: " + "; ".join(FORBIDDEN_PRIMARY[:3]), fill=(160, 150, 140), font=_font(13))
    return canvas


def render_structure_map(candidate: Image.Image, spec: dict[str, Any]) -> Image.Image:
    im = candidate.convert("RGB").copy()
    draw = ImageDraw.Draw(im)
    palette = {
        "headline": (255, 255, 255),
        "unit_type": (180, 196, 210),
        "price": (201, 168, 92),
        "discount": (201, 140, 72),
        "discount_label": (201, 140, 72),
        "cta": (90, 200, 130),
        "project_logo": (200, 120, 255),
    }
    w, h = im.size
    for item in list(spec.get("editable_commercial_groups") or []):
        role = str(item.get("role") or "")
        box = item.get("bounds")
        if not isinstance(box, dict):
            continue
        x0 = int(float(box["x"]) * w)
        y0 = int(float(box["y"]) * h)
        x1 = int((float(box["x"]) + float(box["w"])) * w)
        y1 = int((float(box["y"]) + float(box["h"])) * h)
        color = palette.get(role, (180, 180, 180))
        draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
        draw.text((x0 + 6, max(4, y0 - 18) if y0 > 22 else y0 + 6), role.upper(), fill=color, font=_font(13))
    bar = Image.new("RGB", (im.width, 44), (12, 14, 20))
    ImageDraw.Draw(bar).text(
        (12, 12),
        f"GraphicFieldMasterDesignSpecV1 — {spec.get('candidate_key')}  {((spec.get('reference_system_provenance') or {}).get('system_id'))}",
        fill=(201, 168, 92),
        font=_font(16),
    )
    out = Image.new("RGB", (im.width, im.height + 44), (12, 14, 20))
    out.paste(bar, (0, 0))
    out.paste(im, (0, 44))
    return out


def render_scorecard(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((32, 24), "PHASE 5.4E CRITIC SCORECARD — FINAL COMPOSITOR  DO NOT PROMOTE", fill=(201, 168, 92), font=_font(22))
    keys = (
        "professional_art_direction",
        "reference_system_fidelity",
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
    y = 70
    for item in candidates:
        critic = dict(item.get("critic") or {})
        ready = dict((item.get("revision_readiness_detail") or {}).get("checks") or {})
        draw.text(
            (32, y),
            f"{item.get('key')}  {item.get('concept')}  sys={item.get('system_id')}  "
            f"arch={item.get('architecture_fidelity')}  "
            f"PRICE={ready.get('PRICE_EDIT_ONLY')} COPY={ready.get('COPY_EDIT_ONLY')} VISUAL={ready.get('VISUAL_REPLACE_ONLY')}",
            fill=(236, 230, 218),
            font=_font(16),
        )
        y += 28
        line = "  ".join(f"{key.split('_')[0][:8]}={critic.get(key)}" for key in keys[:7])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 22
        line = "  ".join(f"{key.split('_')[0][:10]}={critic.get(key)}" for key in keys[7:])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 24
        for chunk in _wrap("Reject: " + ", ".join(item.get("hard_reject") or ["none"]), 118):
            draw.text((32, y), chunk, fill=(220, 120, 90), font=_font(14))
            y += 20
        y += 18
    return canvas


def render_human_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "HUMAN REVIEW BOARD — 5.4E GRAPHIC-FIELD MASTER  ARCHITECTURE B", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 52), "DO NOT PROMOTE. Stop for visual review.", fill=(236, 230, 218), font=_font(16))
    x = 36
    for item in candidates:
        im = item.get("image")
        if isinstance(im, Image.Image):
            tile = im.copy().resize((380, 475), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 90))
        critic = dict(item.get("critic") or {})
        draw.text((x, 578), f"{item.get('key')} {item.get('concept')}", fill=(236, 230, 218), font=_font(14))
        draw.text((x, 600), str(item.get("system_id") or "")[:28], fill=(180, 176, 168), font=_font(13))
        draw.text(
            (x, 622),
            f"art {critic.get('professional_art_direction')}  pub {critic.get('publishability')}  arch {critic.get('architecture_fidelity')}",
            fill=(180, 176, 168),
            font=_font(13),
        )
        draw.text((x, 644), "PENDING HUMAN REVIEW", fill=(201, 168, 92), font=_font(14))
        x += 410
    draw.text((36, 700), "Approved master and production cover were not modified.", fill=(180, 176, 168), font=_font(14))
    draw.text((36, 726), "Phase 5.5 revision was not executed. PRICE/COPY/VISUAL revisions were not tested live.", fill=(180, 176, 168), font=_font(14))
    return canvas


def render_three_way(candidates: list[dict[str, Any]]) -> Image.Image:
    tiles = []
    for item in candidates:
        im = item.get("image")
        if not isinstance(im, Image.Image):
            continue
        resized = im.copy().resize((360, 450), Image.Resampling.LANCZOS)
        bar = 48
        tile = Image.new("RGB", (resized.width, resized.height + bar), (12, 14, 20))
        tile.paste(resized, (0, bar))
        ImageDraw.Draw(tile).text(
            (12, 10),
            f"{item.get('key')}  {str(item.get('concept') or '').replace('_', ' ')}",
            fill=(201, 168, 92),
            font=_font(13),
        )
        ImageDraw.Draw(tile).text((12, 28), str(item.get("system_id") or "")[:34], fill=(180, 176, 168), font=_font(12))
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


def _load_grade_a(db: Session, library: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    filtered = filter_references(list(library.get("references") or []), minimum_grade="A")
    allowed: list[dict[str, Any]] = []
    by_name: dict[str, dict[str, Any]] = {}
    for entry in filtered["allowed"]:
        try:
            raw = _read_bytes(db, UUID(str(entry["asset_id"])))
            preview = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            continue
        blob = dict(entry)
        blob["_preview"] = preview
        allowed.append(blob)
        by_name[str(entry.get("filename"))] = blob
    ordered = []
    for name in GRADE_A_ORDER:
        if name in by_name:
            ordered.append(by_name[name])
    for item in allowed:
        if item not in ordered:
            ordered.append(item)
    return ordered, filtered, 0


def _extract_systems(allowed: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], int]:
    catalog: dict[str, dict[str, Any]] = {}
    calls = 0
    for item in allowed:
        name = str(item.get("filename") or "")
        preview = item.get("_preview")
        if isinstance(preview, Image.Image) and name:
            system, n = request_executable_system(preview, filename=name)
            calls += n
            catalog[name] = system
        else:
            catalog[name] = seeded_system(name)
    return catalog, calls


def _generate_one(
    *,
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    key: str,
    foundation: Image.Image,
    protection: dict[str, Any],
    mask: dict[str, Any],
    catalog: dict[str, dict[str, Any]],
    allowed: list[dict[str, Any]],
    fonts: dict[str, Any],
    logo_rgba: Image.Image | None,
    crop_meta: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    vision = 0
    systems = systems_for_candidate(key, catalog)
    direction = {
        "key": key,
        "concept": systems["concept"],
        "intent": systems["intent"],
    }
    by_name = {str(item.get("filename")): item for item in allowed}
    ref_images: list[Image.Image] = []
    for name in (systems["primary_filename"], systems["secondary_filename"]):
        preview = (by_name.get(name) or {}).get("_preview")
        if isinstance(preview, Image.Image):
            ref_images.append(preview)
    plan, calls = request_graphic_field_plan(
        foundation=foundation,
        protection_preview=mask["visualization"],
        systems=systems,
        references=ref_images,
        direction=direction,
    )
    vision += calls
    prompt = build_graphic_field_prompt(plan, systems, direction)
    field, gen_meta, field_inspect, more = run_graphic_field_pass(
        foundation=foundation,
        mask=mask,
        references=ref_images,
        prompt=prompt,
        quality="high",
        max_retries=2,
    )
    vision += more
    qa = architecture_integrity_qa(
        foundation,
        field,
        mask=mask["mask_l"],
        source_asset_id=LOCKED_HERO_ASSET_ID,
    )
    pack = compose_typography_v2(
        field,
        systems=systems,
        fonts=fonts,
        logo_rgba=logo_rgba,
        protection=protection,
        facts=dict(REQUIRED_FACTS),
    )
    field_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(field),
        content_type="image/png",
        campaign_mode="project-graphic-field",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.4E {key} graphic field {systems.get('system_id')}",
    )
    spec = build_master_spec(
        key=key,
        pack=pack,
        systems=systems,
        crop=crop_meta,
        photo_asset=LOCKED_HERO_ASSET_ID,
        logo_asset=LOCKED_LOGO_ASSET_ID,
        graphic_field_asset_id=str(field_asset.id),
        architecture_lock=mask,
    )
    ready = revision_readiness(spec)
    inspect, calls = inspect_final_candidate(
        candidate=pack["image"],
        foundation=foundation,
        graphic_field=field,
        required=list(REQUIRED_COPY),
    )
    vision += calls
    if pack.get("spire_collision"):
        inspect["spire_collision"] = True
    critic, calls = request_graphic_field_critic(
        candidate=pack["image"],
        foundation=foundation,
        references=ref_images,
        concept=str(systems["concept"]),
        system_id=str(systems.get("system_id") or ""),
    )
    vision += calls
    met, fail_reasons = critic_targets_met_54e(critic) if critic.get("mode") == "vision" else (False, ["critic_unavailable"])
    rejects = hard_reject_54e(inspect=inspect, architecture_qa=qa)
    pixels_ok = bool(gen_meta.get("protected_pixels_unchanged"))
    arch_pass = str(qa.get("architecture_integrity_status") or qa.get("status") or "") == "pass" and pixels_ok
    if not arch_pass and "architecture_changed" not in rejects:
        rejects.append("architecture_changed")
        rejects = sorted(set(rejects))
    final_asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=_png(pack["image"]),
        content_type="image/png",
        campaign_mode="project-graphic-field-master-candidate",
        session_id=str(uuid4()),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt=f"PHASE 5.4E {key} {systems.get('system_id')}",
    )
    return (
        {
            "key": key,
            "concept": systems["concept"],
            "intent": systems["intent"],
            "system_id": systems.get("system_id"),
            "primary_filename": systems.get("primary_filename"),
            "secondary_filename": systems.get("secondary_filename"),
            "plan": _jsonable(plan),
            "generation": _jsonable(gen_meta),
            "field_inspect": field_inspect,
            "inspect": inspect,
            "spec": spec,
            "spec_id": spec["spec_id"],
            "asset_id": str(final_asset.id),
            "graphic_field_id": str(field_asset.id),
            "revision_readiness": ready["revision_readiness"],
            "revision_readiness_detail": ready,
            "architecture_fidelity": "PASS" if arch_pass else "FAIL",
            "architecture_qa": _jsonable(qa),
            "protected_pixels_unchanged": pixels_ok,
            "hard_reject": rejects,
            "internally_rejected": bool(rejects),
            "critic": critic,
            "quality_targets_met": met and not rejects,
            "quality_fail_reasons": fail_reasons,
            "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
            "image": pack["image"],
            "graphic_field": field,
        },
        vision,
    )


def generate_graphic_field_master_4x5(
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
    filtered: dict[str, Any] | None = None
    catalog: dict[str, dict[str, Any]] = {}
    allowed: list[dict[str, Any]] = []
    briefs: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    provenance: dict[str, Any] | None = None
    foundation_meta: dict[str, Any] | None = None

    if location.get("found"):
        library = build_reference_library(db, location)
        if int(library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            allowed, filtered, _ = _load_grade_a(db, library)
            if len(allowed) < 3:
                lock_failed.append("INSUFFICIENT_GRADE_A_REFERENCES")
                status = "FAIL_FAST_INSUFFICIENT_GRADE_A"
            else:
                catalog, sys_calls = _extract_systems(allowed)
                vision_calls += sys_calls
                fonts = build_font_registry()
                source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
                logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
                crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
                graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
                crop_meta = {
                    "centering": list(transform.get("centering") or []),
                    "source_crop": transform.get("source_crop"),
                    "canvas": list(CANVAS_4X5),
                }
                protection, calls = request_protection_map(graded)
                vision_calls += calls
                if not (protection.get("regions") or {}).get("SPIRE"):
                    protection = {
                        "schema": "ProtectedArchitectureMapV1",
                        "regions": dict(HEURISTIC_PROTECTION),
                        "mode": "heuristic",
                    }
                protection_img = render_protection_map(graded, protection)
                mask = architecture_protection_mask_v2(graded, protection)
                logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
                foundation_meta = {
                    "schema": "TempleGraphicFoundationV1",
                    "source_asset_id": LOCKED_HERO_ASSET_ID,
                    "source_filename": HERO_FILENAME,
                    "canvas": list(CANVAS_4X5),
                    "aspect": "4:5",
                    "photographic_grade": dict(LOCKED_GRADE),
                    "text": False,
                    "logo": False,
                    "price": False,
                    "cta": False,
                    "fake_graphic_ui": False,
                    "architecture_protection": "ArchitectureProtectionMaskV2",
                    "protected_coverage": mask.get("protected_coverage"),
                    "composite_rule": mask.get("composite_rule"),
                }
                images["grade_a_board"] = render_grade_a_board(allowed)
                images["executable_systems"] = render_executable_systems(catalog, allowed)
                images["foundation"] = graded
                images["protection"] = mask["visualization"]
                images["protection_map"] = protection_img
                for key in CANDIDATE_KEYS:
                    item, more = _generate_one(
                        db=db,
                        user=user,
                        row=row,
                        key=key,
                        foundation=graded,
                        protection=protection,
                        mask=mask,
                        catalog=catalog,
                        allowed=allowed,
                        fonts=fonts,
                        logo_rgba=logo_rgba,
                        crop_meta=crop_meta,
                    )
                    vision_calls += more
                    candidates.append(item)
                    briefs.append(item["plan"])
                    specs.append(item["spec"])
                provenance = architecture_provenance_qa(
                    source=source,
                    foundation=crop,
                    final=candidates[0]["image"] if candidates else graded,
                    transform=transform,
                )
                images["comparison"] = render_three_way(candidates)
                images["structure"] = render_structure_map(candidates[0]["image"], candidates[0]["spec"]) if candidates else graded
                images["scorecard"] = render_scorecard(candidates)
                images["human_board"] = render_human_board(candidates)
                status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    gpt_calls = provider_call_count()
    serializable_candidates = []
    for item in candidates:
        serializable_candidates.append(
            {k: v for k, v in item.items() if k not in {"image", "graphic_field"}}
        )
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54E,
        "created_at": _now(),
        "status": status,
        "architecture": "B — GRAPHIC FIELD + STRUCTURED COMPOSITOR",
        "generation_model": "gpt-image-2",
        "candidates": serializable_candidates,
        "grade_a_filenames": [str(item.get("filename")) for item in allowed],
        "grade_a_ids": [str(item.get("reference_id")) for item in allowed],
        "filter": _jsonable({k: v for k, v in dict(filtered or {}).items() if k not in {"allowed", "stored_not_used", "excluded"}}),
        "lock_failed": lock_failed,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "provider_call_count": gpt_calls + vision_calls,
        "live_routing_active": True,
        "promoted_to_master": False,
        "existing_master_id": MASTER_COMMERCIAL_R1_ID,
        "existing_master_asset_id": APPROVED_R1_ASSET_ID,
        "existing_master_changed": False,
        "production_cover_changed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "foundation": foundation_meta,
        "provenance_qa": provenance,
        "library_status": (library or {}).get("status") if library else "NOT_BUILT",
        "phase55_executed": False,
        "price_revision_executed": False,
        "copy_revision_executed": False,
        "visual_replace_executed": False,
        "formats_created": False,
        "video_started": False,
        "publishing_started": False,
    }
    tests = [
        t
        for t in list(blob.get("graphic_field_master_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54E)
    ]
    stored = json.loads(json.dumps(record, default=str))
    tests.append(stored)
    blob["graphic_field_master_tests"] = tests
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
        raise RuntimeError("Phase 5.4E refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4E refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4E refused to modify approved creative masters")
    if blob.get("creative_quality_tests") != preserved.get("quality54b"):
        raise RuntimeError("Phase 5.4E refused to overwrite Phase 5.4B history")
    if blob.get("creative_quality_r1_tests") != preserved.get("quality54b_r1"):
        raise RuntimeError("Phase 5.4E refused to overwrite Phase 5.4B-R1 history")
    if blob.get("generative_master_tests") != preserved.get("quality54c"):
        raise RuntimeError("Phase 5.4E refused to overwrite Phase 5.4C history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4E refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library
    record["catalog"] = catalog
    record["briefs"] = briefs
    record["specs"] = specs
    record["candidate_images"] = candidates
    record["allowed"] = [{k: v for k, v in item.items() if k != "_preview"} for item in allowed]
    record["filtered"] = _jsonable(
        {k: ([{kk: vv for kk, vv in e.items() if kk != "_preview"} for e in v] if isinstance(v, list) else v) for k, v in dict(filtered or {}).items()}
    )
    _ = language
    return record
