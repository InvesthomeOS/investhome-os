"""Creative self-critique — one fix pass on Production Brief before finished-ad provider."""

from __future__ import annotations

from typing import Any

from investhome_api.services.creative_director.production_brief import (
    looks_english_ad_copy,
    lock_copy_to_language,
    lock_supporting_messages,
)
from investhome_api.services.creative_director.quality_lock.simplicity import (
    simplicity_caps_for_intent,
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _s(value: Any) -> str:
    return str(value or "").strip()


def critique_production_brief(
    production_brief: dict[str, Any],
    *,
    campaign_intent: str | None = None,
    recent_asset_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Return critique findings. Does not mutate the brief."""
    brief = production_brief or {}
    intent = str(campaign_intent or brief.get("campaign_intent") or "").strip().lower()
    lang = str(brief.get("language") or "tr").strip().lower() or "tr"
    issues: list[str] = []
    checks: dict[str, bool] = {}

    primary = _s(brief.get("hero") or brief.get("big_idea") or _as_dict(brief.get("final_copy")).get("headline"))
    checks["two_second_clarity"] = bool(primary) and len(primary) <= 80
    if not checks["two_second_clarity"]:
        issues.append("primary_message_unclear_or_too_long")

    supporting = [str(x).strip() for x in _as_list(brief.get("supporting")) if str(x).strip()]
    caps = simplicity_caps_for_intent(intent)
    checks["one_dominant_message"] = bool(primary) and len(supporting) <= caps.max_supporting
    if len(supporting) > caps.max_supporting:
        issues.append("excess_supporting_messages")

    asset_lock = _as_dict(brief.get("asset_lock"))
    selected = _as_list(brief.get("selected_assets"))
    hero_id = _s(asset_lock.get("interior_asset_id") or (selected[0].get("asset_id") if selected and isinstance(selected[0], dict) else ""))
    checks["asset_present"] = bool(hero_id)
    if not hero_id:
        issues.append("missing_locked_asset")

    recent = {str(x) for x in (recent_asset_ids or []) if str(x).strip()}
    checks["not_blind_repeat"] = not (hero_id and hero_id in recent and len(recent) >= 1)
    # Blind repeat is a soft warning — still allowed if truly best; flag for report.
    if hero_id and hero_id in recent:
        issues.append("asset_matches_recent_selection")

    final = _as_dict(brief.get("final_copy"))
    cta = _s(brief.get("cta") or final.get("cta"))
    checks["cta_present"] = bool(cta)
    if not cta:
        issues.append("missing_cta")

    logo_ok = bool(asset_lock.get("logo_asset_id") or _as_dict(brief.get("logo_lock")).get("logo_asset_id"))
    checks["logo_locked"] = logo_ok
    if not logo_ok:
        issues.append("missing_logo_lock")

    user_facing = " ".join(
        [
            primary,
            _s(brief.get("sales_hook")),
            cta,
            " ".join(supporting),
            _s(final.get("headline")),
            _s(final.get("supporting")),
        ]
    )
    if lang.startswith("tr"):
        english_leak = looks_english_ad_copy(primary) or looks_english_ad_copy(cta) or any(
            looks_english_ad_copy(m) for m in supporting
        )
        checks["language_ok"] = not english_leak
        if english_leak:
            issues.append("english_leak_in_turkish_campaign")
    else:
        checks["language_ok"] = True

    approved = _as_list(brief.get("approved_claims"))
    forbidden = _as_list(brief.get("forbidden_claims"))
    checks["claims_present_or_lifestyle"] = bool(approved) or intent in {
        "lifestyle",
        "amenities",
        "location",
        "architecture",
        "general_awareness",
        "project_brand",
        "educational",
    }
    blob = user_facing.lower()
    invented_finance = any(tok in blob for tok in ("roi", "irr", "yield", "guaranteed profit"))
    checks["no_invented_finance_language"] = not invented_finance
    if invented_finance:
        issues.append("invented_finance_language")

    design = _as_dict(brief.get("design_direction"))
    checks["premium_direction"] = bool(design.get("premium_level") or brief.get("visual_direction") or design.get("visual_mood"))
    if not checks["premium_direction"]:
        issues.append("weak_design_direction")

    checks["similarity_noted"] = "asset_matches_recent_selection" not in issues or True

    status = "pass" if not any(
        k in issues
        for k in (
            "primary_message_unclear_or_too_long",
            "excess_supporting_messages",
            "missing_locked_asset",
            "missing_cta",
            "missing_logo_lock",
            "english_leak_in_turkish_campaign",
            "invented_finance_language",
        )
    ) else "needs_fix"

    return {
        "status": status,
        "checks": checks,
        "issues": issues,
        "forbidden_claim_count": len(forbidden),
        "campaign_intent": intent,
    }


def apply_critique_fixes(
    production_brief: dict[str, Any],
    critique: dict[str, Any],
) -> dict[str, Any]:
    """One-pass deterministic fixes for common critique failures."""
    brief = dict(production_brief or {})
    issues = set(critique.get("issues") or [])
    intent = str(brief.get("campaign_intent") or critique.get("campaign_intent") or "")
    lang = str(brief.get("language") or "tr")
    caps = simplicity_caps_for_intent(intent)
    final = dict(_as_dict(brief.get("final_copy")))

    if "excess_supporting_messages" in issues:
        supporting = lock_supporting_messages(
            _as_list(brief.get("supporting")),
            language=lang,
            max_items=caps.max_supporting,
        )
        brief["supporting"] = supporting
        if supporting:
            final["supporting"] = " | ".join(supporting)
        else:
            final["supporting"] = ""

    if "english_leak_in_turkish_campaign" in issues and lang.lower().startswith("tr"):
        for key in ("big_idea", "hero", "sales_hook", "offer", "cta"):
            brief[key] = lock_copy_to_language(
                _s(brief.get(key)),
                language=lang,
                fallback=_s(final.get("headline") if key in {"big_idea", "hero"} else final.get(key) or ""),
            )
        brief["supporting"] = lock_supporting_messages(
            _as_list(brief.get("supporting")),
            language=lang,
            max_items=caps.max_supporting,
        )
        for fk in ("eyebrow", "headline", "supporting", "cta"):
            final[fk] = lock_copy_to_language(final.get(fk), language=lang, fallback=_s(final.get(fk)))
        if looks_english_ad_copy(final.get("cta")) or not _s(final.get("cta")):
            final["cta"] = "Detayları İncele"
            brief["cta"] = "Detayları İncele"

    if "missing_cta" in issues:
        fallback_cta = "Detayları İncele" if lang.lower().startswith("tr") else "Explore details"
        brief["cta"] = fallback_cta
        final["cta"] = fallback_cta

    if "primary_message_unclear_or_too_long" in issues:
        primary = _s(brief.get("hero") or brief.get("big_idea") or final.get("headline"))
        if len(primary) > 80:
            primary = primary[:77].rstrip() + "…"
        if primary:
            brief["hero"] = primary
            final["headline"] = primary

    if "invented_finance_language" in issues:
        for key in ("big_idea", "hero", "sales_hook", "offer"):
            val = _s(brief.get(key))
            for tok in ("ROI", "IRR", "yield", "Yield", "guaranteed profit", "Guaranteed profit"):
                val = val.replace(tok, "")
            brief[key] = " ".join(val.split()).strip(" -|,")

    brief["final_copy"] = final
    simplicity = _as_dict(brief.get("simplicity_director"))
    simplicity["max_supporting"] = caps.max_supporting
    simplicity["applied_after_critique"] = True
    brief["simplicity_director"] = simplicity
    brief["max_supporting_messages"] = caps.max_supporting
    return brief


def critique_and_fix_production_brief(
    production_brief: dict[str, Any],
    *,
    campaign_intent: str | None = None,
    recent_asset_ids: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Critique once; if needs_fix, apply one fix pass and re-check."""
    critique = critique_production_brief(
        production_brief,
        campaign_intent=campaign_intent,
        recent_asset_ids=recent_asset_ids,
    )
    brief = production_brief
    if critique.get("status") == "needs_fix":
        brief = apply_critique_fixes(production_brief, critique)
        critique_after = critique_production_brief(
            brief,
            campaign_intent=campaign_intent,
            recent_asset_ids=recent_asset_ids,
        )
        critique = {
            **critique_after,
            "fixed_once": True,
            "pre_fix_issues": critique.get("issues") or [],
            "post_fix_issues": critique_after.get("issues") or [],
        }
    else:
        critique = {**critique, "fixed_once": False}
    brief = dict(brief)
    brief["self_critique"] = critique
    return brief, critique
