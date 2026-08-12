"""Quality validator — repair composition before canvas mutation.

Obvious layout/copy problems are fixed automatically. Font shrinking is last resort.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from investhome_api.services.social_design_engine.creative_director import (
    CreativeConcept,
    LOCATION_DENY_TERMS,
    clip_headline,
    is_generic_cta,
    is_generic_headline,
)
from investhome_api.services.social_design_engine.generation import (
    CampaignFact,
    ContentPackage,
    DesignPlan,
    DesignPlanElement,
    GenerationIntent,
    _clip_copy,
)
from investhome_api.services.social_design_engine.layout import (
    LINE_HEIGHT,
    _boxes_overlap,
    element_within_bounds,
    measure_text_block,
    role_font_prefs,
    safe_content_box,
    subject_safe_regions,
)
from investhome_api.services.social_design_engine.ops import FORMAT_PRESETS, looks_like_rag_or_debug_copy

MAX_CANVAS_TEXT_BLOCKS = 4  # eyebrow + headline + support + CTA
HEADLINE_MAX_WORDS = 8
HEADLINE_MIN_WORDS = 2
SUPPORT_MAX_CHARS = 110


@dataclass
class QualityIssue:
    code: str
    detail: str
    repair: str


@dataclass
class ValidationReport:
    passed: bool
    issues: list[QualityIssue] = field(default_factory=list)
    repairs: list[str] = field(default_factory=list)


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _word_count(text: str) -> int:
    return len([w for w in re.split(r"\s+", (text or "").strip()) if w])


def _canvas_copy_blob(package: ContentPackage) -> str:
    return " ".join(
        [
            package.headline or "",
            package.supporting_text or "",
            package.key_fact or "",
            package.cta or "",
            getattr(package, "eyebrow", "") or "",
        ]
    )


def _unnecessary_fact_hits(blob: str, concept: CreativeConcept) -> list[str]:
    hits: list[str] = []
    lower = _norm(blob)
    if concept.objective == "location":
        for term in LOCATION_DENY_TERMS:
            if term in lower:
                hits.append(term)
        for fact in concept.suppressed_facts:
            token = (fact.text or "").strip()
            if token and len(token) >= 6 and _norm(token) in lower:
                hits.append(token)
    for fact in concept.suppressed_facts:
        token = (fact.text or "").strip()
        if token and len(token) >= 8 and token in (blob or ""):
            hits.append(token)
    return list(dict.fromkeys(hits))


def _strip_denied_phrases(text: str, hits: list[str]) -> str:
    out = text or ""
    for hit in hits:
        out = re.sub(re.escape(hit), "", out, flags=re.I)
    out = re.sub(r"\s{2,}", " ", out)
    out = re.sub(r"\s+([,.;])", r"\1", out).strip(" ,.;")
    return out


def _plan_text_elements(plan: DesignPlan) -> list[DesignPlanElement]:
    return [el for el in plan.elements if el.type in {"TEXT", "BUTTON", "CTA"}]


def _element_box(el: DesignPlanElement) -> dict[str, Any]:
    return {"x": el.x, "y": el.y, "width": el.width, "height": el.height, "type": el.type, "role": el.role}


def inspect_quality(
    *,
    package: ContentPackage,
    plan: DesignPlan,
    concept: CreativeConcept,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
) -> ValidationReport:
    issues: list[QualityIssue] = []
    blob = _canvas_copy_blob(package)
    w, h = FORMAT_PRESETS.get(plan.format_preset, (1080, 1080))

    if not (package.headline or "").strip():
        issues.append(QualityIssue("missing_primary", "Headline is empty", "restore_primary"))
    if _word_count(package.headline) > HEADLINE_MAX_WORDS or len(package.headline) > 70:
        issues.append(QualityIssue("headline_too_long", package.headline, "shorten_headline"))
    if _word_count(package.headline) == 1:
        issues.append(QualityIssue("headline_too_short", package.headline, "expand_headline"))
    if is_generic_headline(package.headline):
        issues.append(QualityIssue("generic_headline", package.headline, "replace_headline"))
    if is_generic_cta(package.cta):
        issues.append(QualityIssue("generic_cta", package.cta, "replace_cta"))
    if looks_like_rag_or_debug_copy(blob):
        issues.append(QualityIssue("rag_on_canvas", "debug copy leaked", "strip_rag"))

    if concept.objective == "location":
        place_ok = any(
            k in _norm(blob)
            for k in (
                "washington",
                "columbia",
                "heights",
                "location",
                "address",
                "dc",
                "d.c",
                "city",
                "central",
            )
        ) or any(f.reason.startswith("identity_") for f in concept.selected_facts)
        if not place_ok:
            issues.append(QualityIssue("objective_missing", "location not represented", "restore_objective"))
    if concept.objective == "investment":
        missing = [f.display for f in campaign_facts if f.display not in blob]
        if missing:
            issues.append(QualityIssue("campaign_missing", ",".join(missing), "restore_campaign"))

    denied = _unnecessary_fact_hits(blob, concept)
    if denied:
        issues.append(QualityIssue("unnecessary_facts", "; ".join(denied[:6]), "remove_facts"))

    support = package.supporting_text or ""
    if support.count("\n") > 1 or len(support) > SUPPORT_MAX_CHARS:
        issues.append(QualityIssue("support_verbose", support, "shorten_support"))

    text_blocks = _plan_text_elements(plan)
    if len(text_blocks) > MAX_CANVAS_TEXT_BLOCKS:
        issues.append(QualityIssue("too_many_blocks", str(len(text_blocks)), "drop_low_priority"))

    # Hierarchy: headline font must dominate body
    headline_el = next((e for e in plan.elements if e.role == "headline"), None)
    body_el = next((e for e in plan.elements if e.role == "body"), None)
    eyebrow_el = next((e for e in plan.elements if e.role == "eyebrow"), None)
    if headline_el and body_el and headline_el.font_size and body_el.font_size:
        if headline_el.font_size < int(body_el.font_size * 1.45):
            issues.append(QualityIssue("weak_hierarchy", "headline not dominant", "fix_hierarchy"))
    if headline_el and eyebrow_el and headline_el.font_size and eyebrow_el.font_size:
        if eyebrow_el.font_size >= headline_el.font_size:
            issues.append(QualityIssue("eyebrow_too_large", "eyebrow competes", "fix_hierarchy"))

    # Overlap / safe margins / focal obstruction
    box = safe_content_box(w, h)
    regions = subject_safe_regions(w, h)
    subject = regions["subject"]
    for el in plan.elements:
        if el.type == "TEXT" or el.type in {"BUTTON", "CTA"}:
            if not element_within_bounds(_element_box(el), w, h):
                issues.append(QualityIssue("unsafe_margin", el.role, "clamp_safe"))
    for i, a in enumerate(plan.elements):
        for b in plan.elements[i + 1 :]:
            if a.type == "TEXT" and b.type in {"TEXT", "BUTTON", "CTA"}:
                if _boxes_overlap(_element_box(a), _element_box(b), gap=8):
                    issues.append(QualityIssue("overlap", f"{a.role}/{b.role}", "resolve_overlap"))

    if concept.composition_strategy in {"MINIMAL_HERO", "LOCATION"} and headline_el:
        # Headline should not sit in the likely building band
        hy = headline_el.y + headline_el.height // 2
        sub_y = subject["y"]
        sub_bottom = subject["y"] + subject["height"]
        if sub_y <= hy <= sub_bottom and concept.safe_text_zone == "top":
            issues.append(QualityIssue("focal_obstruction", "headline covers subject", "move_to_safe_zone"))

    # Density: stacked text occupying too much of the frame
    text_h = sum(el.height for el in plan.elements if el.type in {"TEXT", "BUTTON", "CTA"})
    if text_h > int(h * 0.48) and body_el:
        issues.append(QualityIssue("crowded", "text occupies too much frame", "reduce_density"))

    if plan.overlay in {"gradient", "full", "heavy"}:
        issues.append(QualityIssue("heavy_overlay", plan.overlay, "localize_overlay"))

    passed = not issues
    return ValidationReport(passed=passed, issues=issues, repairs=[i.repair for i in issues])


def _apply_copy_repairs(
    package: ContentPackage,
    concept: CreativeConcept,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
    issues: list[QualityIssue],
) -> ContentPackage:
    headline = package.headline
    support = package.supporting_text
    key_fact = package.key_fact
    cta = package.cta
    eyebrow = getattr(package, "eyebrow", "") or ""
    codes = {i.code for i in issues}

    if "strip_rag" in codes or "unnecessary_facts" in codes:
        hits: list[str] = []
        for issue in issues:
            if issue.code in {"unnecessary_facts", "rag_on_canvas"}:
                hits.extend([p.strip() for p in issue.detail.split(";") if p.strip()])
        hits.extend(LOCATION_DENY_TERMS if concept.objective == "location" else [])
        headline = _strip_denied_phrases(headline, hits)
        support = _strip_denied_phrases(support, hits)
        key_fact = _strip_denied_phrases(key_fact, hits)
        eyebrow = _strip_denied_phrases(eyebrow, hits)

    if "shorten_headline" in codes or "generic_headline" in codes or "replace_headline" in codes:
        headline = clip_headline(concept.primary_message or headline)
        if is_generic_headline(headline) or _word_count(headline) > HEADLINE_MAX_WORDS:
            headline = clip_headline(concept.primary_message)

    if "expand_headline" in codes and _word_count(headline) < HEADLINE_MIN_WORDS:
        headline = clip_headline(concept.primary_message or headline)

    if "shorten_support" in codes or "reduce_density" in codes or "crowded" in codes:
        support = _clip_copy(support, SUPPORT_MAX_CHARS)
        if "\n" in support:
            support = " ".join(line.strip() for line in support.splitlines() if line.strip())[:SUPPORT_MAX_CHARS]
        key_fact = ""

    if "drop_low_priority" in codes or "reduce_density" in codes:
        eyebrow = ""
        if concept.composition_strategy == "MINIMAL_HERO":
            support = ""
            key_fact = ""
        elif support and key_fact:
            key_fact = ""

    if "replace_cta" in codes or "generic_cta" in codes:
        cta = concept.cta or cta
        if is_generic_cta(cta):
            cta = "Schedule a private tour" if intent.language != "tr" else "Özel tur planla"
            if concept.objective == "investment":
                cta = "Explore the investment" if intent.language != "tr" else "Yatırım fırsatını incele"

    if "restore_campaign" in codes and campaign_facts:
        extra = " · ".join(f.display for f in campaign_facts)
        if extra not in f"{headline} {support} {key_fact}":
            support = extra if not support else f"{support} · {extra}" if extra not in support else support

    if "restore_objective" in codes and concept.objective == "location":
        if "washington" not in _norm(headline) and "columbia" not in _norm(headline):
            headline = clip_headline(concept.primary_message or headline)
        if not support:
            support = concept.supporting_message

    if "restore_primary" in codes:
        headline = concept.primary_message or headline

    return ContentPackage(
        headline=_clip_copy(headline, 70) or concept.primary_message,
        supporting_text=_clip_copy(support, 160),
        key_fact=_clip_copy(key_fact, 80),
        cta=_clip_copy(cta, 36) or concept.cta,
        language=package.language,
        tone=package.tone,
        eyebrow=_clip_copy(eyebrow, 32),
    )


def _apply_plan_repairs(
    plan: DesignPlan,
    package: ContentPackage,
    concept: CreativeConcept,
    issues: list[QualityIssue],
) -> DesignPlan:
    from investhome_api.services.social_design_engine.generation import build_design_plan

    codes = {i.code for i in issues}
    if codes & {
        "drop_low_priority",
        "reduce_density",
        "crowded",
        "focal_obstruction",
        "overlap",
        "unsafe_margin",
        "weak_hierarchy",
        "heavy_overlay",
        "too_many_blocks",
        "fix_hierarchy",
        "move_to_safe_zone",
        "clamp_safe",
        "resolve_overlap",
        "localize_overlay",
        "eyebrow_too_large",
    }:
        if "crowded" in codes or "reduce_density" in codes or "too_many_blocks" in codes:
            concept.include_eyebrow = False
            concept.eyebrow = ""
            if concept.composition_strategy != "INVESTMENT":
                if concept.text_density != "sparse":
                    concept.text_density = "sparse"
            if concept.composition_strategy == "EDITORIAL":
                concept.composition_strategy = "MINIMAL_HERO"
                concept.include_support = bool(package.supporting_text)
        if "heavy_overlay" in codes or "localize_overlay" in codes:
            concept.contrast_strategy = "localized_gradient"
        rebuilt = build_design_plan(
            package=package,
            intent=GenerationIntent(
                platform=plan.platform,
                format_preset=plan.format_preset,
                marketing_objective=concept.objective,
                tone=concept.tone,
            ),
            picked_asset_id=None,
            post_id=plan.post_id,
            rebuild=plan.rebuild,
            concept=concept,
        )
        rebuilt.background_asset_id = plan.background_asset_id
        rebuilt.name = plan.name
        return rebuilt
    return plan


def validate_and_repair(
    *,
    package: ContentPackage,
    plan: DesignPlan,
    concept: CreativeConcept,
    intent: GenerationIntent,
    campaign_facts: list[CampaignFact],
) -> tuple[ContentPackage, DesignPlan, CreativeConcept, ValidationReport]:
    """Inspect, repair copy/layout, re-inspect. Never requires user intervention."""
    report = inspect_quality(
        package=package,
        plan=plan,
        concept=concept,
        intent=intent,
        campaign_facts=campaign_facts,
    )
    if report.passed:
        return package, plan, concept, report

    repaired_pkg = _apply_copy_repairs(package, concept, intent, campaign_facts, report.issues)
    # Keep campaign tokens verbatim after copy repairs
    from investhome_api.services.social_design_engine.generation import enforce_campaign_facts

    if campaign_facts and concept.objective == "investment":
        repaired_pkg = enforce_campaign_facts(repaired_pkg, campaign_facts)

    concept.primary_message = repaired_pkg.headline
    concept.supporting_message = repaired_pkg.supporting_text
    concept.cta = repaired_pkg.cta
    concept.eyebrow = repaired_pkg.eyebrow
    concept.include_eyebrow = bool(repaired_pkg.eyebrow)
    concept.include_support = bool(repaired_pkg.supporting_text)

    repaired_plan = _apply_plan_repairs(plan, repaired_pkg, concept, report.issues)
    final = inspect_quality(
        package=repaired_pkg,
        plan=repaired_plan,
        concept=concept,
        intent=intent,
        campaign_facts=campaign_facts,
    )
    final.repairs = list(dict.fromkeys(report.repairs + final.repairs))
    # Second pass: if still crowded, drop support (never shrink-only).
    if any(i.code in {"crowded", "too_many_blocks"} for i in final.issues):
        repaired_pkg = ContentPackage(
            headline=repaired_pkg.headline,
            supporting_text="" if concept.composition_strategy != "INVESTMENT" else repaired_pkg.supporting_text,
            key_fact="",
            cta=repaired_pkg.cta,
            language=repaired_pkg.language,
            tone=repaired_pkg.tone,
            eyebrow="",
        )
        concept.include_eyebrow = False
        concept.include_support = bool(repaired_pkg.supporting_text)
        concept.text_density = "sparse"
        repaired_plan = _apply_plan_repairs(repaired_plan, repaired_pkg, concept, final.issues)
        final = inspect_quality(
            package=repaired_pkg,
            plan=repaired_plan,
            concept=concept,
            intent=intent,
            campaign_facts=campaign_facts,
        )
        final.repairs.append("drop_support_for_density")
    return repaired_pkg, repaired_plan, concept, final
