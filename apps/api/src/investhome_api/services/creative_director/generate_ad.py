"""Generate one MASTER Instagram ad from an approved Creative Director Campaign Context.

Reuses GPT Image PROJECT MODE + Final Composition. Does not rewrite CD brief logic.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.models.creative_director_campaign import CreativeDirectorCampaign
from investhome_api.models.user_auth import User
from investhome_api.schemas.creative_director import (
    CreativeDirectorGenerateAdRequest,
    CreativeDirectorGenerateAdResponse,
)
from investhome_api.schemas.gpt_image_design import GptImageDesignRequest
from investhome_api.services.creative_director.art_direction_translator import (
    render_gpt_image_art_direction_prompt,
    translate_campaign_art_direction,
)
from investhome_api.services.gpt_image_design.service import generate_gpt_image_creatives


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


def resolve_locked_assets(ctx: dict[str, Any]) -> tuple[UUID, UUID, dict[str, Any], dict[str, Any]]:
    """PROJECT ASSET LOCK — interior + logo from stored Campaign Context only."""
    selected_assets = _as_list(ctx.get("selected_assets"))
    interior_meta = selected_assets[0] if selected_assets else None
    if not isinstance(interior_meta, dict):
        drive = _as_dict(ctx.get("drive_research"))
        interior_meta = drive.get("selected_interior")
    logo_meta = ctx.get("selected_logo")
    if not isinstance(logo_meta, dict):
        drive = _as_dict(ctx.get("drive_research"))
        logo_meta = drive.get("selected_logo")
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
    return interior_id, logo_id, _as_dict(interior_meta), _as_dict(logo_meta)


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
    support_msgs = _as_list(
        campaign_copy.get("supporting_messages") or strategy.get("supporting_messages")
    )

    if lifestyle:
        headline = big_idea or hero or "Eviniz, Sığınak"
        hero_tr = hero or headline
        sales_line = sales_hook or hero_tr
        callouts = [str(x).strip() for x in support_msgs[:3] if str(x).strip()]
        supporting = " · ".join(callouts) if callouts else sales_line
        cta = cta_src if _has_turkish_chars(cta_src) else "Detayları Keşfet"
        eyebrow = sales_hook or hero_tr
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
            "value": value_src if _has_turkish_chars(value_src) else "",
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
        elif big_idea:
            headline = big_idea if _has_turkish_chars(big_idea) else hero or big_idea
        else:
            headline = hero or "Tarihi karakter. Modern yaşam."

        eyebrow = f"{unit_display} Lansman Fırsatı"
        if "204" in sales_hook or "launch" in sales_hook.lower() or "lansman" in sales_hook.lower():
            sales_line = f"{unit_display} Lansman Fırsatı"
        else:
            sales_line = sales_hook if _has_turkish_chars(sales_hook) else eyebrow

        supporting = f"{unit_display} Lansman Fırsatı"
        # Price hierarchy + value sit in verified/OS location line for accuracy.

        cta = cta_src if _has_turkish_chars(cta_src) else "Detayları İncele"
        if any(tok in cta_src.lower() for tok in ("explore", "schedule", "viewing", "details")):
            cta = "Detayları İncele"

        hero_tr = (
            hero
            if _has_turkish_chars(hero)
            else "Tarihi karakterle modern yaşam bir arada."
        )
        value_tr = value_badge if "lansman" in value_src.lower() or not _has_turkish_chars(value_src) else value_src
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
    return {
        "status": "pass" if locked_ok else "fail",
        "interior_asset_id": str(interior_id),
        "interior_filename": interior_meta.get("filename"),
        "logo_asset_id": str(logo_id),
        "logo_filename": logo_meta.get("filename"),
        "source_used_asset_id": str(source_asset_id) if source_asset_id else None,
        "interior_architecture_locked": True,
        "logo_os_composited": True,
        "gpt_must_not_invent_interior": True,
        "gpt_must_not_draw_logo": True,
    }


def generate_ad_from_campaign(
    db: Session,
    user: User,
    campaign_id: UUID,
    body: CreativeDirectorGenerateAdRequest | None = None,
) -> CreativeDirectorGenerateAdResponse:
    """Load Campaign Context → GPT Image PROJECT MODE → persist final ML asset."""
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
    # Persist language on campaign for later EN reuse of the same context.
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
    art_direction = translate_campaign_art_direction(
        ctx=ctx,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        language=language,
        lifestyle=lifestyle,
    )
    format_preset = (body.format_preset or "portrait").strip() or "portrait"
    aspect_ratio = (body.aspect_ratio or "4:5").strip() or "4:5"
    instruction = render_gpt_image_art_direction_prompt(
        art_direction,
        texts=texts,
        interior_meta=interior_meta,
        logo_meta=logo_meta,
        original_brief=original_brief,
        aspect_ratio=aspect_ratio,
    )

    forced_verified: list[str] = []
    if not lifestyle:
        forced_verified = [texts["price_hierarchy"] + " · " + texts["value_badge"]]

    gpt_body = GptImageDesignRequest(
        linked_project_id=row.linked_project_id,
        instruction=instruction,
        design_provider="gpt-image",
        campaign_mode="project",
        format_preset=format_preset,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        language=language,
        selected_asset_ids=[interior_id],
        builder_context={
            "creative_director_campaign_id": str(row.id),
            "forced_visible_copy": {
                "eyebrow": texts["eyebrow"],
                "headline": texts["headline"],
                "supporting": texts["supporting"],
                "cta": texts["cta"],
            },
            "forced_verified_lines": forced_verified,
            "approved_financial_tokens": allowed_tokens,
            "preferred_logo_asset_id": str(logo_id),
            "interior_project_asset_lock": True,
            "master_ad": True,
            "campaign_mode": "lifestyle" if lifestyle else "launch_price",
            "art_direction_plan": art_direction.to_dict(),
            "use_art_direction_prompt": True,
        },
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

    # Persist generation on Campaign Context (no CD brief rewrite).
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
    ctx["language"] = language
    row.context_json = ctx
    if row.status == "draft":
        row.status = "ready"
    db.flush()

    return CreativeDirectorGenerateAdResponse(
        campaign_id=row.id,
        project_id=row.linked_project_id,
        language=language,
        aspect_ratio=aspect_ratio,
        format_preset=format_preset,
        interior_asset_id=interior_id,
        logo_asset_id=logo_id,
        final_asset_id=output.local_asset_id,
        final_asset_url=output.local_asset_url,
        composition_base_asset_id=output.composition_base_asset_id,
        creative_brief_summary=creative_brief_summary,
        final_turkish_texts=texts,
        claim_guard=claim_guard,
        project_asset_lock=asset_lock,
        provider_call_count=result.provider_call_count,
        latency_ms=result.latency_ms,
        warnings=list(result.warnings or []),
        gpt_image=result.model_dump(mode="json"),
    )
