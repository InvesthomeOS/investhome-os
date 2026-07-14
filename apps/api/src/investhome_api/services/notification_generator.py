"""Generate notifications from real business data."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from investhome_api.config.executive_config import COMPLETED_PROJECT_STATUSES
from investhome_api.config.notification_config import (
    BUDGET_VARIANCE_AT_RISK_RATIO,
    BUDGET_VARIANCE_ATTENTION_RATIO,
    COMPLETION_APPROACHING_DAYS,
    EXECUTIVE_ONLY_RULES,
    FUNDING_GAP_AT_RISK,
    FUNDING_GAP_ATTENTION,
    LEAD_INACTIVITY_DAYS,
    LEAD_NO_FOLLOWUP_DAYS,
    LOW_AVAILABLE_BALANCE_RATIO,
    PROPOSAL_NOT_SENT_DAYS,
    QUALIFIED_LEAD_WAITING_DAYS,
)
from investhome_api.models.finance import (
    CommitmentStatus,
    FinancialAccount,
    FinanceTransaction,
    FundingCommitment,
    ObligationStatus,
    PaymentObligation,
    ProjectBudget,
    TransactionStatus,
)
from investhome_api.models.investor import Investor, InvestorStatus
from investhome_api.models.lead import Lead, LeadStatus
from investhome_api.models.notification import NotificationSource
from investhome_api.models.project import Project, ProjectStatus
from investhome_api.models.user_auth import Role, User, UserStatus
from investhome_api.services.notification_service import (
    NotificationCandidate,
    NotificationPriority,
    NotificationType,
    _dedupe_key,
    dismiss_stale_automation,
    upsert_candidate,
)
from investhome_api.services.permission_service import is_super_admin, user_has_permission

ACTIVE_LEAD_STATUSES = frozenset(
    {
        LeadStatus.NEW,
        LeadStatus.CONTACTED,
        LeadStatus.QUALIFIED,
        LeadStatus.MEETING_SCHEDULED,
        LeadStatus.PROPOSAL_SENT,
        LeadStatus.NEGOTIATION,
    }
)


def _project_funding_gap(project: Project) -> Decimal:
    required = project.equity_required or Decimal("0")
    raised = project.equity_raised or Decimal("0")
    return max(required - raised, Decimal("0"))


def _user_has_executive(user: User) -> bool:
    return is_super_admin(user) or user_has_permission(user, "executive", "view")


def _user_can_receive_rule(user: User, rule_key: str, resource: str) -> bool:
    if rule_key in EXECUTIVE_ONLY_RULES and not _user_has_executive(user):
        return False
    if is_super_admin(user):
        return True
    return user_has_permission(user, resource, "view")


def collect_candidates_for_user(db: Session, user: User) -> list[NotificationCandidate]:
    today = date.today()
    candidates: list[NotificationCandidate] = []

    if _user_can_receive_rule(user, "lead.no_followup", "leads"):
        leads = db.scalars(
            select(Lead).where(Lead.archived_at.is_(None), Lead.status.in_(ACTIVE_LEAD_STATUSES))
        ).all()
        cutoff = today - timedelta(days=LEAD_NO_FOLLOWUP_DAYS)
        for lead in leads:
            if lead.updated_at.date() <= cutoff:
                candidates.append(
                    NotificationCandidate(
                        rule_key="lead.no_followup",
                        type=NotificationType.REMINDER,
                        priority=NotificationPriority.MEDIUM,
                        title_key="notifications.lead.no_followup.title",
                        message_key="notifications.lead.no_followup.message",
                        metadata={"name": lead.full_name, "days": LEAD_NO_FOLLOWUP_DAYS},
                        related_entity_type="lead",
                        related_entity_id=lead.id,
                        is_demo=lead.is_demo,
                        link_module="leads",
                        related_label=lead.full_name,
                    )
                )

    if _user_can_receive_rule(user, "lead.qualified_waiting", "leads"):
        waiting_cutoff = today - timedelta(days=QUALIFIED_LEAD_WAITING_DAYS)
        leads = db.scalars(
            select(Lead).where(
                Lead.archived_at.is_(None),
                Lead.status == LeadStatus.QUALIFIED,
            )
        ).all()
        for lead in leads:
            if lead.updated_at.date() <= waiting_cutoff:
                candidates.append(
                    NotificationCandidate(
                        rule_key="lead.qualified_waiting",
                        type=NotificationType.REMINDER,
                        priority=NotificationPriority.MEDIUM,
                        title_key="notifications.lead.qualified_waiting.title",
                        message_key="notifications.lead.qualified_waiting.message",
                        metadata={"name": lead.full_name},
                        related_entity_type="lead",
                        related_entity_id=lead.id,
                        is_demo=lead.is_demo,
                        link_module="leads",
                        related_label=lead.full_name,
                    )
                )

    if _user_can_receive_rule(user, "lead.proposal_not_sent", "leads"):
        proposal_cutoff = today - timedelta(days=PROPOSAL_NOT_SENT_DAYS)
        leads = db.scalars(
            select(Lead).where(
                Lead.archived_at.is_(None),
                Lead.status == LeadStatus.MEETING_SCHEDULED,
            )
        ).all()
        for lead in leads:
            if lead.updated_at.date() <= proposal_cutoff:
                candidates.append(
                    NotificationCandidate(
                        rule_key="lead.proposal_not_sent",
                        type=NotificationType.WARNING,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.lead.proposal_not_sent.title",
                        message_key="notifications.lead.proposal_not_sent.message",
                        metadata={"name": lead.full_name},
                        related_entity_type="lead",
                        related_entity_id=lead.id,
                        is_demo=lead.is_demo,
                        link_module="leads",
                        related_label=lead.full_name,
                    )
                )

    if _user_can_receive_rule(user, "lead.meeting_today", "leads"):
        leads = db.scalars(
            select(Lead).where(
                Lead.archived_at.is_(None),
                Lead.status == LeadStatus.MEETING_SCHEDULED,
            )
        ).all()
        for lead in leads:
            if lead.updated_at.date() == today:
                candidates.append(
                    NotificationCandidate(
                        rule_key="lead.meeting_today",
                        type=NotificationType.REMINDER,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.lead.meeting_today.title",
                        message_key="notifications.lead.meeting_today.message",
                        metadata={"name": lead.full_name},
                        related_entity_type="lead",
                        related_entity_id=lead.id,
                        is_demo=lead.is_demo,
                        link_module="leads",
                        related_label=lead.full_name,
                    )
                )

    if _user_can_receive_rule(user, "lead.inactive_qualified", "leads"):
        inactivity_cutoff = today - timedelta(days=LEAD_INACTIVITY_DAYS)
        leads = db.scalars(
            select(Lead).where(Lead.archived_at.is_(None), Lead.status == LeadStatus.QUALIFIED)
        ).all()
        for lead in leads:
            if lead.updated_at.date() <= inactivity_cutoff:
                candidates.append(
                    NotificationCandidate(
                        rule_key="lead.inactive_qualified",
                        type=NotificationType.REMINDER,
                        priority=NotificationPriority.LOW,
                        title_key="notifications.lead.inactive_qualified.title",
                        message_key="notifications.lead.inactive_qualified.message",
                        metadata={"name": lead.full_name, "days": LEAD_INACTIVITY_DAYS},
                        related_entity_type="lead",
                        related_entity_id=lead.id,
                        is_demo=lead.is_demo,
                        link_module="leads",
                        related_label=lead.full_name,
                    )
                )

    if _user_can_receive_rule(user, "investor.follow_up_overdue", "investors"):
        investors = db.scalars(select(Investor).where(Investor.archived_at.is_(None))).all()
        for investor in investors:
            if investor.next_follow_up_date and investor.next_follow_up_date < today:
                candidates.append(
                    NotificationCandidate(
                        rule_key="investor.follow_up_overdue",
                        type=NotificationType.INVESTOR,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.investor.follow_up_overdue.title",
                        message_key="notifications.investor.follow_up_overdue.message",
                        metadata={"name": investor.full_name},
                        related_entity_type="investor",
                        related_entity_id=investor.id,
                        is_demo=investor.is_demo,
                        link_module="investors",
                        related_label=investor.full_name,
                    )
                )

    if _user_can_receive_rule(user, "investor.funding_commitment_due", "investors"):
        commitments = db.scalars(
            select(FundingCommitment).where(
                FundingCommitment.status.notin_(
                    [CommitmentStatus.FULLY_FUNDED, CommitmentStatus.CANCELLED]
                )
            )
        ).all()
        for commitment in commitments:
            if commitment.target_funding_date and commitment.target_funding_date <= today:
                candidates.append(
                    NotificationCandidate(
                        rule_key="investor.funding_commitment_due",
                        type=NotificationType.INVESTOR,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.investor.funding_commitment_due.title",
                        message_key="notifications.investor.funding_commitment_due.message",
                        metadata={
                            "amount": str(commitment.committed_amount),
                            "currency": commitment.currency,
                        },
                        related_entity_type="funding_commitment",
                        related_entity_id=commitment.id,
                        is_demo=commitment.is_demo,
                        link_module="finance",
                        link_query={"tab": "funding"},
                    )
                )

    if _user_can_receive_rule(user, "project.completion_approaching", "projects"):
        approaching = today + timedelta(days=COMPLETION_APPROACHING_DAYS)
        projects = db.scalars(select(Project).where(Project.archived_at.is_(None))).all()
        for project in projects:
            if (
                project.target_completion_date
                and today <= project.target_completion_date <= approaching
                and project.project_status.value not in COMPLETED_PROJECT_STATUSES
            ):
                candidates.append(
                    NotificationCandidate(
                        rule_key="project.completion_approaching",
                        type=NotificationType.PROJECT,
                        priority=NotificationPriority.MEDIUM,
                        title_key="notifications.project.completion_approaching.title",
                        message_key="notifications.project.completion_approaching.message",
                        metadata={"name": project.project_name},
                        related_entity_type="project",
                        related_entity_id=project.id,
                        is_demo=project.is_demo,
                        link_module="projects",
                        related_label=project.project_name,
                    )
                )

    if _user_can_receive_rule(user, "project.overdue", "projects"):
        projects = db.scalars(select(Project).where(Project.archived_at.is_(None))).all()
        for project in projects:
            if (
                project.target_completion_date
                and project.target_completion_date < today
                and project.project_status.value not in COMPLETED_PROJECT_STATUSES
            ):
                candidates.append(
                    NotificationCandidate(
                        rule_key="project.overdue",
                        type=NotificationType.PROJECT,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.project.overdue.title",
                        message_key="notifications.project.overdue.message",
                        metadata={"name": project.project_name},
                        related_entity_type="project",
                        related_entity_id=project.id,
                        is_demo=project.is_demo,
                        link_module="projects",
                        related_label=project.project_name,
                    )
                )

    if _user_can_receive_rule(user, "project.funding_gap", "projects"):
        projects = db.scalars(select(Project).where(Project.archived_at.is_(None))).all()
        for project in projects:
            gap = _project_funding_gap(project)
            if gap >= FUNDING_GAP_ATTENTION:
                candidates.append(
                    NotificationCandidate(
                        rule_key="project.funding_gap",
                        type=NotificationType.PROJECT,
                        priority=(
                            NotificationPriority.CRITICAL
                            if gap >= FUNDING_GAP_AT_RISK
                            else NotificationPriority.HIGH
                        ),
                        title_key="notifications.project.funding_gap.title",
                        message_key="notifications.project.funding_gap.message",
                        metadata={"name": project.project_name, "gap": str(gap)},
                        related_entity_type="project",
                        related_entity_id=project.id,
                        is_demo=project.is_demo,
                        link_module="projects",
                        related_label=project.project_name,
                    )
                )

    if _user_can_receive_rule(user, "project.budget_variance", "projects"):
        projects = db.scalars(select(Project).where(Project.archived_at.is_(None))).all()
        for project in projects:
            budgets = db.scalars(
                select(ProjectBudget).where(ProjectBudget.project_id == project.id)
            ).all()
            for budget in budgets:
                revised = budget.revised_budget or budget.original_budget or Decimal("0")
                if revised <= 0:
                    continue
                forecast = budget.forecast_amount or revised
                ratio = abs(forecast - revised) / revised
                if ratio >= BUDGET_VARIANCE_ATTENTION_RATIO:
                    candidates.append(
                        NotificationCandidate(
                            rule_key="project.budget_variance",
                            type=NotificationType.PROJECT,
                            priority=(
                                NotificationPriority.CRITICAL
                                if ratio >= BUDGET_VARIANCE_AT_RISK_RATIO
                                else NotificationPriority.MEDIUM
                            ),
                            title_key="notifications.project.budget_variance.title",
                            message_key="notifications.project.budget_variance.message",
                            metadata={"name": project.project_name, "variance": f"{ratio:.0%}"},
                            related_entity_type="project_budget",
                            related_entity_id=budget.id,
                            is_demo=budget.is_demo,
                            link_module="finance",
                            link_query={"tab": "budgets"},
                            related_label=project.project_name,
                        )
                    )

    if _user_can_receive_rule(user, "finance.payment_due", "finance"):
        obligations = db.scalars(
            select(PaymentObligation).where(
                PaymentObligation.archived_at.is_(None),
                PaymentObligation.status.notin_(
                    [ObligationStatus.PAID, ObligationStatus.CANCELLED]
                ),
            )
        ).all()
        for obligation in obligations:
            if obligation.due_date and obligation.due_date == today:
                candidates.append(
                    NotificationCandidate(
                        rule_key="finance.payment_due",
                        type=NotificationType.PAYMENT,
                        priority=NotificationPriority.MEDIUM,
                        title_key="notifications.finance.payment_due.title",
                        message_key="notifications.finance.payment_due.message",
                        metadata={
                            "payee": obligation.payee or "",
                            "amount": str(obligation.amount),
                            "currency": obligation.currency,
                        },
                        related_entity_type="payment_obligation",
                        related_entity_id=obligation.id,
                        is_demo=obligation.is_demo,
                        link_module="finance",
                        link_query={"tab": "payments"},
                        related_label=obligation.payee,
                    )
                )
            elif obligation.status == ObligationStatus.OVERDUE or (
                obligation.due_date and obligation.due_date < today
            ):
                candidates.append(
                    NotificationCandidate(
                        rule_key="finance.payment_overdue",
                        type=NotificationType.PAYMENT,
                        priority=NotificationPriority.CRITICAL,
                        title_key="notifications.finance.payment_overdue.title",
                        message_key="notifications.finance.payment_overdue.message",
                        metadata={
                            "payee": obligation.payee or "",
                            "amount": str(obligation.amount),
                            "currency": obligation.currency,
                        },
                        related_entity_type="payment_obligation",
                        related_entity_id=obligation.id,
                        is_demo=obligation.is_demo,
                        link_module="finance",
                        link_query={"tab": "payments"},
                        related_label=obligation.payee,
                    )
                )

    if _user_can_receive_rule(user, "finance.low_cash_balance", "finance"):
        accounts = db.scalars(
            select(FinancialAccount).where(FinancialAccount.archived_at.is_(None))
        ).all()
        for account in accounts:
            current = account.current_balance or Decimal("0")
            available = account.available_balance or Decimal("0")
            if current > 0 and available / current < LOW_AVAILABLE_BALANCE_RATIO:
                candidates.append(
                    NotificationCandidate(
                        rule_key="finance.low_cash_balance",
                        type=NotificationType.FINANCE,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.finance.low_cash_balance.title",
                        message_key="notifications.finance.low_cash_balance.message",
                        metadata={
                            "account": account.account_name,
                            "currency": account.currency,
                        },
                        related_entity_type="financial_account",
                        related_entity_id=account.id,
                        is_demo=account.is_demo,
                        link_module="finance",
                        link_query={"tab": "accounts"},
                        related_label=account.account_name,
                    )
                )

    if _user_can_receive_rule(user, "finance.transaction_overdue", "finance"):
        transactions = db.scalars(
            select(FinanceTransaction).where(
                FinanceTransaction.archived_at.is_(None),
                FinanceTransaction.status.in_(
                    [TransactionStatus.PENDING, TransactionStatus.SCHEDULED, TransactionStatus.OVERDUE]
                ),
            )
        ).all()
        for txn in transactions:
            if txn.due_date and txn.due_date < today:
                candidates.append(
                    NotificationCandidate(
                        rule_key="finance.transaction_overdue",
                        type=NotificationType.FINANCE,
                        priority=NotificationPriority.HIGH,
                        title_key="notifications.finance.transaction_failed.title",
                        message_key="notifications.finance.transaction_failed.message",
                        metadata={
                            "description": txn.description or "",
                            "amount": str(txn.amount),
                            "currency": txn.currency,
                        },
                        related_entity_type="transaction",
                        related_entity_id=txn.id,
                        is_demo=txn.is_demo,
                        link_module="finance",
                        link_query={"tab": "transactions"},
                        related_label=txn.description,
                    )
                )

    return candidates


def sync_notifications_for_user(db: Session, user: User) -> int:
    """Evaluate business rules and upsert notifications for one user."""
    candidates = collect_candidates_for_user(db, user)
    active_keys: set[str] = set()
    created = 0
    for candidate in candidates:
        key = _dedupe_key(
            candidate.rule_key, candidate.related_entity_type, candidate.related_entity_id
        )
        active_keys.add(key)
        if upsert_candidate(db, user.id, candidate):
            created += 1
    dismiss_stale_automation(db, user.id, active_keys)
    db.flush()
    return created


def sync_notifications_for_all_users(db: Session) -> int:
    users = list(
        db.scalars(
            select(User)
            .where(User.archived_at.is_(None), User.status == UserStatus.ACTIVE)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        ).all()
    )
    total = 0
    for user in users:
        total += sync_notifications_for_user(db, user)
    db.commit()
    return total
