"""Background jobs for sales proposal lifecycle."""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from investhome_api.db import session as db_session
from investhome_api.models.sales_proposal import (
    TERMINAL_PROPOSAL_STATUSES,
    ProposalStatus,
    SalesProposal,
)
from investhome_api.services.sales import proposal_notifications as notify
from investhome_api.services.sales.proposal_service import mark_expired

JOB_EXPIRE_PROPOSALS = "sales_expire_proposals"
JOB_PROPOSAL_EXPIRING_REMINDERS = "sales_proposal_expiring_reminders"


async def expire_proposals_job(_ctx: dict) -> None:
    """Mark past-validity proposals as expired — idempotent."""
    db = db_session.SessionLocal()
    try:
        today = date.today()
        proposals = list(
            db.scalars(
                select(SalesProposal).where(
                    SalesProposal.archived_at.is_(None),
                    SalesProposal.status.notin_(tuple(TERMINAL_PROPOSAL_STATUSES)),
                    SalesProposal.valid_until.isnot(None),
                    SalesProposal.valid_until < today,
                )
            ).all()
        )
        for proposal in proposals:
            mark_expired(db, proposal, actor=None)
        db.commit()
    finally:
        db.close()


async def proposal_expiring_reminders_job(_ctx: dict) -> None:
    """Notify owners of proposals expiring within 7 days — dedupe via notification hooks."""
    db = db_session.SessionLocal()
    try:
        today = date.today()
        cutoff = today.toordinal()
        proposals = list(
            db.scalars(
                select(SalesProposal).where(
                    SalesProposal.archived_at.is_(None),
                    SalesProposal.status.in_(
                        [
                            ProposalStatus.APPROVED,
                            ProposalStatus.SENT,
                            ProposalStatus.VIEWED,
                        ]
                    ),
                    SalesProposal.valid_until.isnot(None),
                    SalesProposal.valid_until >= today,
                )
            ).all()
        )
        for proposal in proposals:
            if proposal.valid_until is None:
                continue
            days_left = proposal.valid_until.toordinal() - cutoff
            if 0 <= days_left <= 7:
                notify.notify_expiring(db, proposal, days_left=days_left)
        db.commit()
    finally:
        db.close()
