"""Search result ranking for CRM entities."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime


def _normalize(text: str) -> str:
    return text.strip().lower()


def score_text_match(query: str, *values: str | None, exact: bool = False) -> float:
    needle = _normalize(query)
    if not needle:
        return 0.0
    best = 0.0
    for raw in values:
        if not raw:
            continue
        hay = _normalize(str(raw))
        if hay == needle:
            best = max(best, 100.0)
        elif hay.startswith(needle):
            best = max(best, 85.0)
        elif needle in hay:
            best = max(best, 65.0)
        elif not exact:
            tokens = [t for t in re.split(r"\s+", needle) if t]
            if tokens and all(t in hay for t in tokens):
                best = max(best, 55.0)
    return best


def score_recency(updated_at: datetime | None, *, now: datetime | None = None) -> float:
    if updated_at is None:
        return 0.0
    ref = now or datetime.now(UTC)
    if updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=UTC)
    days = max((ref - updated_at).total_seconds() / 86400, 0)
    return max(0.0, 30.0 * math.exp(-days / 30))


def score_relationship_strength(strength: str | None) -> float:
    return {"weak": 5.0, "moderate": 10.0, "strong": 20.0, "strategic": 30.0}.get(strength or "", 0.0)


def compute_combined_score(
    *,
    text_score: float,
    recency_score: float,
    relationship_score: float = 0.0,
    is_favorite: bool = False,
    is_pinned: bool = False,
) -> tuple[float, float, float, float]:
    bonus = (5.0 if is_favorite else 0.0) + (3.0 if is_pinned else 0.0)
    relevance = text_score + bonus
    combined = relevance * 0.7 + recency_score * 0.2 + relationship_score * 0.1
    return combined, relevance, recency_score, relationship_score


def build_highlight_html(text: str, query: str) -> str:
    if not text or not query.strip():
        return text
    import html

    escaped = html.escape(text)
    needle = query.strip()
    pattern = re.compile(re.escape(needle), re.IGNORECASE)
    return pattern.sub(lambda m: f"<mark>{html.escape(m.group(0))}</mark>", escaped)


def build_snippet(text: str, query: str, *, max_len: int = 120) -> str:
    if not text:
        return ""
    lower = text.lower()
    idx = lower.find(query.lower())
    if idx < 0:
        return text[:max_len] + ("…" if len(text) > max_len else "")
    start = max(0, idx - 24)
    end = min(len(text), idx + len(query) + 48)
    snippet = text[start:end]
    if start > 0:
        snippet = f"…{snippet}"
    if end < len(text):
        snippet = f"{snippet}…"
    return snippet


def suggest_did_you_mean(query: str, candidates: list[str]) -> str | None:
    if not query or not candidates:
        return None
    q = _normalize(query)
    best: tuple[float, str] | None = None
    for candidate in candidates:
        c = _normalize(candidate)
        if c == q:
            continue
        # simple character overlap ratio
        overlap = len(set(q) & set(c)) / max(len(set(q) | set(c)), 1)
        if overlap > 0.6 and (best is None or overlap > best[0]):
            best = (overlap, candidate)
    return best[1] if best else None
