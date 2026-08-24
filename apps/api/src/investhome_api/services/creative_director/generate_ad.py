"""Generate one MASTER Instagram ad from an approved Creative Director Campaign Context.

Reuses GPT Image PROJECT MODE + Final Composition. Does not rewrite CD brief logic.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorGenerateAdResponse,
    CreativeDirectorRecomposeAdRequest,
)
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.art_direction_translator import (
    render_gpt_image_art_direction_prompt,
    translate_campaign_art_direction,
)
from investhome_api.services.creative_director.design_spec import (
    assemble_editable_design,
    collect_supporting_lines,
    ensure_revision_overlay_targets,
    hydrate_supporting_copy,
    stamp_editable_text_targets,
)
from investhome_api.services.creative_director.production_brief import (
    build_production_brief,
    lock_copy_to_language,
    lock_supporting_messages,
    looks_english_ad_copy,
    render_finished_ad_production_prompt,
    verify_logo_lock,
)
from investhome_api.services.creative_director.quality_lock.architecture_truth import (
    annotate_asset_truth,
    architecture_truth_guard,
)
from investhome_api.services.creative_director.quality_lock.intent import is_visual_lifestyle_intent
from investhome_api.services.creative_director.quality_lock.self_critique import (
    critique_and_fix_production_brief,
)
from investhome_api.services.creative_director.provider_router import (
    assert_image_provider_available,
    route_ad_social_image,
)
from investhome_api.services.gpt_image_design.compose import (
    build_slot_plan,
    compose_final_layers,
    render_layout_plan,
)
from investhome_api.services.gpt_image_design.config import canvas_for_preset
from investhome_api.services.gpt_image_design.design_plan import design_plan_to_dict
from investhome_api.services.gpt_image_design.os_composition_plan import count_internal_leaks
from investhome_api.services.gpt_image_design.visual_layout_director import run_visual_layout_director
from investhome_api.services.gpt_image_design.persistence import asset_url, persist_gpt_image, sniff_image_content_type
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives
from investhome_api.services.gpt_image_design.source import ResolvedSourceImage, resolve_image_bytes
from investhome_api.services.creative_studio_media_service import get_asset_or_404, open_asset_content
from investhome_api.schemas.social_design_engine import SocialDesignMediaCandidate


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _asset_id(row: Any) -> UUID | None:
    if isinstance(row, dict):
        raw = row.get("asset_id") or row.get("id")
    else:
        raw = row
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except (TypeError, ValueError):
        return None


def _finished_ad_quality_guard(
    *,
    claim_guard: dict[str, Any],
    asset_lock: dict[str, Any],
    texts: dict[str, str],
    production_brief: dict[str, Any],
    language: str,
    architecture_truth: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Structural quality gate for golden finished-ad path (no layer reconstruction).

    Automatic FAIL on missing logo lock, claim-guard fail, empty primary copy,
    architecture truth fail-closed, or language mismatch signals. Visual overflow/
    premium feel require user review — never declare Visual Quality PASS from this
    guard alone.
    """
    failures: list[str] = []
    checks: dict[str, bool] = {}

    logo_ok = str(asset_lock.get("status") or "").lower() == "pass"
    checks["logo_locked"] = logo_ok
    if not logo_ok:
        failures.append("distorted_or_unlocked_logo")

    claim_ok = str(claim_guard.get("status") or "").lower() in {"pass", "ok", "n/a", "lifestyle"}
    checks["facts_language"] = claim_ok
    if not claim_ok:
        failures.append("claim_guard_fail")

    truth = architecture_truth or {}
    truth_ok = str(truth.get("status") or "pass").lower() in {"pass", "ok", "review", ""}
    if truth.get("fail_closed"):
        truth_ok = False
    checks["architecture_truth"] = truth_ok
    if not truth_ok:
        failures.append("architecture_truth_fail_closed")

    headline = str(texts.get("headline") or production_brief.get("hero") or "").strip()
    checks["headline_present"] = bool(headline)
    if not headline:
        failures.append("missing_headline")

    cta = str(texts.get("cta") or production_brief.get("cta") or "").strip()
    checks["cta_present"] = bool(cta)

    lang = (language or "").lower()
    checks["language_set"] = lang.startswith("tr") or lang.startswith("en")
    if not checks["language_set"]:
        failures.append("language_unset")

    # Heuristic risk flags (warnings only — visual overflow needs human review)
    checks["headline_length_ok"] = len(headline) <= 90
    warnings: list[str] = []
    if headline and not checks["headline_length_ok"]:
        warnings.append("cropped_headline_risk")

    # Hard automatic FAIL only for structural lock / facts / architecture / empty primary
    hard_failures = [f for f in failures if f != "cropped_headline_risk"]
    status_val = "fail" if hard_failures else "review"
    return {
        "status": status_val,
        "mode": "finished_ad",
        "checks": checks,
        "failures": hard_failures,
        "warnings": warnings,
        "architecture_truth": truth or None,
        "automatic_fail_triggers": [
            "text_overflow",
            "cropped_headline",
            "distorted_logo",
            "unreadable_text",
            "architecture_truth_fail_closed",
        ],
        "note": "User visual approval required — do not declare Visual Quality PASS.",
    }


def _resolve_production_mode(
    body: CreativeDirectorGenerateAdRequest | CreativeDirectorRecomposeAdRequest | None,
) -> str:
    if body is None or isinstance(body, CreativeDirectorRecomposeAdRequest):
        return "os_compose"
    if body.skip_gpt_image:
        return "os_compose"
    mode = (body.production_mode or "finished_ad").strip().lower()
    return (
        mode
        if mode in {"finished_ad", "os_compose", "editable_finished_ad"}
        else "finished_ad"
    )


def resolve_locked_assets(ctx: dict[str, Any]) -> tuple[UUID, UUID, dict[str, Any], dict[str, Any]]:
    """PROJECT ASSET LOCK — interior + logo from stored Campaign Context only."""
    selected_assets = _as_list(ctx.get("selected_assets"))
    interior_meta = selected_assets[0] if selected_assets else None
    drive = _as_dict(ctx.get("drive_research"))
    if not isinstance(interior_meta, dict) or _asset_id(interior_meta) is None:
        interior_meta = drive.get("selected_interior") or interior_meta
    logo_meta = ctx.get("selected_logo")
    if not isinstance(logo_meta, dict) or _asset_id(logo_meta) is None:
        logo_meta = drive.get("selected_logo") or logo_meta
    interior_id = _asset_id(interior_meta)
    logo_id = _asset_id(logo_meta)
    if interior_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign Context has no locked interior asset. Cannot generate ad.",
        )
    if logo_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Campaign Context has no locked project logo. Cannot generate ad.",
        )
    logo_dict = _as_dict(logo_meta)
    logo_lock = verify_logo_lock(logo_dict)
    if logo_lock.get("status") != "pass":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project logo Asset ID missing or unverified. AI must not invent logos.",
        )
    logo_dict["logo_locked"] = True
    logo_dict["ai_must_not_draw_logo"] = True
    logo_dict["no_duplicate_logos"] = True
    interior_dict = annotate_asset_truth(_as_dict(interior_meta))
    return interior_id, logo_id, interior_dict, logo_dict


def _brief_requires_historic_plus_addition(original_brief: str) -> bool:
    brief = (original_brief or "").strip().lower()
    return any(
        k in brief
        for k in (
            "historic+addition",
            "historic + addition",
            "historic and addition",
            "tarihi+addition",
            "historic plus addition",
            "historic_plus_addition",
        )
    )


def _brief_bans_unit_and_price(original_brief: str) -> bool:
    brief = (original_brief or "").strip().lower()
    if not brief:
        return False
    ban_markers = ("kullanma", "don't use", "do not use", "must not", "yok")
    bans_unit = "unit 204" in brief and any(m in brief for m in ban_markers)
    bans_price = "fiyat" in brief and any(m in brief for m in ban_markers)
    return bans_unit or bans_price


def _has_price_presentation(pricing: dict[str, Any]) -> bool:
    presentation = _as_dict(pricing.get("price_presentation"))
    return bool(str(presentation.get("list") or "").strip() and str(presentation.get("offer") or "").strip())


def is_lifestyle_campaign(
    *,
    ctx: dict[str, Any],
    pricing: dict[str, Any],
    original_brief: str,
) -> bool:
    """Interior / lifestyle campaigns without launch price dramatization."""
    if _has_price_presentation(pricing):
        return False
    intent = str(ctx.get("campaign_intent") or "").strip().lower()
    if is_visual_lifestyle_intent(intent) or intent in {
        "location",
        "architecture",
        "general_awareness",
        "project_brand",
        "educational",
    }:
        return True
    if intent == "lifestyle":
        return True
    if _brief_bans_unit_and_price(original_brief):
        return True
    return not pricing.get("list_price") and not pricing.get("launch_price")


def filter_active_claims(
    approved_claims: list[Any],
    *,
    lifestyle: bool,
) -> list[Any]:
    """Drop brief-banned unit/financial claims from active ad copy."""
    if not lifestyle:
        return list(approved_claims)
    active: list[Any] = []
    for claim in approved_claims:
        if not isinstance(claim, dict):
            continue
        if claim.get("key") == "unit_code":
            continue
        if claim.get("is_financial"):
            continue
        active.append(claim)
    return active


def _pricing_tokens(
    pricing: dict[str, Any],
    approved_claims: list[Any],
    *,
    lifestyle: bool = False,
) -> list[str]:
    if lifestyle:
        return []
    tokens: list[str] = []
    presentation = _as_dict(pricing.get("price_presentation"))
    for key in ("list", "offer", "copy"):
        val = str(presentation.get(key) or "").strip()
        if val and val not in tokens:
            tokens.append(val)
    discount = _as_dict(presentation.get("discount") or pricing.get("discount"))
    for key in ("display",):
        val = str(discount.get(key) or "").strip()
        if val and val not in tokens:
            tokens.append(val)
    if "~25%" not in tokens and str(discount.get("percent") or "") in {"25", "25.0"}:
        tokens.append("~25%")
    if "25%" not in tokens:
        tokens.append("25%")
    for claim in approved_claims:
        if not isinstance(claim, dict):
            continue
        display = str(claim.get("display") or "").strip()
        if display and display not in tokens:
            tokens.append(display)
    # Canonical Unit 204 launch pair — never invent extras.
    for required in ("$400,000", "$300,000", "Unit 204"):
        if required not in tokens:
            tokens.append(required)
    return tokens


def _looks_history_modern(*, big_idea: str, emphasis: list[Any], brief: str) -> bool:
    hay = " ".join(
        [
            big_idea or "",
            " ".join(str(x) for x in emphasis),
            brief or "",
        ]
    ).lower()
    historic = any(tok in hay for tok in ("history", "historic", "heritage", "tarihi", "tarih"))
    modern = "modern" in hay
    return historic and modern


def adapt_final_turkish_texts(
    *,
    language: str,
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any],
    pricing: dict[str, Any],
    approved_claims: list[Any],
    original_brief: str,
    lifestyle: bool = False,
) -> dict[str, str]:
    """Map CD concept → natural Turkish ad copy. Facts stay locked to approved claims."""
    lang = (language or "tr").strip().lower() or "tr"
    big_idea = str(
        campaign_copy.get("big_idea") or strategy.get("big_idea") or strategy.get("concept") or ""
    ).strip()
    emphasis = _as_list(campaign_copy.get("emphasis") or strategy.get("emphasis"))
    hero = str(campaign_copy.get("hero_message") or strategy.get("hero_message") or "").strip()
    sales_hook = str(campaign_copy.get("sales_hook") or strategy.get("sales_hook") or "").strip()
    cta_src = str(campaign_copy.get("cta") or strategy.get("cta") or "").strip()
    value_src = str(
        campaign_copy.get("value_proposition") or strategy.get("value_proposition") or ""
    ).strip()
    support_msgs = lock_supporting_messages(
        _as_list(campaign_copy.get("supporting_messages") or strategy.get("supporting_messages")),
        language=lang,
        max_items=3,
    )

    if lifestyle:
        headline = lock_copy_to_language(
            big_idea or hero, language=lang, fallback="Eviniz, Sığınak"
        ) or "Eviniz, Sığınak"
        hero_tr = lock_copy_to_language(hero, language=lang, fallback=headline) or headline
        sales_line = lock_copy_to_language(sales_hook, language=lang, fallback=hero_tr) or hero_tr
        callouts = support_msgs[:3]
        supporting = " · ".join(callouts) if callouts else sales_line
        cta = lock_copy_to_language(cta_src, language=lang, fallback="Detayları Keşfet") or "Detayları Keşfet"
        eyebrow = sales_line
        return {
            "language": lang,
            "big_idea": headline,
            "hero": hero_tr,
            "sales_hook": sales_line,
            "eyebrow": eyebrow,
            "headline": headline,
            "supporting": supporting,
            "supporting_callouts": "|".join(callouts),
            "offer": "",
            "list_price": "",
            "offer_price": "",
            "value": lock_copy_to_language(value_src, language=lang, fallback=""),
            "value_badge": "",
            "cta": cta,
            "unit": "",
            "price_hierarchy": "",
            "campaign_mode": "lifestyle",
        }

    presentation = _as_dict(pricing.get("price_presentation"))
    list_price = str(presentation.get("list") or "$400,000").strip()
    offer_price = str(presentation.get("offer") or "$300,000").strip()
    discount = _as_dict(presentation.get("discount") or pricing.get("discount"))
    discount_display = str(discount.get("display") or "~25%").strip() or "~25%"
    unit_display = "Unit 204"
    for claim in approved_claims:
        if isinstance(claim, dict) and claim.get("key") == "unit_code":
            unit_display = str(claim.get("display") or unit_display).strip() or unit_display
            break

    price_hierarchy = f"{list_price} → {offer_price}"
    value_badge = f"{discount_display} lansman fiyat avantajı"

    if lang.startswith("tr"):
        if _looks_history_modern(big_idea=big_idea, emphasis=emphasis, brief=original_brief):
            # Adaptive TR compression of History↔Modernity (brief already asks modern/şık/tarihi).
            brief_l = (original_brief or "").lower()
            parts = ["Modern"]
            if any(tok in brief_l for tok in ("şık", "sik", "stylish", "elegant")) or any(
                "stylish" in str(e).lower() or "şık" in str(e).lower() for e in emphasis
            ):
                parts.append("Şık")
            parts.append("Tarihi")
            headline = ". ".join(parts) + "."
        elif big_idea and not looks_english_ad_copy(big_idea):
            headline = big_idea if _has_turkish_chars(big_idea) else (hero if _has_turkish_chars(hero) else "Tarihi karakter. Modern yaşam.")
        else:
            headline = (
                hero
                if _has_turkish_chars(hero) and not looks_english_ad_copy(hero)
                else "Tarihi karakter. Modern yaşam."
            )

        eyebrow = f"{unit_display} Lansman Fırsatı"
        if "204" in sales_hook or "launch" in sales_hook.lower() or "lansman" in sales_hook.lower() or looks_english_ad_copy(sales_hook):
            sales_line = f"{unit_display} Lansman Fırsatı"
        else:
            sales_line = sales_hook if _has_turkish_chars(sales_hook) else eyebrow

        supporting = f"{unit_display} Lansman Fırsatı"
        # Price hierarchy + value sit in verified/OS location line for accuracy.

        cta = lock_copy_to_language(cta_src, language=lang, fallback="Detayları İncele") or "Detayları İncele"
        if any(tok in cta_src.lower() for tok in ("explore", "schedule", "viewing", "details", "learn more")):
            cta = "Detayları İncele"

        hero_tr = (
            hero
            if _has_turkish_chars(hero) and not looks_english_ad_copy(hero)
            else "Tarihi karakterle modern yaşam bir arada."
        )
        value_tr = value_badge if looks_english_ad_copy(value_src) or "lansman" in value_src.lower() or not _has_turkish_chars(value_src) else value_src
    else:
        # Language field exists for later EN reuse — this sprint only ships TR.
        headline = big_idea or hero or "History Meets Modernity"
        eyebrow = sales_hook or f"{unit_display} Launch Opportunity"
        sales_line = sales_hook or eyebrow
        supporting = f"{price_hierarchy} · {discount_display} launch price advantage"
        cta = cta_src or "Explore Details"
        hero_tr = hero
        value_tr = value_src or f"{discount_display} launch price advantage"

    return {
        "language": lang,
        "big_idea": headline,
        "hero": hero_tr,
        "sales_hook": sales_line,
        "eyebrow": eyebrow,
        "headline": headline,
        "supporting": supporting,
        "supporting_callouts": "|".join(support_msgs) if lifestyle else "",
        "offer": price_hierarchy,
        "list_price": list_price,
        "offer_price": offer_price,
        "value": value_tr if lang.startswith("tr") else (value_src or value_badge),
        "value_badge": value_badge if lang.startswith("tr") else f"{discount_display} launch price advantage",
        "cta": cta,
        "unit": unit_display,
        "price_hierarchy": price_hierarchy,
        "campaign_mode": "launch_price",
    }


def _has_turkish_chars(text: str) -> bool:
    return any(ch in (text or "") for ch in "çÇğĞıİöÖşŞüÜ")


def build_gpt_instruction(
    *,
    strategy: dict[str, Any],
    campaign_copy: dict[str, Any],
    pricing: dict[str, Any],
    texts: dict[str, str],
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    original_brief: str,
    language: str,
) -> str:
    """Full CD brief → GPT Image instruction. Composition stays flexible; facts/assets locked."""
    presentation = _as_dict(pricing.get("price_presentation"))
    support = _as_list(campaign_copy.get("supporting_messages") or strategy.get("supporting_messages"))
    emphasis = _as_list(campaign_copy.get("emphasis") or strategy.get("emphasis"))
    lines = [
        "MASTER Instagram 4:5 feed ad for The Temple — PROJECT MODE edit of the locked interior render.",
        f"LANGUAGE: {language} (all final OS-typeset copy is {language}; compose atmosphere only).",
        "CREATIVE DIRECTOR BRIEF (authoritative concept — adapt visually, do not invent facts):",
        f"- Big Idea: {campaign_copy.get('big_idea') or strategy.get('big_idea') or strategy.get('concept')}",
        f"- Hero: {campaign_copy.get('hero_message') or strategy.get('hero_message')}",
        f"- Sales Hook: {campaign_copy.get('sales_hook') or strategy.get('sales_hook')}",
        f"- Offer: {campaign_copy.get('offer') or presentation.get('copy')}",
        f"- Price hierarchy (OS typeset): {texts['list_price']} (secondary) → {texts['offer_price']} (primary)",
        f"- Value: {texts['value_badge']}",
        f"- Emphasis: {', '.join(str(x) for x in emphasis) if emphasis else 'n/a'}",
        f"- Supporting: {'; '.join(str(x) for x in support[:4]) if support else 'n/a'}",
        f"- CTA (OS typeset): {texts['cta']}",
        f"- Tone: {strategy.get('tone') or 'premium luxury editorial'}",
        f"- Visual direction: {strategy.get('visual_direction') or campaign_copy.get('visual_direction') or ''}",
        f"- Composition direction (flexible — do NOT force left panel / bottom band templates): "
        f"{strategy.get('composition_direction') or 'premium editorial RE; strong sales hierarchy; few effective words'}",
        f"- Typography direction: {strategy.get('typography_direction') or ''}",
        f"- Color direction: {strategy.get('color_direction') or ''}",
        "BRAND: The Temple project identity + Investhome supporting brand. Real logo composited by OS — never draw it.",
        "SOURCE CONSTRAINTS / PROJECT ASSET LOCK:",
        f"- Locked interior filename: {interior_meta.get('filename')} (asset {interior_meta.get('asset_id')}).",
        "- Preserve room geometry, windows, furniture layout, architecture, materials — do NOT invent another living room.",
        "- Do NOT change interior architecture. No other interior substitute.",
        f"- Locked logo filename: {logo_meta.get('filename')} (asset {logo_meta.get('asset_id')}) — OS composites; never redraw.",
        "GOAL: premium luxury editorial real-estate campaign, strong sales message, strong price hierarchy, "
        "professional CTA air, brand integrity. Creative composition is flexible.",
        "APPROVED FINANCIAL CLAIMS ONLY (do not invent yields/ROI/rent):",
        f"- {texts['unit']}",
        f"- {texts['price_hierarchy']}",
        f"- {texts['value_badge']}",
        "FINAL OS COPY PREVIEW (do not rasterize — leave contrast/air for these zones):",
        f"- Eyebrow: {texts['eyebrow']}",
        f"- Headline: {texts['headline']}",
        f"- Supporting: {texts['supporting']}",
        f"- CTA: {texts['cta']}",
        "ORIGINAL USER BRIEF:",
        original_brief.strip(),
    ]
    return "\n".join(lines)


def claim_guard_summary(
    *,
    approved_claims: list[Any],
    allowed_tokens: list[str],
    texts: dict[str, str],
    lifestyle: bool = False,
) -> dict[str, Any]:
    """Claim Guard — launch price pair OR lifestyle interior (no unit/price in copy)."""
    if lifestyle:
        blob = " ".join(str(v) for v in texts.values()).lower()
        banned_hits = [
            tok
            for tok in (
                "unit 204",
                "$400",
                "$300",
                "400,000",
                "300,000",
                "lansman fiyat",
                "~25%",
                "25%",
            )
            if tok in blob
        ]
        if texts.get("unit"):
            banned_hits.append("unit_in_forced_copy")
        invented_blocked = True
        for claim in approved_claims:
            if not isinstance(claim, dict):
                continue
            if claim.get("is_financial") and not claim.get("verified", False):
                invented_blocked = False
        return {
            "status": "pass" if not banned_hits and invented_blocked else "fail",
            "campaign_mode": "lifestyle",
            "approved_claims": approved_claims,
            "allowed_financial_tokens": allowed_tokens,
            "banned_public_tokens_blocked": not banned_hits,
            "violations": banned_hits,
            "invented_financial_claims_blocked": invented_blocked,
        }

    required = {
        texts["unit"],
        texts["list_price"],
        texts["offer_price"],
        texts.get("value_badge", ""),
    }
    missing = [
        tok
        for tok in (texts["list_price"], texts["offer_price"], "~25%", "Unit 204")
        if tok not in " ".join(allowed_tokens)
    ]
    # ~25% may appear as display token
    if any("~25%" in t or t == "25%" for t in allowed_tokens):
        missing = [m for m in missing if m not in {"~25%", "25%"}]
    invented_blocked = True
    for claim in approved_claims:
        if not isinstance(claim, dict):
            continue
        # Financial public claims must be verified; unit confirmation may be soft.
        if claim.get("key") in {"list_price", "launch_price", "launch_discount_percent"}:
            if claim.get("is_financial") and not claim.get("verified", False):
                invented_blocked = False
    return {
        "status": "pass" if not missing and invented_blocked else "fail",
        "campaign_mode": "launch_price",
        "approved_claims": approved_claims,
        "allowed_financial_tokens": allowed_tokens,
        "required_public_tokens": sorted(t for t in required if t),
        "missing_required_tokens": missing,
        "invented_financial_claims_blocked": invented_blocked,
        "public_price_hierarchy": texts["price_hierarchy"],
        "public_value_badge": texts.get("value_badge"),
    }


def project_asset_lock_summary(
    *,
    interior_id: UUID,
    logo_id: UUID,
    interior_meta: dict[str, Any],
    logo_meta: dict[str, Any],
    source_asset_id: UUID | None,
) -> dict[str, Any]:
    locked_ok = source_asset_id is not None and source_asset_id == interior_id
    logo_lock = verify_logo_lock(logo_meta)
    truth = annotate_asset_truth(dict(interior_meta or {}))
    return {
        "status": "pass" if locked_ok and logo_lock.get("status") == "pass" else "fail",
        "interior_asset_id": str(interior_id),
        "interior_filename": interior_meta.get("filename"),
        "logo_asset_id": str(logo_id),
        "logo_filename": logo_meta.get("filename"),
        "logo_locked": bool(logo_lock.get("logo_locked")),
        "verified_project_logo": bool(logo_lock.get("verified_project_logo")),
        "source_used_asset_id": str(source_asset_id) if source_asset_id else None,
        "interior_architecture_locked": True,
        "logo_os_composited": True,
        "gpt_must_not_invent_interior": True,
        "gpt_must_not_draw_logo": True,
        "ai_must_not_draw_logo": True,
        "no_duplicate_logos": True,
        "asset_id": str(interior_id),
        "classification": truth.get("classification"),
        "architecture_locked": bool(truth.get("architecture_locked")),
        "creative_freedom_level": truth.get("creative_freedom_level"),
        "project_relation": truth.get("project_relation"),
        "approved_status": truth.get("approved_status"),
        "approved": bool(truth.get("approved")),
        "no_invented_architecture": True,
    }


def _load_background_bytes(db: Session, asset_id: UUID, *, linked_project_id: UUID) -> tuple[bytes, Any]:
    asset = get_asset_or_404(asset_id, db)
    if asset.linked_project_id != linked_project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Background asset does not belong to this campaign project.",
        )
    stream, _ctype = open_asset_content(asset, linked_project_id=linked_project_id)
    return stream.read(), asset


def _resolve_logo_image(
    db: Session,
    *,
    linked_project_id: UUID,
    logo_id: UUID,
    logo_meta: dict[str, Any],
) -> ResolvedSourceImage | None:
    asset = get_asset_or_404(logo_id, db)
    candidate = SocialDesignMediaCandidate(
        asset_id=logo_id,
        filename=str(logo_meta.get("filename") or asset.filename or "logo.svg"),
        content_type=str(asset.content_type or "image/svg+xml"),
        folder_category=str(asset.folder_category or "01_BRAND"),
        tags=list(asset.tags or []),
        score=1.0,
        linked_project_id=linked_project_id,
    )
    return resolve_image_bytes(
        db,
        linked_project_id=linked_project_id,
        candidate=candidate,
        role="project_logo",
        allow_svg=True,
    )


def _prepare_campaign_ad_context(
    db: Session,
    campaign_id: UUID,
    body: CreativeDirectorGenerateAdRequest | CreativeDirectorRecomposeAdRequest | None,
):
    """Shared Campaign Context prep for generate + recompose."""
    body = body or CreativeDirectorGenerateAdRequest()
    row = db.get(CreativeDirectorCampaign, campaign_id)
    if row is None or row.archived_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")

    ctx = dict(row.context_json or {})
    strategy = _as_dict(ctx.get("cd_strategy"))
    campaign_copy = _as_dict(ctx.get("campaign_copy"))
    pricing = _as_dict(ctx.get("pricing"))
    original_brief = str(ctx.get("original_user_brief") or row.original_brief or "")
    lifestyle = is_lifestyle_campaign(ctx=ctx, pricing=pricing, original_brief=original_brief)
    approved_claims = filter_active_claims(
        list(ctx.get("approved_claims") or pricing.get("claims") or []),
        lifestyle=lifestyle,
    )
    language = (body.language or ctx.get("language") or "tr").strip().lower() or "tr"
    if ctx.get("language") != language:
        ctx["language"] = language
        row.context_json = ctx
        db.flush()

    interior_id, logo_id, interior_meta, logo_meta = resolve_locked_assets(ctx)
    texts = adapt_final_turkish_texts(
        language=language,
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        approved_claims=approved_claims,
        original_brief=original_brief,
        lifestyle=lifestyle,
    )
    allowed_tokens = _pricing_tokens(pricing, approved_claims, lifestyle=lifestyle)
    format_preset = (body.format_preset or "portrait").strip() or "portrait"
    aspect_ratio = (body.aspect_ratio or "4:5").strip() or "4:5"
    art_direction = translate_campaign_art_direction(
        ctx=ctx,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        language=language,
        lifestyle=lifestyle,
    )
    production_brief = build_production_brief(
        ctx=ctx,
        strategy=strategy,
        campaign_copy=campaign_copy,
        pricing=pricing,
        texts=texts,
        approved_claims=approved_claims,
        blocked_claims=list(ctx.get("blocked_claims") or []),
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        art_direction=art_direction.to_dict(),
        message_strategy=ctx.get("message_strategy"),
        design_direction=ctx.get("design_direction"),
        simplicity_director=ctx.get("simplicity_director"),
        campaign_intent=str(ctx.get("campaign_intent") or ""),
    )
    recent_ids: list[str] = []
    for item in _as_list(ctx.get("output_history")):
        if isinstance(item, dict) and item.get("interior_asset_id"):
            recent_ids.append(str(item["interior_asset_id"]))
    for asset in _as_list(ctx.get("generated_assets")):
        if isinstance(asset, dict) and asset.get("source_asset_id"):
            recent_ids.append(str(asset["source_asset_id"]))
    production_brief, critique = critique_and_fix_production_brief(
        production_brief,
        campaign_intent=str(ctx.get("campaign_intent") or ""),
        recent_asset_ids=recent_ids,
    )
    ctx["production_brief"] = production_brief
    ctx["self_critique"] = critique
    row.context_json = ctx
    db.flush()
    return (
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
    )


def recompose_ad_from_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorRecomposeAdRequest | None = None,
) -> CreativeDirectorGenerateAdResponse:
    """Regenerate OS Final Composition from an existing clean background — no GPT Image call."""
    prep = _prepare_campaign_ad_context(db, campaign_id, body)
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
    if body is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="background_asset_id is required for recompose.",
        )
    background_id = body.background_asset_id
    base_bytes, base_asset = _load_background_bytes(
        db,
        background_id,
        linked_project_id=row.linked_project_id,
    )
    canvas_w, canvas_h = canvas_for_preset(format_preset)
    logo_image = _resolve_logo_image(
        db,
        linked_project_id=row.linked_project_id,
        logo_id=logo_id,
        logo_meta=logo_meta,
    )
    if logo_image is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project logo could not be loaded for OS recomposition.",
        )
    callouts = [x.strip() for x in str(texts.get("supporting_callouts") or "").split("|") if x.strip()]
    slots = build_slot_plan(
        visible_copy={
            "headline": texts["headline"],
            "supporting": texts.get("supporting", ""),
            "cta": texts["cta"],
            "supporting_callouts": texts.get("supporting_callouts", ""),
        },
        verified_lines=[],
        include_slogan=True,
        feature_callouts=callouts,
    )

    def _render_plan(plan):
        result = render_layout_plan(
            base_bytes,
            logos=[logo_image],
            slots=slots,
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            plan=plan,
        )
        return result.layers

    vld = run_visual_layout_director(
        background_bytes=base_bytes,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        texts=texts,
        art_direction=art_direction.to_dict(),
        lifestyle=lifestyle,
        has_project_logo=True,
        has_investhome_logo=False,
        include_slogan=True,
        render_fn=_render_plan,
        max_passes=2,
        campaign_id=str(campaign_id),
        background_asset_id=str(background_id),
    )
    design_plan = vld.design_plan
    composition = render_layout_plan(
        base_bytes,
        logos=[logo_image],
        slots=slots,
        canvas_width=canvas_w,
        canvas_height=canvas_h,
        base_asset_id=base_asset.id,
        plan=design_plan,
    )
    vld_report = dict(vld.report)
    vld_report["final_asset_id"] = None  # filled after persist
    asset = persist_gpt_image(
        db,
        actor=user,
        linked_project_id=row.linked_project_id,
        content=composition.png_bytes,
        content_type=sniff_image_content_type(composition.png_bytes),
        campaign_mode="project-recompose",
        session_id=str(campaign_id),
        provider_generation_id=None,
        campaign_context_id=str(row.id),
        brief_excerpt="os-recompose",
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
    layer_texts = [
        str(el.get("content") or el.get("label") or "")
        for el in composition.layers
        if isinstance(el, dict)
    ]
    leak_count = count_internal_leaks(*layer_texts)
    duplication_guard = dict(composition.duplication_guard or {})
    duplication_guard["internal_leak_count"] = leak_count

    creative_brief_summary = {
        "big_idea": campaign_copy.get("big_idea") or strategy.get("big_idea"),
        "composition_family": design_plan.composition_type,
        "headline_runs": next(
            (el.get("runs") for el in composition.layers if el.get("id") == "text-headline"),
            None,
        ),
        "feature_layers": [el for el in composition.layers if str(el.get("id", "")).startswith("feature-")],
        "art_direction": art_direction.to_dict(),
        "editable_elements": [el.get("id") for el in composition.layers if el.get("id")],
        "internal_leak_count": leak_count,
        "background_aware_placement": design_plan.negative_space,
        "visual_layout_director": vld_report,
        "layout_plan": vld.layout_plan.to_dict(),
    }

    ctx = dict(row.context_json or {})
    generated = list(ctx.get("generated_assets") or [])
    generated.append(
        {
            "asset_id": str(asset.id),
            "role": "master_instagram_4_5_recompose",
            "language": language,
            "provider": "os-recompose",
            "composition_base_asset_id": str(base_asset.id),
        }
    )
    history = list(ctx.get("output_history") or [])
    history.append(
        {
            "type": "recompose_ad",
            "asset_id": str(asset.id),
            "language": language,
            "format": aspect_ratio,
            "background_asset_id": str(background_id),
            "gpt_image_call_count": 0,
        }
    )
    ctx["generated_assets"] = generated
    ctx["output_history"] = history
    ctx["latest_master_ad_asset_id"] = str(asset.id)
    row.context_json = ctx
    db.flush()

    vld_report["final_asset_id"] = str(asset.id)
    creative_brief_summary["visual_layout_director"] = vld_report

    gpt_image_payload = {
        "outputs": [
            {
                "local_asset_id": str(asset.id),
                "local_asset_url": asset_url(asset.id),
                "composition_base_asset_id": str(base_asset.id),
                "canvas_width": canvas_w,
                "canvas_height": canvas_h,
                "layers": composition.layers,
                "metadata": {
                    "composition_type": design_plan.composition_type,
                    "design_plan_variation": design_plan.variation,
                    "duplication_guard": duplication_guard,
                    "gpt_generated_text_count": 0,
                    "gpt_generated_logo_count": 0,
                    "internal_leak_count": leak_count,
                    "background_asset_id": str(base_asset.id),
                    "visual_layout_director": vld_report,
                    "layout_plan": vld.layout_plan.to_dict(),
                },
            }
        ],
        "provider_call_count": 0,
        "brief": {"design_plan": design_plan_to_dict(design_plan), "layout_plan": vld.layout_plan.to_dict()},
    }

    return CreativeDirectorGenerateAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        production_mode="os_compose",
        production_brief=production_brief,
        provider_route={"provider_id": "os-recompose", "available": True, "missing": False},
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=asset.id,
        final_asset_url=asset_url(asset.id),
        composition_base_asset_id=base_asset.id,
        creative_brief_summary=creative_brief_summary,
        final_turkish_texts=texts,
        claim_guard=claim_guard,
        project_asset_lock=asset_lock,
        duplication_guard=duplication_guard,
        provider_call_count=0,
        gpt_image_call_count=0,
        latency_ms=0,
        warnings=list(composition.warnings),
        gpt_image=gpt_image_payload,
    )


def generate_ad_from_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorGenerateAdRequest | None = None,
) -> CreativeDirectorGenerateAdResponse:
    """Load Campaign Context → GPT Image PROJECT MODE → persist final ML asset."""
    body = body or CreativeDirectorGenerateAdRequest()
    if body.skip_gpt_image:
        if body.background_asset_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="background_asset_id is required when skip_gpt_image=true",
            )
        return recompose_ad_from_campaign(
            db,
            user,
            campaign_id,
            CreativeDirectorRecomposeAdRequest(
                language=body.language,
                aspect_ratio=body.aspect_ratio,
                format_preset=body.format_preset,
                background_asset_id=body.background_asset_id,
            ),
        )

    prep = _prepare_campaign_ad_context(db, campaign_id, body)
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
    production_mode = _resolve_production_mode(body)
    provider_route = route_ad_social_image(prefer_edit=True)
    try:
        assert_image_provider_available(provider_route)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    # Fail-closed BEFORE provider spend when architectural fidelity cannot be established.
    pre_truth = architecture_truth_guard(
        hero_meta=interior_meta,
        source_asset_id=str(interior_id),
        campaign_intent=str(
            ctx.get("campaign_intent") or production_brief.get("campaign_intent") or ""
        ),
        require_historic_plus_addition=_brief_requires_historic_plus_addition(original_brief),
    )
    drive_truth = _as_dict(_as_dict(ctx.get("drive_research")).get("architecture_truth"))
    if drive_truth.get("fail_closed") or pre_truth.get("fail_closed"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "Architectural Truth Lock FAIL CLOSED — approved exterior/architecture "
                    "source missing or untraceable. Fake architecture fallback FORBIDDEN."
                ),
                "architecture_truth_guard": pre_truth,
                "drive_architecture_truth": drive_truth or None,
            },
        )

    if production_mode in {"finished_ad", "editable_finished_ad"}:
        instruction = render_finished_ad_production_prompt(
            production_brief=production_brief,
            art_direction=art_direction.to_dict(),
            original_brief=original_brief,
            lifestyle=lifestyle,
        )
    else:
        instruction = render_gpt_image_art_direction_prompt(
            art_direction,
            texts=texts,
            interior_meta=interior_meta,
            logo_meta=logo_meta,
            original_brief=original_brief,
            aspect_ratio=aspect_ratio,
        )

    forced_verified: list[str] = []
    if not lifestyle and production_mode not in {"finished_ad", "editable_finished_ad"}:
        forced_verified = [texts["price_hierarchy"] + " · " + texts["value_badge"]]

    callouts = [x.strip() for x in str(texts.get("supporting_callouts") or "").split("|") if x.strip()]
    builder_context: dict[str, Any] = {
        "creative_director_campaign_id": str(row.id),
        "approved_financial_tokens": allowed_tokens,
        "preferred_logo_asset_id": str(logo_id),
        "interior_project_asset_lock": True,
        "campaign_mode": "lifestyle" if lifestyle else "launch_price",
        "art_direction_plan": art_direction.to_dict(),
        "production_brief": production_brief,
        "production_mode": production_mode,
        "image_provider_route": provider_route.to_dict(),
        "feature_callouts": callouts,
    }
    if production_mode in {"finished_ad", "editable_finished_ad"}:
        # Provider still produces a flat reference raster; editable mode hydrates layers separately.
        builder_context["finished_ad"] = True
        if production_mode == "editable_finished_ad":
            builder_context["editable_finished_ad"] = True
    else:
        builder_context.update(
            {
                "forced_visible_copy": {
                    "eyebrow": texts["eyebrow"],
                    "headline": texts["headline"],
                    "supporting": texts["supporting"],
                    "supporting_callouts": texts.get("supporting_callouts", ""),
                    "cta": texts["cta"],
                },
                "forced_verified_lines": forced_verified,
                "master_ad": True,
                "use_art_direction_prompt": True,
            }
        )

    gpt_body = GptImageDesignRequest(
        linked_project_id=row.linked_project_id,
        instruction=instruction,
        design_provider="gpt-image",
        campaign_mode="project",
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        language=language,
        selected_asset_ids=[interior_id],
        builder_context=builder_context,
    )

    result = generate_gpt_image_creatives(db, user, gpt_body)
    output = result.outputs[0] if result.outputs else None
    if output is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GPT Image returned no outputs for campaign ad generation.",
        )

    source_id = result.source_image.asset_id if result.source_image else None
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
        source_asset_id=source_id,
    )

    truth_guard = architecture_truth_guard(
        hero_meta=interior_meta,
        source_asset_id=str(source_id) if source_id else None,
        campaign_intent=str(
            ctx.get("campaign_intent") or production_brief.get("campaign_intent") or ""
        ),
        require_historic_plus_addition=_brief_requires_historic_plus_addition(original_brief),
    )
    if truth_guard.get("fail_closed"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "Architectural Truth Lock FAIL CLOSED — cannot establish project "
                    "architecture fidelity. Fake architecture will not be published."
                ),
                "architecture_truth_guard": truth_guard,
            },
        )
    asset_lock["architecture_truth_guard"] = truth_guard
    production_brief = dict(production_brief)
    production_brief["architecture_truth_guard"] = truth_guard

    output_meta = output.metadata if isinstance(getattr(output, "metadata", None), dict) else {}
    duplication_guard = dict(output_meta.get("duplication_guard") or {})
    layer_texts = [
        str(el.get("content") or el.get("label") or "")
        for el in (output.layers or [])
        if isinstance(el, dict)
    ]
    duplication_guard["internal_leak_count"] = count_internal_leaks(*layer_texts)

    creative_brief_summary = {
        "big_idea": campaign_copy.get("big_idea") or strategy.get("big_idea"),
        "hero": campaign_copy.get("hero_message") or strategy.get("hero_message"),
        "sales_hook": campaign_copy.get("sales_hook") or strategy.get("sales_hook"),
        "offer": campaign_copy.get("offer") or _as_dict(pricing.get("price_presentation")).get("copy"),
        "price_hierarchy": texts["price_hierarchy"],
        "value": texts["value_badge"],
        "emphasis": campaign_copy.get("emphasis") or strategy.get("emphasis"),
        "supporting": campaign_copy.get("supporting_messages") or strategy.get("supporting_messages"),
        "cta": texts["cta"],
        "tone": strategy.get("tone"),
        "visual_direction": strategy.get("visual_direction"),
        "composition_direction": strategy.get("composition_direction"),
        "composition_family": output_meta.get("composition_type"),
        "art_direction": art_direction.to_dict(),
        "source_constraints": {
            "interior_asset_id": str(interior_id),
            "interior_filename": interior_meta.get("filename"),
            "logo_asset_id": str(logo_id),
            "logo_filename": logo_meta.get("filename"),
        },
        "brand": "The Temple + Investhome",
        "language": language,
        "format": f"Instagram {aspect_ratio}",
        "prompt_excerpt": (result.brief or {}).get("prompt")
        or (result.brief or {}).get("user_instruction")
        or instruction[:1200],
    }

    ctx = dict(row.context_json or {})
    generated = list(ctx.get("generated_assets") or [])
    generated.append(
        {
            "asset_id": str(output.local_asset_id),
            "role": "master_instagram_4_5",
            "language": language,
            "provider": result.provider,
            "composition_base_asset_id": str(output.composition_base_asset_id)
            if output.composition_base_asset_id
            else None,
        }
    )
    history = list(ctx.get("output_history") or [])
    history.append(
        {
            "type": "generate_ad",
            "asset_id": str(output.local_asset_id),
            "language": language,
            "format": aspect_ratio,
            "claim_guard": claim_guard.get("status"),
            "project_asset_lock": asset_lock.get("status"),
        }
    )
    ctx["generated_assets"] = generated
    ctx["output_history"] = history
    ctx["image_generation_performed"] = True
    ctx["latest_master_ad_asset_id"] = str(output.local_asset_id)
    # Immutable revision master: first approved finished-ad only (never overwrite).
    if production_mode in {"finished_ad", "editable_finished_ad"} and not ctx.get("master_asset_id"):
        ctx["master_asset_id"] = str(output.local_asset_id)
        ctx["master_finished_ad_asset_id"] = str(output.local_asset_id)
        ctx["revision_operations"] = []
        ctx["current_revision_index"] = 0
    elif production_mode in {"finished_ad", "editable_finished_ad"} and not ctx.get(
        "master_finished_ad_asset_id"
    ):
        # Align alias when master already set from prior path
        ctx["master_finished_ad_asset_id"] = str(ctx.get("master_asset_id") or output.local_asset_id)

    design_spec: dict[str, Any] | None = None
    editable_layers: list[dict[str, Any]] = []
    master_background_id: UUID | None = None
    finished_raster_id: UUID | None = None
    quality_guard: dict[str, Any] = {
        "status": "review",
        "mode": production_mode,
        "checks": {},
        "failures": [],
        "note": "User visual approval required — do not declare Visual Quality PASS.",
    }

    if production_mode == "finished_ad":
        # Golden hybrid default: single finished-ad raster is the client deliverable.
        # Keep a Design Spec in campaign context so LAYER_ONLY revision can mutate
        # copy without reconstructing a new creative or swapping the photograph.
        finished_raster_id = output.local_asset_id
        ctx["production_mode"] = "finished_ad"
        ctx["editable_finished_ad"] = False
        ctx["finished_ad_raster_asset_id"] = str(finished_raster_id)
        ctx["master_background_asset_id"] = str(interior_id)
        try:
            spec_texts, spec_brief = hydrate_supporting_copy(
                texts=texts,
                production_brief=production_brief,
                campaign_copy=campaign_copy,
                strategy=strategy,
                ctx=ctx,
            )
            assembled = assemble_editable_design(
                production_brief=spec_brief,
                texts=spec_texts,
                master_background_asset_id=interior_id,
                logo_asset_id=logo_id,
                finished_ad_raster_asset_id=finished_raster_id,
                aspect_ratio=aspect_ratio,
                format_preset=format_preset,
                language=language,
                campaign_intent=str(spec_brief.get("campaign_intent") or production_brief.get("campaign_intent") or ""),
            )
            spec = assembled.get("design_spec") if isinstance(assembled.get("design_spec"), dict) else {}
            spec = ensure_revision_overlay_targets(
                spec,
                production_brief=spec_brief,
                texts=spec_texts,
            )
            spec = stamp_editable_text_targets(spec)
            ctx["design_spec"] = spec
            ctx["composition_plan"] = assembled.get("composition_plan")
            if spec.get("editable_text_targets"):
                ctx["editable_text_targets"] = spec["editable_text_targets"]
            if spec_texts.get("supporting_callouts"):
                ctx["supporting_callouts"] = spec_texts["supporting_callouts"]
        except Exception:
            logger.exception("finished_ad design_spec persist failed campaign=%s", row.id)
        quality_guard = _finished_ad_quality_guard(
            claim_guard=claim_guard,
            asset_lock=asset_lock,
            texts=texts,
            production_brief=production_brief,
            language=language,
            architecture_truth=truth_guard,
        )
        ctx["latest_quality_guard"] = quality_guard

    if production_mode == "editable_finished_ad":
        master_background_id = interior_id
        finished_raster_id = output.local_asset_id
        spec_texts, spec_brief = hydrate_supporting_copy(
            texts=texts,
            production_brief=production_brief,
            campaign_copy=campaign_copy,
            strategy=strategy,
            ctx=ctx,
        )
        assembled = assemble_editable_design(
            production_brief=spec_brief,
            texts=spec_texts,
            master_background_asset_id=master_background_id,
            logo_asset_id=logo_id,
            finished_ad_raster_asset_id=finished_raster_id,
            aspect_ratio=aspect_ratio,
            format_preset=format_preset,
            language=language,
            campaign_intent=str(spec_brief.get("campaign_intent") or production_brief.get("campaign_intent") or ""),
        )
        design_spec = assembled["design_spec"]
        design_spec = ensure_revision_overlay_targets(
            design_spec if isinstance(design_spec, dict) else {},
            production_brief=spec_brief,
            texts=spec_texts,
        )
        design_spec = stamp_editable_text_targets(design_spec)
        editable_layers = assembled["editable_layers"]
        ctx["design_spec"] = design_spec
        ctx["composition_plan"] = assembled.get("composition_plan")
        if isinstance(design_spec, dict) and design_spec.get("editable_text_targets"):
            ctx["editable_text_targets"] = design_spec["editable_text_targets"]
        if spec_texts.get("supporting_callouts"):
            ctx["supporting_callouts"] = spec_texts["supporting_callouts"]
        ctx["quality_critique"] = assembled.get("quality_critique")
        ctx["geometry_check"] = assembled.get("geometry_check")
        ctx["master_background_asset_id"] = str(master_background_id)
        ctx["finished_ad_raster_asset_id"] = str(finished_raster_id)
        ctx["editable_finished_ad"] = True
        ctx["production_mode"] = "editable_finished_ad"
        critique = assembled.get("quality_critique") or {}
        quality_guard = {
            "status": critique.get("status") or "review",
            "mode": "editable_finished_ad",
            "checks": critique.get("checks") or {},
            "failures": critique.get("issues") or [],
            "note": "Legacy editable path — not production default.",
        }
        ctx["latest_quality_guard"] = quality_guard

    ctx["language"] = language
    row.context_json = ctx
    if row.status == "draft":
        row.status = "ready"
    db.flush()

    master_id_out: UUID | None = None
    raw_master = ctx.get("master_finished_ad_asset_id") or ctx.get("master_asset_id")
    if raw_master:
        try:
            master_id_out = UUID(str(raw_master))
        except (TypeError, ValueError):
            master_id_out = None

    return CreativeDirectorGenerateAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        production_mode=production_mode,  # type: ignore[arg-type]
        production_brief=production_brief,
        provider_route=provider_route.to_dict(),
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=output.local_asset_id,
        final_asset_url=output.local_asset_url,
        composition_base_asset_id=(
            master_background_id if production_mode == "editable_finished_ad" else output.composition_base_asset_id
        ),
        creative_brief_summary=creative_brief_summary,
        final_turkish_texts=texts,
        claim_guard=claim_guard,
        project_asset_lock=asset_lock,
        architecture_truth_guard=truth_guard,
        duplication_guard=duplication_guard,
        provider_call_count=result.provider_call_count,
        gpt_image_call_count=result.provider_call_count,
        latency_ms=result.latency_ms,
        warnings=list(result.warnings or []),
        gpt_image=result.model_dump(mode="json"),
        design_spec=design_spec,
        master_background_asset_id=master_background_id,
        finished_ad_raster_asset_id=finished_raster_id,
        editable_layers=editable_layers,
        master_asset_id=master_id_out,
        master_finished_ad_asset_id=master_id_out,
        quality_guard=quality_guard,
    )
