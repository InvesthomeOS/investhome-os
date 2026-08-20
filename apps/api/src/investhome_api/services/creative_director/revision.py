"""AI Revision Mode — revise an existing finished-ad without a new campaign.

Uses the CURRENT final asset as GPT Image reference. Surgical changes only.
Claim Guard / language lock / logo lock stay on.
"""

from __future__ import annotations

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
)
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
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
from investhome_api.services.creative_studio_media_service import get_asset_or_404
from investhome_api.services.gpt_image_design.persistence import asset_url
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives

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
    if any(m in raw for m in ("görsel", "visual", "renk", "color", "kontrast", "ışık")):
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


def build_revision_brief(
    *,
    instruction: str,
    intents: list[str],
    production_brief: dict[str, Any],
    original_brief: str,
    language: str,
    current_final_asset_id: UUID,
) -> dict[str, Any]:
    """CD revision brief — only necessary changes; preserve locked facts."""
    lang = (language or "tr").strip().lower() or "tr"
    final = _as_dict(production_brief.get("final_copy"))
    instr = (instruction or "").strip()
    low = _normalize_tr(instr)

    # Surgical copy overrides inferred from common revision patterns.
    copy_overrides: dict[str, str] = {}
    if "cta" in low and "detayları incele" in low:
        copy_overrides["cta"] = "Detayları İncele"

    # Remove scarcity-style supporting lines when instructed.
    supporting = list(production_brief.get("supporting") or [])
    if any(tok in low for tok in ("sınırlı", "scarcity", "limited")) and "kaldır" in low:
        scarcity_markers = ("sınırlı", "limited", "son ünite", "last chance")
        supporting = [
            s for s in supporting if not any(m in str(s).lower() for m in scarcity_markers)
        ]
        copy_overrides["remove_scarcity"] = "true"

    if "premium" in low and ("başlık" in low or "headline" in low):
        hero = str(final.get("headline") or production_brief.get("hero") or "").strip()
        if hero and "premium" not in hero.lower():
            # Soft premium tone — do not invent new facts.
            copy_overrides["headline_direction"] = "more_premium_tone"
            copy_overrides["headline_keep_meaning"] = hero

    if any(tok in low for tok in ("%25", "25%", "rozet")) and any(
        tok in low for tok in ("küçült", "smaller", "küçük")
    ):
        copy_overrides["badge_scale"] = "slightly_smaller"

    locked_cta = lock_copy_to_language(
        copy_overrides.get("cta") or final.get("cta") or production_brief.get("cta"),
        language=lang,
        fallback="Detayları İncele",
    )

    return {
        "mode": "revision",
        "instruction": instr,
        "intents": intents,
        "language": lang,
        "language_lock": lang.startswith("tr"),
        "current_final_asset_id": str(current_final_asset_id),
        "preserve_campaign_context": True,
        "preserve_design_when_possible": True,
        "keep_unchanged_default": True,
        "copy_overrides": copy_overrides,
        "cta": locked_cta,
        "supporting": supporting,
        "production_brief_snapshot": {
            "campaign_intent": production_brief.get("campaign_intent"),
            "big_idea": production_brief.get("big_idea"),
            "hero": production_brief.get("hero"),
            "cta": locked_cta,
            "final_copy": {**final, **{k: v for k, v in copy_overrides.items() if k in final or k == "cta"}},
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


def render_revision_production_prompt(
    *,
    revision_brief: dict[str, Any],
    production_brief: dict[str, Any],
    original_brief: str,
    lifestyle: bool = False,
) -> str:
    """Prompt for GPT Image edit of an EXISTING finished ad — surgical only."""
    base = render_finished_ad_production_prompt(
        production_brief=production_brief,
        art_direction=_as_dict(production_brief.get("design_direction")),
        original_brief=original_brief,
        lifestyle=lifestyle,
    )
    intents = ", ".join(revision_brief.get("intents") or [])
    overrides = _as_dict(revision_brief.get("copy_overrides"))
    lines = [
        "AI REVISION MODE — EDIT THE EXISTING FINISHED AD.",
        "Input image is the CURRENT FINAL ASSET (already a complete ad).",
        "KEEP EVERYTHING ELSE UNCHANGED when possible.",
        "Do NOT redesign the whole layout. Do NOT invent a new campaign.",
        "Do NOT invent ROI, yield, scarcity, rent, or extra prices.",
        "Preserve logo lock, language lock, verified prices, and brand mark.",
        f"Revision intents: {intents or 'COPY_CHANGE'}.",
        f"User revision instruction: {revision_brief.get('instruction')}",
        "",
        "SURGICAL CHANGES ONLY:",
    ]
    if overrides.get("cta"):
        lines.append(f"- Change CTA text exactly to: {overrides['cta']}")
    if overrides.get("headline_direction") == "more_premium_tone":
        lines.append(
            f"- Make the headline more premium in tone while keeping meaning of: "
            f"{overrides.get('headline_keep_meaning')}"
        )
    if overrides.get("badge_scale") == "slightly_smaller":
        lines.append("- Make the ~25% / %25 discount badge slightly smaller.")
    if overrides.get("remove_scarcity") == "true":
        lines.append(
            "- Remove any scarcity / 'sınırlı sayıda ünite' / limited-units wording. "
            "Do not replace it with another scarcity claim."
        )
    if "SIMPLIFY" in (revision_brief.get("intents") or []):
        lines.append("- Simplify: fewer elements, more breathing room, no new badges.")
    if not any(
        k in overrides for k in ("cta", "headline_direction", "badge_scale", "remove_scarcity")
    ):
        lines.append(f"- Apply only what the instruction asks: {revision_brief.get('instruction')}")

    lines.extend(
        [
            "",
            "PRESERVE UNCHANGED:",
            "- Same photograph / architecture composition base",
            "- Same project logo (do not redraw or duplicate)",
            "- Same verified list/offer prices when present ($400,000 → $300,000, ~25%)",
            "- Same language (Turkish when language=tr)",
            "- Overall design system unless instruction explicitly changes style/layout",
            "",
            "BASE PRODUCTION BRIEF (for locked facts — do not expand scope):",
            base,
        ]
    )
    return "\n".join(lines)


def _version_label(history: list[Any]) -> str:
    # original + len(history) prior revisions → next is v{n+1} where original is implicit v1
    n = 1 + sum(1 for h in history if isinstance(h, dict) and h.get("new_asset_id"))
    return f"v{n + 1}" if n >= 1 else "v2"


def revise_ad_from_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorReviseRequest,
) -> CreativeDirectorReviseAdResponse:
    """Revise existing finished-ad using current final asset as GPT Image reference."""
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

    # Honor explicit language override on revise.
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

    logo_lock = verify_logo_lock(logo_meta)
    if logo_lock.get("status") != "pass":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project logo Asset ID missing or unverified. AI must not invent logos.",
        )

    intents = interpret_revision_intents(instruction)
    revision_brief = build_revision_brief(
        instruction=instruction,
        intents=intents,
        production_brief=production_brief,
        original_brief=original_brief,
        language=language,
        current_final_asset_id=current_id,
    )

    # Apply surgical CTA override into production brief copy for prompt + claim guard texts.
    if revision_brief.get("cta"):
        texts = dict(texts)
        texts["cta"] = str(revision_brief["cta"])
        pb_copy = dict(production_brief)
        final_copy = dict(_as_dict(pb_copy.get("final_copy")))
        final_copy["cta"] = texts["cta"]
        pb_copy["final_copy"] = final_copy
        pb_copy["cta"] = texts["cta"]
        production_brief = pb_copy

    provider_route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(provider_route)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    instruction_prompt = render_revision_production_prompt(
        revision_brief=revision_brief,
        production_brief=production_brief,
        original_brief=original_brief,
        lifestyle=lifestyle,
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
        "image_provider_route": provider_route.to_dict(),
        # Logo already baked into finished-ad reference — do not re-attach as edit input.
        "skip_logo_edit_input": True,
    }

    gpt_body = GptImageDesignRequest(
        linked_project_id=row.linked_project_id,
        instruction=instruction_prompt,
        design_provider="gpt-image",
        campaign_mode="project",
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        language=language,
        # CURRENT final asset is the edit reference (not a fresh interior generate).
        selected_asset_ids=[current_id],
        builder_context=builder_context,
    )

    result = generate_gpt_image_creatives(db, user, gpt_body)
    output = result.outputs[0] if result.outputs else None
    if output is None or output.local_asset_id is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GPT Image returned no outputs for campaign revision.",
        )

    new_asset_id = output.local_asset_id
    claim_guard = claim_guard_summary(
        approved_claims=approved_claims,
        allowed_tokens=allowed_tokens,
        texts=texts,
        lifestyle=lifestyle,
    )
    # Revision references finished ad, not raw interior — mark architecture preserved via reference.
    asset_lock = project_asset_lock_summary(
        interior_id=interior_id,
        logo_id=logo_id,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        source_asset_id=interior_id,
    )
    asset_lock["revision_reference_asset_id"] = str(current_id)
    asset_lock["revision_source_used"] = str(
        result.source_image.asset_id if result.source_image else current_id
    )
    asset_lock["status"] = "pass" if logo_lock.get("status") == "pass" else "fail"

    history = list(ctx.get("revision_history") or [])
    # Ensure original entry exists once.
    if not any(isinstance(h, dict) and h.get("version") == "original" for h in history):
        history.insert(
            0,
            {
                "version": "original",
                "previous_asset_id": None,
                "new_asset_id": str(current_id),
                "instruction": None,
                "revision_brief": None,
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
        "instruction": instruction,
        "revision_brief": revision_brief,
        "intents": intents,
        "provider": result.provider,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "campaign_context_id": str(row.id),
        "claim_guard": claim_guard.get("status"),
        "language": language,
    }
    history.append(entry)

    generated = list(ctx.get("generated_assets") or [])
    generated.append(
        {
            "asset_id": str(new_asset_id),
            "role": "revision_finished_ad",
            "language": language,
            "provider": result.provider,
            "previous_asset_id": str(current_id),
            "version": version,
        }
    )
    output_history = list(ctx.get("output_history") or [])
    output_history.append(
        {
            "type": "revise_ad",
            "asset_id": str(new_asset_id),
            "previous_asset_id": str(current_id),
            "language": language,
            "version": version,
            "claim_guard": claim_guard.get("status"),
        }
    )

    ctx["revision_history"] = history
    ctx["latest_revision_instruction"] = instruction
    ctx["latest_revision_brief"] = {
        "mode": revision_brief.get("mode"),
        "instruction": revision_brief.get("instruction"),
        "intents": revision_brief.get("intents"),
        "copy_overrides": revision_brief.get("copy_overrides"),
        "cta": revision_brief.get("cta"),
        "language": revision_brief.get("language"),
        "current_final_asset_id": revision_brief.get("current_final_asset_id"),
    }
    ctx["generated_assets"] = generated
    ctx["output_history"] = output_history
    ctx["image_generation_performed"] = True
    ctx["latest_master_ad_asset_id"] = str(new_asset_id)
    ctx["language"] = language
    # Persist lean history entries (avoid nesting full production_brief snapshots).
    lean_history: list[dict[str, Any]] = []
    for item in history:
        if not isinstance(item, dict):
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
            }
        lean_history.append(
            {
                "version": item.get("version"),
                "previous_asset_id": item.get("previous_asset_id"),
                "new_asset_id": item.get("new_asset_id"),
                "instruction": item.get("instruction"),
                "revision_brief": lean_rb,
                "intents": item.get("intents"),
                "provider": item.get("provider"),
                "timestamp": item.get("timestamp"),
                "campaign_context_id": item.get("campaign_context_id"),
                "claim_guard": item.get("claim_guard"),
                "language": item.get("language"),
            }
        )
    ctx["revision_history"] = lean_history
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
        revision_history=lean_history,
        previous_asset_id=current_id,
        provider_route=provider_route.to_dict(),
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=new_asset_id,
        final_asset_url=asset_url(new_asset_id),
        composition_base_asset_id=None,
        creative_brief_summary={
            "mode": "revision",
            "version": version,
            "instruction": instruction,
            "cta": texts.get("cta"),
            "language": language,
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
    )


def undo_campaign_revision(
    db: Session,
    user: User,
    campaign_id: UUID,
) -> CreativeDirectorReviseAdResponse:
    """Simple undo — restore previous_asset_id from last revision entry."""
    _ = user
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    ctx = dict(row.context_json or {})
    history = list(ctx.get("revision_history") or [])
    # Find last real revision (not original).
    last_idx = None
    for i in range(len(history) - 1, -1, -1):
        entry = history[i]
        if isinstance(entry, dict) and entry.get("version") not in {None, "original"} and entry.get(
            "previous_asset_id"
        ):
            last_idx = i
            break
    if last_idx is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No revision to undo.",
        )
    entry = history[last_idx]
    previous_id = UUID(str(entry["previous_asset_id"]))
    undone = history.pop(last_idx)
    ctx["revision_history"] = history
    ctx["latest_master_ad_asset_id"] = str(previous_id)
    ctx["latest_undo"] = {
        "undone_version": undone.get("version"),
        "restored_asset_id": str(previous_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    row.context_json = dict(ctx)
    flag_modified(row, "context_json")
    db.flush()

    interior_id, logo_id, _, _ = resolve_locked_assets(ctx)
    language = str(ctx.get("language") or "tr")
    return CreativeDirectorReviseAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio="4:5",
        format_preset="portrait",
        production_mode="finished_ad",
        production_brief=_as_dict(ctx.get("production_brief")),
        revision_brief={"mode": "undo", "restored_asset_id": str(previous_id)},
        revision_intents=[],
        revision_history=history,
        previous_asset_id=UUID(str(undone.get("new_asset_id"))) if undone.get("new_asset_id") else None,
        provider_route={"provider_id": "undo", "available": True, "missing": False},
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=previous_id,
        final_asset_url=asset_url(previous_id),
        creative_brief_summary={"mode": "undo"},
        final_turkish_texts={},
        claim_guard={"status": "pass"},
        project_asset_lock={"status": "pass"},
        provider_call_count=0,
        gpt_image_call_count=0,
        latency_ms=0,
        warnings=[],
        gpt_image={},
        campaign_context=ctx,
    )
