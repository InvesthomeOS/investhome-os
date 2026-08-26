"""Creative Generation Engine v1 — short natural-language brief → production intent.

Does not invent commercial facts. Does not change SMB UI, revision, or Native Renderer.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


_PROJECT_ALIASES = (
    "the temple",
    "temple",
    "tapinak",
    "tapınak",
)
_BRAND_ALIASES = (
    "investhome",
    "invest home",
    "sirket marka",
    "sirket reklam",
    "marka reklam",
    "brand ad",
)
_INTERIOR_TOKENS = (
    "interior",
    "ic mekan",
    "ic mekân",
    "living",
    "oturma",
    "daire ici",
    "suite",
)
_EXTERIOR_TOKENS = (
    "dis cephe",
    "dış cephe",
    "exterior",
    "facade",
    "cephe",
    "bina disi",
    "bina dışı",
)
_CITY_TOKENS = (
    "washington",
    "washington dc",
    "sehir",
    "şehir",
    "cityscape",
    "skyline",
    "mahalle",
    "neighborhood",
)
_INVESTMENT_TOKENS = (
    "yatirim",
    "yatırım",
    "investment",
    "investor",
    "yatirimci",
    "yatırımcı",
)
_PRICE_TOKENS = (
    "fiyat",
    "indirim",
    "lansman fiyat",
    "discount",
    "$",
    "kampanya fiyat",
)


def detect_output_format(brief: str) -> dict[str, Any]:
    """Map spoken format to SMB preset. Unspecified → caller keeps SMB default."""
    t = _norm(brief)
    if any(k in t for k in ("reel cover", "reels cover", "reels kapak", "reel kapak")):
        return {
            "specified": True,
            "format_preset": "reelsCover",
            "aspect_ratio": "9:16",
            "label": "Reel cover",
        }
    if any(k in t for k in ("instagram story", "ig story", "hikaye")):
        return {
            "specified": True,
            "format_preset": "story",
            "aspect_ratio": "9:16",
            "label": "Story",
        }
    if any(k in t for k in ("kare", "square", "1:1", "1/1")):
        return {
            "specified": True,
            "format_preset": "square",
            "aspect_ratio": "1:1",
            "label": "Square",
        }
    if any(
        k in t
        for k in (
            "instagram post",
            "instagram postu",
            "ig post",
            "feed post",
            "4:5",
            "4/5",
        )
    ):
        return {
            "specified": True,
            "format_preset": "portrait",
            "aspect_ratio": "4:5",
            "label": "Instagram Post",
        }
    return {
        "specified": False,
        "format_preset": None,
        "aspect_ratio": None,
        "label": None,
    }


def _visual_kind(t: str) -> str:
    if any(k in t for k in _INTERIOR_TOKENS) and not any(k in t for k in _EXTERIOR_TOKENS):
        return "interior"
    if any(k in t for k in _EXTERIOR_TOKENS) and not any(k in t for k in _INTERIOR_TOKENS):
        return "exterior"
    if any(k in t for k in _CITY_TOKENS):
        return "city"
    return "unspecified"


def _extract_cta(brief: str) -> str | None:
    match = re.search(r"(?:cta|cagri|çağrı)\s*[:\-]\s*(.+)$", brief or "", re.I | re.M)
    if match:
        return match.group(1).strip().split("\n")[0][:80] or None
    return None


def classify_ad_scope(
    brief: str,
    *,
    project_name: str | None = None,
) -> str:
    """project = named project ad. brand = Investhome / city-market ad. Never invent a project."""
    t = _norm(brief)
    pname = _norm(project_name or "")
    named_project = any(alias in t for alias in _PROJECT_ALIASES)
    if pname and len(pname) >= 4 and pname in t:
        named_project = True
    if named_project:
        return "project"
    if any(alias in t for alias in _BRAND_ALIASES):
        return "brand"
    city_market = any(k in t for k in ("washington", "dc'de", "dc de", "washington dc"))
    investment = any(k in t for k in _INVESTMENT_TOKENS)
    audience_tr = any(
        k in t
        for k in (
            "turkiye",
            "türkiye",
            "turkiyedeki",
            "türkiyedeki",
            "turk yatirim",
            "türk yatirim",
        )
    )
    if city_market and (investment or audience_tr) and not named_project:
        return "brand"
    return "project"


def interpret_short_user_brief(
    brief: str,
    *,
    project_name: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    """Turn a short Turkish command into production intent. Does not invent prices/ROI."""
    raw = (brief or "").strip()
    t = _norm(raw)
    fmt = detect_output_format(raw)
    scope = classify_ad_scope(raw, project_name=project_name)
    visual_kind = _visual_kind(t)
    investment = any(k in t for k in _INVESTMENT_TOKENS)
    price_mentioned = any(k in t for k in _PRICE_TOKENS) or bool(re.search(r"\$\s*\d", raw))
    american_colors = any(
        k in t for k in ("amerikan renk", "american color", "amerikan palet", "us color")
    )
    audience = None
    if any(k in t for k in ("turkiye", "türkiye", "turkiyedeki", "türkiyedeki")):
        audience = "Türkiye'deki yatırımcılar" if investment else "Türkiye'deki alıcılar"
    purpose = "investment_awareness" if investment else "general_awareness"
    if scope == "brand" and investment:
        purpose = "brand_investment"
    cta = _extract_cta(raw)
    invented: list[str] = []
    required_facts: list[str] = []
    if price_mentioned:
        required_facts.append("only_user_supplied_price")
    else:
        invented.append("no_price_invented")
    invented.append("no_roi_invented")

    forbidden = [
        "invent_logo",
        "invent_roi",
        "invent_price",
        "fake_brand_mark",
    ]
    if scope == "brand":
        forbidden.extend(["project_render_as_hero", "the_temple_as_product"])
        required_assets = ["approved_investhome_logo", "washington_dc_or_city_visual"]
        logo_role = "investhome_logo"
    else:
        required_assets = ["approved_project_logo", "approved_project_photograph"]
        logo_role = "project_logo"
        if visual_kind == "interior":
            forbidden.append("exterior_as_hero")
            required_assets.append("project_interior")
        if visual_kind == "exterior":
            forbidden.append("interior_as_hero")
            required_assets.append("project_exterior")

    return {
        "user_brief": raw,
        "ad_scope": scope,
        "purpose": purpose,
        "campaign_intent_hint": "investment" if investment else None,
        "audience": audience,
        "primary_message": None,
        "campaign": None,
        "price_mentioned": price_mentioned,
        "investment_message": investment,
        "visual_kind": visual_kind,
        "format": fmt,
        "cta": cta,
        "color_direction": (
            "Amerikan paleti: navy, cream, restrained red accent — luxury editorial, not a flag collage"
            if american_colors
            else None
        ),
        "american_colors": american_colors,
        "place": "Washington DC" if "washington" in t else None,
        "language": (language or "tr").strip().lower() or "tr",
        "logo_role": logo_role,
        "required_assets": required_assets,
        "required_facts": required_facts,
        "forbidden_changes": forbidden,
        "invented_facts_blocked": invented,
        "native_renderer_primary": False,
        "production_mode": "finished_ad",
    }


def generation_engine_for_context(parsed: dict[str, Any]) -> dict[str, Any]:
    fmt = parsed.get("format") if isinstance(parsed.get("format"), dict) else {}
    return {
        "version": 1,
        "ad_scope": parsed.get("ad_scope"),
        "purpose": parsed.get("purpose"),
        "visual_kind": parsed.get("visual_kind"),
        "audience": parsed.get("audience"),
        "place": parsed.get("place"),
        "logo_role": parsed.get("logo_role"),
        "format_specified": bool(fmt.get("specified")),
        "format_preset": fmt.get("format_preset"),
        "aspect_ratio": fmt.get("aspect_ratio"),
        "format_label": fmt.get("label"),
        "color_direction": parsed.get("color_direction"),
        "cta": parsed.get("cta"),
        "required_assets": parsed.get("required_assets") or [],
        "required_facts": parsed.get("required_facts") or [],
        "forbidden_changes": parsed.get("forbidden_changes") or [],
        "invented_facts_blocked": parsed.get("invented_facts_blocked") or [],
        "production_mode": "finished_ad",
        "native_renderer_primary": False,
    }
