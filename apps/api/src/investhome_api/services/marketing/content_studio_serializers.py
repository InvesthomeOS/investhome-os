"""Serialize marketing content studio ORM models for API responses."""

from __future__ import annotations

from investhome_api.models.marketing import MarketingApproval
from investhome_api.models.marketing_content_studio import (
    AIContentGenerationRecord,
    ApprovedClaim,
    AssetRights,
    AssetUsageRecord,
    BrandComplianceResult,
    BrandTerminology,
    ContentTranslation,
    ContentVariant,
    ContentVersion,
    MarketingAsset,
    MarketingBrandProfile,
    MarketingContent,
    MarketingContentBrief,
    MarketingTemplate,
    ProhibitedClaim,
    TemplatePlaceholder,
    TemplateVersion,
)


def _enum(val):
    return val.value if hasattr(val, "value") else val


def content_dict(content: MarketingContent) -> dict:
    return {
        "id": str(content.id),
        "title": content.title,
        "code": content.code,
        "description": content.description,
        "content_type": content.content_type,
        "format": content.format,
        "status": _enum(content.status),
        "owner_user_id": str(content.owner_user_id) if content.owner_user_id else None,
        "team_id": str(content.team_id) if content.team_id else None,
        "primary_language": content.primary_language,
        "project_ids": content.project_ids,
        "property_ids": content.property_ids,
        "audience_ids": content.audience_ids,
        "campaign_ids": content.campaign_ids,
        "asset_ids": content.asset_ids,
        "channel_ids": content.channel_ids,
        "current_version_id": str(content.current_version_id) if content.current_version_id else None,
        "scheduled_at": content.scheduled_at,
        "published_at": content.published_at,
        "expires_at": content.expires_at,
        "tags": content.tags,
        "archived_at": content.archived_at,
        "created_at": content.created_at,
        "updated_at": content.updated_at,
    }


def brief_dict(brief: MarketingContentBrief) -> dict:
    return {
        "id": str(brief.id),
        "content_id": str(brief.content_id),
        "objective": brief.objective,
        "target_audience": brief.target_audience,
        "key_messages": brief.key_messages,
        "tone_and_voice": brief.tone_and_voice,
        "deliverables": brief.deliverables,
        "constraints": brief.constraints,
        "success_criteria": brief.success_criteria,
        "created_at": brief.created_at,
        "updated_at": brief.updated_at,
    }


def version_dict(version: ContentVersion) -> dict:
    return {
        "id": str(version.id),
        "content_id": str(version.content_id),
        "version_number": version.version_number,
        "label": version.label,
        "body_json": version.body_json,
        "document_id": str(version.document_id) if version.document_id else None,
        "change_summary": version.change_summary,
        "is_published": version.is_published,
        "created_at": version.created_at,
    }


def variant_dict(variant: ContentVariant) -> dict:
    return {
        "id": str(variant.id),
        "content_id": str(variant.content_id),
        "version_id": str(variant.version_id) if variant.version_id else None,
        "channel_id": str(variant.channel_id) if variant.channel_id else None,
        "channel_category": variant.channel_category,
        "variant_key": variant.variant_key,
        "title": variant.title,
        "body_json": variant.body_json,
        "validation_status": variant.validation_status,
        "validation_errors": variant.validation_errors,
        "created_at": variant.created_at,
        "updated_at": variant.updated_at,
    }


def translation_dict(translation: ContentTranslation) -> dict:
    return {
        "id": str(translation.id),
        "content_id": str(translation.content_id),
        "version_id": str(translation.version_id) if translation.version_id else None,
        "locale": translation.locale,
        "title": translation.title,
        "body_json": translation.body_json,
        "is_outdated": translation.is_outdated,
        "created_at": translation.created_at,
        "updated_at": translation.updated_at,
    }


def approval_dict(approval: MarketingApproval) -> dict:
    return {
        "id": str(approval.id),
        "entity_type": approval.entity_type,
        "entity_id": str(approval.entity_id),
        "version_id": str(approval.version_id) if approval.version_id else None,
        "approval_type": _enum(approval.approval_type),
        "status": _enum(approval.status),
        "notes": approval.notes,
        "created_at": approval.created_at,
    }


def ai_record_dict(record: AIContentGenerationRecord) -> dict:
    return {
        "id": str(record.id),
        "content_id": str(record.content_id) if record.content_id else None,
        "version_id": str(record.version_id) if record.version_id else None,
        "prompt": record.prompt,
        "provider": record.provider,
        "status": _enum(record.status),
        "requires_review": record.status.value in {"pending_review", "pending"},
        "created_at": record.created_at,
    }


def rights_dict(rights: AssetRights) -> dict:
    return {
        "id": str(rights.id),
        "asset_id": str(rights.asset_id),
        "license_type": rights.license_type,
        "holder": rights.holder,
        "valid_from": rights.valid_from,
        "valid_until": rights.valid_until,
        "territory": rights.territory,
        "usage_restrictions": rights.usage_restrictions,
        "attribution_required": rights.attribution_required,
        "status": _enum(rights.status),
    }


def usage_dict(usage: AssetUsageRecord) -> dict:
    return {
        "id": str(usage.id),
        "asset_id": str(usage.asset_id),
        "entity_type": usage.entity_type,
        "entity_id": str(usage.entity_id),
        "usage_context": usage.usage_context,
        "channel_id": str(usage.channel_id) if usage.channel_id else None,
        "recorded_at": usage.recorded_at,
    }


def brand_profile_dict(profile: MarketingBrandProfile) -> dict:
    return {
        "id": str(profile.id),
        "name": profile.name,
        "description": profile.description,
        "company_brand_id": str(profile.company_brand_id) if profile.company_brand_id else None,
        "colors_json": profile.colors_json,
        "typography_json": profile.typography_json,
        "voice_json": profile.voice_json,
        "guidelines_json": profile.guidelines_json,
        "logo_asset_ids": profile.logo_asset_ids,
        "status": profile.status,
        "is_default": profile.is_default,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
    }


def terminology_dict(term: BrandTerminology) -> dict:
    return {
        "id": str(term.id),
        "brand_profile_id": str(term.brand_profile_id),
        "term": term.term,
        "preferred_usage": term.preferred_usage,
        "avoid_usage": term.avoid_usage,
        "definition": term.definition,
        "category": term.category,
        "is_active": term.is_active,
    }


def claim_dict(claim: ApprovedClaim | ProhibitedClaim) -> dict:
    base = {
        "id": str(claim.id),
        "brand_profile_id": str(claim.brand_profile_id),
        "claim_text": claim.claim_text,
        "is_active": claim.is_active,
    }
    if isinstance(claim, ApprovedClaim):
        base.update({"category": claim.category, "evidence_ref": claim.evidence_ref, "valid_until": claim.valid_until})
    else:
        base.update({"reason": claim.reason, "severity": claim.severity})
    return base


def compliance_dict(result: BrandComplianceResult) -> dict:
    return {
        "id": str(result.id),
        "content_id": str(result.content_id) if result.content_id else None,
        "version_id": str(result.version_id) if result.version_id else None,
        "brand_profile_id": str(result.brand_profile_id) if result.brand_profile_id else None,
        "status": result.status,
        "violations_json": result.violations_json,
        "warnings_json": result.warnings_json,
        "checked_at": result.checked_at,
    }


def template_dict(template: MarketingTemplate) -> dict:
    return {
        "id": str(template.id),
        "name": template.name,
        "description": template.description,
        "template_type": _enum(template.template_type),
        "content_type": template.content_type,
        "channel_category": template.channel_category,
        "status": _enum(template.status),
        "current_version_id": str(template.current_version_id) if template.current_version_id else None,
        "created_at": template.created_at,
        "updated_at": template.updated_at,
    }


def placeholder_dict(ph: TemplatePlaceholder) -> dict:
    return {
        "id": str(ph.id),
        "template_id": str(ph.template_id),
        "placeholder_key": ph.placeholder_key,
        "label": ph.label,
        "placeholder_type": ph.placeholder_type,
        "required": ph.required,
        "default_value": ph.default_value,
        "sort_order": ph.sort_order,
    }
