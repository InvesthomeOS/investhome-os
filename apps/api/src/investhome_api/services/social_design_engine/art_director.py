"""Investhome Art Director — plan before render, real assets only.

Produces three editable DesignPlans (A/B/C) from the same real project asset
pool. Never reconstructs architecture via text-to-image.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Any, Literal
from uuid import UUID

from investhome_api.schemas.social_design_engine import (
    ArtDirectorProvenance,
    ArtDirectorVariant,
    SocialDesignMediaCandidate,
)
from investhome_api.services.social_design_engine.campaign_intent import CampaignIntentKind
from investhome_api.services.social_design_engine.creative_director import CreativeConcept
from investhome_api.services.social_design_engine.creative_plan import (
    CreativeDirectionKind,
    CreativePlan,
    DENSITY_TO_LEGACY,
    build_creative_plan,
    creative_plan_to_dict,
)
from investhome_api.services.social_design_engine.generation import (
    ContentPackage,
    DesignPlan,
    DesignPlanElement,
    GenerationIntent,
    build_design_plan,
    compose_ops_from_plan,
    design_plan_to_dict,
)
from investhome_api.services.social_design_engine.ops import FORMAT_PRESETS
from investhome_api.services.social_design_engine.composition_engine import PRIMITIVE_FAMILY_HINT
from investhome_api.services.social_design_engine.media import (
    extract_design_reference_language,
    pick_best_asset,
    pick_logo_asset,
    pick_map_asset,
    pick_supporting_logo_asset,
)

ArtDirectorCampaign = Literal[
    "LOCATION",
    "INVESTMENT",
    "ARCHITECTURE",
    "LIFESTYLE",
    "LAUNCH",
    "PROJECT_OVERVIEW",
]

VariantKey = Literal["A", "B", "C"]


@dataclass(frozen=True)
class VariantRecipe:
    key: VariantKey
    label: str
    direction: CreativeDirectionKind
    composition: str
    crop_strategy: str
    focal_area: str
    logo_placement: str
    alignment: str


INVESTMENT_RECIPES: tuple[VariantRecipe, ...] = (
    VariantRecipe(
        key="A",
        label="EDITORIAL LUXURY",
        direction="EDITORIAL_LUXURY",
        composition="TOP_LEFT_EDITORIAL",
        crop_strategy="editorial_left_safe",
        focal_area="building_right",
        logo_placement="top-left",
        alignment="left",
    ),
    VariantRecipe(
        key="B",
        label="INSTITUTIONAL INVESTMENT",
        direction="INVESTMENT_DATA",
        composition="LOWER_THIRD",
        crop_strategy="lower_third_safe",
        focal_area="facade_center",
        logo_placement="top-right",
        alignment="left",
    ),
    VariantRecipe(
        key="C",
        label="ARCHITECTURAL PREMIUM",
        direction="ARCHITECTURAL_FEATURE",
        composition="IMAGE_DOMINANT",
        crop_strategy="architecture_full",
        focal_area="facade_full",
        logo_placement="top-left",
        alignment="left",
    ),
)

LOCATION_RECIPES: tuple[VariantRecipe, ...] = (
    VariantRecipe(
        key="A",
        label="EDITORIAL LUXURY",
        direction="EDITORIAL_LUXURY",
        composition="TOP_LEFT_EDITORIAL",
        crop_strategy="editorial_left_safe",
        focal_area="skyline_right",
        logo_placement="top-left",
        alignment="left",
    ),
    VariantRecipe(
        key="B",
        label="LOCATION STORY",
        direction="LOCATION_STORY",
        composition="ASYMMETRIC_EDITORIAL",
        crop_strategy="asymmetric_left_panel",
        focal_area="neighborhood_field",
        logo_placement="top-right",
        alignment="left",
    ),
    VariantRecipe(
        key="C",
        label="ARCHITECTURAL PREMIUM",
        direction="ARCHITECTURAL_FEATURE",
        composition="IMAGE_DOMINANT",
        crop_strategy="architecture_full",
        focal_area="facade_full",
        logo_placement="top-left",
        alignment="left",
    ),
)

ARCHITECTURE_RECIPES: tuple[VariantRecipe, ...] = (
    VariantRecipe(
        key="A",
        label="EDITORIAL LUXURY",
        direction="EDITORIAL_LUXURY",
        composition="TOP_LEFT_EDITORIAL",
        crop_strategy="editorial_left_safe",
        focal_area="facade_right",
        logo_placement="top-left",
        alignment="left",
    ),
    VariantRecipe(
        key="B",
        label="INSTITUTIONAL INVESTMENT",
        direction="INFORMATIONAL_EDITORIAL",
        composition="SIDE_COLUMN",
        crop_strategy="side_column_left",
        focal_area="facade_right",
        logo_placement="top-right",
        alignment="left",
    ),
    VariantRecipe(
        key="C",
        label="ARCHITECTURAL PREMIUM",
        direction="ARCHITECTURAL_FEATURE",
        composition="IMAGE_DOMINANT",
        crop_strategy="architecture_full",
        focal_area="facade_full",
        logo_placement="top-left",
        alignment="left",
    ),
)

LIFESTYLE_RECIPES: tuple[VariantRecipe, ...] = (
    VariantRecipe(
        key="A",
        label="EDITORIAL LUXURY",
        direction="EDITORIAL_LUXURY",
        composition="TOP_LEFT_EDITORIAL",
        crop_strategy="editorial_left_safe",
        focal_area="interior_right",
        logo_placement="top-left",
        alignment="left",
    ),
    VariantRecipe(
        key="B",
        label="LIFESTYLE PREMIUM",
        direction="LIFESTYLE_PREMIUM",
        composition="LOWER_THIRD",
        crop_strategy="lower_third_safe",
        focal_area="amenity_center",
        logo_placement="top-right",
        alignment="left",
    ),
    VariantRecipe(
        key="C",
        label="ARCHITECTURAL PREMIUM",
        direction="ARCHITECTURAL_FEATURE",
        composition="IMAGE_DOMINANT",
        crop_strategy="architecture_full",
        focal_area="interior_full",
        logo_placement="top-left",
        alignment="left",
    ),
)


# Starting grammars — mutated per production. Never the only layouts.
COMPOSITION_TYPES = (
    "editorial_architecture",
    "location_story",
    "architectural_hero",
    "split_information",
)

CROP_BY_TYPE: dict[str, dict[str, Any]] = {
    "editorial_architecture": {
        "x": 16.0,
        "y": 0.0,
        "w": 84.0,
        "h": 100.0,
        "focal_bias": "right",
        "object_position": "74% 46%",
        "strategy": "editorial_left_safe",
    },
    "location_story": {
        "x": 8.0,
        "y": 4.0,
        "w": 92.0,
        "h": 96.0,
        "focal_bias": "horizon",
        "object_position": "58% 38%",
        "strategy": "location_field",
    },
    "architectural_hero": {
        "x": 0.0,
        "y": 0.0,
        "w": 100.0,
        "h": 100.0,
        "focal_bias": "facade",
        "object_position": "52% 44%",
        "strategy": "architecture_full",
    },
    "split_information": {
        "x": 28.0,
        "y": 0.0,
        "w": 72.0,
        "h": 100.0,
        "focal_bias": "right",
        "object_position": "80% 48%",
        "strategy": "asymmetric_left_panel",
    },
}


def _canvas_for_intent(intent: GenerationIntent) -> tuple[int, int]:
    preset = intent.format_preset if intent.format_preset in FORMAT_PRESETS else "square"
    return FORMAT_PRESETS.get(preset, (1080, 1080))


def _digest_int(*parts: str) -> int:
    blob = "|".join(parts)
    return int(hashlib.sha1(blob.encode("utf-8")).hexdigest()[:8], 16)


def choose_composition_type(
    *,
    campaign_type: ArtDirectorCampaign,
    recipe: VariantRecipe,
    asset: SocialDesignMediaCandidate | None,
    has_map: bool,
    instruction: str,
    refs: dict[str, Any],
) -> str:
    """Design decision — recipes hint, they do not imprison the layout."""
    subject = (asset.visual_subject or "") if asset else ""
    if campaign_type == "LOCATION":
        if recipe.key == "A":
            picked = "location_story" if subject in {"AERIAL", "NEIGHBORHOOD", "LOCATION"} else "editorial_architecture"
        elif recipe.key == "B":
            picked = "split_information" if has_map else "location_story"
        else:
            picked = "architectural_hero"
        if refs.get("image_text_balance") == "image_dominant" and recipe.key != "B":
            if subject in {"ARCHITECTURAL_RENDER", "EXTERIOR"}:
                picked = "architectural_hero" if recipe.key == "C" else picked
        return picked
    if campaign_type == "ARCHITECTURE":
        return {"A": "editorial_architecture", "B": "split_information", "C": "architectural_hero"}.get(
            recipe.key, "architectural_hero"
        )
    if campaign_type == "LIFESTYLE":
        return {"A": "editorial_architecture", "B": "location_story", "C": "architectural_hero"}.get(
            recipe.key, "editorial_architecture"
        )
    # Investment / launch: still mutate away from a single slot fill.
    return {"A": "editorial_architecture", "B": "split_information", "C": "architectural_hero"}.get(
        recipe.key, "editorial_architecture"
    )


def choose_primary_variant(
    recipes: tuple[VariantRecipe, ...],
    *,
    campaign_type: ArtDirectorCampaign,
    asset: SocialDesignMediaCandidate | None,
    instruction: str,
    has_map: bool,
) -> VariantKey:
    if campaign_type != "LOCATION" or not recipes:
        return "A"
    subject = (asset.visual_subject or "") if asset else ""
    if has_map:
        return next((r.key for r in recipes if r.key == "B"), recipes[0].key)
    if subject in {"AERIAL", "NEIGHBORHOOD", "LOCATION"}:
        return next((r.key for r in recipes if r.key == "B"), recipes[0].key)
    digest = _digest_int(instruction, subject, campaign_type)
    pool = [r.key for r in recipes if r.key != "A"] or [recipes[0].key]
    return pool[digest % len(pool)]


def _directed_regions(
    *,
    composition_type: str,
    canvas_w: int,
    canvas_h: int,
    refs: dict[str, Any],
    salt: int,
    include_support: bool,
) -> dict[str, dict[str, int]]:
    """Pixel regions from a design decision. Starting grammar, then mutate."""
    generous = refs.get("whitespace") == "generous"
    mx = max(48, int(round(canvas_w * (0.078 if generous else 0.062))))
    my = max(44, int(round(canvas_h * (0.072 if generous else 0.055))))
    jitter_x = (salt % 17) - 8
    jitter_y = ((salt // 17) % 21) - 10

    if composition_type == "split_information":
        col_w = max(320, int(round(canvas_w * 0.38)))
        headline = {
            "x": mx,
            "y": my + int(round(canvas_h * 0.16)) + jitter_y,
            "width": col_w,
            "height": int(round(canvas_h * 0.18)),
        }
        body = {
            "x": mx,
            "y": headline["y"] + headline["height"] + max(18, int(round(canvas_h * 0.02))),
            "width": col_w - 12,
            "height": int(round(canvas_h * 0.14 if include_support else 0.08)),
        }
        cta = {
            "x": mx,
            "y": min(canvas_h - my - int(round(canvas_h * 0.05)), int(round(canvas_h * 0.82)) + jitter_y // 2),
            "width": min(col_w - 8, max(200, int(round(canvas_w * 0.28)))),
            "height": max(40, int(round(canvas_h * 0.044))),
        }
        overlay = "soft-left"
        logo_project = {"x": mx, "y": my, "width": max(140, int(round(canvas_w * 0.20))), "height": max(44, int(round(canvas_h * 0.048)))}
        logo_ih = {
            "x": mx,
            "y": canvas_h - my - max(32, int(round(canvas_h * 0.032))),
            "width": max(96, int(round(canvas_w * 0.12))),
            "height": max(28, int(round(canvas_h * 0.028))),
        }
    elif composition_type == "location_story":
        col_w = max(360, int(round(canvas_w * 0.62)))
        headline = {
            "x": mx + max(0, jitter_x),
            "y": int(round(canvas_h * 0.58)) + jitter_y,
            "width": col_w,
            "height": int(round(canvas_h * 0.14)),
        }
        body = {
            "x": headline["x"],
            "y": headline["y"] + headline["height"] + max(14, int(round(canvas_h * 0.016))),
            "width": int(round(col_w * 0.86)),
            "height": int(round(canvas_h * 0.09 if include_support else 0.05)),
        }
        cta = {
            "x": headline["x"],
            "y": min(canvas_h - my - 48, body["y"] + body["height"] + 16),
            "width": max(200, int(round(canvas_w * 0.30))),
            "height": max(40, int(round(canvas_h * 0.042))),
        }
        overlay = "localized-bottom"
        logo_project = {
            "x": mx,
            "y": my,
            "width": max(150, int(round(canvas_w * 0.22))),
            "height": max(46, int(round(canvas_h * 0.05))),
        }
        logo_ih = {
            "x": canvas_w - mx - max(96, int(round(canvas_w * 0.11))),
            "y": my + 4,
            "width": max(96, int(round(canvas_w * 0.11))),
            "height": max(28, int(round(canvas_h * 0.028))),
        }
    elif composition_type == "architectural_hero":
        col_w = max(340, int(round(canvas_w * 0.48)))
        headline = {
            "x": mx + jitter_x,
            "y": my + int(round(canvas_h * 0.08)) + jitter_y,
            "width": col_w,
            "height": int(round(canvas_h * 0.16)),
        }
        body = {
            "x": headline["x"],
            "y": headline["y"] + headline["height"] + max(16, int(round(canvas_h * 0.018))),
            "width": int(round(col_w * 0.92)),
            "height": int(round(canvas_h * 0.08 if include_support else 0.04)),
        }
        cta = {
            "x": headline["x"],
            "y": min(canvas_h - my - 44, int(round(canvas_h * 0.86))),
            "width": max(180, int(round(canvas_w * 0.26))),
            "height": max(36, int(round(canvas_h * 0.04))),
        }
        overlay = "subtle-top"
        logo_project = {
            "x": mx,
            "y": my,
            "width": max(160, int(round(canvas_w * 0.24))),
            "height": max(48, int(round(canvas_h * 0.052))),
        }
        logo_ih = {
            "x": canvas_w - mx - max(92, int(round(canvas_w * 0.10))),
            "y": canvas_h - my - max(30, int(round(canvas_h * 0.03))),
            "width": max(92, int(round(canvas_w * 0.10))),
            "height": max(28, int(round(canvas_h * 0.026))),
        }
    else:
        # editorial_architecture — sky/negative-space type, not the old 7%/4% slot.
        col_w = max(380, int(round(canvas_w * 0.56)))
        headline = {
            "x": mx + jitter_x,
            "y": my + int(round(canvas_h * 0.11)) + jitter_y,
            "width": col_w,
            "height": int(round(canvas_h * 0.20)),
        }
        body = {
            "x": headline["x"],
            "y": headline["y"] + headline["height"] + max(18, int(round(canvas_h * 0.02))),
            "width": int(round(col_w * 0.88)),
            "height": int(round(canvas_h * 0.10 if include_support else 0.05)),
        }
        cta = {
            "x": headline["x"],
            "y": min(canvas_h - my - 48, int(round(canvas_h * 0.78)) + jitter_y // 2),
            "width": max(210, int(round(canvas_w * 0.32))),
            "height": max(40, int(round(canvas_h * 0.044))),
        }
        overlay = "localized-top"
        logo_project = {
            "x": mx,
            "y": my,
            "width": max(152, int(round(canvas_w * 0.21))),
            "height": max(46, int(round(canvas_h * 0.05))),
        }
        logo_ih = {
            "x": canvas_w - mx - max(100, int(round(canvas_w * 0.12))),
            "y": my,
            "width": max(100, int(round(canvas_w * 0.12))),
            "height": max(30, int(round(canvas_h * 0.03))),
        }

    eyebrow = {
        "x": headline["x"],
        "y": max(my, headline["y"] - max(28, int(round(canvas_h * 0.032)))),
        "width": min(headline["width"], int(round(canvas_w * 0.42))),
        "height": max(22, int(round(canvas_h * 0.024))),
    }
    return {
        "headline": headline,
        "body": body,
        "cta": cta,
        "eyebrow": eyebrow,
        "project_logo": logo_project,
        "investhome_logo": logo_ih,
        "overlay_meta": {"token": overlay},
    }


def _apply_region(el: DesignPlanElement, region: dict[str, int], *, font_size: int | None = None) -> DesignPlanElement:
    return replace(
        el,
        x=int(region["x"]),
        y=int(region["y"]),
        width=int(region["width"]),
        height=int(region["height"]),
        font_size=font_size if font_size is not None else el.font_size,
        align="left",
    )


def direct_plan_geometry(
    plan: DesignPlan,
    *,
    recipe: VariantRecipe,
    campaign_type: ArtDirectorCampaign,
    intent: GenerationIntent,
    package: ContentPackage,
    asset: SocialDesignMediaCandidate | None,
    logo: SocialDesignMediaCandidate | None,
    supporting_logo: SocialDesignMediaCandidate | None,
    map_asset: SocialDesignMediaCandidate | None,
    refs: dict[str, Any],
    instruction: str,
) -> DesignPlan:
    """Overwrite recipe-slot geometry with a real Design Plan that moves pixels."""
    canvas_w, canvas_h = _canvas_for_intent(intent)
    composition_type = choose_composition_type(
        campaign_type=campaign_type,
        recipe=recipe,
        asset=asset,
        has_map=map_asset is not None,
        instruction=instruction,
        refs=refs,
    )
    salt = _digest_int(
        instruction,
        recipe.key,
        composition_type,
        asset.filename if asset else "",
        package.headline,
        intent.format_preset or "square",
    )
    include_support = any(el.role == "body" for el in plan.elements)
    regions = _directed_regions(
        composition_type=composition_type,
        canvas_w=canvas_w,
        canvas_h=canvas_h,
        refs=refs,
        salt=salt,
        include_support=include_support,
    )
    headline_font = 52 if composition_type == "architectural_hero" else (46 if composition_type == "location_story" else 50)
    headline_font = max(36, min(72, int(round(canvas_w * (0.048 if composition_type == "location_story" else 0.054)))))
    body_font = max(16, min(26, int(round(canvas_w * 0.022))))
    eyebrow_font = max(12, min(18, int(round(canvas_w * 0.016))))

    directed: list[DesignPlanElement] = []
    for el in plan.elements:
        if el.role == "headline":
            directed.append(_apply_region(el, regions["headline"], font_size=headline_font))
        elif el.role == "body":
            directed.append(_apply_region(el, regions["body"], font_size=body_font))
        elif el.role == "eyebrow":
            directed.append(_apply_region(el, regions["eyebrow"], font_size=eyebrow_font))
        elif el.role == "cta" or el.type in {"BUTTON", "CTA"}:
            directed.append(_apply_region(el, regions["cta"]))
        else:
            directed.append(el)

    crop = dict(CROP_BY_TYPE.get(composition_type) or CROP_BY_TYPE["editorial_architecture"])
    if composition_type == "architectural_hero":
        crop["object_position"] = "50% 42%"
    overlay_token = str(regions["overlay_meta"]["token"])
    project_logo = dict(regions["project_logo"])
    if logo is not None:
        project_logo["asset_id"] = str(logo.asset_id)
    investhome_logo: dict[str, Any] = dict(regions["investhome_logo"])
    if supporting_logo is not None:
        investhome_logo["asset_id"] = str(supporting_logo.asset_id)
    else:
        investhome_logo = {}
    map_spec: dict[str, Any] = {}
    if map_asset is not None and composition_type in {"split_information", "location_story"}:
        map_w = max(180, int(round(canvas_w * 0.28)))
        map_h = max(140, int(round(canvas_h * 0.18)))
        map_spec = {
            "asset_id": str(map_asset.asset_id),
            "x": canvas_w - max(48, int(round(canvas_w * 0.06))) - map_w,
            "y": canvas_h - max(48, int(round(canvas_h * 0.08))) - map_h,
            "width": map_w,
            "height": map_h,
        }

    plan.elements = directed
    plan.overlay = overlay_token
    plan.alignment = "left"
    plan.preserve_geometry = True
    plan.image_crop = crop
    plan.project_logo = project_logo if logo is not None else {}
    plan.investhome_logo = investhome_logo
    plan.map_asset = map_spec
    plan.composition_type = composition_type
    plan.safe_text_zone = "bottom" if composition_type == "location_story" else "top"
    return plan


def campaign_type_from_intent(kind: CampaignIntentKind | str) -> ArtDirectorCampaign:
    key = str(kind or "").strip().lower()
    if key in {"location", "neighborhood"}:
        return "LOCATION"
    if key in {"investment", "rental_income", "value_proposition"}:
        return "INVESTMENT"
    if key == "architecture":
        return "ARCHITECTURE"
    if key in {"lifestyle", "amenities"}:
        return "LIFESTYLE"
    if key in {"launch", "availability"}:
        return "LAUNCH"
    return "PROJECT_OVERVIEW"


def recipes_for_campaign(campaign_type: ArtDirectorCampaign) -> tuple[VariantRecipe, ...]:
    if campaign_type == "LOCATION":
        return LOCATION_RECIPES
    if campaign_type == "ARCHITECTURE":
        return ARCHITECTURE_RECIPES
    if campaign_type == "LIFESTYLE":
        return LIFESTYLE_RECIPES
    if campaign_type in {"LAUNCH", "PROJECT_OVERVIEW"}:
        return INVESTMENT_RECIPES if campaign_type == "LAUNCH" else LOCATION_RECIPES
    return INVESTMENT_RECIPES


def select_real_asset(
    candidates: list[SocialDesignMediaCandidate],
    *,
    campaign_type: ArtDirectorCampaign,
    exclude_asset_ids: set[UUID] | None = None,
) -> SocialDesignMediaCandidate | None:
    skip = {str(a) for a in (exclude_asset_ids or set())}
    filtered = [c for c in candidates if str(c.asset_id) not in skip]
    picked_id = pick_best_asset(filtered, require_image=True, campaign_type=campaign_type)
    if picked_id is None:
        return None
    return next((c for c in filtered if c.asset_id == picked_id), None)


def financial_facts_source(campaign_intelligence: Any) -> str:
    if campaign_intelligence is None:
        return "none"
    facts = list(getattr(campaign_intelligence, "verified_campaign_facts", []) or [])
    sources = []
    for fact in facts:
        src = str(getattr(fact, "source", "") or "")
        if src and src not in sources:
            sources.append(src)
    if "user_campaign_input" in sources:
        return "user_campaign_input"
    if sources:
        return sources[0]
    return "none"


def build_provenance(
    *,
    project_id: UUID,
    asset: SocialDesignMediaCandidate | None,
    logo: SocialDesignMediaCandidate | None,
    campaign_intelligence: Any,
) -> ArtDirectorProvenance:
    logo_status = "approved_logo" if logo is not None else "no_approved_logo"
    return ArtDirectorProvenance(
        project_id=project_id,
        selected_asset_id=asset.asset_id if asset else None,
        source=asset.provenance_source if asset else None,
        filename=asset.filename if asset else None,
        category=asset.folder_category if asset else None,
        visual_subject=asset.visual_subject if asset else None,
        financial_facts_source=financial_facts_source(campaign_intelligence),
        logo_asset_id=logo.asset_id if logo else None,
        logo_status=logo_status,
    )


def _concept_with_plan(concept: CreativeConcept, plan: CreativePlan, recipe: VariantRecipe) -> CreativeConcept:
    density_legacy = DENSITY_TO_LEGACY.get(plan.copy_density, "sparse")
    return replace(
        concept,
        composition_strategy=plan.family,  # type: ignore[arg-type]
        alignment=recipe.alignment,  # type: ignore[arg-type]
        overlay_region=plan.overlay_region,  # type: ignore[arg-type]
        text_density=density_legacy,  # type: ignore[arg-type]
        include_eyebrow=plan.include_eyebrow,
        include_support=plan.include_support,
        include_cta=plan.include_cta,
        safe_text_zone=plan.safe_text_zone,  # type: ignore[arg-type]
        creative_direction=plan.creative_direction,
        composition_primitive=recipe.composition,
        copy_density_kind=plan.copy_density,
        cta_strategy=plan.cta_strategy,
        contrast_kind=plan.contrast_strategy,
        brand_treatment=plan.brand_treatment,
        visual_priority=plan.visual_priority,
        creative_plan=creative_plan_to_dict(plan),
        contrast_strategy=plan.overlay_strategy,
        composition_blueprint={},
    )


def _force_plan(
    *,
    concept: CreativeConcept,
    recipe: VariantRecipe,
    campaign_type: ArtDirectorCampaign,
    has_metrics: bool,
    intent: GenerationIntent,
    instruction: str,
) -> CreativePlan:
    creative_intent = concept.creative_intent
    plan = build_creative_plan(
        intent=creative_intent,
        audience=concept.tone or intent.audience or "general",
        objective=str(concept.objective),
        profile=concept.asset_profile,
        has_eligible_metrics=has_metrics,
        copy_length=len(concept.primary_message or "") + len(concept.supporting_message or ""),
        format_preset=intent.format_preset or "square",
        campaign_goal=campaign_type,
        tone=concept.tone or intent.tone or "premium",
        used_signals=[],
        instruction=f"{instruction} {recipe.label} {recipe.composition}",
        project_name=concept.project_identity_line or "",
        force_direction=recipe.direction,
        force_composition=recipe.composition,  # type: ignore[arg-type]
    )
    if campaign_type == "INVESTMENT" and has_metrics:
        plan.include_metrics = True
        plan.metric_strategy = "STRUCTURED_GROUP"
        plan.include_support = False
        if recipe.direction == "EDITORIAL_LUXURY":
            plan.copy_density = "LOW"
            plan.include_eyebrow = True
            plan.include_cta = True
            plan.cta_strategy = "TEXT_LINK_STYLE"
        elif recipe.direction == "INVESTMENT_DATA":
            plan.copy_density = "DATA_RICH"
            plan.include_eyebrow = True
            plan.include_cta = True
            plan.cta_strategy = "PILL_BUTTON"
        elif recipe.direction == "ARCHITECTURAL_FEATURE":
            plan.copy_density = "MINIMAL"
            plan.include_eyebrow = False
            plan.include_cta = True
            plan.cta_strategy = "MINIMAL_BUTTON"
    else:
        plan.include_metrics = False
        plan.metric_strategy = "NONE"
        if campaign_type == "LOCATION":
            plan.include_support = recipe.direction != "ARCHITECTURAL_FEATURE"
            plan.include_cta = True
    plan.alignment = recipe.alignment
    plan.composition = recipe.composition  # type: ignore[assignment]
    return plan


def art_director_plan_payload(
    plan: DesignPlan,
    *,
    recipe: VariantRecipe,
    campaign_type: ArtDirectorCampaign,
    package: ContentPackage,
    asset: SocialDesignMediaCandidate | None,
    logo: SocialDesignMediaCandidate | None,
    provenance: ArtDirectorProvenance,
    structured_metrics: list[dict[str, Any]] | None,
    refs: dict[str, Any] | None = None,
    canvas_w: int = 1080,
    canvas_h: int = 1080,
) -> dict[str, Any]:
    headline_el = next((el for el in plan.elements if el.role == "headline"), None)
    support_el = next((el for el in plan.elements if el.role == "body"), None)
    cta_el = next((el for el in plan.elements if el.role == "cta" or el.type in {"BUTTON", "CTA"}), None)
    headline = headline_el.text if headline_el is not None else package.headline
    support = support_el.text if support_el is not None else package.supporting_text
    cta = cta_el.text if cta_el is not None else package.cta
    hierarchy = {
        "level_1": "headline",
        "level_2": "metrics" if campaign_type == "INVESTMENT" else "supporting_copy",
        "level_3": "cta",
        "brand": "project_logo",
    }
    payload = design_plan_to_dict(plan)
    payload.update(
        {
            "campaign_type": campaign_type,
            "creative_direction": recipe.direction,
            "asset_id": str(asset.asset_id) if asset else None,
            "crop_strategy": (plan.image_crop or {}).get("strategy") or recipe.crop_strategy,
            "focal_area": recipe.focal_area,
            "overlay": plan.overlay,
            "headline": {
                "text": headline,
                "x": headline_el.x if headline_el else 0,
                "y": headline_el.y if headline_el else 0,
                "width": headline_el.width if headline_el else 0,
                "font_family": "sans-serif",
                "font_size": headline_el.font_size if headline_el else None,
                "weight": headline_el.font_weight if headline_el else "bold",
                "color": headline_el.color if headline_el else "#ffffff",
                "alignment": headline_el.align if headline_el else "left",
            },
            "supporting_copy": support,
            "supporting_text": {
                "text": support,
                "x": support_el.x if support_el else None,
                "y": support_el.y if support_el else None,
                "width": support_el.width if support_el else None,
                "font_size": support_el.font_size if support_el else None,
                "weight": support_el.font_weight if support_el else "normal",
                "color": support_el.color if support_el else "#ffffff",
                "alignment": support_el.align if support_el else "left",
            }
            if support_el
            else None,
            "metrics": structured_metrics or [],
            "cta": cta,
            "logo_placement": recipe.logo_placement if logo else "none",
            "logo_asset_id": str(logo.asset_id) if logo else None,
            "project_logo": plan.project_logo,
            "investhome_logo": plan.investhome_logo,
            "typography_hierarchy": hierarchy,
            "alignment": plan.alignment or "left",
            "composition": plan.composition_type or recipe.composition,
            "composition_type": plan.composition_type,
            "contrast_strategy": plan.overlay,
            "canvas": {"width": canvas_w, "height": canvas_h, "format": plan.format_preset},
            "background": {
                "asset_id": plan.background_asset_id,
                "strategy": "hero_photograph",
            },
            "image_strategy": (plan.image_crop or {}).get("focal_bias") or recipe.focal_area,
            "image_crop": plan.image_crop,
            "location_elements": [plan.map_asset] if plan.map_asset else [],
            "graphic_elements": [{"kind": "overlay", "token": plan.overlay}],
            "information_blocks": [
                {"role": el.role, "x": el.x, "y": el.y, "width": el.width, "height": el.height}
                for el in plan.elements
                if el.role in {"body", "eyebrow"}
            ],
            "visual_hierarchy": hierarchy,
            "design_references": (refs or {}).get("references") or [],
            "variant": recipe.key,
            "variant_label": recipe.label,
            "provenance": provenance.model_dump(mode="json"),
        }
    )
    return payload


@dataclass
class ArtDirectorSession:
    campaign_type: ArtDirectorCampaign
    selected_asset: SocialDesignMediaCandidate | None
    logo: SocialDesignMediaCandidate | None
    provenance: ArtDirectorProvenance
    variants: list[ArtDirectorVariant] = field(default_factory=list)
    selected_variant: VariantKey = "A"
    ops: list[dict[str, Any]] = field(default_factory=list)
    design_plan: DesignPlan | None = None
    warnings: list[str] = field(default_factory=list)
    supporting_logo: SocialDesignMediaCandidate | None = None
    map_asset: SocialDesignMediaCandidate | None = None


def build_art_director_session(
    *,
    project_id: UUID,
    instruction: str,
    campaign_type: ArtDirectorCampaign,
    intent: GenerationIntent,
    concept: CreativeConcept,
    package: ContentPackage,
    candidates: list[SocialDesignMediaCandidate],
    campaign_intelligence: Any,
    structured_metrics: list[Any] | None,
    post_id: str,
    rebuild: bool,
    linked_project_id: UUID,
    exclude_asset_ids: set[UUID] | None = None,
) -> ArtDirectorSession:
    warnings: list[str] = []
    ident = getattr(getattr(campaign_intelligence, "project_knowledge", None), "project_identity", None) or {}
    if not isinstance(ident, dict):
        ident = {}
    asset = select_real_asset(candidates, campaign_type=campaign_type, exclude_asset_ids=exclude_asset_ids)
    logo = pick_logo_asset(
        candidates,
        project_name=str(ident.get("project_name") or concept.project_identity_line or intent.project_hint or ""),
        project_code=str(ident.get("project_code") or "") or None,
    )
    supporting_logo = pick_supporting_logo_asset(
        candidates,
        project_logo=logo,
        project_name=str(ident.get("project_name") or concept.project_identity_line or ""),
    )
    map_asset = pick_map_asset(candidates) if campaign_type == "LOCATION" else None
    refs = extract_design_reference_language(
        candidates,
        project_name=str(ident.get("project_name") or concept.project_identity_line or ""),
    )
    if logo is None:
        warnings.append("no_approved_logo")
    if asset is None:
        warnings.append("no_valid_project_media")
        warnings.append("art_director_failed_no_real_asset")
        provenance = build_provenance(
            project_id=project_id,
            asset=None,
            logo=logo,
            campaign_intelligence=campaign_intelligence,
        )
        return ArtDirectorSession(
            campaign_type=campaign_type,
            selected_asset=None,
            logo=logo,
            provenance=provenance,
            warnings=warnings,
        )

    has_metrics = bool(structured_metrics) and campaign_type == "INVESTMENT"
    metric_dicts: list[dict[str, Any]] = []
    if has_metrics and structured_metrics:
        from investhome_api.services.social_design_engine.metrics import structured_metrics_to_dicts

        if structured_metrics and hasattr(structured_metrics[0], "display_value"):
            metric_dicts = structured_metrics_to_dicts(list(structured_metrics))
        else:
            metric_dicts = [row for row in structured_metrics if isinstance(row, dict)]

    provenance = build_provenance(
        project_id=project_id,
        asset=asset,
        logo=logo,
        campaign_intelligence=campaign_intelligence,
    )
    recipes = recipes_for_campaign(campaign_type)
    variants: list[ArtDirectorVariant] = []
    primary_ops: list[dict[str, Any]] = []
    primary_plan: DesignPlan | None = None

    from investhome_api.services.social_design_engine.apply import apply_ops
    from investhome_api.services.social_design_engine.ops import validate_ops

    allowed_ids = {asset.asset_id}
    if logo is not None:
        allowed_ids.add(logo.asset_id)
    if supporting_logo is not None:
        allowed_ids.add(supporting_logo.asset_id)
    if map_asset is not None:
        allowed_ids.add(map_asset.asset_id)
    selected_key = choose_primary_variant(
        recipes,
        campaign_type=campaign_type,
        asset=asset,
        instruction=instruction,
        has_map=map_asset is not None,
    )
    canvas_w, canvas_h = _canvas_for_intent(intent)

    for recipe in recipes:
        plan_model = _force_plan(
            concept=concept,
            recipe=recipe,
            campaign_type=campaign_type,
            has_metrics=has_metrics,
            intent=intent,
            instruction=instruction,
        )
        variant_concept = _concept_with_plan(concept, plan_model, recipe)
        if campaign_type != "INVESTMENT":
            variant_concept.structured_metrics = []
        design = build_design_plan(
            package=package,
            intent=intent,
            picked_asset_id=asset.asset_id,
            post_id=post_id,
            rebuild=rebuild,
            concept=variant_concept,
            structured_metrics=metric_dicts if has_metrics and plan_model.include_metrics else None,
            force_composition_family=PRIMITIVE_FAMILY_HINT.get(recipe.composition),
        )
        design.name = f"{recipe.key} · {recipe.label}"
        design = direct_plan_geometry(
            design,
            recipe=recipe,
            campaign_type=campaign_type,
            intent=intent,
            package=package,
            asset=asset,
            logo=logo,
            supporting_logo=supporting_logo,
            map_asset=map_asset,
            refs=refs,
            instruction=instruction,
        )
        ops = compose_ops_from_plan(
            design,
            linked_project_id=linked_project_id,
            instruction=instruction,
            logo_asset_id=logo.asset_id if logo else None,
            logo_placement="none" if design.project_logo else (recipe.logo_placement if logo else "none"),
            project_name=concept.project_identity_line or "",
        )
        accepted, _rejected = validate_ops(
            ops,
            linked_project_id=linked_project_id,
            posts=[],
            allowed_asset_ids=allowed_ids,
        )
        posts, _selected = apply_ops(
            [],
            accepted,
            linked_project_id=linked_project_id,
            selected_post_id=None,
        )
        post = posts[0] if posts else {}
        payload = art_director_plan_payload(
            design,
            recipe=recipe,
            campaign_type=campaign_type,
            package=package,
            asset=asset,
            logo=logo,
            provenance=provenance,
            structured_metrics=metric_dicts if has_metrics and plan_model.include_metrics else [],
            refs=refs,
            canvas_w=canvas_w,
            canvas_h=canvas_h,
        )
        variants.append(
            ArtDirectorVariant(
                key=recipe.key,
                label=recipe.label,
                creative_direction=recipe.direction,
                composition=design.composition_type or recipe.composition,
                campaign_type=campaign_type,
                design_plan=payload,
                post=post,
                provenance=provenance,
            )
        )
        if recipe.key == selected_key:
            primary_ops = ops
            primary_plan = design

    return ArtDirectorSession(
        campaign_type=campaign_type,
        selected_asset=asset,
        logo=logo,
        provenance=provenance,
        variants=variants,
        selected_variant=selected_key,
        ops=primary_ops,
        design_plan=primary_plan,
        warnings=warnings,
        supporting_logo=supporting_logo,
        map_asset=map_asset,
    )


def selected_asset_indicator(asset: SocialDesignMediaCandidate | None) -> dict[str, Any] | None:
    if asset is None:
        return None
    return {
        "asset_id": str(asset.asset_id),
        "filename": asset.filename,
        "category": asset.folder_category,
        "visual_subject": asset.visual_subject,
        "source": asset.provenance_source,
        "score": asset.score,
    }
