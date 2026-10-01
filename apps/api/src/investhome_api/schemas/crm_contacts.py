"""CRM contact Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.crm_contact import (
    CrmContactPriority,
    CrmContactStatus,
    CrmContactType,
    CrmLifecycleStage,
    CrmRecordKind,
    CrmRelationshipStatus,
    CrmRelationshipStrength,
)
from investhome_api.schemas.crm_agreements import CrmUnitHistoryStep


class CrmLabeledValue(BaseModel):
    label: str
    value: str


class CrmInvestmentProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investor_type: str | None = None
    accreditation_status: str | None = None
    risk_profile: str | None = None
    investment_capacity_min: float | None = None
    investment_capacity_max: float | None = None
    preferred_asset_classes: list[str] | None = None
    preferred_regions: list[str] | None = None
    investment_timeline: str | None = None
    notes: str | None = None


class CrmBuyerProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    budget_min: float | None = None
    budget_max: float | None = None
    preferred_locations: list[str] | None = None
    property_types: list[str] | None = None
    bedroom_min: int | None = None
    financing_status: str | None = None
    purchase_timeline: str | None = None
    notes: str | None = None


class CrmBrokerProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    license_number: str | None = None
    brokerage_name: str | None = None
    specialization: str | None = None
    service_areas: list[str] | None = None
    commission_structure: str | None = None
    notes: str | None = None


class CrmVendorProfileSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    vendor_category: str | None = None
    service_scope: str | None = None
    contract_status: str | None = None
    payment_terms: str | None = None
    insurance_verified: bool = False
    notes: str | None = None


class CrmVerifiedAmountTotal(BaseModel):
    currency: str | None = None
    total: str
    label: str


class CrmContactTagItem(BaseModel):
    id: UUID
    name: str
    status: str = "active"


class CrmContactSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_type: CrmContactType
    contact_types: list[CrmContactType] = Field(default_factory=list)
    record_kind: CrmRecordKind
    display_name: str
    organization_name: str | None = None
    primary_email: str | None = None
    primary_phone: str | None = None
    source: str | None = None
    status: CrmContactStatus
    lifecycle_stage: CrmLifecycleStage = CrmLifecycleStage.NEW
    relationship_status: CrmRelationshipStatus = CrmRelationshipStatus.UNKNOWN
    relationship_strength: CrmRelationshipStrength = CrmRelationshipStrength.MODERATE
    priority: CrmContactPriority = CrmContactPriority.NORMAL
    tags: list[str] | None = None
    tag_items: list[CrmContactTagItem] = Field(default_factory=list)
    is_favorite: bool = False
    is_pinned: bool = False
    owner_user_id: UUID | None = None
    owner_name: str | None = None
    company_id: UUID | None = None
    company_name: str | None = None
    lead_id: UUID | None = None
    investor_id: UUID | None = None
    last_contact_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    relationship_score: int = 0
    engagement_score: int = 0
    junk_reason: str | None = None
    junked_at: datetime | None = None
    review_required: bool = False
    is_agent: bool = False
    has_agreements: bool = False
    agreement_count: int = 0
    verified_amount_totals: list[CrmVerifiedAmountTotal] = Field(default_factory=list)
    agreement_projects: list[str] = Field(default_factory=list)
    bitrix_original_stage: str | None = None
    bitrix_historical_junk: bool = False
    bitrix_source_channel: str | None = None
    bitrix_responsible: str | None = None
    secondary_emails: list[str] | None = None
    secondary_phones: list[str] | None = None
    whatsapp: str | None = None
    job_title: str | None = None
    city: str | None = None
    address_line1: str | None = None
    notes: str | None = None
    updated_at: datetime
    created_at: datetime


class CrmContactDetail(CrmContactSummary):
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    secondary_emails: list[str] | None = None
    secondary_phones: list[str] | None = None
    linkedin_url: str | None = None
    whatsapp: str | None = None
    website: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    referred_by_contact_id: UUID | None = None
    notes: str | None = None
    communication_prefs: dict[str, Any] | None = None
    compliance_data: dict[str, Any] | None = None
    investment_profile: CrmInvestmentProfileSchema | None = None
    buyer_profile: CrmBuyerProfileSchema | None = None
    broker_profile: CrmBrokerProfileSchema | None = None
    vendor_profile: CrmVendorProfileSchema | None = None
    bitrix_history: CrmBitrixHistory | None = None
    amount_and_currency_label: str | None = None
    amount_and_currency_field_id: str | None = None
    amount_and_currency_amount: str | None = None
    amount_and_currency_currency: str | None = None
    crm_activities: list[CrmContactActivityVerification] = Field(default_factory=list)
    crm_agreements: list[CrmContactAgreementVerification] = Field(default_factory=list)
    agent: CrmContactAgentVerification | None = None
    project_card_pilot: "CrmProjectCardPilot | None" = None
    purchases: list["CrmPurchaseSummary"] = Field(default_factory=list)
    profile_fields: list[CrmLabeledValue] = Field(default_factory=list)


class CrmBitrixHistory(BaseModel):
    external_ids: list[str] = Field(default_factory=list)
    source_files: list[str] = Field(default_factory=list)
    source_roles: list[str] = Field(default_factory=list)
    historical_junk: bool = False
    original_asama: str | None = None
    mapped_sales_stage: str | None = None
    conflict_fields: list[str] = Field(default_factory=list)
    warning_flags: list[str] = Field(default_factory=list)
    junk_reason: str | None = None
    review_required: bool = False


class CrmProjectCardPilotProject(BaseModel):
    id: str
    label: str


class CrmProjectCardPilot(BaseModel):
    enabled: bool = False
    canonical_contact_id: UUID | None = None
    selected_project: str = "all"
    available_projects: list[CrmProjectCardPilotProject] = Field(default_factory=list)
    history_counts: dict[str, int] = Field(default_factory=dict)
    unclassified_history_count: int = 0
    tutar_by_project: dict[str, str] = Field(default_factory=dict)


class CrmPurchaseParticipant(BaseModel):
    contact_id: UUID
    display_name: str
    role: str = "owner"
    ownership_pct: str | None = None
    is_primary: bool = False
    source: str | None = None


class CrmPurchaseSummary(BaseModel):
    agreement_id: UUID
    bitrix_deal_id: str | None = None
    project_group: str
    project_label: str
    unit_number: str | None = None
    amount: str | None = None
    currency: str | None = None
    amount_label: str | None = None
    stage: str | None = None
    begin_date: str | None = None
    close_date: str | None = None
    owners_label: str | None = None
    participants: list[CrmPurchaseParticipant] = Field(default_factory=list)
    opens_purchase_card: bool = False
    status: str | None = None
    hemen_kira: bool = False
    is_historical_unit_change: bool = False
    unit_change_status: str | None = None
    original_unit: str | None = None
    final_unit: str | None = None
    unit_history: list[CrmUnitHistoryStep] = Field(default_factory=list)


class CrmContactActivityVerification(BaseModel):
    id: UUID
    activity_type: str
    activity_category: str
    title: str
    description: str | None = None
    status: str
    imported_historical_comment: bool = False
    due_date: datetime | None = None
    assigned_user_id: UUID | None = None
    task_status: str | None = None
    created_at: datetime


class CrmContactAgreementVerification(BaseModel):
    id: UUID
    project_group: str
    project_label: str
    status: str
    agreement_date: date | None = None
    unit_number: str | None = None
    investment_amount: str | None = None
    payment_amount: str | None = None
    deposit: str | None = None
    purchase_price: str | None = None
    amount_and_currency_label: str | None = None
    amount_and_currency_field_id: str | None = None
    amount_and_currency_amount: str | None = None
    amount_and_currency_currency: str | None = None
    email: str | None = None
    phone: str | None = None
    review_required: bool = False
    relationship: str = "Anlaşma tarafı"


class CrmContactAgentVerification(BaseModel):
    is_agent: bool
    status: str
    contact_types: list[CrmContactType] = Field(default_factory=list)
    brokerage_name: str | None = None
    specialization: str | None = None


class CrmBitrixVerificationSummary(BaseModel):
    total_contacts: int
    bitrix_contacts: int
    non_bitrix_contacts: int
    active_bitrix: int
    archived_bitrix: int
    bitrix_with_phone: int
    bitrix_with_email: int
    bitrix_with_external_id: int
    imported_historical_comments: int
    imported_agents: int
    imported_agreements: int
    agreements_by_project: dict[str, int] = Field(default_factory=dict)


class CrmContactCreate(BaseModel):
    contact_type: CrmContactType
    contact_types: list[CrmContactType] | None = None
    record_kind: CrmRecordKind = CrmRecordKind.PERSON
    display_name: str = Field(min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    organization_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    primary_email: str | None = Field(default=None, max_length=255)
    secondary_emails: list[str] | None = None
    primary_phone: str | None = Field(default=None, max_length=50)
    secondary_phones: list[str] | None = None
    linkedin_url: str | None = Field(default=None, max_length=500)
    whatsapp: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_province: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=30)
    country: str | None = Field(default=None, max_length=100)
    lifecycle_stage: CrmLifecycleStage = CrmLifecycleStage.NEW
    relationship_status: CrmRelationshipStatus = CrmRelationshipStatus.UNKNOWN
    relationship_strength: CrmRelationshipStrength = CrmRelationshipStrength.MODERATE
    priority: CrmContactPriority = CrmContactPriority.NORMAL
    source: str | None = Field(default=None, max_length=120)
    referred_by_contact_id: UUID | None = None
    last_contact_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    tags: list[str] | None = None
    status: CrmContactStatus = CrmContactStatus.ACTIVE
    owner_user_id: UUID | None = None
    company_id: UUID | None = None
    lead_id: UUID | None = None
    investor_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_favorite: bool = False
    is_pinned: bool = False
    junk_reason: str | None = Field(default=None, max_length=255)
    communication_prefs: dict[str, Any] | None = None
    compliance_data: dict[str, Any] | None = None
    investment_profile: CrmInvestmentProfileSchema | None = None
    buyer_profile: CrmBuyerProfileSchema | None = None
    broker_profile: CrmBrokerProfileSchema | None = None
    vendor_profile: CrmVendorProfileSchema | None = None


class CrmContactUpdate(BaseModel):
    contact_type: CrmContactType | None = None
    contact_types: list[CrmContactType] | None = None
    record_kind: CrmRecordKind | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    organization_name: str | None = Field(default=None, max_length=255)
    job_title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    primary_email: str | None = Field(default=None, max_length=255)
    secondary_emails: list[str] | None = None
    primary_phone: str | None = Field(default=None, max_length=50)
    secondary_phones: list[str] | None = None
    linkedin_url: str | None = Field(default=None, max_length=500)
    whatsapp: str | None = Field(default=None, max_length=50)
    website: str | None = Field(default=None, max_length=500)
    address_line1: str | None = Field(default=None, max_length=255)
    address_line2: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=120)
    state_province: str | None = Field(default=None, max_length=120)
    postal_code: str | None = Field(default=None, max_length=30)
    country: str | None = Field(default=None, max_length=100)
    lifecycle_stage: CrmLifecycleStage | None = None
    relationship_status: CrmRelationshipStatus | None = None
    relationship_strength: CrmRelationshipStrength | None = None
    priority: CrmContactPriority | None = None
    source: str | None = Field(default=None, max_length=120)
    referred_by_contact_id: UUID | None = None
    last_contact_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    tags: list[str] | None = None
    status: CrmContactStatus | None = None
    owner_user_id: UUID | None = None
    company_id: UUID | None = None
    lead_id: UUID | None = None
    investor_id: UUID | None = None
    notes: str | None = Field(default=None, max_length=5000)
    is_favorite: bool | None = None
    is_pinned: bool | None = None
    junk_reason: str | None = Field(default=None, max_length=255)
    communication_prefs: dict[str, Any] | None = None
    compliance_data: dict[str, Any] | None = None
    investment_profile: CrmInvestmentProfileSchema | None = None
    buyer_profile: CrmBuyerProfileSchema | None = None
    broker_profile: CrmBrokerProfileSchema | None = None
    vendor_profile: CrmVendorProfileSchema | None = None


class CrmContactListResponse(BaseModel):
    items: list[CrmContactSummary]
    page: int
    page_size: int
    total: int
    pages: int
    request_id: str = ""


class CrmContactMutationResponse(BaseModel):
    contact: CrmContactDetail
    warnings: list[str] = Field(default_factory=list)


class CrmDuplicateMatch(BaseModel):
    contact_id: UUID
    display_name: str
    match_reason: str
    match_score: float


class CrmDuplicateCheckRequest(BaseModel):
    primary_email: str | None = None
    primary_phone: str | None = None
    display_name: str | None = None
    organization_name: str | None = None
    linkedin_url: str | None = None
    whatsapp: str | None = None
    exclude_contact_id: UUID | None = None


class CrmDuplicateCheckResponse(BaseModel):
    matches: list[CrmDuplicateMatch]


class CrmContactMergeRequest(BaseModel):
    survivor_contact_id: UUID
    merged_contact_id: UUID


class CrmContactBulkUpdateRequest(BaseModel):
    contact_ids: list[UUID] = Field(min_length=1)
    owner_user_id: UUID | None = None
    lifecycle_stage: CrmLifecycleStage | None = None
    priority: CrmContactPriority | None = None
    tags: list[str] | None = None
    archive: bool | None = None


class CrmContactAssignOwnerRequest(BaseModel):
    owner_user_id: UUID


class CrmContactStatusChangeRequest(BaseModel):
    status: CrmContactStatus
    junk_reason: str | None = Field(default=None, max_length=255)
    next_follow_up_at: datetime | None = None


class CrmContactImportRow(BaseModel):
    display_name: str
    contact_type: CrmContactType = CrmContactType.PROSPECT
    primary_email: str | None = None
    primary_phone: str | None = None
    organization_name: str | None = None
    tags: list[str] | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None


class CrmContactImportRequest(BaseModel):
    rows: list[CrmContactImportRow] = Field(min_length=1)
    mode: str = Field(default="create", pattern="^(create|update|skip|merge)$")


class CrmContactImportResponse(BaseModel):
    created: int = 0
    updated: int = 0
    skipped: int = 0
    errors: list[str] = Field(default_factory=list)


class CrmContactSavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_shared: bool = False
    is_default: bool = False
    filters_json: dict[str, Any] | None = None
    sort_by: str | None = Field(default=None, max_length=40)
    sort_dir: str | None = Field(default=None, pattern="^(asc|desc)$")
    columns_json: list[str] | None = None
    density: str | None = Field(default=None, max_length=20)


class CrmContactSavedViewUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    is_shared: bool | None = None
    is_default: bool | None = None
    filters_json: dict[str, Any] | None = None
    sort_by: str | None = Field(default=None, max_length=40)
    sort_dir: str | None = Field(default=None, pattern="^(asc|desc)$")
    columns_json: list[str] | None = None
    density: str | None = Field(default=None, max_length=20)


class CrmContactSavedViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    owner_user_id: UUID
    is_shared: bool
    is_default: bool
    filters_json: dict[str, Any] | None = None
    sort_by: str | None = None
    sort_dir: str | None = None
    columns_json: list[str] | None = None
    density: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmContactTimelineEntry(BaseModel):
    id: str
    source: str
    activity_type: str
    title: str
    summary: str | None = None
    status: str | None = None
    actor_name: str | None = None
    created_at: datetime
    is_system_event: bool = False
    imported_historical_comment: bool = False
    action: str | None = None
    description_key: str | None = None
    metadata: dict[str, Any] | None = None
    project_contexts: list[str] = Field(default_factory=list)
    project_assignment: str | None = None


class CrmPeopleCounts(BaseModel):
    total: int
    active: int
    junk: int
    review_required: int
    missing_info: int


class CrmInvestorCounts(BaseModel):
    total: int
    active: int
    purchases: int
    missing_info: int
    review_required: int


class CrmJunkReasonCount(BaseModel):
    reason: str
    count: int


class CrmJunkReasonListResponse(BaseModel):
    items: list[CrmJunkReasonCount]
    total: int


class CrmContactRelationshipEntry(BaseModel):
    contact_id: UUID
    display_name: str
    contact_type: CrmContactType
    relationship_status: CrmRelationshipStatus
    relationship_strength: CrmRelationshipStrength


class CrmContactTimelineResponse(BaseModel):
    items: list[CrmContactTimelineEntry]


class CrmContactRelationshipsResponse(BaseModel):
    items: list[CrmContactRelationshipEntry]
