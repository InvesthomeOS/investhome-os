"""Marketing AI intelligence — insights, recommendations, predictions, anomalies, briefings."""

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
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from investhome_api.db.base import Base


class AIConfidenceLevel(str, enum.Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AIInsightCategory(str, enum.Enum):
    CAMPAIGN = "campaign"
    COUNTRY = "country"
    PROJECT = "project"
    CHANNEL = "channel"
    CREATIVE = "creative"
    LANDING_PAGE = "landing_page"
    FORM = "form"
    REVENUE = "revenue"
    AUDIENCE = "audience"
    BUDGET = "budget"
    AUTOMATION = "automation"
    GENERAL = "general"


class AIInsightSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AIRecommendationType(str, enum.Enum):
    INCREASE_BUDGET = "increase_budget"
    DECREASE_BUDGET = "decrease_budget"
    PAUSE_CAMPAIGN = "pause_campaign"
    SCALE_CAMPAIGN = "scale_campaign"
    DUPLICATE_CAMPAIGN = "duplicate_campaign"
    REFRESH_CREATIVE = "refresh_creative"
    IMPROVE_LANDING_PAGE = "improve_landing_page"
    IMPROVE_FORM = "improve_form"
    FIX_TRACKING = "fix_tracking"
    REALLOCATE_BUDGET = "reallocate_budget"
    CALL_LEAD = "call_lead"
    ASSIGN_SALES = "assign_sales"
    SEND_EMAIL = "send_email"
    SEND_WHATSAPP = "send_whatsapp"
    OTHER = "other"


class AIPredictionFramework(str, enum.Enum):
    LEAD_SCORING = "lead_scoring"
    PREDICTIVE_REVENUE = "predictive_revenue"
    CAMPAIGN_OPTIMIZATION = "campaign_optimization"
    CREATIVE_INTELLIGENCE = "creative_intelligence"
    AUDIENCE_INTELLIGENCE = "audience_intelligence"
    BUDGET_OPTIMIZATION = "budget_optimization"
    NEXT_BEST_ACTION = "next_best_action"


class AIAnomalyType(str, enum.Enum):
    TRAFFIC_DROP = "traffic_drop"
    LEAD_DROP = "lead_drop"
    CONVERSION_DROP = "conversion_drop"
    CTR_DROP = "ctr_drop"
    DUPLICATE_SPIKE = "duplicate_spike"
    SPAM_SPIKE = "spam_spike"
    TRACKING_FAILURE = "tracking_failure"
    REVENUE_DROP = "revenue_drop"


class AIBriefingPeriod(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    BOARD = "board"


class MarketingAIInsight(Base):
    __tablename__ = "marketing_ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    category: Mapped[AIInsightCategory] = mapped_column(
        Enum(
            AIInsightCategory,
            name="ai_insight_category",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
    )
    severity: Mapped[AIInsightSeverity] = mapped_column(
        Enum(
            AIInsightSeverity,
            name="ai_insight_severity",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=AIInsightSeverity.INFO,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(
            AIConfidenceLevel,
            name="ai_confidence_level",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        default=AIConfidenceLevel.UNKNOWN,
        nullable=False,
    )
    evidence_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_marketing_ai_insights_category_active", "category", "is_active"),)


class MarketingAIRecommendation(Base):
    __tablename__ = "marketing_ai_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recommendation_type: Mapped[AIRecommendationType] = mapped_column(
        Enum(AIRecommendationType, name="ai_recommendation_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(AIConfidenceLevel, name="ai_confidence_level", create_constraint=False), default=AIConfidenceLevel.UNKNOWN, nullable=False
    )
    evidence_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    requires_evidence: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    status: Mapped[str] = mapped_column(String(40), server_default="pending", nullable=False)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class MarketingAIPrediction(Base):
    __tablename__ = "marketing_ai_predictions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    framework: Mapped[AIPredictionFramework] = mapped_column(
        Enum(AIPredictionFramework, name="ai_prediction_framework"), nullable=False
    )
    prediction_key: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(AIConfidenceLevel, name="ai_confidence_level", create_constraint=False), default=AIConfidenceLevel.UNKNOWN, nullable=False
    )
    confidence_pct: Mapped[int | None] = mapped_column(nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_marketing_ai_predictions_framework_key", "framework", "prediction_key"),)


class MarketingAIAnomaly(Base):
    __tablename__ = "marketing_ai_anomalies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    anomaly_type: Mapped[AIAnomalyType] = mapped_column(
        Enum(AIAnomalyType, name="ai_anomaly_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(AIConfidenceLevel, name="ai_confidence_level", create_constraint=False), default=AIConfidenceLevel.UNKNOWN, nullable=False
    )
    evidence_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    severity: Mapped[AIInsightSeverity] = mapped_column(
        Enum(AIInsightSeverity, name="ai_insight_severity", create_constraint=False), default=AIInsightSeverity.WARNING, nullable=False
    )
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    is_resolved: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingAIBriefing(Base):
    __tablename__ = "marketing_ai_briefings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    period: Mapped[AIBriefingPeriod] = mapped_column(
        Enum(AIBriefingPeriod, name="ai_briefing_period"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(AIConfidenceLevel, name="ai_confidence_level", create_constraint=False), default=AIConfidenceLevel.UNKNOWN, nullable=False
    )
    sections_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    generated_for_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MarketingAICopilotQuery(Base):
    __tablename__ = "marketing_ai_copilot_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(80), nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[AIConfidenceLevel] = mapped_column(
        Enum(AIConfidenceLevel, name="ai_confidence_level", create_constraint=False), default=AIConfidenceLevel.UNKNOWN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_marketing_ai_copilot_queries_user_created", "user_id", "created_at"),)


class MarketingAIOutputType(str, enum.Enum):
    MARKETING_SUMMARY = "marketing_summary"
    CAMPAIGN_ANALYSIS = "campaign_analysis"
    CONTENT_DRAFT = "content_draft"
    CAMPAIGN_BRIEF = "campaign_brief"
    AUDIENCE_SUGGESTION = "audience_suggestion"
    CHANNEL_SUGGESTION = "channel_suggestion"
    TRANSLATION = "translation"
    NEXT_ACTIONS = "next_actions"


class MarketingAIOutputStatus(str, enum.Enum):
    DRAFT = "draft"
    SAVED = "saved"
    ARCHIVED = "archived"


class MarketingAIOutput(Base):
    """Draft-only AI Marketing Assistant outputs (Sprint 8A4)."""

    __tablename__ = "marketing_ai_outputs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    output_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="draft", nullable=False)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_campaigns.id", ondelete="SET NULL"), nullable=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("marketing_assets.id", ondelete="SET NULL"), nullable=True
    )
    language: Mapped[str | None] = mapped_column(String(10), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_content: Mapped[str] = mapped_column(Text, nullable=False)
    structured_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_sources: Mapped[list | None] = mapped_column(JSON, nullable=True)
    data_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)
    assumptions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    safety_flags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_key: Mapped[str | None] = mapped_column(String(80), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    token_usage: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    client_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index("ix_mkt_ai_outputs_org_created", "organization_id", "created_at"),
        Index("ix_mkt_ai_outputs_user_created", "created_by_user_id", "created_at"),
        Index("ix_mkt_ai_outputs_type_status", "output_type", "status"),
        Index("ix_mkt_ai_outputs_client_req", "created_by_user_id", "client_request_id"),
    )
