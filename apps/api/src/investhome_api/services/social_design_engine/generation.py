"""AI-first complete social post generation.

Generation path (create mode): intent → campaign facts → RAG-grounded copy →
semantic asset pick → design plan → Design Ops composer → layout.

Edit path stays in intent.py. This module never invents project facts and
never writes RAG/debug metadata into canvas copy.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.services.social_design_engine.layout import social_layout_slots
from investhome_api.services.social_design_engine.ops import (
    FORMAT_PRESETS,
    looks_like_rag_or_debug_copy,
    sanitize_creative_copy,
)

MarketingObjective = Literal[
    "location",
    "investment",
    "lifestyle",
    "launch",
    "project_introduction",
    "architecture",
    "interior",
    "floor_plan",
    "general",
]
AssetPreference = Literal[
    "exterior",
    "neighborhood",
    "aerial",
    "interior",
    "premium_hero",
    "floor_plan",
    "any",
]
DesignMode = Literal["create", "edit"]

CONTENT_PACKAGE_MARKER = "CONTENT_PACKAGE_JSON"

GENERATION_VERBS = (
    "hazırla",
    "hazirla",
    "oluştur",
    "olustur",
    "oluşturun",
    "create a",
    "create an",
    "create the",
    "generate a",
    "generate an",
    "prepare a",
    "prepare an",
    "postu hazırla",
    "post hazırla",
    "post oluştur",
    "post olustur",
    "complete post",
    "yeni post",
    "new post",
    "kare post",
    "instagram post",
    "feed post",
    "tasarla",
)

COMPLETE_POST_MARKERS = (
    "post",
    "instagram",
    "kare",
    "feed",
    "story",
    "gönderi",
    "gonderi",
    "kreatif",
    "creative",
)

# Surgical edits — win over incidental words like "premium" / "görsel".
EDIT_VERBS = (
    "taşı",
    "tasi",
    "yukarı al",
    "yukari al",
    "aşağı al",
    "asagi al",
    "sola al",
    "sağa al",
    "saga al",
    "kaldır",
    "kaldir",
    "remove the",
    "delete the",
    "küçült",
    "kucult",
    "büyüt",
    "buyut",
    "rengini",
    "rengini",
    "başlığı biraz",
    "basligi biraz",
    "cta'yı kaldır",
    "cta'yi kaldir",
    "cta’yı kaldır",
    "move the",
    "shift the",
    "nudge",
    "başlığı daha güçlü",
    "basligi daha guclu",
    "adres bilgisini",
    "daha kurumsal",
    "rakamları alt alta",
    "rakamlari alt alta",
    "rakamları kart",
    "rakamlari kart",
    "getiriyi öne",
    "getiriyi one",
    "daha küçük göster",
    "daha kucuk goster",
)

REPLACE_IMAGE_EDIT = (
    "başka bir",
    "baska bir",
    "another photo",
    "another image",
    "another temple photo",
    "another temple",
    "farklı foto",
    "farkli foto",
    "different photo",
    "replace the image",
    "replace image",
)


@dataclass
class CampaignFact:
    """User-supplied campaign value — authoritative, never rewritten."""

    label: str
    display: str
    kind: str  # money | percent | duration | other
    source: Literal["user_supplied"] = "user_supplied"


@dataclass
class GenerationIntent:
    project_hint: str | None = None
    platform: str = "instagram"
    format_preset: str = "square"
    language: str = "en"
    marketing_objective: MarketingObjective = "general"
    audience: str = "general"
    tone: str = "premium"
    key_message: str = ""
    requested_facts: list[str] = field(default_factory=list)
    requested_financial_figures: list[str] = field(default_factory=list)
    cta_hint: str | None = None
    asset_preference: AssetPreference = "any"


@dataclass
class ContentPackage:
    headline: str
    supporting_text: str
    key_fact: str
    cta: str
    language: str
    tone: str
    eyebrow: str = ""


@dataclass
class DesignPlanElement:
    type: str  # TEXT | BUTTON | METRIC_GROUP
    role: str  # headline | body | cta | eyebrow | metric_group
    text: str
    x: int
    y: int
    width: int
    height: int
    font_size: int | None = None
    font_weight: str | None = None
    align: str = "center"
    color: str = "#ffffff"
    background_color: str | None = None
    text_color: str | None = None
    z_index: int = 2
    metrics: list[dict[str, Any]] | None = None
    metric_layout: str | None = None


@dataclass
class DesignPlan:
    format_preset: str
    platform: str
    background_asset_id: str | None
    overlay: str
    post_id: str
    rebuild: bool
    elements: list[DesignPlanElement] = field(default_factory=list)
    name: str = "AI social post"
    composition_strategy: str = "LOCATION"
    alignment: str = "left"
    overlay_region: str = "top"
    text_density: str = "sparse"
    safe_text_zone: str = "top"


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return folded.strip().lower()


def is_complete_post_generation(instruction: str) -> bool:
    t = _norm(instruction)
    has_verb = any(v in t for v in GENERATION_VERBS)
    has_post = any(m in t for m in COMPLETE_POST_MARKERS)
    if has_verb and has_post:
        return True
    if any(
        p in t
        for p in (
            "postu hazırla",
            "post hazırla",
            "instagram kare",
            "instagram post",
            "create a premium",
            "prepare a premium",
        )
    ):
        return True
    return False


def is_surgical_edit(instruction: str) -> bool:
    t = _norm(instruction)
    if any(v in t for v in EDIT_VERBS):
        return True
    if any(v in t for v in REPLACE_IMAGE_EDIT) and any(
        k in t for k in ("foto", "photo", "görsel", "gorsel", "image", "render")
    ):
        return True
    if re.search(r"\b(cta|buton|button|başlık|baslik|headline)\b.{0,24}\b(kaldır|kaldir|remove|delete)\b", t):
        return True
    if re.search(r"\b(kaldır|kaldir|remove|delete)\b.{0,24}\b(cta|buton|button|başlık|baslik)\b", t):
        return True
    if any(
        k in t
        for k in (
            "rakamları alt alta",
            "rakamlari alt alta",
            "rakamları kart",
            "rakamlari kart",
            "metric",
            "stacked",
            "getiriyi öne",
            "getiriyi one",
        )
    ):
        return True
    if re.search(r"\b(\d+)\s*(ayı?|months?)\b.{0,12}\b(\d+)\s*(ayı?|months?)\b", t) and any(
        k in t for k in ("yap", "make", "change", "değiştir", "degistir")
    ):
        return True
    return False


def infer_design_mode(
    instruction: str,
    posts: list[dict[str, Any]],
    requested: str | None = None,
) -> DesignMode:
    """Classify GENERATION (create/rebuild) vs EDIT (surgical). Generation wins for complete-post briefs."""
    from investhome_api.services.social_design_engine.copy_director import classify_copy_intelligence_edit

    req = (requested or "create").strip().lower()
    if req not in {"create", "edit"}:
        req = "create"
    if not posts:
        return "create"

    copy_kind, _ = classify_copy_intelligence_edit(instruction)
    if copy_kind == "change_objective":
        return "create"

    generation = is_complete_post_generation(instruction)
    surgical = is_surgical_edit(instruction) or copy_kind != "none"

    if generation and not surgical:
        return "create"
    if surgical and not generation:
        return "edit"
    if generation and surgical:
        # "hazırla" + incidental "görselini seç" is still generation.
        # "Başlığı biraz yukarı al" never includes complete-post verbs.
        return "create"
    if req == "edit":
        return "edit"
    return "create"


def extract_campaign_facts(instruction: str) -> list[CampaignFact]:
    """Pull user-supplied campaign numbers. Preserve exact display tokens."""
    raw = instruction or ""
    facts: list[CampaignFact] = []
    seen: set[str] = set()

    def _add(label: str, display: str, kind: str) -> None:
        token = display.strip()
        if not token or token in seen:
            return
        seen.add(token)
        facts.append(CampaignFact(label=label, display=token, kind=kind))

    for m in re.finditer(r"\$\s*[\d]{1,3}(?:,\d{3})+(?:\.\d+)?", raw):
        _add("campaign_money", m.group(0).replace(" ", ""), "money")
    for m in re.finditer(r"\$\s*\d+(?:\.\d+)?\s*(?:k|m|mn|million)\b", raw, re.I):
        token = re.sub(r"\s+", "", m.group(0))
        if token not in seen and not any(token != s and token in s for s in seen):
            _add("campaign_money", m.group(0).strip(), "money")
    for m in re.finditer(r"\$\s*\d+(?:\.\d+)?\b", raw):
        token = m.group(0).replace(" ", "")
        # Skip `$500` when `$500,000` was already captured.
        if any(s.startswith(token) and s != token for s in seen):
            continue
        if token not in seen:
            _add("campaign_money", m.group(0).strip(), "money")

    for m in re.finditer(r"%\s*\d+(?:[.,]\d+)?", raw):
        _add("campaign_percent", m.group(0).replace(" ", ""), "percent")
    for m in re.finditer(r"\d+(?:[.,]\d+)?\s*%", raw):
        _add("campaign_percent", m.group(0).strip(), "percent")

    for m in re.finditer(
        r"\b(\d{1,3})\s*(ay|ayı|ayi|month|months|mo)\b",
        raw,
        re.I,
    ):
        _add("campaign_duration", m.group(0).strip(), "duration")

    return facts


def classify_generation_intent(
    instruction: str,
    *,
    language: str | None = None,
    project_name: str | None = None,
) -> GenerationIntent:
    t = _norm(instruction)
    raw = instruction or ""

    lang = (language or "").strip().lower()
    if any(k in t for k in ("ingilizce", "in english", "english", "write in english")):
        lang = "en"
    elif any(k in t for k in ("türkçe", "turkce", "in turkish", "turkish")):
        lang = "tr"
    elif not lang:
        lang = "en" if re.search(r"[a-z]{4,}", t) and not re.search(r"[çğıöşü]", t) else "tr"
    if lang.startswith("tr"):
        lang = "tr"
    else:
        lang = "en"

    platform = "instagram"
    if "linkedin" in t:
        platform = "linkedin"
    elif "facebook" in t:
        platform = "facebook"
    elif re.search(r"\bx\b|twitter", t):
        platform = "x"

    format_preset = "square"
    if any(k in t for k in ("story", "hikaye", "hikayesi")):
        format_preset = "story"
    elif any(k in t for k in ("portrait", "dikey", "4:5", "4/5")):
        format_preset = "portrait"
    elif any(k in t for k in ("landscape", "yatay")):
        format_preset = "landscape"
    elif any(k in t for k in ("reel", "reels")):
        format_preset = "reelsCover"
    elif any(k in t for k in ("kare", "square", "1:1", "1/1")):
        format_preset = "square"

    objective: MarketingObjective = "general"
    asset: AssetPreference = "any"
    audience = "general"
    if any(k in t for k in ("yatırım", "yatirim", "invest", "investor", "roi", "getiri")):
        objective = "investment"
        asset = "premium_hero"
        audience = "investors"
    elif any(k in t for k in ("kat plan", "floor plan", "floorplan", "planı", "plani")):
        objective = "floor_plan"
        asset = "floor_plan"
    elif any(k in t for k in ("iç mekan", "ic mekan", "interior", "lobby", "daire iç")):
        objective = "interior"
        asset = "interior"
    elif any(
        k in t
        for k in (
            "mimari",
            "architecture",
            "architectural",
            "karakter",
            "character",
            "façade",
            "facade",
            "design language",
            "malzeme",
            "materiality",
        )
    ):
        objective = "architecture"
        asset = "exterior"
    elif any(
        k in t
        for k in (
            "lokasyon",
            "location",
            "konum",
            "merkezi",
            "neighborhood",
            "mahalle",
            "washington",
            "adres",
        )
    ):
        objective = "location"
        asset = "exterior"
    elif any(k in t for k in ("tanıtım", "tanitim", "introduction", "introduce", "lansman", "launch", "opening")):
        objective = "project_introduction"
        asset = "premium_hero"
    elif any(k in t for k in ("yaşam", "yasam", "lifestyle", "amenit")):
        objective = "lifestyle"
        asset = "interior"

    tone = "premium" if any(k in t for k in ("premium", "lüks", "luks", "luxury", "quiet luxury")) else "professional"

    facts = extract_campaign_facts(raw)
    requested_financial = [f.display for f in facts]

    key_message = ""
    if objective == "location":
        key_message = "central location"
    elif objective == "investment":
        key_message = "investment opportunity"
    elif objective == "architecture":
        key_message = "architectural character"
    elif project_name:
        key_message = project_name

    cta_hint = None
    if objective == "investment":
        from investhome_api.services.social_design_engine.localization import choose_investment_cta

        cta_hint = choose_investment_cta(lang)
    elif objective == "location":
        cta_hint = "Explore the Neighborhood" if lang == "en" else "Mahalleyi keşfet"
    elif any(k in t for k in ("tur", "tour", "randevu")):
        cta_hint = "Schedule a private tour" if lang == "en" else "Özel tur planla"

    return GenerationIntent(
        project_hint=project_name,
        platform=platform,
        format_preset=format_preset if format_preset in FORMAT_PRESETS else "square",
        language=lang,
        marketing_objective=objective,
        audience=audience,
        tone=tone,
        key_message=key_message,
        requested_facts=[],
        requested_financial_figures=requested_financial,
        cta_hint=cta_hint,
        asset_preference=asset,
    )


def generation_intent_to_dict(intent: GenerationIntent) -> dict[str, Any]:
    return asdict(intent)


def campaign_facts_to_dicts(facts: list[CampaignFact]) -> list[dict[str, Any]]:
    return [asdict(f) for f in facts]


def asset_preference_tokens(preference: AssetPreference | str) -> set[str]:
    pref = (preference or "any").strip().lower()
    mapping: dict[str, set[str]] = {
        "exterior": {
            "exterior",
            "facade",
            "façade",
            "street",
            "neighborhood",
            "aerial",
            "drone",
            "skyline",
            "hero",
            "outside",
            "building",
            "twilight",
            "location",
        },
        "neighborhood": {
            "neighborhood",
            "street",
            "aerial",
            "drone",
            "context",
            "location",
            "block",
            "avenue",
        },
        "aerial": {"aerial", "drone", "birdseye", "bird", "overhead", "site"},
        "interior": {
            "interior",
            "lobby",
            "living",
            "kitchen",
            "bedroom",
            "amenity",
            "spa",
            "pool",
            "inside",
        },
        "premium_hero": {
            "hero",
            "exterior",
            "facade",
            "premium",
            "twilight",
            "render",
            "aerial",
            "building",
        },
        "floor_plan": {"plan", "floorplan", "floor-plan", "layout", "unit", "plate"},
        "any": set(),
    }
    return mapping.get(pref, set())


def _readable_facts(facts: list[str], *, limit: int = 8) -> list[str]:
    out: list[str] = []
    for f in facts:
        text = (f or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        if "=" in text and re.match(
            r"^(project_name|project_code|city|country|address|total_units|project_type|project_status)\s*=",
            text,
            re.I,
        ):
            key, _, val = text.partition("=")
            val = val.strip()
            if not val:
                continue
            key_l = key.strip().lower()
            if key_l == "project_name":
                text = val
            elif key_l == "city":
                text = val
            elif key_l == "address":
                text = val
            elif key_l == "country":
                text = val
            elif key_l == "total_units":
                text = f"{val} units"
            else:
                continue
        out.append(text[:220])
        if len(out) >= limit:
            break
    return out


def _marketing_lines(retrieved: list[Any], *, limit: int = 4) -> list[str]:
    out: list[str] = []
    for row in retrieved:
        if not isinstance(row, dict):
            continue
        name = str(row.get("document_name") or "").lower()
        if "metadata.json" in name or name.endswith(".json"):
            continue
        text = str(row.get("text") or row.get("excerpt") or "").strip()
        if not text or looks_like_rag_or_debug_copy(text):
            continue
        sentence = text.split(".")[0].strip()
        if len(sentence) < 12:
            continue
        out.append(sentence[:180])
        if len(out) >= limit:
            break
    return out


def _clip_copy(text: str, max_len: int) -> str:
    clean = sanitize_creative_copy(text, max_len=max_len)
    if not clean:
        return ""
    if len(clean) <= max_len:
        return clean
    cut = clean[: max_len - 1].rsplit(" ", 1)[0].strip()
    return cut or clean[:max_len]


def _restore_exact_tokens(text: str, facts: list[CampaignFact]) -> str:
    """Replace converted number forms with the user-supplied display tokens."""
    out = text or ""
    for fact in facts:
        token = fact.display
        if not token or token in out:
            continue
        if fact.kind == "percent":
            m = re.search(r"%?\s*(\d+(?:[.,]\d+)?)\s*%?", token)
            if m:
                n = m.group(1)
                out = re.sub(rf"\b{re.escape(n)}\s*%", token, out)
                out = re.sub(rf"%\s*{re.escape(n)}", token, out)
        elif fact.kind == "duration":
            m = re.search(r"(\d+)", token)
            if m:
                n = m.group(1)
                out = re.sub(rf"\b{re.escape(n)}\s*(months?|mo|ayı?|ay)\b", token, out, flags=re.I)
        elif fact.kind == "money":
            digits = re.sub(r"[^\d]", "", token)
            if digits:
                grouped = f"{int(digits):,}"
                out = re.sub(rf"\$\s*{re.escape(grouped)}(?:\.\d+)?", token, out)
                out = re.sub(rf"\$\s*{re.escape(digits)}(?:\.\d+)?", token, out)
    return out


def enforce_campaign_facts(package: ContentPackage, facts: list[CampaignFact]) -> ContentPackage:
    """Keep user-supplied numbers immutable. Do not flatten metrics into a sentence."""
    from investhome_api.services.social_design_engine.localization import (
        looks_like_concatenated_metrics,
        repair_language_leaks,
        validate_creative_language,
        visible_fields_from_package,
    )

    headline = package.headline
    supporting = package.supporting_text
    key_fact = package.key_fact
    cta = package.cta
    eyebrow = getattr(package, "eyebrow", "") or ""
    lang = package.language or "en"

    if looks_like_concatenated_metrics(supporting):
        supporting = ""
    if looks_like_concatenated_metrics(key_fact):
        key_fact = ""
    if looks_like_concatenated_metrics(headline):
        headline = repair_language_leaks(headline, language=lang)

    headline = repair_language_leaks(headline, language=lang)
    supporting = repair_language_leaks(supporting, language=lang)
    key_fact = repair_language_leaks(key_fact, language=lang)
    cta = repair_language_leaks(cta, language=lang)
    eyebrow = repair_language_leaks(eyebrow, language=lang)

    repaired = ContentPackage(
        headline=_clip_copy(headline, 70),
        supporting_text=_clip_copy(supporting, 160),
        key_fact=_clip_copy(key_fact, 80),
        cta=_clip_copy(cta, 36) or package.cta,
        language=package.language,
        tone=package.tone,
        eyebrow=_clip_copy(eyebrow, 48),
    )
    report = validate_creative_language(language=lang, fields=visible_fields_from_package(repaired))
    if not report.passed:
        for issue in report.issues:
            if issue.field == "headline":
                repaired.headline = repair_language_leaks(repaired.headline, language=lang)
            elif issue.field == "support":
                repaired.supporting_text = repair_language_leaks(repaired.supporting_text, language=lang)
            elif issue.field == "cta":
                repaired.cta = repair_language_leaks(repaired.cta, language=lang)
            elif issue.field == "eyebrow":
                repaired.eyebrow = repair_language_leaks(repaired.eyebrow, language=lang)
    _ = facts
    return repaired


def build_heuristic_content_package(
    *,
    instruction: str,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    concept: Any | None = None,
) -> ContentPackage:
    from investhome_api.services.social_design_engine.creative_director import (
        clip_headline,
        is_generic_cta,
        is_generic_headline,
    )

    project_name = context.project_identity.project_name or "Project"
    lang = intent.language
    en = lang != "tr"

    if concept is not None:
        headline = clip_headline(concept.primary_message or project_name)
        supporting = concept.supporting_message if concept.include_support else ""
        eyebrow = concept.eyebrow if concept.include_eyebrow else ""
        cta = concept.cta if concept.include_cta else ""
        key_fact = ""
        if intent.marketing_objective == "investment" and campaign_facts:
            # Metrics are a structured group, not supporting copy.
            supporting = supporting if not any(f.display in (supporting or "") for f in campaign_facts) else ""
            if " · " in (supporting or ""):
                supporting = ""
        if is_generic_headline(headline):
            headline = clip_headline(concept.primary_message or project_name)
        if is_generic_cta(cta):
            cta = concept.cta
        package = ContentPackage(
            headline=_clip_copy(headline, 70) or project_name,
            supporting_text=_clip_copy(supporting, 160),
            key_fact="",
            cta=_clip_copy(cta, 36) or ("Schedule a private tour" if en else "Özel tur planla"),
            language=lang,
            tone=intent.tone,
            eyebrow=_clip_copy(eyebrow, 32),
        )
        return enforce_campaign_facts(package, campaign_facts)

    facts = _readable_facts(list(context.verified_facts or []))
    marketing = _marketing_lines(list(context.retrieved_content or []))
    location_bits = [b for b in facts if b and b.lower() not in {project_name.lower()}]
    city = context.project_identity.city or ""
    city_bit = next((b for b in location_bits if city and city.lower() in b.lower()), city)
    eyebrow = ""

    if intent.marketing_objective == "investment":
        from investhome_api.services.social_design_engine.localization import (
            choose_investment_cta,
            project_identity_lines,
        )

        ident, place = project_identity_lines(
            project_name=project_name,
            city=city,
            locale=lang,
        )
        headline = f"Invest in {project_name}" if en else f"{project_name} yatırım fırsatı"
        supporting = ""
        key_fact = ""
        cta = intent.cta_hint or choose_investment_cta(lang)
        eyebrow = ident if ident else ""
        if place and eyebrow and len(eyebrow) + len(place) + 3 <= 48:
            eyebrow = f"{eyebrow}\n{place}"
    elif intent.marketing_objective == "location":
        place = city or project_name
        headline = (
            f"A Central {place} Address" if en and place and place != project_name else project_name
        )
        loc_keys = ("location", "neighborhood", "city", city.lower()) if city else ("location",)
        supporting = next(
            (m for m in marketing if any(k in m.lower() for k in loc_keys) and "construction" not in m.lower()),
            f"A refined address in {place}." if en and place else (marketing[0] if marketing else ""),
        )
        if re.search(r"\b\d{1,6}\s+\S+\s+(rd|ave|st|blvd)\b", supporting, re.I):
            supporting = f"A refined address in {place}." if en and place else ""
        key_fact = ""
        cta = intent.cta_hint or ("Explore the Neighborhood" if en else "Mahalleyi keşfet")
    else:
        headline = project_name
        supporting = next((m for m in marketing if m != headline), "")
        key_fact = ""
        cta = intent.cta_hint or ("Schedule a private tour" if en else "Özel tur planla")

    from investhome_api.services.social_design_engine.creative_director import clip_headline as _clip_h

    headline = _clip_h(_clip_copy(headline, 70))
    supporting = _clip_copy(supporting, 160)
    cta = _clip_copy(cta, 36)
    if looks_like_rag_or_debug_copy(headline):
        headline = project_name
    if looks_like_rag_or_debug_copy(supporting):
        supporting = ""
    if looks_like_rag_or_debug_copy(cta):
        cta = "Schedule a private tour" if en else "Özel tur planla"

    package = ContentPackage(
        headline=headline or project_name,
        supporting_text=supporting,
        key_fact=key_fact if key_fact != headline else "",
        cta=cta or ("Schedule a private tour" if en else "Özel tur planla"),
        language=lang,
        tone=intent.tone,
        eyebrow=_clip_copy(eyebrow, 48),
    )
    return enforce_campaign_facts(package, campaign_facts)


def build_content_package_prompt(
    *,
    instruction: str,
    intent: GenerationIntent,
    context: CreativeStudioGenerationContext,
    campaign_facts: list[CampaignFact],
    concept: Any | None = None,
    strategy: Any | None = None,
    copy_package: Any | None = None,
    max_prompt_chars: int = 10_000,
) -> tuple[str, str]:
    system = (
        "You are an advertising copywriter for InvestHome OS Social Media Builder. "
        "Reply with JSON only: "
        '{"eyebrow":"","headline":"","supporting_text":"","cta":"","language":"","tone":""}. '
        "Follow marketing_strategy and final_copy_package. "
        "Facts are evidence, not automatically the advertisement. "
        "Answer the strategy's single_minded_message — ONE idea, not a RAG summary. "
        "Rules: use ONLY selected_facts, supporting_evidence, and user_supplied_campaign_facts. "
        "Never invent project facts or financial figures. "
        "Actively omit information_to_exclude and excluded_facts. More facts is worse. "
        "Never use a full street address as the headline. Address is internal evidence. "
        "Never put construction status, GSF, zoning, unit counts, financing, or filenames on the canvas. "
        "Do not claim steps from / minutes from / heart of DC / walkable / connected to everything "
        "unless those phrases appear in supporting_evidence. "
        "User-supplied campaign figures are structured metrics (value + label), not a concatenated sentence. "
        "Do NOT write strings like '$500,000 · %14 · 24 ay'. Do not put campaign numbers in headline or support. "
        "Do not silently change 500000 / 14 / 24. Semantic localization is owned by the metric layer. "
        "If output language is English: 14% not %14; 24 Months not 24 ay; no Turkish fragments in the ad. "
        "If a metric is the headline it must keep meaning (14% TARGET RETURN), never 'Target %14'. "
        "Do not persist campaign numbers as canonical project facts — they are this campaign only. "
        "Never include RAG/debug/metadata (Sources, chunk ids, document filenames, asset ids, provider). "
        "Headline: 2–8 words, campaign idea, not a database summary or street line. "
        "Do NOT use generic lines like Explore More Today, Discover More, Premium Living, Unique Opportunity, "
        "On Columbia Rd unless they are genuinely the right line. "
        "Do not spam premium/luxury/exclusive/unique. Prefer specificity and restraint. "
        "Support: 1 sentence or max 2 short lines. CTA must match the marketing objective. "
        "Optional eyebrow only if final_copy_package.eyebrow is non-empty. "
        "Do not add a fifth text block. Image-led posts prefer even less copy. "
        "Match the requested language and tone. No chain-of-thought."
    )
    selected = []
    exclude = []
    concept_payload: dict[str, Any] = {}
    if concept is not None:
        from investhome_api.services.social_design_engine.creative_director import (
            creative_concept_to_dict,
            selected_fact_texts,
        )

        concept_payload = {
            k: v
            for k, v in creative_concept_to_dict(concept).items()
            if k not in {"suppressed_facts", "asset_profile"}
        }
        selected = selected_fact_texts(concept)
        exclude = list(concept.information_to_exclude)
    else:
        selected = _readable_facts(list(context.verified_facts or []))
    strategy_payload: dict[str, Any] = {}
    if strategy is not None:
        from investhome_api.services.social_design_engine.marketing_strategist import strategy_to_dict

        raw_strategy = strategy_to_dict(strategy)
        strategy_payload = {
            k: v
            for k, v in raw_strategy.items()
            if k != "classified_facts"
        }
        exclude = list(dict.fromkeys(list(exclude) + list(strategy.excluded_facts)))
        selected = [s for s in selected if s not in strategy.excluded_facts]
    copy_payload: dict[str, Any] = {}
    if copy_package is not None:
        copy_payload = {
            "eyebrow": getattr(copy_package, "eyebrow", "") or "",
            "headline": getattr(copy_package, "headline", "") or "",
            "supporting_text": getattr(copy_package, "supporting_copy", None)
            or getattr(copy_package, "supporting_text", "")
            or "",
            "cta": getattr(copy_package, "cta", "") or "",
        }
    user_obj = {
        "instruction": instruction.strip(),
        "generation_intent": generation_intent_to_dict(intent),
        "marketing_strategy": strategy_payload,
        "final_copy_package": copy_payload,
        "creative_concept": concept_payload,
        "project_identity": {
            "project_name": context.project_identity.project_name,
            "city": context.project_identity.city,
        },
        "selected_facts": selected,
        "information_to_exclude": exclude,
        "user_supplied_campaign_facts": campaign_facts_to_dicts(campaign_facts),
        "structured_metrics": list(getattr(concept, "structured_metrics", []) or []) if concept is not None else [],
        "language": intent.language,
    }
    user = f"{CONTENT_PACKAGE_MARKER}\n{json.dumps(user_obj, ensure_ascii=False, default=str)}"
    if len(system) + len(user) > max_prompt_chars:
        user_obj["selected_facts"] = user_obj["selected_facts"][:4]
        user = f"{CONTENT_PACKAGE_MARKER}\n{json.dumps(user_obj, ensure_ascii=False, default=str)}"
    return system, user


def _json_object_candidates(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    candidates: list[str] = []
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw, re.I)
    if fence:
        candidates.append(fence.group(1).strip())
    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(raw):
        start = raw.find("{", idx)
        if start < 0:
            break
        try:
            _, end = decoder.raw_decode(raw, start)
            candidates.append(raw[start:end])
            idx = end
        except json.JSONDecodeError:
            idx = start + 1
    candidates.append(raw)
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item and item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def parse_content_package_from_llm(text: str) -> ContentPackage | None:
    raw = (text or "").strip()
    if not raw:
        return None
    candidates = _json_object_candidates(raw)
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        headline = sanitize_creative_copy(data.get("headline"), max_len=80)
        supporting = sanitize_creative_copy(data.get("supporting_text") or data.get("body"), max_len=180)
        key_fact = sanitize_creative_copy(data.get("key_fact"), max_len=80)
        cta = sanitize_creative_copy(data.get("cta") or data.get("cta_label"), max_len=40)
        eyebrow = sanitize_creative_copy(data.get("eyebrow"), max_len=40)
        if not headline:
            continue
        if looks_like_rag_or_debug_copy(headline) or looks_like_rag_or_debug_copy(supporting):
            continue
        from investhome_api.services.social_design_engine.creative_director import clip_headline

        return ContentPackage(
            headline=clip_headline(_clip_copy(headline, 70)),
            supporting_text=_clip_copy(supporting, 160),
            key_fact=_clip_copy(key_fact, 80),
            cta=_clip_copy(cta, 36) or "Schedule a private tour",
            language=str(data.get("language") or "en")[:8],
            tone=str(data.get("tone") or "premium")[:32],
            eyebrow=_clip_copy(eyebrow, 32),
        )
    return None


def content_package_to_dict(package: ContentPackage) -> dict[str, Any]:
    return asdict(package)


def build_design_plan(
    *,
    package: ContentPackage,
    intent: GenerationIntent,
    picked_asset_id: UUID | None,
    post_id: str,
    rebuild: bool,
    canvas_w: int | None = None,
    canvas_h: int | None = None,
    concept: Any | None = None,
    structured_metrics: list[Any] | None = None,
    metric_layout: str | None = None,
) -> DesignPlan:
    from investhome_api.services.social_design_engine.layout import measure_text_block, role_font_prefs

    preset = intent.format_preset if intent.format_preset in FORMAT_PRESETS else "square"
    w, h = FORMAT_PRESETS.get(preset, (1080, 1080))
    if canvas_w and canvas_h:
        w, h = canvas_w, canvas_h

    family = "LOCATION"
    align = "left"
    overlay_region = "top"
    density = "sparse"
    safe_zone = "top"
    overlay = "localized_gradient"
    if concept is not None:
        family = concept.composition_strategy
        align = concept.alignment
        overlay_region = concept.overlay_region
        density = concept.text_density
        safe_zone = concept.safe_text_zone
        overlay = f"localized-{overlay_region}"

    slots = social_layout_slots(w, h, family=family, align=align, safe_zone=safe_zone)
    hs = slots["headline"]
    bs = slots["body"]
    cs = slots["cta"]
    es = slots.get("eyebrow")

    include_eyebrow = bool(package.eyebrow) and (concept is None or concept.include_eyebrow)
    include_support = bool(package.supporting_text) and (concept is None or concept.include_support)
    include_cta = bool(package.cta) and (concept is None or concept.include_cta)

    from investhome_api.services.social_design_engine.localization import looks_like_concatenated_metrics
    from investhome_api.services.social_design_engine.metrics import (
        choose_metric_group_layout,
        structured_metrics_from_dicts,
        structured_metrics_to_dicts,
    )

    metrics_in = structured_metrics
    if metrics_in is None and concept is not None:
        metrics_in = getattr(concept, "structured_metrics", None)
    parsed_metrics = []
    if metrics_in:
        if metrics_in and hasattr(metrics_in[0], "display_value"):
            parsed_metrics = list(metrics_in)
        else:
            parsed_metrics = structured_metrics_from_dicts(list(metrics_in))
    requested_layout = metric_layout
    if requested_layout is None and concept is not None:
        requested_layout = getattr(concept, "metric_group_layout", None)
    include_metrics = bool(parsed_metrics)
    if include_metrics:
        include_support = False

    body_text = package.supporting_text
    if package.key_fact and package.key_fact not in (body_text or "") and include_support:
        if looks_like_concatenated_metrics(package.key_fact):
            pass
        else:
            body_text = f"{body_text} · {package.key_fact}".strip(" ·") if body_text else package.key_fact
    if looks_like_concatenated_metrics(body_text or ""):
        body_text = ""
        include_support = False
    body_text = _clip_copy(body_text, 160) if include_support else ""

    h_prefs = role_font_prefs("headline", w)
    b_prefs = role_font_prefs("body", w)
    e_prefs = role_font_prefs("eyebrow", w)
    stack_gap = max(16, int(round(h * 0.018)))

    def _block_h(text: str, font: int, width: int, *, bold: bool, cap: int) -> int:
        _, measured, _ = measure_text_block(text, font, width, bold=bold)
        return min(cap, max(int(round(font * 1.2)), measured))

    elements: list[DesignPlanElement] = []
    y_cursor = hs["y"]
    if include_eyebrow and es:
        eh = _block_h(package.eyebrow, e_prefs["preferred"], es["width"], bold=False, cap=es["max_height"])
        elements.append(
            DesignPlanElement(
                type="TEXT",
                role="eyebrow",
                text=package.eyebrow,
                x=es["x"],
                y=es["y"],
                width=es["width"],
                height=eh,
                font_size=e_prefs["preferred"],
                font_weight="normal",
                align=align,
                color="#ffffff",
                z_index=2,
            )
        )
        y_cursor = max(y_cursor, es["y"] + eh + stack_gap)
    hh = _block_h(package.headline, h_prefs["preferred"], hs["width"], bold=True, cap=hs["max_height"])
    headline_y = max(hs["y"], y_cursor)
    elements.append(
        DesignPlanElement(
            type="TEXT",
            role="headline",
            text=package.headline,
            x=hs["x"],
            y=headline_y,
            width=hs["width"],
            height=hh,
            font_size=h_prefs["preferred"],
            font_weight="bold",
            align=align,
            color="#ffffff",
            z_index=3,
        )
    )
    y_cursor = headline_y + hh + stack_gap
    if include_metrics:
        ms = slots.get("metric_group") or bs
        layout = choose_metric_group_layout(
            metrics=parsed_metrics,
            format_preset=preset,
            canvas_w=w,
            available_width=int(ms.get("width") or hs["width"]),
            requested=requested_layout,  # type: ignore[arg-type]
        )
        mg_h = int(ms.get("max_height") or max(120, int(round(h * 0.16))))
        if layout == "stacked":
            mg_h = min(int(round(h * 0.28)), max(mg_h, 48 * len(parsed_metrics)))
        elif layout == "cards":
            mg_h = min(int(round(h * 0.26)), max(mg_h, 88))
        mg_y = max(int(ms.get("y") or y_cursor), y_cursor)
        elements.append(
            DesignPlanElement(
                type="METRIC_GROUP",
                role="metric_group",
                text="",
                x=int(ms.get("x") or hs["x"]),
                y=mg_y,
                width=int(ms.get("width") or hs["width"]),
                height=mg_h,
                align=align,
                color="#ffffff",
                z_index=4,
                metrics=structured_metrics_to_dicts(parsed_metrics),
                metric_layout=layout,
            )
        )
        y_cursor = mg_y + mg_h + stack_gap
    if include_support and body_text:
        bh = _block_h(body_text, b_prefs["preferred"], bs["width"], bold=False, cap=bs["max_height"])
        body_y = max(bs["y"], y_cursor)
        # Keep support in the same content group; never overlap the headline.
        if body_y < y_cursor:
            body_y = y_cursor
        elements.append(
            DesignPlanElement(
                type="TEXT",
                role="body",
                text=body_text,
                x=bs["x"],
                y=body_y,
                width=bs["width"],
                height=bh,
                font_size=b_prefs["preferred"],
                font_weight="normal",
                align=align,
                color="#ffffff",
                z_index=4,
            )
        )
    if include_cta:
        elements.append(
            DesignPlanElement(
                type="BUTTON",
                role="cta",
                text=package.cta,
                x=cs["x"],
                y=cs["y"],
                width=cs["width"],
                height=cs["height"],
                align=align,
                background_color="#ffffff",
                text_color="#111827",
                z_index=5,
            )
        )
    return DesignPlan(
        format_preset=preset,
        platform=intent.platform,
        background_asset_id=str(picked_asset_id) if picked_asset_id else None,
        overlay=overlay,
        post_id=post_id,
        rebuild=rebuild,
        elements=elements,
        name=f"AI {preset}",
        composition_strategy=family,
        alignment=align,
        overlay_region=overlay_region,
        text_density=density,
        safe_text_zone=safe_zone,
    )


def design_plan_to_dict(plan: DesignPlan) -> dict[str, Any]:
    return {
        "format": plan.format_preset,
        "platform": plan.platform,
        "background_asset_id": plan.background_asset_id,
        "overlay": plan.overlay,
        "post_id": plan.post_id,
        "rebuild": plan.rebuild,
        "name": plan.name,
        "composition_strategy": plan.composition_strategy,
        "alignment": plan.alignment,
        "overlay_region": plan.overlay_region,
        "text_density": plan.text_density,
        "safe_text_zone": plan.safe_text_zone,
        "elements": [asdict(el) for el in plan.elements],
    }


def compose_ops_from_plan(
    plan: DesignPlan,
    *,
    linked_project_id: UUID,
    instruction: str,
) -> list[dict[str, Any]]:
    """Convert a design plan into existing Design Ops (same posts[].elements[] schema)."""
    pid = str(linked_project_id)
    post_id = plan.post_id or str(uuid4())
    ops: list[dict[str, Any]] = [
        {
            "op": "CREATE_POST",
            "linked_project_id": pid,
            "post_id": post_id,
            "element_id": None,
            "payload": {
                "formatPreset": plan.format_preset,
                "platform": plan.platform,
                "name": plan.name,
                "description": (instruction or "")[:240],
                "rebuild": True,
                "compositionStrategy": plan.composition_strategy,
                "overlayStrategy": plan.overlay,
                "textAlign": plan.alignment,
                "safeTextZone": plan.safe_text_zone,
                "textDensity": plan.text_density,
            },
        },
        {
            "op": "SET_FORMAT",
            "linked_project_id": pid,
            "post_id": post_id,
            "element_id": None,
            "payload": {"formatPreset": plan.format_preset},
        },
    ]
    if plan.background_asset_id:
        ops.append(
            {
                "op": "SET_BACKGROUND",
                "linked_project_id": pid,
                "post_id": post_id,
                "element_id": None,
                "payload": {"asset_id": plan.background_asset_id},
            }
        )
    for el in plan.elements:
        if el.type == "TEXT":
            ops.append(
                {
                    "op": "ADD_TEXT",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": None,
                    "payload": {
                        "role": el.role,
                        "content": el.text,
                        "fontWeight": el.font_weight or ("bold" if el.role == "headline" else "normal"),
                        "fontSize": el.font_size,
                        "align": el.align,
                        "color": el.color,
                        "zIndex": el.z_index,
                    },
                }
            )
        elif el.type in {"BUTTON", "CTA"}:
            ops.append(
                {
                    "op": "ADD_CTA",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": None,
                    "payload": {
                        "label": el.text,
                        "backgroundColor": el.background_color or "#ffffff",
                        "textColor": el.text_color or "#111827",
                        "zIndex": el.z_index,
                    },
                }
            )
        elif el.type == "METRIC_GROUP":
            ops.append(
                {
                    "op": "ADD_METRIC_GROUP",
                    "linked_project_id": pid,
                    "post_id": post_id,
                    "element_id": None,
                    "payload": {
                        "layout": el.metric_layout or "horizontal",
                        "metrics": el.metrics or [],
                        "color": el.color,
                        "zIndex": el.z_index,
                        "x": el.x,
                        "y": el.y,
                        "width": el.width,
                        "height": el.height,
                    },
                }
            )
    return ops


def attach_generation_metadata(
    post: dict[str, Any],
    *,
    meta: dict[str, Any],
) -> dict[str, Any]:
    """Store generation metadata on the post document — never as a canvas TEXT/CTA element."""
    post["generationMeta"] = meta
    return post


def build_generation_metadata(
    *,
    project_id: UUID,
    user_prompt: str,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    source_document_ids: list[str],
    selected_asset_ids: list[str],
    provider: str,
    model: str,
    content_package: ContentPackage | None = None,
    design_plan: DesignPlan | None = None,
    creative_concept: dict[str, Any] | None = None,
    validation: dict[str, Any] | None = None,
    marketing_strategy: dict[str, Any] | None = None,
    copy_quality: dict[str, Any] | None = None,
    headline_candidates: list[dict[str, Any]] | None = None,
    structured_metrics: list[dict[str, Any]] | None = None,
    metric_group: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "generated_by": "social_design_engine",
        "project_id": str(project_id),
        "user_prompt": (user_prompt or "")[:2000],
        "generation_intent": generation_intent_to_dict(intent),
        "campaign_facts": campaign_facts_to_dicts(campaign_facts),
        "structured_metrics": structured_metrics or [],
        "metric_group": metric_group,
        "source_document_ids": source_document_ids,
        "selected_asset_ids": selected_asset_ids,
        "provider": provider,
        "model": model,
        "generated_at": datetime.now(UTC).isoformat(),
        "content_package": content_package_to_dict(content_package) if content_package else None,
        "design_plan": design_plan_to_dict(design_plan) if design_plan else None,
        "creative_concept": creative_concept,
        "validation": validation,
        "marketing_strategy": marketing_strategy,
        "copy_quality": copy_quality,
        "headline_candidates": headline_candidates or [],
    }


def resolve_generation_post_id(
    draft_posts: list[dict[str, Any]],
    selected_post_id: str | None,
) -> tuple[str, bool]:
    """Reuse the current post for rebuild; mint an id only when the canvas is empty."""
    if selected_post_id:
        for post in draft_posts:
            if isinstance(post, dict) and str(post.get("id") or "") == selected_post_id:
                return selected_post_id, True
    if draft_posts and isinstance(draft_posts[0], dict) and draft_posts[0].get("id"):
        return str(draft_posts[0]["id"]), True
    return str(uuid4()), False
