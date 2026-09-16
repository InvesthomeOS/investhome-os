"""CRM workspace API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from investhome_api.api.deps.auth import get_current_user
from investhome_api.db.session import get_db
from investhome_api.models.crm_contact import CrmContactTag, CrmTag
from investhome_api.models.user_auth import User
from investhome_api.schemas.crm import CrmDashboardResponse, CrmTagItem, CrmTagListResponse
from investhome_api.services.crm_dashboard_service import build_crm_dashboard
from investhome_api.services.permission_service import user_has_permission

router = APIRouter(prefix="/crm", tags=["crm"])


def _require_crm_read():
    async def _dependency(user: User = Depends(get_current_user)) -> User:
        if not user_has_permission(user, "crm", "read"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _dependency


@router.get("/dashboard", response_model=CrmDashboardResponse)
def get_crm_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmDashboardResponse:
    return build_crm_dashboard(db, user)


@router.get("/tags", response_model=CrmTagListResponse)
def list_crm_tags(
    db: Session = Depends(get_db),
    user: User = Depends(_require_crm_read()),
) -> CrmTagListResponse:
    del user
    usage = (
        select(CrmContactTag.tag_id, func.count().label("usage_count"))
        .group_by(CrmContactTag.tag_id)
        .subquery()
    )
    rows = db.execute(
        select(CrmTag, func.coalesce(usage.c.usage_count, 0))
        .outerjoin(usage, usage.c.tag_id == CrmTag.id)
        .order_by(CrmTag.name.asc())
    ).all()
    return CrmTagListResponse(
        items=[
            CrmTagItem(
                id=tag.id,
                name=tag.name,
                color=tag.color,
                usage_count=int(usage_count),
            )
            for tag, usage_count in rows
        ]
    )
