"""Investhome Art Director — plan before render, real assets only.

Produces three editable DesignPlans (A/B/C) from the same real project asset
pool. Never reconstructs architecture via text-to-image.
"""

from __future__ import annotations

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
    GenerationIntent,
    build_design_plan,
    compose_ops_from_plan,
    design_plan_to_dict,
)
from investhome_api.services.social_design_engine.composition_engine import PRIMITIVE_FAMILY_HINT
from investhome_api.services.social_design_engine.media import pick_best_asset, pick_logo_asset

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
) -> dict[str, Any]:
    headline = package.headline
    support = package.supporting_text
    cta = package.cta
    for el in plan.elements:
        if el.role == "headline":
            headline = el.text
        elif el.role == "body":
            support = el.text
        elif el.role == "cta":
            cta = el.text
    hierarchy = {
        "level_1": "headline",
        "level_2": "metrics" if campaign_type == "INVESTMENT" else "supporting_copy",
        "level_3": "cta",
    }
    payload = design_plan_to_dict(plan)
    payload.update(
        {
            "campaign_type": campaign_type,
            "creative_direction": recipe.direction,
            "asset_id": str(asset.asset_id) if asset else None,
            "crop_strategy": recipe.crop_strategy,
            "focal_area": recipe.focal_area,
            "overlay": plan.overlay,
            "headline": headline,
            "supporting_copy": support,
            "metrics": structured_metrics or [],
            "cta": cta,
            "logo_placement": recipe.logo_placement if logo else "none",
            "logo_asset_id": str(logo.asset_id) if logo else None,
            "typography_hierarchy": hierarchy,
            "alignment": recipe.alignment,
            "composition": recipe.composition,
            "contrast_strategy": plan.overlay,
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
    asset = select_real_asset(candidates, campaign_type=campaign_type, exclude_asset_ids=exclude_asset_ids)
    logo = pick_logo_asset(candidates)
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
        ops = compose_ops_from_plan(
            design,
            linked_project_id=linked_project_id,
            instruction=instruction,
            logo_asset_id=logo.asset_id if logo else None,
            logo_placement=recipe.logo_placement if logo else "none",
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
        )
        variants.append(
            ArtDirectorVariant(
                key=recipe.key,
                label=recipe.label,
                creative_direction=recipe.direction,
                composition=recipe.composition,
                campaign_type=campaign_type,
                design_plan=payload,
                post=post,
                provenance=provenance,
            )
        )
        if recipe.key == "A":
            primary_ops = ops
            primary_plan = design

    return ArtDirectorSession(
        campaign_type=campaign_type,
        selected_asset=asset,
        logo=logo,
        provenance=provenance,
        variants=variants,
        selected_variant="A",
        ops=primary_ops,
        design_plan=primary_plan,
        warnings=warnings,
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
