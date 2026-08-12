"""Locale-aware metric formatting + language consistency for generated creatives.

Output language governs display. UI chrome may stay Turkish; the advertisement
itself must not mix languages unless the user asked for it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Literal

LocaleCode = Literal["en", "tr"]

# Turkish fragments that must not leak into an English creative.
# Word-boundary checked; "May" / "day" / "pay" are not matches for "ay".
EN_FORBIDDEN_TR_FRAGMENTS = (
    "ay",
    "ayı",
    "ayi",
    "yıl",
    "yil",
    "yatırım",
    "yatirim",
    "getiri",
    "detaylar",
    "incele",
)

TR_FORBIDDEN_EN_DURATION = ("months", "month")

_LABELS: dict[str, dict[str, str]] = {
    "minimum_investment": {"en": "Minimum Investment", "tr": "Minimum Yatırım"},
    "target_return": {"en": "Target Return", "tr": "Hedef Getiri"},
    "target_yield": {"en": "Target Yield", "tr": "Hedef Getiri"},
    "investment_period": {"en": "Investment Period", "tr": "Yatırım Süresi"},
    "price": {"en": "Price", "tr": "Fiyat"},
    "count": {"en": "Count", "tr": "Adet"},
    "generic": {"en": "Figure", "tr": "Rakam"},
}

_UNITS: dict[str, dict[str, str]] = {
    "months": {"en": "Months", "tr": "Ay"},
    "years": {"en": "Years", "tr": "Yıl"},
}

INVESTMENT_CTA_POOL: dict[str, tuple[str, ...]] = {
    "en": (
        "Explore the Investment",
        "View Investment Details",
        "Request Investment Information",
        "Speak With Our Investment Team",
    ),
    "tr": (
        "Yatırımı İncele",
        "Yatırım Detaylarını Gör",
        "Yatırım Bilgisi İste",
        "Yatırım Ekibiyle Görüşün",
    ),
}


def normalize_locale(language: str | None) -> LocaleCode:
    lang = (language or "").strip().lower()
    if lang.startswith("tr"):
        return "tr"
    return "en"


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def localized_metric_label(key: str, locale: str) -> str:
    loc = normalize_locale(locale)
    row = _LABELS.get(key) or _LABELS["generic"]
    return row.get(loc) or row["en"]


def localized_unit(key: str, locale: str) -> str:
    loc = normalize_locale(locale)
    row = _UNITS.get(key) or {"en": key, "tr": key}
    return row.get(loc) or row["en"]


def format_percentage(raw_value: int | float | str, locale: str) -> str:
    loc = normalize_locale(locale)
    try:
        n = float(raw_value)
    except (TypeError, ValueError):
        token = str(raw_value).strip()
        return token
    if n.is_integer():
        shown = str(int(n))
    else:
        shown = f"{n:g}"
    if loc == "tr":
        return f"%{shown}"
    return f"{shown}%"


def format_duration(raw_value: int | float | str, locale: str) -> str:
    loc = normalize_locale(locale)
    try:
        n = float(raw_value)
    except (TypeError, ValueError):
        return str(raw_value).strip()
    count = int(n) if n.is_integer() else n
    unit = localized_unit("months", loc)
    if loc == "en" and isinstance(count, int) and count == 1:
        unit = "Month"
    return f"{count} {unit}"


def format_currency(
    raw_value: int | float | str,
    locale: str,
    *,
    compact: bool = False,
) -> str:
    loc = normalize_locale(locale)
    try:
        n = float(raw_value)
    except (TypeError, ValueError):
        return str(raw_value).strip()
    amount = int(n) if n.is_integer() else n
    if compact and isinstance(amount, int) and amount >= 1000 and amount % 1000 == 0:
        if amount >= 1_000_000 and amount % 1_000_000 == 0:
            millions = amount // 1_000_000
            return f"${millions}M"
        thousands = amount // 1000
        return f"${thousands}K"
    if isinstance(amount, float):
        whole = f"{amount:,.2f}"
    else:
        whole = f"{amount:,}"
    if loc == "tr":
        whole = whole.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"${whole}"


def format_metric_display(
    *,
    metric_type: str,
    raw_value: int | float | str,
    locale: str,
    compact_currency: bool = False,
) -> str:
    if metric_type in {"percentage", "return", "yield"}:
        return format_percentage(raw_value, locale)
    if metric_type == "duration":
        return format_duration(raw_value, locale)
    if metric_type in {"currency", "price"}:
        return format_currency(raw_value, locale, compact=compact_currency)
    if metric_type == "count":
        try:
            n = float(raw_value)
            return str(int(n) if n.is_integer() else n)
        except (TypeError, ValueError):
            return str(raw_value)
    return str(raw_value)


def choose_investment_cta(locale: str, *, angle: str | None = None) -> str:
    """Objective-matched CTA from a pool — not one hardcoded global string."""
    loc = normalize_locale(locale)
    pool = INVESTMENT_CTA_POOL[loc]
    key = _norm(angle or "")
    if any(k in key for k in ("detail", "information", "bilgi")):
        return pool[1] if loc == "en" else pool[1]
    if any(k in key for k in ("team", "speak", "ekip", "gorus")):
        return pool[3]
    if any(k in key for k in ("request", "iste")):
        return pool[2]
    return pool[0]


def project_identity_lines(
    *,
    project_name: str,
    city: str = "",
    country: str = "",
    locale: str = "en",
) -> tuple[str, str]:
    """Restrained identifier from verified project data — never hardcoded globally."""
    name = (project_name or "").strip()
    if not name:
        return "", ""
    ident = name.upper() if len(name) <= 28 else name
    place_bits: list[str] = []
    city_s = (city or "").strip()
    country_s = (country or "").strip()
    if city_s:
        place_bits.append(city_s.upper() if len(city_s) <= 18 else city_s)
    if country_s and country_s.upper() in {"US", "USA", "UNITED STATES"} and city_s:
        if "DC" not in city_s.upper() and "WASHINGTON" in city_s.upper():
            place_bits[-1] = f"{place_bits[-1]}, DC" if "DC" not in place_bits[-1] else place_bits[-1]
        elif country_s.upper() in {"US", "USA"} and "DC" not in (place_bits[-1] if place_bits else ""):
            pass
    place = ", ".join(place_bits)
    _ = locale
    return ident, place


@dataclass
class LanguageIssue:
    field: str
    fragment: str
    text: str


@dataclass
class LanguageReport:
    passed: bool
    issues: list[LanguageIssue] = field(default_factory=list)


def _token_hits(text: str, fragments: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    src = text or ""
    for frag in fragments:
        if not frag:
            continue
        if re.search(rf"(?<![a-zA-ZçğıöşüÇĞİÖŞÜ]){re.escape(frag)}(?![a-zA-ZçğıöşüÇĞİÖŞÜ])", src, re.I):
            hits.append(frag)
    return hits


def collect_visible_creative_strings(
    *,
    eyebrow: str = "",
    headline: str = "",
    supporting: str = "",
    cta: str = "",
    badges: list[str] | None = None,
    captions: list[str] | None = None,
    metric_labels: list[str] | None = None,
    metric_displays: list[str] | None = None,
    metric_units: list[str] | None = None,
) -> dict[str, str]:
    fields: dict[str, str] = {
        "eyebrow": eyebrow or "",
        "headline": headline or "",
        "support": supporting or "",
        "cta": cta or "",
    }
    for i, val in enumerate(badges or []):
        fields[f"badge_{i}"] = val or ""
    for i, val in enumerate(captions or []):
        fields[f"caption_{i}"] = val or ""
    for i, val in enumerate(metric_labels or []):
        fields[f"metric_label_{i}"] = val or ""
    for i, val in enumerate(metric_displays or []):
        fields[f"metric_display_{i}"] = val or ""
    for i, val in enumerate(metric_units or []):
        fields[f"metric_unit_{i}"] = val or ""
    return fields


def validate_creative_language(
    *,
    language: str,
    fields: dict[str, str],
) -> LanguageReport:
    loc = normalize_locale(language)
    issues: list[LanguageIssue] = []
    for field_name, text in fields.items():
        if not (text or "").strip():
            continue
        if loc == "en":
            for frag in _token_hits(text, EN_FORBIDDEN_TR_FRAGMENTS):
                issues.append(LanguageIssue(field=field_name, fragment=frag, text=text))
            # EN must not keep TR percent prefix "%14"
            if re.search(r"%\s*\d", text) and not re.search(r"\d\s*%", text):
                if any(k in field_name for k in ("headline", "support", "metric_display", "cta", "eyebrow")):
                    issues.append(LanguageIssue(field=field_name, fragment="%n", text=text))
        elif loc == "tr":
            for frag in _token_hits(text, TR_FORBIDDEN_EN_DURATION):
                issues.append(LanguageIssue(field=field_name, fragment=frag, text=text))
    return LanguageReport(passed=not issues, issues=issues)


def looks_like_concatenated_metrics(text: str) -> bool:
    src = (text or "").strip()
    if " · " not in src and " • " not in src:
        return False
    parts = re.split(r"\s*[·•]\s*", src)
    if len(parts) < 2:
        return False
    numericish = 0
    for part in parts:
        if re.search(r"[\d%$]", part):
            numericish += 1
    return numericish >= 2


def repair_language_leaks(text: str, *, language: str) -> str:
    """Best-effort localization of leaked duration/percent fragments. Does not change raw numbers."""
    loc = normalize_locale(language)
    out = text or ""
    if loc == "en":
        out = re.sub(r"\b(\d+)\s*ayı?\b", r"\1 Months", out, flags=re.I)
        out = re.sub(r"\b(\d+)\s*yıl\b", r"\1 Years", out, flags=re.I)
        out = re.sub(r"%\s*(\d+(?:[.,]\d+)?)", r"\1%", out)
    elif loc == "tr":
        out = re.sub(r"\b(\d+)\s*months?\b", r"\1 Ay", out, flags=re.I)
        out = re.sub(r"\b(\d+(?:[.,]\d+)?)\s*%", r"%\1", out)
    return re.sub(r"\s{2,}", " ", out).strip()


def visible_fields_from_package(package: Any, metrics: list[Any] | None = None) -> dict[str, str]:
    labels = [getattr(m, "label", "") for m in (metrics or [])]
    displays = [getattr(m, "display_value", "") for m in (metrics or [])]
    units = [getattr(m, "unit", "") for m in (metrics or [])]
    return collect_visible_creative_strings(
        eyebrow=getattr(package, "eyebrow", "") or "",
        headline=getattr(package, "headline", "") or "",
        supporting=getattr(package, "supporting_text", None)
        or getattr(package, "supporting_copy", "")
        or "",
        cta=getattr(package, "cta", "") or "",
        metric_labels=labels,
        metric_displays=displays,
        metric_units=units,
    )
