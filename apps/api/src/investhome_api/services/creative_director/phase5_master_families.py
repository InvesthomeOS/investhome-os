"""Phase 5.4F — Reference-derived Master Families.

Stop generative master experiments. Extract Grade-A craft into structured
families, adapt them to The Temple, produce F1/F2/F3.

GPT Image calls = 0. Does not promote. Does not touch master, cover, or 5.5.
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
from investhome_api.services.creative_director.creative_family_adapter import (
    adapt_family_to_project,
    build_family_master_spec,
    crop_for_family,
    family_revision_readiness,
)
from investhome_api.services.creative_director.creative_font_registry import build_font_registry
from investhome_api.services.creative_director.creative_master_family import (
    GRADE_A_ORDER,
    build_family_library,
    family_by_id,
    request_reference_family,
    seeded_reference_family,
)
from investhome_api.services.creative_director.creative_master_family_router import rank_families, request_router_rationale
from investhome_api.services.creative_director.creative_master_library import MASTER_COMMERCIAL_R1_ID
from investhome_api.services.creative_director.creative_reference_library import (
    attach_media_library_mapping,
    build_reference_library,
    index_design_references_folder,
    locate_design_references,
)
from investhome_api.services.creative_director.graphic_field_director import (
    architecture_protection_mask_v2,
    protected_pixels_unchanged,
)
from investhome_api.services.creative_director.master_design_spec import snapshot_identity
from investhome_api.services.creative_director.phase5_creative_quality import (
    APPROVED_R1_ASSET_ID,
    _HISTORY_KEYS as _BASE_HISTORY,
    _font,
    _preserve as _preserve_base,
    _wrap,
)
from investhome_api.services.creative_director.phase5_design_scene import _vision
from investhome_api.services.creative_director.phase5_photo_foundation import architecture_provenance_qa
from investhome_api.services.creative_director.phase5_premium_commercial_final import _png
from investhome_api.services.creative_director.phase5_production_creative import (
    HEURISTIC_PROTECTION,
    _jpeg_b64,
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
from investhome_api.services.creative_director.reference_quality_filter import filter_references
from investhome_api.services.gpt_image_design.client import provider_call_count, reset_provider_call_count
from investhome_api.services.gpt_image_design.compose import logo_to_rgba
from investhome_api.services.gpt_image_design.persistence import persist_gpt_image
from investhome_api.services.creative_director.structured_typography_compositor_v2 import turkish_copy_is_valid
from investhome_api.services.gpt_image_design.visual_layout_director import VISION_MODEL

WORKFLOW_ID_54F = "phase5_4f_master_families"
REQUIRED_COPY = (
    REQUIRED_FACTS["headline"],
    f"{REQUIRED_FACTS['unit']} {REQUIRED_FACTS['unit_label']}",
    REQUIRED_FACTS["list_price"],
    REQUIRED_FACTS["discount"],
    REQUIRED_FACTS["discount_label"],
    REQUIRED_FACTS["cta"],
)
_HISTORY_KEYS = _BASE_HISTORY + (
    ("creative_quality_tests", "quality54b"),
    ("creative_quality_r1_tests", "quality54b_r1"),
    ("generative_master_tests", "quality54c"),
    ("graphic_field_master_tests", "quality54e"),
)


def _preserve(blob: dict[str, Any]) -> dict[str, Any]:
    preserved = _preserve_base(blob)
    preserved["quality54b"] = list(blob.get("creative_quality_tests") or [])
    preserved["quality54b_r1"] = list(blob.get("creative_quality_r1_tests") or [])
    preserved["quality54c"] = list(blob.get("generative_master_tests") or [])
    preserved["quality54e"] = list(blob.get("graphic_field_master_tests") or [])
    return preserved


def _jsonable(value: Any) -> Any:
    if isinstance(value, Image.Image):
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items() if not str(k).startswith("_")}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _load_grade_a(db: Session, library: dict[str, Any]) -> list[dict[str, Any]]:
    filtered = filter_references(list(library.get("references") or []), minimum_grade="A")
    by_name: dict[str, dict[str, Any]] = {}
    for entry in filtered["allowed"]:
        try:
            raw = _read_bytes(db, UUID(str(entry["asset_id"])))
            preview = Image.open(io.BytesIO(raw)).convert("RGB")
        except Exception:
            continue
        blob = dict(entry)
        blob["_preview"] = preview
        by_name[str(entry.get("filename"))] = blob
    ordered = []
    for name in GRADE_A_ORDER:
        if name in by_name:
            ordered.append(by_name[name])
    return ordered


def render_deconstruction_board(allowed: list[dict[str, Any]], catalog: dict[str, dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 980), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "PHASE 5.4F — GRADE A DECONSTRUCTION  structure, not adjectives", fill=(201, 168, 92), font=_font(22))
    x, y = 36, 70
    for name in GRADE_A_ORDER:
        item = next((a for a in allowed if a.get("filename") == name), None)
        family = catalog.get(name) or seeded_reference_family(name)
        tile = Image.new("RGB", (520, 430), (22, 24, 32))
        tdraw = ImageDraw.Draw(tile)
        preview = (item or {}).get("_preview")
        if isinstance(preview, Image.Image):
            fitted = preview.copy()
            fitted.thumbnail((500, 280), Image.Resampling.LANCZOS)
            tile.paste(fitted, ((520 - fitted.width) // 2, 36))
        tdraw.text((12, 8), f"{name}  {family.get('system_id')}", fill=(201, 168, 92), font=_font(13))
        head = dict(family.get("headline") or {})
        tdraw.text((12, 330), f"align {head.get('alignment')}  scale {head.get('scale_ratio')}", fill=(220, 216, 208), font=_font(13))
        tdraw.text((12, 352), f"origin {((family.get('canvas') or {}).get('content_origin'))}", fill=(180, 176, 168), font=_font(13))
        tdraw.text((12, 374), str((family.get("graphic_devices") or {}).get("fields") or "")[:48], fill=(180, 176, 168), font=_font(13))
        canvas.paste(tile, (x, y))
        x += 540
        if x > 1500:
            x = 36
            y += 450
    return canvas


def render_cluster_board(library: dict[str, Any], allowed: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1600, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "FAMILY CLUSTERS — related systems, not six forced templates", fill=(201, 168, 92), font=_font(22))
    by_name = {str(a.get("filename")): a for a in allowed}
    y = 80
    for cluster in list(library.get("clusters") or []):
        draw.text((36, y), str(cluster.get("family_id")), fill=(236, 230, 218), font=_font(18))
        draw.text((36, y + 26), str(cluster.get("identity"))[:110], fill=(180, 176, 168), font=_font(14))
        x = 36
        y += 54
        for name in list(cluster.get("members") or []):
            preview = (by_name.get(name) or {}).get("_preview")
            if isinstance(preview, Image.Image):
                fitted = preview.copy()
                fitted.thumbnail((220, 160), Image.Resampling.LANCZOS)
                canvas.paste(fitted, (x, y))
            draw.text((x, y + 164), name, fill=(201, 168, 92), font=_font(12))
            x += 240
        y += 200
    return canvas


def render_library_board(library: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1400, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "CreativeMasterFamilyLibraryV1  — internal, not a user picker", fill=(201, 168, 92), font=_font(22))
    y = 80
    for family in list(library.get("families") or []):
        draw.text((36, y), f"{family.get('family_id')}", fill=(236, 230, 218), font=_font(20))
        y += 28
        draw.text((36, y), "refs: " + ", ".join(family.get("source_references") or []), fill=(201, 168, 92), font=_font(14))
        y += 24
        overlay = (family.get("graphic_devices") or {}).get("overlay")
        align = (family.get("headline") or {}).get("alignment")
        draw.text((36, y), f"overlay {overlay}   headline {align}   roles {', '.join(family.get('roles') or [])}", fill=(180, 176, 168), font=_font(14))
        y += 48
    draw.text((36, y + 20), "User request path: understand → evaluate photo → select family internally → adapt → structured master.", fill=(160, 150, 140), font=_font(14))
    return canvas


def render_ranking_board(ranking: dict[str, Any]) -> Image.Image:
    canvas = Image.new("RGB", (1400, 800), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 22), "TEMPLE FAMILY ROUTER — Day_004  not a template picker", fill=(201, 168, 92), font=_font(22))
    y = 80
    for idx, item in enumerate(list(ranking.get("ranking") or []), start=1):
        mark = "F" + str(idx) if idx <= 3 else "  "
        draw.text((36, y), f"{mark}  {idx}. {item.get('family_id')}   score {item.get('score')}   slot {item.get('slot')}", fill=(236, 230, 218), font=_font(18))
        y += 28
        for reason in list(item.get("reasons") or [])[:3]:
            for chunk in _wrap(str(reason), 108):
                draw.text((56, y), chunk, fill=(180, 176, 168), font=_font(14))
                y += 20
        y += 16
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
        ImageDraw.Draw(tile).text((12, 10), f"{item.get('key')}  {item.get('family_id')}", fill=(201, 168, 92), font=_font(13))
        ImageDraw.Draw(tile).text((12, 28), str(item.get("primary_reference") or "")[:34], fill=(180, 176, 168), font=_font(12))
        tiles.append(tile)
    if not tiles:
        return Image.new("RGB", (1088, 400), (12, 14, 20))
    gap = 20
    out = Image.new("RGB", (sum(t.width for t in tiles) + gap * (len(tiles) + 1), tiles[0].height + 40), (12, 14, 20))
    x = gap
    for tile in tiles:
        out.paste(tile, (x, 20))
        x += tile.width + gap
    return out


def render_fidelity_board(candidates: list[dict[str, Any]], allowed: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1680, 720), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 16), "FAMILY FIDELITY — Grade-A source vs Temple adaptation", fill=(201, 168, 92), font=_font(20))
    by_name = {str(a.get("filename")): a for a in allowed}
    x = 24
    for item in candidates:
        src_name = str(item.get("primary_reference") or "")
        preview = (by_name.get(src_name) or {}).get("_preview")
        if isinstance(preview, Image.Image):
            left = preview.copy()
            left.thumbnail((240, 300), Image.Resampling.LANCZOS)
            canvas.paste(left, (x, 56))
        im = item.get("image")
        if isinstance(im, Image.Image):
            right = im.copy()
            right.thumbnail((240, 300), Image.Resampling.LANCZOS)
            canvas.paste(right, (x + 250, 56))
        fid = dict(item.get("fidelity") or {})
        draw.text((x, 370), f"{item.get('key')} {item.get('family_id')}", fill=(236, 230, 218), font=_font(14))
        draw.text((x, 392), f"fidelity {fid.get('family_fidelity')}  hierarchy {fid.get('hierarchy')}", fill=(180, 176, 168), font=_font(13))
        x += 540
    return canvas


def render_scorecard(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1480, 900), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((32, 24), "PHASE 5.4F CRITIC  —  GPT IMAGE 0  DO NOT PROMOTE", fill=(201, 168, 92), font=_font(22))
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
    y = 70
    for item in candidates:
        critic = dict(item.get("critic") or {})
        ready = dict((item.get("revision_readiness_detail") or {}).get("checks") or {})
        draw.text(
            (32, y),
            f"{item.get('key')}  {item.get('family_id')}  arch={item.get('architecture_fidelity')}  "
            f"PRICE={ready.get('PRICE_EDIT_ONLY')} COPY={ready.get('COPY_EDIT_ONLY')} VISUAL={ready.get('VISUAL_REPLACE_ONLY')}",
            fill=(236, 230, 218),
            font=_font(16),
        )
        y += 28
        line = "  ".join(f"{k.split('_')[0][:8]}={critic.get(k)}" for k in keys[:7])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 22
        line = "  ".join(f"{k.split('_')[0][:10]}={critic.get(k)}" for k in keys[7:])
        draw.text((32, y), line, fill=(180, 176, 168), font=_font(14))
        y += 24
        for chunk in _wrap("Reject: " + ", ".join(item.get("hard_reject") or ["none"]), 118):
            draw.text((32, y), chunk, fill=(220, 120, 90), font=_font(14))
            y += 20
        y += 16
    return canvas


def render_human_board(candidates: list[dict[str, Any]]) -> Image.Image:
    canvas = Image.new("RGB", (1280, 1680), (12, 14, 20))
    draw = ImageDraw.Draw(canvas)
    draw.text((36, 24), "HUMAN REVIEW BOARD — 5.4F MASTER FAMILIES", fill=(201, 168, 92), font=_font(20))
    draw.text((36, 52), "GPT IMAGE 0. DO NOT PROMOTE.", fill=(236, 230, 218), font=_font(16))
    x = 36
    for item in candidates:
        im = item.get("image")
        if isinstance(im, Image.Image):
            tile = im.copy().resize((380, 475), Image.Resampling.LANCZOS)
            canvas.paste(tile, (x, 90))
        critic = dict(item.get("critic") or {})
        draw.text((x, 578), f"{item.get('key')} {item.get('family_id')}", fill=(236, 230, 218), font=_font(14))
        draw.text(
            (x, 600),
            f"art {critic.get('professional_art_direction')}  fid {critic.get('family_fidelity')}  pub {critic.get('publishability')}",
            fill=(180, 176, 168),
            font=_font(13),
        )
        draw.text((x, 622), "PENDING HUMAN REVIEW", fill=(201, 168, 92), font=_font(14))
        x += 410
    draw.text((36, 680), "Approved master and production cover were not modified.", fill=(180, 176, 168), font=_font(14))
    draw.text((36, 706), "Phase 5.5 was not executed. This is not a user-facing template picker.", fill=(180, 176, 168), font=_font(14))
    return canvas


def request_family_fidelity(
    *,
    reference: Image.Image,
    candidate: Image.Image,
    family_id: str,
) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 900,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Compare family source vs adaptation. Score structure retention. JSON only. Do not inflate."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Image 1 is the Grade-A family source. Image 2 is the Temple adaptation of {family_id}. "
                            "Do not penalize different buildings or copy. Score 0-10: family_fidelity, hierarchy, "
                            "typography_ratios, spacing_rhythm, image_design_relationship, commercial_hierarchy, "
                            "brand_relationship, cta_behavior, visual_density, graphic_restraint. "
                            "JSON also: notes, broken_identity (boolean)."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(reference)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    parsed["schema"] = "FamilyFidelityScoreV1"
    parsed["family_id"] = family_id
    parsed["mode"] = "vision" if parsed.get("family_fidelity") is not None else "unavailable"
    return parsed, calls


def request_family_critic(*, candidate: Image.Image, foundation: Image.Image, family_id: str) -> tuple[dict[str, Any], int]:
    payload = {
        "model": VISION_MODEL,
        "temperature": 0,
        "max_tokens": 1400,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Independent luxury real-estate art director. Score the FINAL compositor output. Do not inflate. JSON only."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            f"Family {family_id}. Image 1 = Temple adaptation. Image 2 = Day_004 foundation. "
                            "Scores 0-10: professional_art_direction, family_fidelity, composition, "
                            "image_design_integration, typography, hierarchy, commercial_clarity, logo_integration, "
                            "cta_integration, premium_character, readability, architecture_fidelity, publishability. "
                            "Also: spire_collision, unreadable, broken_family_identity, listing_card, dashboard, "
                            "malformed_turkish, architecture_modified, hard_reject_reasons, notes."
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(candidate)}", "detail": "high"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{_jpeg_b64(foundation, quality=70)}", "detail": "low"}},
                ],
            },
        ],
    }
    parsed, calls = _vision(payload)
    parsed = dict(parsed or {})
    parsed["mode"] = "vision" if parsed.get("professional_art_direction") is not None else "unavailable"
    return parsed, calls


def hard_reject_54f(*, inspect: dict[str, Any], pack: dict[str, Any], critic: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    technical_collision = bool(pack.get("spire_collision") or inspect.get("spire_collision"))
    if technical_collision:
        reasons.append("text_spire_collision")
    if inspect.get("unreadable") or critic.get("unreadable"):
        reasons.append("unreadable_content")
    if inspect.get("broken_family_identity") or critic.get("broken_family_identity"):
        reasons.append("broken_family_identity")
    if inspect.get("listing_card") or critic.get("listing_card"):
        reasons.append("listing_card_appearance")
    if inspect.get("dashboard") or critic.get("dashboard"):
        reasons.append("dashboard_appearance")
    critic_turkish = bool(inspect.get("malformed_turkish") or critic.get("malformed_turkish"))
    if critic_turkish and not turkish_copy_is_valid(pack.get("facts") or {}):
        reasons.append("malformed_turkish")
    if inspect.get("architecture_modified") or critic.get("architecture_modified"):
        reasons.append("architecture_modification")
    return sorted(set(reasons))


def generate_master_families_4x5(
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
    library_blob: dict[str, Any] | None = None
    ranking: dict[str, Any] | None = None
    catalog: dict[str, dict[str, Any]] = {}
    allowed: list[dict[str, Any]] = []
    specs: list[dict[str, Any]] = []
    provenance: dict[str, Any] | None = None

    if location.get("found"):
        ref_library = build_reference_library(db, location)
        if int(ref_library.get("image_count") or 0) <= 0:
            lock_failed.append("DESIGN_REFERENCES_EMPTY")
            status = "FAIL_FAST_EMPTY_DESIGN_REFERENCES"
        else:
            allowed = _load_grade_a(db, ref_library)
            if len(allowed) < 3:
                lock_failed.append("INSUFFICIENT_GRADE_A_REFERENCES")
                status = "FAIL_FAST_INSUFFICIENT_GRADE_A"
            else:
                for item in allowed:
                    name = str(item.get("filename") or "")
                    preview = item.get("_preview")
                    if isinstance(preview, Image.Image):
                        family, n = request_reference_family(preview, filename=name)
                        vision_calls += n
                        catalog[name] = family
                    else:
                        catalog[name] = seeded_reference_family(name)
                library_blob = build_family_library(catalog)
                fonts = build_font_registry()
                source = Image.open(io.BytesIO(_read_bytes(db, UUID(LOCKED_HERO_ASSET_ID)))).convert("RGB")
                logo_bytes = _read_bytes(db, UUID(LOCKED_LOGO_ASSET_ID))
                logo_rgba = logo_to_rgba(logo_bytes, "IH_DC_TMP_001_Logo_Primary.svg", "image/svg+xml")
                probe, _crop = crop_for_family(source, {"flexibility": {"crop_bias": {"x": 0.55, "y": 0.48}}})
                protection, calls = request_protection_map(probe)
                vision_calls += calls
                if not (protection.get("regions") or {}).get("SPIRE"):
                    protection = {"schema": "ProtectedArchitectureMapV1", "regions": dict(HEURISTIC_PROTECTION), "mode": "heuristic"}
                mask = architecture_protection_mask_v2(probe, protection)
                ranking = rank_families(library_blob, photo=probe, protection=protection, commercial_density=6)
                ranking, more = request_router_rationale(probe, ranking)
                vision_calls += more
                selected_ids = list(ranking.get("selected") or [])[:3]
                images["deconstruction"] = render_deconstruction_board(allowed, catalog)
                images["clusters"] = render_cluster_board(library_blob, allowed)
                images["library"] = render_library_board(library_blob)
                images["ranking"] = render_ranking_board(ranking)
                by_name = {str(a.get("filename")): a for a in allowed}
                for idx, family_id in enumerate(selected_ids, start=1):
                    family = family_by_id(library_blob, family_id)
                    pack = adapt_family_to_project(
                        source=source,
                        family=family,
                        protection=protection,
                        protect_l=mask["mask_l"],
                        fonts=fonts,
                        logo_rgba=logo_rgba,
                        facts=dict(REQUIRED_FACTS),
                    )
                    pixels_ok = protected_pixels_unchanged(pack["foundation"], pack["fielded"], mask["mask_l"])
                    asset = persist_gpt_image(
                        db,
                        actor=user,
                        linked_project_id=row.linked_project_id,
                        content=_png(pack["image"]),
                        content_type="image/png",
                        campaign_mode="project-master-family-candidate",
                        session_id=str(uuid4()),
                        provider_generation_id=None,
                        campaign_context_id=str(row.id),
                        brief_excerpt=f"PHASE 5.4F F{idx} {family_id}",
                    )
                    spec = build_family_master_spec(
                        key=f"F{idx}",
                        pack=pack,
                        family=family,
                        crop=pack["crop"],
                        photo_asset=LOCKED_HERO_ASSET_ID,
                        logo_asset=LOCKED_LOGO_ASSET_ID,
                        candidate_asset_id=str(asset.id),
                        architecture_lock=mask,
                    )
                    ready = family_revision_readiness(spec)
                    src_preview = (by_name.get(str(family.get("primary_reference"))) or {}).get("_preview")
                    fidelity = {"mode": "unavailable"}
                    if isinstance(src_preview, Image.Image):
                        fidelity, n = request_family_fidelity(
                            reference=src_preview, candidate=pack["image"], family_id=family_id
                        )
                        vision_calls += n
                    critic, n = request_family_critic(
                        candidate=pack["image"], foundation=pack["foundation"], family_id=family_id
                    )
                    vision_calls += n
                    inspect = {
                        "spire_collision": bool(pack.get("spire_collision") or critic.get("spire_collision")),
                        "unreadable": bool(critic.get("unreadable")),
                        "broken_family_identity": bool(fidelity.get("broken_identity") or critic.get("broken_family_identity")),
                        "listing_card": bool(critic.get("listing_card")),
                        "dashboard": bool(critic.get("dashboard")),
                        "malformed_turkish": bool(critic.get("malformed_turkish")),
                        "architecture_modified": (not pixels_ok) or bool(critic.get("architecture_modified")),
                    }
                    rejects = hard_reject_54f(inspect=inspect, pack=pack, critic=critic)
                    if not pixels_ok:
                        rejects = sorted(set(rejects + ["architecture_modification"]))
                    arch_pass = pixels_ok and not pack.get("spire_collision")
                    item = {
                        "key": f"F{idx}",
                        "family_id": family_id,
                        "primary_reference": family.get("primary_reference"),
                        "source_references": family.get("source_references"),
                        "asset_id": str(asset.id),
                        "spec_id": spec["spec_id"],
                        "spec": spec,
                        "placement": pack.get("placement"),
                        "adapter": pack.get("adapter"),
                        "revision_readiness": ready["revision_readiness"],
                        "revision_readiness_detail": ready,
                        "architecture_fidelity": "PASS" if arch_pass else "FAIL",
                        "protected_pixels_unchanged": pixels_ok,
                        "fidelity": fidelity,
                        "critic": critic,
                        "hard_reject": rejects,
                        "internally_rejected": bool(rejects),
                        "approval_status": "CANDIDATE_PENDING_HUMAN_REVIEW",
                        "image": pack["image"],
                        "foundation": pack["foundation"],
                    }
                    candidates.append(item)
                    specs.append(spec)
                provenance = architecture_provenance_qa(
                    source=source,
                    foundation=candidates[0]["foundation"] if candidates else probe,
                    final=candidates[0]["image"] if candidates else probe,
                    transform={"centering": [0.55, 0.48], "source_crop": (0, 0, 1, 1)},
                )
                images["comparison"] = render_three_way(candidates)
                images["fidelity"] = render_fidelity_board(candidates, allowed)
                images["scorecard"] = render_scorecard(candidates)
                images["human_board"] = render_human_board(candidates)
                status = "CANDIDATES_PENDING_HUMAN_REVIEW"
    else:
        lock_failed.append("DESIGN_REFERENCES_NOT_FOUND")

    gpt_calls = provider_call_count()
    record: dict[str, Any] = {
        "test_id": str(uuid4()),
        "workflow": WORKFLOW_ID_54F,
        "created_at": _now(),
        "status": status,
        "master_family_count": int((library_blob or {}).get("family_count") or 0),
        "families_created": [f.get("family_id") for f in list((library_blob or {}).get("families") or [])],
        "router_ranking": _jsonable(ranking),
        "generation_model": None,
        "gpt_image_calls": gpt_calls,
        "vision_calls": vision_calls,
        "candidates": [{k: v for k, v in item.items() if k not in {"image", "foundation"}} for item in candidates],
        "grade_a_filenames": [str(item.get("filename")) for item in allowed],
        "lock_failed": lock_failed,
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
        "phase55_executed": False,
        "price_revision_executed": False,
        "copy_revision_executed": False,
        "visual_replace_executed": False,
        "formats_created": False,
        "video_started": False,
        "publishing_started": False,
        "user_facing_template_picker": False,
    }
    tests = [
        t
        for t in list(blob.get("master_family_tests") or [])
        if not (isinstance(t, dict) and t.get("workflow") == WORKFLOW_ID_54F)
    ]
    stored = json.loads(json.dumps(record, default=str))
    tests.append(stored)
    blob["master_family_tests"] = tests
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
        raise RuntimeError("Phase 5.4F refused to overwrite Phase 5.4A-R1")
    if blob.get("master_revision_tests") != preserved["revision"]:
        raise RuntimeError("Phase 5.4F refused to overwrite Phase 5.5 revision history")
    if blob.get("approved_creative_masters") != preserved["approved_creative"]:
        raise RuntimeError("Phase 5.4F refused to modify approved creative masters")
    if blob.get("graphic_field_master_tests") != preserved.get("quality54e"):
        raise RuntimeError("Phase 5.4F refused to overwrite Phase 5.4E history")
    if str(ctx.get("current_cover_asset_id") or "") not in {"", PRODUCTION_COVER_V2} and str(
        ctx.get("current_cover_asset_id")
    ) != str(original.get("current_cover_asset_id") or ""):
        raise RuntimeError("Phase 5.4F refused to change production cover")
    row.context_json = ctx
    flag_modified(row, "context_json")
    db.flush()
    record["images"] = images
    record["library"] = library_blob
    record["catalog"] = catalog
    record["specs"] = specs
    record["candidate_images"] = candidates
    record["allowed"] = [{k: v for k, v in item.items() if k != "_preview"} for item in allowed]
    record["ranking"] = ranking
    _ = language
    return record
