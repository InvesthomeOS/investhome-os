"""Sales readiness configuration — requirement groups and document type mapping."""

from __future__ import annotations

from investhome_api.models.document import DocumentType
from investhome_api.models.sales_readiness import ReadinessRequirementType, ReadinessTemplateGroup

LEGAL_REQUIREMENT_TYPES = frozenset(
    {
        ReadinessRequirementType.LEGAL_REVIEW,
        ReadinessRequirementType.OPERATING_AGREEMENT,
        ReadinessRequirementType.DISCLOSURE,
        ReadinessRequirementType.PURCHASE_AGREEMENT,
        ReadinessRequirementType.SUBSCRIPTION_AGREEMENT,
        ReadinessRequirementType.SIGNATURE_REQUIRED,
        ReadinessRequirementType.SIGNATURE_COMPLETED,
    }
)

FINANCE_REQUIREMENT_TYPES = frozenset(
    {
        ReadinessRequirementType.DEPOSIT_DUE,
        ReadinessRequirementType.DEPOSIT_RECEIVED,
        ReadinessRequirementType.FINANCING_CONFIRMATION,
        ReadinessRequirementType.PAYMENT_SCHEDULE,
        ReadinessRequirementType.PROOF_OF_FUNDS,
    }
)

REQUIREMENT_GROUP_MAP: dict[ReadinessRequirementType, ReadinessTemplateGroup] = {
    ReadinessRequirementType.RESERVATION_APPROVED: ReadinessTemplateGroup.RESERVATION,
    ReadinessRequirementType.DEPOSIT_DUE: ReadinessTemplateGroup.DEPOSIT,
    ReadinessRequirementType.DEPOSIT_RECEIVED: ReadinessTemplateGroup.DEPOSIT,
    ReadinessRequirementType.PARTY_IDENTITY: ReadinessTemplateGroup.PARTY,
    ReadinessRequirementType.PARTY_ORGANIZATION_DOCUMENTS: ReadinessTemplateGroup.PARTY,
    ReadinessRequirementType.KYC_DOCUMENT: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.PROOF_OF_FUNDS: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.FINANCING_CONFIRMATION: ReadinessTemplateGroup.DEPOSIT,
    ReadinessRequirementType.PROPOSAL_ACCEPTED: ReadinessTemplateGroup.CONTRACT,
    ReadinessRequirementType.PURCHASE_AGREEMENT: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.SUBSCRIPTION_AGREEMENT: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.OPERATING_AGREEMENT: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.DISCLOSURE: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.PAYMENT_SCHEDULE: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.TAX_FORM: ReadinessTemplateGroup.DOCUMENTS,
    ReadinessRequirementType.LEGAL_REVIEW: ReadinessTemplateGroup.CONTRACT,
    ReadinessRequirementType.SIGNATURE_REQUIRED: ReadinessTemplateGroup.CONTRACT,
    ReadinessRequirementType.SIGNATURE_COMPLETED: ReadinessTemplateGroup.CONTRACT,
    ReadinessRequirementType.CLOSING_DATE_CONFIRMED: ReadinessTemplateGroup.HANDOFF,
    ReadinessRequirementType.OTHER: ReadinessTemplateGroup.HANDOFF,
}

DOCUMENT_TYPE_TO_REQUIREMENT: dict[str, ReadinessRequirementType] = {
    DocumentType.LEGAL_DOCUMENT.value: ReadinessRequirementType.PARTY_IDENTITY,
    DocumentType.INVESTOR_DOCUMENT.value: ReadinessRequirementType.KYC_DOCUMENT,
    DocumentType.BANK_STATEMENT.value: ReadinessRequirementType.PROOF_OF_FUNDS,
    DocumentType.FINANCIAL_REPORT.value: ReadinessRequirementType.PROOF_OF_FUNDS,
    DocumentType.CONTRACT.value: ReadinessRequirementType.PURCHASE_AGREEMENT,
    DocumentType.OPERATING_AGREEMENT.value: ReadinessRequirementType.OPERATING_AGREEMENT,
    DocumentType.SUBSCRIPTION_AGREEMENT.value: ReadinessRequirementType.SUBSCRIPTION_AGREEMENT,
    DocumentType.OFFERING_DOCUMENT.value: ReadinessRequirementType.DISCLOSURE,
    DocumentType.TAX_DOCUMENT.value: ReadinessRequirementType.TAX_FORM,
    DocumentType.CLOSING_DOCUMENT.value: ReadinessRequirementType.SIGNATURE_COMPLETED,
    DocumentType.LOAN_DOCUMENT.value: ReadinessRequirementType.FINANCING_CONFIRMATION,
}

DEFAULT_TEMPLATE_ITEMS: list[dict] = [
    {
        "group": ReadinessTemplateGroup.RESERVATION,
        "type": ReadinessRequirementType.RESERVATION_APPROVED,
        "title": "Reservation approved",
        "mandatory": True,
        "order": 10,
    },
    {
        "group": ReadinessTemplateGroup.DEPOSIT,
        "type": ReadinessRequirementType.DEPOSIT_DUE,
        "title": "Deposit due date confirmed",
        "mandatory": True,
        "order": 20,
    },
    {
        "group": ReadinessTemplateGroup.DEPOSIT,
        "type": ReadinessRequirementType.DEPOSIT_RECEIVED,
        "title": "Deposit received",
        "mandatory": True,
        "order": 30,
    },
    {
        "group": ReadinessTemplateGroup.PARTY,
        "type": ReadinessRequirementType.PARTY_IDENTITY,
        "title": "Party identity confirmed",
        "mandatory": True,
        "order": 40,
    },
    {
        "group": ReadinessTemplateGroup.PARTY,
        "type": ReadinessRequirementType.PARTY_ORGANIZATION_DOCUMENTS,
        "title": "Organization documents",
        "mandatory": False,
        "order": 50,
    },
    {
        "group": ReadinessTemplateGroup.DOCUMENTS,
        "type": ReadinessRequirementType.PROOF_OF_FUNDS,
        "title": "Proof of funds",
        "mandatory": True,
        "order": 60,
    },
    {
        "group": ReadinessTemplateGroup.DOCUMENTS,
        "type": ReadinessRequirementType.KYC_DOCUMENT,
        "title": "KYC document",
        "mandatory": False,
        "order": 70,
    },
    {
        "group": ReadinessTemplateGroup.CONTRACT,
        "type": ReadinessRequirementType.PROPOSAL_ACCEPTED,
        "title": "Proposal accepted",
        "mandatory": True,
        "order": 80,
    },
    {
        "group": ReadinessTemplateGroup.DOCUMENTS,
        "type": ReadinessRequirementType.PURCHASE_AGREEMENT,
        "title": "Purchase agreement",
        "mandatory": True,
        "order": 90,
    },
    {
        "group": ReadinessTemplateGroup.DOCUMENTS,
        "type": ReadinessRequirementType.PAYMENT_SCHEDULE,
        "title": "Payment schedule",
        "mandatory": True,
        "order": 100,
    },
    {
        "group": ReadinessTemplateGroup.CONTRACT,
        "type": ReadinessRequirementType.LEGAL_REVIEW,
        "title": "Legal review complete",
        "mandatory": True,
        "order": 110,
    },
    {
        "group": ReadinessTemplateGroup.CONTRACT,
        "type": ReadinessRequirementType.SIGNATURE_REQUIRED,
        "title": "Signature requested",
        "mandatory": True,
        "order": 120,
    },
    {
        "group": ReadinessTemplateGroup.CONTRACT,
        "type": ReadinessRequirementType.SIGNATURE_COMPLETED,
        "title": "Signature completed",
        "mandatory": True,
        "order": 130,
    },
    {
        "group": ReadinessTemplateGroup.HANDOFF,
        "type": ReadinessRequirementType.CLOSING_DATE_CONFIRMED,
        "title": "Target closing date confirmed",
        "mandatory": True,
        "order": 140,
    },
]
