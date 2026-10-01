"""Strip CRM agreement/purchase financial fields unless crm:view_financial is granted."""

from __future__ import annotations

from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_agreements import CrmAgreementSummary, CrmPurchaseCard
from investhome_api.schemas.crm_contacts import (
    CrmContactAgreementVerification,
    CrmContactDetail,
    CrmContactSummary,
    CrmPurchaseSummary,
)
from investhome_api.schemas.crm_reports import CrmReportAmount, CrmReportsSummary, CrmReportsWorkspace
from investhome_api.services.permission_service import user_has_permission


def can_view_crm_financial(user: User | None) -> bool:
    """Auth-disabled and service callers without a user keep existing full payloads."""
    if user is None:
        return True
    return user_has_permission(user, "crm", "view_financial")


def strip_agreement_summary(item: CrmAgreementSummary) -> CrmAgreementSummary:
    item.investment_amount = None
    item.amount_label = None
    item.deposit_amount = None
    item.payment_dates = None
    item.share_ratio = None
    for participant in item.participants:
        participant.ownership_pct = None
    return item


def strip_purchase_summary(item: CrmPurchaseSummary) -> CrmPurchaseSummary:
    item.amount = None
    item.currency = None
    item.amount_label = None
    for participant in item.participants:
        participant.ownership_pct = None
    return item


def strip_purchase_card(card: CrmPurchaseCard) -> CrmPurchaseCard:
    card.amount = None
    card.currency = None
    card.amount_label = None
    card.payment = {}
    card.payment_fields = []
    card.extra_fields = []
    for participant in card.participants:
        participant.ownership_pct = None
    for related in card.related_purchases:
        related.amount_label = None
    return card


def strip_contact_agreement(item: CrmContactAgreementVerification) -> CrmContactAgreementVerification:
    item.investment_amount = None
    item.payment_amount = None
    item.deposit = None
    item.purchase_price = None
    item.amount_and_currency_label = None
    item.amount_and_currency_field_id = None
    item.amount_and_currency_amount = None
    item.amount_and_currency_currency = None
    return item


def strip_contact_summary_financial(item: CrmContactSummary) -> CrmContactSummary:
    item.verified_amount_totals = []
    return item


def strip_contact_detail_financial(detail: CrmContactDetail) -> CrmContactDetail:
    strip_contact_summary_financial(detail)
    detail.amount_and_currency_label = None
    detail.amount_and_currency_field_id = None
    detail.amount_and_currency_amount = None
    detail.amount_and_currency_currency = None
    detail.crm_agreements = [strip_contact_agreement(row) for row in detail.crm_agreements]
    detail.purchases = [strip_purchase_summary(row) for row in detail.purchases]
    if detail.project_card_pilot is not None:
        detail.project_card_pilot.tutar_by_project = {}
    return detail


def maybe_strip_agreement_summaries(
    user: User | None, items: list[CrmAgreementSummary]
) -> list[CrmAgreementSummary]:
    if can_view_crm_financial(user):
        return items
    return [strip_agreement_summary(item) for item in items]


def maybe_strip_purchase_card(user: User | None, card: CrmPurchaseCard) -> CrmPurchaseCard:
    if can_view_crm_financial(user):
        return card
    return strip_purchase_card(card)


def maybe_strip_contact_summaries(
    user: User | None, items: list[CrmContactSummary]
) -> list[CrmContactSummary]:
    if can_view_crm_financial(user):
        return items
    return [strip_contact_summary_financial(item) for item in items]


def maybe_strip_reports_summary(user: User | None, summary: CrmReportsSummary) -> CrmReportsSummary:
    if can_view_crm_financial(user):
        return summary
    summary.reit_investment = CrmReportAmount(populated_count=0, total=None)
    return summary


def maybe_strip_reports_workspace(user: User | None, workspace: CrmReportsWorkspace) -> CrmReportsWorkspace:
    if can_view_crm_financial(user):
        return workspace
    workspace.kpis.sales_totals = []
    for row in workspace.sales.by_project:
        row.amounts = []
    for row in workspace.sales.table:
        row.amounts = []
    for row in workspace.investors.table:
        row.amounts = []
    workspace.filter_options.currencies = []
    return workspace
