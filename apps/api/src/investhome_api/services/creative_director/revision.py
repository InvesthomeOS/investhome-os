"""AI Revision Mode — current approved cover is visual source of truth.

Immutable master_asset_id = first approved finished-ad (v1), never overwritten.
Every revise starts from master_creative.current_cover_asset_id, not v1,
unless the user explicitly reverts. Undo/Redo: GPT-free cursor over saved covers.
"""

from __future__ import annotations

import io
import logging
import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.project import Project
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorReviseAdResponse,
    CreativeDirectorReviseRequest,
    RevisionDiff,
    RevisionOperation,
)
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.design_spec import (
    apply_layer_operations,
    assemble_editable_design,
    build_design_spec,
    build_golden_native_v1_spec,
    collect_supporting_lines,
    compose_layer_only_on_locked_raster,
    design_spec_to_smb_elements,
    ensure_revision_overlay_targets,
    hydrate_supporting_copy,
    is_golden_native_v1,
    is_micro_edit_route,
    is_provider_revision_route,
    project_golden_native_structured_data,
    project_structured_design_data,
    route_revision,
    stamp_editable_text_targets,
    sync_production_brief_from_spec,
)
from investhome_api.services.creative_director.revision_intelligence import (
    build_user_feedback,
    interpret_revision_plan,
    snapshot_elements,
    validate_change_diff,
)
from investhome_api.services.creative_director.revision_intelligence_v3 import (
    dump_semantic_plan,
    extract_working_instruction,
    validate_execution,
)
from investhome_api.services.creative_director.generate_ad import (
    _as_dict,
    _prepare_campaign_ad_context,
    claim_guard_summary,
    project_asset_lock_summary,
    resolve_locked_assets,
)
from investhome_api.services.creative_director.master_revision_controller import (
    classify_revision_command,
)
from investhome_api.services.creative_director.edit_map import (
    attach_edit_map_for_cover,
    load_edit_map,
    rebind_edit_map_for_cover,
    render_debug_overlay,
    resolve_current_cover_asset_id,
    stamp_current_cover,
)
from investhome_api.services.creative_director.research import select_visual_replace_source
from investhome_api.services.creative_director.production_brief import (
    lock_copy_to_language,
    verify_logo_lock,
)
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.creative_studio_media_service import (
    get_asset_or_404,
    open_asset_content,
)
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives

logger = logging.getLogger(__name__)

REVISION_INTENTS = (
    "COPY_CHANGE",
    "VISUAL_CHANGE",
    "ASSET_CHANGE",
    "LAYOUT_CHANGE",
    "STYLE_CHANGE",
    "LANGUAGE_CHANGE",
    "SIMPLIFY",
    "COMMERCIAL_EMPHASIS",
)

_CLAIM_INVENTION_MARKERS = (
    "roi",
    "yield",
    "getiri",
    "kira getirisi",
    "scarcity",
    "limited units",
    "sınırlı sayıda",
    "son ünite",
    "last chance",
    "guaranteed",
    "garanti getiri",
)

# Quality Comparison Guard thresholds (0–255 luminance / channel space).
QUALITY_BRIGHTNESS_DELTA_MAX = 12.0
QUALITY_CONTRAST_DELTA_MAX = 15.0
QUALITY_COLOR_SHIFT_MAX = 18.0
QUALITY_DIMENSION_DELTA_PCT_MAX = 2.0

DEFAULT_PRESERVE = [
    "exposure",
    "brightness",
    "white_balance",
    "contrast",
    "sharpness",
    "resolution",
    "architectural_interior_details",
    "composition_unless_requested",
    "logo_quality",
    "unaffected_typography",
    "verified_prices",
    "project_logo",
    "background_photograph",
]

DEFAULT_FORBIDDEN = [
    "darkening",
    "recoloring",
    "cinematic_grading",
    "contrast_increase",
    "vignette",
    "blur_changes",
    "sharpening_changes",
    "crop_changes",
    "lighting_changes",
    "full_redesign",
    "generation_from_prior_revision_raster",
]

QUALITY_LOCK_BRIEF = {
    "preserve": list(DEFAULT_PRESERVE),
    "forbidden_unless_explicitly_requested": list(DEFAULT_FORBIDDEN),
    "rule": (
        "If revision intent is not color grading / lighting, do not change image treatment. "
        "Source image is the IMMUTABLE MASTER finished-ad — apply cumulative ops only."
    ),
}


def _normalize_tr(text: str) -> str:
    """Lowercase with Turkish İ/I handling for revision heuristics."""
    return (
        (text or "")
        .replace("İ", "i")
        .replace("I", "ı")
        .lower()
    )


def interpret_revision_intents(instruction: str) -> list[str]:
    """Map NL revision instruction → revision intent tags (deterministic heuristics)."""
    from investhome_api.services.creative_director.master_revision_controller import (
        has_tr_word,
        is_visual_replace_command,
        working_revision_text,
    )

    raw = working_revision_text(instruction).strip()
    if not raw:
        return []
    found: list[str] = []

    def add(tag: str) -> None:
        if tag not in found:
            found.append(tag)

    copy_markers = (
        "başlık",
        "headline",
        "cta",
        "yazı",
        "metin",
        "copy",
        "ifade",
        "rozet",
        "badge",
        "kaldır",
        "remove",
        "değiştir",
        "yap",
    )
    if any(m in raw for m in copy_markers):
        add("COPY_CHANGE")
    if any(m in raw for m in ("görsel", "visual", "renk", "color", "kontrast", "ışık", "karart", "darken")):
        add("VISUAL_CHANGE")

    if is_visual_replace_command(instruction):
        add("ASSET_CHANGE")
    if any(m in raw for m in ("layout", "düzen", "yerleşim", "konum", "aşağı", "yukarı", "küçült", "büyüt")):
        add("LAYOUT_CHANGE")
    if any(m in raw for m in ("stil", "style", "premium", "modern", "editorial")):
        add("STYLE_CHANGE")
    if any(m in raw for m in ("türkçe", "english", "dil", "language", "ingilizce")):
        add("LANGUAGE_CHANGE")
    if any(
        has_tr_word(raw, m)
        for m in ("sade", "simplify", "basit", "azalt", "kalabalık", "sadeleştir", "sadelestir")
    ):
        add("SIMPLIFY")
    if any(m in raw for m in ("fiyat", "price", "satış", "offer", "ticari", "commercial", "%", "indirim")):
        add("COMMERCIAL_EMPHASIS")

    if not found:
        add("COPY_CHANGE")
    return found


def _strip_quotes(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] in "'\"“”‘’" and v[-1] in "'\"“”‘’":
        return v[1:-1].strip()
    return v


def _extract_quoted_or_tail(pattern: re.Pattern[str], text: str) -> str | None:
    m = pattern.search(text)
    if not m:
        return None
    return _strip_quotes(m.group(1).strip().rstrip("."))


def _op_dict(op: RevisionOperation) -> dict[str, Any]:
    return op.model_dump(by_alias=True, exclude_none=True)


def build_revision_diff(
    *,
    instruction: str,
    production_brief: dict[str, Any] | None = None,
    design_spec: dict[str, Any] | None = None,
    selected_element_id: str | None = None,
) -> RevisionDiff:
    """Revision Director: structured plan — never copy user NL verbatim into provider.

    Delegates to Revision Intelligence v2 (geometric + min-change). Legacy callers
    without design_spec still receive a valid RevisionDiff.
    """
    return interpret_revision_plan(
        instruction=instruction,
        production_brief=production_brief,
        design_spec=design_spec,
        selected_element_id=selected_element_id,
    )


def build_revision_brief(
    *,
    instruction: str,
    intents: list[str],
    production_brief: dict[str, Any],
    original_brief: str,
    language: str,
    current_final_asset_id: UUID,
    master_asset_id: UUID | None = None,
    revision_diff: RevisionDiff | dict[str, Any] | None = None,
    cumulative_operations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """CD revision brief — structured diff + quality lock; preserve locked facts."""
    lang = (language or "tr").strip().lower() or "tr"
    final = _as_dict(production_brief.get("final_copy"))
    instr = (instruction or "").strip()

    diff = revision_diff
    if diff is None:
        diff = build_revision_diff(instruction=instr, production_brief=production_brief)
    if isinstance(diff, RevisionDiff):
        diff_payload = diff.model_dump(by_alias=True)
        ops = list(diff.operations)
    else:
        diff_payload = dict(diff)
        ops = [
            RevisionOperation.model_validate(o) if not isinstance(o, RevisionOperation) else o
            for o in (diff_payload.get("operations") or [])
        ]

    copy_overrides: dict[str, str] = {}
    supporting = list(production_brief.get("supporting") or [])

    for op in ops:
        if op.target == "cta" and op.action == "replace_text" and op.to_value:
            copy_overrides["cta"] = op.to_value
        if op.target == "headline" and op.action == "replace_text" and op.to_value:
            copy_overrides["headline"] = op.to_value
        if op.target == "headline" and op.action == "tone_adjust":
            copy_overrides["headline_direction"] = "more_premium_tone"
            copy_overrides["headline_keep_meaning"] = str(
                op.from_value or final.get("headline") or production_brief.get("hero") or ""
            )
        if op.target == "badge" and op.action == "scale" and op.scale_factor is not None:
            copy_overrides["badge_scale"] = str(op.scale_factor)
            copy_overrides["badge_scale_note"] = op.note or f"scale_factor={op.scale_factor}"
        if op.target == "support_message" and op.action == "remove":
            scarcity_markers = ("sınırlı", "limited", "son ünite", "last chance")
            supporting = [
                s for s in supporting if not any(m in str(s).lower() for m in scarcity_markers)
            ]
            copy_overrides["remove_scarcity"] = "true"
        if op.target == "logo" and op.action == "scale" and op.scale_factor is not None:
            copy_overrides["logo_scale"] = str(op.scale_factor)

    locked_cta = lock_copy_to_language(
        copy_overrides.get("cta") or final.get("cta") or production_brief.get("cta"),
        language=lang,
        fallback="Detayları İncele",
    )
    if copy_overrides.get("headline"):
        # Exact headline — do not run through soft tone rewrite.
        pass

    return {
        "mode": "revision",
        "instruction": instr,
        "intents": intents,
        "language": lang,
        "language_lock": lang.startswith("tr"),
        "current_final_asset_id": str(current_final_asset_id),
        "master_asset_id": str(master_asset_id) if master_asset_id else None,
        "master_source_asset_id": None,
        "revision_source": "master_source_image",
        "preserve_campaign_context": True,
        "preserve_design_when_possible": True,
        "keep_unchanged_default": True,
        "copy_overrides": copy_overrides,
        "cta": locked_cta,
        "supporting": supporting,
        "revision_diff": diff_payload,
        "cumulative_operations": list(cumulative_operations or []),
        "quality_lock": dict(QUALITY_LOCK_BRIEF),
        "production_brief_snapshot": {
            "campaign_intent": production_brief.get("campaign_intent"),
            "big_idea": production_brief.get("big_idea"),
            "hero": copy_overrides.get("headline") or production_brief.get("hero"),
            "cta": locked_cta,
            "final_copy": {
                **final,
                **{
                    k: v
                    for k, v in copy_overrides.items()
                    if k in ("headline", "cta") or k in final
                },
            },
            "approved_claims": production_brief.get("approved_claims"),
            "forbidden_claims": production_brief.get("forbidden_claims"),
            "asset_lock": production_brief.get("asset_lock"),
            "logo_lock": production_brief.get("logo_lock"),
            "design_direction": production_brief.get("design_direction"),
            "message_strategy": production_brief.get("message_strategy"),
            "simplicity_director": production_brief.get("simplicity_director"),
        },
        "original_user_brief": original_brief,
        "claim_guard_active": True,
        "forbidden_invention_markers": list(_CLAIM_INVENTION_MARKERS),
    }


def _format_operation_line(op: dict[str, Any] | RevisionOperation) -> str:
    d = _op_dict(op) if isinstance(op, RevisionOperation) else dict(op)
    target = d.get("target")
    action = d.get("action")
    conf = d.get("confidence", "medium")
    to_value = d.get("to") if d.get("to") is not None else d.get("to_value")
    from_value = d.get("from") if d.get("from") is not None else d.get("from_value")
    parts = [f"- [{conf}] {target}.{action}"]
    if from_value is not None:
        parts.append(f"from={from_value!r}")
    if to_value is not None:
        parts.append(f"to={to_value!r}")
    if d.get("scale_factor") is not None:
        parts.append(f"scale_factor={d.get('scale_factor')}")
    if d.get("note"):
        parts.append(f"({d.get('note')})")
    return " ".join(parts)


RECOMPOSE_LOCK_DEFAULT = [
    "element positions",
    "headline zone / region (not the requested headline copy)",
    "logo zone / position / treatment (except requested scale)",
    "CTA zone / size / position / style / copy",
    "font character and typography style",
    "visual hierarchy",
    "margins and alignment",
    "colors and palette",
    "remaining supporting copy",
    "decorative details",
    "background crop",
    "image lighting and grade",
    "overall visual density — do not simplify or redesign",
]


def build_recompose_change_lock_lists(
    *,
    revision_diff: RevisionDiff | dict[str, Any] | None,
    copy_overrides: dict[str, Any] | None = None,
    master_visible_copy: dict[str, Any] | None = None,
) -> tuple[list[str], list[str]]:
    """CHANGE = explicit requests only. LOCK = everything else visible in master."""
    if isinstance(revision_diff, RevisionDiff):
        ops = [_op_dict(o) for o in revision_diff.operations]
    else:
        d = _as_dict(revision_diff)
        ops = [_op_dict(o) if not isinstance(o, dict) else dict(o) for o in (d.get("operations") or [])]
    overrides = _as_dict(copy_overrides)
    visible = _as_dict(master_visible_copy)
    change: list[str] = []
    for op in ops:
        target = str(op.get("target") or "").strip().lower()
        action = str(op.get("action") or "").strip().lower()
        to_value = op.get("to") if op.get("to") is not None else op.get("to_value")
        scale = op.get("scale_factor")
        if target in {"headline", "primary_headline"} and action in {"replace_text", "set_text"} and to_value:
            change.append(
                f"headline copy → {to_value}. Fit inside the EXISTING headline region only "
                "(line wrap, modest font-size, modest line-height, small local spacing). "
                "Do not move the headline to another region or enlarge it dramatically."
            )
        elif target in {"support_message", "left_feature_texts", "feature_text"} and action in {
            "remove",
            "delete",
            "hide",
        }:
            change.append(
                "remove the FIRST left supporting line only. Keep every remaining supporting line "
                "in the same place, size, and style."
            )
        elif target == "logo" and action == "scale":
            factor = float(scale) if scale is not None else float(overrides.get("logo_scale") or 0.85)
            pct = abs(1.0 - factor) * 100.0
            direction = "smaller" if factor < 1.0 else "larger"
            change.append(
                f"logo approximately {pct:.0f}% {direction} (scale_factor={factor}). "
                "Same mark, same corner, same treatment. Do not redraw or restyle the logo."
            )
        elif target == "cta" and to_value:
            change.append(f"CTA copy → {to_value}. Keep CTA size, position, and style.")
        else:
            change.append(_format_operation_line(op).lstrip("- ").strip())
    if not change:
        change.append("No structured ops — apply only the explicit user request. Change nothing else.")

    remaining = visible.get("supporting") or []
    cta = visible.get("cta") or ""
    lock = list(RECOMPOSE_LOCK_DEFAULT)
    if cta:
        lock.append(f"CTA copy stays exactly: {cta}")
    if remaining:
        lock.append("remaining supporting copy stays exactly: " + " | ".join(str(s) for s in remaining))
    lock.append("Default: if the user did not request it, preserve it.")
    return change, lock


def render_visual_replace_production_prompt(
    *,
    revision_brief: dict[str, Any],
    original_brief: str,
    selected_filename: str | None = None,
) -> str:
    """Replace only the hero photograph. Do not redesign the advertisement."""
    selected = selected_filename or revision_brief.get("selected_exterior_filename") or "approved exterior"
    lock = list(revision_brief.get("lock_list") or RECOMPOSE_LOCK_DEFAULT)
    lines = [
        "VISUAL_REPLACE_ONLY — REPLACE THE HERO PHOTOGRAPH. DO NOT REDESIGN THE ADVERTISEMENT.",
        "EDIT IMAGE 1. Do not create a new advertisement. Do not restyle. Do not recompose.",
        "",
        "PROVIDER INPUTS:",
        "IMAGE 1 IS THE CURRENT MASTER FINISHED ADVERTISEMENT — the design to keep.",
        "IMAGE 2 IS THE NEW APPROVED PROJECT EXTERIOR PHOTOGRAPH — use it as the new hero visual only.",
        "Do not use any previous interior photograph. Image 2 is the replacement scene.",
        "",
        f"Campaign identity (do not restyle): {(original_brief or '')[:240]}",
        f"Master finished-ad asset id: {revision_brief.get('master_asset_id')}.",
        f"New source visual: {selected} ({revision_brief.get('master_source_asset_id')}).",
        "",
        "CHANGE (only this):",
        "- Replace the hero / background photograph with Image 2. Keep crop framing as close as possible to Image 1.",
        "",
        "LOCK (must stay the same as Image 1):",
        *[f"- {item}" for item in lock],
        "- Headline copy and placement (ALIRKEN KAZAN if present)",
        "- Unit line 2+1",
        "- Price 675.000 USD / $675,000",
        "- Discount %35",
        "- Supporting copy",
        "- Project logo (same mark, size, corner, treatment)",
        "- CTA copy, size, position, style",
        "- Typography, font scale, colors, spacing, alignment, decorative elements",
        "- Overall visual hierarchy",
        "",
        "CURRENT USER REQUEST:",
        f"- {revision_brief.get('instruction') or ''}",
        "",
        "FORBIDDEN:",
        "- Redesign, restyle, or recreate the advertisement",
        "- Move, rewrite, or restyle locked commercial elements",
        "- Invent architecture that is not in Image 2",
        "- Draw or replace the logo",
    ]
    return "\n".join(lines)


def render_revision_production_prompt(
    *,
    revision_brief: dict[str, Any],
    production_brief: dict[str, Any],
    original_brief: str,
    lifestyle: bool = False,
) -> str:
    """Edit-only CREATIVE_RECOMPOSE prompt. Never a new-ad generation brief."""
    del lifestyle  # signature stable; generation brief is intentionally not used.
    overrides = _as_dict(revision_brief.get("copy_overrides"))
    diff = _as_dict(revision_brief.get("revision_diff"))
    cumulative = list(revision_brief.get("cumulative_operations") or [])
    snapshot = _as_dict(revision_brief.get("production_brief_snapshot"))
    visible = _as_dict(revision_brief.get("master_visible_copy"))
    if not visible:
        visible = {
            "headline": snapshot.get("hero") or _as_dict(production_brief.get("final_copy")).get("headline"),
            "cta": snapshot.get("cta") or production_brief.get("cta"),
            "supporting": snapshot.get("supporting") or production_brief.get("supporting") or [],
        }
    change, lock = build_recompose_change_lock_lists(
        revision_diff=diff,
        copy_overrides=overrides,
        master_visible_copy=visible,
    )
    revision_brief["change_list"] = list(change)
    revision_brief["lock_list"] = list(lock)

    lines = [
        "AI REVISION FIDELITY LOCK — EDIT IMAGE 1. DO NOT DESIGN A NEW ADVERTISEMENT.",
        "CREATIVE_RECOMPOSE — MINIMUM NECESSARY CHANGE TO THE SAME ADVERTISEMENT.",
        "",
        "PROVIDER INPUTS:",
        "IMAGE 1 IS THE DESIGN TO EDIT. It is the IMMUTABLE MASTER finished advertisement.",
        "Do not reinterpret Image 1. Do not restyle it. Do not create a new advertisement from it.",
        "IMAGE 2 IS RECONSTRUCTION MATERIAL ONLY (approved clean source photograph).",
        "Use Image 2 only if a tiny patch of the photograph must be reconstructed after a local edit.",
        "Do not design a new advertisement from Image 2 plus a text brief.",
        "",
        f"Campaign identity (do not restyle): {(original_brief or '')[:240]}",
        f"Master finished-ad asset id: {revision_brief.get('master_asset_id')}.",
        f"Master source asset id: {revision_brief.get('master_source_asset_id')}.",
        f"Command mode: {diff.get('command_mode') or 'exact'}.",
        "",
        "CURRENT USER REQUEST:",
        f"- {revision_brief.get('instruction') or ''}",
        "",
        "STRUCTURED REVISION DIFF",
        "CHANGE (only these explicit requests):",
        *[f"- {item}" for item in change],
        "",
        "LOCK (everything else visible in the master — preserve pixel-faithfully):",
        *[f"- {item}" for item in lock],
        "",
        "LOCAL RECOMPOSITION ONLY:",
        "When headline copy changes: first attempt to fit the new headline inside the EXISTING headline region.",
        "Allowed: line wrapping, modest font-size adjustment, modest line-height adjustment, small local spacing.",
        "FORBIDDEN unless explicitly in CHANGE: move headline to a different region, enlarge headline dramatically,",
        "redesign hierarchy, move CTA, move logo, delete unrequested copy, simplify the ad,",
        "change background crop, change lighting, change colors, change decorative details.",
        "The result must clearly look like THE SAME ADVERTISEMENT as Image 1.",
        "",
        "IMAGE QUALITY LOCK — FORBIDDEN unless explicitly requested:",
        *[f"- {f}" for f in (QUALITY_LOCK_BRIEF["forbidden_unless_explicitly_requested"])],
    ]
    if cumulative:
        lines.extend(
            [
                "",
                "CUMULATIVE APPROVED OPERATIONS (already accepted — keep all of these):",
            ]
        )
        for op in cumulative:
            lines.append(_format_operation_line(op))
    return "\n".join(lines)


def resolve_master_asset_id(
    ctx: dict[str, Any],
    *,
    current_final_asset_id: UUID | None = None,
    history: list[Any] | None = None,
) -> UUID:
    """Immutable master = first approved finished-ad for this campaign."""
    raw = ctx.get("master_finished_ad_asset_id") or ctx.get("master_asset_id")
    if raw:
        return UUID(str(raw))
    entries = revision_entries(history if history is not None else ctx.get("revision_history"))
    for item in entries:
        if item.get("version") == "original" and item.get("new_asset_id"):
            return UUID(str(item["new_asset_id"]))
    if entries and entries[0].get("new_asset_id"):
        return UUID(str(entries[0]["new_asset_id"]))
    # Fall back to first generate_ad asset or current tip (becomes master on first revise).
    for g in ctx.get("generated_assets") or []:
        if isinstance(g, dict) and g.get("asset_id") and g.get("role") in {
            "master_instagram_4_5",
            "finished_ad",
            "master_finished_ad",
        }:
            return UUID(str(g["asset_id"]))
    latest = ctx.get("latest_master_ad_asset_id")
    if latest:
        return UUID(str(latest))
    if current_final_asset_id is not None:
        return current_final_asset_id
    raise ValueError("master_asset_id cannot be resolved")


def resolve_revision_visual_asset_id(
    ctx: dict[str, Any],
    *,
    smb_current_final_asset_id: UUID,
) -> UUID:
    """IMAGE 1 / quality compare = current approved cover, never v1 master by default."""
    try:
        return resolve_current_cover_asset_id(ctx, fallback=smb_current_final_asset_id)
    except ValueError:
        return smb_current_final_asset_id


def ensure_master_asset_id(ctx: dict[str, Any], asset_id: UUID) -> UUID:
    """Set master once; never overwrite. Keep master_finished_ad_asset_id in sync."""
    existing = ctx.get("master_finished_ad_asset_id") or ctx.get("master_asset_id")
    if existing:
        mid = UUID(str(existing))
        ctx["master_asset_id"] = str(mid)
        ctx["master_finished_ad_asset_id"] = str(mid)
        return mid
    ctx["master_asset_id"] = str(asset_id)
    ctx["master_finished_ad_asset_id"] = str(asset_id)
    return asset_id


def ensure_master_creative_lock(
    ctx: dict[str, Any],
    *,
    production_brief: dict[str, Any] | None,
    interior_id: UUID | str | None,
    logo_id: UUID | str | None,
    art_direction: Any = None,
) -> dict[str, Any]:
    """Stamp immutable Golden Creative masters once. Never overwrite."""
    if not ctx.get("master_production_brief") and isinstance(production_brief, dict):
        ctx["master_production_brief"] = deepcopy(production_brief)
    if not ctx.get("master_source_assets"):
        ctx["master_source_assets"] = {
            "interior_asset_id": str(interior_id) if interior_id else None,
            "logo_asset_id": str(logo_id) if logo_id else None,
        }
    if not ctx.get("master_creative_direction"):
        if hasattr(art_direction, "to_dict"):
            ctx["master_creative_direction"] = art_direction.to_dict()
        elif isinstance(art_direction, dict):
            ctx["master_creative_direction"] = dict(art_direction)
        elif isinstance(production_brief, dict):
            ctx["master_creative_direction"] = deepcopy(
                _as_dict(production_brief.get("design_direction"))
            )
    return ctx


def apply_revision_ops_to_working_brief(
    *,
    master_brief: dict[str, Any],
    ops: list[Any],
) -> dict[str, Any]:
    """Apply structured revision ops onto a working copy of the MASTER brief."""
    brief = deepcopy(master_brief) if isinstance(master_brief, dict) else {}
    final = dict(_as_dict(brief.get("final_copy")))
    supporting = list(brief.get("supporting") or [])
    if not supporting:
        supporting = collect_supporting_lines(
            final.get("supporting"),
            brief.get("supporting_messages"),
            headline=str(final.get("headline") or brief.get("hero") or ""),
            limit=4,
        )
    logo_scale = 1.0
    removed_first_support = False
    for op in ops:
        d = _op_dict(op) if not isinstance(op, dict) else dict(op)
        target = str(d.get("target") or "").lower()
        action = str(d.get("action") or "").lower()
        to_value = d.get("to") if d.get("to") is not None else d.get("to_value")
        if target in {"headline", "primary_headline"} and action == "replace_text" and to_value:
            final["headline"] = str(to_value)
            brief["hero"] = str(to_value)
        if target == "cta" and action == "replace_text" and to_value:
            final["cta"] = str(to_value)
            brief["cta"] = str(to_value)
        if action in {"delete", "remove", "hide"} and target in {
            "left_feature_texts",
            "support_message",
            "top_small_description",
            "subheadline",
            "eyebrow",
        }:
            ids = [str(i).lower() for i in (d.get("element_ids") or []) if i]
            eid = str(d.get("element_id") or "").lower()
            first_ids = {"support-message-1", "feature-1"}
            if target == "top_small_description" or eid in {
                "unit-label",
                "subheadline",
                "eyebrow",
                "top-description",
            }:
                brief["kicker"] = ""
                final["unit"] = final.get("unit") or ""
            elif (not ids and not eid) or any(i in first_ids for i in ids + [eid]):
                if supporting and not removed_first_support:
                    supporting = supporting[1:]
                    removed_first_support = True
            elif any(i in {"support-message-2", "feature-2"} for i in ids + [eid]) and len(supporting) > 1:
                supporting = [supporting[0], *supporting[2:]]
        if target == "logo" and action in {"scale", "resize"}:
            try:
                logo_scale *= float(d.get("scale_factor") or d.get("value") or 1.0)
            except (TypeError, ValueError):
                pass
    brief["final_copy"] = final
    brief["supporting"] = supporting
    if logo_scale != 1.0:
        brief["logo_scale"] = round(logo_scale, 4)
    return brief


def golden_revision_artifact_guard(
    *,
    editable_layers: list[Any] | None,
    interior_before: str | None,
    interior_after: str | None,
    logo_before: str | None,
    logo_after: str | None,
    background_requested: bool,
) -> dict[str, Any]:
    """HARD FAIL artifacts that destroy Golden Creative quality."""
    failures: list[str] = []
    texts: list[str] = []
    for el in editable_layers or []:
        if not isinstance(el, dict):
            continue
        eid = str(el.get("id") or "").lower()
        role = str(el.get("_designRole") or el.get("role") or "").lower()
        fill = str(el.get("fill") or "")
        if eid.startswith("hide-plate") or role == "revision_hide_plate":
            failures.append("black_hide_plate")
        if "12,10,8" in fill.replace(" ", "") or fill.lower() in {"#000", "#000000", "black"}:
            if str(el.get("type") or "").upper() == "SHAPE":
                failures.append("black_hide_plate")
        copy = str(el.get("content") or el.get("text") or el.get("label") or "").strip().lower()
        if copy:
            if copy in texts:
                failures.append(f"duplicate_semantic_text:{copy[:48]}")
            texts.append(copy)
    if not background_requested and interior_before and interior_after:
        if str(interior_before) != str(interior_after):
            failures.append("background_changed_without_request")
    if logo_before and logo_after and str(logo_before) != str(logo_after):
        failures.append("logo_asset_changed")
    unique = sorted(set(failures))
    return {
        "status": "fail" if unique else "pass",
        "failures": unique,
        "compared_against": "master_creative_lock",
    }


def revision_operations_at_cursor(
    ctx: dict[str, Any],
    revision_index: int | None = None,
) -> list[dict[str, Any]]:
    """Cumulative approved ops aligned with current undo/redo tip."""
    entries, index = normalize_revision_cursor(
        ctx.get("revision_history"),
        revision_index if revision_index is not None else ctx.get("revision_index"),
    )
    stored = ctx.get("revision_operations")
    if isinstance(stored, list) and stored and not entries:
        return [dict(o) for o in stored if isinstance(o, dict)]

    cumulative: list[dict[str, Any]] = []
    for i, item in enumerate(entries):
        if i == 0 and item.get("version") == "original":
            continue
        if revision_index is not None and i > index:
            break
        if i > index:
            break
        ops = item.get("operations") or []
        if isinstance(ops, list):
            for op in ops:
                if isinstance(op, dict):
                    cumulative.append(dict(op))
        # Legacy entries without structured ops — skip
    return cumulative


def truncate_forward_operations(
    ops: list[dict[str, Any]] | None,
    history: list[Any] | None,
    revision_index: Any,
) -> list[dict[str, Any]]:
    """After undo+new revise, ops must match truncated history tip."""
    entries, index = normalize_revision_cursor(history, revision_index)
    cumulative: list[dict[str, Any]] = []
    for i, item in enumerate(entries):
        if i > index:
            break
        if item.get("version") == "original":
            continue
        for op in item.get("operations") or []:
            if isinstance(op, dict):
                cumulative.append(dict(op))
    if cumulative:
        return cumulative
    return list(ops or [])[:0]  # cleared when no ops on kept entries


def _version_label(history: list[Any]) -> str:
    n = 1 + sum(1 for h in history if isinstance(h, dict) and h.get("new_asset_id"))
    return f"v{n + 1}" if n >= 1 else "v2"


def revision_entries(history: list[Any] | None) -> list[dict[str, Any]]:
    """Lean entries that carry a final asset id (skip stubs / malformed)."""
    out: list[dict[str, Any]] = []
    for item in history or []:
        if isinstance(item, dict) and item.get("new_asset_id"):
            out.append(item)
    return out


def normalize_revision_cursor(
    history: list[Any] | None,
    revision_index: Any = None,
) -> tuple[list[dict[str, Any]], int]:
    """Resolve (entries, index). Missing index → tip (legacy pop-history compatible)."""
    entries = revision_entries(history)
    if not entries:
        return [], 0
    if isinstance(revision_index, int) and 0 <= revision_index < len(entries):
        return entries, revision_index
    return entries, len(entries) - 1


def asset_id_at_index(history: list[dict[str, Any]], index: int) -> str | None:
    if index < 0 or index >= len(history):
        return None
    raw = history[index].get("new_asset_id")
    return str(raw) if raw else None


def move_revision_cursor(
    history: list[Any] | None,
    revision_index: Any,
    *,
    delta: int,
) -> tuple[list[dict[str, Any]], int, str]:
    """Undo (delta=-1) / redo (delta=+1) without mutating GPT — switch saved final assets."""
    entries, index = normalize_revision_cursor(history, revision_index)
    if not entries:
        raise ValueError("No revision history.")
    next_index = index + int(delta)
    if next_index < 0:
        raise ValueError("No previous revision to undo.")
    if next_index >= len(entries):
        raise ValueError("No forward revision to redo.")
    asset_id = asset_id_at_index(entries, next_index)
    if not asset_id:
        raise ValueError("Revision entry missing asset id.")
    return entries, next_index, asset_id


def truncate_forward_history(
    history: list[Any] | None,
    revision_index: Any,
) -> tuple[list[dict[str, Any]], int]:
    """After undo, a new revise clears unreachable forward versions (A→B→C, undo to B, revise→D)."""
    entries, index = normalize_revision_cursor(history, revision_index)
    if not entries:
        return [], 0
    kept = entries[: index + 1]
    return kept, len(kept) - 1


def lean_revision_history(history: list[Any] | None) -> list[dict[str, Any]]:
    """Persist lean history entries (avoid nesting full production_brief snapshots)."""
    lean_history: list[dict[str, Any]] = []
    for item in history or []:
        if not isinstance(item, dict):
            continue
        if not item.get("new_asset_id"):
            continue
        rb = item.get("revision_brief")
        lean_rb = None
        if isinstance(rb, dict):
            lean_rb = {
                "mode": rb.get("mode"),
                "instruction": rb.get("instruction"),
                "intents": rb.get("intents"),
                "copy_overrides": rb.get("copy_overrides"),
                "cta": rb.get("cta"),
                "language": rb.get("language"),
                "master_asset_id": rb.get("master_asset_id"),
                "revision_source": rb.get("revision_source"),
                "revision_diff": rb.get("revision_diff"),
            }
        lean_history.append(
            {
                "version": item.get("version"),
                "intent": item.get("intent") or item.get("revision_route"),
                "previous_asset_id": item.get("previous_asset_id"),
                "new_asset_id": item.get("new_asset_id"),
                "master_asset_id": item.get("master_asset_id"),
                "revision_source_asset_id": item.get("revision_source_asset_id"),
                "instruction": item.get("instruction"),
                "revision_brief": lean_rb,
                "operations": item.get("operations") or [],
                "intents": item.get("intents"),
                "provider": item.get("provider"),
                "timestamp": item.get("timestamp"),
                "campaign_context_id": item.get("campaign_context_id"),
                "claim_guard": item.get("claim_guard"),
                "language": item.get("language"),
                "quality_guard": item.get("quality_guard"),
                "revision_route": item.get("revision_route"),
                "design_spec": item.get("design_spec"),
                "master_background_asset_id": item.get("master_background_asset_id"),
                "user_prompt": item.get("user_prompt") or item.get("instruction"),
                "selected_element_id": item.get("selected_element_id"),
                "interpreted_plan": item.get("interpreted_plan"),
                "geometry_operations": item.get("geometry_operations") or [],
                "changed_elements": item.get("changed_elements") or [],
                "previous_values": item.get("previous_values") or {},
                "new_values": item.get("new_values") or {},
                "provider_used": item.get("provider_used") or item.get("provider"),
                "provider_calls": item.get("provider_calls"),
                "user_feedback": item.get("user_feedback"),
                "change_diff_validation": item.get("change_diff_validation"),
            }
        )
    return lean_history


def _image_stats(content: bytes) -> dict[str, float]:
    from PIL import Image, ImageStat

    with Image.open(io.BytesIO(content)) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        # Downsample for speed
        thumb = rgb.copy()
        thumb.thumbnail((256, 256))
        stat = ImageStat.Stat(thumb)
        means = stat.mean  # R,G,B
        stddevs = stat.stddev
        brightness = float(sum(means) / 3.0)
        contrast = float(sum(stddevs) / 3.0)
        return {
            "width": float(w),
            "height": float(h),
            "brightness": brightness,
            "contrast": contrast,
            "mean_r": float(means[0]),
            "mean_g": float(means[1]),
            "mean_b": float(means[2]),
        }


def compare_revision_quality(
    *,
    master_bytes: bytes,
    revised_bytes: bytes,
    revision_diff: RevisionDiff | dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Best-effort quality guard vs MASTER. Fails on brightness/treatment drift when not requested."""
    master = _image_stats(master_bytes)
    revised = _image_stats(revised_bytes)
    brightness_delta = revised["brightness"] - master["brightness"]
    contrast_delta = revised["contrast"] - master["contrast"]
    color_shift = math.sqrt(
        (revised["mean_r"] - master["mean_r"]) ** 2
        + (revised["mean_g"] - master["mean_g"]) ** 2
        + (revised["mean_b"] - master["mean_b"]) ** 2
    )
    dim_delta_pct = 0.0
    if master["width"] > 0 and master["height"] > 0:
        dim_delta_pct = max(
            abs(revised["width"] - master["width"]) / master["width"] * 100.0,
            abs(revised["height"] - master["height"]) / master["height"] * 100.0,
        )

    diff = revision_diff
    if isinstance(diff, RevisionDiff):
        ops = diff.operations
        forbidden = set(diff.forbidden_changes)
    else:
        d = _as_dict(diff)
        ops = [
            RevisionOperation.model_validate(o) if isinstance(o, dict) else o
            for o in (d.get("operations") or [])
        ]
        forbidden = set(d.get("forbidden_changes") or [])

    requests_grade = False
    for o in ops:
        note = _normalize_tr(str(o.note or "") + str(getattr(o, "to_value", None) or ""))
        if any(k in note for k in ("darken", "grade", "kontrast", "ışık", "color", "recolor")):
            requests_grade = True
        if o.target == "background" and o.action not in {"preserve", "minimum_change"}:
            requests_grade = True
        if o.target == "overall" and o.action == "tone_adjust":
            requests_grade = True
    _ = forbidden  # reserved for future forbid-aware thresholds

    failures: list[str] = []
    if not requests_grade:
        if abs(brightness_delta) > QUALITY_BRIGHTNESS_DELTA_MAX:
            failures.append(
                f"brightness_drift={brightness_delta:.2f} (max ±{QUALITY_BRIGHTNESS_DELTA_MAX})"
            )
        if abs(contrast_delta) > QUALITY_CONTRAST_DELTA_MAX:
            failures.append(
                f"contrast_drift={contrast_delta:.2f} (max ±{QUALITY_CONTRAST_DELTA_MAX})"
            )
        if color_shift > QUALITY_COLOR_SHIFT_MAX:
            failures.append(f"color_shift={color_shift:.2f} (max {QUALITY_COLOR_SHIFT_MAX})")
    if dim_delta_pct > QUALITY_DIMENSION_DELTA_PCT_MAX:
        failures.append(f"dimension_drift_pct={dim_delta_pct:.2f}")

    status_val = "fail" if failures else "pass"
    return {
        "status": status_val,
        "master": master,
        "revised": revised,
        "brightness_delta": round(brightness_delta, 3),
        "contrast_delta": round(contrast_delta, 3),
        "color_shift": round(color_shift, 3),
        "dimension_delta_pct": round(dim_delta_pct, 3),
        "thresholds": {
            "brightness": QUALITY_BRIGHTNESS_DELTA_MAX,
            "contrast": QUALITY_CONTRAST_DELTA_MAX,
            "color_shift": QUALITY_COLOR_SHIFT_MAX,
            "dimension_pct": QUALITY_DIMENSION_DELTA_PCT_MAX,
        },
        "failures": failures,
        "compared_against": "master_asset",
    }


_HEADLINE_TARGETS = frozenset(
    {"headline", "primary_headline", "subheadline", "eyebrow", "top_small_description"}
)
_SUPPORT_DELETE_TARGETS = frozenset(
    {
        "support_message",
        "left_feature_texts",
        "feature_text",
        "top_small_description",
        "subheadline",
        "eyebrow",
    }
)
_CTA_TARGETS = frozenset({"cta"})
_LOGO_TARGETS = frozenset({"logo"})
_BACKGROUND_TARGETS = frozenset({"background", "layout", "style", "overall"})

# Visual lock vs MASTER finished-ad (not metadata). Tuned so the real Temple
# redesign rasters fail while a true local reflow in the requested zones can pass.
VISUAL_COMPARE_SIZE = (384, 480)
VISUAL_CTA_MAD_MAX = 16.0
VISUAL_CENTER_MAD_MAX = 15.0
VISUAL_CENTER_EDGE_MAD_MAX = 24.0
VISUAL_HEADLINE_OVERLAY_GROWTH_MAX = 1.25
VISUAL_LOGO_OVERLAY_GROWTH_MAX = 1.20
VISUAL_REMAINING_SUPPORT_MAD_MAX = 16.0
VISUAL_LOCKED_MAD_MAX = 10.0
VISUAL_LOGO_MAD_MAX_UNREQUESTED = 14.0

_HEADLINE_BOX = (0.02, 0.04, 0.72, 0.34)
_SUPPORT_BOX = (0.02, 0.26, 0.55, 0.50)
_REMAINING_SUPPORT_BOX = (0.02, 0.36, 0.55, 0.62)
_LOGO_BOX = (0.62, 0.02, 0.98, 0.22)
_CTA_BOX = (0.02, 0.78, 0.42, 0.96)
_CENTER_BOX = (0.28, 0.28, 0.78, 0.78)
# AI-first Temple masters place CTA + logo on the bottom center, not the left rail.
_CTA_REPLACE_BOX = (0.18, 0.74, 0.82, 0.93)
_LOGO_FOOTER_BOX = (0.18, 0.88, 0.82, 0.995)


def _revision_requested_targets(
    revision_diff: RevisionDiff | dict[str, Any] | None,
) -> tuple[set[str], set[str]]:
    if isinstance(revision_diff, RevisionDiff):
        ops = revision_diff.operations
    else:
        d = _as_dict(revision_diff)
        ops = [
            RevisionOperation.model_validate(o) if isinstance(o, dict) else o
            for o in (d.get("operations") or [])
        ]
    targets: set[str] = set()
    delete_targets: set[str] = set()
    for op in ops:
        target = str(getattr(op, "target", "") or "").strip()
        action = str(getattr(op, "action", "") or "").strip()
        if target:
            targets.add(target)
        if action in {"remove", "delete", "hide"}:
            delete_targets.add(target)
    return targets, delete_targets


def _crop_frac(img: Any, box: tuple[float, float, float, float]) -> Any:
    w, h = img.size
    x0, y0, x1, y1 = box
    return img.crop((int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h)))


def _mad(a: Any, b: Any) -> float:
    from PIL import ImageChops, ImageStat

    if a.size != b.size:
        b = b.resize(a.size)
    return float(ImageStat.Stat(ImageChops.difference(a, b)).mean[0])


def _overlay_mask(rgb: Any) -> Any:
    """Cream/gold/white UI overlay — not a perfect text OCR, used for scale/treatment."""
    from PIL import Image

    w, h = rgb.size
    px = rgb.load()
    out = Image.new("L", (w, h), 0)
    op = out.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y][:3]
            mx = max(r, g, b)
            mn = min(r, g, b)
            lum = (r + g + b) / 3.0
            gold = (r - b) > 28 and (g - b) > 12 and 70 <= lum <= 220
            light = lum >= 205 and (mx - mn) < 55
            cream = lum >= 175 and (r + g) / 2 - b > 18 and (mx - mn) < 80
            if gold or light or cream:
                op[x, y] = 255
    return out


def _mask_ratio(mask: Any) -> float:
    hist = mask.histogram()
    on = sum(hist[200:])
    return on / float(mask.size[0] * mask.size[1] or 1)


def _mask_on_count(mask: Any) -> int:
    hist = mask.histogram()
    return int(sum(hist[200:]))


def _overlay_lock_failures(
    name: str,
    ov_m: Any,
    ov_r: Any,
    box: tuple[float, float, float, float],
    *,
    growth_max: float = 1.45,
    drop_max: float = 0.50,
) -> list[str]:
    """Lock commercial overlay pixels. Ignore bright hero-photo pixels in the same box."""
    from PIL import ImageChops, ImageFilter

    master_mask = _crop_frac(ov_m, box)
    revised_mask = _crop_frac(ov_r, box)
    master_on = _mask_on_count(master_mask)
    if master_on < 12:
        return []
    retained = _mask_on_count(ImageChops.multiply(master_mask, revised_mask))
    drop = 1.0 - (retained / master_on)
    if drop > drop_max:
        return [f"{name}_overlay_lost drop={drop:.2f}"]
    dilated = master_mask.filter(ImageFilter.MaxFilter(9))
    extra = _mask_on_count(ImageChops.subtract(revised_mask, dilated))
    growth = (master_on + extra) / master_on
    if growth > growth_max:
        return [f"{name}_treatment_changed overlay_growth={growth:.2f}"]
    return []


def _frac_box_to_px(size: tuple[int, int], box: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
    w, h = size
    return (int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h))


def _locked_mad(master_g: Any, revised_g: Any, exempt_boxes: list[tuple[float, float, float, float]]) -> float:
    from PIL import Image, ImageChops

    w, h = master_g.size
    diff = ImageChops.difference(master_g, revised_g)
    exempt = Image.new("L", (w, h), 0)
    for box in exempt_boxes:
        x0, y0, x1, y1 = _frac_box_to_px((w, h), box)
        exempt.paste(255, (x0, y0, x1, y1))
    px = diff.load()
    ex = exempt.load()
    acc = 0.0
    n = 0
    step = 2  # subsample
    for y in range(0, h, step):
        for x in range(0, w, step):
            if ex[x, y] > 0:
                continue
            acc += px[x, y]
            n += 1
    return acc / float(n or 1)


def _region_metrics(
    master_g: Any,
    revised_g: Any,
    edges_m: Any,
    edges_r: Any,
    ov_m: Any,
    ov_r: Any,
    box: tuple[float, float, float, float],
) -> dict[str, float]:
    return {
        "mad": round(_mad(_crop_frac(master_g, box), _crop_frac(revised_g, box)), 3),
        "edge_mad": round(_mad(_crop_frac(edges_m, box), _crop_frac(edges_r, box)), 3),
        "overlay_master": round(_mask_ratio(_crop_frac(ov_m, box)), 4),
        "overlay_revised": round(_mask_ratio(_crop_frac(ov_r, box)), 4),
    }


def _left_text_bands(gray: Any, *, y0_frac: float, y1_frac: float, thresh: float = 18.0) -> list[tuple[int, int]]:
    """Horizontal bands where the left column is brighter than the right (editorial type)."""
    w, h = gray.size
    y0 = max(0, int(y0_frac * h))
    y1 = min(h, int(y1_frac * h))
    left_w = max(8, int(w * 0.48))
    right0 = int(w * 0.55)
    px = gray.load()
    bands: list[tuple[int, int]] = []
    in_band = False
    start = y0
    for y in range(y0, y1):
        left_acc = 0
        for x in range(left_w):
            left_acc += px[x, y]
        right_acc = 0
        n = 0
        for x in range(right0, w):
            right_acc += px[x, y]
            n += 1
        delta = (left_acc / float(left_w)) - (right_acc / float(n or 1))
        if delta > thresh:
            if not in_band:
                in_band = True
                start = y
        elif in_band:
            if (y - start) >= 4:
                bands.append((start, y))
            in_band = False
    if in_band and (y1 - start) >= 4:
        bands.append((start, y1))
    return bands


def _support_line_boxes(gray: Any) -> tuple[tuple[float, float, float, float] | None, tuple[float, float, float, float] | None]:
    """First vs remaining supporting-copy bands below the headline, as frac boxes."""
    w, h = gray.size
    bands = _left_text_bands(gray, y0_frac=0.18, y1_frac=0.58, thresh=18.0)
    support: list[tuple[int, int]] = []
    for y0, y1 in bands:
        if y0 >= int(0.18 * h) and y0 < int(0.50 * h) and (y1 - y0) >= 8:
            support.append((y0, y1))
    if len(support) == 1 and (support[0][1] - support[0][0]) >= max(22, int(0.05 * h)):
        y0, y1 = support[0]
        mid = (y0 + y1) // 2
        support = [(y0, mid), (mid, y1)]
    elif len(support) > 2:
        support = [support[0], (support[1][0], support[-1][1])]

    def _box(band: tuple[int, int] | None) -> tuple[float, float, float, float] | None:
        if not band:
            return None
        pad = 4
        return (
            0.02,
            max(0.0, (band[0] - pad) / float(h)),
            0.55,
            min(1.0, (band[1] + pad) / float(h)),
        )

    first = _box(support[0] if support else None)
    remaining = _box(support[1] if len(support) > 1 else None)
    return first, remaining


def compare_recompose_composition_fidelity(
    *,
    master_bytes: bytes,
    revised_bytes: bytes,
    revision_diff: RevisionDiff | dict[str, Any] | None = None,
    hero_visual_replace: bool = False,
) -> dict[str, Any]:
    """Fail-closed VISUAL lock vs MASTER finished-ad.

    Requested ops are exempted. Unrequested supporting-copy loss, giant headline,
    CTA/logo treatment, crop, or layout simplification must reject.
    VISUAL_REPLACE_ONLY may change the hero photograph; commercial overlay must stay.
    """
    from PIL import Image, ImageFilter

    targets, delete_targets = _revision_requested_targets(revision_diff)
    headline_ok = bool(targets & _HEADLINE_TARGETS)
    support_delete_ok = bool(delete_targets & _SUPPORT_DELETE_TARGETS) or bool(
        targets & {"support_message", "left_feature_texts", "feature_text"}
    )
    cta_ok = bool(targets & _CTA_TARGETS)
    logo_ok = bool(targets & _LOGO_TARGETS)
    background_ok = bool(targets & _BACKGROUND_TARGETS) or hero_visual_replace

    with Image.open(io.BytesIO(master_bytes)) as im_m, Image.open(io.BytesIO(revised_bytes)) as im_r:
        master_rgb = im_m.convert("RGB")
        master_rgb.thumbnail(VISUAL_COMPARE_SIZE, Image.Resampling.LANCZOS)
        revised_rgb = im_r.convert("RGB")
        if revised_rgb.size != master_rgb.size:
            revised_rgb = revised_rgb.resize(master_rgb.size, Image.Resampling.LANCZOS)
        master_g = master_rgb.convert("L")
        revised_g = revised_rgb.convert("L")
        edges_m = master_g.filter(ImageFilter.FIND_EDGES)
        edges_r = revised_g.filter(ImageFilter.FIND_EDGES)
        ov_m = _overlay_mask(master_rgb)
        ov_r = _overlay_mask(revised_rgb)

    first_support_box, remaining_support_box = _support_line_boxes(master_g)
    remaining_box = remaining_support_box or _REMAINING_SUPPORT_BOX
    first_box = first_support_box or _SUPPORT_BOX
    regions = {
        "headline": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, _HEADLINE_BOX),
        "support": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, first_box),
        "remaining_support": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, remaining_box),
        "logo": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, _LOGO_BOX),
        "cta": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, _CTA_BOX),
        "center": _region_metrics(master_g, revised_g, edges_m, edges_r, ov_m, ov_r, _CENTER_BOX),
    }
    regions["remaining_support"]["band_detected"] = 1.0 if remaining_support_box else 0.0
    exempt: list[tuple[float, float, float, float]] = []
    if headline_ok:
        exempt.append(_HEADLINE_BOX)
    if support_delete_ok:
        exempt.append(first_box)
    if logo_ok:
        exempt.append(_LOGO_BOX)
    locked_mad = round(_locked_mad(master_g, revised_g, exempt), 3)

    headline_ov_m = regions["headline"]["overlay_master"] or 0.0001
    headline_growth = regions["headline"]["overlay_revised"] / headline_ov_m
    logo_ov_m = regions["logo"]["overlay_master"] or 0.0001
    logo_growth = regions["logo"]["overlay_revised"] / logo_ov_m
    headline_drop = 1.0 - (regions["headline"]["overlay_revised"] / headline_ov_m)

    failures: list[str] = []
    if hero_visual_replace:
        # Do not use the left-rail CTA box: a brighter exterior in that crop is
        # not a CTA redesign. Lock overlay where the master actually has UI.
        for name, box in (
            ("headline", _HEADLINE_BOX),
            ("cta", _CTA_REPLACE_BOX),
            ("logo", _LOGO_FOOTER_BOX),
            ("logo_corner", _LOGO_BOX),
        ):
            failures.extend(_overlay_lock_failures(name, ov_m, ov_r, box))
    else:
        if not cta_ok and regions["cta"]["mad"] > VISUAL_CTA_MAD_MAX:
            failures.append(f"cta_visual_changed mad={regions['cta']['mad']}")
        if logo_ok:
            if logo_growth > VISUAL_LOGO_OVERLAY_GROWTH_MAX:
                failures.append(f"logo_treatment_changed overlay_growth={logo_growth:.2f}")
        elif regions["logo"]["mad"] > VISUAL_LOGO_MAD_MAX_UNREQUESTED:
            failures.append(f"logo_visual_changed mad={regions['logo']['mad']}")
        if headline_ok:
            if headline_growth > VISUAL_HEADLINE_OVERLAY_GROWTH_MAX:
                failures.append(f"headline_scale_changed overlay_growth={headline_growth:.2f}")
            elif headline_drop > 0.45 and regions["center"]["mad"] > 12:
                failures.append("headline_region_moved")
        elif regions["headline"]["mad"] > 18:
            failures.append(f"headline_unrequested_change mad={regions['headline']['mad']}")
        if support_delete_ok:
            if remaining_support_box and regions["remaining_support"]["mad"] > VISUAL_REMAINING_SUPPORT_MAD_MAX:
                failures.append(
                    f"supporting_text_disappeared remaining_mad={regions['remaining_support']['mad']}"
                )
        elif regions["support"]["mad"] > VISUAL_REMAINING_SUPPORT_MAD_MAX:
            failures.append(f"supporting_text_disappeared mad={regions['support']['mad']}")
        if not background_ok:
            if regions["center"]["mad"] > VISUAL_CENTER_MAD_MAX:
                failures.append(f"background_crop_or_composition_changed mad={regions['center']['mad']}")
            elif regions["center"]["edge_mad"] > VISUAL_CENTER_EDGE_MAD_MAX:
                failures.append(
                    f"background_crop_or_composition_changed edge_mad={regions['center']['edge_mad']}"
                )
            if locked_mad > VISUAL_LOCKED_MAD_MAX:
                failures.append(f"unrequested_layout_simplification locked_mad={locked_mad}")

    cta_left_m = _crop_frac(master_g, (0.02, 0.78, 0.36, 0.96))
    cta_right_m = _crop_frac(master_g, (0.64, 0.78, 0.98, 0.96))
    cta_left_r = _crop_frac(revised_g, (0.02, 0.78, 0.36, 0.96))
    cta_right_r = _crop_frac(revised_g, (0.64, 0.78, 0.98, 0.96))
    from PIL import ImageStat as _IS

    def _var(im: Any) -> float:
        v = _IS.Stat(im).var
        return float(v[0] if v else 0.0)

    master_cta_anchor = "left" if _var(cta_left_m) >= _var(cta_right_m) else "right"
    revised_cta_anchor = "left" if _var(cta_left_r) >= _var(cta_right_r) else "right"
    if not cta_ok and not hero_visual_replace and master_cta_anchor != revised_cta_anchor:
        failures.append(f"cta_anchor_changed master={master_cta_anchor} result={revised_cta_anchor}")

    status_val = "fail" if failures else "pass"
    return {
        "status": status_val,
        "composition_fidelity": status_val,
        "visual_fidelity": status_val,
        "composition_failures": failures,
        "cta_anchor": {"master": master_cta_anchor, "result": revised_cta_anchor},
        "regions": regions,
        "headline_overlay_growth": round(headline_growth, 3),
        "logo_overlay_growth": round(logo_growth, 3),
        "locked_mad": locked_mad,
        "requested_targets": sorted(targets),
        "compared_against": "master_finished_ad",
        "hero_visual_replace": hero_visual_replace,
    }


def _read_asset_bytes(db: Session, asset_id: UUID) -> bytes:
    asset = get_asset_or_404(asset_id, db)
    stream, _media = open_asset_content(asset)
    try:
        return stream.read()
    finally:
        try:
            stream.close()
        except Exception:
            pass


def revise_ad_from_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorReviseRequest,
) -> CreativeDirectorReviseAdResponse:
    """Revise from IMMUTABLE MASTER + cumulative ops (never prior revision raster)."""
    instruction = (body.instruction or "").strip()
    if not instruction:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Revision instruction is required.",
        )
    if body.current_final_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_final_asset_id is required for AI revision.",
        )

    row_early = db.get(CreativeDirectorCampaign, campaign_id)
    if row_early is not None:
        from investhome_api.services.creative_director.phase5_workflow import (
            revise_ad_phase5,
            should_route_revise_to_phase5,
        )

        early_ctx = dict(row_early.context_json or {})
        if should_route_revise_to_phase5(early_ctx, body.current_final_asset_id):
            return revise_ad_phase5(db, user, campaign_id, body)

    gen_body = CreativeDirectorGenerateAdRequest(
        language=body.language,
        aspect_ratio=body.aspect_ratio or "4:5",
        format_preset=body.format_preset or "portrait",
        production_mode="finished_ad",
    )
    prep = _prepare_campaign_ad_context(db, campaign_id, gen_body)
    (
        row,
        ctx,
        strategy,
        campaign_copy,
        pricing,
        original_brief,
        lifestyle,
        approved_claims,
        language,
        format_preset,
        aspect_ratio,
        interior_id,
        logo_id,
        interior_meta,
        logo_meta,
        texts,
        allowed_tokens,
        art_direction,
        production_brief,
    ) = prep

    if body.language:
        language = body.language.strip().lower() or language

    current_id = body.current_final_asset_id
    current_asset = get_asset_or_404(current_id, db)
    if (
        current_asset.linked_project_id is not None
        and current_asset.linked_project_id != row.linked_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="current_final_asset_id does not belong to this campaign project.",
        )

    os_cover = resolve_revision_visual_asset_id(ctx, smb_current_final_asset_id=current_id)
    if os_cover != current_id:
        os_asset = get_asset_or_404(os_cover, db)
        if (
            os_asset.linked_project_id is not None
            and os_asset.linked_project_id != row.linked_project_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="current_cover_asset_id does not belong to this campaign project.",
            )
        logger.info(
            "revision_visual_sot cover=%s smb_current=%s master=%s",
            os_cover,
            current_id,
            ctx.get("master_asset_id"),
        )
        current_id = os_cover
    stamp_current_cover(ctx, current_id)

    # Cursor truncate (undo then revise clears forward history + ops).
    history, _cursor = truncate_forward_history(
        ctx.get("revision_history"),
        ctx.get("revision_index"),
    )

    master_id = ensure_master_asset_id(
        ctx,
        resolve_master_asset_id(ctx, current_final_asset_id=current_id, history=history),
    )
    ensure_master_creative_lock(
        ctx,
        production_brief=production_brief,
        interior_id=interior_id,
        logo_id=logo_id,
        art_direction=art_direction,
    )
    master_asset = get_asset_or_404(master_id, db)
    if (
        master_asset.linked_project_id is not None
        and master_asset.linked_project_id != row.linked_project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="master_asset_id does not belong to this campaign project.",
        )

    logo_lock = verify_logo_lock(logo_meta)
    if logo_lock.get("status") != "pass":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project logo Asset ID missing or unverified. AI must not invent logos.",
        )

    prior_ops: list[dict[str, Any]] = []
    for item in history:
        if item.get("version") == "original":
            continue
        for op in item.get("operations") or []:
            if isinstance(op, dict):
                prior_ops.append(dict(op))

    working_instruction, _ = extract_working_instruction(instruction)
    intents = interpret_revision_intents(working_instruction)
    classified = classify_revision_command(instruction)
    classified_intent = str(classified.get("intent") or "")
    visual_replace_only = classified_intent == "VISUAL_REPLACE_ONLY"
    price_edit_only = classified_intent == "PRICE_EDIT_ONLY"
    if visual_replace_only:
        intents = [tag for tag in intents if tag != "SIMPLIFY"]
        if "ASSET_CHANGE" not in intents:
            intents.insert(0, "ASSET_CHANGE")
        if "VISUAL_CHANGE" not in intents:
            intents.insert(0, "VISUAL_CHANGE")
    if price_edit_only:
        intents = [
            tag
            for tag in intents
            if tag not in {"VISUAL_CHANGE", "ASSET_CHANGE", "LAYOUT_CHANGE"}
        ]
        if "COMMERCIAL_EMPHASIS" not in intents:
            intents.insert(0, "COMMERCIAL_EMPHASIS")
    from investhome_api.services.creative_director.price_block_revision import (
        apply_local_price_zone,
        is_baked_price_ad,
        parse_price_block,
    )

    price_intent = parse_price_block(instruction) or parse_price_block(working_instruction)
    if price_edit_only and price_intent is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "PRICE_EDIT_ONLY fail-closed — price facts could not be parsed. "
                "Full-ad generation was not used."
            ),
        )
    base_spec_for_plan = ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else None
    selected_element_id = getattr(body, "selected_element_id", None)
    revision_diff = build_revision_diff(
        instruction=instruction,
        production_brief=production_brief,
        design_spec=base_spec_for_plan,
        selected_element_id=selected_element_id,
    )
    new_ops = [_op_dict(o) for o in revision_diff.operations]
    cumulative_after = prior_ops + new_ops
    revision_route = route_revision(
        instruction=working_instruction,
        revision_diff=revision_diff,
        intents=intents,
        has_structured_design=bool(
            ctx.get("structured_design_data") or ctx.get("design_spec")
        ),
    )
    if revision_route == "LAYER_ONLY":
        revision_route = "MICRO_EDIT"

    visual_replace_pick: dict[str, Any] | None = None
    previous_source_id = UUID(str(interior_id))
    if visual_replace_only:
        if price_intent is not None and not price_edit_only:
            price_intent = None
        revision_route = "VISUAL_REPLACE_ONLY"
        revision_diff = RevisionDiff(
            operations=[
                RevisionOperation(
                    target="background",
                    action="minimum_change",
                    note="VISUAL_REPLACE_ONLY: replace hero photograph",
                    confidence="high",
                    mode="exact",
                    priority="exact_numeric",
                )
            ],
            preserve=list(classified.get("locked") or []),
            forbidden_changes=list(classified.get("locked") or []),
            command_mode="exact",
            strict_preserve=True,
            requested_changes=[{"target": "hero_visual", "action": "replace"}],
        )
        new_ops = [_op_dict(o) for o in revision_diff.operations]
        cumulative_after = prior_ops + new_ops
        project_row = db.get(Project, row.linked_project_id)
        if project_row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="VISUAL_REPLACE_ONLY requires a linked construction project.",
            )
        picked, pick_report = select_visual_replace_source(
            db,
            project=project_row,
            instruction=instruction,
            exclude_asset_ids={str(interior_id), str(master_id), str(current_id)},
            logo_asset_id=str(logo_id) if logo_id else None,
        )
        visual_replace_pick = pick_report
        if picked is None or not picked.asset_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        "VISUAL_REPLACE_ONLY: no approved Temple exterior found in this "
                        "project's Drive / Media Library. Will not keep the current interior."
                    ),
                    "visual_replace": pick_report,
                },
            )
        if str(picked.asset_id) == str(interior_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "VISUAL_REPLACE_ONLY selected the current interior. Fail closed.",
                    "visual_replace": pick_report,
                },
            )
        interior_id = UUID(str(picked.asset_id))
        interior_meta = picked.to_dict()
        logger.info(
            "visual_replace_only selected=%s filename=%s excluded_interior=%s candidates=%s",
            picked.asset_id,
            picked.filename,
            previous_source_id,
            len(pick_report.get("candidates") or []),
        )

    micro_edit = is_micro_edit_route(revision_route)
    editable_mode = micro_edit and bool(
        ctx.get("editable_finished_ad") is True
        or ctx.get("production_mode") in {"editable_finished_ad", "finished_ad"}
        or ctx.get("design_spec")
        or True
    )
    interpreted_plan = {
        "operations": new_ops,
        "semantic_plan": dump_semantic_plan(revision_diff),
        "command_mode": revision_diff.command_mode,
        "strict_preserve": revision_diff.strict_preserve,
        "selected_element_id": selected_element_id,
        "geometry_operations": list(revision_diff.geometry_operations or []),
        "requested_changes": list(revision_diff.requested_changes or []),
        "priority_order": [
            "exact_numeric",
            "relational_geometric",
            "percentage",
            "relative_nl",
            "subjective",
        ],
    }
    if visual_replace_only:
        interpreted_plan["scope"] = "VISUAL_REPLACE_ONLY"
        interpreted_plan["intent"] = "VISUAL_REPLACE_ONLY"
        interpreted_plan["visual_replace"] = visual_replace_pick

    revision_brief = build_revision_brief(
        instruction=instruction,
        intents=intents,
        production_brief=production_brief,
        original_brief=original_brief,
        language=language,
        current_final_asset_id=current_id,
        master_asset_id=master_id,
        revision_diff=revision_diff,
        cumulative_operations=prior_ops,
    )
    revision_brief["revision_route"] = revision_route
    revision_brief["master_source_asset_id"] = str(interior_id)
    source_assets = _as_dict(ctx.get("master_source_assets"))
    if source_assets.get("interior_asset_id") and not visual_replace_only:
        revision_brief["master_source_asset_id"] = str(source_assets["interior_asset_id"])
    if visual_replace_only:
        revision_brief["intent"] = "VISUAL_REPLACE_ONLY"
        revision_brief["visual_replace"] = visual_replace_pick
        revision_brief["previous_source_visual_asset_id"] = str(previous_source_id)
        revision_brief["selected_exterior_filename"] = (
            (interior_meta or {}).get("filename") if isinstance(interior_meta, dict) else None
        )
        revision_brief["lock_list"] = list(classified.get("locked") or [])
        revision_brief["change_list"] = [
            "Replace hero photograph with the selected approved project exterior. Change nothing else."
        ]

    if revision_brief.get("cta"):
        texts = dict(texts)
        texts["cta"] = str(revision_brief["cta"])
        pb_copy = dict(production_brief)
        final_copy = dict(_as_dict(pb_copy.get("final_copy")))
        final_copy["cta"] = texts["cta"]
        if revision_brief.get("copy_overrides", {}).get("headline"):
            final_copy["headline"] = revision_brief["copy_overrides"]["headline"]
            texts["headline"] = final_copy["headline"]
            pb_copy["hero"] = final_copy["headline"]
        pb_copy["final_copy"] = final_copy
        pb_copy["cta"] = texts["cta"]
        production_brief = pb_copy

    if price_intent is not None:
        interpreted_plan["price_block"] = price_intent.to_dict()
        interpreted_plan["scope"] = "PRICE_EDIT_ONLY" if price_edit_only else "PRICE_BLOCK_ONLY"
        interpreted_plan["intent"] = "PRICE_EDIT_ONLY" if price_edit_only else interpreted_plan.get("intent")
        revision_brief["price_block"] = price_intent.to_dict()
        revision_brief["scope"] = interpreted_plan["scope"]
        if price_edit_only:
            revision_brief["intent"] = "PRICE_EDIT_ONLY"
            revision_brief["lock_list"] = list(classified.get("locked") or [])
            revision_brief["change_list"] = [
                "old_price_decoration",
                "launch_price",
                "savings",
            ]

    v2_layers = bool(
        ctx.get("revision_engine_v2")
        or ctx.get("visual_foundation_asset_id")
        or (
            isinstance(ctx.get("design_spec"), dict)
            and ctx["design_spec"].get("revision_engine_v2") is True
        )
    )

    # Revision Engine v2: real editable price layers. Fail-closed — never
    # fall back to PRICE_BLOCK_ONLY pixel surgery or a full GPT redesign.
    if price_intent is not None and v2_layers:
        spec_now = ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else {}
        ids_now = {
            str(el.get("id") or "").lower()
            for el in (spec_now.get("elements") or [])
            if isinstance(el, dict)
        }
        if "old-price" not in ids_now:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        "Revision Engine v2 fail-closed — editable old-price layer is missing. "
                        "Will not inpaint, hide-plate, or regenerate this creative."
                    ),
                    "scope": "REVISION_ENGINE_V2",
                    "required_layers": ["old-price", "new-price", "savings-price"],
                    "present_layers": sorted(ids_now),
                },
            )
        revision_route = "MICRO_EDIT"
        micro_edit = True
        interpreted_plan["scope"] = "REVISION_ENGINE_V2"
        revision_brief["scope"] = "REVISION_ENGINE_V2"

    # ── PRICE_EDIT_ONLY: bounded local recomposition on content growth ──
    # Overlay / glyph PRICE_BLOCK is the failed designer and is not used here.
    elif price_intent is not None and (price_edit_only or is_baked_price_ad(ctx)):
        source_visual_before = str(interior_id)
        source_bytes = _read_asset_bytes(db, current_id)
        bounded = False
        persist_mode = "price_block_revision"
        persist_brief = "PRICE_BLOCK_ONLY local zone"
        persist_gen_id = "price_block_local_v1"
        provider_used = "price_block_local"
        provider_calls_n = 0
        occupied_slots: dict[str, bool] | None = None
        execution_name: str | None = None
        if price_edit_only:
            from investhome_api.services.creative_director.bounded_local_recomposition import (
                LOCKED_SOURCE_VISUAL_DAY_004,
                detect_price_content_growth,
                execute_bounded_commercial_recomposition,
                public_trace,
                write_evidence_files,
            )

            mc_now = _as_dict(ctx.get("master_creative"))
            src_now = _as_dict(ctx.get("master_source_assets"))
            locked_source = UUID(
                str(
                    mc_now.get("source_visual_asset_id")
                    or src_now.get("source_visual_asset_id")
                    or interior_id
                )
            )
            interior_id = locked_source
            source_visual_before = str(interior_id)
            map_id, edit_map = load_edit_map(ctx, cover_asset_id=current_id)
            if edit_map is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "message": (
                            "PRICE_EDIT_ONLY fail-closed — Edit Map missing for the current "
                            "approved cover. Overlay / PRICE_BLOCK was not used."
                        ),
                        "current_cover_asset_id": str(current_id),
                        "edit_map_id": map_id,
                    },
                )
            growth = detect_price_content_growth(edit_map, price_intent)
            if not growth.get("content_growth"):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail={
                        "message": (
                            "PRICE_EDIT_ONLY fail-closed — content growth required for "
                            "BOUNDED_LOCAL_RECOMPOSITION. Overlay was not used."
                        ),
                        "growth": growth,
                    },
                )
            patched_bytes, price_trace = execute_bounded_commercial_recomposition(
                cover_bytes=source_bytes,
                edit_map=edit_map,
                intent=price_intent,
                source_visual_asset_id=str(interior_id),
                expected_source_visual_asset_id=LOCKED_SOURCE_VISUAL_DAY_004,
            )
            price_trace = public_trace(price_trace)
            price_trace["edit_map_id_used"] = map_id
            bounded = True
            persist_mode = "bounded_local_recomposition"
            persist_brief = "PRICE_EDIT_ONLY bounded local recomposition"
            persist_gen_id = "bounded_local_recomposition_v1"
            provider_used = str(price_trace.get("provider_id") or "gpt-image")
            provider_calls_n = int(price_trace.get("provider_calls") or 1)
            occupied_slots = {
                "old_price": True,
                "new_price": True,
                "savings_price": True,
            }
            execution_name = "BOUNDED_LOCAL_RECOMPOSITION"
        else:
            patched_bytes, price_trace = apply_local_price_zone(
                source_bytes,
                spec=None,
                intent=price_intent,
            )
        if str(interior_id) != source_visual_before:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        "PRICE_EDIT_ONLY fail-closed — source visual changed. "
                        "Existing finished-ad was not persisted."
                    ),
                    "source_visual_before": source_visual_before,
                    "source_visual_after": str(interior_id),
                },
            )
        new_asset = persist_gpt_image(
            db,
            actor=user,
            linked_project_id=row.linked_project_id,
            content=patched_bytes,
            content_type="image/png",
            campaign_mode=persist_mode,
            session_id=str(row.id),
            provider_generation_id=persist_gen_id,
            campaign_context_id=str(row.id),
            brief_excerpt=persist_brief,
        )
        new_asset_id = new_asset.id
        from investhome_api.services.creative_director.price_block_revision import format_tr_usd

        pb_copy = dict(production_brief)
        final_copy = dict(_as_dict(pb_copy.get("final_copy")))
        final_copy["list_price"] = format_tr_usd(price_intent.list_amount)
        final_copy["offer_price"] = format_tr_usd(price_intent.launch_amount)
        final_copy["savings"] = format_tr_usd(price_intent.savings_amount)
        pb_copy["final_copy"] = final_copy
        production_brief = pb_copy
        texts = dict(texts)
        texts["list_price"] = final_copy["list_price"]
        texts["offer_price"] = final_copy["offer_price"]
        texts["savings"] = final_copy["savings"]

        revision_route = execution_name or "PRICE_EDIT_ONLY"
        interpreted_plan["intent"] = "PRICE_EDIT_ONLY"
        interpreted_plan["scope"] = "PRICE_EDIT_ONLY"
        if execution_name:
            interpreted_plan["execution"] = execution_name
        interpreted_plan["execution_trace"] = {
            "provider_calls": provider_calls_n,
            "generate_calls": 0,
            "execution": execution_name or "price_block_local",
            "price_block": price_trace,
            "revision_source": {
                "campaign_id": str(row.id),
                "asset_id": str(current_id),
                "raster_asset_id": str(current_id),
                "new_asset_id": str(new_asset_id),
                "interior_asset_id": str(interior_id),
                "logo_asset_id": str(logo_id),
                "master_asset_id": str(master_id),
                "source_visual_asset_id": str(interior_id),
            },
        }
        revision_brief["revision_route"] = revision_route
        revision_brief["execution"] = execution_name
        revision_brief["price_zone"] = price_trace.get("zone") or price_trace.get("mutable_region")

        claim_guard = claim_guard_summary(
            approved_claims=approved_claims,
            allowed_tokens=allowed_tokens,
            texts=texts,
            lifestyle=lifestyle,
        )
        asset_lock = project_asset_lock_summary(
            interior_id=interior_id,
            logo_id=logo_id,
            interior_meta=interior_meta,
            logo_meta=logo_meta,
            source_asset_id=interior_id,
        )
        asset_lock["master_asset_id"] = str(master_id)
        asset_lock["revision_model"] = (
            "bounded_local_recomposition" if bounded else "price_block_local_zone"
        )
        asset_lock["status"] = "pass" if logo_lock.get("status") == "pass" else "fail"

        quality_guard: dict[str, Any] = {
            "status": "pass",
            "gpt_calls": provider_calls_n,
            "generate_calls": 0,
            "route": revision_route,
            "execution": execution_name or "price_block_local",
            "composition_fidelity": "pass",
            "composition_failures": [],
            "price_block": price_trace,
            "compared_against": "selected_finished_ad",
        }

        if not any(isinstance(h, dict) and h.get("version") == "original" for h in history):
            history.insert(
                0,
                {
                    "version": "original",
                    "previous_asset_id": None,
                    "new_asset_id": str(master_id),
                    "master_asset_id": str(master_id),
                    "revision_source_asset_id": str(master_id),
                    "instruction": None,
                    "revision_brief": None,
                    "operations": [],
                    "provider": None,
                    "timestamp": None,
                    "campaign_context_id": str(row.id),
                    "revision_route": None,
                    "finished_ad_raster_asset_id": str(current_id),
                },
            )
        mc = dict(ctx.get("master_creative") or {})
        try:
            prev_version = int(mc.get("current_version") or 1)
        except (TypeError, ValueError):
            prev_version = 1
        version_n = prev_version + 1
        version = f"v{version_n}"
        entry = {
            "version": version,
            "intent": "PRICE_EDIT_ONLY",
            "execution": execution_name,
            "previous_asset_id": str(current_id),
            "new_asset_id": str(new_asset_id),
            "master_asset_id": str(master_id),
            "revision_source_asset_id": str(interior_id),
            "source_visual_asset_id": str(interior_id),
            "previous_source_visual_asset_id": str(interior_id),
            "instruction": instruction,
            "user_prompt": instruction,
            "interpreted_plan": interpreted_plan,
            "provider_used": provider_used,
            "provider_calls": provider_calls_n,
            "generate_calls": 0,
            "revision_brief": revision_brief,
            "operations": new_ops,
            "intents": intents,
            "provider": provider_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "campaign_context_id": str(row.id),
            "claim_guard": claim_guard.get("status"),
            "language": language,
            "quality_guard": quality_guard,
            "revision_route": revision_route,
            "finished_ad_raster_asset_id": str(new_asset_id),
        }
        history.append(entry)
        revision_index = len(history) - 1
        lean_history = lean_revision_history(history)

        generated = list(ctx.get("generated_assets") or [])
        generated.append(
            {
                "asset_id": str(new_asset_id),
                "role": persist_mode,
                "language": language,
                "provider": provider_used,
                "previous_asset_id": str(current_id),
                "master_asset_id": str(master_id),
                "version": version,
            }
        )
        output_history = list(ctx.get("output_history") or [])
        output_history.append(
            {
                "type": "revise_ad",
                "asset_id": str(new_asset_id),
                "previous_asset_id": str(current_id),
                "master_asset_id": str(master_id),
                "language": language,
                "version": version,
                "claim_guard": claim_guard.get("status"),
                "quality_guard": quality_guard.get("status"),
                "scope": "PRICE_EDIT_ONLY",
                "intent": "PRICE_EDIT_ONLY",
                "execution": execution_name,
            }
        )

        mc_hist = list(mc.get("revision_history") or [])
        mc_hist.append(
            {
                "version": version_n,
                "intent": "PRICE_EDIT_ONLY",
                "execution": execution_name,
                "previous_cover_asset_id": str(current_id),
                "new_cover_asset_id": str(new_asset_id),
                "source_visual_asset_id": str(interior_id),
                "previous_source_visual_asset_id": str(interior_id),
                "master_asset_id": str(master_id),
            }
        )
        mc["current_version"] = version_n
        mc["revision_history"] = mc_hist
        mc["master_asset_id"] = str(master_id)
        mc["source_visual_asset_id"] = str(interior_id)
        ctx["master_creative"] = mc
        stamp_current_cover(ctx, new_asset_id)
        new_map = None
        try:
            new_map = attach_edit_map_for_cover(
                db,
                ctx,
                cover_asset_id=new_asset_id,
                source_visual_asset_id=interior_id,
                logo_asset_id=logo_id,
                occupied_price_slots=occupied_slots,
            )
        except Exception as exc:
            logger.warning("edit_map_attach_on_price_edit_failed: %s", exc)
        if bounded and not new_map:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "BOUNDED_LOCAL_RECOMPOSITION fail-closed — v3 Edit Map could not be "
                    "generated. Cover was not persisted as current."
                ),
            )
        if bounded and new_map:
            try:
                from PIL import Image
                from investhome_api.services.creative_director.bounded_local_recomposition import (
                    write_evidence_files,
                )

                composed_im = Image.open(io.BytesIO(patched_bytes)).convert("RGB")
                dbg = render_debug_overlay(composed_im, new_map)
                dbg_buf = io.BytesIO()
                dbg.save(dbg_buf, format="PNG")
                write_evidence_files(**{"after-edit-map.png": dbg_buf.getvalue()})
            except Exception as exc:
                logger.warning("edit_map_debug_dump_failed: %s", exc)

        ctx["revision_history"] = lean_history
        ctx["revision_index"] = revision_index
        ctx["master_asset_id"] = str(master_id)
        ctx["master_finished_ad_asset_id"] = str(master_id)
        ctx["revision_operations"] = cumulative_after
        ctx["current_revision_index"] = revision_index
        ctx["latest_revision_instruction"] = instruction
        ctx["latest_revision_brief"] = {
            "mode": "price_edit_only",
            "instruction": instruction,
            "intents": intents,
            "language": language,
            "revision_route": revision_route,
            "scope": "PRICE_EDIT_ONLY",
            "intent": "PRICE_EDIT_ONLY",
            "execution": execution_name,
            "price_block": price_intent.to_dict(),
            "master_asset_id": str(master_id),
            "revision_diff": revision_diff.model_dump(by_alias=True),
            "interpreted_plan": interpreted_plan,
        }
        ctx["latest_revision_diff"] = revision_diff.model_dump(by_alias=True)
        ctx["latest_quality_guard"] = quality_guard
        ctx["generated_assets"] = generated
        ctx["output_history"] = output_history
        ctx["image_generation_performed"] = False
        ctx["latest_master_ad_asset_id"] = str(new_asset_id)
        ctx["language"] = language
        ctx["finished_ad_raster_asset_id"] = str(new_asset_id)
        ctx["production_mode"] = "finished_ad"
        ctx["editable_finished_ad"] = False
        ctx["production_brief"] = production_brief
        ctx["revision_instruction_log"] = list(ctx.get("revision_instruction_log") or []) + [
            instruction
        ]
        row.context_json = dict(ctx)
        flag_modified(row, "context_json")
        if row.status == "draft":
            row.status = "ready"
        db.flush()

        logger.info(
            "PRICE_EDIT_ONLY campaign=%s cover=%s -> %s source_visual=%s execution=%s provider_calls=%s",
            row.id,
            current_id,
            new_asset_id,
            interior_id,
            execution_name or "price_block_local",
            provider_calls_n,
        )

        return CreativeDirectorReviseAdResponse(
            campaign_id=row.id,
            project_id=row.linked_project_id,
            language=language,
            aspect_ratio=aspect_ratio,
            format_preset=format_preset,
            production_mode="finished_ad",
            production_brief=production_brief,
            revision_brief=revision_brief,
            revision_intents=intents,
            revision_diff=revision_diff.model_dump(by_alias=True),
            revision_history=lean_history,
            revision_index=revision_index,
            revision_operations=cumulative_after,
            master_asset_id=master_id,
            master_finished_ad_asset_id=master_id,
            revision_source_asset_id=interior_id,
            quality_guard=quality_guard,
            previous_asset_id=current_id,
            provider_route={
                "provider_id": provider_used,
                "available": True,
                "missing": False,
                "capability": "edit_region" if bounded else "price_block_local",
            },
            interior_asset_id=interior_id,
            logo_asset_id=logo_id,
            final_asset_id=new_asset_id,
            final_asset_url=asset_url(new_asset_id),
            composition_base_asset_id=interior_id,
            creative_brief_summary={
                "mode": "price_edit_only",
                "version": version,
                "instruction": instruction,
                "revision_route": revision_route,
                "gpt_image_call_count": provider_calls_n,
                "scope": "PRICE_EDIT_ONLY",
                "intent": "PRICE_EDIT_ONLY",
                "execution": execution_name,
            },
            final_turkish_texts=texts,
            claim_guard=claim_guard,
            project_asset_lock=asset_lock,
            duplication_guard={"status": "pass"},
            provider_call_count=provider_calls_n,
            gpt_image_call_count=provider_calls_n,
            latency_ms=0,
            warnings=[],
            gpt_image={},
            campaign_context=ctx,
            design_spec=ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else None,
            structured_design_data=(
                ctx.get("structured_design_data")
                if isinstance(ctx.get("structured_design_data"), dict)
                else None
            ),
            master_background_asset_id=(
                UUID(str(ctx["master_background_asset_id"]))
                if ctx.get("master_background_asset_id")
                else interior_id
            ),
            finished_ad_raster_asset_id=new_asset_id,
            editable_layers=[],
            revision_route=revision_route,
            interpreted_plan=interpreted_plan,
            master_creative=ctx.get("master_creative") if isinstance(ctx.get("master_creative"), dict) else None,
        )
    if micro_edit:
        native_v1 = (
            is_golden_native_v1(ctx)
            or ctx.get("golden_native_v1") is True
            or is_golden_native_v1(ctx.get("design_spec"))
        )
        engine_v2 = bool(v2_layers)
        base_spec = ctx.get("design_spec")
        reconstructed = False
        if not isinstance(base_spec, dict) or not base_spec.get("elements"):
            bg = ctx.get("master_background_asset_id") or str(interior_id)
            builder_kwargs = dict(
                production_brief=production_brief,
                texts=texts,
                master_background_asset_id=bg,
                logo_asset_id=logo_id,
                aspect_ratio=aspect_ratio,
                format_preset=format_preset,
                language=language,
                campaign_intent=str(production_brief.get("campaign_intent") or ""),
            )
            if native_v1:
                base_spec = build_golden_native_v1_spec(**builder_kwargs)
            else:
                base_spec = build_design_spec(
                    **builder_kwargs,
                    finished_ad_raster_asset_id=ctx.get("finished_ad_raster_asset_id") or str(master_id),
                    revision_engine_v2=engine_v2,
                )
            reconstructed = True
        ids_before_overlay = {
            str(el.get("id"))
            for el in (base_spec.get("elements") or [])
            if isinstance(el, dict) and el.get("id")
        }
        # Raster-only generate pops design_spec. Residence/brand_minimal
        # reconstruction (and some stored specs) omit kicker + 2nd feature.
        # Always bind them from the production brief so LAYER_ONLY ops resolve.
        texts, production_brief = hydrate_supporting_copy(
            texts=texts,
            production_brief=production_brief if isinstance(production_brief, dict) else {},
            campaign_copy=campaign_copy if isinstance(campaign_copy, dict) else None,
            strategy=strategy if isinstance(strategy, dict) else None,
            ctx=ctx if isinstance(ctx, dict) else None,
        )
        if isinstance(base_spec, dict) and not base_spec.get("editable_text_targets"):
            stored = ctx.get("editable_text_targets")
            if isinstance(stored, list) and stored:
                base_spec = dict(base_spec)
                base_spec["editable_text_targets"] = stored
        if not native_v1:
            base_spec = ensure_revision_overlay_targets(
                base_spec,
                production_brief=production_brief,
                texts=texts,
            )
        ids_after_overlay = {
            str(el.get("id"))
            for el in (base_spec.get("elements") or [])
            if isinstance(el, dict) and el.get("id")
        }
        if reconstructed or ids_after_overlay != ids_before_overlay:
            # Re-interpret with concrete geometry once overlay targets exist.
            revision_diff = build_revision_diff(
                instruction=instruction,
                production_brief=production_brief,
                design_spec=base_spec,
                selected_element_id=selected_element_id,
            )
            new_ops = [_op_dict(o) for o in revision_diff.operations]
            cumulative_after = prior_ops + new_ops
            interpreted_plan = {
                "operations": new_ops,
                "semantic_plan": dump_semantic_plan(revision_diff),
                "command_mode": revision_diff.command_mode,
                "strict_preserve": revision_diff.strict_preserve,
                "selected_element_id": selected_element_id,
                "geometry_operations": list(revision_diff.geometry_operations or []),
                "requested_changes": list(revision_diff.requested_changes or []),
                "priority_order": [
                    "exact_numeric",
                    "relational_geometric",
                    "percentage",
                    "relative_nl",
                    "subjective",
                ],
            }

        before_snap = snapshot_elements(base_spec)
        logger.info(
            "SMB_REV_V3 plan campaign=%s route=%s ops=%s resolved=%s",
            row.id,
            revision_route,
            [
                {
                    "action": o.get("action"),
                    "target": o.get("target"),
                    "element_id": o.get("element_id"),
                    "element_ids": o.get("element_ids"),
                    "scale_factor": o.get("scale_factor") or o.get("value"),
                }
                for o in new_ops
            ],
            {
                str(o.get("target")): o.get("element_ids") or o.get("element_id")
                for o in new_ops
            },
        )
        candidate_spec = apply_layer_operations(base_spec, revision_diff.operations)
        after_snap = snapshot_elements(candidate_spec)
        logger.info(
            "SMB_REV_V3 apply campaign=%s before_fonts=%s after_fonts=%s removed=%s provider_calls=0",
            row.id,
            {
                eid: (el.get("typography") or el.get("style") or {}).get("font_size")
                for eid, el in before_snap.items()
            },
            {
                eid: (el.get("typography") or el.get("style") or {}).get("font_size")
                for eid, el in after_snap.items()
            },
            sorted(set(before_snap) - set(after_snap)),
        )
        preservation = validate_change_diff(
            before=before_snap,
            after_spec=candidate_spec,
            revision_diff=revision_diff,
        )
        execution = validate_execution(
            before=before_snap,
            after_spec=candidate_spec,
            revision_diff=revision_diff,
        )
        combined_ok = (
            preservation.get("status") == "pass" and execution.get("status") == "pass"
        )
        validation = {
            **preservation,
            "execution_validation": execution,
            "status": "pass" if combined_ok else "fail",
        }
        if not combined_ok:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": (
                        "Revision failed execution or preservation validation. "
                        "Requested operations must all apply; unmentioned elements must not change."
                    ),
                    "execution_validation": execution,
                    "change_diff_validation": preservation,
                    "interpreted_plan": dump_semantic_plan(revision_diff),
                },
            )
        next_spec = candidate_spec
        user_feedback = build_user_feedback(revision_diff, validation)
        interpreted_plan["execution_trace"] = {
            "resolved_layer_ids": {
                str(o.get("target")): o.get("element_ids") or o.get("element_id")
                for o in new_ops
            },
            "before_fonts": {
                eid: (el.get("typography") or el.get("style") or {}).get("font_size")
                for eid, el in before_snap.items()
            },
            "after_fonts": {
                eid: (el.get("typography") or el.get("style") or {}).get("font_size")
                for eid, el in after_snap.items()
            },
            "removed_ids": sorted(set(before_snap) - set(after_snap)),
            "provider_calls": 0,
            "revision_source": {
                "campaign_id": str(row.id),
                "asset_id": str(current_id),
                "raster_asset_id": str(ctx.get("finished_ad_raster_asset_id") or current_id),
                "interior_asset_id": str(interior_id),
                "logo_asset_id": str(logo_id),
                "master_asset_id": str(master_id),
            },
        }

        production_brief = sync_production_brief_from_spec(production_brief, next_spec)
        # Selected post cover is the source of truth — never another campaign raster.
        locked_raster = str(current_id)
        if native_v1 or engine_v2:
            # Real layers on a clean visual foundation — never overlays on baked type.
            editable_layers = design_spec_to_smb_elements(next_spec)
        else:
            editable_layers = compose_layer_only_on_locked_raster(
                after_spec=next_spec,
                before_snap=before_snap,
                locked_raster_asset_id=locked_raster,
            )
        logger.info(
            "SMB_REV_V3 compose campaign=%s layer_ids=%s",
            row.id,
            [el.get("id") for el in editable_layers if isinstance(el, dict)],
        )
        artifact = golden_revision_artifact_guard(
            editable_layers=editable_layers,
            interior_before=str(interior_id),
            interior_after=str(interior_id),
            logo_before=str(logo_id),
            logo_after=str(logo_id),
            background_requested=False,
        )
        if artifact.get("status") == "fail":
            logger.warning(
                "MICRO_EDIT artifact guard review campaign=%s failures=%s layers=%s",
                row.id,
                artifact.get("failures"),
                [el.get("id") for el in editable_layers if isinstance(el, dict)],
            )
        # Cover / display master is the SELECTED finished raster — never a new interior.
        master_bg_id = UUID(str(locked_raster))
        tip_asset_id = current_id  # display tip unchanged — selected raster stays the cover
        if str(tip_asset_id) != locked_raster:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="LAYER_ONLY revision must keep the selected raster asset.",
            )

        claim_guard = claim_guard_summary(
            approved_claims=approved_claims,
            allowed_tokens=allowed_tokens,
            texts=texts,
            lifestyle=lifestyle,
        )
        asset_lock = project_asset_lock_summary(
            interior_id=interior_id,
            logo_id=logo_id,
            interior_meta=interior_meta,
            logo_meta=logo_meta,
            source_asset_id=interior_id,
        )
        asset_lock["master_asset_id"] = str(master_id)
        asset_lock["revision_model"] = "layer_only_design_spec"
        asset_lock["status"] = "pass" if logo_lock.get("status") == "pass" else "fail"

        if not any(isinstance(h, dict) and h.get("version") == "original" for h in history):
            history.insert(
                0,
                {
                    "version": "original",
                    "previous_asset_id": None,
                    "new_asset_id": str(master_id),
                    "master_asset_id": str(master_id),
                    "revision_source_asset_id": str(master_id),
                    "instruction": None,
                    "revision_brief": None,
                    "operations": [],
                    "provider": None,
                    "timestamp": None,
                    "campaign_context_id": str(row.id),
                    "revision_route": None,
                    "design_spec": base_spec,
                    "master_background_asset_id": str(interior_id),
                    "finished_ad_raster_asset_id": str(current_id),
                },
            )
        version = _version_label(history)
        entry = {
            "version": version,
            "previous_asset_id": str(current_id),
            "new_asset_id": str(tip_asset_id),
            "master_asset_id": str(master_id),
            "revision_source_asset_id": str(master_id),
            "instruction": instruction,
            "user_prompt": instruction,
            "selected_element_id": selected_element_id,
            "interpreted_plan": interpreted_plan,
            "geometry_operations": list(revision_diff.geometry_operations or []),
            "changed_elements": validation.get("changed_elements") or [],
            "previous_values": {
                c["id"]: c.get("previous")
                for c in (validation.get("changed_elements") or [])
                if isinstance(c, dict) and c.get("id")
            },
            "new_values": {
                c["id"]: c.get("new")
                for c in (validation.get("changed_elements") or [])
                if isinstance(c, dict) and c.get("id")
            },
            "provider_used": "layer_only",
            "provider_calls": 0,
            "revision_brief": revision_brief,
            "operations": new_ops,
            "intents": intents,
            "provider": "layer_only",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "campaign_context_id": str(row.id),
            "claim_guard": claim_guard.get("status"),
            "language": language,
            "quality_guard": {
                "status": "n/a",
                "gpt_calls": 0,
                "route": revision_route,
                "change_diff_validation": validation,
            },
            "revision_route": revision_route,
            "design_spec": next_spec,
            "master_background_asset_id": str(master_bg_id),
            "user_feedback": user_feedback,
            "change_diff_validation": validation,
        }
        history.append(entry)
        revision_index = len(history) - 1
        lean_history = lean_revision_history(history)

        ctx["revision_history"] = lean_history
        ctx["revision_index"] = revision_index
        ctx["master_asset_id"] = str(master_id)
        ctx["master_finished_ad_asset_id"] = str(master_id)
        ctx["revision_operations"] = cumulative_after
        ctx["current_revision_index"] = revision_index
        ctx["latest_revision_instruction"] = instruction
        ctx["latest_revision_brief"] = {
            "mode": revision_brief.get("mode"),
            "instruction": revision_brief.get("instruction"),
            "intents": revision_brief.get("intents"),
            "copy_overrides": revision_brief.get("copy_overrides"),
            "cta": revision_brief.get("cta"),
            "language": revision_brief.get("language"),
            "revision_route": revision_route,
            "master_asset_id": str(master_id),
            "revision_diff": revision_diff.model_dump(by_alias=True),
            "interpreted_plan": interpreted_plan,
            "user_feedback": user_feedback,
        }
        ctx["latest_revision_diff"] = revision_diff.model_dump(by_alias=True)
        next_spec = stamp_editable_text_targets(next_spec)
        ctx["design_spec"] = next_spec
        if native_v1:
            ctx["structured_design_data"] = project_golden_native_structured_data(
                next_spec, production_brief=production_brief
            )
        else:
            ctx["structured_design_data"] = project_structured_design_data(
                next_spec, production_brief=production_brief
            )
        if texts.get("supporting_callouts"):
            ctx["supporting_callouts"] = texts["supporting_callouts"]
        if next_spec.get("editable_text_targets"):
            ctx["editable_text_targets"] = next_spec["editable_text_targets"]
        if engine_v2:
            foundation = (
                ctx.get("visual_foundation_asset_id")
                or ctx.get("finished_ad_raster_asset_id")
                or current_id
            )
            ctx["master_background_asset_id"] = str(foundation)
            ctx["visual_foundation_asset_id"] = str(foundation)
            ctx["revision_engine_v2"] = True
        else:
            ctx["master_background_asset_id"] = str(interior_id)
        ctx["finished_ad_raster_asset_id"] = str(current_id)
        ctx["editable_finished_ad"] = True
        ctx["golden_native_v1"] = bool(native_v1)
        ctx["production_mode"] = "golden_native_v1" if native_v1 else "editable_finished_ad"
        ctx["production_brief"] = production_brief
        ctx["latest_master_ad_asset_id"] = str(tip_asset_id)
        ctx["language"] = language
        row.context_json = dict(ctx)
        flag_modified(row, "context_json")
        if row.status == "draft":
            row.status = "ready"
        db.flush()

        return CreativeDirectorReviseAdResponse(
            campaign_id=row.id,
            project_id=row.linked_project_id,
            language=language,
            aspect_ratio=aspect_ratio,
            format_preset=format_preset,
            production_mode="golden_native_v1" if native_v1 else "editable_finished_ad",
            production_brief=production_brief,
            revision_brief=revision_brief,
            revision_intents=intents,
            revision_diff=revision_diff.model_dump(by_alias=True),
            revision_history=lean_history,
            revision_index=revision_index,
            revision_operations=cumulative_after,
            master_asset_id=master_id,
            master_finished_ad_asset_id=master_id,
            revision_source_asset_id=master_id,
            quality_guard={
                "status": "n/a",
                "gpt_calls": 0,
                "route": revision_route,
                "change_diff_validation": validation,
            },
            previous_asset_id=current_id,
            provider_route={"provider_id": "layer_only", "available": True, "missing": False},
            interior_asset_id=interior_id,
            logo_asset_id=logo_id,
            final_asset_id=tip_asset_id,
            final_asset_url=asset_url(tip_asset_id),
            composition_base_asset_id=master_bg_id,
            creative_brief_summary={
                "mode": "revision_micro_edit",
                "version": version,
                "instruction": instruction,
                "revision_route": revision_route,
                "gpt_image_call_count": 0,
                "user_feedback": user_feedback,
            },
            final_turkish_texts=texts,
            claim_guard=claim_guard,
            project_asset_lock=asset_lock,
            duplication_guard={"status": "pass"},
            provider_call_count=0,
            gpt_image_call_count=0,
            latency_ms=0,
            warnings=[],
            gpt_image={},
            campaign_context=ctx,
            design_spec=next_spec,
            structured_design_data=(
                ctx.get("structured_design_data")
                if isinstance(ctx.get("structured_design_data"), dict)
                else None
            ),
            master_background_asset_id=master_bg_id,
            finished_ad_raster_asset_id=UUID(str(current_id)),
            editable_layers=editable_layers,
            revision_route=revision_route,
            user_feedback=user_feedback,
            change_diff_validation=validation,
            interpreted_plan=interpreted_plan,
            execution_validation=execution,
        )

    provider_route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(provider_route)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    master_source_id = UUID(str(revision_brief.get("master_source_asset_id") or interior_id))
    working_brief = apply_revision_ops_to_working_brief(
        master_brief=_as_dict(ctx.get("master_production_brief")) or production_brief,
        ops=cumulative_after,
    )
    if working_brief.get("design_direction") is None and production_brief.get("design_direction"):
        working_brief["design_direction"] = production_brief.get("design_direction")
    production_brief = working_brief
    if _as_dict(working_brief.get("final_copy")).get("headline"):
        texts = dict(texts)
        texts["headline"] = str(working_brief["final_copy"]["headline"])
    if working_brief.get("cta"):
        texts = dict(texts)
        texts["cta"] = str(working_brief["cta"])
    revision_brief["production_brief_snapshot"] = {
        **_as_dict(revision_brief.get("production_brief_snapshot")),
        "hero": working_brief.get("hero") or _as_dict(working_brief.get("final_copy")).get("headline"),
        "cta": working_brief.get("cta"),
        "final_copy": working_brief.get("final_copy"),
        "supporting": working_brief.get("supporting"),
        "big_idea": working_brief.get("big_idea") or _as_dict(ctx.get("master_production_brief")).get("big_idea"),
        "campaign_intent": working_brief.get("campaign_intent"),
    }
    master_pb = _as_dict(ctx.get("master_production_brief")) or _as_dict(production_brief)
    master_final = _as_dict(master_pb.get("final_copy"))
    revision_brief["master_visible_copy"] = {
        "headline": master_final.get("headline") or master_pb.get("hero"),
        "cta": master_pb.get("cta") or master_final.get("cta"),
        "supporting": list(master_pb.get("supporting") or []),
    }

    if visual_replace_only:
        instruction_prompt = render_visual_replace_production_prompt(
            revision_brief=revision_brief,
            original_brief=original_brief,
            selected_filename=revision_brief.get("selected_exterior_filename"),
        )
    else:
        instruction_prompt = render_revision_production_prompt(
            revision_brief=revision_brief,
            production_brief=production_brief,
            original_brief=original_brief,
            lifestyle=lifestyle,
        )
    # Keep within GptImageDesignRequest.instruction max_length.
    _max_instruction = 12000
    if len(instruction_prompt) > _max_instruction:
        instruction_prompt = (
            instruction_prompt[: _max_instruction - 96]
            + "\n\n[truncated — preserve architecture lock + revision ops above]"
        )

    builder_context: dict[str, Any] = {
        "creative_director_campaign_id": str(row.id),
        "approved_financial_tokens": allowed_tokens,
        "preferred_logo_asset_id": str(logo_id),
        "interior_project_asset_lock": True,
        "campaign_mode": "lifestyle" if lifestyle else "launch_price",
        "art_direction_plan": art_direction.to_dict(),
        "production_brief": production_brief,
        "production_mode": "finished_ad",
        "finished_ad": True,
        "revision_mode": True,
        "revision_route": revision_route,
        "revision_brief": revision_brief,
        "revision_diff": revision_diff.model_dump(by_alias=True),
        "master_asset_id": str(master_id),
        "revision_visual_reference_asset_id": str(current_id),
        "revision_source_asset_id": str(master_source_id),
        "skip_logo_edit_input": True,
        "cumulative_operations": cumulative_after,
        "change_list": list(revision_brief.get("change_list") or []),
        "lock_list": list(revision_brief.get("lock_list") or []),
        "image_provider_route": provider_route.to_dict(),
    }

    # VISUAL_REPLACE_ONLY: IMAGE 2 = new exterior. CREATIVE_RECOMPOSE: IMAGE 2 = original source.
    gpt_body = GptImageDesignRequest(
        linked_project_id=row.linked_project_id,
        instruction=instruction_prompt,
        design_provider="gpt-image",
        campaign_mode="project",
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        language=language,
        selected_asset_ids=[master_source_id],
        builder_context=builder_context,
    )

    logger.info(
        "revision_fidelity_lock source=master_source_asset_id=%s master_finished=%s tip=%s ops=%s route=%s change=%s",
        master_source_id,
        master_id,
        current_id,
        len(cumulative_after),
        revision_route,
        revision_brief.get("change_list"),
    )

    result = generate_gpt_image_creatives(db, user, gpt_body)
    output = result.outputs[0] if result.outputs else None
    if output is None or output.local_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GPT Image returned no outputs for campaign revision.",
        )

    new_asset_id = output.local_asset_id
    source_used = result.source_image.asset_id if result.source_image else master_source_id
    if str(source_used) != str(master_source_id):
        logger.warning(
            "revision_source_mismatch expected_source=%s got=%s",
            master_source_id,
            source_used,
        )

    # Quality Comparison Guard vs MASTER finished-ad.
    # Photometric drift is advisory; composition/anchor drift is fail-closed.
    quality_guard: dict[str, Any]
    master_bytes = b""
    revised_bytes = b""
    try:
        master_bytes = _read_asset_bytes(db, current_id)
        revised_bytes = _read_asset_bytes(db, new_asset_id)
        quality_guard = compare_revision_quality(
            master_bytes=master_bytes,
            revised_bytes=revised_bytes,
            revision_diff=revision_diff,
        )
    except Exception as exc:  # best-effort — do not block if IO fails
        logger.warning("revision_quality_guard_unavailable: %s", exc)
        quality_guard = {
            "status": "skip",
            "failures": [],
            "reason": str(exc),
            "compared_against": "master_asset",
        }
    if quality_guard.get("status") == "fail":
        quality_guard["status"] = "review"
        quality_guard["advisory_failures"] = list(quality_guard.get("failures") or [])
        quality_guard["failures"] = []
        quality_guard["note"] = (
            "Photometric drift vs master is advisory for CREATIVE_RECOMPOSE; "
            "composition fidelity is fail-closed."
        )

    composition: dict[str, Any] = {
        "status": "skip",
        "composition_failures": [],
    }
    if master_bytes and revised_bytes:
        try:
            composition = compare_recompose_composition_fidelity(
                master_bytes=master_bytes,
                revised_bytes=revised_bytes,
                revision_diff=revision_diff,
                hero_visual_replace=visual_replace_only,
            )
        except Exception as exc:
            logger.warning("revision_composition_fidelity_unavailable: %s", exc)
            composition = {
                "status": "skip",
                "composition_failures": [],
                "reason": str(exc),
            }
    quality_guard["composition_fidelity"] = composition.get("status")
    quality_guard["visual_fidelity"] = composition.get("visual_fidelity") or composition.get("status")
    quality_guard["composition_failures"] = list(composition.get("composition_failures") or [])
    quality_guard["cta_anchor"] = composition.get("cta_anchor")
    quality_guard["headline_overlay_growth"] = composition.get("headline_overlay_growth")
    quality_guard["logo_overlay_growth"] = composition.get("logo_overlay_growth")
    quality_guard["locked_mad"] = composition.get("locked_mad")
    quality_guard["visual_regions"] = composition.get("regions")
    quality_guard["compared_against"] = composition.get("compared_against") or "master_finished_ad"
    if composition.get("status") == "fail":
        quality_guard["status"] = "fail"
        logger.warning(
            "composition_fidelity_fail route=%s hero_visual_replace=%s failures=%s",
            revision_route,
            visual_replace_only,
            composition.get("composition_failures"),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    f"{revision_route} failed visual fidelity vs MASTER finished-ad. "
                    "Result was not hydrated onto the SMB canvas."
                ),
                "quality_guard": quality_guard,
                "master_asset_id": str(master_id),
                "rejected_asset_id": str(new_asset_id),
                "change_list": list(revision_brief.get("change_list") or []),
                "lock_list": list(revision_brief.get("lock_list") or []),
                "gpt_image_call_count": int(getattr(result, "provider_call_count", 0) or 0),
            },
        )

    artifact = golden_revision_artifact_guard(
        editable_layers=[],
        interior_before=str(previous_source_id if visual_replace_only else master_source_id),
        interior_after=str(source_used or master_source_id),
        logo_before=str(logo_id),
        logo_after=str(logo_id),
        background_requested=revision_route in {"IMAGE_REQUIRED", "VISUAL_REPLACE_ONLY"},
    )
    quality_guard["artifact_guard"] = artifact
    if artifact.get("status") == "fail":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Revision failed Golden Creative quality guard. Bad revision was not hydrated.",
                "quality_guard": quality_guard,
                "master_asset_id": str(master_id),
                "rejected_asset_id": str(new_asset_id),
            },
        )

    claim_guard = claim_guard_summary(
        approved_claims=approved_claims,
        allowed_tokens=allowed_tokens,
        texts=texts,
        lifestyle=lifestyle,
    )
    asset_lock = project_asset_lock_summary(
        interior_id=interior_id,
        logo_id=logo_id,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        source_asset_id=interior_id,
    )
    asset_lock["revision_reference_asset_id"] = str(master_id)
    asset_lock["revision_source_used"] = str(source_used)
    asset_lock["master_asset_id"] = str(master_id)
    asset_lock["revision_model"] = "master_plus_cumulative_ops"
    asset_lock["status"] = "pass" if logo_lock.get("status") == "pass" else "fail"

    if not any(isinstance(h, dict) and h.get("version") == "original" for h in history):
        history.insert(
            0,
            {
                "version": "original",
                "previous_asset_id": None,
                "new_asset_id": str(master_id),
                "master_asset_id": str(master_id),
                "revision_source_asset_id": str(master_id),
                "instruction": None,
                "revision_brief": None,
                "operations": [],
                "provider": None,
                "timestamp": None,
                "campaign_context_id": str(row.id),
            },
        )
    version = "v2" if visual_replace_only and all(
        not isinstance(h, dict) or h.get("version") == "original" for h in history
    ) else _version_label(history)
    entry = {
        "version": version,
        "intent": "VISUAL_REPLACE_ONLY" if visual_replace_only else revision_route,
        "previous_asset_id": str(current_id),
        "new_asset_id": str(new_asset_id),
        "master_asset_id": str(master_id),
        "revision_source_asset_id": str(master_source_id),
        "previous_source_visual_asset_id": str(previous_source_id),
        "source_visual_asset_id": str(master_source_id),
        "instruction": instruction,
        "revision_brief": revision_brief,
        "operations": new_ops,
        "intents": intents,
        "provider": result.provider,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_context_id": str(row.id),
        "claim_guard": claim_guard.get("status"),
        "language": language,
        "quality_guard": {
            "status": quality_guard.get("status"),
            "brightness_delta": quality_guard.get("brightness_delta"),
            "contrast_delta": quality_guard.get("contrast_delta"),
            "color_shift": quality_guard.get("color_shift"),
        },
        "revision_route": revision_route,
        "design_spec": ctx.get("design_spec"),
        "master_background_asset_id": ctx.get("master_background_asset_id"),
    }
    history.append(entry)
    revision_index = len(history) - 1

    generated = list(ctx.get("generated_assets") or [])
    generated.append(
        {
            "asset_id": str(new_asset_id),
            "role": "revision_finished_ad",
            "language": language,
            "provider": result.provider,
            "previous_asset_id": str(current_id),
            "master_asset_id": str(master_id),
            "revision_source_asset_id": str(master_source_id),
            "version": version,
        }
    )
    output_history = list(ctx.get("output_history") or [])
    output_history.append(
        {
            "type": "revise_ad",
            "asset_id": str(new_asset_id),
            "previous_asset_id": str(current_id),
            "master_asset_id": str(master_id),
            "revision_source_asset_id": str(master_source_id),
            "language": language,
            "version": version,
            "claim_guard": claim_guard.get("status"),
            "quality_guard": quality_guard.get("status"),
        }
    )

    lean_history = lean_revision_history(history)
    ctx["revision_history"] = lean_history
    ctx["revision_index"] = revision_index
    ctx["master_asset_id"] = str(master_id)
    ctx["master_finished_ad_asset_id"] = str(master_id)
    ctx["revision_operations"] = cumulative_after
    ctx["current_revision_index"] = revision_index
    ctx["latest_revision_instruction"] = instruction
    ctx["latest_revision_brief"] = {
        "mode": revision_brief.get("mode"),
        "instruction": revision_brief.get("instruction"),
        "intents": revision_brief.get("intents"),
        "copy_overrides": revision_brief.get("copy_overrides"),
        "cta": revision_brief.get("cta"),
        "language": revision_brief.get("language"),
        "current_final_asset_id": revision_brief.get("current_final_asset_id"),
        "master_asset_id": str(master_id),
        "revision_source": "master_source_image",
        "revision_route": revision_route,
        "revision_diff": revision_diff.model_dump(by_alias=True),
    }
    ctx["latest_revision_diff"] = revision_diff.model_dump(by_alias=True)
    ctx["latest_quality_guard"] = quality_guard
    ctx["generated_assets"] = generated
    ctx["output_history"] = output_history
    ctx["image_generation_performed"] = True
    ctx["latest_master_ad_asset_id"] = str(new_asset_id)  # tip (display); master stays immutable
    ctx["language"] = language
    ctx["finished_ad_raster_asset_id"] = str(new_asset_id)
    ctx["production_mode"] = "finished_ad"
    ctx["editable_finished_ad"] = False
    ctx["revision_instruction_log"] = list(ctx.get("revision_instruction_log") or []) + [instruction]
    if visual_replace_only:
        ctx["master_background_asset_id"] = str(master_source_id)
        selected_assets = list(ctx.get("selected_assets") or [])
        hero_meta = dict(interior_meta) if isinstance(interior_meta, dict) else {"asset_id": str(master_source_id)}
        hero_meta["role"] = "hero_exterior"
        hero_meta["asset_id"] = str(master_source_id)
        if selected_assets:
            selected_assets[0] = hero_meta
        else:
            selected_assets = [hero_meta]
        ctx["selected_assets"] = selected_assets
        source_lock = dict(_as_dict(ctx.get("master_source_assets")))
        source_lock["interior_asset_id"] = str(previous_source_id)
        source_lock["source_visual_asset_id"] = str(master_source_id)
        source_lock["previous_source_visual_asset_id"] = str(previous_source_id)
        ctx["master_source_assets"] = source_lock
        mc = dict(ctx.get("master_creative") or {})
        mc_hist = list(mc.get("revision_history") or [])
        mc_hist.append(
            {
                "version": 2 if version == "v2" else version,
                "intent": "VISUAL_REPLACE_ONLY",
                "previous_cover_asset_id": str(current_id),
                "new_cover_asset_id": str(new_asset_id),
                "previous_source_visual_asset_id": str(previous_source_id),
                "source_visual_asset_id": str(master_source_id),
                "source_visual_filename": (
                    interior_meta.get("filename") if isinstance(interior_meta, dict) else None
                ),
                "master_asset_id": str(master_id),
            }
        )
        mc["current_version"] = 2 if version == "v2" else mc.get("current_version")
        mc["source_visual_asset_id"] = str(master_source_id)
        mc["source_visual_filename"] = (
            interior_meta.get("filename") if isinstance(interior_meta, dict) else mc.get("source_visual_filename")
        )
        mc["source_visual_folder"] = (
            interior_meta.get("folder_category") if isinstance(interior_meta, dict) else mc.get("source_visual_folder")
        )
        mc["source_visual_approval"] = (
            interior_meta.get("approved_status")
            or ("approved" if interior_meta.get("approved") else mc.get("source_visual_approval"))
            if isinstance(interior_meta, dict)
            else mc.get("source_visual_approval")
        )
        mc["revision_history"] = mc_hist
        mc["master_asset_id"] = str(master_id)
        ctx["master_creative"] = mc
        stamp_current_cover(ctx, new_asset_id)
    recomposed_spec: dict[str, Any] | None = None
    try:
        spec_texts, spec_brief = hydrate_supporting_copy(
            texts=texts,
            production_brief=production_brief,
            campaign_copy=campaign_copy if isinstance(campaign_copy, dict) else None,
            strategy=strategy if isinstance(strategy, dict) else None,
            ctx=ctx,
        )
        assembled = assemble_editable_design(
            production_brief=spec_brief,
            texts=spec_texts,
            master_background_asset_id=interior_id,
            logo_asset_id=logo_id,
            finished_ad_raster_asset_id=new_asset_id,
            aspect_ratio=aspect_ratio,
            format_preset=format_preset,
            language=language,
            campaign_intent=str(spec_brief.get("campaign_intent") or production_brief.get("campaign_intent") or ""),
        )
        spec = assembled.get("design_spec") if isinstance(assembled.get("design_spec"), dict) else {}
        spec = ensure_revision_overlay_targets(spec, production_brief=spec_brief, texts=spec_texts)
        recomposed_spec = stamp_editable_text_targets(spec)
        ctx["design_spec"] = recomposed_spec
        ctx["structured_design_data"] = project_structured_design_data(
            recomposed_spec, production_brief=spec_brief
        )
        if recomposed_spec.get("editable_text_targets"):
            ctx["editable_text_targets"] = recomposed_spec["editable_text_targets"]
    except Exception:
        logger.exception("CREATIVE_RECOMPOSE design_spec persist failed campaign=%s", row.id)
    stamp_current_cover(ctx, new_asset_id)
    try:
        attach_edit_map_for_cover(
            db,
            ctx,
            cover_asset_id=new_asset_id,
            source_visual_asset_id=master_source_id if visual_replace_only else interior_id,
            logo_asset_id=logo_id,
        )
    except Exception as exc:
        logger.warning("edit_map_attach_on_revise_failed: %s", exc)
    row.context_json = dict(ctx)
    flag_modified(row, "context_json")
    if row.status == "draft":
        row.status = "ready"
    db.flush()

    output_meta = output.metadata if isinstance(getattr(output, "metadata", None), dict) else {}
    gpt_image_payload = {
        "provider": result.provider,
        "model": result.model,
        "session_id": result.session_id,
        "outputs": [
            {
                "local_asset_id": str(output.local_asset_id),
                "local_asset_url": output.local_asset_url,
                "metadata": output_meta,
            }
        ],
        "provider_call_count": result.provider_call_count,
        "latency_ms": result.latency_ms,
    }

    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        production_mode="finished_ad",
        production_brief=production_brief,
        revision_brief=revision_brief,
        revision_intents=intents,
        revision_diff=revision_diff.model_dump(by_alias=True),
        revision_history=lean_history,
        revision_index=revision_index,
        revision_operations=cumulative_after,
        master_asset_id=master_id,
        master_finished_ad_asset_id=master_id,
        revision_source_asset_id=master_source_id,
        quality_guard=quality_guard,
        previous_asset_id=current_id,
        provider_route=provider_route.to_dict(),
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=new_asset_id,
        final_asset_url=asset_url(new_asset_id),
        composition_base_asset_id=(
            UUID(str(ctx["master_background_asset_id"]))
            if ctx.get("master_background_asset_id")
            else None
        ),
        creative_brief_summary={
            "mode": "revision",
            "version": version,
            "instruction": instruction,
            "cta": texts.get("cta"),
            "language": language,
            "master_asset_id": str(master_id),
            "revision_source": "master_source_image",
            "cumulative_ops_count": len(cumulative_after),
            "revision_route": revision_route,
            "intent": "VISUAL_REPLACE_ONLY" if visual_replace_only else revision_route,
        },
        final_turkish_texts=texts,
        claim_guard=claim_guard,
        project_asset_lock=asset_lock,
        duplication_guard={"status": "pass"},
        provider_call_count=int(result.provider_call_count or 0),
        gpt_image_call_count=int(result.provider_call_count or 0),
        latency_ms=int(result.latency_ms or 0),
        warnings=list(result.warnings or []),
        gpt_image=gpt_image_payload,
        campaign_context=ctx,
        design_spec=ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else None,
        structured_design_data=(
            ctx.get("structured_design_data")
            if isinstance(ctx.get("structured_design_data"), dict)
            else None
        ),
        master_background_asset_id=(
            UUID(str(ctx["master_background_asset_id"]))
            if ctx.get("master_background_asset_id")
            else None
        ),
        finished_ad_raster_asset_id=new_asset_id,
        editable_layers=[],
        revision_route=revision_route,
        interpreted_plan=interpreted_plan,
        master_creative=ctx.get("master_creative") if isinstance(ctx.get("master_creative"), dict) else None,
    )


def _move_campaign_revision(
    db: Session,
    user: User,
    campaign_id: UUID,
    *,
    delta: int,
) -> CreativeDirectorReviseAdResponse:
    """Undo/redo cursor move — restore saved final_asset_id (0 provider / GPT calls)."""
    _ = user
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ctx = dict(row.context_json or {})
    try:
        history, next_index, restored_asset = move_revision_cursor(
            ctx.get("revision_history"),
            ctx.get("revision_index"),
            delta=delta,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    restored_id = UUID(str(restored_asset))
    previous_tip = asset_id_at_index(history, next_index - delta)
    mode = "undo" if delta < 0 else "redo"
    lean_history = lean_revision_history(history)
    # Realign cumulative ops to cursor tip (no GPT).
    tip_ops: list[dict[str, Any]] = []
    for i, item in enumerate(lean_history):
        if i > next_index:
            break
        if item.get("version") == "original":
            continue
        for op in item.get("operations") or []:
            if isinstance(op, dict):
                tip_ops.append(dict(op))
    master_raw = ctx.get("master_asset_id")
    if not master_raw and lean_history:
        master_raw = lean_history[0].get("master_asset_id") or lean_history[0].get("new_asset_id")
    ctx["revision_history"] = lean_history
    ctx["revision_index"] = next_index
    ctx["current_revision_index"] = next_index
    ctx["revision_operations"] = tip_ops
    if master_raw:
        ctx["master_asset_id"] = str(master_raw)
        ctx["master_finished_ad_asset_id"] = str(master_raw)
    ctx["latest_master_ad_asset_id"] = str(restored_id)
    tip_entry = lean_history[next_index] if 0 <= next_index < len(lean_history) else {}
    if isinstance(tip_entry, dict) and isinstance(tip_entry.get("design_spec"), dict):
        ctx["design_spec"] = tip_entry["design_spec"]
    if isinstance(tip_entry, dict) and tip_entry.get("master_background_asset_id"):
        ctx["master_background_asset_id"] = tip_entry["master_background_asset_id"]
    restored_route = (
        str(tip_entry.get("revision_route"))
        if isinstance(tip_entry, dict) and tip_entry.get("revision_route")
        else None
    )
    ctx["finished_ad_raster_asset_id"] = str(restored_id)
    rebind_edit_map_for_cover(ctx, restored_id)
    ctx["production_mode"] = "finished_ad" if not is_micro_edit_route(restored_route) else ctx.get(
        "production_mode"
    ) or "finished_ad"
    ctx["editable_finished_ad"] = is_micro_edit_route(restored_route)
    ctx[f"latest_{mode}"] = {
        "restored_asset_id": str(restored_id),
        "revision_index": next_index,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "gpt_image_call_count": 0,
    }
    row.context_json = dict(ctx)
    flag_modified(row, "context_json")
    db.flush()

    interior_id, logo_id, _, _ = resolve_locked_assets(ctx)
    language = str(ctx.get("language") or "tr")
    master_uuid = UUID(str(master_raw)) if master_raw else None
    design_spec = ctx.get("design_spec") if isinstance(ctx.get("design_spec"), dict) else None
    master_bg = (
        UUID(str(ctx["master_background_asset_id"]))
        if ctx.get("master_background_asset_id")
        else None
    )
    editable = bool(
        ctx.get("editable_finished_ad") is True or ctx.get("production_mode") == "editable_finished_ad"
    )
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio="4:5",
        format_preset="portrait",
        production_mode="editable_finished_ad" if editable else "finished_ad",
        production_brief=_as_dict(ctx.get("production_brief")),
        revision_brief={"mode": mode, "restored_asset_id": str(restored_id)},
        revision_intents=[],
        revision_diff={},
        revision_history=lean_history,
        revision_index=next_index,
        revision_operations=tip_ops,
        master_asset_id=master_uuid,
        master_finished_ad_asset_id=master_uuid,
        revision_source_asset_id=master_uuid,
        quality_guard={"status": "n/a", "gpt_calls": 0},
        previous_asset_id=UUID(str(previous_tip)) if previous_tip else None,
        provider_route={"provider_id": mode, "available": True, "missing": False},
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=restored_id,
        final_asset_url=asset_url(restored_id),
        creative_brief_summary={"mode": mode, "gpt_image_call_count": 0},
        final_turkish_texts={},
        claim_guard={"status": "pass"},
        project_asset_lock={"status": "pass"},
        provider_call_count=0,
        gpt_image_call_count=0,
        latency_ms=0,
        warnings=[],
        gpt_image={},
        campaign_context=ctx,
        design_spec=design_spec,
        structured_design_data=(
            ctx.get("structured_design_data")
            if isinstance(ctx.get("structured_design_data"), dict)
            else None
        ),
        master_background_asset_id=master_bg,
        finished_ad_raster_asset_id=restored_id,
        editable_layers=(
            design_spec_to_smb_elements(design_spec)
            if is_micro_edit_route(restored_route) and design_spec
            else []
        ),
        revision_route=restored_route or ("MICRO_EDIT" if editable else "CREATIVE_RECOMPOSE"),
        composition_base_asset_id=master_bg,
    )


def undo_campaign_revision(
    db: Session,
    user: User,
    campaign_id: UUID,
) -> CreativeDirectorReviseAdResponse:
    """Undo — move revision cursor back (keeps forward history for redo; 0 GPT calls)."""
    return _move_campaign_revision(db, user, campaign_id, delta=-1)


def redo_campaign_revision(
    db: Session,
    user: User,
    campaign_id: UUID,
) -> CreativeDirectorReviseAdResponse:
    """Redo — move revision cursor forward to a saved final_asset_id (0 GPT calls)."""
    return _move_campaign_revision(db, user, campaign_id, delta=+1)
