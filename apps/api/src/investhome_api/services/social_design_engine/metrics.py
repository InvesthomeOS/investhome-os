"""Structured campaign metrics — VALUE + MEANING, never concatenated text.

Campaign facts stay user-supplied source tokens. This module maps them to
semantic metrics with immutable raw_value and localized display_value.
Campaign figures are never promoted to canonical project/RAG data.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from investhome_api.services.social_design_engine.generation import CampaignFact

MetricType = Literal[
    "currency",
    "percentage",
    "duration",
    "count",
    "yield",
    "return",
    "price",
    "generic_numeric",
]
MetricEmphasis = Literal["primary", "secondary", "tertiary"]
MetricGroupLayout = Literal["horizontal", "stacked", "cards"]

METRIC_TYPES: frozenset[str] = frozenset(
    {
        "currency",
        "percentage",
        "duration",
        "count",
        "yield",
        "return",
        "price",
        "generic_numeric",
    }
)
METRIC_LAYOUTS: frozenset[str] = frozenset({"horizontal", "stacked", "cards"})
MAX_CAMPAIGN_METRICS = 3

_KIND_TO_TYPE: dict[str, MetricType] = {
    "money": "currency",
    "percent": "percentage",
    "duration": "duration",
}


@dataclass
class StructuredMetric:
    """One campaign figure with semantic meaning. raw_value is immutable."""

    id: str
    type: MetricType
    raw_value: int | float | str
    display_value: str
    label: str
    unit: str
    locale: str
    emphasis: MetricEmphasis = "secondary"
    source_token: str = ""


@dataclass
class MetricGroup:
    layout: MetricGroupLayout = "horizontal"
    metrics: list[StructuredMetric] = field(default_factory=list)


def _norm(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return folded.strip().lower()


def parse_raw_numeric(token: str, kind: str) -> int | float | str:
    """Extract the user-provided numeric payload without rewriting it."""
    raw = (token or "").strip()
    if not raw:
        return ""
    if kind == "money":
        compact = re.search(r"([\d]+(?:[.,]\d+)?)\s*(k|m|mn|million)\b", raw, re.I)
        if compact:
            n = compact.group(1).replace(",", "")
            try:
                base = float(n) if "." in n else int(n)
            except ValueError:
                return raw
            suffix = compact.group(2).lower()
            factor = 1_000_000 if suffix in {"m", "mn", "million"} else 1_000
            value = base * factor
            return int(value) if float(value).is_integer() else value
        digits = re.sub(r"[^\d]", "", raw)
        if digits:
            try:
                return int(digits)
            except ValueError:
                return raw
        return raw
    if kind in {"percent", "duration"}:
        m = re.search(r"(\d+(?:[.,]\d+)?)", raw)
        if not m:
            return raw
        n = m.group(1).replace(",", ".")
        try:
            value = float(n) if "." in n else int(n)
        except ValueError:
            return raw
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return value
    m = re.search(r"(\d+(?:[.,]\d+)?)", raw)
    if not m:
        return raw
    n = m.group(1).replace(",", ".")
    try:
        value = float(n) if "." in n else int(n)
    except ValueError:
        return raw
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _window_around(instruction: str, token: str, radius: int = 48) -> str:
    src = instruction or ""
    idx = src.find(token)
    if idx < 0:
        idx = _norm(src).find(_norm(token))
        if idx < 0:
            return src
    start = max(0, idx - radius)
    end = min(len(src), idx + len(token) + radius)
    return src[start:end]


def infer_metric_type(kind: str, instruction: str, token: str) -> MetricType:
    window = _norm(_window_around(instruction, token))
    if kind == "money":
        if any(k in window for k in ("price", "fiyat", "from", "starting")):
            return "price"
        return "currency"
    if kind == "percent":
        if any(k in window for k in ("yield", "getiri orani", "net yield")):
            return "yield"
        if any(k in window for k in ("getiri", "return", "roi", "hedef")):
            return "return"
        return "percentage"
    if kind == "duration":
        return "duration"
    if kind == "count":
        return "count"
    return "generic_numeric"


def infer_metric_label(*, kind: str, metric_type: MetricType, instruction: str, token: str, locale: str) -> str:
    from investhome_api.services.social_design_engine.localization import localized_metric_label

    window = _norm(_window_around(instruction, token))
    key = "generic"
    if kind == "money" or metric_type in {"currency", "price"}:
        if any(k in window for k in ("minimum", "min ", "min.", "asgari")):
            key = "minimum_investment"
        elif metric_type == "price":
            key = "price"
        else:
            key = "minimum_investment"
    elif kind == "percent" or metric_type in {"percentage", "return", "yield"}:
        if metric_type == "yield" or "yield" in window:
            key = "target_yield"
        else:
            key = "target_return"
    elif kind == "duration" or metric_type == "duration":
        key = "investment_period"
    elif metric_type == "count":
        key = "count"
    return localized_metric_label(key, locale)


def infer_unit(metric_type: MetricType, locale: str) -> str:
    from investhome_api.services.social_design_engine.localization import localized_unit

    if metric_type in {"currency", "price"}:
        return "USD"
    if metric_type in {"percentage", "return", "yield"}:
        return "%"
    if metric_type == "duration":
        return localized_unit("months", locale)
    return ""


def campaign_facts_to_structured_metrics(
    facts: list[CampaignFact],
    *,
    language: str,
    instruction: str = "",
    compact_currency: bool = False,
) -> list[StructuredMetric]:
    """Map user-supplied campaign facts → semantic metrics. Never invent figures."""
    from investhome_api.services.social_design_engine.localization import (
        format_metric_display,
        normalize_locale,
    )

    locale = normalize_locale(language)
    metrics: list[StructuredMetric] = []
    seen_raw: set[tuple[str, str]] = set()
    for index, fact in enumerate(facts or []):
        if len(metrics) >= MAX_CAMPAIGN_METRICS:
            break
        token = (fact.display or "").strip()
        if not token:
            continue
        metric_type = infer_metric_type(fact.kind, instruction, token)
        raw_value = parse_raw_numeric(token, fact.kind)
        key = (metric_type, str(raw_value))
        if key in seen_raw:
            continue
        seen_raw.add(key)
        label = infer_metric_label(
            kind=fact.kind,
            metric_type=metric_type,
            instruction=instruction,
            token=token,
            locale=locale,
        )
        unit = infer_unit(metric_type, locale)
        display = format_metric_display(
            metric_type=metric_type,
            raw_value=raw_value,
            locale=locale,
            compact_currency=compact_currency,
        )
        emphasis: MetricEmphasis = "primary" if index == 0 else "secondary" if index == 1 else "tertiary"
        metrics.append(
            StructuredMetric(
                id=f"metric-{index + 1}-{metric_type}",
                type=metric_type,
                raw_value=raw_value,
                display_value=display,
                label=label,
                unit=unit,
                locale=locale,
                emphasis=emphasis,
                source_token=token,
            )
        )
    return metrics


def structured_metrics_to_dicts(metrics: list[StructuredMetric]) -> list[dict[str, Any]]:
    return [asdict(m) for m in metrics]


def structured_metrics_from_dicts(rows: list[Any] | None) -> list[StructuredMetric]:
    out: list[StructuredMetric] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        mtype = str(row.get("type") or "generic_numeric")
        if mtype not in METRIC_TYPES:
            mtype = "generic_numeric"
        emphasis = str(row.get("emphasis") or "secondary")
        if emphasis not in {"primary", "secondary", "tertiary"}:
            emphasis = "secondary"
        raw = row.get("raw_value")
        if isinstance(raw, bool) or raw is None:
            continue
        if not isinstance(raw, (int, float, str)):
            continue
        out.append(
            StructuredMetric(
                id=str(row.get("id") or f"metric-{len(out) + 1}"),
                type=mtype,  # type: ignore[arg-type]
                raw_value=raw,
                display_value=str(row.get("display_value") or ""),
                label=str(row.get("label") or ""),
                unit=str(row.get("unit") or ""),
                locale=str(row.get("locale") or "en"),
                emphasis=emphasis,  # type: ignore[arg-type]
                source_token=str(row.get("source_token") or ""),
            )
        )
    return out[:MAX_CAMPAIGN_METRICS]


def metric_group_to_dict(group: MetricGroup) -> dict[str, Any]:
    layout = group.layout if group.layout in METRIC_LAYOUTS else "horizontal"
    return {
        "layout": layout,
        "metrics": structured_metrics_to_dicts(group.metrics),
    }


def raw_values_unchanged(original: list[StructuredMetric], current: list[StructuredMetric]) -> bool:
    """Financial safety: never silently rewrite 500000 / 14 / 24."""
    if len(original) != len(current):
        return False
    for a, b in zip(original, current, strict=True):
        if a.raw_value != b.raw_value:
            return False
        if a.type != b.type:
            return False
    return True


def apply_compact_currency(metrics: list[StructuredMetric], *, compact: bool) -> list[StructuredMetric]:
    from investhome_api.services.social_design_engine.localization import format_metric_display

    next_metrics: list[StructuredMetric] = []
    for metric in metrics:
        if metric.type in {"currency", "price"}:
            display = format_metric_display(
                metric_type=metric.type,
                raw_value=metric.raw_value,
                locale=metric.locale,
                compact_currency=compact,
            )
            next_metrics.append(
                StructuredMetric(
                    id=metric.id,
                    type=metric.type,
                    raw_value=metric.raw_value,
                    display_value=display,
                    label=metric.label,
                    unit=metric.unit,
                    locale=metric.locale,
                    emphasis=metric.emphasis,
                    source_token=metric.source_token,
                )
            )
        else:
            next_metrics.append(metric)
    return next_metrics


def choose_metric_group_layout(
    *,
    metrics: list[StructuredMetric],
    format_preset: str,
    canvas_w: int,
    available_width: int,
    requested: MetricGroupLayout | None = None,
    family: str | None = None,
) -> MetricGroupLayout:
    """CD may request a layout; Layout Intelligence may fall back if it does not fit.

    Fallback order for horizontal requests:
    horizontal (comfortable) → compact horizontal → cards → stacked.
    Compact is still persisted as ``horizontal`` (density is a render concern).
    Three metrics on a square are not always a horizontal row.
    """
    fam = str(family or "").upper()
    if requested in METRIC_LAYOUTS:
        preferred: MetricGroupLayout = requested
    elif fam in {"INVESTMENT_GRID", "LOWER_THIRD"} and len(metrics) >= 3 and format_preset == "square":
        preferred = "cards"
    elif fam in {"SPLIT_LAYOUT"} and len(metrics) >= 2:
        preferred = "stacked"
    elif fam == "FLOATING_DATA":
        preferred = "horizontal" if len(metrics) <= 2 else "cards"
    elif len(metrics) <= 1:
        preferred = "stacked"
    elif format_preset == "square" and len(metrics) <= 3:
        preferred = "horizontal"
    elif len(metrics) >= 3:
        preferred = "cards"
    else:
        preferred = "horizontal"
    if preferred != "horizontal":
        return preferred
    if horizontal_metrics_fit(metrics, available_width, canvas_w, density="comfortable"):
        return "horizontal"
    if horizontal_metrics_fit(metrics, available_width, canvas_w, density="compact"):
        return "horizontal"
    return "stacked" if len(metrics) <= 2 else "cards"


def horizontal_metrics_fit(
    metrics: list[StructuredMetric],
    available_width: int,
    canvas_w: int,
    *,
    density: str = "comfortable",
) -> bool:
    """True when all values can sit on one line in equal columns after safe font shrink."""
    if not metrics:
        return True
    n = max(1, len(metrics))
    compact = density == "compact"
    gutter = max(6 if compact else 12, int(round(available_width * (0.012 if compact else 0.018))))
    pad_x = 4 if compact else 8
    col_w = int((available_width - gutter * max(0, n - 1)) / n) if available_width else 0
    min_col = max(72 if compact else 96, int(round(canvas_w * (0.11 if compact else 0.14))))
    if col_w < min_col:
        return False
    inner = max(8, col_w - pad_x * 2)
    # Preferred value size mirrors client (~0.38 of typical group height on square).
    group_h = max(96, int(round(canvas_w * 0.14)))
    preferred = max(16 if compact else 18, int(round(group_h * (0.32 if compact else 0.38))))
    min_font = max(13, int(round(preferred * 0.65)))
    char_ratio = 0.66
    for font in range(preferred, min_font - 1, -1):
        if all(int(round(len((m.display_value or "").strip()) * font * char_ratio)) <= inner for m in metrics):
            return True
    return False


def update_metric_raw_value(metric: StructuredMetric, new_raw: int | float | str) -> StructuredMetric:
    """Explicit user command only — factual content change, not a silent rewrite."""
    from investhome_api.services.social_design_engine.localization import format_metric_display

    display = format_metric_display(
        metric_type=metric.type,
        raw_value=new_raw,
        locale=metric.locale,
        compact_currency="$K" in (metric.display_value or "") or "K" in (metric.display_value or ""),
    )
    return StructuredMetric(
        id=metric.id,
        type=metric.type,
        raw_value=new_raw,
        display_value=display,
        label=metric.label,
        unit=metric.unit,
        locale=metric.locale,
        emphasis=metric.emphasis,
        source_token=metric.source_token,
    )


def set_metric_emphasis(metric: StructuredMetric, emphasis: MetricEmphasis) -> StructuredMetric:
    return StructuredMetric(
        id=metric.id,
        type=metric.type,
        raw_value=metric.raw_value,
        display_value=metric.display_value,
        label=metric.label,
        unit=metric.unit,
        locale=metric.locale,
        emphasis=emphasis,
        source_token=metric.source_token,
    )


def visible_metric_strings(metrics: list[StructuredMetric]) -> list[str]:
    out: list[str] = []
    for metric in metrics:
        if metric.display_value:
            out.append(metric.display_value)
        if metric.label:
            out.append(metric.label)
        if metric.unit:
            out.append(metric.unit)
    return out
