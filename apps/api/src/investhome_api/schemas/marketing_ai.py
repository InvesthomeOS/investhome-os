"""Marketing AI intelligence API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AIConfidenceMixin(BaseModel):
    confidence: str = "unknown"
    confidence_pct: int | None = None


class EvidenceRef(BaseModel):
    source: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    metric_key: str | None = None
    value: str | None = None


class AIInsightItem(AIConfidenceMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    severity: str
    title: str
    summary: str
    evidence_refs: list[EvidenceRef] | list[dict] | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    created_at: datetime | None = None


class AIInsightListResponse(BaseModel):
    items: list[AIInsightItem]
    total: int


class AIRecommendationItem(AIConfidenceMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recommendation_type: str
    title: str
    rationale: str
    evidence_refs: list[EvidenceRef] | list[dict] | None = None
    requires_evidence: bool = True
    entity_type: str | None = None
    entity_id: UUID | None = None
    status: str = "pending"
    created_at: datetime | None = None


class AIRecommendationListResponse(BaseModel):
    items: list[AIRecommendationItem]
    total: int


class AIPredictionItem(AIConfidenceMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    framework: str
    prediction_key: str
    label: str
    value: str | None = None
    model_version: str | None = None
    metadata_json: dict | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None


class AIPredictionFrameworkResponse(BaseModel):
    framework: str
    label: str
    description: str
    model_connected: bool = False
    items: list[AIPredictionItem]


class AIPredictionsResponse(BaseModel):
    frameworks: list[AIPredictionFrameworkResponse]


class AIAnomalyItem(AIConfidenceMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    anomaly_type: str
    title: str
    description: str
    severity: str
    evidence_refs: list[EvidenceRef] | list[dict] | None = None
    entity_type: str | None = None
    entity_id: UUID | None = None
    is_resolved: bool = False
    detected_at: datetime | None = None


class AIAnomalyListResponse(BaseModel):
    items: list[AIAnomalyItem]
    total: int


class AIBriefingItem(AIConfidenceMixin):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
    period: str
    title: str
    summary: str
    sections: list[dict] | None = None
    generated_at: datetime | None = None


class AIBriefingResponse(BaseModel):
    briefing: AIBriefingItem


class AIMarketingHealthCategory(BaseModel):
    key: str
    label: str
    status: str = "unknown"
    score: int | None = None
    message: str | None = None


class AIMarketingHealthResponse(BaseModel):
    overall_status: str = "unknown"
    overall_score: int | None = None
    confidence: str = "unknown"
    categories: list[AIMarketingHealthCategory]
    data_freshness_at: datetime | None = None


class AIDashboardSection(BaseModel):
    key: str
    title: str
    status: str = "unknown"
    confidence: str = "unknown"
    items: list[dict] = Field(default_factory=list)


class AIDashboardResponse(BaseModel):
    executive_summary: str
    marketing_health: AIMarketingHealthResponse
    critical_insights: list[AIInsightItem]
    campaign_recommendations: list[AIRecommendationItem]
    budget_recommendations: list[AIRecommendationItem]
    lead_quality: AIDashboardSection
    prediction_confidence: AIDashboardSection
    anomaly_alerts: list[AIAnomalyItem]
    next_best_actions: list[AIRecommendationItem]
    executive_briefing: AIBriefingItem
    data_freshness_at: datetime | None = None


class CopilotQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    preset: str = "last_30_days"
    timezone: str = "UTC"


class CopilotAnswerSection(BaseModel):
    heading: str
    content: str
    data_points: list[dict] = Field(default_factory=list)


class CopilotQueryResponse(AIConfidenceMixin):
    query: str
    intent: str | None = None
    answer: str
    sections: list[CopilotAnswerSection] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] | list[dict] = Field(default_factory=list)
    insufficient_data: bool = False
    model_connected: bool = False


class AISettingsResponse(BaseModel):
    copilot_enabled: bool = True
    predictions_enabled: bool = True
    anomaly_detection_enabled: bool = True
    briefing_auto_generate: bool = False
    model_pipeline_connected: bool = False
    default_confidence: str = "unknown"


class AISettingsUpdate(BaseModel):
    copilot_enabled: bool | None = None
    predictions_enabled: bool | None = None
    anomaly_detection_enabled: bool | None = None
    briefing_auto_generate: bool | None = None


class AcceptRecommendationRequest(BaseModel):
    notes: str | None = None
