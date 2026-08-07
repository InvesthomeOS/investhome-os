"""Structure-aware text chunking for AI Documents (600–1200 chars)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

# Target window — prefer filling toward max without mid-word splits
CHUNK_MIN_CHARS = 600
CHUNK_MAX_CHARS = 1200

_HEADING_RE = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Za-z0-9 /&-]{2,80})$")
_LIST_ITEM_RE = re.compile(r"^(\s*[-*•]\s+|\s*\d+[.)]\s+)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜÄÖÜ\"'])")
_WORD_SPLIT_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ChunkDraft:
    chunk_order: int
    text: str
    checksum: str


def text_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_structural_break(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if _LIST_ITEM_RE.match(stripped):
        return True
    if stripped.startswith("#"):
        return True
    if _HEADING_RE.match(stripped) and len(stripped) < 100:
        return True
    return False


def _split_into_blocks(text: str) -> list[str]:
    """Split on blank lines / headings / list boundaries, keep order."""
    if not text or not text.strip():
        return []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[str] = []
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        joined = "\n".join(buf).strip()
        if joined:
            blocks.append(joined)
        buf = []

    for line in lines:
        if not line.strip():
            flush()
            continue
        if buf and _is_structural_break(line) and not _LIST_ITEM_RE.match(buf[-1].strip() or ""):
            # Start new block on heading / list item after prose
            if _LIST_ITEM_RE.match(line.strip()) or line.strip().startswith("#"):
                flush()
        buf.append(line)
    flush()
    return blocks


def _split_oversized(block: str, max_chars: int) -> list[str]:
    """Split a too-large block on sentences, then words — never mid-word."""
    if len(block) <= max_chars:
        return [block]
    parts: list[str] = []
    sentences = _SENTENCE_SPLIT_RE.split(block)
    if len(sentences) == 1:
        # No sentence boundaries — split on whitespace
        words = _WORD_SPLIT_RE.split(block)
        current = ""
        for word in words:
            if not word:
                continue
            candidate = f"{current} {word}".strip() if current else word
            if len(candidate) > max_chars and current:
                parts.append(current)
                current = word
            else:
                current = candidate
        if current:
            parts.append(current)
        return parts

    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            parts.extend(_split_oversized(current, max_chars) if len(current) > max_chars else [current])
            current = sentence
        else:
            current = candidate
    if current:
        parts.extend(_split_oversized(current, max_chars) if len(current) > max_chars else [current])
    return parts


def _pack_blocks(blocks: list[str], *, min_chars: int, max_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for block in blocks:
        pieces = _split_oversized(block, max_chars)
        for piece in pieces:
            if not current:
                current = piece
                continue
            candidate = f"{current}\n\n{piece}"
            if len(candidate) <= max_chars:
                current = candidate
                continue
            # Current is ready if it meets min, else force-append when tiny
            if len(current) >= min_chars or len(candidate) > max_chars:
                chunks.append(current)
                current = piece
            else:
                # Prefer not leaving tiny leftovers under min when possible
                current = candidate if len(candidate) <= max_chars else current
                if len(candidate) > max_chars:
                    chunks.append(current)
                    current = piece
    if current:
        # Merge tiny trailing chunk into previous when possible
        if chunks and len(current) < min_chars:
            merged = f"{chunks[-1]}\n\n{current}"
            if len(merged) <= max_chars + (min_chars // 2):
                # Soft allow slight overflow only when absorbing tiny tail under 1.5x max
                if len(merged) <= max_chars:
                    chunks[-1] = merged
                else:
                    chunks.append(current)
            else:
                chunks.append(current)
        else:
            chunks.append(current)
    return chunks


def build_chunks(
    text: str,
    *,
    min_chars: int = CHUNK_MIN_CHARS,
    max_chars: int = CHUNK_MAX_CHARS,
) -> list[ChunkDraft]:
    """Build ordered chunk drafts from document text."""
    cleaned = (text or "").strip()
    if not cleaned:
        return []
    if len(cleaned) <= max_chars:
        return [ChunkDraft(chunk_order=0, text=cleaned, checksum=text_checksum(cleaned))]

    blocks = _split_into_blocks(cleaned)
    if not blocks:
        blocks = [cleaned]
    packed = _pack_blocks(blocks, min_chars=min_chars, max_chars=max_chars)
    return [
        ChunkDraft(chunk_order=i, text=part, checksum=text_checksum(part))
        for i, part in enumerate(packed)
        if part.strip()
    ]
