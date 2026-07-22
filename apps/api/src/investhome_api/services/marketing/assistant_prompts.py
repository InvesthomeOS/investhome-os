"""Centralized versioned prompts for AI Marketing Assistant — Sprint 8A4."""

from __future__ import annotations

from dataclasses import dataclass

from investhome_api.services.document_intelligence.prompts import PromptSpec

PROMPT_VERSION = "mkt-assistant-v1.0.0"
SCHEMA_VERSION = "1"

MODE_PROMPT_KEYS: dict[str, str] = {
    "marketing_summary": "marketing.summary",
    "campaign_analysis": "marketing.campaign_analysis",
    "content_draft": "marketing.content_draft",
    "campaign_brief": "marketing.campaign_brief",
    "audience_suggestion": "marketing.audience_suggestion",
    "channel_suggestion": "marketing.channel_suggestion",
    "translation": "marketing.translation",
    "next_actions": "marketing.next_actions",
}

_COMMON_SYSTEM = (
    "You are the Investhome OS Marketing AI Assistant. "
    "Use ONLY the provided allowlisted context. "
    "Never invent returns, guarantees, dates, pricing, legal/tax claims, awards, testimonials, or statistics. "
    "Distinguish verified internal data, user assumptions, AI suggestions, and missing information. "
    "Do not target protected classes. Do not publish, send, activate, or spend. "
    "All outputs are DRAFT suggestions for human review. "
    "If data is missing, say so clearly."
)


def _spec(key: str, user_template: str) -> PromptSpec:
    return PromptSpec(
        key=key,
        version=PROMPT_VERSION,
        provider="local",
        model="local-heuristic-v1",
        language="en",
        schema_version=SCHEMA_VERSION,
        system=_COMMON_SYSTEM,
        user_template=user_template,
    )


PROMPTS: dict[str, PromptSpec] = {
    "marketing.summary": _spec(
        "marketing.summary",
        "Produce a management marketing summary from this context JSON.\n\n{context_json}\n\n"
        "User instruction: {user_instruction}\nLanguage: {language}",
    ),
    "marketing.campaign_analysis": _spec(
        "marketing.campaign_analysis",
        "Analyze this campaign using only cited internal records.\n\n{context_json}\n\n"
        "User instruction: {user_instruction}\nLanguage: {language}\n"
        "Avoid unsupported causal claims. Use cautious language.",
    ),
    "marketing.content_draft": _spec(
        "marketing.content_draft",
        "Draft {content_type} marketing content. Status must remain DRAFT.\n\n{context_json}\n\n"
        "Tone: {tone}\nChannel: {channel}\nLength: {length}\nCTA: {call_to_action}\n"
        "User instruction: {user_instruction}\nLanguage: {language}",
    ),
    "marketing.campaign_brief": _spec(
        "marketing.campaign_brief",
        "Generate an editable campaign brief structure. Do not create or activate a campaign.\n\n"
        "{context_json}\n\nUser instruction: {user_instruction}\nLanguage: {language}",
    ),
    "marketing.audience_suggestion": _spec(
        "marketing.audience_suggestion",
        "Suggest audiences from internal context only. No ad-platform audiences. "
        "No protected-class targeting.\n\n{context_json}\n\n"
        "User instruction: {user_instruction}\nLanguage: {language}",
    ),
    "marketing.channel_suggestion": _spec(
        "marketing.channel_suggestion",
        "Suggest channels from internal performance only. No exact lead/ROI predictions "
        "without supporting data.\n\n{context_json}\n\n"
        "User instruction: {user_instruction}\nLanguage: {language}",
    ),
    "marketing.translation": _spec(
        "marketing.translation",
        "Translate/adapt content from {source_language} to {target_language}. "
        "Style: {adaptation_style}. Preserve project names, addresses, currency values, "
        "approved numbers, legal disclaimers, and brand terms. Never alter numeric facts.\n\n"
        "Source text:\n{source_text}\n\nContext:\n{context_json}\n\n"
        "User instruction: {user_instruction}",
    ),
    "marketing.next_actions": _spec(
        "marketing.next_actions",
        "Suggest practical next best actions with optional page links. Do not execute actions.\n\n"
        "{context_json}\n\nUser instruction: {user_instruction}\nLanguage: {language}",
    ),
}


def get_assistant_prompt(key: str) -> PromptSpec:
    if key not in PROMPTS:
        msg = f"Unknown marketing assistant prompt key: {key}"
        raise KeyError(msg)
    return PROMPTS[key]


def prompt_key_for_mode(mode: str) -> str:
    if mode not in MODE_PROMPT_KEYS:
        msg = f"Unknown assistant mode: {mode}"
        raise KeyError(msg)
    return MODE_PROMPT_KEYS[mode]


@dataclass(frozen=True)
class ModeMeta:
    key: str
    prompt_key: str
    label_key: str
    requires_campaign: bool = False
    requires_source_text: bool = False


MODE_META: list[ModeMeta] = [
    ModeMeta("marketing_summary", "marketing.summary", "modes.marketingSummary"),
    ModeMeta("campaign_analysis", "marketing.campaign_analysis", "modes.campaignAnalysis", requires_campaign=True),
    ModeMeta("content_draft", "marketing.content_draft", "modes.contentDraft"),
    ModeMeta("campaign_brief", "marketing.campaign_brief", "modes.campaignBrief"),
    ModeMeta("audience_suggestion", "marketing.audience_suggestion", "modes.audienceSuggestion"),
    ModeMeta("channel_suggestion", "marketing.channel_suggestion", "modes.channelSuggestion"),
    ModeMeta(
        "translation",
        "marketing.translation",
        "modes.translation",
        requires_source_text=True,
    ),
    ModeMeta("next_actions", "marketing.next_actions", "modes.nextActions"),
]
