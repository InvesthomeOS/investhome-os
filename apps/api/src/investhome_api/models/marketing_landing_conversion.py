"""Marketing landing pages, forms, submissions, and conversion infrastructure."""

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


class LandingPageStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class FormStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class SubmissionStatus(str, enum.Enum):
    RECEIVED = "received"
    VALIDATING = "validating"
    NORMALIZED = "normalized"
    CONSENT_CHECKED = "consent_checked"
    SPAM_CHECKED = "spam_checked"
    VERIFICATION_PENDING = "verification_pending"
    IDENTITY_RESOLVED = "identity_resolved"
    DUPLICATE_DETECTED = "duplicate_detected"
    PENDING_REVIEW = "pending_review"
    CONTACT_CREATED = "contact_created"
    LEAD_CONTEXT_CREATED = "lead_context_created"
    ROUTED = "routed"
    HANDED_OFF = "handed_off"
    REJECTED = "rejected"
    FAILED = "failed"


class LandingPageSectionType(str, enum.Enum):
    HERO = "hero"
    LEAD_FORM = "lead_form"
    PROJECT_SUMMARY = "project_summary"
    PROPERTY_SUMMARY = "property_summary"
    FEATURES = "features"
    TESTIMONIALS = "testimonials"
    CTA = "cta"
    GALLERY = "gallery"
    VIDEO = "video"
    FAQ = "faq"
    FOOTER = "footer"


class FormFieldType(str, enum.Enum):
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    TEXTAREA = "textarea"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    CONSENT = "consent"
    HIDDEN = "hidden"
    NUMBER = "number"
    DATE = "date"


class LogicOperator(str, enum.Enum):
    AND = "and"
    OR = "or"


class LogicCondition(str, enum.Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class DomainVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class ReviewItemStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MarketingLandingPage(Base):
    __tablename__ = "marketing_landing_pages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[LandingPageStatus] = mapped_column(
        Enum(LandingPageStatus, name="landing_page_status"), default=LandingPageStatus.DRAFT, nullable=False
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"))
    content_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="SET NULL"))
    project_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    property_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    meta_title: Mapped[str | None] = mapped_column(String(255))
    meta_description: Mapped[str | None] = mapped_column(Text)
    tracking_config_json: Mapped[dict | None] = mapped_column(JSON)
    consent_config_json: Mapped[dict | None] = mapped_column(JSON)
    approval_status: Mapped[str | None] = mapped_column(String(30))
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LandingPageSection(Base):
    __tablename__ = "marketing_landing_page_sections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    landing_page_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="CASCADE"))
    section_type: Mapped[LandingPageSectionType] = mapped_column(Enum(LandingPageSectionType, name="landing_page_section_type"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LandingPageVersion(Base):
    __tablename__ = "marketing_landing_page_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    landing_page_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LandingPageDomain(Base):
    __tablename__ = "marketing_landing_page_domains"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    landing_page_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="CASCADE"))
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    path_prefix: Mapped[str | None] = mapped_column(String(255))
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_status: Mapped[DomainVerificationStatus] = mapped_column(
        Enum(DomainVerificationStatus, name="domain_verification_status"), default=DomainVerificationStatus.PENDING
    )
    dns_records_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class LandingPageExperiment(Base):
    __tablename__ = "marketing_landing_page_experiments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    landing_page_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ExperimentStatus] = mapped_column(Enum(ExperimentStatus, name="experiment_status"), default=ExperimentStatus.DRAFT)
    traffic_split_json: Mapped[dict | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class LandingPageExperimentVariant(Base):
    __tablename__ = "marketing_landing_page_experiment_variants"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    experiment_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_landing_page_experiments.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_landing_page_versions.id", ondelete="SET NULL"))
    weight_percent: Mapped[int] = mapped_column(Integer, default=50)
    is_control: Mapped[bool] = mapped_column(Boolean, default=False)


class MarketingForm(Base):
    __tablename__ = "marketing_forms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    status: Mapped[FormStatus] = mapped_column(Enum(FormStatus, name="form_status"), default=FormStatus.DRAFT)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"))
    consent_config_json: Mapped[dict | None] = mapped_column(JSON)
    routing_config_json: Mapped[dict | None] = mapped_column(JSON)
    notification_config_json: Mapped[dict | None] = mapped_column(JSON)
    spam_config_json: Mapped[dict | None] = mapped_column(JSON)
    published_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketingFormField(Base):
    __tablename__ = "marketing_form_fields"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="CASCADE"))
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    field_type: Mapped[FormFieldType] = mapped_column(Enum(FormFieldType, name="form_field_type"))
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    config_json: Mapped[dict | None] = mapped_column(JSON)
    validation_json: Mapped[dict | None] = mapped_column(JSON)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_marketing_form_fields_form_key", "form_id", "field_key", unique=True),)


class FormLogicGroup(Base):
    __tablename__ = "marketing_form_logic_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="CASCADE"))
    target_field_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_form_fields.id", ondelete="CASCADE"))
    operator: Mapped[LogicOperator] = mapped_column(Enum(LogicOperator, name="logic_operator"), default=LogicOperator.AND)
    action: Mapped[str] = mapped_column(String(30), default="show")
    conditions_json: Mapped[list | None] = mapped_column(JSON)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FormVersion(Base):
    __tablename__ = "marketing_form_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingFormSubmission(Base):
    __tablename__ = "marketing_form_submissions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    form_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="CASCADE"))
    landing_page_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str | None] = mapped_column(String(255), index=True)
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus, name="submission_status"), default=SubmissionStatus.RECEIVED)
    raw_values_reference: Mapped[str | None] = mapped_column(String(500))
    normalized_values_json: Mapped[dict | None] = mapped_column(JSON)
    tracking_context_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_tracking_contexts.id", ondelete="SET NULL"))
    consent_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_consent_evidence.id", ondelete="SET NULL", use_alter=True)
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    lead_context_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_contexts.id", ondelete="SET NULL"))
    duplicate_of_submission_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    pipeline_errors_json: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (Index("ix_marketing_form_submissions_form_idempotency", "form_id", "idempotency_key", unique=True),)


class LandingPageSectionRegistry(Base):
    __tablename__ = "marketing_landing_page_section_registry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    section_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    config_schema_json: Mapped[dict | None] = mapped_column(JSON)
    allowed_public_fields_json: Mapped[list | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class FormFieldRegistry(Base):
    __tablename__ = "marketing_form_field_registry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    field_type: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    config_schema_json: Mapped[dict | None] = mapped_column(JSON)
    validation_schema_json: Mapped[dict | None] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class PublicDataFieldRegistry(Base):
    __tablename__ = "marketing_public_data_field_registry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    field_key: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(30), default="string")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (Index("ix_public_data_field_entity_key", "entity_type", "field_key", unique=True),)


class MarketingTrackingContext(Base):
    __tablename__ = "marketing_tracking_contexts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    utm_source: Mapped[str | None] = mapped_column(String(255))
    utm_medium: Mapped[str | None] = mapped_column(String(255))
    utm_campaign: Mapped[str | None] = mapped_column(String(255))
    utm_term: Mapped[str | None] = mapped_column(String(255))
    utm_content: Mapped[str | None] = mapped_column(String(255))
    referrer: Mapped[str | None] = mapped_column(String(500))
    landing_url: Mapped[str | None] = mapped_column(String(500))
    ip_hash: Mapped[str | None] = mapped_column(String(64))
    user_agent_hash: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[str | None] = mapped_column(String(255))
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"))
    raw_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingConversionEvent(Base):
    __tablename__ = "marketing_conversion_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_form_submissions.id", ondelete="SET NULL"))
    lead_context_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_contexts.id", ondelete="SET NULL"))
    landing_page_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_landing_pages.id", ondelete="SET NULL"))
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="SET NULL"))
    tracking_context_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_tracking_contexts.id", ondelete="SET NULL"))
    value_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingLeadRoutingRule(Base):
    __tablename__ = "marketing_lead_routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False)
    conditions_json: Mapped[dict | None] = mapped_column(JSON)
    action_json: Mapped[dict | None] = mapped_column(JSON)
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="SET NULL"))
    source_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_lead_sources.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MarketingSalesHandoff(Base):
    __tablename__ = "marketing_sales_handoffs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lead_context_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_lead_contexts.id", ondelete="CASCADE"))
    submission_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_form_submissions.id", ondelete="SET NULL"))
    sales_lead_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    sla_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_handoff_slas.id", ondelete="SET NULL"))
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blockers_json: Mapped[list | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class HandoffSLA(Base):
    __tablename__ = "marketing_handoff_slas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ConsentEvidence(Base):
    __tablename__ = "marketing_consent_evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_form_submissions.id", ondelete="SET NULL"))
    consent_snapshot_json: Mapped[dict | None] = mapped_column(JSON)
    marketing_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_source: Mapped[str | None] = mapped_column(String(50))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SubmissionReviewItem(Base):
    __tablename__ = "marketing_submission_review_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_form_submissions.id", ondelete="CASCADE"))
    review_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[ReviewItemStatus] = mapped_column(Enum(ReviewItemStatus, name="review_item_status"), default=ReviewItemStatus.PENDING)
    reason: Mapped[str | None] = mapped_column(Text)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingWebhook(Base):
    __tablename__ = "marketing_webhooks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    event_types_json: Mapped[list | None] = mapped_column(JSON)
    secret_ref: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    form_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("marketing_forms.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class WebhookDelivery(Base):
    __tablename__ = "marketing_webhook_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    webhook_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("marketing_webhooks.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[WebhookDeliveryStatus] = mapped_column(
        Enum(WebhookDeliveryStatus, name="webhook_delivery_status"), default=WebhookDeliveryStatus.PENDING
    )
    response_code: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
