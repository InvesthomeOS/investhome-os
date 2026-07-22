"""Marketing content studio domain models — content, assets, brand, templates."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class MarketingContentStatus(str, enum.Enum):
    IDEA = "idea"
    REQUESTED = "requested"
    BRIEFING = "briefing"
    DRAFT = "draft"
    IN_PRODUCTION = "in_production"
    INTERNAL_REVIEW = "internal_review"
    PENDING_BRAND_REVIEW = "pending_brand_review"
    PENDING_LEGAL_REVIEW = "pending_legal_review"
    PENDING_COMPLIANCE_REVIEW = "pending_compliance_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class PublishingReadinessState(str, enum.Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


class AssetRightsStatus(str, enum.Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    CLEARED = "cleared"
    RESTRICTED = "restricted"
    EXPIRED = "expired"


class MarketingAssetType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    LOGO = "logo"
    BROCHURE = "brochure"
    PDF = "pdf"
    SOCIAL_POST = "social_post"
    BLOG = "blog"
    EMAIL_TEMPLATE = "email_template"
    PRESENTATION = "presentation"
    DOCUMENT = "document"
    AUDIO = "audio"
    OTHER = "other"


class MarketingAssetStatus(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    ACTIVE = "active"  # legacy synonym of ready; retained for existing rows
    ARCHIVED = "archived"


class MarketingAssetFolder(str, enum.Enum):
    PROJECTS = "projects"
    CAMPAIGNS = "campaigns"
    BRAND = "brand"
    LOGOS = "logos"
    VIDEOS = "videos"
    SOCIAL = "social"
    DOCUMENTS = "documents"


class MarketingTemplateType(str, enum.Enum):
    EMAIL = "email"
    SOCIAL = "social"
    LANDING_PAGE = "landing_page"
    AD_CREATIVE = "ad_creative"
    DOCUMENT = "document"
    OTHER = "other"


class MarketingTemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class AIGenerationStatus(str, enum.Enum):
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class MarketingContent(Base):
    __tablename__ = "marketing_contents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[MarketingContentStatus] = mapped_column(
        Enum(MarketingContentStatus, native_enum=False, length=40),
        nullable=False,
        default=MarketingContentStatus.IDEA,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    primary_language: Mapped[str] = mapped_column(String(10), server_default="en", nullable=False)
    project_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    property_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    audience_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    campaign_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    channel_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_contents_status", "status"),
        Index("ix_marketing_contents_content_type", "content_type"),
        Index("ix_marketing_contents_owner_user_id", "owner_user_id"),
        Index("ix_marketing_contents_scheduled_at", "scheduled_at"),
        Index("ix_marketing_contents_archived_at", "archived_at"),
    )


class MarketingContentBrief(Base):
    __tablename__ = "marketing_content_briefs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_messages: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone_and_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    deliverables: Mapped[str | None] = mapped_column(Text, nullable=True)
    constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_criteria: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ContentVersion(Base):
    __tablename__ = "marketing_content_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_content_versions_content_id", "content_id"),)


class ContentVariant(Base):
    __tablename__ = "marketing_content_variants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    channel_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    variant_key: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(20), server_default="pending", nullable=False)
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_content_variants_content_id", "content_id"),)


class ContentTranslation(Base):
    __tablename__ = "marketing_content_translations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    locale: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_outdated: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_content_translations_content_id", "content_id"),)


class ContentTypeFieldRegistry(Base):
    __tablename__ = "marketing_content_type_field_registry"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_type: Mapped[str] = mapped_column(String(30), nullable=False)
    format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    channel_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    field_key: Mapped[str] = mapped_column(String(80), nullable=False)
    field_label: Mapped[str] = mapped_column(String(120), nullable=False)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    constraints_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_mkt_content_type_registry_type", "content_type"),)


class MarketingAsset(Base):
    __tablename__ = "marketing_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[MarketingAssetType] = mapped_column(
        Enum(MarketingAssetType, native_enum=False, length=40),
        nullable=False,
    )
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[MarketingAssetStatus] = mapped_column(
        Enum(MarketingAssetStatus, native_enum=False, length=30),
        nullable=False,
        default=MarketingAssetStatus.DRAFT,
    )
    folder: Mapped[str | None] = mapped_column(String(40), nullable=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    ai_prep_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rights_status: Mapped[AssetRightsStatus] = mapped_column(
        Enum(AssetRightsStatus, native_enum=False, length=30),
        nullable=False,
        default=AssetRightsStatus.UNKNOWN,
    )
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_assets_asset_type", "asset_type"),
        Index("ix_marketing_assets_rights_status", "rights_status"),
        Index("ix_marketing_assets_status", "status"),
        Index("ix_marketing_assets_folder", "folder"),
        Index("ix_marketing_assets_project_id", "project_id"),
        Index("ix_marketing_assets_campaign_id", "campaign_id"),
    )


class AssetRights(Base):
    __tablename__ = "marketing_asset_rights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_assets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    license_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    holder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    territory: Mapped[str | None] = mapped_column(String(120), nullable=True)
    usage_restrictions: Mapped[str | None] = mapped_column(Text, nullable=True)
    attribution_required: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    status: Mapped[AssetRightsStatus] = mapped_column(
        Enum(AssetRightsStatus, native_enum=False, length=30),
        nullable=False,
        default=AssetRightsStatus.UNKNOWN,
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class AssetUsageRecord(Base):
    __tablename__ = "marketing_asset_usage_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_assets.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    usage_context: Mapped[str | None] = mapped_column(String(80), nullable=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_asset_usage_asset_id", "asset_id"),
        Index("ix_marketing_asset_usage_entity", "entity_type", "entity_id"),
    )


class MarketingBrandProfile(Base):
    """Marketing Brand Center profile — references company BrandProfile optionally."""

    __tablename__ = "marketing_brand_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("brand_profiles.id", ondelete="SET NULL"), nullable=True
    )
    colors_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    typography_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    voice_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    guidelines_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    logo_asset_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="active", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BrandTerminology(Base):
    __tablename__ = "marketing_brand_terminology"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_brand_profiles.id", ondelete="CASCADE"), nullable=False
    )
    term: Mapped[str] = mapped_column(String(120), nullable=False)
    preferred_usage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avoid_usage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    definition: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_brand_terminology_profile", "brand_profile_id"),)


class ApprovedClaim(Base):
    __tablename__ = "marketing_approved_claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_brand_profiles.id", ondelete="CASCADE"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ProhibitedClaim(Base):
    __tablename__ = "marketing_prohibited_claims"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    brand_profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_brand_profiles.id", ondelete="CASCADE"), nullable=False
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(20), server_default="warning", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class BrandComplianceResult(Base):
    __tablename__ = "marketing_brand_compliance_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    brand_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_brand_profiles.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    violations_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    checked_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class MarketingTemplate(Base):
    __tablename__ = "marketing_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_type: Mapped[MarketingTemplateType] = mapped_column(
        Enum(MarketingTemplateType, native_enum=False, length=40),
        nullable=False,
    )
    content_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    channel_category: Mapped[str | None] = mapped_column(String(30), nullable=True)
    status: Mapped[MarketingTemplateStatus] = mapped_column(
        Enum(MarketingTemplateStatus, native_enum=False, length=30),
        nullable=False,
        default=MarketingTemplateStatus.DRAFT,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_templates_template_type", "template_type"),
        Index("ix_marketing_templates_status", "status"),
    )


class TemplateVersion(Base):
    __tablename__ = "marketing_template_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_templates.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(nullable=False)
    body_template: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_template_versions_template_id", "template_id"),)


class TemplatePlaceholder(Base):
    __tablename__ = "marketing_template_placeholders"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_templates.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_template_versions.id", ondelete="CASCADE"), nullable=True
    )
    placeholder_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    placeholder_type: Mapped[str] = mapped_column(String(30), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    default_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_template_placeholders_template_id", "template_id"),)


class AIContentGenerationRecord(Base):
    __tablename__ = "marketing_ai_content_generation_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="CASCADE"), nullable=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[AIGenerationStatus] = mapped_column(
        Enum(AIGenerationStatus, native_enum=False, length=30),
        nullable=False,
        default=AIGenerationStatus.PENDING_REVIEW,
    )
    output_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
