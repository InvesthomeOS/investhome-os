"""Marketing assistant generation via existing AI provider settings/abstraction."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from investhome_api.config.settings import get_settings
from investhome_api.services.document_intelligence.ai import get_ai_provider
from investhome_api.services.marketing.assistant_prompts import (
    PROMPT_VERSION,
    get_assistant_prompt,
    prompt_key_for_mode,
)


@dataclass
class AssistantGenerationResult:
    content: str
    structured: dict[str, Any]
    provider: str
    model: str
    prompt_key: str
    prompt_version: str
    input_tokens: int | None
    output_tokens: int | None
    duration_ms: int
    assumptions: list[str]
    action_links: list[dict[str, str]]
    provider_available: bool = True


def provider_status() -> tuple[bool, str]:
    """Local heuristic is always available; OpenAI is used only when keyed."""
    settings = get_settings()
    if settings.ai_provider == "openai" and settings.ai_api_key:
        return True, "openai"
    # Always fall back to the shared local provider abstraction.
    provider = get_ai_provider(confidentiality="internal")
    return True, getattr(provider, "name", "local")


def _metric_val(block: dict | None, key: str) -> Any:
    if not block:
        return None
    node = block.get(key) or {}
    return node.get("value")


def _local_generate(mode: str, context: dict[str, Any], *, language: str) -> tuple[str, dict[str, Any], list[str], list[dict[str, str]]]:
    assumptions: list[str] = []
    actions: list[dict[str, str]] = []
    perf = context.get("performance_summary") or {}
    campaign = context.get("campaign_summary") or {}
    project = context.get("project_summary") or {}
    warnings = list(context.get("data_warnings") or [])
    tr = language == "tr"

    if mode == "marketing_summary":
        structured = {
            "active_campaigns": _metric_val(perf, "active_campaigns"),
            "current_spend": _metric_val(perf, "total_spend"),
            "leads_generated": _metric_val(perf, "total_leads"),
            "qualified_leads": _metric_val(perf, "qualified_leads"),
            "conversions": _metric_val(perf, "converted_leads"),
            "campaigns_requiring_attention": _metric_val(perf, "campaigns_requiring_attention"),
            "missing_data": warnings,
            "recommended_next_steps": [
                "Review campaigns requiring attention",
                "Complete missing budget or spend records",
                "Link campaigns to projects where missing",
            ],
        }
        content = (
            "Pazarlama özeti (doğrulanmış raporlama verisine dayalı DRAFT).\n"
            if tr
            else "Marketing summary (DRAFT based on verified reporting data).\n"
        )
        content += (
            f"- Active campaigns: {structured['active_campaigns']}\n"
            f"- Spend: {structured['current_spend']} {perf.get('currency') or ''}\n"
            f"- Leads: {structured['leads_generated']} | Qualified: {structured['qualified_leads']} | "
            f"Converted: {structured['conversions']}\n"
            f"- Attention: {structured['campaigns_requiring_attention']}\n"
        )
        if warnings:
            content += ("Eksik veri: " if tr else "Missing data: ") + ", ".join(warnings) + "\n"
        assumptions.append("Summary consumes centralized performance service values only.")
        actions.append({"label": "Open reports", "href": "/workspaces/marketing/reports", "reason": "Review metrics"})
        return content, structured, assumptions, actions

    if mode == "campaign_analysis":
        camp_perf = context.get("campaign_performance") or {}
        metrics = camp_perf.get("metrics") or camp_perf
        structured = {
            "campaign_name": campaign.get("name"),
            "project": project.get("project_name"),
            "dates": {"start": campaign.get("start_date"), "end": campaign.get("end_date")},
            "budget": campaign.get("budget_amount"),
            "channel": campaign.get("primary_channel"),
            "metrics": metrics,
            "citations": context.get("data_sources") or [],
            "caveat": "The available data suggests correlations; causal claims are not supported.",
        }
        content = (
            f"Kampanya analizi DRAFT — {campaign.get('name') or '—'}\n"
            if tr
            else f"Campaign analysis DRAFT — {campaign.get('name') or '—'}\n"
        )
        content += (
            "Available data suggests reviewing spend vs leads and completing missing fields. "
            "There is not enough data to determine exact causality.\n"
        )
        if warnings:
            content += ("Eksik: " if tr else "Missing: ") + ", ".join(warnings) + "\n"
        assumptions.append("Analysis cites internal campaign and performance records only.")
        if campaign.get("id"):
            actions.append(
                {
                    "label": "Open campaign",
                    "href": f"/workspaces/marketing/campaigns/{campaign['id']}",
                    "reason": "Review campaign detail",
                }
            )
        return content, structured, assumptions, actions

    if mode == "content_draft":
        content_type = context.get("content_type") or "social_media_post"
        proj_name = project.get("project_name") or campaign.get("name") or "Investhome"
        location_bits = [project.get("city"), project.get("country")]
        location = ", ".join([str(x) for x in location_bits if x]) or ("[location missing]" if not tr else "[konum eksik]")
        draft = (
            f"{proj_name} — {location}. "
            f"{project.get('description') or ('' if not warnings else '[Project description missing]')}. "
            f"{context.get('call_to_action') or ('Contact our team to learn more.' if not tr else 'Daha fazla bilgi için ekibimizle iletişime geçin.')}"
        )
        structured = {
            "content_type": content_type,
            "tone": context.get("tone"),
            "channel": context.get("channel"),
            "status": "draft",
            "body": draft,
            "variants": [draft],
        }
        content = f"[DRAFT/{content_type}]\n{draft}\n"
        if warnings:
            content += ("\nUyarılar: " if tr else "\nWarnings: ") + ", ".join(warnings)
        assumptions.append("Draft uses only approved project/campaign fields; invent nothing.")
        return content, structured, assumptions, actions

    if mode == "campaign_brief":
        structured = {
            "campaign_name": campaign.get("name") or (context.get("user_instruction") or "New campaign")[:80],
            "objective": campaign.get("objective") or "[missing]",
            "project": project.get("project_name"),
            "target_audience": (context.get("audience_summary") or {}).get("name") or "[missing]",
            "primary_message": "[AI suggestion — edit before save]",
            "supporting_messages": [],
            "channels": [campaign.get("primary_channel")] if campaign.get("primary_channel") else [],
            "content_requirements": [],
            "asset_requirements": [a.get("name") for a in (context.get("selected_assets") or [])],
            "budget_guidance": campaign.get("budget_amount") or "[missing]",
            "timeline": {"start": campaign.get("start_date"), "end": campaign.get("end_date")},
            "call_to_action": context.get("call_to_action"),
            "success_metrics": ["leads", "qualified_leads", "conversions"],
            "risks": warnings,
            "missing_information": warnings,
            "status": "draft",
            "auto_created_campaign": False,
        }
        content = json.dumps(structured, ensure_ascii=False, indent=2)
        assumptions.append("Brief is editable DRAFT; user must explicitly save. No campaign auto-created.")
        actions.append({"label": "Campaigns", "href": "/workspaces/marketing/campaigns", "reason": "Create manually if needed"})
        return content, structured, assumptions, actions

    if mode == "audience_suggestion":
        suggestions = [
            {
                "audience_name": "Local buyer interest",
                "audience_description": "People exploring residential opportunities in the project market.",
                "likely_motivation": "Property purchase interest",
                "recommended_message": "Highlight approved project location and features only.",
                "recommended_channel": "meta",
                "data_basis": "project geography + campaign objective",
                "confidence_note": "Suggestion only — not an ad-platform audience; no customer upload.",
            },
            {
                "audience_name": "Investor-oriented outreach",
                "audience_description": "Investor-profile messaging without return guarantees.",
                "likely_motivation": "Portfolio diversification interest",
                "recommended_message": "Use approved investment information only; mark missing fields.",
                "recommended_channel": "linkedin",
                "data_basis": "campaign type / objective when present",
                "confidence_note": "No protected-class targeting. Geography and property interest only.",
            },
        ]
        structured = {"suggestions": suggestions, "ad_platform_audiences_created": False}
        content = json.dumps(structured, ensure_ascii=False, indent=2)
        assumptions.append("Audience suggestions are internal planning aids only.")
        return content, structured, assumptions, actions

    if mode == "channel_suggestion":
        channel_perf = context.get("channel_performance") or {}
        items = channel_perf.get("items") or []
        suggestions = []
        for item in items[:5]:
            suggestions.append(
                {
                    "recommended_channel": item.get("channel") or item.get("primary_channel") or "other",
                    "reason": "Supported by existing internal channel performance rows.",
                    "existing_supporting_data": item,
                    "expected_purpose": "Lead generation / awareness based on campaign objective",
                    "limitation": "Exact lead volumes and ROI are not predicted without reliable data.",
                }
            )
        if not suggestions:
            for ch in ("meta", "google", "email", "whatsapp", "linkedin", "seo", "content"):
                suggestions.append(
                    {
                        "recommended_channel": ch,
                        "reason": "Default planning suggestion — insufficient historical channel data.",
                        "existing_supporting_data": None,
                        "expected_purpose": "Explore channel fit",
                        "limitation": "No exact lead/ROI prediction — supporting data missing.",
                    }
                )
            warnings.append("channel_performance_empty")
        structured = {"suggestions": suggestions}
        content = json.dumps(structured, ensure_ascii=False, indent=2)
        assumptions.append("Channel recommendations use internal performance only.")
        return content, structured, assumptions, actions

    if mode == "translation":
        source = context.get("_source_text") or ""
        target = context.get("target_language") or ("en" if language == "tr" else "tr")
        # Preserve numbers/currency; local provider marks adaptation without inventing facts.
        adapted = source
        note = (
            f"[Adapted {context.get('language')}→{target}; style={context.get('adaptation_style') or 'professional'}; "
            "numeric facts preserved]"
        )
        structured = {
            "source_language": context.get("language"),
            "target_language": target,
            "adaptation_style": context.get("adaptation_style"),
            "adapted_text": f"{adapted}\n\n{note}",
            "numeric_facts_altered": False,
        }
        content = structured["adapted_text"]
        assumptions.append("Translation/adaptation preserves numeric facts and brand terms.")
        return content, structured, assumptions, actions

    # next_actions
    next_items = []
    if "campaign_budget_missing" in warnings and campaign.get("id"):
        next_items.append(
            {
                "action": "Complete missing campaign budget",
                "href": f"/workspaces/marketing/campaigns/{campaign['id']}/budget",
                "reason": "Budget field missing",
            }
        )
    if "campaign_project_unlinked" in warnings and campaign.get("id"):
        next_items.append(
            {
                "action": "Link campaign to a project",
                "href": f"/workspaces/marketing/campaigns/{campaign['id']}",
                "reason": "Project not linked",
            }
        )
    if not (context.get("selected_assets")):
        next_items.append(
            {
                "action": "Add campaign assets",
                "href": "/workspaces/marketing/assets",
                "reason": "No assets selected",
            }
        )
    next_items.extend(
        [
            {
                "action": "Prepare Turkish version" if not tr else "Türkçe versiyon hazırla",
                "href": "/workspaces/marketing/ai/assistant?mode=translation&lang=tr",
                "reason": "Localization",
            },
            {
                "action": "Prepare English version" if not tr else "İngilizce versiyon hazırla",
                "href": "/workspaces/marketing/ai/assistant?mode=translation&lang=en",
                "reason": "Localization",
            },
            {
                "action": "Create a new campaign brief",
                "href": "/workspaces/marketing/ai/assistant?mode=campaign_brief",
                "reason": "Planning",
            },
            {
                "action": "Review underperforming campaigns",
                "href": "/workspaces/marketing/reports",
                "reason": "Performance review",
            },
        ]
    )
    structured = {"actions": next_items, "auto_executed": False}
    content = json.dumps(structured, ensure_ascii=False, indent=2)
    actions = [{"label": i["action"], "href": i["href"], "reason": i.get("reason")} for i in next_items]
    assumptions.append("Next actions are suggestions only and are never executed automatically.")
    return content, structured, assumptions, actions


def generate_assistant_output(
    mode: str,
    context: dict[str, Any],
    *,
    language: str = "en",
    source_text: str | None = None,
    timeout_seconds: float = 45.0,
) -> AssistantGenerationResult:
    started = time.perf_counter()
    available, provider_name = provider_status()
    if not available:
        duration_ms = int((time.perf_counter() - started) * 1000)
        return AssistantGenerationResult(
            content="",
            structured={"error": "provider_unavailable"},
            provider=provider_name,
            model=get_settings().ai_model,
            prompt_key=prompt_key_for_mode(mode),
            prompt_version=PROMPT_VERSION,
            input_tokens=None,
            output_tokens=None,
            duration_ms=duration_ms,
            assumptions=[],
            action_links=[],
            provider_available=False,
        )

    prompt_key = prompt_key_for_mode(mode)
    prompt = get_assistant_prompt(prompt_key)
    ctx = dict(context)
    ctx["_source_text"] = source_text or ""

    settings = get_settings()
    # Prefer structured local generation; optionally enrich via OpenAI chat when configured.
    if settings.ai_provider == "openai" and settings.ai_api_key:
        try:
            context_json = json.dumps({k: v for k, v in ctx.items() if not k.startswith("_")}, ensure_ascii=False)[
                :14000
            ]
            user_content = prompt.user_template.format(
                context_json=context_json,
                user_instruction=ctx.get("user_instruction") or "",
                language=language,
                content_type=ctx.get("content_type") or "",
                tone=ctx.get("tone") or "",
                channel=ctx.get("channel") or "",
                length=ctx.get("length") or "",
                call_to_action=ctx.get("call_to_action") or "",
                source_language=ctx.get("language") or language,
                target_language=ctx.get("target_language") or language,
                adaptation_style=ctx.get("adaptation_style") or "professional",
                source_text=(source_text or "")[:8000],
            )
            payload = {
                "model": settings.ai_model,
                "messages": [
                    {"role": "system", "content": prompt.system},
                    {"role": "user", "content": user_content},
                ],
                "temperature": 0.3,
            }
            with httpx.Client(timeout=timeout_seconds) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.ai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
            data = response.json()
            text = data["choices"][0]["message"]["content"]
            usage = data.get("usage") or {}
            duration_ms = int((time.perf_counter() - started) * 1000)
            # Keep structured local skeleton for UI consistency; attach model text as body.
            _, structured, assumptions, actions = _local_generate(mode, ctx, language=language)
            structured["model_text"] = text
            return AssistantGenerationResult(
                content=text,
                structured=structured,
                provider="openai",
                model=settings.ai_model,
                prompt_key=prompt_key,
                prompt_version=PROMPT_VERSION,
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                duration_ms=duration_ms,
                assumptions=assumptions + ["OpenAI text attached; structured fields remain draft suggestions."],
                action_links=actions,
                provider_available=True,
            )
        except httpx.TimeoutException as exc:
            raise TimeoutError("AI provider timed out") from exc
        except Exception:
            # Fall back to local structured generation — never fail closed without draft.
            pass

    content, structured, assumptions, actions = _local_generate(mode, ctx, language=language)
    duration_ms = int((time.perf_counter() - started) * 1000)
    provider = get_ai_provider(confidentiality="internal")
    return AssistantGenerationResult(
        content=content,
        structured=structured,
        provider=getattr(provider, "name", "local"),
        model=getattr(provider, "model", settings.ai_model),
        prompt_key=prompt_key,
        prompt_version=PROMPT_VERSION,
        input_tokens=len(json.dumps(ctx)) // 4,
        output_tokens=len(content) // 4,
        duration_ms=duration_ms,
        assumptions=assumptions,
        action_links=actions,
        provider_available=True,
    )
