"""CRM reporting routes — prefix /crm/reports."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user
from investhome_api.db.session import get_db
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm_reports import CrmReportsSummary
from investhome_api.services.crm.report_service import build_crm_reports_summary
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
