"""CRM reporting routes — prefix /crm/reports."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_reports import CrmReportsSummary, CrmReportsWorkspace
from investhome_api.services.crm.report_service import build_crm_reports_summary, build_crm_reports_workspace
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm/reports", tags=["crm-reports"])


def _require_crm_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(user, "crm", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency


@router.get("/summary", response_model=CrmReportsSummary)
def get_crm_reports_summary(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmReportsSummary:
    return build_crm_reports_summary(db)


@router.get("/workspace", response_model=CrmReportsWorkspace)
def get_crm_reports_workspace(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    project_group: str | None = Query(default=None, max_length=40),
    owner_id: UUID | None = Query(default=None),
    source: str | None = Query(default=None, max_length=100),
    currency: str | None = Query(default=None, max_length=12),
) -> CrmReportsWorkspace:
    return build_crm_reports_workspace(
        db,
        date_from=date_from,
        date_to=date_to,
        project_group=project_group or None,
        owner_id=owner_id,
        source=source or None,
        currency=currency or None,
    )
