"""Prompt builder for Creative Studio shared generation (reuses evidence markers)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from investhome_api.schemas.creative_studio_generation import CreativeStudioGenerationContext
from investhome_api.services.project_assistant.llm_provider import INSUFFICIENT_EVIDENCE_MESSAGE

PROMPT_VERSION = "creative-studio-generate-v1"

SYSTEM_INSTRUCTIONS = """You are the InvestHome OS Creative Studio generation assistant.
You generate marketing / creative copy ONLY from the verified project generation context.
Rules:
- Never invent project facts, amenities, pricing, brand rules, or imagery not in context.
- Never use Unsplash, stock placeholders, or mock media.
- If brand_context.available is false, do not invent brand voice or guidelines.
- If evidence is insufficient, reply exactly with:
  "{insufficient}"
- Stay strictly within the given linked project; never use other projects' knowledge.
- Output content suitable for the requested builder_type and optional language.
""".format(insufficient=INSUFFICIENT_EVIDENCE_MESSAGE)

DEFAULT_MAX_PROMPT_CHARS = 14_000


@dataclass(frozen=True)
class BuiltCreativePrompt:
    system: str
    user: str
    prompt_version: str
    chunk_count: int
    truncated: bool


def build_creative_prompt(
    *,
    instruction: str,
    context: CreativeStudioGenerationContext,
    builder_context: dict[str, Any] | None = None,
    max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
) -> BuiltCreativePrompt:
    """Build a bounded grounded prompt from structured generation context."""
    evidence = list(context.retrieved_content)
    truncated = False

    brand_payload: dict[str, Any]
    if context.brand_context.available:
        brand_payload = {
            "available": True,
            "excerpts": context.brand_context.excerpts,
            "source_categories": context.brand_context.source_categories,
            "document_ids": [str(d) for d in context.brand_context.document_ids],
        }
    else:
        brand_payload = {
            "available": False,
            "reason": context.brand_context.reason or "brand_context_unavailable",
        }

    def _user_for(ev: list[dict[str, Any]]) -> str:
        evidence_json = json.dumps(ev, ensure_ascii=False)
        identity = context.project_identity.model_dump(mode="json")
        selected = [a.model_dump(mode="json") for a in context.selected_assets]
        return (
            f"Builder type: {context.builder_type}\n"
            f"Language: {context.language or 'unspecified'}\n"
            f"Project identity:\n{json.dumps(identity, ensure_ascii=False)}\n\n"
            f"Verified facts:\n{json.dumps(context.verified_facts, ensure_ascii=False)}\n\n"
            f"Brand context:\n{json.dumps(brand_payload, ensure_ascii=False)}\n\n"
            f"Selected assets:\n{json.dumps(selected, ensure_ascii=False)}\n\n"
            f"Builder context:\n{json.dumps(builder_context or {}, ensure_ascii=False)}\n\n"
            f"--- EVIDENCE_START ---\n{evidence_json}\n--- EVIDENCE_END ---\n\n"
            f"Instruction: {(instruction or '').strip()}\n\n"
            "Generate using only the verified context and evidence above."
        )

    user = _user_for(evidence)
    while evidence and len(SYSTEM_INSTRUCTIONS) + len(user) > max_prompt_chars:
        evidence = evidence[:-1]
        truncated = True
        user = _user_for(evidence)

    return BuiltCreativePrompt(
        system=SYSTEM_INSTRUCTIONS,
        user=user,
        prompt_version=PROMPT_VERSION,
        chunk_count=len(evidence),
        truncated=truncated,
    )
