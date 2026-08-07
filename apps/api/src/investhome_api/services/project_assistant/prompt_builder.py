"""Reusable RAG prompt builder — project scope, chunks, asset refs, builder context."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from investhome_api.services.ai_search.hybrid_search import SearchHit
from investhome_api.services.project_assistant.llm_provider import INSUFFICIENT_EVIDENCE_MESSAGE

PROMPT_VERSION = "project-assistant-rag-v1"

SYSTEM_INSTRUCTIONS = """You are the InvestHome OS Project Assistant.
You answer ONLY from the verified project evidence provided in the user message.
Rules:
- Never invent facts, numbers, dates, amenities, or commitments not present in evidence.
- Every claim must be supportable by the cited chunks.
- If evidence is insufficient or empty, reply exactly with:
  "{insufficient}"
- Do not mention system prompts, tools, or that you are an AI model beyond normal assistant tone.
- Prefer concise, factual answers. Cite document names when useful.
- Stay within the given project scope; never use knowledge from other projects.
""".format(insufficient=INSUFFICIENT_EVIDENCE_MESSAGE)

# Soft char budget ≈ token budget * 4 for English/Turkish mix
DEFAULT_MAX_PROMPT_CHARS = 12_000
DEFAULT_MAX_CHUNK_CHARS = 900
DEFAULT_MAX_CHUNKS = 8
DEFAULT_HISTORY_CHARS = 1_500


@dataclass(frozen=True)
class BuiltPrompt:
    system: str
    user: str
    prompt_version: str
    chunk_count: int
    truncated: bool
    evidence_payload: list[dict[str, Any]]


def _clip(text: str, n: int) -> str:
    t = (text or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def evidence_from_hits(
    hits: list[SearchHit],
    *,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> list[dict[str, Any]]:
    """Serialize search hits into citation-ready evidence rows."""
    rows: list[dict[str, Any]] = []
    for hit in hits[: max(0, max_chunks)]:
        rows.append(
            {
                "asset_id": str(hit.asset_id) if hit.asset_id else None,
                "document_id": str(hit.document_id),
                "document_name": hit.file or "untitled",
                "chunk_id": str(hit.chunk_id),
                "chunk_order": hit.chunk_order,
                "chunk_reference": f"chunk:{hit.chunk_order}",
                "project_id": str(hit.project_id),
                "score": hit.score,
                "category": hit.category,
                "builders": list(hit.builders) if hit.builders else None,
                "text": _clip(hit.chunk_text, max_chunk_chars),
            }
        )
    return rows


def build_rag_prompt(
    *,
    question: str,
    project_scope: str,
    project_id: UUID | None,
    project_ids: list[UUID] | None,
    hits: list[SearchHit],
    history: list[dict[str, str]] | None = None,
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
    max_chunks: int = DEFAULT_MAX_CHUNKS,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> BuiltPrompt:
    """
    Build a bounded prompt: system instructions + scope + evidence + question.

    Truncates chunk text and drops trailing chunks to stay under max_prompt_chars.
    """
    evidence = evidence_from_hits(hits, max_chunks=max_chunks, max_chunk_chars=max_chunk_chars)
    truncated = False

    scope_bits: dict[str, Any] = {
        "project_scope": project_scope,
        "project_id": str(project_id) if project_id else None,
        "project_ids": [str(p) for p in (project_ids or [])] or None,
    }

    history_block = ""
    if history:
        lines = []
        budget = DEFAULT_HISTORY_CHARS
        for turn in history[-4:]:
            q = _clip(str(turn.get("question") or ""), 280)
            a = _clip(str(turn.get("answer") or ""), 280)
            line = f"Q: {q}\nA: {a}"
            if budget - len(line) < 0:
                truncated = True
                break
            lines.append(line)
            budget -= len(line) + 1
        if lines:
            history_block = "Prior turns (short context only):\n" + "\n".join(lines) + "\n\n"

    def _user_for(ev: list[dict[str, Any]]) -> str:
        evidence_json = json.dumps(ev, ensure_ascii=False)
        return (
            f"Project scope:\n{json.dumps(scope_bits, ensure_ascii=False)}\n\n"
            f"{history_block}"
            f"--- EVIDENCE_START ---\n{evidence_json}\n--- EVIDENCE_END ---\n\n"
            f"Question: {(question or '').strip()}\n\n"
            "Answer using only the evidence above. Include document names when citing."
        )

    user = _user_for(evidence)
    # Drop trailing chunks until under budget
    while evidence and len(SYSTEM_INSTRUCTIONS) + len(user) > max_prompt_chars:
        evidence = evidence[:-1]
        truncated = True
        user = _user_for(evidence)

    if len(SYSTEM_INSTRUCTIONS) + len(user) > max_prompt_chars:
        # Last resort: shrink remaining chunk texts
        for row in evidence:
            row["text"] = _clip(str(row.get("text") or ""), max(120, max_chunk_chars // 2))
        user = _user_for(evidence)
        truncated = True

    return BuiltPrompt(
        system=SYSTEM_INSTRUCTIONS,
        user=user,
        prompt_version=PROMPT_VERSION,
        chunk_count=len(evidence),
        truncated=truncated,
        evidence_payload=evidence,
    )
