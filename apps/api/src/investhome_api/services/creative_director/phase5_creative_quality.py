"""Phase 5.4B — creative quality engine.

Stops if DESIGN_REFERENCES cannot be located. Does not generate from invented
references. Does not overwrite the approved 5.4A-R1 master or Phase 5.5 history.
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
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_quality_doctrine import build_quality_doctrine
from investhome_api.services.creative_director.creative_reference_library import (
    CANONICAL_FOLDER_NAME,
    build_reference_library,
    index_design_references_folder,
    locate_design_references,
    attach_media_library_mapping,
    retrieve_references,
)
from investhome_api.services.creative_director.generative_creative_director_v2 import (
    critic_targets_met,
    normalize_candidates,
    request_concept_set,
    request_critic_v2,
    request_photo_composition_analysis,
    request_reference_dna,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_design_scene import font_face_css, inline_logo_svg, _jpeg_data_uri
from investhome_api.services.creative_director.phase5_photo_foundation import (
    CANVAS_4X5,
    _centering_from_mass,
    apply_photographic_grade,
    architecture_provenance_qa,
    cover_fit_canvas,
)
from investhome_api.services.creative_director.phase5_premium_commercial_r1 import LOCKED_GRADE
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png, _render_scene
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

WORKFLOW_ID_54B = "phase5_4b_creative_quality"
APPROVED_R1_ASSET_ID = "32f6deee-ca4d-45a5-8dc3-303052609d35"
MAX_DNA_IMAGES = 10
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
    ("master_revision_tests", "revision"),
)


def _count_keys(blob: dict[str, Any]) -> dict[str, int]:
    return {f"{key}_count": len(list(blob.get(key) or [])) for key, _alias in _HISTORY_KEYS}


def _font(size: int = 16):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def _wrap(text: str, width: int) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if len(trial) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_location_board(location: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1088, 1360), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    font = _font(18)
    small = _font(14)
    y = 40
    draw.text((40, y), "PHASE 5.4B — DESIGN_REFERENCES LOCATOR", fill=(201, 168, 92), font=font)
    y += 40
    found = bool(location.get("found"))
    draw.text((40, y), "FOUND" if found else "NOT FOUND — FAIL FAST", fill=(80, 200, 120) if found else (220, 80, 80), font=font)
    y += 36
    media = dict(location.get("media_library_search") or {})
    named = dict(location.get("drive_name_query") or {})
    full = dict(location.get("drive_full_scope") or {})
    account = dict(full.get("connected_account") or {})
    prev = dict(location.get("previous_search_root") or {})
    lines = [
        f"Canonical name: {CANONICAL_FOLDER_NAME} (also DESIGN_REFERENCE)",
        f"Connected Drive account: {account.get('email') or 'unknown'}",
        f"Previous search root: {prev.get('name')} / {prev.get('id')}",
        f"Correct search root: {location.get('correct_search_root')}",
        f"Full-scope unique folders: {full.get('unique_folder_count')}",
        f"sharedWithMe folders: {full.get('shared_with_me_folder_count')}",
        f"Media Library folders scanned: {media.get('folder_count_scanned')}",
        f"Name-query matches: {len(named.get('matches') or [])}",
        "",
        str(location.get("reason") or ""),
        "",
        "Did not fall back to prior Investhome OS experiment PNGs.",
        "Did not invent design references.",
        "Did not generate generic ads without references.",
    ]
    for line in lines:
        for chunk in _wrap(line, 88):
            draw.text((40, y), chunk, fill=(236, 230, 218), font=small)
            y += 22
            if y > 1280:
                return canvas
    return canvas


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = {
        "session": blob.get("current_session_id"),
        "family": blob.get("current_format_family_id"),
        "approved": {mid: dict(rec) for mid, rec in dict(blob.get("approved_masters") or {}).items()},
        "approved_creative": {mid: dict(rec) for mid, rec in dict(blob.get("approved_creative_masters") or {}).items()},
        "sessions": dict(blob.get("sessions") or {}),
    }
    for key, alias in _HISTORY_KEYS:
        preserved[alias] = list(blob.get(key) or [])
    return preserved


def _analyze_references(db: Session, library: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Image.Image], int]:
    dna_rows: list[dict[str, Any]] = []
    previews: dict[str, Image.Image] = {}
    calls_total = 0
    skipped = list(library.get("skipped") or [])
    for entry in list(library.get("references") or [])[:MAX_DNA_IMAGES]:
        try:
            raw = _read_bytes(db, UUID(str(entry["asset_id"])))
            preview = Image.open(io.BytesIO(raw)).convert("RGB")
            previews[str(entry["reference_id"])] = preview
            dna, calls = request_reference_dna(preview, filename=str(entry.get("filename") or ""))
            calls_total += calls
            dna["reference_id"] = entry["reference_id"]
            dna["asset_id"] = entry["asset_id"]
            dna["filename"] = entry.get("filename")
            dna_rows.append(dna)
            entry["visual_analysis_status"] = dna.get("visual_analysis_status")
            entry["reference_quality_status"] = "ANALYZED" if dna.get("visual_analysis_status") == "ANALYZED" else "FAILED"
        except Exception as exc:
            skipped.append({"asset_id": entry.get("asset_id"), "filename": entry.get("filename"), "reason": f"unreadable:{exc}"})
            entry["visual_analysis_status"] = "FAILED"
    library["skipped"] = skipped
    library["dna"] = dna_rows
    library["skipped_count"] = len(skipped)
    return library, previews, calls_total


def _render_candidates(
    db: Session,
    user: User,
    row: CreativeDirectorCampaign,
    *,
    retrieved: list[dict[str, Any]],
    doctrine: dict[str, Any],
    graded: Image.Image,
    photo_analysis: dict[str, Any],
    fonts: dict[str, Any],
    photo_uri: str,
    logo_markup: str,
    font_css: str,
    logo_preview: Image.Image,
) -> tuple[list[dict[str, Any]], int]:
    concept_set, calls = request_concept_set(
        foundation=graded,
        photo_analysis=photo_analysis,
        doctrine=doctrine,
        retrieved=retrieved,
        fonts=fonts,
        facts=dict(REQUIRED_FACTS),
        logo_preview=logo_preview,
    )
    vision_calls = calls
    normalized = normalize_candidates(concept_set, dict(REQUIRED_FACTS), photo_uri)
    out: list[dict[str, Any]] = []
    for item in normalized:
        markup = str(item.get("markup") or "")
        if not markup:
            item["render_error"] = "missing_markup"
            out.append(item)
            continue
        pack = _render_scene(
            markup,
            photo_uri=photo_uri,
            logo_markup=logo_markup,
            font_css=font_css,
            facts=dict(REQUIRED_FACTS),
        )
        critic, calls = request_critic_v2(candidate=pack["image"], foundation=graded, concept=str(item.get("concept")))
        vision_calls += calls
        met, reasons = critic_targets_met(critic) if critic.get("mode") == "vision" else (False, ["critic_unavailable"])
        asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=_png(pack["image"]),
            content_type="image/png",
            campaign_mode="project-creative-quality-candidate",
            session_id=str(uuid4()),
            provider_generation_id=None,
            campaign_context_id=str(row.id),
            brief_excerpt=f"PHASE 5.4B {item.get('concept')}",
        )
        item["asset_id"] = str(asset.id)
        item["image"] = pack["image"]
        item["rendered"] = pack
        item["critic"] = critic
        item["quality_targets_met"] = met
        item["quality_fail_reasons"] = reasons
        out.append(item)
    return out, vision_calls


def generate_creative_quality_4x5(
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
    before.update(_count_keys({key: preserved[alias] for key, alias in _HISTORY_KEYS}))

    location = locate_design_references(db)
    if location.get("found") and (location.get("folder") or {}).get("drive_folder_id"):
        index_result = index_design_references_folder(db, location)
        location = attach_media_library_mapping(db, location)
        location["index_result"] = index_result
        if index_result.get("reason") == "credential_cannot_read":
            location["readable"] = False
            location["reason"] = (
                "DESIGN_REFERENCES was located but the application Drive credential cannot read its contents. "
                f"{index_result.get('error')}"
            )
    vision_calls = 0
    candidates: list[dict[str, Any]] = []
    library: dict[str, Any] | None = None
    doctrine = build_quality_doctrine([])
    photo_analysis: dict[str, Any] | None = None
    retrieved: list[dict[str, Any]] = []
    images: dict[str, Any] = {"location_board": render_location_board(location)}
    lock_failed: list[str] = []
    status = "FAIL_FAST_MISSING_DESIGN_REFERENCES"
    provenance: dict[str, Any] | None = None

    if location.get("index_result", {}).get("reason") == "credential_cannot_read":
        lock_failed.append("DESIGN_REFERENCES_UNREADABLE")
        status = "FAIL_FAST_UNREADABLE_DESIGN_REFERENCES"
    elif location.get("found"):
        library = build_reference_library(db, location)
        if int(library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            library, previews, dna_calls = _analyze_references(db, library)
            vision_calls += dna_calls
            analyzed = [row for row in list(library.get("dna") or []) if row.get("visual_analysis_status") == "ANALYZED"]
            if not analyzed:
                lock_failed.append("NO_VISUAL_DNA")
                status = "FAIL_FAST_NO_VISUAL_ANALYSIS"
            else:
                retrieved = retrieve_references(library, purpose="premium_project_campaign", format_aspect="4:5")
                for item in retrieved:
                    preview = previews.get(str(item.get("reference_id")))
                    if preview is not None:
                        item["_preview"] = preview
                doctrine = build_quality_doctrine(retrieved)
                fonts = build_font_registry()
                source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
                logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
                crop, transform = cover_fit_canvas(source, CANVAS_4X5, centering=_centering_from_mass(source))
                graded = apply_photographic_grade(crop, dict(LOCKED_GRADE))
                photo_uri = _jpeg_data_uri(graded)
                photo_analysis, calls = request_photo_composition_analysis(graded)
                vision_calls += calls
                try:
                    logo_preview = Image.open(io.BytesIO(logo_bytes)).convert("RGB")
                except Exception:
                    logo_preview = Image.new("RGB", (80, 32), (20, 24, 30))
                candidates, more = _render_candidates(
                    db,
                    user,
                    row,
                    retrieved=retrieved,
                    doctrine=doctrine,
                    graded=graded,
                    photo_analysis=photo_analysis,
                    fonts=fonts,
                    photo_uri=photo_uri,
                    logo_markup=inline_logo_svg(logo_bytes),
                    font_css=font_face_css(fonts),
                    logo_preview=logo_preview,
                )
                vision_calls += more
                first = next((item.get("image") for item in candidates if isinstance(item.get("image"), Image.Image)), graded)
                provenance = architecture_provenance_qa(source=source, foundation=crop, final=first, transform=transform)
                images.update({"source": source, "crop": crop, "foundation": graded})
                status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54B,
        "created_at": _now(),
        "status": status,
        "location": dict(location),
        "library_status": (library or {}).get("status") if library else "NOT_BUILT",
        "dna_status": "ANALYZED"
        if any(d.get("visual_analysis_status") == "ANALYZED" for d in list((library or {}).get("dna") or []))
        else "NOT_RUN",
        "doctrine_status": doctrine.get("status"),
        "photo_analysis_id": None if photo_analysis is None else str(uuid4()),
        "candidates": [{k: v for k, v in item.items() if k not in {"image", "rendered", "_preview"}} for item in candidates],
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
        "visual_replace_executed": False,
        "price_revision_executed": False,
        "project_id": TEMPLE_PROJECT_ID,
        "source_photo": LOCKED_HERO_ASSET_ID,
        "source_filename": HERO_FILENAME,
        "logo_asset_id": LOCKED_LOGO_ASSET_ID,
        "provenance_qa": provenance,
    }
    if library is not None:
        record["library_summary"] = {
            "file_count": library.get("file_count"),
            "image_count": library.get("image_count"),
            "skipped_count": library.get("skipped_count"),
            "analyzed": len([d for d in list(library.get("dna") or []) if d.get("visual_analysis_status") == "ANALYZED"]),
        }
    tests = [
        t
        for t in list(blob.get("creative_quality_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54B)
    ]
    tests.append({k: v for k, v in record.items()})
    blob["creative_quality_tests"] = tests
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
    after.update(_count_keys(blob))
    _production_guard(before, after)
    if blob.get("premium_commercial_r1_tests") != preserved["r1"]:
        raise RuntimeError("Phase 5.4B refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4B refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4B refused to modify approved creative masters")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4B refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library
    record["doctrine"] = doctrine
    record["photo_analysis"] = photo_analysis
    record["retrieved"] = [{k: v for k, v in item.items() if k != "_preview"} for item in retrieved]
    record["candidate_images"] = candidates
    _ = language
    return record


