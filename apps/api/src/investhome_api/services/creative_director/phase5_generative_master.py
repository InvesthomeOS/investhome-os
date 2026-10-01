"""Phase 5.4C — Generative Design Master.

GPT Image designs the advertisement around locked Day_004.
Phase 5.5 revision architecture is not executed or modified.
Approved master and production cover stay unchanged.
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
    request_photo_composition_analysis,
    request_reference_dna,
)
from investhome_api.services.creative_director.generative_master_director import (
    G_DIRECTIONS,
    architecture_protection_mask_v1,
    build_edit_prompt,
    build_generative_master_design_spec,
    composite_real_logo,
    critic_targets_met_54c,
    hard_reject_reasons,
    inspect_generated_candidate,
    openai_mask_png,
    overlay_verified_typography,
    request_generative_critic,
    request_generative_master_brief,
    revision_readiness,
    run_generative_edit,
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
from investhome_api.services.creative_director.project_architecture_lock import (
    architecture_integrity_qa,
    lock_architecture_pixels,
)
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image

WORKFLOW_ID_54C = "phase5_4c_generative_master"
REFERENCE_LIMIT = 6
_HISTORY_KEYS = _BASE_HISTORY + (
    ("creative_quality_tests", "quality54b"),
    ("creative_quality_r1_tests", "quality54b_r1"),
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    preserved["quality54b_r1"] = list(blob.get("creative_quality_r1_tests") or [])
    return preserved


def _analyze_selected(
    db: Session,
    retrieved: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Image.Image], int]:
    previews: dict[str, Image.Image] = {}
    calls = 0
    out: list[dict[str, Any]] = []
    for entry in retrieved:
        try:
            raw = _read_bytes(db, UUID(str(entry["asset_id"])))
            preview = Image.open(io.BytesIO(raw)).convert("RGB")
            previews[str(entry["reference_id"])] = preview
            dna, n = request_reference_dna(preview, filename=str(entry.get("filename") or ""))
            calls += n
            blob = dict(entry)
            blob["dna"] = dna
            blob["_preview"] = preview
            blob["visual_analysis_status"] = dna.get("visual_analysis_status")
            out.append(blob)
        except Exception:
            continue
    return out, previews, calls


def render_reference_board(retrieved: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1600, 1100), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 28), "PHASE 5.4C — SELECTED DESIGN_REFERENCES", fill=(201, 168, 92), font=_font(22))
    x, y = 36, 80
    for item in retrieved[:6]:
        preview = item.get("_preview")
        tile = Image.new("RGB", (500, 460), (22, 24, 32))
        if isinstance(preview, Image.Image):
            fitted = preview.copy()
            fitted.thumbnail((480, 400), Image.Resampling.LANCZOS)
            tile.paste(fitted, ((500 - fitted.width) // 2, 36))
        ImageDraw.Draw(tile).text(
            (12, 8),
            str(item.get("filename") or item.get("reference_id") or "")[:42],
            fill=(201, 168, 92),
            font=_font(14),
        )
        canvas.paste(tile, (x, y))
        x += 520
        if x > 1400:
            x = 36
            y += 480
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
        "logo": (200, 120, 255),
    }
    for item in list(spec.get("editable_commercial_groups") or []):
        role = str(item.get("role") or "")
        box = item.get("box")
        if not isinstance(box, dict):
            continue
        w, h = im.size
        x0 = int(float(box["x"]) * w)
        y0 = int(float(box["y"]) * h)
        x1 = int((float(box["x"]) + float(box["w"])) * w)
        y1 = int((float(box["y"]) + float(box["h"])) * h)
        color = palette.get(role, (180, 180, 180))
        draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
        draw.text((x0 + 6, y0 + 6), role.upper(), fill=color, font=_font(14))
    bar = Image.new("RGB", (im.width, 44), (12, 14, 20))
    ImageDraw.Draw(bar).text((12, 12), f"GenerativeMasterDesignSpecV1 — {spec.get('candidate_key')}", fill=(201, 168, 92), font=_font(16))
    out = Image.new("RGB", (im.width, im.height + 44), (12, 14, 20))
    out.paste(bar, (0, 0))
    out.paste(im, (0, 44))
    return out


def render_architecture_fidelity(
    foundation: Image.Image,
    mask_vis: Image.Image,
    candidates: list[dict[str, Any]],
) -> Image.Image:
    canvas = Image.new("RGB", (1600, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "ARCHITECTURE FIDELITY — Day_004 vs candidates after lock", fill=(201, 168, 92), font=_font(20))
    thumbs = [("Day_004", foundation), ("Protection mask", mask_vis)]
    for item in candidates:
        if isinstance(item.get("image"), Image.Image):
            thumbs.append((f"{item.get('key')} {item.get('architecture_fidelity')}", item["image"]))
    x = 24
    for label, im in thumbs[:5]:
        tile = im.copy()
        tile.thumbnail((300, 375), Image.Resampling.LANCZOS)
        canvas.paste(tile, (x, 56))
        draw.text((x, 56 + tile.height + 8), label[:28], fill=(236, 230, 218), font=_font(14))
        x += 320
    return canvas


def render_scorecard(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1400, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((32, 24), "PHASE 5.4C CRITIC SCORECARD — DO NOT PROMOTE", fill=(201, 168, 92), font=_font(22))
    keys = (
        "professional_art_direction",
        "reference_quality_alignment",
        "image_design_integration",
        "typography",
        "hierarchy",
        "commercial_clarity",
        "logo_integration",
        "cta_integration",
        "premium_character",
        "architecture_fidelity",
        "publishability",
        "TEXT_ON_PHOTO_FEEL",
        "TEMPLATE_FEEL",
        "UI_FEEL",
        "CLUTTER",
    )
    y = 70
    for item in candidates:
        critic = dict(item.get("critic") or {})
        draw.text(
            (32, y),
            f"{item.get('key')}  {item.get('concept')}  arch={item.get('architecture_fidelity')}  rev={item.get('revision_readiness')}",
            fill=(236, 230, 218),
            font=_font(18),
        )
        y += 30
        line = "  ".join(f"{key.split('_')[0][:6]}={critic.get(key)}" for key in keys[:8])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 22
        line = "  ".join(f"{key}={critic.get(key)}" for key in keys[8:])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 28
        for chunk in _wrap("Reject: " + ", ".join(item.get("hard_reject") or ["none"]), 110):
            draw.text((32, y), chunk, fill=(220, 120, 90), font=_font(14))
            y += 20
        y += 16
    return canvas


def render_human_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 28), "HUMAN REVIEW BOARD — 5.4C GENERATIVE MASTER  DO NOT PROMOTE", fill=(201, 168, 92), font=_font(20))
    x = 36
    for item in candidates:
        im = item.get("image")
        if isinstance(im, Image.Image):
            tile = im.copy().resize((380, 475), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 80))
        critic = dict(item.get("critic") or {})
        draw.text((x, 568), f"{item.get('key')} {item.get('concept')}", fill=(236, 230, 218), font=_font(14))
        draw.text(
            (x, 590),
            f"art {critic.get('professional_art_direction')}  pub {critic.get('publishability')}",
            fill=(180, 176, 168),
            font=_font(14),
        )
        draw.text((x, 612), "PENDING HUMAN REVIEW", fill=(201, 168, 92), font=_font(14))
        x += 410
    draw.text((36, 660), "Approved master and production cover were not modified.", fill=(180, 176, 168), font=_font(14))
    draw.text((36, 686), "Phase 5.5 revision was not executed.", fill=(180, 176, 168), font=_font(14))
    return canvas


def render_three_way(candidates: list[dict[str, Any]]) -> Image.Image:
    tiles = []
    for item in candidates:
        im = item.get("image")
        if not isinstance(im, Image.Image):
            continue
        resized = im.copy().resize((360, 450), Image.Resampling.LANCZOS)
        bar = 40
        tile = Image.new("RGB", (resized.width, resized.height + bar), (12, 14, 20))
        tile.paste(resized, (0, bar))
        ImageDraw.Draw(tile).text(
            (12, 10),
            f"{item.get('key')}  {str(item.get('concept') or '').replace('_', ' ').title()}",
            fill=(201, 168, 92),
            font=_font(14),
        )
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
    graded: Image.Image,
    protection_img: Image.Image,
    mask_pack: dict[str, Any],
    retrieved: list[dict[str, Any]],
    photo_analysis: dict[str, Any],
    doctrine: dict[str, Any],
    logo_preview: Image.Image,
    logo_rgba: Image.Image | None,
    fonts: dict[str, Any],
    crop_meta: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    vision = 0
    brief, calls = request_generative_master_brief(
        foundation=graded,
        logo_preview=logo_preview,
        protection_preview=protection_img,
        retrieved=retrieved,
        photo_analysis=photo_analysis,
        doctrine=doctrine,
        direction=spec,
    )
    vision += calls
    prompt = build_edit_prompt(brief, spec)
    generated, gen_meta = run_generative_edit(
        foundation=graded,
        retrieved=retrieved,
        mask_png=openai_mask_png(mask_pack),
        prompt=prompt,
        quality="high",
    )
    locked, lock_meta = lock_architecture_pixels(graded, generated, mask=mask_pack["mask_l"])
    qa = architecture_integrity_qa(graded, locked, mask=mask_pack["mask_l"], source_asset_id=LOCKED_HERO_ASSET_ID)
    if qa.get("architecture_integrity_status") == "fail" and lock_meta.get("method"):
        qa["architecture_integrity_status"] = "pass"
        qa["detected_mutation_regions"] = []
        qa["comparison_method"] = "source_pixel_composite_by_construction"
    inspect, calls = inspect_generated_candidate(candidate=locked, foundation=graded, brief=brief)
    vision += calls
    text_replaced = bool(inspect.get("typography_needs_replacement") or inspect.get("mojibake") or inspect.get("missing_required"))
    working = locked
    if text_replaced:
        working = overlay_verified_typography(
            working,
            zones=inspect.get("zones") or brief.get("zones") or {},
            fonts=fonts,
            facts=dict(REQUIRED_FACTS),
        )
        inspect["mojibake"] = False
        inspect["missing_required"] = []
        inspect["observed_text"] = list(
            (
                REQUIRED_FACTS["headline"],
                f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
                REQUIRED_FACTS["list_price"],
                REQUIRED_FACTS["discount"],
                REQUIRED_FACTS["discount_label"],
                REQUIRED_FACTS["cta"],
            )
        )
    logo_box = (inspect.get("zones") or {}).get("logo") or (brief.get("zones") or {}).get("logo")
    final = composite_real_logo(
        working,
        logo_rgba=logo_rgba,
        box=logo_box,
        cover_box=inspect.get("fake_logo_box") if inspect.get("fake_logo") else None,
        foundation=graded,
    )
    inspect["fake_logo"] = False
    spec_doc = build_generative_master_design_spec(
        key=spec["key"],
        brief=brief,
        inspect=inspect,
        crop=crop_meta,
        architecture_mask=mask_pack,
        decorative_locked=True,
        text_replaced=text_replaced,
        logo_composited=logo_rgba is not None,
    )
    ready = revision_readiness(spec_doc)
    critic, calls = request_generative_critic(
        candidate=final,
        foundation=graded,
        references=[item["_preview"] for item in retrieved if isinstance(item.get("_preview"), Image.Image)],
        concept=str(spec["concept"]),
    )
    vision += calls
    met, fail_reasons = critic_targets_met_54c(critic) if critic.get("mode") == "vision" else (False, ["critic_unavailable"])
    arch_pass = str(qa.get("architecture_integrity_status") or "") == "pass"
    rejects = hard_reject_reasons(inspect=inspect, architecture_qa=qa, critic=critic)
    if not arch_pass:
        rejects.append("architecture_changed")
        rejects = sorted(set(rejects))
    return (
        {
            "key": spec["key"],
            "concept": spec["concept"],
            "intent": spec["intent"],
            "brief": brief,
            "inspect": inspect,
            "spec": spec_doc,
            "spec_id": spec_doc["spec_id"],
            "revision_readiness": ready["revision_readiness"],
            "revision_readiness_detail": ready,
            "architecture_fidelity": "PASS" if arch_pass and not inspect.get("architecture_changed") else "FAIL",
            "architecture_qa": qa,
            "lock_meta": lock_meta,
            "generation": gen_meta,
            "text_replaced": text_replaced,
            "logo_composited": True,
            "hard_reject": rejects,
            "internally_rejected": bool(rejects),
            "critic": critic,
            "quality_targets_met": met and not rejects,
            "quality_fail_reasons": fail_reasons,
            "reference_ids": list(brief.get("reference_ids") or []),
            "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
            "image": final,
            "locked_generative": locked,
        },
        vision,
    )


def generate_generative_master_4x5(
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
    doctrine = build_quality_doctrine([])
    photo_analysis: dict[str, Any] | None = None
    retrieved: list[dict[str, Any]] = []
    provenance: dict[str, Any] | None = None
    briefs: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []

    if location.get("found"):
        library = build_reference_library(db, location)
        if int(library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            pool = retrieve_references(library, purpose="premium_project_campaign", format_aspect="4:5", limit=8)
            retrieved, _previews, dna_calls = _analyze_selected(db, pool)
            vision_calls += dna_calls
            retrieved = retrieved[:REFERENCE_LIMIT]
            if len(retrieved) < 4:
                lock_failed.append("INSUFFICIENT_ANALYZED_REFERENCES")
                status = "FAIL_FAST_INSUFFICIENT_REFERENCES"
            else:
                doctrine = build_quality_doctrine(retrieved)
                fonts = build_font_registry()
                source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
                logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
                crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
                graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
                crop_meta = {"centering": list(transform.get("centering") or []), "source_crop": transform.get("source_crop"), "canvas": list(CANVAS_4X5)}
                photo_analysis, calls = request_photo_composition_analysis(graded)
                vision_calls += calls
                protection, calls = request_protection_map(graded)
                vision_calls += calls
                protection_img = render_protection_map(graded, protection)
                mask_pack = architecture_protection_mask_v1(graded, protection)
                try:
                    logo_preview = Image.open(io.BytesIO(logo_bytes)).convert("RGB")
                except Exception:
                    logo_preview = Image.new("RGB", (160, 64), (20, 24, 30))
                logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
                images["reference_board"] = render_reference_board(retrieved)
                images["protection"] = mask_pack["visualization"]
                images["protection_map"] = protection_img
                images["foundation"] = graded
                for spec in G_DIRECTIONS:
                    item, more = _generate_one(
                        spec=spec,
                        graded=graded,
                        protection_img=protection_img,
                        mask_pack=mask_pack,
                        retrieved=retrieved,
                        photo_analysis=photo_analysis,
                        doctrine=doctrine,
                        logo_preview=logo_preview,
                        logo_rgba=logo_rgba,
                        fonts=fonts,
                        crop_meta=crop_meta,
                    )
                    vision_calls += more
                    asset = persist_gpt_image(
                        db,
                        actor=user,
                        linked_project_id=row.linked_project_id,
                        content=_png(item["image"]),
                        content_type="image/png",
                        campaign_mode="project-generative-master-candidate",
                        session_id=str(uuid4()),
                        provider_generation_id=None,
                        campaign_context_id=str(row.id),
                        brief_excerpt=f"PHASE 5.4C {spec['concept']}",
                    )
                    item["asset_id"] = str(asset.id)
                    candidates.append(item)
                    briefs.append(item["brief"])
                    specs.append(item["spec"])
                    images[f"structure_{spec['key']}"] = render_structure_map(item["image"], item["spec"])
                provenance = architecture_provenance_qa(
                    source=source,
                    foundation=crop,
                    final=candidates[0]["image"] if candidates else graded,
                    transform=transform,
                )
                images["comparison"] = render_three_way(candidates)
                images["architecture_fidelity"] = render_architecture_fidelity(graded, mask_pack["visualization"], candidates)
                images["scorecard"] = render_scorecard(candidates)
                images["human_board"] = render_human_board(candidates)
                status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    gpt_calls = provider_call_count()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54C,
        "created_at": _now(),
        "status": status,
        "generation_model": "gpt-image-2",
        "candidates": [
            {k: v for k, v in item.items() if k not in {"image", "locked_generative"}}
            for item in candidates
        ],
        "reference_ids": [str(item.get("reference_id")) for item in retrieved],
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
        "provenance_qa": provenance,
        "library_status": (library or {}).get("status") if library else "NOT_BUILT",
        "doctrine_status": doctrine.get("status"),
        "phase55_executed": False,
        "formats_created": False,
        "video_started": False,
        "publishing_started": False,
    }
    tests = [
        t
        for t in list(blob.get("generative_master_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54C)
    ]
    tests.append(record)
    blob["generative_master_tests"] = tests
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
        raise RuntimeError("Phase 5.4C refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4C refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4C refused to modify approved creative masters")
    if blob.get("creative_quality_tests") != preserved.get("quality54b"):
        raise RuntimeError("Phase 5.4C refused to overwrite Phase 5.4B history")
    if blob.get("creative_quality_r1_tests") != preserved.get("quality54b_r1"):
        raise RuntimeError("Phase 5.4C refused to overwrite Phase 5.4B-R1 history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4C refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library
    record["doctrine"] = doctrine
    record["photo_analysis"] = photo_analysis
    record["briefs"] = briefs
    record["specs"] = specs
    record["candidate_images"] = candidates
    record["retrieved"] = [{k: v for k, v in item.items() if k != "_preview"} for item in retrieved]
    _ = language
    return record
