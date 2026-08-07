"""Deterministic rule-based summary — first headings / sentences. No LLM."""

from __future__ import annotations

import re

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def build_summary(text: str, *, max_sentences: int = 3, max_chars: int = 600) -> str:
    """Build a short deterministic summary from headings and early sentences."""
    if not text or not text.strip():
        return ""

    headings = [m.group(2).strip() for m in _HEADING_RE.finditer(text) if m.group(2).strip()]
    if headings:
        heading_part = " | ".join(headings[:3])
        body = _HEADING_RE.sub("", text).strip()
        sentences = _split_sentences(body)
        extras = " ".join(sentences[: max(1, max_sentences - 1)]).strip()
        summary = f"{heading_part}. {extras}".strip() if extras else heading_part
    else:
        sentences = _split_sentences(text)
        summary = " ".join(sentences[:max_sentences]).strip()

    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "…"
    return summary


def _split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in _SENTENCE_RE.split(text) if p and p.strip()]
    # Prefer substantial sentences
    return [p for p in parts if len(p) > 20] or parts
