"""Backfill activity log from existing demo and live records."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.models.activity import (
    ActivityAction,
    ActivityActorType,
    ActivityEntityType,
    ActivityLog,
    ActivitySource,
)
from investhome_api.models.finance import (
    FinanceTransaction,
    FundingCommitment,
    ObligationStatus,
    PaymentObligation,
    TransactionStatus,
)
from investhome_api.models.investor import Investor
from investhome_api.models.lead import Lead
from investhome_api.models.project import Project
from investhome_api.services.activity_service import log_activity


def seed_activity_logs() -> int:
    from investhome_api.db.session import SessionLocal

    with SessionLocal() as session:
        existing = session.scalar(select(ActivityLog.id).limit(1))
        if existing is not None:
            return 0

        count = _backfill_from_entities(session)
        session.commit()
        return count


def _backfill_from_entities(session: Session) -> int:
    count = 0

    for lead in session.scalars(select(Lead).where(Lead.archived_at.is_(None))).all():
        log_activity(
            session,
            action=ActivityAction.CREATED,
            entity_type=ActivityEntityType.LEAD,
            entity_id=lead.id,
            description_key="activity.lead.created",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={"name": lead.full_name, "status": lead.status.value},
            is_demo=lead.is_demo,
            created_at=lead.created_at,
        )
        count += 1

    for investor in session.scalars(
        select(Investor).where(Investor.archived_at.is_(None))
    ).all():
        log_activity(
            session,
            action=ActivityAction.CREATED,
            entity_type=ActivityEntityType.INVESTOR,
            entity_id=investor.id,
            description_key="activity.investor.created",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={"name": investor.full_name},
            is_demo=investor.is_demo,
            created_at=investor.created_at,
        )
        count += 1

    for project in session.scalars(
        select(Project).where(Project.archived_at.is_(None))
    ).all():
        log_activity(
            session,
            action=ActivityAction.CREATED,
            entity_type=ActivityEntityType.PROJECT,
            entity_id=project.id,
            description_key="activity.project.created",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={"name": project.project_name},
            is_demo=project.is_demo,
            created_at=project.created_at,
        )
        count += 1
        if project.updated_at != project.created_at:
            log_activity(
                session,
                action=ActivityAction.UPDATED,
                entity_type=ActivityEntityType.PROJECT,
                entity_id=project.id,
                description_key="activity.project.updated",
                actor_type=ActivityActorType.SYSTEM,
                source=ActivitySource.IMPORT,
                metadata={"name": project.project_name},
                is_demo=project.is_demo,
                created_at=project.updated_at,
            )
            count += 1

    for txn in session.scalars(
        select(FinanceTransaction).where(
            FinanceTransaction.archived_at.is_(None),
            FinanceTransaction.status == TransactionStatus.COMPLETED,
        )
    ).all():
        log_activity(
            session,
            action=ActivityAction.PAYMENT_COMPLETED,
            entity_type=ActivityEntityType.TRANSACTION,
            entity_id=txn.id,
            description_key="activity.transaction.completed",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={
                "amount": str(txn.amount),
                "currency": txn.currency,
                "description": txn.description or "",
            },
            is_demo=txn.is_demo,
            created_at=txn.updated_at,
        )
        count += 1

    for commitment in session.scalars(select(FundingCommitment)).all():
        log_activity(
            session,
            action=ActivityAction.FUNDING_ADDED,
            entity_type=ActivityEntityType.FUNDING_COMMITMENT,
            entity_id=commitment.id,
            description_key="activity.funding_commitment.created",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={
                "amount": str(commitment.committed_amount),
                "currency": commitment.currency,
            },
            is_demo=commitment.is_demo,
            created_at=commitment.created_at,
        )
        count += 1

    for obligation in session.scalars(
        select(PaymentObligation).where(PaymentObligation.status == ObligationStatus.PAID)
    ).all():
        log_activity(
            session,
            action=ActivityAction.PAYMENT_COMPLETED,
            entity_type=ActivityEntityType.PAYMENT_OBLIGATION,
            entity_id=obligation.id,
            description_key="activity.payment_obligation.paid",
            actor_type=ActivityActorType.SYSTEM,
            source=ActivitySource.IMPORT,
            metadata={
                "payee": obligation.payee or "",
                "amount": str(obligation.amount),
                "currency": obligation.currency,
            },
            is_demo=obligation.is_demo,
            created_at=obligation.updated_at,
        )
        count += 1

    return count
