"""AI Revision Mode — MASTER + cumulative ops (never chain prior rasters).

Immutable master_asset_id = first approved finished-ad.
Every revise: MASTER A + cumulative approved ops → provider → current tip.
Undo/Redo: GPT-free cursor over saved final_asset_id versions.
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
    collect_supporting_lines,
    compose_layer_only_on_locked_raster,
    design_spec_to_smb_elements,
    ensure_revision_overlay_targets,
    hydrate_supporting_copy,
    is_micro_edit_route,
    is_provider_revision_route,
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
from investhome_api.services.creative_director.production_brief import (
    lock_copy_to_language,
    render_finished_ad_production_prompt,
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
from investhome_api.services.gpt_image_design.persistence import asset_url
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
    raw = _normalize_tr(instruction).strip()
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
    if any(m in raw for m in ("asset", "görseli değiştir", "foto", "render", "başka görsel")):
        add("ASSET_CHANGE")
    if any(m in raw for m in ("layout", "düzen", "yerleşim", "konum", "aşağı", "yukarı", "küçült", "büyüt")):
        add("LAYOUT_CHANGE")
    if any(m in raw for m in ("stil", "style", "premium", "modern", "editorial")):
        add("STYLE_CHANGE")
    if any(m in raw for m in ("türkçe", "english", "dil", "language", "ingilizce")):
        add("LANGUAGE_CHANGE")
    if any(m in raw for m in ("sade", "simplify", "basit", "azalt", "kalabalık", "sadeleştir")):
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
    parts = [f"- [{conf}] {target}.{action}"]
    if d.get("from") is not None:
        parts.append(f"from={d.get('from')!r}")
    if d.get("to") is not None:
        parts.append(f"to={d.get('to')!r}")
    if d.get("scale_factor") is not None:
        parts.append(f"scale_factor={d.get('scale_factor')}")
    if d.get("note"):
        parts.append(f"({d.get('note')})")
    return " ".join(parts)


def render_revision_production_prompt(
    *,
    revision_brief: dict[str, Any],
    production_brief: dict[str, Any],
    original_brief: str,
    lifestyle: bool = False,
) -> str:
    """Prompt for GPT Image: ORIGINAL SOURCE IMAGE + MASTER creative + cumulative ops."""
    base = render_finished_ad_production_prompt(
        production_brief=production_brief,
        art_direction=_as_dict(production_brief.get("design_direction")),
        original_brief=original_brief,
        lifestyle=lifestyle,
    )
    intents = ", ".join(revision_brief.get("intents") or [])
    overrides = _as_dict(revision_brief.get("copy_overrides"))
    diff = _as_dict(revision_brief.get("revision_diff"))
    cumulative = list(revision_brief.get("cumulative_operations") or [])
    new_ops = list(diff.get("operations") or [])
    preserve = list(diff.get("preserve") or DEFAULT_PRESERVE)
    forbidden = list(diff.get("forbidden_changes") or DEFAULT_FORBIDDEN)
    snapshot = _as_dict(revision_brief.get("production_brief_snapshot"))

    lines = [
        "REVISION CREATIVE BRIEF — REVISE THIS CAMPAIGN, DO NOT CREATE A DIFFERENT CAMPAIGN.",
        "Input image is the ORIGINAL approved project photograph / MASTER source asset.",
        "FORBIDDEN: previous revised raster as source. FORBIDDEN: generation-over-generation.",
        "Preserve the original creative concept, image, logo, palette, CTA style and composition language.",
        "Rebalance typography and spacing only as necessary. Do not redesign the ad.",
        "Do NOT invent a new campaign, new background, new branding, or new architecture.",
        "Do NOT invent ROI, yield, scarcity, rent, or extra prices.",
        f"Revision intents: {intents or 'COPY_CHANGE'}.",
        f"Command mode: {diff.get('command_mode') or 'exact'}.",
        f"Master finished-ad asset id: {revision_brief.get('master_asset_id')}.",
        f"Master source asset id: {revision_brief.get('master_source_asset_id')}.",
        "",
        "ORIGINAL CONCEPT:",
        f"- {snapshot.get('big_idea') or snapshot.get('campaign_intent') or original_brief[:400]}",
        "ORIGINAL HERO MESSAGE:",
        f"- {snapshot.get('hero') or ''}",
        "CURRENT USER REQUEST:",
        f"- {revision_brief.get('instruction') or ''}",
        "",
        "IMAGE QUALITY LOCK — PRESERVE:",
        *[f"- {p}" for p in (QUALITY_LOCK_BRIEF["preserve"])],
        "",
        "IMAGE QUALITY LOCK — FORBIDDEN unless explicitly requested:",
        *[f"- {f}" for f in (QUALITY_LOCK_BRIEF["forbidden_unless_explicitly_requested"])],
        "",
        "If this revision is not about color grading / lighting, do NOT change image treatment.",
        "No darkening, recoloring, cinematic grade, vignette, blur, crop, or contrast boost.",
        "",
        "REQUIRED CHANGES (structured — do not reinterpret exact values):",
    ]
    for op in new_ops:
        lines.append(_format_operation_line(op))

    if cumulative:
        lines.append("")
        lines.append("CUMULATIVE APPROVED OPERATIONS (already accepted — keep all of these):")
        for op in cumulative:
            lines.append(_format_operation_line(op))

    lines.extend(
        [
            "",
            "SURGICAL APPLY:",
        ]
    )
    if overrides.get("headline"):
        lines.append(f"- Set headline text EXACTLY to: {overrides['headline']}")
    if overrides.get("cta"):
        lines.append(f"- Set CTA text EXACTLY to: {overrides['cta']}")
    if overrides.get("headline_direction") == "more_premium_tone":
        lines.append(
            f"- Soft premium tone on headline while keeping meaning of: "
            f"{overrides.get('headline_keep_meaning')} (max 1 targeted change; no redesign)"
        )
    if overrides.get("badge_scale"):
        lines.append(
            f"- Scale the ~25% / %25 discount badge by factor {overrides['badge_scale']} "
            f"relative to MASTER badge size ({overrides.get('badge_scale_note') or ''})."
        )
    if overrides.get("logo_scale"):
        lines.append(f"- Scale project logo by factor {overrides['logo_scale']} (do not redraw).")
    if overrides.get("remove_scarcity") == "true":
        lines.append(
            "- Remove scarcity / 'sınırlı sayıda ünite' / limited-units / support line named. "
            "Do not replace with another scarcity claim."
        )
    if "SIMPLIFY" in (revision_brief.get("intents") or []):
        lines.append("- Simplify: fewer elements, more breathing room, no new badges (max 1–3 mods).")

    lines.extend(
        [
            "",
            "PRESERVE UNCHANGED:",
            *[f"- {p}" for p in preserve],
            "",
            "FORBIDDEN CHANGES:",
            *[f"- {f}" for f in forbidden],
            "",
            "BASE PRODUCTION BRIEF (for locked facts — do not expand scope):",
            base,
        ]
    )
    # Never dump raw user instruction as the sole apply directive.
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
    )
    if revision_route == "LAYER_ONLY":
        revision_route = "MICRO_EDIT"
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
    if source_assets.get("interior_asset_id"):
        revision_brief["master_source_asset_id"] = str(source_assets["interior_asset_id"])

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

    # ── MICRO_EDIT path: mutate design_spec, GPT=0, no hide-plate copy overlays ──
    if micro_edit:
        base_spec = ctx.get("design_spec")
        reconstructed = False
        if not isinstance(base_spec, dict) or not base_spec.get("elements"):
            bg = ctx.get("master_background_asset_id") or str(interior_id)
            base_spec = build_design_spec(
                production_brief=production_brief,
                texts=texts,
                master_background_asset_id=bg,
                logo_asset_id=logo_id,
                finished_ad_raster_asset_id=ctx.get("finished_ad_raster_asset_id") or str(master_id),
                aspect_ratio=aspect_ratio,
                format_preset=format_preset,
                language=language,
                campaign_intent=str(production_brief.get("campaign_intent") or ""),
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
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "message": "MICRO_EDIT revision failed Golden Creative quality guard.",
                    "quality_guard": artifact,
                },
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
        if texts.get("supporting_callouts"):
            ctx["supporting_callouts"] = texts["supporting_callouts"]
        if next_spec.get("editable_text_targets"):
            ctx["editable_text_targets"] = next_spec["editable_text_targets"]
        ctx["master_background_asset_id"] = str(interior_id)
        ctx["finished_ad_raster_asset_id"] = str(current_id)
        ctx["editable_finished_ad"] = True
        ctx["production_mode"] = "editable_finished_ad"
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
            production_mode="editable_finished_ad",
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
        "revision_brief": revision_brief,
        "revision_diff": revision_diff.model_dump(by_alias=True),
        "master_asset_id": str(master_id),
        "revision_source_asset_id": str(master_source_id),
        "cumulative_operations": cumulative_after,
        "image_provider_route": provider_route.to_dict(),
    }

    # CRITICAL: always generate from MASTER source image — never a prior revision raster.
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
        "revision_fidelity_lock source=master_source_asset_id=%s master_finished=%s tip=%s ops=%s route=%s",
        master_source_id,
        master_id,
        current_id,
        len(cumulative_after),
        revision_route,
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

    # Quality Comparison Guard vs MASTER finished-ad (advisory for recompose).
    quality_guard: dict[str, Any]
    try:
        master_bytes = _read_asset_bytes(db, master_id)
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
            "user visual review required."
        )

    artifact = golden_revision_artifact_guard(
        editable_layers=[],
        interior_before=str(master_source_id),
        interior_after=str(source_used or master_source_id),
        logo_before=str(logo_id),
        logo_after=str(logo_id),
        background_requested=revision_route == "IMAGE_REQUIRED",
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
    version = _version_label(history)
    entry = {
        "version": version,
        "previous_asset_id": str(current_id),
        "new_asset_id": str(new_asset_id),
        "master_asset_id": str(master_id),
        "revision_source_asset_id": str(master_id),
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
        if recomposed_spec.get("editable_text_targets"):
            ctx["editable_text_targets"] = recomposed_spec["editable_text_targets"]
    except Exception:
        logger.exception("CREATIVE_RECOMPOSE design_spec persist failed campaign=%s", row.id)
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
        master_background_asset_id=(
            UUID(str(ctx["master_background_asset_id"]))
            if ctx.get("master_background_asset_id")
            else None
        ),
        finished_ad_raster_asset_id=new_asset_id,
        editable_layers=[],
        revision_route=revision_route,
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
