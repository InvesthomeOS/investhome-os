"""Quick Creative production safety — facts, logo integrity, composition checks.

Global rules for every Investhome project. Does not hardcode a project.
Does not invent commercial numbers from templates, references, or seed copy.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from PIL import Image, ImageDraw, ImageStat

logger = logging.getLogger(__name__)

SAFE_MARGIN = 0.08
LOGO_MAX_WIDTH_RATIO = 0.20
LOGO_MAX_HEIGHT_RATIO = 0.14
LOGO_MARGIN_X_RATIO = 0.055
LOGO_MARGIN_Y_RATIO = 0.055
BRAND_LOGO_MAX_WIDTH_RATIO = 0.11
BRAND_LOGO_MAX_HEIGHT_RATIO = 0.055
BRAND_LOGO_MARGIN_X_RATIO = 0.055
BRAND_LOGO_MARGIN_Y_RATIO = 0.055
MIN_LOGO_CONTRAST = 3.0
DARK_BACKGROUND_LUMA = 140
BRAND_PLATE_DARK = (16, 18, 22)
BRAND_PLATE_LIGHT = (245, 242, 236)
PHOTOGRAPHIC_LUMA_STD_MIN = 18.0
PHOTO_SPLIT_GUTTER_ENERGY_MAX = 8.0
DETERMINISTIC_OS_COMPOSITION_CHECKS = frozenset(
    {
        "BRAND_LOGO_VISIBILITY",
        "INVESTHOME_LOGO_COUNT",
    }
)

QUICK_COMPOSITION_FAIL_MESSAGE = (
    "Kompozisyon güvenlik kontrolü geçmedi. Tasarım tamamlanmış sayılmaz. Lütfen tekrar deneyin."
)
QUICK_COMPOSITION_RETRY_FAIL_MESSAGE = (
    "Tasarım güvenlik kontrolünden geçemedi. Yeniden üretmeyi deneyin."
)
QUICK_COMPOSITION_MAX_ATTEMPTS = 2

# Seed / template / fallback commercial copy. DESIGN_REFERENCES must never supply these.
# Values match Phase 5 REQUIRED_FACTS and adapt_final_turkish_texts placeholders — not a project.
SEED_TEMPLATE_COMMERCIAL_TOKENS = (
    "675.000",
    "675000",
    "675,000",
    "438.750",
    "438750",
    "438,750",
    "%35",
    "35%",
    "2+1",
    "2 + 1",
    "alirken kazan",
    "alir kaz",
    "lansman avantajı",
    "lansman avantaji",
    "$400,000",
    "$300,000",
    "400,000",
    "300,000",
    "unit 204",
    "~25%",
    "25%",
)

_PRICE_RE = re.compile(
    r"(?:\$\s*)?(\d{1,3}(?:[.\s]\d{3})+)(?:\s*(usd|eur|tl|₺|\$))?",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(r"(?:%\s*(\d{1,2})|(\d{1,2})\s*%)")
_UNIT_TYPE_RE = re.compile(r"\b(\d\s*\+\s*\d|st[uü]dyo|studio)\b", re.IGNORECASE)
_SQFT_RE = re.compile(r"\b(\d{2,5})\s*(?:m2|m²|sqft|sq\.?\s*ft)\b", re.IGNORECASE)
_CLIP_RE = re.compile(r"(\.\.\.|…|\b\w{2,}-\s*$)", re.MULTILINE)

_COMMERCIAL_FACT_MARKERS = (
    "fiyat",
    "price",
    "roi",
    "getiri",
    "kira",
    "rent",
    "iskonto",
    "indirim",
    "discount",
    "teslim tarihi",
    "completion",
    "yield",
)
_NEGATIVE_CONSTRAINT_CUES = (
    "uydurma",
    "uydurmayin",
    "yazma",
    "yazmayin",
    "kullanma",
    "kullanmayin",
    "ekleme",
    "eklemeyin",
    "gosterme",
    "koyma",
    "koymayin",
    "icat etme",
    "do not",
    "don't",
    "dont ",
    "without price",
    "without roi",
    "no price",
    "no roi",
    "herhangi bir fiyat",
    "herhangi bir finansal",
    "finansal veri uydurma",
    "finansal veri kullanma",
)
_AFFIRMATIVE_FACT_RE = re.compile(
    r"(?:\b(?:yaz(?:in)?|ekle(?:yin)?|koy(?:un)?|belirt(?:in)?|goster(?:in)?|"
    r"kullan(?:in)?|include|add|show|write|put|degistir)\b|"
    r"ne kadar|nedir|\bkac\b)",
    re.IGNORECASE,
)
_CLAUSE_SPLIT_RE = re.compile(r"[.\n;!?]+")

_MULTI_PHOTO_CUES = (
    "iki farkli",
    "iki gorun",
    "ic ve dis",
    "dis ve ic",
    "kolaj",
    "collage",
    "split screen",
    "split-screen",
    "yan yana",
    "ust uste",
    "picture in picture",
    "picture-in-picture",
    "birden fazla gorsel",
    "birden fazla foto",
    "iki dis cephe",
    "iki farkli dis cephe",
    "gorsellerini birlikte",
    "birlikte goster",
    "multiple photo",
    "two photos",
    "two images",
    "use two",
    "use three",
)
_MULTI_PHOTO_COUNT_RE = re.compile(
    r"\b([2-9]|iki|uc|dort)\s+(proje\s+)?(gorsel|foto|photo|image)",
)

COMPOSITION_CHECK_KEYS = (
    "LOGO_VISIBLE",
    "TEXT_WITHIN_SAFE_BOUNDS",
    "NO_CRITICAL_TEXT_OVERLAP",
    "NO_ORPHAN_TEXT",
    "NO_TEMPLATE_FACT_LEAKAGE",
    "NO_REFERENCE_FACT_LEAKAGE",
    "PROJECT_PHOTO_VALID",
    "PROJECT_LOGO_VALID",
    "PROJECT_HERO_PHOTO_COUNT",
    "PROJECT_LOGO_COUNT",
    "PROJECT_LOGO_VISIBILITY",
    "INVESTHOME_LOGO_COUNT",
    "BRAND_LOGO_VISIBILITY",
    "AI_GENERATED_LOGO_COUNT",
)
OCR_DEPENDENT_CHECKS = (
    "TEXT_WITHIN_SAFE_BOUNDS",
    "NO_CRITICAL_TEXT_OVERLAP",
    "NO_ORPHAN_TEXT",
    "NO_TEMPLATE_FACT_LEAKAGE",
    "NO_REFERENCE_FACT_LEAKAGE",
    "AI_GENERATED_LOGO_COUNT",
)

NON_RECOVERABLE_COMPOSITION_CHECKS = frozenset(
    {
        "NO_TEMPLATE_FACT_LEAKAGE",
        "NO_REFERENCE_FACT_LEAKAGE",
        "PROJECT_PHOTO_VALID",
        "PROJECT_LOGO_VALID",
    }
)
RECOVERABLE_COMPOSITION_HINTS = {
    "TEXT_WITHIN_SAFE_BOUNDS": "headline or body type exceeded the 8% safe bounds",
    "NO_CRITICAL_TEXT_OVERLAP": "type overlapped a reserved logo territory",
    "NO_ORPHAN_TEXT": "a word was clipped or left incomplete",
    "PROJECT_HERO_PHOTO_COUNT": "more than one project photograph appeared in the layout",
    "PROJECT_LOGO_COUNT": "an extra project wordmark was painted besides the authentic logo",
    "PROJECT_LOGO_VISIBILITY": "the authentic project logo was not clearly visible against its background",
    "LOGO_VISIBLE": "the authentic project logo was not clearly visible",
    "BRAND_LOGO_VISIBILITY": "the Investhome brand mark was not clearly visible against its background",
    "INVESTHOME_LOGO_COUNT": "the Investhome brand closure was missing or duplicated",
    "AI_GENERATED_LOGO_COUNT": "a model-painted fake logo or wordmark remained",
}

QUICK_PRODUCTION_QUALITY = "high"
QUICK_NO_DESIGN_REFERENCE_MESSAGE = (
    "Onaylı tasarım referansı yüklenemedi. Tasarım tamamlanmış sayılmaz."
)

# Grade-A DESIGN_REFERENCES campaign facts that must never appear on another project.
REFERENCE_CAMPAIGN_LEAK_TOKENS = (
    "uniloft",
    "uni loft",
    "300 i st",
    "357.000",
    "357000",
    "$357",
    "%40",
    "40%",
    "duzenli",
    "düzenli",
    "erken erisim",
    "erken erişim",
    "early access",
    "erken teslim",
)

RESERVED_LOGO_WIDTH_RATIO = 0.24
RESERVED_LOGO_HEIGHT_RATIO = 0.18
RESERVED_BRAND_WIDTH_RATIO = 0.22
RESERVED_BRAND_HEIGHT_RATIO = 0.14

_STYLE_MARKERS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("location", ("konum", "lokasyon", "adres", "yakin", "yakın", "location", "proximity", "mesafe", "yurume", "yürüme")),
    ("lifestyle", ("yasam", "yaşam", "lifestyle", "interior", "ic mekan", "iç mekan", "mutfak", "teras", "kitchen")),
    ("launch", ("lansman kampanya", "launch", "teslim", "delivery", "acilim", "açılım")),
    ("minimal", ("sade", "minimal", "minimalist", "yalin", "yalın")),
    ("editorial", ("prestij", "editorial", "luks", "lüks", "premium", "modern", "anitsal", "flagship")),
    ("investment", ("yatirim", "yatırım", "investment", "getiri")),
)

_STYLE_TO_FILENAME = {
    "editorial": "ORNEK_00013.jpg",
    "investment": "ORNEK_00013.jpg",
    "minimal": "ORNEK_00013.jpg",
    "launch": "ORNEK_00008.jpg",
    "location": "ORNEK_00011.jpg",
    "lifestyle": "ORNEK_00015.jpg",
}
_DEFAULT_REFERENCE_FILENAME = "ORNEK_00013.jpg"


def _fold(text: str) -> str:
    table = str.maketrans({"İ": "i", "I": "i", "ı": "i", "Ş": "s", "ş": "s", "Ğ": "g", "ğ": "g", "Ü": "u", "ü": "u", "Ö": "o", "ö": "o", "Ç": "c", "ç": "c"})
    return (text or "").translate(table).casefold()


def _compact(text: str) -> str:
    return re.sub(r"[\s.,]", "", _fold(text))


def split_intent_clauses(text: str) -> list[str]:
    return [part.strip() for part in _CLAUSE_SPLIT_RE.split(text or "") if part.strip()]


def classify_quick_reference_style(user_request: str) -> str:
    """Map natural language to one DESIGN_REFERENCES art-direction style."""
    folded = _fold(user_request)
    matched: list[str] = []
    for style, markers in _STYLE_MARKERS:
        if any(marker in folded for marker in markers):
            matched.append(style)
    if "editorial" in matched:
        return "editorial"
    if "location" in matched:
        return "location"
    if "lifestyle" in matched:
        return "lifestyle"
    if "launch" in matched:
        return "launch"
    if "investment" in matched:
        return "investment"
    if "minimal" in matched:
        return "minimal"
    return "editorial"


def select_quick_design_reference(user_request: str) -> dict[str, str]:
    """Pick ONE Grade-A DESIGN_REFERENCES asset. Never ORNEK_00001 by default."""
    from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA

    style = classify_quick_reference_style(user_request)
    filename = _STYLE_TO_FILENAME.get(style, _DEFAULT_REFERENCE_FILENAME)
    if filename not in GRADE_A_MEDIA:
        filename = _DEFAULT_REFERENCE_FILENAME
    if filename == "ORNEK_00001.jpg":
        filename = _DEFAULT_REFERENCE_FILENAME
    asset_id = str(GRADE_A_MEDIA[filename])
    return {
        "style": style,
        "filename": filename,
        "asset_id": asset_id,
        "authority": "visual_language_only",
    }


def grade_a_design_reference_ids() -> set[str]:
    from investhome_api.services.creative_director.creative_design_dna_v2 import GRADE_A_MEDIA

    return {str(value) for value in GRADE_A_MEDIA.values()}


def quick_generation_input_contract(builder_context: dict[str, Any]) -> dict[str, Any]:
    """Expected live image-request roles for a Quick Creative generate call."""
    ctx = builder_context or {}
    revision = bool(ctx.get("revision_mode"))
    attach = bool(ctx.get("attach_design_reference")) and not revision
    logo_disabled = bool(ctx.get("skip_logo_edit_input") and ctx.get("skip_project_logo"))
    return {
        "PROJECT_PHOTO_INPUT": 1,
        "DESIGN_REFERENCE_VISUAL_INPUT": 1 if attach else 0,
        "PROJECT_LOGO_GENERATION_INPUT": 0 if logo_disabled else 1,
        "INVESTHOME_LOGO_GENERATION_INPUT": 0 if logo_disabled else 1,
        "REAL_LOGO_POST_COMPOSITE": 1,
        "INVESTHOME_LOGO_POST_COMPOSITE": 1,
        "REFERENCE_FACT_AUTHORITY": 0,
        "REFERENCE_ARCHITECTURE_AUTHORITY": 0,
        "FACT_SAFETY": "ACTIVE",
        "SINGLE_HERO_RULE": "ACTIVE" if ctx.get("single_hero_photo") else "OFF",
        "IMAGE_QUALITY_MODE": str(ctx.get("gpt_image_quality") or ""),
        "design_reference_asset_id": str(ctx.get("design_reference_asset_id") or ""),
        "unguided_fallback": False,
    }


def failed_composition_checks(pack: dict[str, Any] | None) -> list[str]:
    return [str(key) for key in list((pack or {}).get("failed") or [])]


def is_recoverable_composition_failure(pack: dict[str, Any] | None) -> bool:
    """True only for generative visual-layout failures that can change on regeneration.

    Deterministic OS logo placement (Investhome contrast/count) is not a GPT retry.
    """
    failed = failed_composition_checks(pack)
    if not failed:
        return False
    if any(key in NON_RECOVERABLE_COMPOSITION_CHECKS for key in failed):
        return False
    generative = [key for key in failed if key not in DETERMINISTIC_OS_COMPOSITION_CHECKS]
    return bool(generative)


def should_auto_retry_quick_composition(pack: dict[str, Any] | None, *, attempt_index: int) -> bool:
    if attempt_index < 0 or attempt_index >= QUICK_COMPOSITION_MAX_ATTEMPTS - 1:
        return False
    return is_recoverable_composition_failure(pack)


def describe_recoverable_composition_failure(pack: dict[str, Any] | None) -> str:
    failed = failed_composition_checks(pack)
    hints = [RECOVERABLE_COMPOSITION_HINTS.get(key, key.replace("_", " ").lower()) for key in failed]
    if not hints:
        hints = ["a visual layout check failed"]
    joined = "; ".join(hints)
    return (
        f"Previous composition failed because {joined}. "
        "Create a fresh composition preserving the same intent and assets, "
        "with all text fully inside safe areas."
    )


def quick_composition_user_message(*, retried: bool) -> str:
    if retried:
        return QUICK_COMPOSITION_RETRY_FAIL_MESSAGE
    return QUICK_COMPOSITION_FAIL_MESSAGE


def allowed_copy_package(policy: QuickFactPolicy, user_request: str) -> list[str]:
    lines = [f"User message (mood + requested language): {(user_request or '').strip() or '(empty)'}"]
    identity = [f"{key}={value}" for key, value in policy.verified.items() if value]
    lines.append("Verified project identity: " + (", ".join(identity) if identity else "none beyond unnamed project"))
    provided = [f"{key}={value}" for key, value in policy.user_provided.items() if value]
    lines.append("User-provided commercial facts: " + (", ".join(provided) if provided else "none"))
    lines.append("Creative copy may paraphrase the user message. It may not invent numbers or copy IMAGE 2 text.")
    return lines


def has_multi_photo_intent(request: str) -> bool:
    """True only when the user clearly asks for more than one project photo in the ad.

    'Gerçek proje görsellerini kullan' means use the approved library, not a collage.
    """
    folded = _fold(request)
    if any(cue in folded for cue in _MULTI_PHOTO_CUES):
        return True
    return _MULTI_PHOTO_COUNT_RE.search(folded) is not None


def estimate_project_hero_photo_count(image: Image.Image) -> int:
    """Count large independent photographic territories. Default expected value is 1.

    Graphic overlays, footer strips, and type territories are not photographs.
    A structure-energy valley alone is not enough.
    """
    from investhome_api.services.creative_director.project_architecture_lock import (
        STRUCTURE_ENERGY_MIN,
        _edge_energy,
    )

    rgb = image.convert("RGB")
    w, h = rgb.size
    if w < 32 or h < 32:
        return 1
    mx, my = int(w * 0.06), int(h * 0.06)
    left = rgb.crop((0, my, max(1, int(w * 0.46)), h - my))
    right = rgb.crop((min(w - 1, int(w * 0.54)), my, w, h - my))
    mid = rgb.crop((int(w * 0.40), my, int(w * 0.60), h - my))
    top = rgb.crop((mx, 0, w - mx, max(1, int(h * 0.46))))
    bottom = rgb.crop((mx, min(h - 1, int(h * 0.54)), w - mx, h))
    mid_h = rgb.crop((mx, int(h * 0.40), w - mx, max(int(h * 0.40) + 1, int(h * 0.60))))
    left_e = _edge_energy(left)
    right_e = _edge_energy(right)
    mid_e = _edge_energy(mid)
    top_e = _edge_energy(top)
    bot_e = _edge_energy(bottom)
    mid_h_e = _edge_energy(mid_h)
    split_lr = (
        left_e >= STRUCTURE_ENERGY_MIN
        and right_e >= STRUCTURE_ENERGY_MIN
        and mid_e < PHOTO_SPLIT_GUTTER_ENERGY_MAX
        and mid_e < min(left_e, right_e) * 0.45
        and _region_is_photographic(left)
        and _region_is_photographic(right)
    )
    split_tb = (
        top_e >= STRUCTURE_ENERGY_MIN
        and bot_e >= STRUCTURE_ENERGY_MIN
        and mid_h_e < PHOTO_SPLIT_GUTTER_ENERGY_MAX
        and mid_h_e < min(top_e, bot_e) * 0.45
        and _region_is_photographic(top)
        and _region_is_photographic(bottom)
    )
    return 2 if split_lr or split_tb else 1


def resolve_project_hero_photo_count(
    image: Image.Image,
    *,
    provenance_count: int | None = None,
    multi_photo_intent: bool = False,
) -> int:
    """Provenance of project-photo inputs is primary. Visual split is secondary."""
    visual = estimate_project_hero_photo_count(image)
    if multi_photo_intent:
        return visual
    if provenance_count == 1:
        # One project-photo input is authoritative unless a corroborated photographic split exists.
        return 2 if visual == 2 else 1
    return visual


def _region_is_photographic(crop: Image.Image) -> bool:
    return _luma_std(crop) >= PHOTOGRAPHIC_LUMA_STD_MIN


def _luma_std(crop: Image.Image) -> float:
    if crop.width < 2 or crop.height < 2:
        return 0.0
    return float(ImageStat.Stat(crop.convert("L")).stddev[0] or 0.0)


def is_negative_constraint_clause(clause: str) -> bool:
    folded = _fold(clause)
    return any(cue in folded for cue in _NEGATIVE_CONSTRAINT_CUES)


def clause_mentions_commercial_fact(clause: str) -> bool:
    folded = _fold(clause)
    return any(marker in folded for marker in _COMMERCIAL_FACT_MARKERS)


def clause_affirmatively_requests_fact(clause: str) -> bool:
    if is_negative_constraint_clause(clause):
        return False
    if not clause_mentions_commercial_fact(clause):
        return False
    return _AFFIRMATIVE_FACT_RE.search(_fold(clause)) is not None


def requests_unsupported_commercial_fact(request: str) -> bool:
    """True only when the user asks to include a commercial number and does not supply one.

    Negative constraints ("fiyat uydurma") and general creative language ("yatırım odaklı")
    must not block generation. Unsupported facts are omitted instead.
    """
    clauses = split_intent_clauses(request) or [request or ""]
    requested = False
    for clause in clauses:
        if not clause_affirmatively_requests_fact(clause):
            continue
        requested = True
        if _HAS_NUMBER.search(clause):
            return False
    if not requested:
        return False
    return _HAS_NUMBER.search(request or "") is None


_HAS_NUMBER = re.compile(r"\d")


@dataclass
class QuickFactPolicy:
    verified: dict[str, str] = field(default_factory=dict)
    user_provided: dict[str, str] = field(default_factory=dict)
    creative_copy: str = ""
    facts: dict[str, str] = field(default_factory=dict)
    allowed_commercial_tokens: list[str] = field(default_factory=list)
    blocked_template_tokens: list[str] = field(default_factory=list)

    def as_public_dict(self) -> dict[str, Any]:
        return {
            "VERIFIED_PROJECT_FACT": dict(self.verified),
            "USER_PROVIDED_FACT": dict(self.user_provided),
            "CREATIVE_COPY": self.creative_copy,
            "UNVERIFIED_COMMERCIAL_FACT": "forbidden",
        }


def verified_identity_facts(project: Any | None) -> dict[str, str]:
    """Identity only. Never acquisition_price, total_units, or internal finance."""
    if project is None:
        return {}
    out: dict[str, str] = {}
    name = str(getattr(project, "project_name", "") or "").strip()
    city = str(getattr(project, "city", "") or "").strip()
    state = str(getattr(project, "state", "") or "").strip()
    address = str(getattr(project, "address", "") or "").strip()
    if name:
        out["name"] = name
    if city:
        out["city"] = city
    if state:
        out["state"] = state
    if address:
        out["address"] = address
    return out


def extract_user_commercial_facts(user_request: str) -> dict[str, str]:
    raw_clauses = split_intent_clauses(user_request) or [user_request or ""]
    raw = " ".join(clause for clause in raw_clauses if not is_negative_constraint_clause(clause))
    folded = _fold(raw)
    facts: dict[str, str] = {}
    prices = _PRICE_RE.findall(raw)
    if prices:
        amount, currency = prices[-1]
        currency = (currency or "USD").strip().upper().replace("₺", "TL")
        if currency == "$":
            currency = "USD"
        facts["list_price"] = f"{amount.strip()} {currency}".strip()
    percents = _PERCENT_RE.findall(raw)
    if percents and any(tok in folded for tok in ("indirim", "iskonto", "discount", "lansman", "avantaj", "%")):
        digits = next((a or b for a, b in percents if (a or b)), "")
        if digits:
            facts["discount"] = f"%{digits}"
    units = _UNIT_TYPE_RE.findall(raw)
    if units:
        token = re.sub(r"\s+", "", units[-1])
        facts["unit"] = token.upper() if "+" in token else token
        if "+" in token:
            facts["unit_label"] = "DAİRE"
    areas = _SQFT_RE.findall(raw)
    if areas:
        facts["area"] = areas[-1]
    return facts


def classify_quick_facts(
    *,
    user_request: str,
    project: Any | None = None,
    extra_user_text: str = "",
) -> QuickFactPolicy:
    verified = verified_identity_facts(project)
    combined = "\n".join(part for part in (user_request, extra_user_text) if part)
    user_facts = extract_user_commercial_facts(combined)
    allow_haystack = " ".join(
        clause for clause in (split_intent_clauses(combined) or [combined]) if not is_negative_constraint_clause(clause)
    )
    allowed = [value for value in user_facts.values() if value]
    allowed.extend(value for value in verified.values() if value)
    blocked = [
        token
        for token in SEED_TEMPLATE_COMMERCIAL_TOKENS
        if not _token_allowed(token, allowed, allow_haystack)
    ]
    facts = {
        "headline": "",
        "unit": user_facts.get("unit") or "",
        "unit_label": user_facts.get("unit_label") or "",
        "list_price": user_facts.get("list_price") or "",
        "discount": user_facts.get("discount") or "",
        "discount_label": "",
        "cta": "",
    }
    return QuickFactPolicy(
        verified=verified,
        user_provided=user_facts,
        creative_copy=(user_request or "").strip(),
        facts=facts,
        allowed_commercial_tokens=allowed,
        blocked_template_tokens=blocked,
    )


def _token_allowed(token: str, allowed: list[str], user_request: str) -> bool:
    folded_token = _fold(token)
    compact_token = _compact(token)
    hay = _fold(user_request)
    compact_hay = _compact(user_request)
    if folded_token and folded_token in hay:
        return True
    if compact_token and compact_token in compact_hay:
        return True
    for item in allowed:
        folded_item = _fold(item)
        compact_item = _compact(item)
        if folded_token and folded_token in folded_item:
            return True
        if compact_token and compact_item and compact_token in compact_item:
            return True
    return False


def quick_generation_prompt(
    *,
    user_request: str,
    policy: QuickFactPolicy,
    target_format: str,
    retry: bool = False,
    multi_photo_intent: bool | None = None,
    retry_guidance: str | None = None,
) -> str:
    verified_lines = [f"  {key}: {value}" for key, value in policy.verified.items() if value] or ["  (identity only — none beyond project name if unnamed)"]
    user_lines = [f"  {key}: {value}" for key, value in policy.user_provided.items() if value] or [
        "  none — do not invent commercial numbers to fill a layout"
    ]
    blocked = ", ".join(policy.blocked_template_tokens[:18]) or "(template commercial tokens)"
    multi = has_multi_photo_intent(user_request) if multi_photo_intent is None else bool(multi_photo_intent)
    if multi:
        photo_rules = [
            "MULTI-PHOTO INTENT: the user asked for more than one project photograph.",
            "You may combine only the approved project photos needed for that request.",
            "Do not invent additional buildings or scenes.",
        ]
    else:
        photo_rules = [
            "SINGLE HERO PHOTO (mandatory): IMAGE 1 is the ONE primary project photograph.",
            "It is the only project photo in this advertisement.",
            "Phrases like 'gerçek proje görsellerini kullan' mean use the approved project library.",
            "They do NOT mean collage, split-screen, photo strips, picture-in-picture, or stacking.",
            "Do not overlay one project photo over another. Do not blend two project photos into one scene.",
            "Do not duplicate the hero into multiple independent photo objects.",
            "You may crop, mask, grade, or place the hero in a designed image territory.",
            "Do not reconstruct architecture. Do not AI-extend architecture so the real project changes.",
        ]
    copy_lines = allowed_copy_package(policy, user_request)
    lines = [
        "You are the senior art director. Design ONE complete Instagram advertisement.",
        "The OS will not overlay HTML, Pillow templates, or coordinates except authentic approved logos after you finish.",
        "Create an ORIGINAL composition for the requested format. Do not recreate IMAGE 2 pixel-for-pixel.",
        "Do not copy IMAGE 2 coordinates, crop, building, logo, or campaign copy.",
        "",
        "INPUT ROLES (mandatory):",
        "IMAGE 1 = immutable factual project photography. This is the only real project shown.",
        "IMAGE 2 = visual design / art-direction reference ONLY (composition philosophy, hierarchy,",
        "typography character, spacing rhythm, image/text relationship, graphic restraint,",
        "negative space, visual balance, CTA treatment, editorial character).",
        "IMAGE 2 has ZERO factual authority and ZERO architecture authority.",
        "Do not show IMAGE 2 as a second photograph in the advertisement.",
        "Do not inherit IMAGE 2's building, interior, skyline, logo, project name, address, price,",
        "rent, percentage, ROI, unit type, delivery date, or commercial claims.",
        "Compose natively for the requested format. Do not force IMAGE 2's aspect ratio.",
        "",
        "ALLOWED COPY PACKAGE (the only text authority):",
        *[f"  {line}" for line in copy_lines],
        "",
        "FACT CLASSES (mandatory):",
        "VERIFIED PROJECT FACT — identity only; may appear:",
        *verified_lines,
        "USER-PROVIDED FACT — may appear exactly as given:",
        *user_lines,
        "CREATIVE COPY — mood and language from the user request. No invented numbers.",
        "UNVERIFIED COMMERCIAL FACT — forbidden. Remove that semantic element from the design.",
        "",
        "Never infer or invent: price, discount, return, rent, yield, ROI, completion date,",
        "unit type, unit count, square footage, launch-advantage percentage, financial benefit",
        "percentage, or payment terms.",
        "Do not insert placeholder numbers, sample numbers, or facts from another project.",
        "Never paint text that is visible on IMAGE 2 unless it also appears in the ALLOWED COPY PACKAGE.",
        f"Never paint these template/seed tokens unless they appear as USER-PROVIDED FACT: {blocked}.",
        "",
        "LOGO: DO NOT draw, recreate, imitate, typeset, or invent any project logo, Investhome logo, or wordmark.",
        "Do not paint The Temple, UniLoft, Investhome, or any other brand lockup.",
        "Leave the top-right ~20% width × 16% height empty — authentic PROJECT logo territory.",
        "Leave the bottom-left ~16% width × 10% height empty — quieter INVESTHOME brand-closure territory.",
        "The operating system will insert the authentic approved logo files afterward.",
        "Project identity is primary. Investhome is secondary endorsement, not an equal lockup.",
        "Do not place two painted marks together. Do not imitate either file.",
        "",
        "TEXT: Keep every headline, body line, and CTA inside an 8% safe margin on all edges.",
        "Never clip a word. Never show an incomplete visible word (forbidden example: 'ALIR KAZ...').",
        "If copy does not fit: first reduce line size within acceptable limits, then reflow,",
        "then shorten creative copy semantically. Never simply clip it.",
        "Do not overlap type with the reserved logo zone.",
        "",
        *photo_rules,
        "IMAGE 1 architecture is ground truth, not inspiration.",
        "Do not invent, beautify, or redraw the building. Crop or grade as needed.",
        f"Target format: {target_format}. Invent a native layout for this format.",
        "",
        f"USER REQUEST: {user_request}",
    ]
    if retry:
        guidance = (retry_guidance or "").strip() or (
            "Previous composition failed a recoverable visual safety check."
        )
        lines.extend(
            [
                "",
                "RETRY — generate a FRESH advertisement. Do not patch, edit, or reuse the previous raster.",
                guidance,
                "Preserve the same user intent, IMAGE 1 project photo, IMAGE 2 art-direction reference, format, and fact rules.",
                "Create a new composition with all text fully inside the 8% safe areas.",
                "Leave the top-right project-logo territory and the bottom-left Investhome territory empty of type and painted marks.",
                "DO NOT draw, recreate, imitate, typeset, or invent any project logo, Investhome logo, or wordmark.",
                "Use exactly one project photograph (IMAGE 1). IMAGE 2 is art direction, not a second hero.",
            ]
        )
    return "\n".join(lines)


def quick_revision_prompt(
    *,
    instruction: str,
    policy: QuickFactPolicy,
    retry: bool = False,
    retry_guidance: str | None = None,
) -> str:
    user_lines = [f"{key}={value}" for key, value in policy.user_provided.items() if value]
    allowed = " | ".join(user_lines) if user_lines else "none"
    blocked = ", ".join(policy.blocked_template_tokens[:18])
    lines = [
        "REVISION of an existing finished advertisement. You are editing, not redesigning.",
        "IMAGE 1 is the CURRENT creative. Treat it as the visual source of truth.",
        "IMAGE 2 is the approved project photograph (architecture reference only — not a second hero to collage).",
        "Keep a single project hero photograph unless the user explicitly asked for a multi-image composition.",
        "DO NOT draw, recreate, imitate, typeset, or invent any project logo, Investhome logo, or wordmark.",
        "Leave the top-right project-logo territory and the bottom-left Investhome closure territory empty.",
        "The operating system will insert the authentic approved logo files afterward.",
        "Do not copy buildings, logos, names, prices, or claims from any design-reference memory.",
        "",
        f"User instruction: {instruction}",
        f"USER-PROVIDED FACT still allowed: {allowed}.",
        "Do not invent price, discount, rent, ROI, unit type, unit count, or completion date.",
        f"Never paint template/seed tokens unless user-provided: {blocked}.",
        "Keep all type inside an 8% safe margin. Never clip a word. Never show incomplete words.",
        "Small generative drift is acceptable. A new advertisement is not.",
    ]
    if retry:
        guidance = (retry_guidance or "").strip() or (
            "Previous composition failed a recoverable visual safety check."
        )
        lines.extend(
            [
                "RETRY — generate a FRESH revision candidate. Do not patch or reuse the rejected raster.",
                guidance,
                "Keep the same user instruction, project photograph, fact rules, and single-hero policy.",
                "All type must sit fully inside the 8% safe margin. Do not paint any logo or wordmark.",
            ]
        )
    return "\n".join(lines)


def classify_approved_logo_variant(filename: str, tags: list[str] | None = None) -> str | None:
    """Map an approved logo file to primary/white/black. Never invents a treatment."""
    hay = _fold(" ".join([filename or "", *[str(tag) for tag in (tags or [])]]))
    if any(token in hay for token in ("addition", "historic")):
        return None
    if "logo" not in hay and "wordmark" not in hay and "lockup" not in hay:
        return None
    if "white" in hay:
        return "white"
    if "black" in hay:
        return "black"
    if "primary" in hay:
        return "primary"
    return None


def _crop_logo_mark(logo: Image.Image) -> Image.Image:
    mark = logo.convert("RGBA")
    bbox = mark.getbbox()
    if bbox:
        mark = mark.crop(bbox)
    if mark.width < 1 or mark.height < 1:
        raise ValueError("logo_unreadable")
    return mark


def _fit_logo_mark(mark: Image.Image, max_w: int, max_h: int) -> Image.Image:
    scale = min(max_w / mark.width, max_h / mark.height)
    nw = max(1, round(mark.width * scale))
    nh = max(1, round(mark.height * scale))
    if nw > max_w or nh > max_h:
        scale = min(max_w / mark.width, max_h / mark.height)
        nw = max(1, int(mark.width * scale))
        nh = max(1, int(mark.height * scale))
    return mark.resize((nw, nh), Image.Resampling.LANCZOS)


def _srgb_to_lin(channel: float) -> float:
    c = max(0.0, min(255.0, channel)) / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _rel_lum(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * _srgb_to_lin(r) + 0.7152 * _srgb_to_lin(g) + 0.0722 * _srgb_to_lin(b)


def _channel_luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    lighter, darker = max(_rel_lum(a), _rel_lum(b)), min(_rel_lum(a), _rel_lum(b))
    return (lighter + 0.05) / (darker + 0.05)


def _opaque_ink_rgb(logo: Image.Image) -> tuple[int, int, int]:
    mark = _crop_logo_mark(logo)
    sample = mark.copy()
    sample.thumbnail((96, 96), Image.Resampling.BOX)
    pixels = list(sample.getdata())
    ink = [px[:3] for px in pixels if (len(px) == 4 and px[3] >= 32) or len(px) == 3]
    if not ink:
        rgb = sample.convert("RGB").resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
        return (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    n = len(ink)
    return (
        int(round(sum(px[0] for px in ink) / n)),
        int(round(sum(px[1] for px in ink) / n)),
        int(round(sum(px[2] for px in ink) / n)),
    )


def _region_mean_rgb(image: Image.Image, x: int, y: int, w: int, h: int) -> tuple[int, int, int]:
    box = (
        max(0, x),
        max(0, y),
        min(image.width, x + max(1, w)),
        min(image.height, y + max(1, h)),
    )
    crop = image.convert("RGB").crop(box)
    rgb = crop.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))


def _rects_overlap(a: tuple[int, int, int, int], b: tuple[int, int, int, int], pad: int = 12) -> bool:
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def _box_rect(box: dict[str, int], pad: int = 0) -> tuple[int, int, int, int]:
    return (
        box["x"] - pad,
        box["y"] - pad,
        box["x"] + box["w"] + pad,
        box["y"] + box["h"] + pad,
    )


def select_approved_logo_variant(
    primary: Image.Image,
    variants: dict[str, Image.Image] | None,
    background_rgb: tuple[int, int, int],
) -> tuple[Image.Image, str, float]:
    """Pick an existing approved treatment. Never recolor or redraw."""
    available: dict[str, Image.Image] = {"primary": primary}
    for key in ("white", "black", "primary"):
        image = (variants or {}).get(key)
        if image is not None:
            available[key] = image
    bg_luma = _channel_luma(background_rgb)
    preferred = ("white", "primary", "black") if bg_luma < DARK_BACKGROUND_LUMA else ("black", "primary", "white")
    ranked: list[tuple[float, str, Image.Image]] = []
    for name in preferred:
        image = available.get(name)
        if image is None:
            continue
        contrast = contrast_ratio(_opaque_ink_rgb(image), background_rgb)
        ranked.append((contrast, name, image))
    passing = [row for row in ranked if row[0] >= MIN_LOGO_CONTRAST]
    chosen = passing[0] if passing else (ranked[0] if ranked else (0.0, "primary", primary))
    return chosen[2], chosen[1], float(chosen[0])


def composite_real_logo(
    canvas: Image.Image,
    logo: Image.Image,
    *,
    variants: dict[str, Image.Image] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    """Place the authentic project logo top-right. Preserve proportions. Do not redraw."""
    out = canvas.convert("RGBA")
    mark = _crop_logo_mark(logo)
    max_w = max(1, int(out.width * LOGO_MAX_WIDTH_RATIO))
    max_h = max(1, int(out.height * LOGO_MAX_HEIGHT_RATIO))
    probe = _fit_logo_mark(mark, max_w, max_h)
    margin_x = max(8, int(out.width * LOGO_MARGIN_X_RATIO))
    margin_y = max(8, int(out.height * LOGO_MARGIN_Y_RATIO))
    x = out.width - probe.width - margin_x
    y = margin_y
    if x < 0 or y < 0 or x + probe.width > out.width or y + probe.height > out.height:
        raise ValueError("logo_would_clip")
    bg = _region_mean_rgb(canvas, x, y, probe.width, probe.height)
    chosen, variant, contrast = select_approved_logo_variant(logo, variants, bg)
    mark = _fit_logo_mark(_crop_logo_mark(chosen), max_w, max_h)
    x = out.width - mark.width - margin_x
    y = margin_y
    if x < 0 or y < 0 or x + mark.width > out.width or y + mark.height > out.height:
        raise ValueError("logo_would_clip")
    out.alpha_composite(mark, (x, y))
    return out.convert("RGB"), {
        "x": x,
        "y": y,
        "w": mark.width,
        "h": mark.height,
        "variant": variant,
        "contrast": round(contrast, 3),
        "role": "project",
    }


def _region_std(image: Image.Image, x: int, y: int, w: int, h: int) -> float:
    box = (
        max(0, x),
        max(0, y),
        min(image.width, x + max(1, w)),
        min(image.height, y + max(1, h)),
    )
    return _luma_std(image.convert("RGB").crop(box))


def _brand_closure_plate_rgb(ink: tuple[int, int, int]) -> tuple[int, int, int]:
    """Solid backing that preserves authentic ink. Never recolors the mark."""
    if contrast_ratio(ink, BRAND_PLATE_DARK) >= MIN_LOGO_CONTRAST:
        return BRAND_PLATE_DARK
    if contrast_ratio(ink, BRAND_PLATE_LIGHT) >= MIN_LOGO_CONTRAST:
        return BRAND_PLATE_LIGHT
    return BRAND_PLATE_DARK


def _iter_brand_logo_slots(
    canvas_w: int,
    canvas_h: int,
    nw: int,
    nh: int,
    mx: int,
    my: int,
) -> list[tuple[int, int]]:
    slots: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    band_top = max(my, int(canvas_h * 0.62) - nh)
    y = canvas_h - nh - my
    step_y = max(6, nh // 3)
    step_x = max(6, nw // 3)
    x_limit = max(mx, canvas_w - nw - mx)
    while y >= band_top:
        x = mx
        while x <= x_limit:
            key = (x, y)
            if key not in seen:
                seen.add(key)
                slots.append(key)
            x += step_x
        y -= step_y
    for x_frac, y_frac in (
        (BRAND_LOGO_MARGIN_X_RATIO, BRAND_LOGO_MARGIN_Y_RATIO),
        (0.08, 0.07),
        (0.12, 0.06),
        (0.18, 0.08),
    ):
        x = max(mx, int(canvas_w * x_frac))
        y = canvas_h - nh - max(my, int(canvas_h * y_frac))
        key = (x, y)
        if key not in seen:
            seen.add(key)
            slots.append(key)
    return slots


def composite_brand_closure_logo(
    canvas: Image.Image,
    logo: Image.Image,
    *,
    variants: dict[str, Image.Image] | None = None,
    avoid_box: dict[str, int] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    """Place a quieter authentic Investhome mark. Contrast is an OS duty. Do not redraw."""
    rgb_canvas = canvas.convert("RGB")
    out = rgb_canvas.convert("RGBA")
    max_w = max(1, int(out.width * BRAND_LOGO_MAX_WIDTH_RATIO))
    max_h = max(1, int(out.height * BRAND_LOGO_MAX_HEIGHT_RATIO))
    probe = _fit_logo_mark(_crop_logo_mark(logo), max_w, max_h)
    mx = max(8, int(out.width * BRAND_LOGO_MARGIN_X_RATIO))
    my = max(8, int(out.height * BRAND_LOGO_MARGIN_Y_RATIO))
    avoid = _box_rect(avoid_box, pad=16) if avoid_box else None
    prepared: dict[str, Image.Image] = {"primary": probe}
    for key, image in (variants or {}).items():
        if image is None:
            continue
        prepared[str(key)] = _fit_logo_mark(_crop_logo_mark(image), max_w, max_h)
    ranked: list[tuple[float, float, int, int, Image.Image, str, float]] = []
    for sx, sy in _iter_brand_logo_slots(out.width, out.height, probe.width, probe.height, mx, my):
        if sx < 0 or sy < 0 or sx + probe.width > out.width or sy + probe.height > out.height:
            continue
        if avoid and _rects_overlap((sx, sy, sx + probe.width, sy + probe.height), avoid, pad=16):
            continue
        bg = _region_mean_rgb(rgb_canvas, sx, sy, probe.width, probe.height)
        chosen, variant, _probe_contrast = select_approved_logo_variant(probe, prepared, bg)
        mark = prepared.get(variant, probe)
        x = min(max(mx, sx), out.width - mark.width - mx)
        y = min(max(my, sy), out.height - mark.height - my)
        if x < 0 or y < 0 or x + mark.width > out.width or y + mark.height > out.height:
            continue
        if avoid and _rects_overlap((x, y, x + mark.width, y + mark.height), avoid, pad=16):
            continue
        local = _region_mean_rgb(rgb_canvas, x, y, mark.width, mark.height)
        contrast = contrast_ratio(_opaque_ink_rgb(chosen), local)
        uniformity = _region_std(rgb_canvas, x, y, mark.width, mark.height)
        ranked.append((contrast, -uniformity, x, y, mark, variant, uniformity))
    natural = [row for row in ranked if row[0] >= MIN_LOGO_CONTRAST]
    natural.sort(key=lambda row: (-row[0], row[6], row[2]))
    plate_used = False
    plate_rgb: tuple[int, int, int] | None = None
    if natural:
        contrast, _neg_std, x, y, mark, variant, _std = natural[0]
    else:
        if not ranked:
            raise ValueError("brand_logo_would_clip")
        ranked.sort(key=lambda row: (row[6], -row[0], row[2]))
        _c, _ns, x, y, mark, variant, _std = ranked[0]
        ink = _opaque_ink_rgb(mark)
        plate_rgb = _brand_closure_plate_rgb(ink)
        pad = max(6, int(min(out.width, out.height) * 0.012))
        px1, py1 = max(0, x - pad), max(0, y - pad)
        px2, py2 = min(out.width, x + mark.width + pad), min(out.height, y + mark.height + pad)
        if avoid and _rects_overlap((px1, py1, px2, py2), avoid, pad=8):
            x = mx
            y = out.height - mark.height - my
            px1, py1 = max(0, x - pad), max(0, y - pad)
            px2, py2 = min(out.width, x + mark.width + pad), min(out.height, y + mark.height + pad)
        draw = ImageDraw.Draw(out)
        radius = max(2, pad // 2)
        draw.rounded_rectangle([px1, py1, px2 - 1, py2 - 1], radius=radius, fill=(*plate_rgb, 255))
        plate_used = True
        contrast = contrast_ratio(ink, plate_rgb)
    background = out.convert("RGB")
    measured = contrast_ratio(
        _opaque_ink_rgb(mark),
        _region_mean_rgb(background, x, y, mark.width, mark.height),
    )
    if measured < MIN_LOGO_CONTRAST and not plate_used:
        ink = _opaque_ink_rgb(mark)
        plate_rgb = _brand_closure_plate_rgb(ink)
        pad = max(6, int(min(out.width, out.height) * 0.012))
        px1, py1 = max(0, x - pad), max(0, y - pad)
        px2, py2 = min(out.width, x + mark.width + pad), min(out.height, y + mark.height + pad)
        draw = ImageDraw.Draw(out)
        radius = max(2, pad // 2)
        draw.rounded_rectangle([px1, py1, px2 - 1, py2 - 1], radius=radius, fill=(*plate_rgb, 255))
        plate_used = True
        background = out.convert("RGB")
        measured = contrast_ratio(ink, _region_mean_rgb(background, x, y, mark.width, mark.height))
    out.alpha_composite(mark, (x, y))
    return out.convert("RGB"), {
        "x": x,
        "y": y,
        "w": mark.width,
        "h": mark.height,
        "variant": variant,
        "contrast": round(float(measured), 3),
        "role": "investhome",
        "plate": plate_used,
        "plate_rgb": plate_rgb,
        "natural_contrast": round(float(contrast), 3) if not plate_used else None,
    }


def detect_template_fact_leakage(ocr_text: str, *, allowed: list[str], user_request: str) -> list[str]:
    leaked: list[str] = []
    folded = _fold(ocr_text)
    compact = _compact(ocr_text)
    for token in SEED_TEMPLATE_COMMERCIAL_TOKENS:
        if _token_allowed(token, allowed, user_request):
            continue
        folded_token = _fold(token)
        compact_token = _compact(token)
        if (folded_token and folded_token in folded) or (compact_token and compact_token in compact):
            leaked.append(token)
    return leaked


def detect_reference_fact_leakage(ocr_text: str, *, allowed: list[str], user_request: str) -> list[str]:
    leaked: list[str] = []
    folded = _fold(ocr_text)
    compact = _compact(ocr_text)
    for token in REFERENCE_CAMPAIGN_LEAK_TOKENS:
        if _token_allowed(token, allowed, user_request):
            continue
        folded_token = _fold(token)
        compact_token = _compact(token)
        if (folded_token and folded_token in folded) or (compact_token and compact_token in compact):
            leaked.append(token)
    return leaked


def _project_name_tokens(project_name: str) -> list[str]:
    name = _fold(project_name or "")
    if not name:
        return []
    parts = [part for part in re.split(r"\s+", name) if len(part) >= 4]
    tokens = [name]
    tokens.extend(parts)
    return tokens


def detect_duplicate_project_logo(
    boxes: list[tuple[str, int, int, int, int]],
    *,
    project_name: str,
    logo_box: dict[str, int] | None,
    canvas_size: tuple[int, int],
) -> int:
    """Count project wordmarks. OS composite counts as 1; extras in the reserved zone fail."""
    if not logo_box:
        return 0
    w, h = canvas_size
    reserved = (
        int(w * (1.0 - RESERVED_LOGO_WIDTH_RATIO)),
        0,
        w,
        int(h * RESERVED_LOGO_HEIGHT_RATIO),
    )
    logo_rect = (
        logo_box["x"] - 8,
        logo_box["y"] - 8,
        logo_box["x"] + logo_box["w"] + 8,
        logo_box["y"] + logo_box["h"] + 8,
    )
    tokens = _project_name_tokens(project_name)
    extra = 0
    for word, left, top, width, height in boxes:
        folded = _fold(word)
        if not any(token == folded or token in folded for token in tokens):
            continue
        right, bottom = left + width, top + height
        inside_logo = left >= logo_rect[0] and top >= logo_rect[1] and right <= logo_rect[2] and bottom <= logo_rect[3]
        if inside_logo:
            continue
        in_reserved = left < reserved[2] and right > reserved[0] and top < reserved[3] and bottom > reserved[1]
        if in_reserved:
            extra += 1
    return 1 + extra


def detect_ai_generated_logo_count(
    boxes: list[tuple[str, int, int, int, int]],
    *,
    project_name: str,
    logo_box: dict[str, int] | None,
    brand_logo_box: dict[str, int] | None,
    canvas_size: tuple[int, int],
) -> int:
    """Count painted lockups in reserved logo territories that are not the authentic composites."""
    w, h = canvas_size
    project_reserved = (
        int(w * (1.0 - RESERVED_LOGO_WIDTH_RATIO)),
        0,
        w,
        int(h * RESERVED_LOGO_HEIGHT_RATIO),
    )
    brand_reserved = (
        0,
        int(h * (1.0 - RESERVED_BRAND_HEIGHT_RATIO)),
        int(w * RESERVED_BRAND_WIDTH_RATIO),
        h,
    )
    authentic: list[tuple[int, int, int, int]] = []
    if logo_box:
        authentic.append(_box_rect(logo_box, pad=8))
    if brand_logo_box:
        authentic.append(_box_rect(brand_logo_box, pad=8))
    tokens = _project_name_tokens(project_name) + ["investhome", "invest home"]
    extra = 0
    for word, left, top, width, height in boxes:
        folded = _fold(word)
        if not any(token == folded or token in folded for token in tokens):
            continue
        right, bottom = left + width, top + height
        if any(left >= ax and top >= ay and right <= ar and bottom <= ab for ax, ay, ar, ab in authentic):
            continue
        in_project = left < project_reserved[2] and right > project_reserved[0] and top < project_reserved[3] and bottom > project_reserved[1]
        in_brand = left < brand_reserved[2] and right > brand_reserved[0] and top < brand_reserved[3] and bottom > brand_reserved[1]
        if in_project or in_brand:
            extra += 1
    return extra


def detect_clipped_or_orphan_text(ocr_text: str) -> list[str]:
    reasons: list[str] = []
    raw = ocr_text or ""
    folded = _fold(raw)
    if "alir kaz" in folded and "alirken kazan" not in folded:
        reasons.append("clipped_headline_fragment")
    if _CLIP_RE.search(raw):
        reasons.append("ellipsis_or_hyphen_clip")
    return reasons


def _ocr_payload(image: Image.Image) -> tuple[str, list[tuple[str, int, int, int, int]], bool]:
    try:
        import pytesseract

        buf = io.BytesIO()
        image.save(buf, format="PNG")
        content = buf.getvalue()
        opened = Image.open(io.BytesIO(content))
        text = (pytesseract.image_to_string(opened) or "").strip()
        if "OCR placeholder" in text:
            return "", [], False
        data = pytesseract.image_to_data(opened, output_type=pytesseract.Output.DICT)
        boxes: list[tuple[str, int, int, int, int]] = []
        n = len(data.get("text") or [])
        for i in range(n):
            word = str(data["text"][i] or "").strip()
            if not word:
                continue
            try:
                conf = float(data.get("conf", ["-1"])[i])
            except (TypeError, ValueError, IndexError):
                conf = -1
            if conf >= 0 and conf < 30:
                continue
            boxes.append(
                (
                    word,
                    int(data["left"][i]),
                    int(data["top"][i]),
                    int(data["width"][i]),
                    int(data["height"][i]),
                )
            )
        return text, boxes, True
    except Exception:
        logger.info("Quick Creative OCR unavailable", exc_info=True)
        return "", [], False


def evaluate_quick_composition(
    image: Image.Image,
    *,
    policy: QuickFactPolicy,
    user_request: str,
    logo_box: dict[str, int] | None,
    photo_valid: bool,
    logo_valid: bool,
    multi_photo_intent: bool = False,
    brand_logo_box: dict[str, int] | None = None,
    brand_logo_valid: bool = False,
    brand_logo_available: bool = False,
    project_logo_contrast: float | None = None,
    brand_logo_contrast: float | None = None,
    hero_photo_provenance: int | None = None,
) -> dict[str, Any]:
    ocr_text, boxes, ocr_executed = _ocr_payload(image)
    leaked = detect_template_fact_leakage(ocr_text, allowed=policy.allowed_commercial_tokens, user_request=user_request) if ocr_text else []
    reference_leaked = detect_reference_fact_leakage(ocr_text, allowed=policy.allowed_commercial_tokens, user_request=user_request) if ocr_text else []
    clip_reasons = detect_clipped_or_orphan_text(ocr_text) if ocr_text else []
    text_bounds_ok = True
    overlap_ok = True
    protected_rects: list[tuple[int, int, int, int]] = []
    if logo_box:
        protected_rects.append(_box_rect(logo_box, pad=8))
    if brand_logo_box:
        protected_rects.append(_box_rect(brand_logo_box, pad=8))

    def _is_logo_wordmark(left: int, top: int, width: int, height: int) -> bool:
        right, bottom = left + width, top + height
        return any(left >= ax and top >= ay and right <= ar and bottom <= ab for ax, ay, ar, ab in protected_rects)

    def _hits_logo(left: int, top: int, width: int, height: int) -> bool:
        right, bottom = left + width, top + height
        return any(left < ar and right > ax and top < ab and bottom > ay for ax, ay, ar, ab in protected_rects)

    if boxes:
        w, h = image.size
        mx, my = int(w * SAFE_MARGIN), int(h * SAFE_MARGIN)
        for _word, left, top, width, height in boxes:
            if _is_logo_wordmark(left, top, width, height):
                continue
            right, bottom = left + width, top + height
            if left < mx or top < my or right > w - mx or bottom > h - my:
                text_bounds_ok = False
                break
        for _word, left, top, width, height in boxes:
            if _is_logo_wordmark(left, top, width, height):
                continue
            if _hits_logo(left, top, width, height):
                overlap_ok = False
                break
    ocr_available = ocr_executed and bool(ocr_text.strip())
    clipped = bool(clip_reasons)
    visual_hero_count = estimate_project_hero_photo_count(image)
    provenance = 1 if hero_photo_provenance is None and not multi_photo_intent else hero_photo_provenance
    hero_count = resolve_project_hero_photo_count(
        image,
        provenance_count=provenance,
        multi_photo_intent=multi_photo_intent,
    )
    hero_ok = True if multi_photo_intent else hero_count == 1
    logo_count = 1 if logo_valid and logo_box else 0
    project_name = str(policy.verified.get("name") or "")
    if ocr_available and logo_box:
        logo_count = detect_duplicate_project_logo(
            boxes,
            project_name=project_name,
            logo_box=logo_box,
            canvas_size=image.size,
        )
    project_visible = bool(logo_valid and logo_box)
    if project_logo_contrast is not None:
        project_visible = project_visible and project_logo_contrast >= MIN_LOGO_CONTRAST
    brand_count = 1 if brand_logo_available and brand_logo_valid and brand_logo_box else 0
    brand_visible = bool(brand_logo_available and brand_logo_valid and brand_logo_box)
    if brand_logo_contrast is not None:
        brand_visible = brand_visible and brand_logo_contrast >= MIN_LOGO_CONTRAST
    ai_logo_count = 0
    if ocr_available:
        ai_logo_count = detect_ai_generated_logo_count(
            boxes,
            project_name=project_name,
            logo_box=logo_box,
            brand_logo_box=brand_logo_box,
            canvas_size=image.size,
        )
        if logo_count > 1:
            ai_logo_count = max(ai_logo_count, logo_count - 1)
    checks = {
        "LOGO_VISIBLE": "pass" if project_visible else "fail",
        "TEXT_WITHIN_SAFE_BOUNDS": "pass" if (text_bounds_ok if ocr_available else True) else "fail",
        "NO_CRITICAL_TEXT_OVERLAP": "pass" if (overlap_ok if ocr_available else True) else "fail",
        "NO_ORPHAN_TEXT": "fail" if ocr_available and clipped else "pass",
        "NO_TEMPLATE_FACT_LEAKAGE": "pass" if not leaked else "fail",
        "NO_REFERENCE_FACT_LEAKAGE": "pass" if not reference_leaked else "fail",
        "PROJECT_PHOTO_VALID": "pass" if photo_valid else "fail",
        "PROJECT_LOGO_VALID": "pass" if logo_valid else "fail",
        "PROJECT_HERO_PHOTO_COUNT": "pass" if hero_ok else "fail",
        "PROJECT_LOGO_COUNT": "pass" if logo_count == 1 else "fail",
        "PROJECT_LOGO_VISIBILITY": "pass" if project_visible else "fail",
        "INVESTHOME_LOGO_COUNT": (
            "pass" if brand_count == 1 else "fail"
        ) if brand_logo_available else "n/a",
        "BRAND_LOGO_VISIBILITY": (
            "pass" if brand_visible else "fail"
        ) if brand_logo_available else "n/a",
        "AI_GENERATED_LOGO_COUNT": "pass" if (ai_logo_count == 0 if ocr_available else True) else "fail",
    }
    if not ocr_executed:
        for key in OCR_DEPENDENT_CHECKS:
            if checks[key] != "fail":
                checks[key] = "unverified"
        checks["PROJECT_LOGO_COUNT"] = "pass" if logo_valid and logo_box else "fail"
    failed = [key for key, value in checks.items() if value == "fail"]
    unverified = [key for key, value in checks.items() if value == "unverified"]
    return {
        "status": "fail" if failed else "pass",
        "checks": checks,
        "failed": failed,
        "unverified": unverified,
        "leaked_tokens": leaked,
        "reference_leaked_tokens": reference_leaked,
        "clip_reasons": clip_reasons,
        "ocr_available": ocr_available,
        "ocr_executed": ocr_executed,
        "ocr_excerpt": (ocr_text or "")[:400],
        "logo_box": logo_box,
        "brand_logo_box": brand_logo_box,
        "hero_photo_count": hero_count,
        "hero_photo_count_visual": visual_hero_count,
        "hero_photo_provenance": provenance,
        "project_logo_count": logo_count,
        "investhome_logo_count": brand_count,
        "ai_generated_logo_count": ai_logo_count,
        "multi_photo_intent": bool(multi_photo_intent),
        "project_logo_contrast": project_logo_contrast,
        "brand_logo_contrast": brand_logo_contrast,
        "brand_logo_available": bool(brand_logo_available),
    }


def apply_quick_production_pass(
    image: Image.Image,
    logo: Image.Image | None,
    *,
    policy: QuickFactPolicy,
    user_request: str,
    photo_valid: bool,
    multi_photo_intent: bool = False,
    project_logo_variants: dict[str, Image.Image] | None = None,
    brand_logo: Image.Image | None = None,
    brand_logo_variants: dict[str, Image.Image] | None = None,
    hero_photo_provenance: int | None = None,
) -> dict[str, Any]:
    logo_valid = logo is not None
    logo_box = None
    brand_logo_box = None
    brand_logo_valid = False
    brand_available = brand_logo is not None
    project_contrast = None
    brand_contrast = None
    composed = image.convert("RGB")
    changed = False
    if logo is not None:
        try:
            composed, logo_box = composite_real_logo(composed, logo, variants=project_logo_variants)
            changed = True
            logo_valid = True
            project_contrast = float(logo_box.get("contrast") or 0.0)
        except Exception:
            logger.info("Quick Creative logo composite failed", exc_info=True)
            logo_valid = False
            logo_box = None
    if brand_logo is not None:
        try:
            composed, brand_logo_box = composite_brand_closure_logo(
                composed,
                brand_logo,
                variants=brand_logo_variants,
                avoid_box=logo_box,
            )
            changed = True
            brand_logo_valid = True
            brand_contrast = float(brand_logo_box.get("contrast") or 0.0)
        except Exception:
            logger.info("Quick Creative Investhome logo composite failed", exc_info=True)
            brand_logo_valid = False
            brand_logo_box = None
    pack = evaluate_quick_composition(
        composed,
        policy=policy,
        user_request=user_request,
        logo_box=logo_box,
        photo_valid=photo_valid,
        logo_valid=logo_valid,
        multi_photo_intent=multi_photo_intent,
        brand_logo_box=brand_logo_box,
        brand_logo_valid=brand_logo_valid,
        brand_logo_available=brand_available,
        project_logo_contrast=project_contrast,
        brand_logo_contrast=brand_contrast,
        hero_photo_provenance=1 if hero_photo_provenance is None and not multi_photo_intent else hero_photo_provenance,
    )
    pack["image"] = composed
    pack["changed"] = changed
    pack["passed"] = pack["status"] == "pass"
    return pack
