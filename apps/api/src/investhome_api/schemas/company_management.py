"""Pydantic schemas for companies management."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from investhome_api.models.company import (
    CompanyAddressType,
    CompanyContactRole,
    CompanyEntityType,
    CompanyRelationshipType,
    CompanyStatus,
)


class CompanyAddressBase(BaseModel):
    address_type: CompanyAddressType = CompanyAddressType.OTHER
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    is_primary: bool = False


class CompanyAddressCreate(CompanyAddressBase):
    pass


class CompanyAddressResponse(CompanyAddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyContactBase(BaseModel):
    role: CompanyContactRole = CompanyContactRole.OPERATIONS
    full_name: str = Field(min_length=1, max_length=255)
    email: str | None = None
    phone: str | None = None
    is_signatory: bool = False


class CompanyContactCreate(CompanyContactBase):
    pass


class CompanyContactResponse(CompanyContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyBankAccountBase(BaseModel):
    bank_name: str = Field(min_length=1, max_length=255)
    account_name: str | None = None
    account_number: str | None = None
    iban: str | None = None
    routing_number: str | None = None
    currency: str = "USD"
    is_primary: bool = False


class CompanyBankAccountCreate(CompanyBankAccountBase):
    pass


class CompanyBankAccountResponse(CompanyBankAccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyDocumentBase(BaseModel):
    document_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    reference_code: str | None = None
    notes: str | None = None


class CompanyDocumentCreate(CompanyDocumentBase):
    pass


class CompanyDocumentResponse(CompanyDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class CompanyRelationshipBase(BaseModel):
    related_company_id: UUID
    relationship_type: CompanyRelationshipType = CompanyRelationshipType.OTHER
    notes: str | None = None


class CompanyRelationshipCreate(CompanyRelationshipBase):
    pass


class CompanyRelationshipResponse(CompanyRelationshipBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    related_company_name: str | None = None
    created_at: datetime


class CompanyBase(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    legal_name: str | None = None
    entity_type: CompanyEntityType = CompanyEntityType.OTHER
    registration_number: str | None = None
    tax_id: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    status: CompanyStatus = CompanyStatus.DRAFT
    industry: str | None = None
    owner_user_id: UUID | None = None
    logo_document_id: UUID | None = None
    notes: str | None = None


class CompanyCreate(CompanyBase):
    addresses: list[CompanyAddressCreate] = Field(default_factory=list)
    contacts: list[CompanyContactCreate] = Field(default_factory=list)
    bank_accounts: list[CompanyBankAccountCreate] = Field(default_factory=list)
    documents: list[CompanyDocumentCreate] = Field(default_factory=list)
    relationships: list[CompanyRelationshipCreate] = Field(default_factory=list)


class CompanyUpdate(BaseModel):
    company_name: str | None = Field(default=None, min_length=1, max_length=255)
    legal_name: str | None = None
    entity_type: CompanyEntityType | None = None
    registration_number: str | None = None
    tax_id: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    status: CompanyStatus | None = None
    industry: str | None = None
    owner_user_id: UUID | None = None
    logo_document_id: UUID | None = None
    notes: str | None = None
    addresses: list[CompanyAddressCreate] | None = None
    contacts: list[CompanyContactCreate] | None = None
    bank_accounts: list[CompanyBankAccountCreate] | None = None
    documents: list[CompanyDocumentCreate] | None = None
    relationships: list[CompanyRelationshipCreate] | None = None


class CompanyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    logo_document_id: UUID | None = None
    company_name: str
    legal_name: str | None = None
    entity_type: str
    registration_number: str | None = None
    tax_id: str | None = None
    country: str | None = None
    state: str | None = None
    city: str | None = None
    status: str
    industry: str | None = None
    owner_user_id: UUID | None = None
    owner_name: str | None = None
    employee_count: int
    branch_count: int
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class CompanyResponse(CompanyListItem):
    notes: str | None = None
    addresses: list[CompanyAddressResponse] = Field(default_factory=list)
    contacts: list[CompanyContactResponse] = Field(default_factory=list)
    bank_accounts: list[CompanyBankAccountResponse] = Field(default_factory=list)
    documents: list[CompanyDocumentResponse] = Field(default_factory=list)
    relationships: list[CompanyRelationshipResponse] = Field(default_factory=list)


class CompanyListResponse(BaseModel):
    items: list[CompanyListItem]
    total: int
    page: int
    page_size: int
    pages: int


class CompanyTransferOwnershipRequest(BaseModel):
    owner_user_id: UUID


class CompanyImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


class CompanyDuplicateResponse(BaseModel):
    company: CompanyResponse
