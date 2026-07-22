"""Pydantic schemas for CRM Relationship Engine."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class CrmRelationshipEntityTypeEnum(str, Enum):
    CONTACT = "contact"
    COMPANY = "company"
    PROJECT = "project"
    PROPERTY = "property"
    OPPORTUNITY = "opportunity"
    INVESTMENT = "investment"
    TRANSACTION = "transaction"
    VENDOR = "vendor"
    INTERNAL_USER = "internal_user"
    EXTERNAL_ORGANIZATION = "external_organization"
    OTHER = "other"


class CrmRelationshipCategoryEnum(str, Enum):
    ORGANIZATIONAL = "organizational"
    COMMERCIAL = "commercial"
    PERSONAL = "personal"
    REFERRAL = "referral"
    INVESTMENT = "investment"
    OPERATIONAL = "operational"
    OTHER = "other"


class CrmRelationshipStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"
    ARCHIVED = "archived"


class CrmRelationshipStrengthEnum(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    STRATEGIC = "strategic"


class CrmRelationshipDirectionEnum(str, Enum):
    OUTBOUND = "outbound"
    INBOUND = "inbound"
    BIDIRECTIONAL = "bidirectional"


class CrmRelationshipAlertTypeEnum(str, Enum):
    STALE = "stale"
    AT_RISK = "at_risk"
    SCORE_DROP = "score_drop"
    MISSING_FOLLOW_UP = "missing_follow_up"
    CONFLICT = "conflict"
    HIERARCHY_CYCLE = "hierarchy_cycle"
    DUPLICATE = "duplicate"
    OTHER = "other"


class CrmRelationshipAlertStatusEnum(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class CrmDecisionMapRoleTypeEnum(str, Enum):
    DECISION_MAKER = "decision_maker"
    INFLUENCER = "influencer"
    CHAMPION = "champion"
    GATEKEEPER = "gatekeeper"
    END_USER = "end_user"
    BLOCKER = "blocker"
    OTHER = "other"


class CrmReferralStatusEnum(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    CONVERTED = "converted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CrmRelationshipReviewStatusEnum(str, Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class CrmEntityRef(BaseModel):
    entity_type: CrmRelationshipEntityTypeEnum
    entity_id: UUID
    display_name: str | None = None


class CrmRelationshipSummary(BaseModel):
    id: UUID
    source_entity_type: CrmRelationshipEntityTypeEnum
    source_entity_id: UUID
    target_entity_type: CrmRelationshipEntityTypeEnum
    target_entity_id: UUID
    source_display_name: str | None = None
    target_display_name: str | None = None
    relationship_type: str
    reciprocal_type: str | None = None
    reciprocal_label: str | None = None
    category: CrmRelationshipCategoryEnum
    status: CrmRelationshipStatusEnum
    strength: CrmRelationshipStrengthEnum
    direction: CrmRelationshipDirectionEnum
    relationship_score: int = 0
    engagement_score: int = 0
    influence_score: int = 0
    trust_score: int = 0
    business_value_score: int = 0
    risk_score: int = 0
    is_confidential: bool = False
    is_verified: bool = False
    owner_user_id: UUID | None = None
    last_interaction_at: datetime | None = None
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CrmRelationshipDetail(CrmRelationshipSummary):
    notes: str | None = None
    metadata_json: dict | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


class CrmRelationshipCreate(BaseModel):
    source_entity_type: CrmRelationshipEntityTypeEnum
    source_entity_id: UUID
    target_entity_type: CrmRelationshipEntityTypeEnum
    target_entity_id: UUID
    relationship_type: str
    category: CrmRelationshipCategoryEnum | None = None
    status: CrmRelationshipStatusEnum = CrmRelationshipStatusEnum.ACTIVE
    strength: CrmRelationshipStrengthEnum = CrmRelationshipStrengthEnum.MODERATE
    direction: CrmRelationshipDirectionEnum = CrmRelationshipDirectionEnum.OUTBOUND
    is_confidential: bool = False
    is_verified: bool = False
    notes: str | None = None
    metadata_json: dict | None = None
    started_at: datetime | None = None
    owner_user_id: UUID | None = None


class CrmRelationshipUpdate(BaseModel):
    relationship_type: str | None = None
    category: CrmRelationshipCategoryEnum | None = None
    status: CrmRelationshipStatusEnum | None = None
    strength: CrmRelationshipStrengthEnum | None = None
    direction: CrmRelationshipDirectionEnum | None = None
    is_confidential: bool | None = None
    is_verified: bool | None = None
    notes: str | None = None
    metadata_json: dict | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    owner_user_id: UUID | None = None


class CrmRelationshipListResponse(BaseModel):
    items: list[CrmRelationshipSummary]
    total: int
    page: int
    page_size: int


class CrmRelationshipDuplicateCandidate(BaseModel):
    existing_id: UUID
    relationship_type: str
    source_entity_type: CrmRelationshipEntityTypeEnum
    source_entity_id: UUID
    target_entity_type: CrmRelationshipEntityTypeEnum
    target_entity_id: UUID
    match_score: float


class CrmRelationshipBulkActionRequest(BaseModel):
    relationship_ids: list[UUID]
    action: str
    payload: dict | None = None


class CrmRelationshipBulkActionResponse(BaseModel):
    updated: int
    failed: int = 0


class CrmRelationshipScoreBreakdown(BaseModel):
    relationship_score: int
    engagement_score: int
    influence_score: int
    trust_score: int
    business_value_score: int
    risk_score: int
    factors: dict = Field(default_factory=dict)


class CrmRelationshipScoreCalculateRequest(BaseModel):
    relationship_ids: list[UUID] | None = None
    recalculate_all: bool = False


class CrmRelationshipScoreCalculateResponse(BaseModel):
    calculated: int
    results: list[CrmRelationshipScoreBreakdown] = Field(default_factory=list)


class CrmGraphNode(BaseModel):
    id: str
    entity_type: CrmRelationshipEntityTypeEnum
    entity_id: UUID
    label: str
    score: int = 0
    is_center: bool = False
    expanded: bool = False


class CrmGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_id: UUID
    relationship_type: str
    reciprocal_type: str | None = None
    strength: CrmRelationshipStrengthEnum
    relationship_score: int = 0
    is_confidential: bool = False


class CrmRelationshipGraphResponse(BaseModel):
    nodes: list[CrmGraphNode]
    edges: list[CrmGraphEdge]
    truncated: bool = False
    warning: str | None = None
    depth: int
    limit: int


class CrmGraphExpandRequest(BaseModel):
    node_id: str
    depth: int = 1


class CrmIntroductionPathStep(BaseModel):
    node: CrmGraphNode
    edge: CrmGraphEdge | None = None
    explanation: str | None = None


class CrmIntroductionPath(BaseModel):
    steps: list[CrmIntroductionPathStep]
    total_score: int = 0
    total_hops: int = 0
    strategy: str


class CrmIntroductionPathsResponse(BaseModel):
    paths: list[CrmIntroductionPath]
    source_entity_type: CrmRelationshipEntityTypeEnum
    source_entity_id: UUID
    target_entity_type: CrmRelationshipEntityTypeEnum
    target_entity_id: UUID


class CrmRelationshipAlertResponse(BaseModel):
    id: UUID
    relationship_id: UUID | None = None
    entity_type: CrmRelationshipEntityTypeEnum | None = None
    entity_id: UUID | None = None
    alert_type: CrmRelationshipAlertTypeEnum
    severity: str
    message: str
    status: CrmRelationshipAlertStatusEnum
    created_at: datetime
    resolved_at: datetime | None = None


class CrmRelationshipAlertStatusUpdate(BaseModel):
    status: CrmRelationshipAlertStatusEnum


class CrmRelationshipRecommendation(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    entity_type: CrmRelationshipEntityTypeEnum | None = None
    entity_id: UUID | None = None
    relationship_id: UUID | None = None
    reason: str


class CrmDecisionMapRoleResponse(BaseModel):
    id: UUID
    company_id: UUID
    contact_id: UUID
    contact_display_name: str | None = None
    role_type: CrmDecisionMapRoleTypeEnum
    influence_level: int
    notes: str | None = None


class CrmDecisionMapRoleCreate(BaseModel):
    contact_id: UUID
    role_type: CrmDecisionMapRoleTypeEnum
    influence_level: int = 50
    notes: str | None = None


class CrmDecisionMapResponse(BaseModel):
    company_id: UUID
    roles: list[CrmDecisionMapRoleResponse]


class CrmReferralResponse(BaseModel):
    id: UUID
    referrer_entity_type: CrmRelationshipEntityTypeEnum
    referrer_entity_id: UUID
    referred_entity_type: CrmRelationshipEntityTypeEnum
    referred_entity_id: UUID
    referrer_display_name: str | None = None
    referred_display_name: str | None = None
    relationship_id: UUID | None = None
    status: CrmReferralStatusEnum
    compensation_amount: float | None = None
    compensation_currency: str | None = None
    compensation_status: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmReferralCreate(BaseModel):
    referrer_entity_type: CrmRelationshipEntityTypeEnum
    referrer_entity_id: UUID
    referred_entity_type: CrmRelationshipEntityTypeEnum
    referred_entity_id: UUID
    relationship_id: UUID | None = None
    status: CrmReferralStatusEnum = CrmReferralStatusEnum.PENDING
    compensation_amount: float | None = None
    compensation_currency: str | None = None
    compensation_status: str | None = None
    notes: str | None = None


class CrmRelationshipReviewResponse(BaseModel):
    id: UUID
    relationship_id: UUID
    reviewer_user_id: UUID | None = None
    review_date: datetime
    status: CrmRelationshipReviewStatusEnum
    notes: str | None = None
    scores_snapshot: dict | None = None
    created_at: datetime


class CrmRelationshipReviewCreate(BaseModel):
    relationship_id: UUID
    review_date: datetime
    status: CrmRelationshipReviewStatusEnum = CrmRelationshipReviewStatusEnum.SCHEDULED
    notes: str | None = None


class CrmRelationshipSavedViewResponse(BaseModel):
    id: UUID
    name: str
    filters: dict | None = None
    is_default: bool = False


class CrmRelationshipSavedViewCreate(BaseModel):
    name: str
    filters: dict | None = None
    is_default: bool = False


class CrmRelationshipIntelligenceDashboard(BaseModel):
    total_relationships: int = 0
    active_relationships: int = 0
    average_score: float = 0.0
    at_risk_count: int = 0
    stale_count: int = 0
    top_influencers: list[CrmEntityRef] = Field(default_factory=list)
    score_distribution: dict[str, int] = Field(default_factory=dict)
    category_breakdown: dict[str, int] = Field(default_factory=dict)
    open_alerts: int = 0
