"""Marketing workspace domain models."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class MarketingCampaignType(str, enum.Enum):
    BRAND_AWARENESS = "brand_awareness"
    LEAD_GENERATION = "lead_generation"
    INVESTOR_ACQUISITION = "investor_acquisition"
    BUYER_ACQUISITION = "buyer_acquisition"
    BROKER_ACQUISITION = "broker_acquisition"
    PROPERTY_LAUNCH = "property_launch"
    PROJECT_LAUNCH = "project_launch"
    RETARGETING = "retargeting"
    NURTURE = "nurture"
    EVENT_PROMOTION = "event_promotion"
    OTHER = "other"


class MarketingCampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class MarketingCampaignObjective(str, enum.Enum):
    AWARENESS = "awareness"
    REACH = "reach"
    ENGAGEMENT = "engagement"
    TRAFFIC = "traffic"
    LEAD_GENERATION = "lead_generation"
    CONVERSION = "conversion"
    RETENTION = "retention"
    REVENUE = "revenue"


class MarketingCampaignPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class MarketingCampaignPrimaryChannel(str, enum.Enum):
    """Channel/medium for Sprint 8A1 lightweight campaign UX.

    Kept separate from MarketingCampaignType (purpose/objective taxonomy).
    """

    META = "meta"
    GOOGLE = "google"
    SEO = "seo"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    CONTENT = "content"
    YOUTUBE = "youtube"
    LINKEDIN = "linkedin"
    REFERRAL = "referral"
    EVENT = "event"
    OTHER = "other"


class MarketingChannelCategory(str, enum.Enum):
    PAID_SEARCH = "paid_search"
    PAID_SOCIAL = "paid_social"
    DISPLAY = "display"
    EMAIL = "email"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    SOCIAL_ORGANIC = "social_organic"
    SEO = "seo"
    EVENT = "event"
    DIRECT = "direct"
    REFERRAL = "referral"
    OTHER = "other"


class MarketingChannelStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ERROR = "error"


class MarketingConnectionStatus(str, enum.Enum):
    CONNECTED = "connected"
    PARTIALLY_CONNECTED = "partially_connected"
    NOT_CONNECTED = "not_connected"
    AUTHENTICATION_REQUIRED = "authentication_required"
    SYNCING = "syncing"
    DELAYED = "delayed"
    ERROR = "error"
    PERMISSION_RESTRICTED = "permission_restricted"
    NO_DATA = "no_data"


class MarketingAudienceMode(str, enum.Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    HYBRID = "hybrid"
    PROVIDER_SYNCED = "provider_synced"


class MarketingAudienceStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class MarketingAudienceType(str, enum.Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    LOOKALIKE = "lookalike"
    IMPORTED = "imported"
    CRM_SEGMENT = "crm_segment"


class MarketingSegmentType(str, enum.Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    BEHAVIORAL = "behavioral"


class SegmentCalculationStatus(str, enum.Enum):
    NOT_CALCULATED = "not_calculated"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MembershipInclusionSource(str, enum.Enum):
    EXPLICIT = "explicit"
    DYNAMIC = "dynamic"
    IMPORT = "import"
    SEGMENT = "segment"


class MembershipExclusionReason(str, enum.Enum):
    LEGAL = "legal"
    SUPPRESSION = "suppression"
    EXPLICIT = "explicit"
    CONSENT = "consent"
    CHANNEL = "channel"
    DYNAMIC = "dynamic"


class MarketingLeadHandoffStatus(str, enum.Enum):
    NOT_READY = "not_ready"
    READY = "ready"
    BLOCKED = "blocked"
    HANDED_OFF = "handed_off"


class MarketingLeadSourceType(str, enum.Enum):
    ORGANIC = "organic"
    PAID = "paid"
    REFERRAL = "referral"
    EVENT = "event"
    PARTNER = "partner"
    DIRECT = "direct"
    SOCIAL = "social"
    EMAIL = "email"
    OTHER = "other"


class MarketingContentType(str, enum.Enum):
    ARTICLE = "article"
    BLOG_POST = "blog_post"
    SOCIAL_POST = "social_post"
    EMAIL_TEMPLATE = "email_template"
    LANDING_PAGE = "landing_page"
    VIDEO = "video"
    IMAGE = "image"
    DOCUMENT = "document"
    AD_CREATIVE = "ad_creative"
    OTHER = "other"


class MarketingEventType(str, enum.Enum):
    WEBINAR = "webinar"
    OPEN_HOUSE = "open_house"
    CONFERENCE = "conference"
    NETWORKING = "networking"
    LAUNCH = "launch"
    WORKSHOP = "workshop"
    OTHER = "other"


class MarketingApprovalType(str, enum.Enum):
    CAMPAIGN = "campaign"
    CONTENT = "content"
    BUDGET = "budget"
    CREATIVE = "creative"
    EVENT = "event"


class MarketingApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class MarketingAlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MarketingAlertCategory(str, enum.Enum):
    CAMPAIGN = "campaign"
    BUDGET = "budget"
    PROVIDER = "provider"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    SYSTEM = "system"


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    objective: Mapped[MarketingCampaignObjective] = mapped_column(
        Enum(MarketingCampaignObjective, native_enum=False, length=40),
        nullable=False,
        default=MarketingCampaignObjective.AWARENESS,
    )
    campaign_type: Mapped[MarketingCampaignType] = mapped_column(
        Enum(MarketingCampaignType, native_enum=False, length=40),
        nullable=False,
        default=MarketingCampaignType.OTHER,
    )
    status: Mapped[MarketingCampaignStatus] = mapped_column(
        Enum(MarketingCampaignStatus, native_enum=False, length=30),
        nullable=False,
        default=MarketingCampaignStatus.DRAFT,
    )
    priority: Mapped[MarketingCampaignPriority] = mapped_column(
        Enum(MarketingCampaignPriority, native_enum=False, length=20),
        nullable=False,
        default=MarketingCampaignPriority.NORMAL,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    target_project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    lead_source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"), nullable=True
    )
    primary_channel: Mapped[MarketingCampaignPrimaryChannel | None] = mapped_column(
        Enum(MarketingCampaignPrimaryChannel, native_enum=False, length=30),
        nullable=True,
    )
    project_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    property_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    audience_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    segment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    channel_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    targets_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
        Index("ix_marketing_campaigns_status", "status"),
        Index("ix_marketing_campaigns_campaign_type", "campaign_type"),
        Index("ix_marketing_campaigns_owner_user_id", "owner_user_id"),
        Index("ix_marketing_campaigns_code", "code"),
        Index("ix_marketing_campaigns_updated_at", "updated_at"),
        Index("ix_marketing_campaigns_archived_at", "archived_at"),
        Index("ix_marketing_campaigns_primary_channel", "primary_channel"),
        Index("ix_marketing_campaigns_lead_source_id", "lead_source_id"),
        Index("ix_marketing_campaigns_target_project_id", "target_project_id"),
        Index("ix_marketing_campaigns_company_id", "company_id"),
    )


class MarketingChannel(Base):
    __tablename__ = "marketing_channels"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[MarketingChannelCategory] = mapped_column(
        Enum(MarketingChannelCategory, native_enum=False, length=30),
        nullable=False,
    )
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[MarketingChannelStatus] = mapped_column(
        Enum(MarketingChannelStatus, native_enum=False, length=20),
        nullable=False,
        default=MarketingChannelStatus.INACTIVE,
    )
    account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connection_status: Mapped[MarketingConnectionStatus] = mapped_column(
        Enum(MarketingConnectionStatus, native_enum=False, length=30),
        nullable=False,
        default=MarketingConnectionStatus.NOT_CONNECTED,
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_channels_category", "category"),
        Index("ix_marketing_channels_status", "status"),
        Index("ix_marketing_channels_connection_status", "connection_status"),
    )


class MarketingAudience(Base):
    __tablename__ = "marketing_audiences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience_type: Mapped[MarketingAudienceType] = mapped_column(
        Enum(MarketingAudienceType, native_enum=False, length=30),
        nullable=False,
    )
    mode: Mapped[MarketingAudienceMode] = mapped_column(
        Enum(MarketingAudienceMode, native_enum=False, length=30),
        nullable=False,
        default=MarketingAudienceMode.STATIC,
    )
    status: Mapped[MarketingAudienceStatus] = mapped_column(
        Enum(MarketingAudienceStatus, native_enum=False, length=20),
        nullable=False,
        default=MarketingAudienceStatus.DRAFT,
    )
    source: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estimated_size: Mapped[int | None] = mapped_column(nullable=True)
    calculated_size: Mapped[int | None] = mapped_column(nullable=True)
    contact_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    company_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    segment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    inclusion_refs_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exclusion_refs_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    segment_rules_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consent_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consent_requirements_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    channel_eligibility_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    geo_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refresh_policy_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    channel_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
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
        Index("ix_marketing_audiences_audience_type", "audience_type"),
        Index("ix_marketing_audiences_mode", "mode"),
        Index("ix_marketing_audiences_status", "status"),
        Index("ix_marketing_audiences_archived_at", "archived_at"),
    )


class MarketingSegment(Base):
    __tablename__ = "marketing_segments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    segment_type: Mapped[MarketingSegmentType] = mapped_column(
        Enum(MarketingSegmentType, native_enum=False, length=30),
        nullable=False,
    )
    rules_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    refresh_frequency: Mapped[str | None] = mapped_column(String(40), nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), server_default="team", nullable=False)
    estimated_size: Mapped[int | None] = mapped_column(nullable=True)
    calculated_size: Mapped[int | None] = mapped_column(nullable=True)
    calculation_status: Mapped[SegmentCalculationStatus] = mapped_column(
        Enum(SegmentCalculationStatus, native_enum=False, length=20),
        nullable=False,
        default=SegmentCalculationStatus.NOT_CALCULATED,
    )
    current_version: Mapped[int] = mapped_column(nullable=False, server_default="1")
    depends_on_segment_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        Index("ix_marketing_segments_segment_type", "segment_type"),
        Index("ix_marketing_segments_calculation_status", "calculation_status"),
        Index("ix_marketing_segments_archived_at", "archived_at"),
    )


class MarketingLeadContext(Base):
    """Marketing attribution context — references canonical Sales lead + CRM contact."""

    __tablename__ = "marketing_lead_contexts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("crm_contacts.id", ondelete="SET NULL"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    landing_page_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    attribution_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    utm_data_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scores_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consent_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    marketing_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verification_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    handoff_status: Mapped[MarketingLeadHandoffStatus] = mapped_column(
        Enum(MarketingLeadHandoffStatus, native_enum=False, length=20),
        nullable=False,
        default=MarketingLeadHandoffStatus.NOT_READY,
    )
    suppression_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_lead_contexts_lead_id", "lead_id"),
        Index("ix_marketing_lead_contexts_contact_id", "contact_id"),
        Index("ix_marketing_lead_contexts_campaign_id", "campaign_id"),
        Index("ix_marketing_lead_contexts_source_id", "source_id"),
        Index("ix_marketing_lead_contexts_handoff_status", "handoff_status"),
    )


class MarketingLeadSource(Base):
    __tablename__ = "marketing_lead_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"), nullable=True
    )
    source_type: Mapped[MarketingLeadSourceType] = mapped_column(
        Enum(MarketingLeadSourceType, native_enum=False, length=30),
        nullable=False,
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    utm_defaults_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tracking_readiness: Mapped[str | None] = mapped_column(String(30), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
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
        Index("ix_marketing_lead_sources_source_type", "source_type"),
        Index("ix_marketing_lead_sources_tracking_code", "tracking_code"),
        Index("ix_marketing_lead_sources_parent_id", "parent_id"),
        Index("ix_marketing_lead_sources_archived_at", "archived_at"),
    )


class MarketingContentAsset(Base):
    __tablename__ = "marketing_content_assets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[MarketingContentType] = mapped_column(
        Enum(MarketingContentType, native_enum=False, length=30),
        nullable=False,
    )
    format: Mapped[str | None] = mapped_column(String(40), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    file_ref: Mapped[str | None] = mapped_column(String(512), nullable=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), server_default="draft", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_content_assets_content_type", "content_type"),
        Index("ix_marketing_content_assets_campaign_id", "campaign_id"),
        Index("ix_marketing_content_assets_status", "status"),
    )


class MarketingEvent(Base):
    __tablename__ = "marketing_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_type: Mapped[MarketingEventType] = mapped_column(
        Enum(MarketingEventType, native_enum=False, length=30),
        nullable=False,
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    property_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    registration_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    status: Mapped[str] = mapped_column(String(30), server_default="draft", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_events_event_type", "event_type"),
        Index("ix_marketing_events_campaign_id", "campaign_id"),
        Index("ix_marketing_events_start_at", "start_at"),
        Index("ix_marketing_events_status", "status"),
    )


class MarketingBudget(Base):
    __tablename__ = "marketing_budgets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    planned_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spent_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), server_default="draft", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_budgets_campaign_id", "campaign_id"),
        Index("ix_marketing_budgets_status", "status"),
    )


class MarketingApproval(Base):
    __tablename__ = "marketing_approvals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    approval_type: Mapped[MarketingApprovalType] = mapped_column(
        Enum(MarketingApprovalType, native_enum=False, length=30),
        nullable=False,
    )
    status: Mapped[MarketingApprovalStatus] = mapped_column(
        Enum(MarketingApprovalStatus, native_enum=False, length=20),
        nullable=False,
        default=MarketingApprovalStatus.DRAFT,
    )
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_approvals_entity", "entity_type", "entity_id"),
        Index("ix_marketing_approvals_status", "status"),
    )


class MarketingAlert(Base):
    __tablename__ = "marketing_alerts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[MarketingAlertCategory] = mapped_column(
        Enum(MarketingAlertCategory, native_enum=False, length=30),
        nullable=False,
    )
    severity: Mapped[MarketingAlertSeverity] = mapped_column(
        Enum(MarketingAlertSeverity, native_enum=False, length=20),
        nullable=False,
        default=MarketingAlertSeverity.INFO,
    )
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_alerts_category", "category"),
        Index("ix_marketing_alerts_severity", "severity"),
        Index("ix_marketing_alerts_is_resolved", "is_resolved"),
    )


class CampaignMilestoneType(str, enum.Enum):
    PLANNING = "planning"
    CONTENT = "content"
    APPROVAL = "approval"
    LAUNCH = "launch"
    OPTIMIZATION = "optimization"
    REVIEW = "review"
    COMPLETION = "completion"
    OTHER = "other"


class CampaignMilestoneStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CampaignTrackingReadiness(str, enum.Enum):
    NOT_CONFIGURED = "not_configured"
    INCOMPLETE = "incomplete"
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


class CampaignReadinessState(str, enum.Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"


class CampaignBrief(Base):
    __tablename__ = "marketing_campaign_briefs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    objectives: Mapped[str | None] = mapped_column(Text, nullable=True)
    messaging: Mapped[str | None] = mapped_column(Text, nullable=True)
    strategies: Mapped[str | None] = mapped_column(Text, nullable=True)
    risks: Mapped[str | None] = mapped_column(Text, nullable=True)
    competitive_context: Mapped[str | None] = mapped_column(Text, nullable=True)
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


class CampaignMilestone(Base):
    __tablename__ = "marketing_campaign_milestones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    milestone_type: Mapped[CampaignMilestoneType] = mapped_column(
        Enum(CampaignMilestoneType, native_enum=False, length=30),
        nullable=False,
        default=CampaignMilestoneType.OTHER,
    )
    status: Mapped[CampaignMilestoneStatus] = mapped_column(
        Enum(CampaignMilestoneStatus, native_enum=False, length=20),
        nullable=False,
        default=CampaignMilestoneStatus.NOT_STARTED,
    )
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    depends_on_ids: Mapped[list | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_campaign_milestones_campaign_id", "campaign_id"),
        Index("ix_marketing_campaign_milestones_status", "status"),
    )


class CampaignChannelAssignment(Base):
    __tablename__ = "marketing_campaign_channel_assignments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    channel_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    budget_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    budget_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    schedule_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tracking_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(30), server_default="draft", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_campaign_channel_assignments_campaign_id", "campaign_id"),
        Index("ix_marketing_campaign_channel_assignments_channel_id", "channel_id"),
    )


class CampaignBudgetAllocation(Base):
    __tablename__ = "marketing_campaign_budget_allocations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    budget_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_budgets.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), server_default="USD", nullable=False)
    planned_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    committed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    spent_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_campaign_budget_allocations_campaign_id", "campaign_id"),)


class CampaignTracking(Base):
    __tablename__ = "marketing_campaign_tracking"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(120), nullable=True)
    landing_page_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    readiness_status: Mapped[CampaignTrackingReadiness] = mapped_column(
        Enum(CampaignTrackingReadiness, native_enum=False, length=20),
        nullable=False,
        default=CampaignTrackingReadiness.NOT_CONFIGURED,
    )
    validation_errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CampaignTarget(Base):
    __tablename__ = "marketing_campaign_targets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="CASCADE"), nullable=False
    )
    metric_key: Mapped[str] = mapped_column(String(80), nullable=False)
    metric_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    period: Mapped[str | None] = mapped_column(String(40), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_campaign_targets_campaign_id", "campaign_id"),)


class CampaignTemplate(Base):
    __tablename__ = "marketing_campaign_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[MarketingCampaignType | None] = mapped_column(
        Enum(MarketingCampaignType, native_enum=False, length=40),
        nullable=True,
    )
    objective: Mapped[MarketingCampaignObjective | None] = mapped_column(
        Enum(MarketingCampaignObjective, native_enum=False, length=40),
        nullable=True,
    )
    template_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class CampaignSavedView(Base):
    __tablename__ = "marketing_campaign_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_campaign_saved_views_user_id", "user_id"),)


class MarketingRecommendation(Base):
    __tablename__ = "marketing_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommendation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="active", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_marketing_recommendations_status", "status"),
        Index("ix_marketing_recommendations_type", "recommendation_type"),
    )


class AudienceMembership(Base):
    """Canonical contact/company membership with explainability."""

    __tablename__ = "marketing_audience_memberships"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audience_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_audiences.id", ondelete="CASCADE"), nullable=False
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("crm_contacts.id", ondelete="CASCADE"), nullable=True
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True
    )
    is_included: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    inclusion_source: Mapped[MembershipInclusionSource | None] = mapped_column(
        Enum(MembershipInclusionSource, native_enum=False, length=20), nullable=True
    )
    exclusion_reason: Mapped[MembershipExclusionReason | None] = mapped_column(
        Enum(MembershipExclusionReason, native_enum=False, length=20), nullable=True
    )
    eligibility_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    explainability_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_marketing_audience_memberships_audience_id", "audience_id"),
        Index("ix_marketing_audience_memberships_contact_id", "contact_id"),
        Index("ix_marketing_audience_memberships_company_id", "company_id"),
    )


class AudienceConsentRequirement(Base):
    __tablename__ = "marketing_audience_consent_requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audience_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_audiences.id", ondelete="CASCADE"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SegmentRuleGroup(Base):
    __tablename__ = "marketing_segment_rule_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_segments.id", ondelete="CASCADE"), nullable=False
    )
    parent_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_segment_rule_groups.id", ondelete="CASCADE"), nullable=True
    )
    operator: Mapped[str] = mapped_column(String(10), server_default="and", nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_segment_rule_groups_segment_id", "segment_id"),)


class SegmentRule(Base):
    __tablename__ = "marketing_segment_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_segment_rule_groups.id", ondelete="CASCADE"), nullable=False
    )
    field_key: Mapped[str] = mapped_column(String(80), nullable=False)
    operator: Mapped[str] = mapped_column(String(40), nullable=False)
    value_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    negate: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    sort_order: Mapped[int] = mapped_column(nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_segment_rules_group_id", "group_id"),)


class SegmentCalculationRun(Base):
    __tablename__ = "marketing_segment_calculation_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_segments.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[SegmentCalculationStatus] = mapped_column(
        Enum(SegmentCalculationStatus, native_enum=False, length=20),
        nullable=False,
        default=SegmentCalculationStatus.PENDING,
    )
    version: Mapped[int] = mapped_column(nullable=False, server_default="1")
    member_count: Mapped[int | None] = mapped_column(nullable=True)
    warnings_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    triggered_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_segment_calculation_runs_segment_id", "segment_id"),)


class SegmentVersion(Base):
    __tablename__ = "marketing_segment_versions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_segments.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(nullable=False)
    rules_snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_segment_versions_segment_id", "segment_id"),)


class LeadSourceMapping(Base):
    __tablename__ = "marketing_lead_source_mappings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_lead_sources.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(80), nullable=True)
    external_key: Mapped[str] = mapped_column(String(255), nullable=False)
    mapping_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_lead_source_mappings_source_id", "source_id"),)


class LeadSourceNormalization(Base):
    __tablename__ = "marketing_lead_source_normalizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_lead_sources.id", ondelete="CASCADE"), nullable=False
    )
    raw_value: Mapped[str] = mapped_column(String(512), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_lead_source_normalizations_source_id", "source_id"),)


class AudienceSavedView(Base):
    __tablename__ = "marketing_audience_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SegmentSavedView(Base):
    __tablename__ = "marketing_segment_saved_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filters_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    is_shared: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
