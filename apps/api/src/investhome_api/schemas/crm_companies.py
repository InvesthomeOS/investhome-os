"""CRM Company management schemas."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CrmCompanyTypeEnum(str, Enum):
    INVESTMENT_COMPANY = "investment_company"
    BUYER_ENTITY = "buyer_entity"
    BROKERAGE = "brokerage"
    LAW_FIRM = "law_firm"
    BANK = "bank"
    LENDER = "lender"
    PROPERTY_MANAGEMENT = "property_management"
    CONSTRUCTION = "construction"
    CONTRACTOR = "contractor"
    ARCHITECTURE = "architecture"
    ACCOUNTING = "accounting"
    CONSULTING = "consulting"
    INSURANCE = "insurance"
    MEDIA = "media"
    GOVERNMENT = "government"
    VENDOR = "vendor"
    PARTNER = "partner"
    INTERNAL_ENTITY = "internal_entity"
    OTHER = "other"


class CrmCompanyStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    ARCHIVED = "archived"


class CrmEntityTypeEnum(str, Enum):
    CORPORATION = "corporation"
    LLC = "llc"
    PARTNERSHIP = "partnership"
    TRUST = "trust"
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    NON_PROFIT = "non_profit"
    GOVERNMENT = "government"
    OTHER = "other"


class CrmCompanyLifecycleStageEnum(str, Enum):
    NEW = "new"
    ENGAGED = "engaged"
    QUALIFIED = "qualified"
    ACTIVE_RELATIONSHIP = "active_relationship"
    DORMANT = "dormant"
    CHURNED = "churned"


class CrmCompanyAddressTypeEnum(str, Enum):
    HEADQUARTERS = "headquarters"
    BILLING = "billing"
    SHIPPING = "shipping"
    MAILING = "mailing"
    BRANCH = "branch"
    OTHER = "other"


class CrmCompanyContactRoleEnum(str, Enum):
    PRIMARY = "primary"
    BILLING = "billing"
    LEGAL = "legal"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"
    OTHER = "other"


class CrmCompanyContactStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    FORMER = "former"


class CrmCompanyRelationshipTypeEnum(str, Enum):
    PARENT = "parent"
    SUBSIDIARY = "subsidiary"
    AFFILIATE = "affiliate"
    PARTNER = "partner"
    COMPETITOR = "competitor"
    VENDOR = "vendor"
    CLIENT = "client"
    INVESTOR = "investor"
    OTHER = "other"


class CrmCompanyAddressCreate(BaseModel):
    address_type: CrmCompanyAddressTypeEnum = CrmCompanyAddressTypeEnum.HEADQUARTERS
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    is_primary: bool = False


class CrmCompanyAddressResponse(CrmCompanyAddressCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class CrmCompanyContactCreate(BaseModel):
    contact_id: UUID
    role: CrmCompanyContactRoleEnum = CrmCompanyContactRoleEnum.OTHER
    job_title: str | None = None
    department: str | None = None
    relationship_type: str | None = None
    ownership_percent: float | None = None
    signing_authority: bool = False
    is_primary: bool = False
    start_date: date | None = None
    end_date: date | None = None
    status: CrmCompanyContactStatusEnum = CrmCompanyContactStatusEnum.ACTIVE


class CrmCompanyContactUpdate(BaseModel):
    role: CrmCompanyContactRoleEnum | None = None
    job_title: str | None = None
    department: str | None = None
    relationship_type: str | None = None
    ownership_percent: float | None = None
    signing_authority: bool | None = None
    is_primary: bool | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: CrmCompanyContactStatusEnum | None = None


class CrmCompanyContactResponse(CrmCompanyContactCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    contact_display_name: str | None = None


class CrmCompanyRelationshipCreate(BaseModel):
    target_company_id: UUID
    relationship_type: CrmCompanyRelationshipTypeEnum
    is_reciprocal: bool = False
    strength: str = "moderate"
    notes: str | None = None


class CrmCompanyRelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    source_company_id: UUID
    target_company_id: UUID
    relationship_type: str
    is_reciprocal: bool
    status: str
    strength: str
    notes: str | None = None
    target_display_name: str | None = None


class CrmCompanyFinancialProfileSchema(BaseModel):
    credit_rating: str | None = None
    annual_revenue: float | None = None
    net_worth: float | None = None
    total_assets: float | None = None
    total_liabilities: float | None = None
    fiscal_year_end: str | None = None
    currency: str | None = None
    bank_name: str | None = None
    notes: str | None = None


class CrmCompanyInvestmentProfileSchema(BaseModel):
    aum: float | None = None
    investment_focus: list[str] | None = None
    preferred_asset_classes: list[str] | None = None
    preferred_regions: list[str] | None = None
    ticket_size_min: float | None = None
    ticket_size_max: float | None = None
    fund_count: int | None = None
    notes: str | None = None


class CrmCompanyBrokerageProfileSchema(BaseModel):
    license_number: str | None = None
    license_state: str | None = None
    specialization: str | None = None
    market_coverage: list[str] | None = None
    agent_count: int | None = None
    notes: str | None = None


class CrmCompanyLenderProfileSchema(BaseModel):
    lender_type: str | None = None
    nmls_id: str | None = None
    loan_types: list[str] | None = None
    max_loan_amount: float | None = None
    min_credit_score: int | None = None
    notes: str | None = None


class CrmCompanyVendorProfileSchema(BaseModel):
    vendor_category: str | None = None
    payment_terms: str | None = None
    contract_status: str | None = None
    insurance_verified: bool = False
    notes: str | None = None


class CrmCompanyLawFirmProfileSchema(BaseModel):
    bar_number: str | None = None
    practice_areas: list[str] | None = None
    attorney_count: int | None = None
    notes: str | None = None


class CrmCompanyPropertyManagementProfileSchema(BaseModel):
    units_managed: int | None = None
    property_types: list[str] | None = None
    service_areas: list[str] | None = None
    license_number: str | None = None
    notes: str | None = None


class CrmCompanyCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = None
    trade_name: str | None = None
    company_type: CrmCompanyTypeEnum
    company_types: list[CrmCompanyTypeEnum] | None = None
    entity_type: CrmEntityTypeEnum | None = None
    status: CrmCompanyStatusEnum = CrmCompanyStatusEnum.ACTIVE
    lifecycle_stage: CrmCompanyLifecycleStageEnum = CrmCompanyLifecycleStageEnum.NEW
    registration_number: str | None = None
    tax_id: str | None = None
    ein: str | None = None
    duns_number: str | None = None
    incorporation_date: date | None = None
    incorporation_country: str | None = None
    incorporation_state: str | None = None
    primary_email: str | None = None
    secondary_emails: list[str] | None = None
    primary_phone: str | None = None
    secondary_phones: list[str] | None = None
    website: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    annual_revenue: float | None = None
    description: str | None = None
    source: str | None = None
    owner_user_id: UUID | None = None
    parent_company_id: UUID | None = None
    tags: list[str] | None = None
    notes: str | None = None
    addresses: list[CrmCompanyAddressCreate] | None = None
    financial_profile: CrmCompanyFinancialProfileSchema | None = None
    investment_profile: CrmCompanyInvestmentProfileSchema | None = None
    brokerage_profile: CrmCompanyBrokerageProfileSchema | None = None
    lender_profile: CrmCompanyLenderProfileSchema | None = None
    vendor_profile: CrmCompanyVendorProfileSchema | None = None
    law_firm_profile: CrmCompanyLawFirmProfileSchema | None = None
    property_management_profile: CrmCompanyPropertyManagementProfileSchema | None = None


class CrmCompanyUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = None
    trade_name: str | None = None
    company_type: CrmCompanyTypeEnum | None = None
    company_types: list[CrmCompanyTypeEnum] | None = None
    entity_type: CrmEntityTypeEnum | None = None
    status: CrmCompanyStatusEnum | None = None
    lifecycle_stage: CrmCompanyLifecycleStageEnum | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    ein: str | None = None
    duns_number: str | None = None
    incorporation_date: date | None = None
    incorporation_country: str | None = None
    incorporation_state: str | None = None
    primary_email: str | None = None
    secondary_emails: list[str] | None = None
    primary_phone: str | None = None
    secondary_phones: list[str] | None = None
    website: str | None = None
    domain: str | None = None
    linkedin_url: str | None = None
    industry: str | None = None
    employee_count: int | None = None
    annual_revenue: float | None = None
    description: str | None = None
    source: str | None = None
    owner_user_id: UUID | None = None
    parent_company_id: UUID | None = None
    tags: list[str] | None = None
    notes: str | None = None
    addresses: list[CrmCompanyAddressCreate] | None = None
    financial_profile: CrmCompanyFinancialProfileSchema | None = None
    investment_profile: CrmCompanyInvestmentProfileSchema | None = None
    brokerage_profile: CrmCompanyBrokerageProfileSchema | None = None
    lender_profile: CrmCompanyLenderProfileSchema | None = None
    vendor_profile: CrmCompanyVendorProfileSchema | None = None
    law_firm_profile: CrmCompanyLawFirmProfileSchema | None = None
    property_management_profile: CrmCompanyPropertyManagementProfileSchema | None = None


class CrmCompanyRelatedPerson(BaseModel):
    id: UUID
    display_name: str
    contact_type: str | None = None
    is_broker: bool = False


class CrmCompanyRelatedAgreement(BaseModel):
    id: UUID
    project_group: str
    unit_number: str | None = None
    investment_amount: str | None = None
    contact_id: UUID
    contact_display_name: str | None = None


class CrmCompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    display_name: str
    legal_name: str | None = None
    company_type: str
    company_types: list[str] | None = None
    entity_type: str | None = None
    status: str
    lifecycle_stage: str
    primary_email: str | None = None
    primary_phone: str | None = None
    domain: str | None = None
    industry: str | None = None
    relationship_status: str
    relationship_strength: str
    owner_user_id: UUID | None = None
    owner_name: str | None = None
    parent_company_id: UUID | None = None
    tags: list[str] | None = None
    is_favorite: bool = False
    is_pinned: bool = False
    contact_count: int = 0
    city: str | None = None
    country: str | None = None
    related_people: list[CrmCompanyRelatedPerson] = Field(default_factory=list)
    open_relationship_count: int = 0
    related_agreement_count: int = 0
    last_activity_at: datetime | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class CrmCompanyCounts(BaseModel):
    total: int
    brokerage: int
    partner: int
    investor: int
    open_relationships: int


class CrmCompanyDetail(CrmCompanyListItem):
    trade_name: str | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    ein: str | None = None
    duns_number: str | None = None
    incorporation_date: date | None = None
    incorporation_country: str | None = None
    incorporation_state: str | None = None
    secondary_emails: list[str] | None = None
    secondary_phones: list[str] | None = None
    website: str | None = None
    linkedin_url: str | None = None
    employee_count: int | None = None
    annual_revenue: float | None = None
    description: str | None = None
    relationship_score: int = 0
    source: str | None = None
    notes: str | None = None
    last_contact_at: datetime | None = None
    next_follow_up_at: datetime | None = None
    archived_at: datetime | None = None
    addresses: list[CrmCompanyAddressResponse] = []
    contacts: list[CrmCompanyContactResponse] = []
    relationships: list[CrmCompanyRelationshipResponse] = []
    financial_profile: CrmCompanyFinancialProfileSchema | None = None
    investment_profile: CrmCompanyInvestmentProfileSchema | None = None
    brokerage_profile: CrmCompanyBrokerageProfileSchema | None = None
    lender_profile: CrmCompanyLenderProfileSchema | None = None
    vendor_profile: CrmCompanyVendorProfileSchema | None = None
    law_firm_profile: CrmCompanyLawFirmProfileSchema | None = None
    property_management_profile: CrmCompanyPropertyManagementProfileSchema | None = None
    legal_data: dict[str, object] | None = None
    compliance_data: dict[str, object] | None = None
    related_agreements: list[CrmCompanyRelatedAgreement] = Field(default_factory=list)


class CrmCompanyListResponse(BaseModel):
    items: list[CrmCompanyListItem]
    page: int
    page_size: int
    total: int
    pages: int


class CrmCompanyMergeRequest(BaseModel):
    source_id: UUID
    target_id: UUID


class CrmCompanyMergeResponse(BaseModel):
    merged_id: UUID
    archived_source_id: UUID


class CrmCompanyDuplicateCandidate(BaseModel):
    id: UUID
    display_name: str
    legal_name: str | None = None
    match_field: str
    match_value: str
    confidence: float


class CrmCompanyImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = []


class CrmCompanyBulkActionRequest(BaseModel):
    company_ids: list[UUID]
    action: str
    payload: dict[str, object] | None = None


class CrmCompanyBulkActionResponse(BaseModel):
    affected: int


class CrmCompanyHierarchyNode(BaseModel):
    id: UUID
    display_name: str
    company_type: str
    status: str
    parent_company_id: UUID | None = None
    children: list[CrmCompanyHierarchyNode] = []


class CrmCompanyHierarchyResponse(BaseModel):
    roots: list[CrmCompanyHierarchyNode]


class CrmCompanySavedViewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    filters: dict[str, object] | None = None
    columns: list[str] | None = None
    sort_by: str | None = None
    sort_order: str | None = None
    is_default: bool = False


class CrmCompanySavedViewResponse(CrmCompanySavedViewCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime


class CrmCompanyTransferOwnershipRequest(BaseModel):
    owner_user_id: UUID


class CrmCompanyTimelineEntry(BaseModel):
    id: UUID
    action: str
    description_key: str
    actor_name: str | None = None
    metadata: dict[str, object] | None = None
    created_at: datetime


class CrmCompanyTimelineResponse(BaseModel):
    items: list[CrmCompanyTimelineEntry]
    total: int
