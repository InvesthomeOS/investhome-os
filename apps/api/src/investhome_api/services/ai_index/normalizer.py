"""Deterministic text normalization for AI Index (no LLM)."""

from __future__ import annotations

import re
import unicodedata


_WS_RE = re.compile(r"[ \t]+")
_BLANK_RE = re.compile(r"\n{3,}")
_LATIN_RE = re.compile(r"[A-Za-z]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
# Turkish-specific letters (not in basic Latin alone)
_TURKISH_RE = re.compile(r"[ğĞüÜşŞıİöÖçÇ]")


def normalize_text(text: str) -> str:
    """Normalize line endings, whitespace, unicode; preserve meaningful structure."""
    if not text:
        return ""
    # NFKC for compatibility forms; keep readable characters
    cleaned = unicodedata.normalize("NFKC", text)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = cleaned.replace("\u00a0", " ").replace("\u200b", "")
    lines = [_WS_RE.sub(" ", line).strip() for line in cleaned.split("\n")]
    cleaned = "\n".join(lines)
    cleaned = _BLANK_RE.sub("\n\n", cleaned).strip()
    return cleaned


def detect_language_code(text: str) -> str:
    """Lightweight heuristic language code — not a full language detector."""
    sample = text[:4000]
    if not sample.strip():
        return "und"
    if _TURKISH_RE.search(sample):
        return "tr"
    if _CYRILLIC_RE.search(sample):
        return "ru"
    if _LATIN_RE.search(sample):
        return "en"
    return "und"


def normalize_language_code(code: str | None) -> str:
    if not code:
        return "und"
    cleaned = code.strip().lower().replace("_", "-")
    if len(cleaned) >= 2 and cleaned[:2].isalpha():
        return cleaned[:2]
    return "und"
