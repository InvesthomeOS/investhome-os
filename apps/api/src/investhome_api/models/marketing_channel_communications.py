"""Marketing channel communications — social, email, WhatsApp, SMS."""

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


class ChannelCampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"
    ARCHIVED = "archived"


class ChannelReadinessState(str, enum.Enum):
    READY = "ready"
    WARNING = "warning"
    BLOCKED = "blocked"
    NOT_CALCULATED = "not_calculated"


class ChannelApprovalStatus(str, enum.Enum):
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class DeliveryEventType(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    UNSUBSCRIBED = "unsubscribed"
    OPTED_OUT = "opted_out"
    REPLIED = "replied"
    PUBLISHED = "published"
    NOT_CONNECTED = "not_connected"


class SocialPostStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SocialNetwork(str, enum.Enum):
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    X = "x"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"
    OTHER = "other"


class WhatsAppTemplateStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_SUBMISSION = "pending_submission"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"


class ChannelCampaignMixin:
    """Shared fields for email/WhatsApp/SMS channel campaigns."""

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ChannelCampaignStatus] = mapped_column(
        Enum(ChannelCampaignStatus, native_enum=False, length=30),
        default=ChannelCampaignStatus.DRAFT,
        nullable=False,
    )
    approval_status: Mapped[ChannelApprovalStatus] = mapped_column(
        Enum(ChannelApprovalStatus, native_enum=False, length=30),
        default=ChannelApprovalStatus.NOT_REQUIRED,
        nullable=False,
    )
    readiness_state: Mapped[ChannelReadinessState] = mapped_column(
        Enum(ChannelReadinessState, native_enum=False, length=30),
        default=ChannelReadinessState.NOT_CALCULATED,
        nullable=False,
    )
    marketing_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    audience_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_audiences.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="SET NULL"), nullable=True
    )
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    personalisation_config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    frequency_policy_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_frequency_policies.id", ondelete="SET NULL"), nullable=True
    )
    recipient_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    eligible_recipient_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    readiness_checks_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    material_change_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MarketingFrequencyPolicy(Base):
    __tablename__ = "marketing_frequency_policies"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    max_messages_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_messages_per_week: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_frequency_policies_channel", "channel"),)


class ChannelDeliveryEvent(Base):
    __tablename__ = "marketing_channel_delivery_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(30), nullable=False)
    campaign_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    event_type: Mapped[DeliveryEventType] = mapped_column(
        Enum(DeliveryEventType, native_enum=False, length=30), nullable=False
    )
    provider_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_marketing_channel_delivery_events_campaign", "campaign_type", "campaign_id"),
        Index("ix_marketing_channel_delivery_events_channel", "channel"),
    )


class ChannelSendOperation(Base):
    """Idempotency record for send/publish operations."""

    __tablename__ = "marketing_channel_send_operations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    operation: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (Index("ix_marketing_channel_send_operations_resource", "resource_type", "resource_id"),)


class SocialAccount(Base):
    __tablename__ = "marketing_social_accounts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    network: Mapped[SocialNetwork] = mapped_column(
        Enum(SocialNetwork, native_enum=False, length=30), nullable=False
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    handle: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_channels.id", ondelete="SET NULL"), nullable=True
    )
    connection_status: Mapped[str] = mapped_column(String(40), default="not_connected", nullable=False)
    external_account_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    capabilities_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SocialPost(Base):
    __tablename__ = "marketing_social_posts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[SocialPostStatus] = mapped_column(
        Enum(SocialPostStatus, native_enum=False, length=30),
        default=SocialPostStatus.DRAFT,
        nullable=False,
    )
    approval_status: Mapped[ChannelApprovalStatus] = mapped_column(
        Enum(ChannelApprovalStatus, native_enum=False, length=30),
        default=ChannelApprovalStatus.NOT_REQUIRED,
        nullable=False,
    )
    readiness_state: Mapped[ChannelReadinessState] = mapped_column(
        Enum(ChannelReadinessState, native_enum=False, length=30),
        default=ChannelReadinessState.NOT_CALCULATED,
        nullable=False,
    )
    marketing_campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="SET NULL"), nullable=True
    )
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    readiness_checks_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    last_idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    material_change_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (Index("ix_marketing_social_posts_status", "status"),)


class SocialPostVariant(Base):
    __tablename__ = "marketing_social_post_variants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    post_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_social_posts.id", ondelete="CASCADE"), nullable=False
    )
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_social_accounts.id", ondelete="CASCADE"), nullable=False
    )
    network: Mapped[SocialNetwork] = mapped_column(
        Enum(SocialNetwork, native_enum=False, length=30), nullable=False
    )
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_refs_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    validation_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    external_post_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publish_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SocialInboxItem(Base):
    __tablename__ = "marketing_social_inbox_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    social_account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_social_accounts.id", ondelete="CASCADE"), nullable=False
    )
    network: Mapped[SocialNetwork] = mapped_column(
        Enum(SocialNetwork, native_enum=False, length=30), nullable=False
    )
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    handoff_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EmailCampaign(Base, ChannelCampaignMixin):
    __tablename__ = "marketing_email_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_email_templates.id", ondelete="SET NULL"), nullable=True
    )
    sender_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_email_sender_profiles.id", ondelete="SET NULL"), nullable=True
    )
    sequence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_email_sequences.id", ondelete="SET NULL"), nullable=True
    )
    unsubscribe_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    unsubscribe_link_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wizard_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wizard_state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_email_campaigns_status", "status"),)


class EmailTemplate(Base):
    __tablename__ = "marketing_email_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(500), nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="SET NULL"), nullable=True
    )
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_content_versions.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailSenderProfile(Base):
    __tablename__ = "marketing_email_sender_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_email_sending_domains.id", ondelete="SET NULL"), nullable=True
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EmailSendingDomain(Base):
    __tablename__ = "marketing_email_sending_domains"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    verification_status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)
    dkim_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    spf_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dmarc_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    dns_records_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class EmailSequence(Base):
    __tablename__ = "marketing_email_sequences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    audience_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_audiences.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EmailSequenceStep(Base):
    __tablename__ = "marketing_email_sequence_steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sequence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("marketing_email_sequences.id", ondelete="CASCADE"), nullable=False
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_email_templates.id", ondelete="SET NULL"), nullable=True
    )
    delay_hours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WhatsAppCampaign(Base, ChannelCampaignMixin):
    __tablename__ = "marketing_whatsapp_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_whatsapp_templates.id", ondelete="SET NULL"), nullable=True
    )
    sender_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_whatsapp_sender_profiles.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_whatsapp_campaigns_status", "status"),)


class WhatsAppTemplate(Base):
    __tablename__ = "marketing_whatsapp_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    header_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    footer_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    placeholders_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[WhatsAppTemplateStatus] = mapped_column(
        Enum(WhatsAppTemplateStatus, native_enum=False, length=30),
        default=WhatsAppTemplateStatus.DRAFT,
        nullable=False,
    )
    external_template_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WhatsAppSenderProfile(Base):
    __tablename__ = "marketing_whatsapp_sender_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connection_status: Mapped[str] = mapped_column(String(40), default="not_connected", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class WhatsAppConversation(Base):
    __tablename__ = "marketing_whatsapp_conversations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    sender_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_whatsapp_sender_profiles.id", ondelete="SET NULL"), nullable=True
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)
    handoff_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    messages_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SmsCampaign(Base, ChannelCampaignMixin):
    __tablename__ = "marketing_sms_campaigns"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    message_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_sms_templates.id", ondelete="SET NULL"), nullable=True
    )
    sender_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_sms_sender_profiles.id", ondelete="SET NULL"), nullable=True
    )
    opt_out_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opt_out_text_present: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    segment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_marketing_sms_campaigns_status", "status"),)


class SmsTemplate(Base):
    __tablename__ = "marketing_sms_templates"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segment_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_contents.id", ondelete="SET NULL"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SmsSenderProfile(Base):
    __tablename__ = "marketing_sms_sender_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_id: Mapped[str] = mapped_column(String(30), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(40), default="not_connected", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
